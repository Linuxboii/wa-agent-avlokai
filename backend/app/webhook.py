import os
import logging
from fastapi import APIRouter, Request, Response, status

from .config import settings
from .db import SessionLocal
from . import models, whatsapp, openai_client
from .ws import manager
from .media_urls import with_signed_media

log = logging.getLogger("webhook")
router = APIRouter(tags=["webhook"])


@router.get("/webhook")
async def verify(request: Request):
    p = request.query_params
    challenge = whatsapp.verify_webhook(
        p.get("hub.mode"), p.get("hub.verify_token"), p.get("hub.challenge")
    )
    if challenge is not None:
        return Response(content=challenge, media_type="text/plain")
    return Response(status_code=status.HTTP_403_FORBIDDEN)


@router.post("/webhook")
async def receive(request: Request):
    body = await request.body()
    if not whatsapp.verify_signature(body, request.headers.get("X-Hub-Signature-256")):
        return Response(status_code=status.HTTP_403_FORBIDDEN)

    payload = await request.json()
    try:
        await _process(payload)
    except Exception:  # never 500 to Meta or it retries forever
        log.exception("webhook processing failed")
    return Response(status_code=status.HTTP_200_OK)


async def _process(payload: dict) -> None:
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            contacts = {c["wa_id"]: c.get("profile", {}).get("name")
                        for c in value.get("contacts", [])}
            for msg in value.get("messages", []):
                await _handle_message(msg, contacts)


async def _handle_message(msg: dict, contacts: dict) -> None:
    wa_id = msg["from"]
    name = contacts.get(wa_id)
    mtype = msg.get("type", "text")
    wa_message_id = msg.get("id")

    body = None
    media_url = None
    transcription = None
    stored_type = "text"

    if mtype == "text":
        body = msg["text"]["body"]
        stored_type = "text"
    elif mtype == "image":
        stored_type = "image"
        body = msg["image"].get("caption")
        media_url = await _save_media(msg["image"]["id"])
    elif mtype == "document":
        stored_type = "document"
        body = msg["document"].get("caption") or msg["document"].get("filename")
        media_url = await _save_media(msg["document"]["id"])
    elif mtype in ("audio", "voice"):
        stored_type = "audio"
        path = await whatsapp.download_media(msg[mtype]["id"])
        media_url = "/api/media/" + os.path.basename(path)
        try:
            transcription = await openai_client.transcribe(path)
        except Exception:
            log.exception("transcription failed")
    else:
        body = f"[unsupported message type: {mtype}]"

    async with SessionLocal() as session:
        conv = await models.get_or_create_conversation(session, wa_id, name)
        stored = await models.add_message(
            session, conv["id"], "in", stored_type, body, media_url,
            transcription, wa_message_id,
        )
        if stored is None:
            return  # duplicate delivery
        await manager.broadcast(
            "message", with_signed_media({"conversation_id": conv["id"], **stored}))

        if conv["ai_paused"]:
            return  # human handling this chat

        cfg = await models.get_settings(session)
        history = await models.get_history_for_ai(session, conv["id"])

    # AI reply (outside session to avoid holding the connection during network call)
    try:
        reply = await openai_client.generate_reply(
            cfg["system_prompt"], history, cfg["openai_model"]
        )
    except Exception:
        log.exception("openai reply failed")
        return
    if not reply:
        return

    sent = await whatsapp.send_text(wa_id, reply)
    out_wamid = sent.get("messages", [{}])[0].get("id")
    async with SessionLocal() as session:
        out = await models.add_message(
            session, conv["id"], "out", "text", reply, wa_message_id=out_wamid
        )
        if out:
            await manager.broadcast("message", {"conversation_id": conv["id"], **out})


async def _save_media(media_id: str) -> str:
    path = await whatsapp.download_media(media_id)
    return "/api/media/" + os.path.basename(path)
