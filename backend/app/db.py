from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text

from .config import settings

engine = create_async_engine(settings.database_url, pool_size=5, max_overflow=10, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session


async def ping() -> bool:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return True
