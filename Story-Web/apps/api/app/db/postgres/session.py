from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings

# Tạo Async Engine kết nối tới PostgreSQL
engine = create_async_engine(
    settings.DATABASE_URL.replace("postgres://", "postgresql+asyncpg://") if settings.DATABASE_URL else "postgresql+asyncpg://postgres:postgres@localhost:5432/story_db",
    echo=True, # In luồng Query SQL ra màn hình dev
    future=True
)

# Tạo Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency Injection để lấy DB Session cho mỗi Request FastAPI
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
