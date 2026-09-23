# Preview verification

Checked on 23 September 2026. This records observed results, not production certification.

| Check | Evidence |
| --- | --- |
| Backend tests | 56 tests covered: 55 passed in the full local run; the remaining filesystem-isolation test passed when rerun with access to Windows temporary files. |
| Installer/model helpers | All 5 tests passed: new setup, preservation of deployment credentials, exact binary reconstruction, corruption rejection and preservation of an existing invalid model. |
| Local services | Seven Docker services running: web, API, local LLM, PostgreSQL, Redis, Elasticsearch and Nginx. API and datastore health checks passed. |
| Browser walkthrough | Sign-in, workspace creation, overview, source management, reports and AI Command Center inspected in a separate documentation workspace. |
| Local AI | A real health question completed with local inference and live service-health provenance. One CPU response took 86.7 seconds; this is an observation, not a benchmark or latency promise. |
| Runtime health | PostgreSQL, Redis, Elasticsearch, system health and model displayed online. Unconfigured dark-web integration displayed unavailable. |
| Model integrity | The local 2,497,277,408-byte GGUF matched the upstream SHA-256. Both release parts were produced and individually hashed; the full model hash was checked during packaging. |
| Screenshot provenance | Gallery PNGs are real browser captures; the cover is an AI-generated illustration. No fictional threat counts or intelligence results were inserted. |

Full model SHA-256:

```text
69b4e7ba4f0648cb805c5ca0db9375c20bfab137ce65993203099ebad01bc542
```

See [GitHub Actions](https://github.com/hexalpha/DarkTrace-X/actions) for the authoritative per-commit CI results. CI covers the API, web build, setup helpers, secret scanning and container builds. The manually triggered release workflow checks the model hash and manifest again before publishing its assets.

## Not claimed

- A clean-machine, end-to-end installation was not performed as part of this walkthrough; the live screenshots came from the existing local deployment. Fresh-install helpers were tested in isolated temporary directories.
- Cloud LLM providers, paid/licensed feeds, SMTP delivery, GPU acceleration and live Kubernetes were not exercised here.
- Empty workspace views are intentionally shown as empty. Some connectors require external configuration; source lists and UI routes do not prove collection coverage.
- No penetration-test, load-test, production-readiness or third-party security certification is implied.
