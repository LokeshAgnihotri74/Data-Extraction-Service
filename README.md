# 🚀 Antigravity Data Extraction Microservice

A production-ready Gen AI Data Extraction microservice built with **FastAPI**, **Pydantic v2**, and **Groq LLM API** (or OpenAI-compatible providers). It ingests raw, unstructured business documents (resumes, invoices, receipts) and extracts clean, fully-validated structured JSON.

---

## 📌 Features & Architecture

- **Pydantic v2 Schema Enforcement**: Rigorous nested schemas for:
  - **Resume**: Candidate profile, work experience, education, skills, projects, certifications.
  - **Invoice**: Metadata, vendor & customer entity info, line items with math checks, taxes, discounts, grand totals.
  - **Receipt**: Merchant details, line items, subtotal, tax, tip, final charged amount, payment method.
- **Automated Self-Correction Loop**: If the LLM generates invalid JSON or misses schema constraints, the service catches validation exceptions and automatically feeds the error back to the LLM with corrective instructions (up to `MAX_RETRIES` attempts).
- **Edge-Case Protections**:
  - Rejects empty or whitespace-only inputs with `400 Bad Request`.
  - Rejects oversized payloads exceeding token/character limits with `413 Payload Too Large`.
  - Catches LLM timeouts with `504 Gateway Timeout`.
- **Zero-Config Instant Testing (Mock Fallback)**: If no API key is provided initially, the service activates synthetic mock extraction, allowing you to test endpoints and Swagger UI out of the box immediately.
- **Interactive Swagger UI**: Full OpenAPI 3.1 documentation and interactive testing sandbox at `/docs`.

---

## 📁 Project Directory Structure

```text
C:\Users\lokes\.gemini\antigravity\scratch\data-extraction-service\
├── app/
│   ├── __init__.py
│   ├── config.py              # Pydantic Settings & environment loader
│   ├── schemas.py             # Pydantic v2 domain schemas & request/response wrappers
│   ├── extractor.py           # Core extraction engine with self-correction & retry loop
│   ├── exceptions.py          # Custom domain exceptions & global HTTP handlers
│   └── main.py                # FastAPI app, endpoints, lifespan, and CORS middleware
├── test_client.py             # Automated end-to-end test script
├── requirements.txt           # Python package dependencies
├── .env                       # Active local environment variables
├── .env.example               # Configuration template
├── .gitignore                 # Git ignore file
└── README.md                  # Complete documentation and usage guide
```

---

## ⚡ Quickstart Guide (Local Setup)

### 1. Open Terminal and Navigate to the Directory
In PowerShell or Command Prompt:
```powershell
cd C:\Users\lokes\.gemini\antigravity\scratch\data-extraction-service
```

### 2. Create and Activate a Virtual Environment
```powershell
# Create virtual environment
python -m venv .venv

# Activate on Windows PowerShell
.\.venv\Scripts\Activate.ps1

# (If using Command Prompt cmd.exe)
# .\.venv\Scripts\activate.bat
```

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Configure Environment Variables (`.env`)
A ready-to-use `.env` file is already created in the project folder. 

To use live Groq LLM inference, obtain a free API key from [Groq Console](https://console.groq.com/keys) and update `.env`:
```env
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_your_actual_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
ALLOW_MOCK_FALLBACK=True
PORT=8000
```
*(Note: If you leave `GROQ_API_KEY` blank, the microservice automatically uses its built-in realistic mock engine so you can test all endpoints immediately).*

### 5. Run the Microservice
```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
The server will start at:
- **API URL**: `http://127.0.0.1:8000`
- **Interactive Swagger Docs**: `http://127.0.0.1:8000/docs`
- **ReDoc Documentation**: `http://127.0.0.1:8000/redoc`

---

## 🧪 Testing the Microservice

### Method A: Automated Test Suite (`test_client.py`)
In a new terminal window (with the server running), simply run:
```powershell
python test_client.py
```
This script tests:
1. `/health` system check
2. `/api/v1/extract/resume` with sample resume text
3. `/api/v1/extract/invoice` with sample invoice text
4. `/api/v1/extract/receipt` with sample receipt text
5. `/api/v1/extract/auto` automatic document classification
6. Edge case: Empty input string (`400 Bad Request`)
7. Edge case: Oversized input payload (`413 Payload Too Large`)

---

### Method B: cURL Examples

#### 1. Health Check
```powershell
curl -X GET "http://127.0.0.1:8000/health"
```

#### 2. Extract Resume
```powershell
curl -X POST "http://127.0.0.1:8000/api/v1/extract/resume" `
  -H "Content-Type: application/json" `
  -d '{
    "text": "ALEXANDER WONG\nSenior ML Engineer\nEmail: alex@tech.io | Phone: +1-415-555-0199\nLocation: Seattle, WA\nExperience: Lead AI Engineer at Nexus Data Labs (2022-Present). Built FastAPI LLM microservices.\nEducation: University of Washington, B.S. in Computer Science (2018), GPA: 3.9.\nSkills: Python, FastAPI, Groq, Docker, Kubernetes."
  }'
```

#### 3. Extract Invoice
```powershell
curl -X POST "http://127.0.0.1:8000/api/v1/extract/invoice" `
  -H "Content-Type: application/json" `
  -d '{
    "text": "TECHFLOW SOLUTIONS INC.\nTax ID: US-882940192\nInvoice Number: INV-2026-0891\nDate: 2026-10-15 | Due Date: 2026-11-14\nBilled To: Acme Global Logistics LLC\n\n1. LLM Consulting: 40 hrs @ $150 = $6,000.00\n2. Microservice License: 1 unit @ $2,500 = $2,500.00\n\nSubtotal: $8,500.00\nTax (8%): $680.00\nGrand Total: $9,180.00 USD"
  }'
```

#### 4. Extract Receipt
```powershell
curl -X POST "http://127.0.0.1:8000/api/v1/extract/receipt" `
  -H "Content-Type: application/json" `
  -d '{
    "text": "BLUE BOTTLE COFFEE\nFerry Building #74, San Francisco\nDate: 2026-10-23 09:42 AM\n1x Espresso $4.75\n2x Almond Cappuccino $13.00\nSubtotal: $17.75\nTax: $1.51\nTip: $3.00\nTotal: $22.26\nPaid by Apple Pay Visa"
  }'
```

#### 5. Auto-Detect and Extract
```powershell
curl -X POST "http://127.0.0.1:8000/api/v1/extract/auto" `
  -H "Content-Type: application/json" `
  -d '{
    "text": "BLUE BOTTLE COFFEE\nDate: 2026-10-23\n1x Cold Brew $6.50\nTotal: $6.50"
  }'
```

#### 6. Test Error Handling (Empty Payload -> 400 Bad Request)
```powershell
curl -X POST "http://127.0.0.1:8000/api/v1/extract/resume" `
  -H "Content-Type: application/json" `
  -d '{"text": "   "}'
```

---

## 🛡️ Error Handling & Self-Correction Flow

```
[Raw Document Text]
        │
        ▼
[Input Validation Guard] ──(Empty or Oversized)──> [HTTP 400 / 413 Error]
        │
        ▼
[Groq LLM Inference (JSON Mode)]
        │
        ▼
[JSON Parsing & Pydantic Validation]
        │
        ├─► Valid ───► [HTTP 200 Return Validated Schema]
        │
        └─► Invalid / Validation Error
                │
                ├─► Retry Count < MAX_RETRIES?
                │       │
                │       └─► Yes: [Feedback Error Report to LLM] ──┐
                │                                                │
                │                (Loop back to Inference) ◄──────┘
                │
                └─► No: [HTTP 422 Unprocessable Entity with Structured Field Errors]
```

---

## 🚢 Production Deployment Recommendations

For deploying to production containers or Kubernetes:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```
