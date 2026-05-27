import time
from app import media_urls


def test_sign_and_verify_roundtrip():
    url = media_urls.signed_url("/api/media/abc.jpg")
    assert url.startswith("/api/media/abc.jpg?exp=")
    q = dict(p.split("=", 1) for p in url.split("?", 1)[1].split("&"))
    assert media_urls.verify("abc.jpg", q["exp"], q["sig"]) is True


def test_verify_rejects_bad_sig():
    assert media_urls.verify("abc.jpg", str(int(time.time()) + 60), "deadbeef") is False


def test_verify_rejects_expired():
    exp = str(int(time.time()) - 1)
    sig = media_urls._sign("abc.jpg", int(exp))
    assert media_urls.verify("abc.jpg", exp, sig) is False


def test_verify_rejects_missing():
    assert media_urls.verify("abc.jpg", None, None) is False


def test_non_media_url_passthrough():
    assert media_urls.signed_url(None) is None
    assert media_urls.signed_url("/other/x") == "/other/x"
