-- AvlokAI WhatsApp Bot — seed data
-- Run after schema.sql:  psql -d avlokai_wa -f seed.sql

-- Default dashboard login.
--   username: admin@avlokai.com
--   password: admin123   (bcrypt hash below)
-- SECURITY: change this password after first login (re-run create_agent.py with a
-- new AGENT_PASSWORD, or UPDATE the hash). Do not ship admin123 to production.
INSERT INTO agents (username, password_hash)
VALUES (
    'admin@avlokai.com',
    '$2b$12$bVpCvuzgMUdQ/5QhAs0Q3uW0xQxC9q3iuoroggUZSFdUZAAq2i2QO'
)
ON CONFLICT (username) DO NOTHING;

INSERT INTO settings (id, system_prompt, openai_model)
VALUES (
    1,
    'You are the AI assistant for AvlokAI, an AI automation agency. ' ||
    'You help potential and existing customers over WhatsApp. ' ||
    'AvlokAI builds custom AI automations: chatbots, workflow automation, ' ||
    'data pipelines, and AI integrations for businesses. ' ||
    'Be concise, friendly, and professional. Answer questions about services, ' ||
    'pricing approach (custom quotes), and how to get started. ' ||
    'If a request needs a human (custom quote, sensitive issue, complaint), say a ' ||
    'team member will follow up shortly. Never invent specific prices or commitments.',
    'gpt-4o-mini'
)
ON CONFLICT (id) DO NOTHING;
