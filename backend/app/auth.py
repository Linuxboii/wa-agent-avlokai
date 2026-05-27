from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_session
from . import models
from .security import verify_password, create_jwt, decode_jwt

router = APIRouter(prefix="/api", tags=["auth"])
_bearer = HTTPBearer(auto_error=False)


class LoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    token: str
    username: str


@router.post("/login", response_model=TokenOut)
async def login(data: LoginIn, session: AsyncSession = Depends(get_session)):
    agent = await models.get_agent(session, data.username)
    if not agent or not verify_password(data.password, agent["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    return TokenOut(token=create_jwt(agent["username"]), username=agent["username"])


async def get_current_agent(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> str:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing token")
    payload = decode_jwt(creds.credentials)
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    return payload["sub"]


def agent_from_token(token: str) -> str | None:
    payload = decode_jwt(token)
    return payload["sub"] if payload else None
