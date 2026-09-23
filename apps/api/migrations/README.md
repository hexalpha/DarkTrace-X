# Database migrations

Run from `apps/api` with `DATABASE_URL` set to the target PostgreSQL database:

```powershell
python -m alembic upgrade head
python -m alembic downgrade -1
```

`0001_source_pipeline` creates the source, crawl, document, entity, observation and threat-event tables idempotently, including indexes and tenant-scoped uniqueness constraints. It is safe to run against an existing DarkTrace X database where these tables were previously created by the development bootstrap.

The older application tables predate this migration package and are still bootstrapped by `Base.metadata.create_all` in the current development profile. Before a production rollout, create and review a baseline migration for those legacy tables, then disable automatic schema creation in production.