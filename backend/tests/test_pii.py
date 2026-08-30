from app.detectors.pii import detect_entities, redact


def test_phone_number_detected():
    entities = detect_entities("Rahul's phone number is 9876543210.")
    assert any(e["type"] == "PHONE_NUMBER" for e in entities)


def test_email_detected():
    entities = detect_entities("Contact priya.patel@corp.example.com for details.")
    assert any(e["type"] == "EMAIL" for e in entities)


def test_salary_detected():
    entities = detect_entities("Priya earns a salary of 18 lakh rupees per year.")
    assert any(e["type"] == "SALARY_INFO" for e in entities)


def test_medical_detected_with_person_context():
    entities = detect_entities("Amit is being treated for depression.")
    assert any(e["type"] == "MEDICAL_INFO" for e in entities)


def test_clean_sentence_not_detected():
    entities = detect_entities("Customers can request a refund within 30 days of purchase.")
    assert entities == []


def test_redaction_masks_entities():
    text = "Call 9876543210 or write to a@b.com."
    result = redact(text, detect_entities(text))
    assert "9876543210" not in result and "a@b.com" not in result
    assert "[REDACTED-PHONE_NUMBER]" in result
