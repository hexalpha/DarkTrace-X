"""Exercise SQL persistence locally without an external PostgreSQL service."""
from types import SimpleNamespace
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.storage.models import Base
from tests.integration_advanced import PersistenceTests


class AsyncSessionAdapter:
    def __init__(self, engine):
        self.session = Session(engine, expire_on_commit=False)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        self.session.close()

    def add(self, record):
        self.session.add(record)

    async def execute(self, query):
        return self.session.execute(query)

    async def scalars(self, query):
        return self.session.scalars(query)

    async def scalar(self, query):
        return self.session.scalar(query)

    async def get(self, model, key):
        return self.session.get(model, key)

    async def delete(self, record):
        self.session.delete(record)

    async def commit(self):
        self.session.commit()

    async def flush(self):
        self.session.flush()


class LocalPersistenceTests(PersistenceTests):
    async def test_lifecycle_and_tenant_isolation(self):
        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine)
        async def noop():
            pass
        db = SimpleNamespace(ready=True, sessions=lambda: AsyncSessionAdapter(engine), connect=noop, close=noop)
        try:
            with patch("app.storage.database.configure_database", return_value=db), patch("app.storage.database.database", db):
                await super().test_lifecycle_and_tenant_isolation()
        finally:
            engine.dispose()


# Avoid unittest collecting the imported PostgreSQL integration case.
del PersistenceTests
