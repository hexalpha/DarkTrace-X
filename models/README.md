# Local model distribution

The full Q4_K_M GGUF is included as two release assets. GitHub requires each asset to be below 2 GiB, so this 2,497,277,408-byte file is split. Joining the parts recreates the original bytes.

```bash
python scripts/model_assets.py download
python scripts/model_assets.py verify
```

Run from the repository root with Python 3.12+. Part and complete-model checksums are verified. Existing valid models are preserved. Git source archives contain the installer/manifest; release assets contain the weights.

## Offline installation

Download both `.part001` and `.part002` files from [v0.1.0-preview](https://github.com/hexalpha/DarkTrace-X/releases/tag/v0.1.0-preview), keep their filenames, and run:

```bash
python scripts/model_assets.py join --parts-dir /path/to/parts
```

On Windows use a path such as `C:/Users/you/Downloads/model-parts`. The joined model is placed at the repository root for Docker's read-only mount. `--source upstream` explicitly selects the original publisher if release downloads are unavailable; the pinned hash still must match.

## Provenance

| Property | Value |
| --- | --- |
| File | `qwen3-4b-cybersecurity-heretic-16bit-q4_k_m.gguf` |
| Bytes | `2497277408` |
| SHA-256 | `69b4e7ba4f0648cb805c5ca0db9375c20bfab137ce65993203099ebad01bc542` |
| Format | Q4_K_M GGUF |
| GGUF publisher | [sillykiwi](https://huggingface.co/sillykiwi/Qwen3-4B-Cybersecurity-Heretic-16bit-Q4_K_M-GGUF) |
| Source model | [DexopT/Qwen3-4B-Cybersecurity-Heretic-16bit](https://huggingface.co/DexopT/Qwen3-4B-Cybersecurity-Heretic-16bit) |
| Lineage | Qwen3 4B → DexopT cybersecurity/Heretic variant → sillykiwi GGUF |
| License | Apache-2.0; [included text](LICENSE-APACHE-2.0.txt) |

The local SHA-256 matches the [upstream file record](https://huggingface.co/sillykiwi/Qwen3-4B-Cybersecurity-Heretic-16bit-Q4_K_M-GGUF/blob/main/qwen3-4b-cybersecurity-heretic-16bit-q4_k_m.gguf). Authors/converters retain their attribution; DarkTrace X did not train this model. Splitting/rejoining does not change its weights. This model license does not relicense the application.

The Heretic variant has modified refusal behavior. Answers may be inaccurate; verify them against evidence. This project uses scoped, read-only tools for authorized defensive analysis. Cloud adapters are separately opt-in.

## Publisher packaging

`python scripts/model_assets.py pack --output output/release` verifies the original checksum and produces parts, a manifest and checksums. Attach them with the license. The checked-in [manifest](manifest.json) records the exact parts.

[GitHub release size limits](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases).
