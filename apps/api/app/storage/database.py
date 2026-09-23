import logging

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy import text

from app.core.config import Settings
from app.storage.models import Base

logger = logging.getLogger(__name__)


class Database:
    """PostgreSQL connection manager. It never substitutes fabricated data when unavailable."""

    def __init__(self, settings: Settings) -> None:
        self.engine: AsyncEngine | None = None
        self.sessions: async_sessionmaker | None = None
        self.bootstrap_error: Exception | None = None
        try:
            self.engine = create_async_engine(settings.database_url, pool_pre_ping=True)
            self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        except Exception as exc:
            self.bootstrap_error = exc
        self.ready = False

    async def connect(self) -> None:
        if self.engine is None:
            logger.warning("PostgreSQL driver unavailable: %s", self.bootstrap_error.__class__.__name__ if self.bootstrap_error else "unknown")
            return
        try:
            async with self.engine.begin() as connection:
                await connection.execute(text("SELECT 1"))
            self.ready = True
        except Exception as exc:  # Startup must still expose liveness and explicit readiness state.
            self.ready = False
            logger.warning("PostgreSQL unavailable: %s", exc.__class__.__name__)

    async def close(self) -> None:
        if self.engine is not None:
            await self.engine.dispose()


database: Database | None = None


def configure_database(settings: Settings) -> Database:
    global database
    database = Database(settings)
    return database
