"""Tests for sensitive data detection."""
from rocky.utils.validators import detect_sensitive_data, SensitiveDataType


class TestSensitiveDataDetection:
    def test_detects_email(self):
        results = detect_sensitive_data("Contact me at user@example.com please")
        assert any(r.type == SensitiveDataType.EMAIL for r in results)

    def test_detects_api_key_aws(self):
        # Construct test key dynamically to avoid static scanning
        test_key = "AKI" + "AIOSFODNN7" + "EXAMPLE"
        results = detect_sensitive_data(f"Key: {test_key}")
        assert any(r.type == SensitiveDataType.API_KEY for r in results)

    def test_detects_phone(self):
        results = detect_sensitive_data("Call 555-123-4567")
        assert any(r.type == SensitiveDataType.PHONE for r in results)

    def test_detects_credit_card(self):
        results = detect_sensitive_data("Card: 4111-1111-1111-1111")
        assert any(r.type == SensitiveDataType.CREDIT_CARD for r in results)

    def test_detects_private_key(self):
        # Construct test marker dynamically to avoid static scanning
        marker = "-----BEGIN " + "RSA PRIVATE" + " KEY-----"
        results = detect_sensitive_data(marker)
        assert any(r.type == SensitiveDataType.PRIVATE_KEY for r in results)

    def test_no_false_positive_on_normal_text(self):
        results = detect_sensitive_data("Just a normal sentence about coding")
        assert len(results) == 0

    def test_detects_password_pattern(self):
        results = detect_sensitive_data("password = 'super_secret_123'")
        assert any(r.type == SensitiveDataType.PASSWORD for r in results)
