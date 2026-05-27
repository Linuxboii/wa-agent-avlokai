# AvlokAI WhatsApp Bot — VPS Deployment Runbook

Run these **in order** on a fresh Ubuntu 22.04/24.04 VPS. Replace
`wa.yourdomain.com`, DB password, and all secrets with your real values.

Assumptions:
- You have a domain and can point an A record to the VPS IP.
- You have your OpenAI API key, WhatsApp permanent token, Business Account ID,
  Phone Number ID, and App Secret ready (from Meta / developers.facebook.com).

---

## 0. Point DNS

In your DNS provider, create an **A record**:
`wa.yourdomain.com  ->  <YOUR_VPS_IP>`
Wait until `ping wa.yourdomain.com` resolves to the VPS IP before TLS step.

---

## 1. Connect + base system

```bash
ssh root@<YOUR_VPS_IP>
apt update && apt upgrade -y
```

## 2. Create a non-root service user

```bash
adduser --disabled-password --gecos "" avlok
usermod -aG sudo avlok
```

## 3. Install system packages

```bash
apt install -y python3 python3-venv python3-pip postgresql postgresql-contrib \
  nginx certbot python3-certbot-nginx git curl
```

## 4. Install Node.js 20 (to build the frontend)

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs
node -v   # expect v20.x
```

## 5. Create the PostgreSQL database + user

```bash
sudo -u postgres psql <<'SQL'
CREATE USER avlok WITH PASSWORD 'CHANGE_ME_DB_PASSWORD';
CREATE DATABASE avlok_wa OWNER avlok;
GRANT ALL PRIVILEGES ON DATABASE avlok_wa TO avlok;
SQL
```

## 6. Get the code onto the VPS

Option A — clone from your git remote:
```bash
sudo mkdir -p /opt/avlok-wa
sudo chown avlok:avlok /opt/avlok-wa
# as the avlok user:
sudo -iu avlok
git clone <YOUR_REPO_URL> /tmp/repo
cp -r /tmp/repo/Whatsapp_template/* /opt/avlok-wa/
cd /opt/avlok-wa
```

Option B — upload the `Whatsapp_template/` folder via scp to `/opt/avlok-wa`.

The result must look like: `/opt/avlok-wa/backend`, `/opt/avlok-wa/frontend`,
`/opt/avlok-wa/db`, `/opt/avlok-wa/deploy`.

## 7. Load the database schema + seed

```bash
cd /opt/avlok-wa/db
psql "postgresql://avlok:CHANGE_ME_DB_PASSWORD@localhost:5432/avlok_wa" -f schema.sql
psql "postgresql://avlok:CHANGE_ME_DB_PASSWORD@localhost:5432/avlok_wa" -f seed.sql
```

## 8. Backend: virtualenv + dependencies

```bash
cd /opt/avlok-wa/backend
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

## 9. Configure environment

```bash
cp .env.example .env
nano .env
```
Fill in **every** value:
- `OPENAI_API_KEY`, `OPENAI_MODEL`
- `WHATSAPP_TOKEN`, `WHATSAPP_BUSINESS_ID`, `WHATSAPP_PHONE_NUMBER_ID`
- `WHATSAPP_VERIFY_TOKEN` (pick any random string — you'll paste the same one into Meta)
- `WHATSAPP_APP_SECRET`
- `AGENT_USERNAME`, `AGENT_PASSWORD` (your dashboard login)
- `JWT_SECRET` (run `openssl rand -hex 32`)
- `DATABASE_URL=postgresql+asyncpg://avlok:CHANGE_ME_DB_PASSWORD@localhost:5432/avlok_wa`
- `PUBLIC_BASE_URL=https://wa.yourdomain.com`
- `MEDIA_DIR=/var/lib/avlok-wa/media`
- `CORS_ORIGINS=https://wa.yourdomain.com`

Create the media dir:
```bash
sudo mkdir -p /var/lib/avlok-wa/media
sudo chown -R avlok:avlok /var/lib/avlok-wa
```

## 10. Create the dashboard login

```bash
cd /opt/avlok-wa/backend
.venv/bin/python create_agent.py   # reads AGENT_USERNAME/AGENT_PASSWORD from .env
```

## 11. Smoke-test the backend

```bash
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 &
sleep 2
curl http://127.0.0.1:8000/health     # expect {"status":"ok"}
kill %1
```

## 12. Install the systemd service

```bash
exit   # back to root (or use sudo)
cp /opt/avlok-wa/deploy/whatsapp-bot.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now whatsapp-bot
systemctl status whatsapp-bot --no-pager   # should be active (running)
```

## 13. Build the frontend

```bash
cd /opt/avlok-wa/frontend
npm install
npm run build          # outputs ./dist
mkdir -p /var/www/avlok-wa
cp -r dist/* /var/www/avlok-wa/
```

## 14. Configure Nginx

```bash
cp /opt/avlok-wa/deploy/nginx.conf /etc/nginx/sites-available/avlok-wa
# edit the file: replace wa.yourdomain.com with your domain
nano /etc/nginx/sites-available/avlok-wa
ln -s /etc/nginx/sites-available/avlok-wa /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t           # test config
systemctl reload nginx
```

## 15. Enable HTTPS (Let's Encrypt)

```bash
certbot --nginx -d wa.yourdomain.com
# choose redirect HTTP->HTTPS when prompted
systemctl reload nginx
```
Verify: open `https://wa.yourdomain.com` — the login screen should load.
Test webhook URL reachable: `curl https://wa.yourdomain.com/health`

## 16. Register the webhook in Meta

In the Meta App dashboard → **WhatsApp → Configuration → Webhook**:
- **Callback URL:** `https://wa.yourdomain.com/webhook`
- **Verify token:** the same string you set in `WHATSAPP_VERIFY_TOKEN`
- Click **Verify and save** (Meta calls GET /webhook; must succeed).
- **Subscribe** to the `messages` field.

Make sure the Phone Number ID and Business Account ID in `.env` match this app,
and that your access token is a **permanent** token (System User token), not a
temporary 24h one.

## 17. End-to-end test

1. From a real phone, send a WhatsApp message to your business number.
2. AI should auto-reply within a few seconds.
3. Open the dashboard, log in, see the conversation appear live.
4. Click **AI active → AI paused**, then reply manually from the dashboard.
5. Send an image and a file from the dashboard — confirm they arrive on the phone.
6. Send a voice note from the phone — confirm the transcription shows in the thread.

---

## Operations cheatsheet

```bash
# logs
journalctl -u whatsapp-bot -f

# restart after code change
systemctl restart whatsapp-bot

# redeploy frontend after change
cd /opt/avlok-wa/frontend && npm run build && cp -r dist/* /var/www/avlok-wa/

# update backend deps
cd /opt/avlok-wa/backend && .venv/bin/pip install -r requirements.txt && systemctl restart whatsapp-bot

# change AI system prompt: use the Settings gear in the dashboard (no redeploy)
```

## Troubleshooting

- **Webhook verify fails:** `WHATSAPP_VERIFY_TOKEN` in `.env` must exactly match
  the token typed in Meta. Service must be running and HTTPS valid.
- **No AI reply:** check `journalctl -u whatsapp-bot -f`; verify `OPENAI_API_KEY`
  and that the conversation is not paused.
- **403 on incoming messages:** `WHATSAPP_APP_SECRET` wrong → signature check fails.
- **Media not loading in dashboard:** ensure `MEDIA_DIR` exists and is writable by
  `avlok`, and `client_max_body_size` in nginx covers the file size.
- **WebSocket not connecting:** confirm nginx `/ws` block present and reloaded.
```
