# Install and run DarkTrace X

## Prerequisites

Git, Python 3.12+, Docker Engine/Desktop with Linux containers and Compose v2, and internet access for images/dependencies/model downloads. Suggested starting allocation: 16 GB RAM, 4 CPU cores and 20 GB free disk. This is planning guidance, not a measured minimum. The first CPU inference image build compiles native dependencies and can take several minutes.

## Fresh installation

```bash
git clone https://github.com/hexalpha/DarkTrace-X.git
cd DarkTrace-X
python scripts/setup_local.py
python scripts/model_assets.py download
docker compose --env-file .env.local up -d --build --wait
```

Use `py -3` on Windows or `python3` on macOS/Linux if needed. Setup generates database/search passwords, a worker shared key, an encryption key and an API signing key. Existing non-empty values are preserved. Secrets are never printed. Protect `.env.local` and `.runtime` with your OS account permissions and keep a secure backup.

The downloader validates both parts and the joined model with SHA-256. Re-running it validates the existing model. After success, `.runtime/model-download` is an optional cache for offline reassembly. If the GitHub release is unavailable, explicitly select the original upstream source; the same pinned checksum must match:

```bash
python scripts/model_assets.py download --source upstream
```

## Running and first login

```bash
docker compose --env-file .env.local ps
curl http://localhost:8080/api/v1/health/ready
```

Expected API response: `{"status":"ready"}`. Model loading is asynchronous; confirm **ONLINE** in the copilot separately. The `elastic-backup-init` one-shot container may show `Exited (0)` after success.

Open **http://localhost:8080**, choose **Create a new workspace**, and supply a unique workspace ID, name, email and password of at least 12 characters. The first account becomes administrator. Keep the workspace ID for login. There are no bundled credentials or seeded detections.

![Authentication](images/sign-in.png)

Use Administration to manage users/roles. Register approved sources in Source Management or import evidence/telemetry in the relevant module. The dashboard remains empty until evidence arrives.

## Local AI

Open **http://localhost:8080/ai-command-center**, confirm ONLINE and try “Which services are unhealthy?” Leave cloud permission unchecked for local-only operation. The supplied image is CPU-based; setting GPU-layer options does not add CUDA support.

![AI command center](images/ai-command-center.png)

## Stop and resume

```bash
docker compose --env-file .env.local stop
docker compose --env-file .env.local up -d --wait
docker compose --env-file .env.local logs --tail=100 api local-llm
```

For upgrades, back up data and secrets, preserve credentials paired with populated volumes, and use the **same environment/profile** as the installation. Review [deployment operations](DEPLOYMENT.md). API startup applies Alembic migrations.

**Do not use `docker compose down -v` for a normal restart:** it deletes named data volumes. Existing `.runtime/deployment.env`, Elasticsearch TLS and gateway TLS profiles should keep their original settings; the fresh-clone quick start is a local-development profile.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| Cannot connect to Docker | Start Docker Desktop/Engine and verify `docker info`. |
| Missing POSTGRES/ELASTIC variables | Run setup for a fresh clone and pass `--env-file .env.local`. |
| Database authentication fails after upgrade | Restore the original credentials for the existing volume. |
| Model missing | Run the download/verify command; the root GGUF must be a file. |
| Checksum mismatch | Remove only the corrupted download cache file and retry; do not bypass verification. |
| Model loading/offline | Inspect `local-llm` logs and allow enough RAM/startup time. |
| Zero dashboard counts | Expected for a new workspace; import source-backed evidence. |
| Port 8080 occupied | Resolve the other listener or deliberately adjust gateway mapping and origins. |
| Scheduled report undelivered | Configure SMTP and inspect durable delivery status. |

## Developer checks

From the repository root: `python -m unittest discover -s scripts/tests -v`.

From `apps/api` with its requirements installed: `python -m unittest discover -s tests -v`.

From `apps/web` with Node 22 and pnpm 11: `pnpm install --frozen-lockfile`, `pnpm lint`, `pnpm typecheck`, `pnpm build`.

CI also audits dependencies, scans secrets and builds application images. These checks do not replace deployment-specific security and recovery qualification.
