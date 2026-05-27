import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import ping
from .auth import router as auth_router
from .webhook import router as webhook_router
from .api import router as api_router
from .ws import router as ws_router

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.whatsapp_app_secret:
        raise RuntimeError("WHATSAPP_APP_SECRET must be set (webhook signature verification).")
    if settings.jwt_secret in ("", "dev-secret-change-me"):
        raise RuntimeError("JWT_SECRET must be set to a strong random value.")
    await ping()
    yield


app = FastAPI(title="AvlokAI WhatsApp Bot", lifespan=lifespan)

_allowed = settings.cors_list
if "*" in _allowed:
    raise RuntimeError(
        "CORS_ORIGINS must not be '*' (credentials enabled). Use explicit origins; "
        "avlokai.com / devtunnels / github.io / ngrok / vercel are matched by regex."
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth_router)
app.include_router(webhook_router)
app.include_router(api_router)
app.include_router(ws_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
