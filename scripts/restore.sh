#!/usr/bin/env bash
set -euo pipefail
if [[ $# -ne 2 ]]; then echo "usage: $0 BACKUP_DIRECTORY NEW_DATABASE" >&2; exit 2; fi
database="$2"
[[ "$database" =~ ^[a-z][a-z0-9_]{0,50}$ ]] || { echo "Invalid database name" >&2; exit 2; }
root="$(cd "$(dirname "$0")/.." && pwd)"
backup="$(cd "$1" && pwd)"
[[ -f "$backup/postgres.dump" ]] || { echo "postgres.dump is missing" >&2; exit 1; }
cd "$root"
expected="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8-sig"))["Hash"].lower())' "$backup/checksum.json")"
actual="$(sha256sum "$backup/postgres.dump" | cut -d ' ' -f1)"
[[ "$expected" == "$actual" ]] || { echo "Backup checksum mismatch" >&2; exit 1; }
# Fail if the destination exists: never replace live data implicitly.
docker compose exec -T postgres createdb -U darktrace "$database"
docker compose exec -T postgres pg_restore -U darktrace -d "$database" --exit-on-error --single-transaction --no-owner < "$backup/postgres.dump"
echo "Restored database: $database. Verify data before switching application writers. Redis recovery uses its persistent AOF volume."
