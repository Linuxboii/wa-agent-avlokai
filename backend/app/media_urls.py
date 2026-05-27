"""Short-lived HMAC-signed media URLs.

Browser <img>/<audio> tags cannot send an Authorization header, so media
access is authorized by a signature embedded in the URL instead of the JWT.
Signatures expire, so leaking a URL only grants brief access.
"""
import hmac
import hashlib
import time

from .config import settings

_TTL_SECONDS = 3600
_PREFIX = "/api/media/"


def _sign(filename: str, exp: int) -> str:
    msg = f"{filename}.{exp}".encode()
    return hmac.new(settings.jwt_secret.encode(), msg, hashlib.sha256).hexdigest()


def signed_url(stored_url: str | None) -> str | None:
    """Turn a stored '/api/media/<file>' path into a signed, expiring URL."""
    if not stored_url or not stored_url.startswith(_PREFIX):
        return stored_url
    filename = stored_url[len(_PREFIX):]
    exp = int(time.time()) + _TTL_SECONDS
    return f"{_PREFIX}{filename}?exp={exp}&sig={_sign(filename, exp)}"


def verify(filename: str, exp: str | None, sig: str | None) -> bool:
    if not exp or not sig:
        return False
    try:
        exp_int = int(exp)
    except ValueError:
        return False
    if exp_int < int(time.time()):
        return False
    return hmac.compare_digest(_sign(filename, exp_int), sig)


def with_signed_media(msg: dict | None) -> dict | None:
    """Return a copy of a message dict with media_url replaced by a signed URL."""
    if not msg:
        return msg
    if msg.get("media_url"):
        msg = {**msg, "media_url": signed_url(msg["media_url"])}
    return msg
