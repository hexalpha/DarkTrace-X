"""Prepare a fresh local Docker install without replacing existing secrets."""
from __future__ import annotations

import base64
import secrets
from pathlib import Path


def read_env(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    return {
        key.strip(): value.strip().strip("\"'")
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#") and "=" in line
        for key, value in [line.split("=", 1)]
    }


def fill_missing(path: Path, defaults: dict[str, str]) -> None:
    values = read_env(path)
    missing = {key: value for key, value in defaults.items() if not values.get(key)}
    if not missing:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = path.read_text(encoding="utf-8-sig").splitlines() if path.exists() else []
    # Replace empty entries, preserving all unrelated settings and comments.
    for index, line in enumerate(lines):
        key = line.split("=", 1)[0].strip() if "=" in line else ""
        if key in missing:
            lines[index] = key + "=" + missing.pop(key)
    lines.extend(key + "=" + value for key, value in missing.items())
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    path.chmod(0o600)


def prepare(root: Path) -> None:
    local = root / ".env.local"
    runtime = root / ".runtime"
    runtime.mkdir(exist_ok=True)
    # A previously deployed installation may have credentials in this file.
    existing = read_env(runtime / "deployment.env")
    defaults = {
        "APP_ENV": "development", "POSTGRES_DB": "darktracex",
        "POSTGRES_USER": "darktrace", "POSTGRES_PASSWORD": secrets.token_urlsafe(36),
        "ELASTIC_PASSWORD": secrets.token_urlsafe(36),
        "LOCAL_LLM_ENABLED": "true",
        "LOCAL_LLM_MODEL_PATH": "./qwen3-4b-cybersecurity-heretic-16bit-q4_k_m.gguf",
        "EXTERNAL_AI_ENABLED": "false",
    }
    fill_missing(local, {key: existing.get(key) or value for key, value in defaults.items()})
    fill_missing(runtime / "copilot.env", {
        "COPILOT_WORKER_KEY": secrets.token_urlsafe(48),
        "AI_SECRET_KEY": base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
    })
    configured_jwt = read_env(local).get("JWT_SECRET", "")
    fill_missing(runtime / "api-security.env", {
        "JWT_SECRET": configured_jwt if len(configured_jwt) >= 32 else secrets.token_urlsafe(48),
    })
    print("Local configuration ready. Existing non-empty settings were preserved.")
    print("Secrets stay in .env.local and .runtime; restrict access to your OS account.")
    print("Next: python scripts/model_assets.py download")
    print("Then: docker compose --env-file .env.local up -d --build --wait")


if __name__ == "__main__":
    prepare(Path(__file__).resolve().parents[1])
