"""Raw-SQL query helpers over the async session. Keeps DB access in one place."""
from typing import Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


# ---------- agents ----------
async def get_agent(session: AsyncSession, username: str) -> Optional[dict]:
    row = (await session.execute(
        text("SELECT id, username, password_hash FROM agents WHERE username = :u"),
        {"u": username},
    )).mappings().first()
    return dict(row) if row else None


async def create_agent(session: AsyncSession, username: str, password_hash: str) -> None:
    await session.execute(
        text("""INSERT INTO agents (username, password_hash) VALUES (:u, :p)
                ON CONFLICT (username) DO UPDATE SET password_hash = EXCLUDED.password_hash"""),
        {"u": username, "p": password_hash},
    )
    await session.commit()


# ---------- contacts / conversations ----------
def _phone_match_enabled(wa_id: str) -> bool:
    return len(wa_id) >= 10 and wa_id.isdigit()


async def _conversation_for_contact(session: AsyncSession, contact_id: int) -> Optional[dict]:
    row = (await session.execute(
        text("""SELECT id, contact_id, ai_paused, last_message_at
                FROM conversations WHERE contact_id = :cid"""),
        {"cid": contact_id},
    )).mappings().first()
    return dict(row) if row else None


async def _merge_contacts(session: AsyncSession, keep_id: int, merge_id: int) -> None:
    keep_conv = await _conversation_for_contact(session, keep_id)
    merge_conv = await _conversation_for_contact(session, merge_id)

    if keep_conv and merge_conv:
        await session.execute(
            text("""UPDATE messages SET conversation_id = :keep_conv
                    WHERE conversation_id = :merge_conv"""),
            {"keep_conv": keep_conv["id"], "merge_conv": merge_conv["id"]},
        )
        await session.execute(
            text("""UPDATE conversations
                    SET ai_paused = conversations.ai_paused OR :merge_paused,
                        last_message_at = GREATEST(conversations.last_message_at, :merge_last)
                    WHERE id = :keep_conv"""),
            {
                "keep_conv": keep_conv["id"],
                "merge_paused": merge_conv["ai_paused"],
                "merge_last": merge_conv["last_message_at"],
            },
        )
        await session.execute(
            text("DELETE FROM conversations WHERE id = :id"), {"id": merge_conv["id"]}
        )
    elif merge_conv:
        await session.execute(
            text("UPDATE conversations SET contact_id = :keep WHERE id = :id"),
            {"keep": keep_id, "id": merge_conv["id"]},
        )

    await session.execute(text("DELETE FROM contacts WHERE id = :id"), {"id": merge_id})


async def get_or_create_conversation(session: AsyncSession, wa_id: str, name: Optional[str]) -> dict:
    can_match_phone = _phone_match_enabled(wa_id)
    matches = (await session.execute(
        text("""SELECT id, wa_id, name
                FROM contacts
                WHERE wa_id = :wa
                   OR (:can_match
                       AND char_length(wa_id) >= 10
                       AND (wa_id LIKE ('%' || :wa) OR :wa LIKE ('%' || wa_id)))
                ORDER BY (wa_id = :wa) DESC, char_length(wa_id) DESC, id ASC"""),
        {"wa": wa_id, "can_match": can_match_phone},
    )).mappings().all()

    if matches:
        contact = dict(matches[0])
        canonical_wa_id = wa_id if len(wa_id) > len(contact["wa_id"]) else contact["wa_id"]
        await session.execute(
            text("""UPDATE contacts
                    SET wa_id = :wa,
                        name = COALESCE(:name, name)
                    WHERE id = :id"""),
            {"id": contact["id"], "wa": canonical_wa_id, "name": name},
        )
        for duplicate in matches[1:]:
            await _merge_contacts(session, contact["id"], duplicate["id"])
    else:
        await session.execute(
            text("""INSERT INTO contacts (wa_id, name) VALUES (:wa, :name)
                    ON CONFLICT (wa_id) DO UPDATE SET name = COALESCE(EXCLUDED.name, contacts.name)"""),
            {"wa": wa_id, "name": name},
        )
        contact = (await session.execute(
            text("SELECT id FROM contacts WHERE wa_id = :wa"), {"wa": wa_id}
        )).mappings().first()

    await session.execute(
        text("""INSERT INTO conversations (contact_id) VALUES (:cid)
                ON CONFLICT (contact_id) DO NOTHING"""),
        {"cid": contact["id"]},
    )
    conv = (await session.execute(
        text("""SELECT id, contact_id, ai_paused FROM conversations WHERE contact_id = :cid"""),
        {"cid": contact["id"]},
    )).mappings().first()
    await session.commit()
    return dict(conv)


async def list_conversations(session: AsyncSession) -> list[dict]:
    rows = (await session.execute(text(
        """SELECT c.id, c.ai_paused, c.last_message_at,
                  ct.wa_id, ct.name,
                  (SELECT body FROM messages m WHERE m.conversation_id = c.id
                     ORDER BY m.created_at DESC LIMIT 1) AS last_body,
                  (SELECT msg_type FROM messages m WHERE m.conversation_id = c.id
                     ORDER BY m.created_at DESC LIMIT 1) AS last_type
           FROM conversations c
           JOIN contacts ct ON ct.id = c.contact_id
           ORDER BY c.last_message_at DESC"""
    ))).mappings().all()
    return [dict(r) for r in rows]


async def set_pause(session: AsyncSession, conversation_id: int, paused: bool) -> None:
    await session.execute(
        text("UPDATE conversations SET ai_paused = :p WHERE id = :id"),
        {"p": paused, "id": conversation_id},
    )
    await session.commit()


async def is_paused(session: AsyncSession, conversation_id: int) -> bool:
    row = (await session.execute(
        text("SELECT ai_paused FROM conversations WHERE id = :id"), {"id": conversation_id}
    )).mappings().first()
    return bool(row and row["ai_paused"])


# ---------- messages ----------
async def add_message(session: AsyncSession, conversation_id: int, direction: str,
                      msg_type: str = "text", body: Optional[str] = None,
                      media_url: Optional[str] = None, transcription: Optional[str] = None,
                      wa_message_id: Optional[str] = None) -> Optional[dict]:
    row = (await session.execute(
        text("""INSERT INTO messages
                   (conversation_id, direction, msg_type, body, media_url, transcription, wa_message_id)
                VALUES (:cid, :dir, :mt, :body, :media, :trans, :wamid)
                ON CONFLICT (wa_message_id) WHERE wa_message_id IS NOT NULL DO NOTHING
                RETURNING id, conversation_id, direction, msg_type, body, media_url,
                          transcription, wa_message_id, created_at"""),
        {"cid": conversation_id, "dir": direction, "mt": msg_type, "body": body,
         "media": media_url, "trans": transcription, "wamid": wa_message_id},
    )).mappings().first()
    if row:
        await session.execute(
            text("UPDATE conversations SET last_message_at = now() WHERE id = :id"),
            {"id": conversation_id},
        )
    await session.commit()
    return dict(row) if row else None


async def get_messages(session: AsyncSession, conversation_id: int, limit: int = 200) -> list[dict]:
    rows = (await session.execute(
        text("""SELECT id, direction, msg_type, body, media_url, transcription, created_at
                FROM messages WHERE conversation_id = :id
                ORDER BY created_at ASC LIMIT :lim"""),
        {"id": conversation_id, "lim": limit},
    )).mappings().all()
    return [dict(r) for r in rows]


async def has_template_message(session: AsyncSession, conversation_id: int) -> bool:
    row = (await session.execute(
        text("""SELECT 1 FROM messages
                WHERE conversation_id = :id
                  AND direction = 'out'
                  AND body LIKE '[template:%'
                LIMIT 1"""),
        {"id": conversation_id},
    )).first()
    return row is not None


async def get_history_for_ai(session: AsyncSession, conversation_id: int, limit: int = 20) -> list[dict]:
    """Return recent messages as OpenAI chat turns (oldest first)."""
    rows = (await session.execute(
        text("""SELECT direction, msg_type, body, transcription FROM messages
                WHERE conversation_id = :id ORDER BY created_at DESC LIMIT :lim"""),
        {"id": conversation_id, "lim": limit},
    )).mappings().all()
    turns = []
    for r in reversed(rows):
        content = r["transcription"] or r["body"]
        if not content:
            content = f"[{r['msg_type']} message]"
        turns.append({"role": "user" if r["direction"] == "in" else "assistant",
                      "content": content})
    return turns


# ---------- settings ----------
async def get_settings(session: AsyncSession) -> dict:
    row = (await session.execute(
        text("SELECT system_prompt, openai_model FROM settings WHERE id = 1")
    )).mappings().first()
    return dict(row) if row else {"system_prompt": "", "openai_model": "gpt-4o-mini"}


async def update_settings(session: AsyncSession, system_prompt: str, openai_model: str) -> dict:
    await session.execute(
        text("""UPDATE settings SET system_prompt = :sp, openai_model = :m, updated_at = now()
                WHERE id = 1"""),
        {"sp": system_prompt, "m": openai_model},
    )
    await session.commit()
    return await get_settings(session)
