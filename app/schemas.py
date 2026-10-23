from enum import Enum
from typing import Any, Generic, List, Optional, TypeVar, Union
from pydantic import BaseModel, ConfigDict, Field


# -------------------------------------------------------------------------
# Document Type Enums & Base Generic Type
# -------------------------------------------------------------------------
class DocumentType(str, Enum):
    RESUME = "resume"
    INVOICE = "invoice"
    RECEIPT = "receipt"
    AUTO = "auto"


T = TypeVar("T")


# -------------------------------------------------------------------------
# 1. Resume Schema
# -------------------------------------------------------------------------
class CandidateInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")
    full_name: str = Field(..., description="Full legal name of candidate", min_length=1)
    email: Optional[str] = Field(None, description="Contact email address")
    phone: Optional[str] = Field(None, description="Contact phone number")
    location: Optional[str] = Field(None, description="City, State/Province, Country")
    linkedin_url: Optional[str] = Field(None, description="LinkedIn profile URL")
    github_url: Optional[str] = Field(None, description="GitHub profile URL")
    portfolio_url: Optional[str] = Field(None, description="Personal portfolio or website URL")


class WorkExperienceItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    company_name: str = Field(..., description="Name of company or organization")
    job_title: str = Field(..., description="Role or position title")
    location: Optional[str] = Field(None, description="Office location or Remote")
    start_date: Optional[str] = Field(None, description="Start date (e.g. YYYY-MM or Month YYYY)")
    end_date: Optional[str] = Field(None, description="End date (e.g. YYYY-MM or Present)")
    is_current: bool = Field(False, description="True if currently working here")
    responsibilities: List[str] = Field(default_factory=list, description="Key duties and achievements")
    technologies_used: List[str] = Field(default_factory=list, description="Tools or tech stack applied")


class EducationItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    institution_name: str = Field(..., description="College, university, or institute name")
    degree: Optional[str] = Field(None, description="Degree earned (e.g. B.Tech, M.S., B.S.)")
    field_of_study: Optional[str] = Field(None, description="Major, department, or specialization")
    start_year: Optional[int] = Field(None, description="Year started")
    graduation_year: Optional[int] = Field(None, description="Year graduated or expected")
    gpa: Optional[float] = Field(None, description="GPA / score if available")
    honors: Optional[str] = Field(None, description="Honors or distinctions")


class SkillSet(BaseModel):
    model_config = ConfigDict(extra="ignore")
    technical_skills: List[str] = Field(default_factory=list, description="Programming languages, frameworks, cloud")
    soft_skills: List[str] = Field(default_factory=list, description="Communication, leadership, teamwork")
    tools_and_frameworks: List[str] = Field(default_factory=list, description="Specific libraries, software tools, IDEs")
    languages: List[str] = Field(default_factory=list, description="Spoken languages")


class CertificationItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str = Field(..., description="Certification name")
    issuing_organization: Optional[str] = Field(None, description="e.g. AWS, Google Cloud, Microsoft")
    issue_date: Optional[str] = Field(None, description="Issue date or year")
    credential_id: Optional[str] = Field(None, description="Credential ID or validation link")


class ProjectItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str = Field(..., description="Project title")
    description: Optional[str] = Field(None, description="Short project overview")
    technologies: List[str] = Field(default_factory=list, description="Tech stack used")
    link: Optional[str] = Field(None, description="Repository or live URL")


class ResumeSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    candidate: CandidateInfo = Field(..., description="Candidate contact and personal info")
    summary: Optional[str] = Field(None, description="Professional summary or objective statement")
    work_experience: List[WorkExperienceItem] = Field(default_factory=list, description="Employment history")
    education: List[EducationItem] = Field(default_factory=list, description="Academic background")
    skills: SkillSet = Field(default_factory=SkillSet, description="Categorized skillset")
    certifications: List[CertificationItem] = Field(default_factory=list, description="Professional certifications")
    projects: List[ProjectItem] = Field(default_factory=list, description="Notable independent or work projects")


# -------------------------------------------------------------------------
# 2. Invoice Schema
# -------------------------------------------------------------------------
class InvoiceMetadata(BaseModel):
    model_config = ConfigDict(extra="ignore")
    invoice_number: str = Field(..., description="Unique invoice identifier or code")
    issue_date: Optional[str] = Field(None, description="Date invoice was issued (YYYY-MM-DD)")
    due_date: Optional[str] = Field(None, description="Payment due date (YYYY-MM-DD)")
    purchase_order_number: Optional[str] = Field(None, description="PO Number if available")


class EntityDetails(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str = Field(..., description="Entity or company name")
    tax_id: Optional[str] = Field(None, description="Tax ID / VAT / GST / EIN")
    address: Optional[str] = Field(None, description="Billing or business address")
    email: Optional[str] = Field(None, description="Contact email")
    phone: Optional[str] = Field(None, description="Contact phone")


class InvoiceLineItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    description: str = Field(..., description="Item or service description")
    item_code: Optional[str] = Field(None, description="SKU or product code")
    quantity: float = Field(1.0, ge=0, description="Quantity of units")
    unit_price: float = Field(0.0, ge=0, description="Unit price before tax")
    line_total: float = Field(0.0, ge=0, description="Total amount for this line item")
    tax_rate_percent: Optional[float] = Field(None, ge=0, description="Tax percentage applied")


class FinancialSummary(BaseModel):
    model_config = ConfigDict(extra="ignore")
    subtotal: float = Field(..., ge=0, description="Subtotal before taxes and discounts")
    tax_amount: float = Field(0.0, ge=0, description="Total calculated tax")
    discount_amount: float = Field(0.0, ge=0, description="Total discount subtracted")
    shipping_amount: float = Field(0.0, ge=0, description="Shipping or freight fees")
    grand_total: float = Field(..., ge=0, description="Final payable amount")
    currency: str = Field("USD", description="Currency ISO code (e.g. USD, EUR, INR)")


class PaymentDetails(BaseModel):
    model_config = ConfigDict(extra="ignore")
    payment_terms: Optional[str] = Field(None, description="e.g. Net 30, Due upon receipt")
    payment_method: Optional[str] = Field(None, description="Bank transfer, Credit Card, Wire")
    bank_name: Optional[str] = Field(None, description="Bank name")
    account_number_or_iban: Optional[str] = Field(None, description="Account number or IBAN")
    routing_or_swift: Optional[str] = Field(None, description="SWIFT / BIC / Routing number")
    payment_status: Optional[str] = Field("unpaid", description="Status: paid, unpaid, pending")


class InvoiceSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    metadata: InvoiceMetadata = Field(..., description="Invoice identification details")
    vendor: EntityDetails = Field(..., description="Issuer/seller details")
    customer: EntityDetails = Field(..., description="Buyer/client details")
    line_items: List[InvoiceLineItem] = Field(..., min_length=1, description="List of invoiced goods/services")
    financial_summary: FinancialSummary = Field(..., description="Financial calculation breakdown")
    payment_details: Optional[PaymentDetails] = Field(None, description="Bank and payment instructions")


# -------------------------------------------------------------------------
# 3. Receipt Schema
# -------------------------------------------------------------------------
class ReceiptLineItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    item_name: str = Field(..., description="Purchased item name")
    quantity: float = Field(1.0, ge=0, description="Quantity purchased")
    unit_price: float = Field(0.0, ge=0, description="Unit price")
    total_price: float = Field(0.0, ge=0, description="Total price for this item")


class ReceiptSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    merchant_name: str = Field(..., description="Store or restaurant name")
    store_branch: Optional[str] = Field(None, description="Store branch ID or name")
    merchant_address: Optional[str] = Field(None, description="Physical location")
    receipt_number: Optional[str] = Field(None, description="Transaction receipt number")
    transaction_date: Optional[str] = Field(None, description="Date of purchase (YYYY-MM-DD)")
    transaction_time: Optional[str] = Field(None, description="Time of purchase (HH:MM:SS)")
    items: List[ReceiptLineItem] = Field(default_factory=list, description="Purchased items breakdown")
    subtotal: float = Field(..., ge=0, description="Subtotal amount")
    tax_amount: float = Field(0.0, ge=0, description="Sales tax")
    tip_amount: float = Field(0.0, ge=0, description="Tip amount")
    grand_total: float = Field(..., ge=0, description="Final charged amount")
    currency: str = Field("USD", description="Currency code (USD, EUR, INR, etc.)")
    payment_method: Optional[str] = Field("card", description="Payment type (cash, visa, mastercard, apple pay)")


# -------------------------------------------------------------------------
# Request & Response Wrappers
# -------------------------------------------------------------------------
class ExtractionRequest(BaseModel):
    text: str = Field(
        ...,
        description="Raw unstructured text from the document to extract data from",
        examples=["JOHN DOE\nSoftware Engineer\nEmail: john@example.com\nExperience: 5 years at Google..."]
    )
    document_type: Optional[DocumentType] = Field(
        None,
        description="Explicit document type hint (optional, will auto-detect if omitted in auto endpoint)"
    )


class ExtractionMetadata(BaseModel):
    model_used: str
    processing_time_ms: float
    retry_count: int
    is_mock: bool = False
    document_type: str


class ExtractionResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T
    metadata: ExtractionMetadata


class AutoExtractionResponse(BaseModel):
    success: bool = True
    detected_type: DocumentType
    data: Union[ResumeSchema, InvoiceSchema, ReceiptSchema]
    metadata: ExtractionMetadata


class ErrorResponse(BaseModel):
    success: bool = False
    error_code: str
    message: str
    details: Optional[Any] = None
