#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
stamp="$(date -u +%Y%m%d-%H%M%S)"
target="$root/backups/$stamp"
mkdir -p "$target"
chmod 700 "$target"
cd "$root"
docker compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom' > "$target/postgres.dump"
python3 -c 'import hashlib,json,sys; p=sys.argv[1]; h=hashlib.file_digest(open(p+"/postgres.dump","rb"),"sha256").hexdigest(); json.dump({"Algorithm":"SHA256","Hash":h},open(p+"/checksum.json","w"))' "$target"
repo='{"type":"fs","settings":{"location":"/backups"}}'
if ! docker compose exec -T -e DARKTRACE_ES_PATH=/_snapshot/darktracex-backup elasticsearch sh /usr/local/bin/dtx-es-request > "$target/elasticsearch-repository.txt"; then
    docker compose exec -T -e DARKTRACE_ES_PATH=/_snapshot/darktracex-backup elasticsearch sh /usr/local/bin/dtx-es-request -X PUT -H 'Content-Type: application/json' -d "$repo" > "$target/elasticsearch-repository.txt"
fi
docker compose exec -T -e "DARKTRACE_ES_PATH=/_snapshot/darktracex-backup/$stamp?wait_for_completion=true" elasticsearch sh /usr/local/bin/dtx-es-request -X PUT -H 'Content-Type: application/json' -d '{"include_global_state":false}' > "$target/elasticsearch-snapshot.json"
python3 -c 'import json,sys; state=json.load(open(sys.argv[1]))["snapshot"]["state"]; sys.exit(0 if state=="SUCCESS" else "Snapshot did not succeed: "+state)' "$target/elasticsearch-snapshot.json"
echo "Backup created: $target"
