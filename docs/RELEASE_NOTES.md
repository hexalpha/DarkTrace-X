# DarkTrace X 0.1.0 Preview

A complete local defensive-intelligence workspace with a Next.js dashboard, FastAPI API, PostgreSQL, Redis, Elasticsearch and a persistent Qwen3 4B GGUF worker.

## Included

- Current application source, tests, database migrations and deployment files.
- Professional README, real application screenshots, installation walkthrough and complete feature catalog.
- Source management and processing views, IOC/actor/graph workflows, alerts, statistical anomaly/trend analysis, reports and scoped AI conversations.
- Local model in two parts, per-part/full SHA-256 checksums, manifest, automatic downloader/joiner, upstream attribution and Apache 2.0 license.

## Install

```bash
git clone https://github.com/hexalpha/DarkTrace-X.git
cd DarkTrace-X
python scripts/setup_local.py
python scripts/model_assets.py download
docker compose --env-file .env.local up -d --build --wait
```

Open http://localhost:8080 and create your workspace. Python 3.12+, Git and Docker Compose v2 are required. See the [installation guide](https://github.com/hexalpha/DarkTrace-X/blob/main/docs/INSTALLATION.md).

## Assets

Download both `.gguf.part001` and `.gguf.part002` for the complete 2,497,277,408-byte model. The installer verifies and joins them; do not rename the parts. GitHub's source ZIP/TAR archives contain code, not model weights. `model-manifest.json`, `SHA256SUMS.txt`, `LICENSE-MODEL.txt` and `MODEL-NOTICE.md` accompany the weights.

Full model SHA-256: `69b4e7ba4f0648cb805c5ca0db9375c20bfab137ce65993203099ebad01bc542`.

The model was published by sillykiwi from DexopT's Qwen3 cybersecurity/Heretic variant; this project does not claim model authorship. Splitting/rejoining leaves weights unchanged.

## Release boundary

This is a local preview, not production certification. Screenshots show a real isolated workspace, including empty data and unavailable integrations. Cloud providers, licensed collection and SMTP require separate configuration. GPU acceleration, live Kubernetes and production security/load qualification are not claimed. Source keeps its existing proprietary/internal status; the model has its own Apache 2.0 license.
