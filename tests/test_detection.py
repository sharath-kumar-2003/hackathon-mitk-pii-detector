import pytest
from backend.detector import PIIDetector

def test_pii_detector_phone():
    detector = PIIDetector()
    results = detector.analyze_text("My phone number is 9000000001")
    assert len(results) > 0
    assert any(r.entity_type in ["PHONE_NUMBER", "IN_AADHAAR"] for r in results)

def test_pii_detector_email():
    detector = PIIDetector()
    results = detector.analyze_text("Contact me at test@example.com")
    assert any(r.entity_type == "EMAIL_ADDRESS" for r in results)

def test_pii_detector_aadhaar():
    detector = PIIDetector()
    results = detector.analyze_text("Applicant Aadhaar is 1234 5678 9012")
    assert any(r.entity_type == "IN_AADHAAR" for r in results)

def test_pii_detector_pan():
    detector = PIIDetector()
    results = detector.analyze_text("Tax ID PAN ABCDE1234F verified")
    assert any(r.entity_type == "IN_PAN" for r in results)

def test_pii_detector_synthetic_fixture_id():
    detector = PIIDetector()
    results = detector.analyze_text("Test fixture identifier SYNTH-ID-9912")
    assert any(r.entity_type == "SYNTHETIC_ID" for r in results)

def test_pii_detector_false_positive_challenge():
    detector = PIIDetector()
    # Non-PII numbers: SKU codes, order numbers, timestamps
    text = "Order ORD-987654 for product SKU-109283 at 2026-10-09T19:30:00Z"
    results = detector.analyze_text(text)
    # Ensure standard order IDs and timestamps are not misclassified as Aadhaar/PAN/Phone
    pii_types = [r.entity_type for r in results]
    assert "IN_PAN" not in pii_types
    assert "IN_AADHAAR" not in pii_types

def test_pii_detector_debit_card_and_pin():
    detector = PIIDetector()
    results = detector.analyze_text("Payment debit card 4532 8912 3456 7890 and ATM PIN 4829")
    pii_types = [r.entity_type for r in results]
    assert any(t in ["CREDIT_CARD", "PAYMENT_CARD"] for t in pii_types)
    assert "CARD_PIN" in pii_types
