import json
import logging
import time
from typing import Any, Dict, Optional, Tuple, Type, TypeVar
import httpx
from pydantic import BaseModel, ValidationError

from app.config import Settings, get_settings
from app.exceptions import (
    EmptyInputException,
    LLMServiceException,
    LLMTimeoutException,
    PayloadTooLargeException,
    SchemaValidationException,
)
from app.schemas import (
    CandidateInfo,
    DocumentType,
    EducationItem,
    EntityDetails,
    ExtractionMetadata,
    FinancialSummary,
    InvoiceLineItem,
    InvoiceMetadata,
    InvoiceSchema,
    ReceiptLineItem,
    ReceiptSchema,
    ResumeSchema,
    SkillSet,
    WorkExperienceItem,
)

logger = logging.getLogger("extractor")
T = TypeVar("T", bound=BaseModel)


class LLMExtractor:
    """Production-grade LLM Extractor with schema enforcement, self-correction, and guardrails."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self._groq_client = None
        self._openai_client = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initializes Groq or OpenAI client based on configuration."""
        groq_key = (self.settings.GROQ_API_KEY or "").strip()
        if groq_key and not groq_key.startswith("gsk_your_"):
            try:
                from groq import Groq
                self._groq_client = Groq(
                    api_key=groq_key,
                    timeout=self.settings.REQUEST_TIMEOUT_SECONDS,
                )
                logger.info("Initialized Groq client with model %s", self.settings.GROQ_MODEL)
            except Exception as e:
                logger.warning("Could not initialize Groq client: %s", str(e))

        elif self.settings.OPENAI_API_KEY and not self.settings.OPENAI_API_KEY.startswith("sk-your"):
            try:
                from openai import OpenAI
                self._openai_client = OpenAI(
                    api_key=self.settings.OPENAI_API_KEY,
                    base_url=self.settings.OPENAI_BASE_URL,
                    timeout=self.settings.REQUEST_TIMEOUT_SECONDS,
                )
                logger.info("Initialized OpenAI client with model %s", self.settings.OPENAI_MODEL)
            except Exception as e:
                logger.warning("Could not initialize OpenAI client: %s", str(e))
        else:
            logger.info("No LLM API key provided. Service will use mock fallback if enabled.")

    def validate_input(self, text: str) -> None:
        """Validates input payload size and presence."""
        if not text or not text.strip():
            raise EmptyInputException("Input payload cannot be empty or whitespace only.")

        clean_text = text.strip()
        if len(clean_text) < self.settings.MIN_INPUT_CHARACTERS:
            raise EmptyInputException(
                f"Input text is too short ({len(clean_text)} characters). Minimum required is {self.settings.MIN_INPUT_CHARACTERS} characters."
            )

        if len(text) > self.settings.MAX_INPUT_CHARACTERS:
            raise PayloadTooLargeException(
                current_length=len(text),
                max_length=self.settings.MAX_INPUT_CHARACTERS
            )

    def extract_structured(
        self,
        raw_text: str,
        schema_cls: Type[T],
        doc_type_name: str = "document"
    ) -> Tuple[T, ExtractionMetadata]:
        """
        Extracts structured data matching schema_cls with self-correction retry loop.
        """
        self.validate_input(raw_text)

        start_time = time.perf_counter()

        # If no client is configured, check mock fallback
        if not self._groq_client and not self._openai_client:
            if self.settings.ALLOW_MOCK_FALLBACK:
                logger.info("Using mock fallback extractor for %s", doc_type_name)
                mock_data = self._generate_mock_data(raw_text, schema_cls)
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                metadata = ExtractionMetadata(
                    model_used="synthetic-mock-extractor",
                    processing_time_ms=round(elapsed_ms, 2),
                    retry_count=0,
                    is_mock=True,
                    document_type=doc_type_name
                )
                return mock_data, metadata
            else:
                raise LLMServiceException(
                    "No LLM API key configured and ALLOW_MOCK_FALLBACK is disabled. Please provide GROQ_API_KEY in .env."
                )

        schema_json = json.dumps(schema_cls.model_json_schema(), indent=2)

        system_instruction = (
            "You are a Principal Data Extraction AI. Your mission is to extract structured information "
            "from the user-provided unstructured text into clean, strictly valid JSON.\n\n"
            f"TARGET JSON SCHEMA:\n{schema_json}\n\n"
            "CRITICAL EXTRACTION RULES:\n"
            "1. Output ONLY a valid JSON object matching the exact schema definition above.\n"
            "2. Do NOT include markdown formatting, backticks (```json), or conversational explanations.\n"
            "3. Infer fields carefully from context. If an optional field is missing in the source text, set it to null or default empty list.\n"
            "4. Ensure all numeric amounts, dates, and nested models strictly comply with the schema."
        )

        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": f"Extract structured data from the following document:\n\n{raw_text}"}
        ]

        retries_used = 0
        max_retries = self.settings.MAX_RETRIES

        while retries_used <= max_retries:
            try:
                raw_response = self._call_llm(messages)
            except Exception as e:
                if self.settings.ALLOW_MOCK_FALLBACK:
                    logger.warning("LLM call failed (%s). Falling back to mock generator.", str(e))
                    mock_data = self._generate_mock_data(raw_text, schema_cls)
                    elapsed_ms = (time.perf_counter() - start_time) * 1000
                    metadata = ExtractionMetadata(
                        model_used="synthetic-mock-fallback",
                        processing_time_ms=round(elapsed_ms, 2),
                        retry_count=0,
                        is_mock=True,
                        document_type=doc_type_name
                    )
                    return mock_data, metadata

                if "timeout" in str(e).lower() or isinstance(e, httpx.TimeoutException):
                    raise LLMTimeoutException(f"LLM request timed out after {self.settings.REQUEST_TIMEOUT_SECONDS}s.")
                raise LLMServiceException(f"Failed to communicate with LLM provider: {str(e)}")

            # 1. Check JSON decodability
            cleaned_json_str = self._clean_raw_llm_output(raw_response)
            try:
                parsed_json = json.loads(cleaned_json_str)
            except json.JSONDecodeError as json_err:
                retries_used += 1
                if retries_used <= max_retries:
                    logger.warning(
                        "Attempt %d failed JSON decode (%s). Feeding error back to LLM.",
                        retries_used, str(json_err)
                    )
                    messages.append({"role": "assistant", "content": raw_response})
                    messages.append({
                        "role": "user",
                        "content": (
                            f"SELF-CORRECTION ERROR: The response was not valid JSON. Error: {str(json_err)}.\n"
                            "Please fix the syntax and return ONLY the valid JSON object adhering to the schema."
                        )
                    })
                    continue
                else:
                    raise SchemaValidationException(
                        message="LLM repeatedly failed to produce valid JSON syntax.",
                        validation_errors=[{"error": "JSONDecodeError", "details": str(json_err)}],
                        raw_response=raw_response
                    )

            # 2. Check Pydantic validation
            try:
                validated_model = schema_cls.model_validate(parsed_json)
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                model_name = self.settings.GROQ_MODEL if self._groq_client else self.settings.OPENAI_MODEL
                metadata = ExtractionMetadata(
                    model_used=model_name,
                    processing_time_ms=round(elapsed_ms, 2),
                    retry_count=retries_used,
                    is_mock=False,
                    document_type=doc_type_name
                )
                return validated_model, metadata

            except ValidationError as val_err:
                retries_used += 1
                simplified_errors = [
                    {"loc": err["loc"], "msg": err["msg"], "type": err["type"]}
                    for err in val_err.errors()
                ]

                if retries_used <= max_retries:
                    logger.warning(
                        "Attempt %d failed Pydantic validation with %d errors. Sending self-correction prompt.",
                        retries_used, len(simplified_errors)
                    )
                    messages.append({"role": "assistant", "content": raw_response})
                    messages.append({
                        "role": "user",
                        "content": (
                            f"SELF-CORRECTION FEEDBACK: Your previous JSON output failed validation with the following errors:\n"
                            f"{json.dumps(simplified_errors, indent=2)}\n\n"
                            "Please correct the data types, required fields, and structures, and return ONLY the corrected valid JSON."
                        )
                    })
                    continue
                else:
                    raise SchemaValidationException(
                        message=f"Extracted data failed validation against {schema_cls.__name__} after {max_retries} self-correction retries.",
                        validation_errors=simplified_errors,
                        raw_response=cleaned_json_str
                    )

        raise SchemaValidationException(
            message="Exceeded maximum self-correction retry attempts.",
            validation_errors=[]
        )

    def _call_llm(self, messages: list) -> str:
        """Invokes Groq or OpenAI API with JSON mode enabled."""
        if self._groq_client:
            completion = self._groq_client.chat.completions.create(
                model=self.settings.GROQ_MODEL,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.0,
            )
            return completion.choices[0].message.content or ""
        elif self._openai_client:
            completion = self._openai_client.chat.completions.create(
                model=self.settings.OPENAI_MODEL,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.0,
            )
            return completion.choices[0].message.content or ""
        raise LLMServiceException("No active LLM client available.")

    def _clean_raw_llm_output(self, raw_str: str) -> str:
        """Strips markdown fences or incidental wrapper text."""
        cleaned = raw_str.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        return cleaned.strip()

    def detect_document_type(self, raw_text: str) -> DocumentType:
        """Classifies document type based on content analysis."""
        lower_text = raw_text.lower()

        # Heuristic scoring
        resume_score = sum(1 for kw in ["education", "experience", "skills", "curriculum vitae", "resume", "bachelor", "master", "gpa"] if kw in lower_text)
        invoice_score = sum(1 for kw in ["invoice", "bill to", "tax id", "due date", "po number", "subtotal", "invoice number", "vat"] if kw in lower_text)
        receipt_score = sum(1 for kw in ["receipt", "cashier", "change due", "subtotal", "store", "terminal", "order #", "tip"] if kw in lower_text)

        if invoice_score > resume_score and invoice_score >= receipt_score:
            return DocumentType.INVOICE
        elif receipt_score > resume_score and receipt_score > invoice_score:
            return DocumentType.RECEIPT
        elif resume_score > 0:
            return DocumentType.RESUME
        else:
            # Fallback default
            return DocumentType.INVOICE

    def _generate_mock_data(self, raw_text: str, schema_cls: Type[T]) -> T:
        """
        Generates realistic synthetic parsed data extracted from raw_text when no API key is provided.
        Ensures users can test endpoints right out of the box.
        """
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        first_line = lines[0] if lines else "Sample Document"

        if schema_cls == ResumeSchema:
            return ResumeSchema(
                candidate=CandidateInfo(
                    full_name=first_line if len(first_line) < 40 else "John Doe",
                    email="john.doe@example.com",
                    phone="+1 (555) 234-5678",
                    location="San Francisco, CA, USA",
                    linkedin_url="https://linkedin.com/in/johndoe",
                    github_url="https://github.com/johndoe"
                ),
                summary="Accomplished professional with deep expertise in software engineering and cloud systems.",
                work_experience=[
                    WorkExperienceItem(
                        company_name="Antigravity AI Tech Corp",
                        job_title="Senior AI Engineer",
                        location="Remote / San Francisco",
                        start_date="2022-01",
                        end_date="Present",
                        is_current=True,
                        responsibilities=[
                            "Architected high-throughput microservices using FastAPI and LLM backends.",
                            "Developed structured data extraction pipelines with Pydantic v2."
                        ],
                        technologies_used=["Python", "FastAPI", "Groq", "Pydantic", "Docker"]
                    )
                ],
                education=[
                    EducationItem(
                        institution_name="University of California, Berkeley",
                        degree="Bachelor of Science",
                        field_of_study="Computer Science",
                        start_year=2016,
                        graduation_year=2020,
                        gpa=3.85
                    )
                ],
                skills=SkillSet(
                    technical_skills=["Python", "FastAPI", "AsyncIO", "PostgreSQL", "LLM APIs"],
                    soft_skills=["System Design", "Technical Leadership", "Problem Solving"],
                    tools_and_frameworks=["Docker", "Git", "Kubernetes", "Pytest"],
                    languages=["English", "Spanish"]
                )
            )

        elif schema_cls == InvoiceSchema:
            return InvoiceSchema(
                metadata=InvoiceMetadata(
                    invoice_number="INV-2026-9042",
                    issue_date="2026-10-01",
                    due_date="2026-10-31",
                    purchase_order_number="PO-77821"
                ),
                vendor=EntityDetails(
                    name="Antigravity AI Cloud Solutions Inc.",
                    tax_id="US-EIN-99-8877665",
                    address="100 Innovation Way, Suite 400, Mountain View, CA",
                    email="billing@antigravity.ai",
                    phone="+1 (800) 555-0199"
                ),
                customer=EntityDetails(
                    name="Nexus Enterprise Corp",
                    tax_id="US-EIN-11-2233445",
                    address="742 Evergreen Terrace, Springfield, OR",
                    email="accounts@nexuscorp.com",
                    phone="+1 (555) 012-3456"
                ),
                line_items=[
                    InvoiceLineItem(
                        description="Data Extraction Microservice Development & Setup",
                        item_code="DEV-SRV-01",
                        quantity=1.0,
                        unit_price=4500.0,
                        line_total=4500.0,
                        tax_rate_percent=10.0
                    ),
                    InvoiceLineItem(
                        description="Enterprise Support & Cloud SLA (1 Month)",
                        item_code="SUP-MTH-01",
                        quantity=1.0,
                        unit_price=500.0,
                        line_total=500.0,
                        tax_rate_percent=10.0
                    )
                ],
                financial_summary=FinancialSummary(
                    subtotal=5000.0,
                    tax_amount=500.0,
                    discount_amount=200.0,
                    shipping_amount=0.0,
                    grand_total=5300.0,
                    currency="USD"
                ),
                payment_details=None
            )

        elif schema_cls == ReceiptSchema:
            return ReceiptSchema(
                merchant_name=first_line if len(first_line) < 30 else "Blue Bottle Coffee",
                store_branch="Market Street #104",
                merchant_address="66 Mint Plaza, San Francisco, CA",
                receipt_number="REC-84920",
                transaction_date="2026-10-23",
                transaction_time="10:30:15",
                items=[
                    ReceiptLineItem(
                        item_name="Cold Brew Coffee (Large)",
                        quantity=2.0,
                        unit_price=6.50,
                        total_price=13.00
                    ),
                    ReceiptLineItem(
                        item_name="Almond Croissant",
                        quantity=1.0,
                        unit_price=5.50,
                        total_price=5.50
                    )
                ],
                subtotal=18.50,
                tax_amount=1.62,
                tip_amount=3.00,
                grand_total=23.12,
                currency="USD",
                payment_method="Visa Contactless"
            )

        raise ValueError(f"No mock generator configured for schema {schema_cls.__name__}")
