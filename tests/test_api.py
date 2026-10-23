"""Unit and integration test suite for Data Extraction microservice."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import DocumentType

client = TestClient(app)


def test_health_check():
    """Verify health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data


def test_empty_payload_validation():
    """Verify 400 Bad Request on empty or whitespace text."""
    response = client.post("/api/v1/extract/resume", json={"text": "   "})
    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert data["error_code"] == "EMPTY_INPUT_PAYLOAD"


def test_too_short_payload():
    """Verify 400 Bad Request on input shorter than 10 chars."""
    response = client.post("/api/v1/extract/invoice", json={"text": "short"})
    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "EMPTY_INPUT_PAYLOAD"


def test_oversized_payload():
    """Verify 413 error when text exceeds MAX_INPUT_CHARACTERS."""
    huge_text = "A" * 45000
    response = client.post("/api/v1/extract/receipt", json={"text": huge_text})
    assert response.status_code == 413
    data = response.json()
    assert data["error_code"] == "PAYLOAD_TOO_LARGE"


def test_resume_extraction():
    """Verify valid resume extraction and schema shape."""
    sample_resume = "Sarah Connor\nLead AI Architect\nEmail: sarah@skynet-defense.com\nExperience at Cyberdyne"
    response = client.post("/api/v1/extract/resume", json={"text": sample_resume})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "candidate" in data["data"]
    assert "work_experience" in data["data"]
    assert "metadata" in data


def test_invoice_extraction():
    """Verify valid invoice extraction and schema shape."""
    sample_invoice = "Invoice Number: INV-001\nVendor: Acme Corp\nCustomer: Globex\nLine 1: Widget $100\nTotal: $100"
    response = client.post("/api/v1/extract/invoice", json={"text": sample_invoice})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "metadata" in data["data"]
    assert "vendor" in data["data"]
    assert "financial_summary" in data["data"]


def test_receipt_extraction():
    """Verify valid receipt extraction and schema shape."""
    sample_receipt = "Store: Pete's Coffee\nDate: 2026-10-23\nLatte $5.00\nTotal: $5.00"
    response = client.post("/api/v1/extract/receipt", json={"text": sample_receipt})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "merchant_name" in data["data"]
    assert "grand_total" in data["data"]


def test_auto_classification():
    """Verify auto-classification of document types."""
    sample_receipt = "Receipt #8921\nCashier: 01\nCoffee $4.00\nSubtotal: $4.00\nTip: $1.00\nTotal: $5.00"
    response = client.post("/api/v1/extract/auto", json={"text": sample_receipt})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["detected_type"] == DocumentType.RECEIPT
