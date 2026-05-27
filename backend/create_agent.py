"""Create/update the single dashboard agent from env vars.
Run once on deploy:  python create_agent.py
Uses AGENT_USERNAME + AGENT_PASSWORD from .env."""
import asyncio
from app.config import settings
from app.db import SessionLocal
from app import models
from app.security import hash_password


async def main():
    if not settings.agent_password:
        raise SystemExit("AGENT_PASSWORD not set in .env")
    async with SessionLocal() as session:
        await models.create_agent(
            session, settings.agent_username, hash_password(settings.agent_password)
        )
    print(f"Agent '{settings.agent_username}' created/updated.")


if __name__ == "__main__":
    asyncio.run(main())
