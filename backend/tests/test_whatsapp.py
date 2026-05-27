import hmac
import hashlib
from app.config import settings
from app import whatsapp


def test_verify_signature_valid():
    settings.whatsapp_app_secret = "secret123"
    body = b'{"hello":"world"}'
    sig = "sha256=" + hmac.new(b"secret123", body, hashlib.sha256).hexdigest()
    assert whatsapp.verify_signature(body, sig) is True


def test_verify_signature_invalid():
    settings.whatsapp_app_secret = "secret123"
    assert whatsapp.verify_signature(b"body", "sha256=deadbeef") is False


def test_verify_signature_missing_header():
    settings.whatsapp_app_secret = "secret123"
    assert whatsapp.verify_signature(b"body", None) is False


def test_verify_webhook_handshake():
    settings.whatsapp_verify_token = "tok"
    assert whatsapp.verify_webhook("subscribe", "tok", "CH") == "CH"
    assert whatsapp.verify_webhook("subscribe", "wrong", "CH") is None
