"""Create a factual DarkTrace X project verification PDF from the readiness JSON."""
from datetime import datetime
from html import escape
import json
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import LongTable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

root = Path(__file__).resolve().parents[1]
data = json.loads((root / "docs" / "readiness-report.json").read_text(encoding="utf-8"))
output = root / "output" / "pdf" / "darktrace-x-project-status-report.pdf"
navy, panel, cyan, text, muted = [colors.HexColor(x) for x in ("#071525", "#0d2236", "#22d3ee", "#dbeafe", "#9fb5c7")]
status_colors = {"PASS": colors.HexColor("#34d399"), "PARTIAL": colors.HexColor("#fbbf24"), "FAIL": colors.HexColor("#fb7185"), "NOT TESTED": colors.HexColor("#7890a4")}
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="coverx", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=27, leading=33, textColor=text, alignment=TA_CENTER, spaceAfter=12))
styles.add(ParagraphStyle(name="subx", parent=styles["Normal"], fontName="Helvetica", fontSize=11, leading=16, textColor=muted, alignment=TA_CENTER, spaceAfter=12))
styles.add(ParagraphStyle(name="h1x", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=17, leading=21, textColor=cyan, spaceAfter=8))
styles.add(ParagraphStyle(name="h2x", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=text, spaceBefore=8, spaceAfter=4))
styles.add(ParagraphStyle(name="bodyx", parent=styles["BodyText"], fontName="Helvetica", fontSize=9, leading=13, textColor=muted, spaceAfter=6))
styles.add(ParagraphStyle(name="cellx", parent=styles["BodyText"], fontName="Helvetica", fontSize=7, leading=9, textColor=muted))
styles.add(ParagraphStyle(name="headx", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=7, leading=9, textColor=text))

def P(value, style="bodyx"):
    return Paragraph(escape(str(value)).replace("\n", "<br/>"), styles[style])

def matrix(rows):
    values = [[P("Feature", "headx"), P("Status", "headx"), P("Evidence / exact reason", "headx")]]
    for row in rows:
        badge_style = ParagraphStyle("badge" + row["status"], parent=styles["headx"], alignment=TA_CENTER, textColor=status_colors[row["status"]])
        values.append([P(row["feature"], "cellx"), Paragraph(escape(row["status"]), badge_style), P(row["reason"], "cellx")])
    table = LongTable(values, colWidths=[45 * mm, 23 * mm, 117 * mm], repeatRows=1, splitByRow=1)
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), panel), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [navy, colors.HexColor("#091c2e")]), ("GRID", (0, 0), (-1, -1), .25, colors.HexColor("#244259")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    return table

def decorate(canvas, doc):
    canvas.saveState(); canvas.setFillColor(navy); canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0); canvas.setFillColor(cyan); canvas.setFont("Helvetica-Bold", 8); canvas.drawString(15 * mm, A4[1] - 13 * mm, "DARKTRACE X"); canvas.setFillColor(muted); canvas.setFont("Helvetica", 7); canvas.drawRightString(A4[0] - 15 * mm, A4[1] - 13 * mm, "PROJECT STATUS AND VERIFICATION"); canvas.line(15 * mm, A4[1] - 17 * mm, A4[0] - 15 * mm, A4[1] - 17 * mm); canvas.line(15 * mm, 14 * mm, A4[0] - 15 * mm, 14 * mm); canvas.drawString(15 * mm, 9 * mm, "Repository evidence snapshot; not a security certification"); canvas.drawRightString(A4[0] - 15 * mm, 9 * mm, f"Page {doc.page}"); canvas.restoreState()

features = data["features"]
groups = {status: [row for row in features if row["status"] == status] for status in ("PASS", "PARTIAL", "FAIL", "NOT TESTED")}
stamp = datetime.fromisoformat(data["generated_at"].replace("Z", "+00:00")).strftime("%d %b %Y, %H:%M UTC")
story = [Spacer(1, 45 * mm), P("DEFENSIVE AI CYBERSECURITY PLATFORM", "subx"), P("DarkTrace X", "coverx"), P("Project Status, Working Features and Verification Report", "subx")]
cover = Table([[P("STATUS", "headx"), P("READINESS", "headx"), P("VERIFIED SNAPSHOT", "headx")], [P(data["status"], "headx"), P(f"{data['readiness_percentage']}%", "headx"), P(stamp, "cellx")]], colWidths=[45 * mm, 45 * mm, 65 * mm])
cover.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), panel), ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#0a2032")), ("GRID", (0, 0), (-1, -1), .4, colors.HexColor("#244259")), ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
story += [cover, Spacer(1, 12 * mm), P("Production Ready: NO", "h2x"), P("The local Docker installation is operational and evidence-tested. Overall status remains PARTIALLY READY because cloud quota, licensed intelligence, GPU and production deployment validation are external or incomplete. Source-code presence is not treated as proof of operation."), PageBreak(), P("1. Executive status", "h1x"), P(f"Verified checklist: {data['scoring']['counts']['PASS']} PASS, {data['scoring']['counts']['PARTIAL']} PARTIAL, {data['scoring']['counts']['FAIL']} FAIL and {data['scoring']['counts']['NOT TESTED']} NOT TESTED. Equal-weight coverage is {data['readiness_percentage']}% ({data['scoring']['earned_points']}/{data['scoring']['possible_points']} points)."), P("The verified entrypoint is the existing Docker Compose deployment at http://localhost:8080. PostgreSQL, Redis and Elasticsearch volumes are preserved. The GGUF model qwen3-4b-cybersecurity-heretic-16bit-q4_k_m.gguf is loaded once by a persistent CPU worker; LOCAL_LLM_MODEL_PATH is configurable."), P("Production data policy: empty workspaces remain empty. Synthetic verification records were isolated to disposable tenants and removed. CISA intelligence is source-attributed and unavailable values are not fabricated."), P("2. Verification summary", "h1x"), P("The prior deployed Docker suite passed 28 backend tests and three model-worker fault tests; four new webhook/report-schedule validation tests pass locally. The updated API image needs a Docker rebuild before its database delivery paths can be live-verified. Next.js production build, TypeScript and lint passed. The live workflow verified authentication, RBAC, tenant isolation, PostgreSQL, Redis, Elasticsearch, GraphQL, WebSocket, MCP, IOC correlation, anomaly detection, alerts, CISA/CVE ingestion, reports and local AI persistence."), PageBreak()]
for title, status, note in [("3. Working and verified features", "PASS", "Direct automated, live or browser evidence exists."), ("4. Partially working features", "PARTIAL", "Bounded implementation works, but the exact limitation prevents a full production claim."), ("5. Broken or unavailable requested feature", "FAIL", "A required capability has a verified failure or unavailable dependency."), ("6. Features not tested", "NOT TESTED", "Live verification could not be completed with the supplied environment.")]:
    story += [P(title, "h1x"), P(note), matrix(groups[status]), PageBreak()]
story += [P("7. Implemented product areas", "h1x")]
for title, body in [("Floating SOC copilot", "Persistent authenticated assistant with history, search, new/clear sessions, Markdown, code blocks, copy, stop, regenerate, streaming, auto-scroll, responsive panel and command-center route."), ("Local model and gateway", "Persistent GGUF worker with configurable runtime, graceful OFFLINE state, encrypted provider keys and bounded primary/fallback/offline routing across local and cloud adapters."), ("Project-aware SOC context", "Allowlisted project knowledge and strict read-only tools for tenant-scoped alerts, IOCs, CVEs, feeds, actors, health, mentions, events, assets and live CISA intelligence."), ("Threat intelligence and operations", "Explainable anomaly detection, evidence-linked forecast, IOC graph/correlation, keyword exposure imports, CISA KEV, actors, alert deduplication, triage, reports, REST, GraphQL, WebSocket and MCP."), ("Deployment", "Docker Compose runs API, web, Nginx, PostgreSQL, Redis, Elasticsearch and local-LLM. Kubernetes manifests now include a non-root GGUF worker, protected PVC, worker-secret boundary and API-to-worker NetworkPolicy.")]:
    story += [P(title, "h2x"), P(body)]
story += [PageBreak(), P("8. Pending work and exact reasons", "h1x")]
pending = ["OpenAI live completion returned HTTP 429; resolve quota/account state externally.", "Gemini, Anthropic, Groq, OpenRouter, custom endpoint and Ollama live completions were not verified with working credentials/services.", "No licensed dark-web provider is configured; defensive evidence import works, but live collection is unavailable.", "GPU inference was not tested on the host; only capability detection and simulated CPU fallback were tested.", "Kubernetes target-cluster rollout, TLS, secret manager, policy enforcement and GPU scheduling remain untested.", "Versioned database migrations and rollback are absent; current bootstrap is additive SQLAlchemy create_all.", "Arbitrary third-party plugin signing, distribution and sandboxing are not implemented; three built-in extensions work.", "Report schedules are durably registered and audited, but delivery remains pending until SMTP or an approved delivery worker is configured.", "TLS, SSO/MFA, database RLS, immutable audit retention, load qualification and disaster-restore testing remain outstanding.", "Autonomous tool reasoning, calibrated forecast accuracy, incident-quality/MITRE evaluation and comprehensive adversarial Markdown tests need dedicated evaluation data."]
story += [P("- " + item) for item in pending] + [P("9. Security and data handling", "h1x")]
for item in ["Tenant and RBAC boundaries are enforced for API, AI tools, conversations and intelligence.", "The model cannot execute shell, SQL, Python, filesystem operations or privileged writes through the current tool set.", "Prompt defenses, strict schemas, request limits, rate controls, timeouts, audit records and redaction are defense in depth; model output remains untrusted.", "Provider secrets are encrypted and never returned to frontend JavaScript. Never paste passwords, tokens, private keys or unrestricted logs into the assistant.", "Before shared deployment configure unique service credentials, TLS, secret management, SSO/MFA and immutable audit retention."]:
    story += [P("- " + item)]
story += [P("10. Required configuration and runbook", "h1x"), P("Required variables: " + ", ".join(data["required_environment"]) + ". Optional integrations: " + ", ".join(data["optional_environment"]) + ". Keep secrets server-side and never commit .env files or the GGUF file."), P("PowerShell: python scripts/setup_copilot.py; docker compose --env-file .env.local up -d --build --wait; docker compose ps"), P("Verification: run the verify compose command with python -m unittest discover -s tests -v, then scripts.verify_copilot and scripts.smoke_workspace."), PageBreak(), P("11. URLs and final status", "h1x")]
url_rows = [[P("Service", "headx"), P("URL/address", "headx"), P("Exposure", "headx")]] + [[P(item["service"], "cellx"), P(item["url"], "cellx"), P("Host loopback" if item["published"] else "Internal only", "cellx")] for item in data["services"]]
url_table = Table(url_rows, colWidths=[48 * mm, 82 * mm, 40 * mm], repeatRows=1)
url_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), panel), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [navy, colors.HexColor("#091c2e")]), ("GRID", (0, 0), (-1, -1), .25, colors.HexColor("#244259")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
story += [url_table, Spacer(1, 8 * mm), P("Primary URL: http://localhost:8080/ai-command-center", "h2x"), P(f"DARKTRACE X STATUS: {data['status']} - {data['readiness_percentage']}%. Ready for local defensive evaluation and controlled internal use after setting secrets. Not certified as a production-ready enterprise deployment until pending validation and external dependencies are addressed.")]
output.parent.mkdir(parents=True, exist_ok=True)
doc = SimpleDocTemplate(str(output), pagesize=A4, rightMargin=15 * mm, leftMargin=15 * mm, topMargin=23 * mm, bottomMargin=19 * mm, title="DarkTrace X Project Status Report", author="DarkTrace X")
doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
print(output)
