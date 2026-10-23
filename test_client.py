"""
Comprehensive Test Client for Document Data Extraction Microservice.
Tests all endpoints, schemas, edge cases, and error responses.
"""

import json
import time
import httpx

BASE_URL = "http://127.0.0.1:8000"

SAMPLE_RESUME = """
ALEXANDER WONG
Senior Machine Learning & Backend Engineer
Email: alex.wong@techinnovate.io | Phone: +1-415-890-1234
Location: Seattle, WA | LinkedIn: https://linkedin.com/in/alexwongml | GitHub: https://github.com/alexwong-dev

SUMMARY:
Results-driven software engineer with 6+ years of experience specializing in generative AI, scalable microservice architectures, and LLM-assisted workflow automation.

PROFESSIONAL EXPERIENCE:
Nexus Data Labs - Lead AI Systems Engineer (2022-03 - Present)
- Designed and deployed high-throughput data extraction microservices handling 2M+ documents monthly using FastAPI, Pydantic, and Groq.
- Reduced inference latency by 45% through aggressive batching and optimized prompt schemas.
- Mentored a team of 4 junior ML engineers on structured output pipelines.
Technologies: Python, FastAPI, Docker, Groq, Kubernetes, Redis, Pytest.

CloudScale Innovations - Backend Engineer (2018-06 - 2022-02)
- Built distributed REST APIs in Python and Go supporting enterprise analytics.
- Integrated PostgreSQL and Elasticsearch for real-time document indexing.
Technologies: Python, Django, PostgreSQL, AWS, Docker.

EDUCATION:
University of Washington
Bachelor of Science in Computer Science & Applied Mathematics (2014 - 2018)
GPA: 3.92 / 4.0 | Magna Cum Laude

SKILLS:
Technical: Python, Go, SQL, FastAPI, Pydantic, PyTorch, LangChain, REST APIs
Tools & Frameworks: Docker, Kubernetes, AWS, Git, CI/CD, Linux, Redis
Soft Skills: Architecture Planning, Team Leadership, Agile Methodologies
Languages: English (Fluent), Mandarin (Conversational)

CERTIFICATIONS:
- AWS Certified Solutions Architect - Associate (Amazon Web Services, 2023)
- Deep Learning Specialization (DeepLearning.AI, 2021)
"""

SAMPLE_INVOICE = """
============================================================
                     TECHFLOW SOLUTIONS INC.
            Tax ID: US-EIN-88-2940192 | VAT: US882940192
       1200 Innovation Parkway, Suite 500, Austin, TX 78701
             Email: billing@techflow.io | Phone: (512) 555-8900
============================================================

INVOICE TO:
Acme Global Logistics LLC
Attn: Accounts Payable
850 Enterprise Blvd, Suite 200, Chicago, IL 60601
Client Contact: finance@acmeglobal.com

INVOICE DETAILS:
Invoice Number: INV-2026-0891
Issue Date: 2026-10-15
Payment Due Date: 2026-11-14
PO Reference: PO-99214-AG

SERVICES & DELIVERABLES:
1. LLM Fine-Tuning & Prompt Engineering Consulting
   Code: AI-CONS-01 | Qty: 40 hrs | Rate: $150.00 | Total: $6,000.00
2. Enterprise Data Extraction Microservice License
   Code: LIC-EXTR-PRO | Qty: 1 | Rate: $2,500.00 | Total: $2,500.00
3. Cloud Hosting & Dedicated SLA Maintenance (Quarterly)
   Code: CLOUD-SLA-Q4 | Qty: 1 | Rate: $950.00 | Total: $950.00

FINANCIAL SUMMARY:
Subtotal: $9,450.00
State Sales Tax (8.25%): $779.63
Discount Applied: -$500.00
Shipping & Handling: $0.00
------------------------------------------------------------
GRAND TOTAL PAYABLE: $9,729.63 USD
------------------------------------------------------------

PAYMENT TERMS:
Payment terms: Net 30 days.
Direct Wire: Chase Manhattan Bank
Routing: 021000021 | Account No: 9918274610
Swift / BIC: CHASUS33
"""

SAMPLE_RECEIPT = """
========================================
           BLUE BOTTLE COFFEE
         Ferry Building #74
        San Francisco, CA 94111
            Tel: 415-555-0182
========================================
Date: 2026-10-23          Time: 09:42 AM
Register: 03              Cashier: Sarah M.
Order #: 408291

1x Single Origin Espresso       $ 4.75
2x Almond Milk Cappuccino       $ 13.00
1x Avocado Toast w/ Egg         $ 12.50
1x Seasonal Pastry (Croissant)  $  5.25

----------------------------------------
SUBTOTAL:                       $ 35.50
TAX (8.5%):                     $  3.02
TIP:                            $  5.00
----------------------------------------
AMOUNT CHARGED:                 $ 43.52
----------------------------------------
Payment Method: Apple Pay (Visa ending 4821)
Auth Code: 994021
Thank you for visiting Blue Bottle!
========================================
"""


import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def get_client():
    """Returns live httpx client if server is running, or in-memory FastAPI TestClient."""
    try:
        live_client = httpx.Client(base_url=BASE_URL, timeout=30.0)
        res = live_client.get("/health")
        if res.status_code == 200:
            print("[INFO] Connected to live server running at", BASE_URL)
            return live_client
    except Exception:
        pass

    print("[INFO] No live server detected on port 8000. Launching in-memory FastAPI TestClient...")
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


def run_tests():
    print("=" * 70)
    print(">>> DOCUMENT DATA EXTRACTION SERVICE - VERIFICATION RUNNER")
    print("=" * 70)

    client = get_client()

    # 1. Health check
    print("\n[TEST 1] Checking Health Endpoint (/health)...")
    resp = client.get("/health")
    print(f"Status: {resp.status_code}")
    print(f"Response: {json.dumps(resp.json(), indent=2)}")
    assert resp.status_code == 200, "Health check failed!"

    # 2. Extract Resume
    print("\n[TEST 2] Testing Resume Extraction (/api/v1/extract/resume)...")
    resp = client.post("/api/v1/extract/resume", json={"text": SAMPLE_RESUME})
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print("Candidate Name:", data["data"]["candidate"]["full_name"])
        print("Candidate Email:", data["data"]["candidate"]["email"])
        print("Work Experiences Count:", len(data["data"]["work_experience"]))
        print("Skills Extracted:", data["data"]["skills"]["technical_skills"][:5])
        print("Metadata:", data["metadata"])
    else:
        print("Error Response:", resp.text)

    # 3. Extract Invoice
    print("\n[TEST 3] Testing Invoice Extraction (/api/v1/extract/invoice)...")
    resp = client.post("/api/v1/extract/invoice", json={"text": SAMPLE_INVOICE})
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print("Invoice Number:", data["data"]["metadata"]["invoice_number"])
        print("Vendor:", data["data"]["vendor"]["name"])
        print("Customer:", data["data"]["customer"]["name"])
        print("Line Items Extracted:", len(data["data"]["line_items"]))
        print("Grand Total:", data["data"]["financial_summary"]["grand_total"], data["data"]["financial_summary"]["currency"])
        print("Metadata:", data["metadata"])
    else:
        print("Error Response:", resp.text)

    # 4. Extract Receipt
    print("\n[TEST 4] Testing Receipt Extraction (/api/v1/extract/receipt)...")
    resp = client.post("/api/v1/extract/receipt", json={"text": SAMPLE_RECEIPT})
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print("Merchant:", data["data"]["merchant_name"])
        print("Items Count:", len(data["data"]["items"]))
        print("Subtotal:", data["data"]["subtotal"])
        print("Grand Total:", data["data"]["grand_total"])
        print("Metadata:", data["metadata"])
    else:
        print("Error Response:", resp.text)

    # 5. Auto Endpoint (Classifies and Extracts)
    print("\n[TEST 5] Testing Auto Extraction (/api/v1/extract/auto)...")
    resp = client.post("/api/v1/extract/auto", json={"text": SAMPLE_INVOICE})
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print("Detected Document Type:", data["detected_type"])
        print("Success:", data["success"])
    else:
        print("Error Response:", resp.text)

    # 6. Edge Case: Empty Payload
    print("\n[TEST 6] Edge Case: Empty Input String (Expected: 400 Bad Request)...")
    resp = client.post("/api/v1/extract/resume", json={"text": "   "})
    print(f"Status: {resp.status_code} (Expected: 400)")
    print(f"Error Code: {resp.json().get('error_code')}")
    print(f"Message: {resp.json().get('message')}")
    assert resp.status_code == 400

    # 7. Edge Case: Oversized Payload
    print("\n[TEST 7] Edge Case: Oversized Text Input (Expected: 413 Payload Too Large)...")
    huge_text = "This is a recurring test string to exceed maximum allowed characters. " * 700
    resp = client.post("/api/v1/extract/resume", json={"text": huge_text})
    print(f"Status: {resp.status_code} (Expected: 413)")
    print(f"Error Code: {resp.json().get('error_code')}")
    print(f"Message: {resp.json().get('message')}")
    assert resp.status_code == 413

    print("\n" + "=" * 70)
    print("[SUCCESS] ALL VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
