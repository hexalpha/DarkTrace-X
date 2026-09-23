"""Package, fetch and verify the exact bundled GGUF using only Python's standard library."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL = "qwen3-4b-cybersecurity-heretic-16bit-q4_k_m.gguf"
MODEL_SHA = "69b4e7ba4f0648cb805c5ca0db9375c20bfab137ce65993203099ebad01bc542"
MODEL_SIZE = 2497277408
RELEASE = "v0.1.0-preview"
BASE = "https://github.com/hexalpha/DarkTrace-X/releases/download/" + RELEASE
UPSTREAM = "https://huggingface.co/sillykiwi/Qwen3-4B-Cybersecurity-Heretic-16bit-Q4_K_M-GGUF/resolve/main/" + MODEL
BLOCK = 8 * 1024 * 1024


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify(path: Path, expected: str, size: int) -> None:
    if not path.is_file() or path.stat().st_size != size or digest(path) != expected:
        raise ValueError("Size or SHA-256 mismatch: " + path.name)


def pack(model: Path, output: Path, part_size: int = 1500000000) -> dict:
    if not 0 < part_size < 2 * 1024**3:
        raise ValueError("Each release part must be below 2 GiB")
    if model.stat().st_size != MODEL_SIZE:
        raise ValueError("Unexpected model size")
    output.mkdir(parents=True, exist_ok=True)
    manifest = {"filename": MODEL, "size": MODEL_SIZE, "sha256": MODEL_SHA,
                "license": "Apache-2.0", "release": RELEASE, "parts": []}
    full_hash = hashlib.sha256()
    with model.open("rb") as source:
        remaining = MODEL_SIZE
        index = 1
        while remaining:
            name = MODEL + f".part{index:03d}"
            size = min(part_size, remaining)
            part_hash = hashlib.sha256()
            with (output / name).open("xb") as target:
                written = 0
                while written < size:
                    data = source.read(min(BLOCK, size - written))
                    if not data:
                        raise ValueError("Unexpected end of model")
                    target.write(data)
                    full_hash.update(data)
                    part_hash.update(data)
                    written += len(data)
            manifest["parts"].append({"filename": name, "size": size,
                                      "sha256": part_hash.hexdigest(), "url": BASE + "/" + name})
            remaining -= size
            print(f"Packaged {name}: {size:,} bytes", flush=True)
            index += 1
    if full_hash.hexdigest() != MODEL_SHA:
        raise ValueError("Model does not match the published upstream checksum; do not publish these parts")
    (output / "model-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (output / "SHA256SUMS.txt").write_text(
        "".join(f"{part['sha256']}  {part['filename']}\n" for part in manifest["parts"])
        + f"{MODEL_SHA}  {MODEL}\n", encoding="utf-8")
    print("Complete model SHA-256 verified against upstream.", flush=True)
    return manifest


def load_manifest(path: Path) -> dict:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if (manifest["filename"], manifest["size"], manifest["sha256"]) != (MODEL, MODEL_SIZE, MODEL_SHA):
        raise ValueError("Manifest does not describe the expected model")
    parts = manifest["parts"]
    if not parts or sum(part["size"] for part in parts) != MODEL_SIZE:
        raise ValueError("Incomplete manifest")
    for index, part in enumerate(parts, 1):
        if part["filename"] != MODEL + f".part{index:03d}" or not 0 < part["size"] < 2 * 1024**3:
            raise ValueError("Invalid part filename or size")
        if part["url"] != BASE + "/" + part["filename"]:
            raise ValueError("Unexpected release asset URL")
    return manifest


def fetch(url: str, target: Path, sha: str, size: int) -> None:
    if target.exists():
        verify(target, sha, size)
        print("Verified cached " + target.name, flush=True)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".download")
    print("Downloading " + target.name, flush=True)
    request = urllib.request.Request(url, headers={"User-Agent": "DarkTrace-X-model-installer/0.1"})
    with urllib.request.urlopen(request, timeout=120) as response, partial.open("wb") as stream:
        shutil.copyfileobj(response, stream, BLOCK)
    verify(partial, sha, size)
    partial.replace(target)


def join_parts(parts: list[dict], directory: Path, target: Path, sha: str, size: int) -> None:
    if target.exists():
        verify(target, sha, size)
        print("Existing model verified; no replacement needed.")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".assembling")
    with temporary.open("wb") as output:
        for part in parts:
            source = directory / part["filename"]
            verify(source, part["sha256"], part["size"])
            with source.open("rb") as stream:
                shutil.copyfileobj(stream, output, BLOCK)
    verify(temporary, sha, size)
    temporary.replace(target)
    print("Model assembled and verified: " + target.name)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["download", "join", "verify", "pack"])
    parser.add_argument("--model", type=Path, default=ROOT / MODEL)
    parser.add_argument("--parts-dir", type=Path, default=ROOT / ".runtime" / "model-download")
    parser.add_argument("--manifest", type=Path, default=ROOT / "models" / "manifest.json")
    parser.add_argument("--output", type=Path, default=ROOT / "output" / "release")
    parser.add_argument("--source", choices=["release", "upstream"], default="release")
    args = parser.parse_args()
    if args.command == "pack":
        pack(args.model, args.output)
    elif args.command == "verify" or (args.command == "download" and args.model.exists()):
        verify(args.model, MODEL_SHA, MODEL_SIZE)
        print("Model size and SHA-256 verified.")
    elif args.command == "download" and args.source == "upstream":
        fetch(UPSTREAM, args.model, MODEL_SHA, MODEL_SIZE)
    else:
        manifest = load_manifest(args.manifest)
        if args.command == "download":
            for part in manifest["parts"]:
                fetch(part["url"], args.parts_dir / part["filename"], part["sha256"], part["size"])
        join_parts(manifest["parts"], args.parts_dir, args.model, MODEL_SHA, MODEL_SIZE)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError) as error:
        print("Model setup failed: " + str(error), file=sys.stderr)
        sys.exit(1)
