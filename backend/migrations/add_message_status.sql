-- Run on VPS: psql $DATABASE_URL -f add_message_status.sql
ALTER TABLE messages ADD COLUMN IF NOT EXISTS status VARCHAR(20);

-- Backfill: outbound messages that have a wamid get 'sent', others stay null
UPDATE messages SET status = 'sent'
WHERE direction = 'out' AND status IS NULL AND wa_message_id IS NOT NULL;
