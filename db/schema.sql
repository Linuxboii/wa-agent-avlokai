-- AvlokAI WhatsApp Bot — PostgreSQL schema
-- Run once on a fresh database:  psql -U avlok -d avlok_wa -f schema.sql

BEGIN;

CREATE TABLE IF NOT EXISTS agents (
    id            SERIAL PRIMARY KEY,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS contacts (
    id         SERIAL PRIMARY KEY,
    wa_id      TEXT NOT NULL UNIQUE,          -- WhatsApp phone (E.164, no +)
    name       TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS conversations (
    id              SERIAL PRIMARY KEY,
    contact_id      INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    ai_paused       BOOLEAN NOT NULL DEFAULT false,
    last_message_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (contact_id)
);

DO $$ BEGIN
    CREATE TYPE msg_direction AS ENUM ('in', 'out');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE msg_type AS ENUM ('text', 'image', 'document', 'audio');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

CREATE TABLE IF NOT EXISTS messages (
    id              SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    direction       msg_direction NOT NULL,
    msg_type        msg_type NOT NULL DEFAULT 'text',
    body            TEXT,                 -- text content (or caption)
    media_url       TEXT,                 -- local path served at /media/<file>
    transcription   TEXT,                 -- Whisper output for inbound audio
    wa_message_id   TEXT,                 -- WhatsApp message id (dedupe)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_messages_conv_created
    ON messages (conversation_id, created_at);
CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_wa_id
    ON messages (wa_message_id) WHERE wa_message_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_conversations_last
    ON conversations (last_message_at DESC);

-- Singleton settings row (id always = 1)
CREATE TABLE IF NOT EXISTS settings (
    id            INTEGER PRIMARY KEY DEFAULT 1,
    system_prompt TEXT NOT NULL,
    openai_model  TEXT NOT NULL DEFAULT 'gpt-4o-mini',
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT settings_singleton CHECK (id = 1)
);

COMMIT;
