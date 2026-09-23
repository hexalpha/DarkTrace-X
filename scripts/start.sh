#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"
environment="${1:-.runtime/deployment.env}"
files=(-f docker-compose.yml -f docker-compose.elasticsearch-tls.yml)
if [[ "${2:-}" == "--production" ]]; then files+=(-f docker-compose.tls.yml); fi
docker compose --env-file "$environment" "${files[@]}" up -d --wait
