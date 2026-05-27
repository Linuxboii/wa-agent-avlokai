import os
import uuid
import mimetypes
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .db import get_session
from . import models, whatsapp
from .auth import get_current_agent
from .ws import manager
from .media_urls import verify as verify_media_sig, with_signed_media

router = APIRouter(prefix="/api", tags=["api"])


class SendTextIn(BaseModel):
    body: str


class PauseIn(BaseModel):
    paused: bool


class SettingsIn(BaseModel):
    system_prompt: str
    openai_model: str


class SendTemplateIn(BaseModel):
    phone: str
    template_name: str
    language: str
    body_params: list[str] | None = None


def _normalize_phone(raw: str) -> str:
    digits = "".join(ch for ch in raw if ch.isdigit())
    if not digits:
        raise HTTPException(400, "Invalid phone number")
    return digits


async def _wa_id(session: AsyncSession, conversation_id: int) -> str:
    convs = await models.list_conversations(session)
    for c in convs:
        if c["id"] == conversation_id:
            return c["wa_id"]
    raise HTTPException(404, "Conversation not found")


@router.get("/conversations")
async def conversations(_: str = Depends(get_current_agent),
                        session: AsyncSession = Depends(get_session)):
    return await models.list_conversations(session)


@router.get("/conversations/{conversation_id}/messages")
async def messages(conversation_id: int, _: str = Depends(get_current_agent),
                   session: AsyncSession = Depends(get_session)):
    rows = await models.get_messages(session, conversation_id)
    return [with_signed_media(m) for m in rows]


@router.post("/conversations/{conversation_id}/send")
async def send(conversation_id: int, data: SendTextIn,
               _: str = Depends(get_current_agent),
               session: AsyncSession = Depends(get_session)):
    wa_id = await _wa_id(session, conversation_id)
    sent = await whatsapp.send_text(wa_id, data.body)
    wamid = sent.get("messages", [{}])[0].get("id")
    out = await models.add_message(session, conversation_id, "out", "text",
                                   data.body, wa_message_id=wamid)
    payload = {"conversation_id": conversation_id, **out}
    await manager.broadcast("message", payload)
    return payload


@router.post("/conversations/{conversation_id}/send-media")
async def send_media(conversation_id: int, file: UploadFile = File(...),
                     caption: str = Form(""),
                     _: str = Depends(get_current_agent),
                     session: AsyncSession = Depends(get_session)):
    wa_id = await _wa_id(session, conversation_id)
    os.makedirs(settings.media_dir, exist_ok=True)
    ext = os.path.splitext(file.filename or "")[1] or ".bin"
    fname = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(settings.media_dir, fname)
    with open(path, "wb") as f:
        f.write(await file.read())

    is_image = (file.content_type or "").startswith("image/")
    if is_image:
        await whatsapp.send_image(wa_id, path, caption or None)
        mtype = "image"
    else:
        await whatsapp.send_document(wa_id, path, caption or None)
        mtype = "document"

    out = await models.add_message(session, conversation_id, "out", mtype,
                                   caption or file.filename, "/api/media/" + fname)
    payload = with_signed_media({"conversation_id": conversation_id, **out})
    await manager.broadcast("message", payload)
    return payload


@router.post("/conversations/{conversation_id}/pause")
async def pause(conversation_id: int, data: PauseIn,
                _: str = Depends(get_current_agent),
                session: AsyncSession = Depends(get_session)):
    await models.set_pause(session, conversation_id, data.paused)
    await manager.broadcast("pause", {"conversation_id": conversation_id,
                                      "ai_paused": data.paused})
    return {"conversation_id": conversation_id, "ai_paused": data.paused}


@router.get("/templates")
async def templates(_: str = Depends(get_current_agent)):
    return await whatsapp.list_templates()


@router.post("/send-template")
async def send_template(data: SendTemplateIn, _: str = Depends(get_current_agent),
                        session: AsyncSession = Depends(get_session)):
    phone = _normalize_phone(data.phone)
    conv = await models.get_or_create_conversation(session, phone, None)
    if await models.has_template_message(session, conv["id"]):
        raise HTTPException(409, "A template has already been sent to this number")

    sent = await whatsapp.send_template(
        phone, data.template_name, data.language, data.body_params
    )
    wamid = sent.get("messages", [{}])[0].get("id")
    body = f"[template: {data.template_name}]"
    out = await models.add_message(session, conv["id"], "out", "text", body,
                                   wa_message_id=wamid)
    payload = {"conversation_id": conv["id"], **out}
    await manager.broadcast("message", payload)
    return {"conversation_id": conv["id"], **payload}


@router.get("/settings")
async def read_settings(_: str = Depends(get_current_agent),
                        session: AsyncSession = Depends(get_session)):
    return await models.get_settings(session)


@router.put("/settings")
async def write_settings(data: SettingsIn, _: str = Depends(get_current_agent),
                         session: AsyncSession = Depends(get_session)):
    return await models.update_settings(session, data.system_prompt, data.openai_model)


_INLINE_SAFE = {"image/jpeg", "image/png", "image/gif", "image/webp",
                "audio/mpeg", "audio/ogg", "audio/mp4", "audio/aac",
                "audio/amr", "application/pdf"}


@router.get("/media/{filename}")
async def media(filename: str, exp: str | None = None, sig: str | None = None):
    safe = os.path.basename(filename)
    if not verify_media_sig(safe, exp, sig):
        raise HTTPException(403, "Invalid or expired media link")
    base = os.path.realpath(settings.media_dir)
    path = os.path.realpath(os.path.join(base, safe))
    if not path.startswith(base + os.sep) or not os.path.isfile(path):
        raise HTTPException(404, "Not found")

    mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
    headers = {"X-Content-Type-Options": "nosniff",
               "Content-Security-Policy": "default-src 'none'; sandbox"}
    if mime in _INLINE_SAFE:
        return FileResponse(path, media_type=mime, headers=headers)
    # anything else (html/svg/scripts/unknown) -> forced download, never executed
    headers["Content-Disposition"] = f'attachment; filename="{safe}"'
    return FileResponse(path, media_type="application/octet-stream", headers=headers)
