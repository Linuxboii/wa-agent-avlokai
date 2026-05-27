import hmac
import hashlib
import os
import uuid
import mimetypes
import httpx

from .config import settings


def verify_signature(body: bytes, signature_header: str | None) -> bool:
    """Validate X-Hub-Signature-256 header from Meta. Format: 'sha256=<hex>'."""
    if not settings.whatsapp_app_secret:
        return False  # never accept unsigned payloads
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(
        settings.whatsapp_app_secret.encode(), body, hashlib.sha256
    ).hexdigest()
    received = signature_header.split("=", 1)[1]
    return hmac.compare_digest(expected, received)


def verify_webhook(mode: str | None, token: str | None, challenge: str | None) -> str | None:
    """GET webhook verification handshake. Returns challenge if valid."""
    if mode == "subscribe" and token == settings.whatsapp_verify_token:
        return challenge
    return None


def _headers() -> dict:
    return {"Authorization": f"Bearer {settings.whatsapp_token}",
            "Content-Type": "application/json"}


def _messages_url() -> str:
    return f"{settings.graph_url}/{settings.whatsapp_phone_number_id}/messages"


async def send_text(to: str, body: str) -> dict:
    payload = {"messaging_product": "whatsapp", "to": to,
               "type": "text", "text": {"body": body}}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(_messages_url(), headers=_headers(), json=payload)
        r.raise_for_status()
        return r.json()


async def _upload_media(file_path: str) -> str:
    """Upload a local file to WhatsApp, return media id."""
    mime = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    url = f"{settings.graph_url}/{settings.whatsapp_phone_number_id}/media"
    async with httpx.AsyncClient(timeout=60) as client:
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, mime)}
            data = {"messaging_product": "whatsapp", "type": mime}
            headers = {"Authorization": f"Bearer {settings.whatsapp_token}"}
            r = await client.post(url, headers=headers, files=files, data=data)
            r.raise_for_status()
            return r.json()["id"]


async def send_image(to: str, file_path: str, caption: str | None = None) -> dict:
    media_id = await _upload_media(file_path)
    payload = {"messaging_product": "whatsapp", "to": to, "type": "image",
               "image": {"id": media_id}}
    if caption:
        payload["image"]["caption"] = caption
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(_messages_url(), headers=_headers(), json=payload)
        r.raise_for_status()
        return r.json()


async def send_document(to: str, file_path: str, caption: str | None = None) -> dict:
    media_id = await _upload_media(file_path)
    payload = {"messaging_product": "whatsapp", "to": to, "type": "document",
               "document": {"id": media_id, "filename": os.path.basename(file_path)}}
    if caption:
        payload["document"]["caption"] = caption
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(_messages_url(), headers=_headers(), json=payload)
        r.raise_for_status()
        return r.json()


async def list_templates() -> list[dict]:
    """Fetch approved message templates for the business account."""
    url = f"{settings.graph_url}/{settings.whatsapp_business_id}/message_templates"
    params = {"limit": 200, "fields": "name,status,language,category,components"}
    out: list[dict] = []
    async with httpx.AsyncClient(timeout=30) as client:
        while url:
            r = await client.get(url, headers=_headers(), params=params)
            r.raise_for_status()
            data = r.json()
            for t in data.get("data", []):
                if t.get("status") == "APPROVED":
                    out.append({"name": t["name"], "language": t["language"],
                                "category": t.get("category"),
                                "components": t.get("components", [])})
            url = data.get("paging", {}).get("next")
            params = None  # next URL already carries query params
    return out


async def send_template(to: str, name: str, language: str,
                        body_params: list[str] | None = None) -> dict:
    template: dict = {"name": name, "language": {"code": language}}
    if body_params:
        template["components"] = [{
            "type": "body",
            "parameters": [{"type": "text", "text": p} for p in body_params],
        }]
    payload = {"messaging_product": "whatsapp", "to": to,
               "type": "template", "template": template}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(_messages_url(), headers=_headers(), json=payload)
        r.raise_for_status()
        return r.json()


async def download_media(media_id: str) -> str:
    """Download inbound media by id. Returns local file path under MEDIA_DIR."""
    os.makedirs(settings.media_dir, exist_ok=True)
    async with httpx.AsyncClient(timeout=60) as client:
        meta = await client.get(f"{settings.graph_url}/{media_id}",
                                headers={"Authorization": f"Bearer {settings.whatsapp_token}"})
        meta.raise_for_status()
        info = meta.json()
        media_url = info["url"]
        mime = info.get("mime_type", "application/octet-stream")
        ext = mimetypes.guess_extension(mime.split(";")[0]) or ".bin"
        fname = f"{uuid.uuid4().hex}{ext}"
        path = os.path.join(settings.media_dir, fname)
        binr = await client.get(media_url,
                                headers={"Authorization": f"Bearer {settings.whatsapp_token}"})
        binr.raise_for_status()
        with open(path, "wb") as f:
            f.write(binr.content)
        return path
