import logging
from contextlib import asynccontextmanager
from typing import Dict, Optional
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.config import get_settings
from app.exceptions import register_exception_handlers
from app.extractor import LLMExtractor
from app.schemas import (
    AutoExtractionResponse,
    DocumentType,
    ErrorResponse,
    ExtractionRequest,
    ExtractionResponse,
    InvoiceSchema,
    ReceiptSchema,
    ResumeSchema,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s"
)
logger = logging.getLogger("main")

# Global extractor instance with lazy getter
_extractor: Optional[LLMExtractor] = None


def get_extractor() -> LLMExtractor:
    """Returns singleton extractor instance, initializing on first access."""
    global _extractor
    if _extractor is None:
        _extractor = LLMExtractor(get_settings())
    return _extractor


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initializes resources on startup and cleans up on shutdown."""
    settings = get_settings()
    logger.info("Starting %s v%s...", settings.APP_NAME, settings.APP_VERSION)
    logger.info("Configured Provider: %s | Model: %s", settings.LLM_PROVIDER, settings.GROQ_MODEL)
    logger.info("Mock Fallback Enabled: %s", settings.ALLOW_MOCK_FALLBACK)
    get_extractor()
    yield
    logger.info("Shutting down %s...", settings.APP_NAME)


app = FastAPI(
    title="Antigravity Data Extraction Microservice",
    description="""
## Production-Ready Generative AI Data Extraction Microservice

Converts raw, unstructured business documents (resumes, invoices, receipts) into clean, fully-validated structured JSON.

### Key Features:
* **Pydantic v2 Schema Enforcement**: Nested models for Work Experience, Education, Skills, Invoice Line Items, and Receipt breakdown.
* **Automated Self-Correction Loop**: If validation fails or JSON is malformed, catches exceptions and feeds validation errors back to the LLM for self-correction.
* **Resilient Edge-Case Handling**: Guards against blank payloads, token/size limits, and network timeouts.
* **Flexible LLM Backend**: Configured for Groq API (free-tier `llama-3.3-70b-versatile`) and OpenAI-compatible providers.
* **Auto-Classification**: Single endpoint `/api/v1/extract/auto` that detects document type automatically.
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    responses={
        400: {"model": ErrorResponse, "description": "Empty or invalid input"},
        413: {"model": ErrorResponse, "description": "Input payload too large"},
        422: {"model": ErrorResponse, "description": "Schema validation failure"},
        502: {"model": ErrorResponse, "description": "Upstream LLM error"},
        504: {"model": ErrorResponse, "description": "LLM request timeout"},
    }
)

# Enable CORS for frontend applications
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register uniform exception handlers
register_exception_handlers(app)


# -----------------------------------------------------------------------------
# Root & Health Check Endpoints
# -----------------------------------------------------------------------------
@app.get(
    "/",
    include_in_schema=False,
    summary="Root redirect to Swagger UI"
)
async def root():
    """Redirects base URL to interactive Swagger docs."""
    return RedirectResponse(url="/docs")


@app.get(
    "/health",
    tags=["System"],
    summary="Health check & system configuration",
    response_description="Current service health, model, and active provider info"
)
async def health_check() -> Dict[str, object]:
    """Returns microservice health status, active model, and configuration."""
    settings = get_settings()
    has_groq_key = bool(settings.GROQ_API_KEY and settings.GROQ_API_KEY.strip())
    has_openai_key = bool(settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.strip())

    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "provider": settings.LLM_PROVIDER,
        "model": settings.GROQ_MODEL if settings.LLM_PROVIDER == "groq" else settings.OPENAI_MODEL,
        "live_llm_ready": has_groq_key or has_openai_key,
        "mock_fallback_active": not (has_groq_key or has_openai_key) and settings.ALLOW_MOCK_FALLBACK,
    }


# -----------------------------------------------------------------------------
# Specialized Document Extraction Endpoints
# -----------------------------------------------------------------------------
@app.post(
    "/api/v1/extract/resume",
    response_model=ExtractionResponse[ResumeSchema],
    tags=["Extraction"],
    summary="Extract structured resume data",
    description="Ingests unstructured resume text and extracts candidate info, work experience, education, skills, and certifications."
)
async def extract_resume(payload: ExtractionRequest) -> ExtractionResponse[ResumeSchema]:
    """Extracts candidate profile and career history into a verified ResumeSchema."""
    data, metadata = get_extractor().extract_structured(
        raw_text=payload.text,
        schema_cls=ResumeSchema,
        doc_type_name="resume"
    )
    return ExtractionResponse(success=True, data=data, metadata=metadata)


@app.post(
    "/api/v1/extract/invoice",
    response_model=ExtractionResponse[InvoiceSchema],
    tags=["Extraction"],
    summary="Extract structured invoice data",
    description="Ingests unstructured invoice text and extracts metadata, vendor/customer entities, line items, and financial summary."
)
async def extract_invoice(payload: ExtractionRequest) -> ExtractionResponse[InvoiceSchema]:
    """Extracts billing details, line items, and financial totals into an InvoiceSchema."""
    data, metadata = get_extractor().extract_structured(
        raw_text=payload.text,
        schema_cls=InvoiceSchema,
        doc_type_name="invoice"
    )
    return ExtractionResponse(success=True, data=data, metadata=metadata)


@app.post(
    "/api/v1/extract/receipt",
    response_model=ExtractionResponse[ReceiptSchema],
    tags=["Extraction"],
    summary="Extract structured receipt data",
    description="Ingests unstructured sales receipt or POS slip text and extracts merchant info, purchased items, taxes, tips, and totals."
)
async def extract_receipt(payload: ExtractionRequest) -> ExtractionResponse[ReceiptSchema]:
    """Extracts transaction items, taxes, tips, and payment method into a ReceiptSchema."""
    data, metadata = get_extractor().extract_structured(
        raw_text=payload.text,
        schema_cls=ReceiptSchema,
        doc_type_name="receipt"
    )
    return ExtractionResponse(success=True, data=data, metadata=metadata)


@app.post(
    "/api/v1/extract/auto",
    response_model=AutoExtractionResponse,
    tags=["Extraction"],
    summary="Auto-detect document type and extract structured JSON",
    description="Automatically classifies whether text is a Resume, Invoice, or Receipt, then extracts the corresponding validated schema."
)
async def extract_auto(payload: ExtractionRequest) -> AutoExtractionResponse:
    """Classifies document type automatically and routes to the appropriate schema."""
    detected_type = payload.document_type
    if not detected_type or detected_type == DocumentType.AUTO:
        detected_type = get_extractor().detect_document_type(payload.text)

    schema_mapping = {
        DocumentType.RESUME: ResumeSchema,
        DocumentType.INVOICE: InvoiceSchema,
        DocumentType.RECEIPT: ReceiptSchema,
    }

    target_schema = schema_mapping.get(detected_type, InvoiceSchema)
    data, metadata = get_extractor().extract_structured(
        raw_text=payload.text,
        schema_cls=target_schema,
        doc_type_name=detected_type.value
    )

    return AutoExtractionResponse(
        success=True,
        detected_type=detected_type,
        data=data,
        metadata=metadata
    )


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
