"use client";
import { apiFetch } from "../lib/api";

import { FormEvent, useEffect, useState } from "react";
import { Activity, ArrowUpRight, BrainCircuit, CheckCircle2, Package, RefreshCw, Server, Shield } from "lucide-react";

export type AdvancedFeature = "anomalies" | "predictive" | "mcp" | "marketplace";
type Finding = { id: string; entity: string; metric: string; value: number; score: number; baseline: number; baseline_samples: number; severity: string; explanation: string; observed_at: string; recommendation: string };
type Forecast = { entity: string; metric: string; risk_score: number; trend: string; confidence: string; evidence_count: number; evidence_ids: string[]; recommendation: string };
type Detection = { event_count: number; baseline_ready: number; learning: number; model: string; anomalies: Finding[]; predictions: Forecast[]; limitations: string; window: string };
type Plugin = { id: string; name: string; description: string; category: string; version: string; scopes: string[]; installed: boolean; enabled: boolean };
type Catalog = { plugins: Plugin[]; can_manage: boolean; can_run: boolean };
type Mcp = { servers: { id: string; name: string; endpoint: string; protocol: string; authentication: string; tools: { name: string; description: string }[] }[] };
const meta = {
  anomalies: ["BEHAVIORAL INTELLIGENCE", "AI Anomaly Detection", "Learn normal activity. Surface unusual behavior with explainable evidence."],
  predictive: ["EARLY WARNING", "Predictive Threat Engine", "Prioritize emerging risk from recent behavioral evidence."],
  mcp: ["CONNECTED INTELLIGENCE", "MCP Servers", "Connect compatible assistants to authenticated, read-only intelligence tools."],
  marketplace: ["EXTEND YOUR WORKSPACE", "Plugin Marketplace", "Discover and manage curated extensions with explicit permissions."],
};

async function api<T>(base: string, path: string, method = "GET", body?: unknown): Promise<T> {
  const response = await apiFetch(`${base}/api/v1${path}`, { method, headers: { "Content-Type": "application/json",  }, ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
  const data = response.status === 204 ? {} : await response.json();
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : Array.isArray(data.detail) ? data.detail.map((e: {msg: string}) => e.msg).join("; ") : "Request failed. Please retry.");
  return data;
}

export function AdvancedWorkspace({ feature, apiBase }: { feature: AdvancedFeature; apiBase: string }) {
  const [data, setData] = useState<Detection | null>(null);
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [servers, setServers] = useState<Mcp | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [revision, setRevision] = useState(0);
  const [query, setQuery] = useState("");
  const [severity, setSeverity] = useState("all");
  const [input, setInput] = useState("");
  const [output, setOutput] = useState<unknown>(null);
  const refresh = () => setRevision(v => v + 1);
  useEffect(() => {
    let active = true;
    setLoading(true); setError(""); setOutput(null);
    const load = async () => {
      try {
        if (feature === "marketplace") { const value = await api<Catalog>(apiBase, "/marketplace"); if (active) setCatalog(value); }
        else if (feature === "mcp") { const value = await api<Mcp>(apiBase, "/mcp/servers"); if (active) setServers(value); }
        else { const value = await api<Detection>(apiBase, "/detection/overview"); if (active) setData(value); }
      } catch (reason) { if (active) setError(reason instanceof Error ? reason.message : "Unable to load workspace"); }
      finally { if (active) setLoading(false); }
    };
    void load(); return () => { active = false; };
  }, [apiBase, feature, revision]);
  async function action(work: () => Promise<void>) {
    setWorking(true); setError(""); setNotice("");
    try { await work(); } catch (reason) { setError(reason instanceof Error ? reason.message : "Action failed"); }
    finally { setWorking(false); }
  }
  function ingest(event: FormEvent) {
    event.preventDefault();
    void action(async () => { const result = await api<{inserted: number; duplicates: number}>(apiBase, "/telemetry", "POST", JSON.parse(input)); setNotice(`${result.inserted} events saved; ${result.duplicates} duplicates skipped.`); refresh(); });
  }
  const [eyebrow, title, description] = meta[feature];
  return <div className="advanced-workspace">
    <section className="module-header"><p>{eyebrow}</p><h1>{title}</h1><span>{description}</span><button className="advanced-refresh" onClick={refresh} disabled={loading || working}><RefreshCw size={14}/> Refresh</button></section>
    {error && <div className="module-notice error" role="alert">{error}</div>}
    {notice && <div className="module-notice success" role="status"><CheckCircle2 size={16}/>{notice}</div>}
    {loading ? <div className="module-loading">Loading workspace…</div> : <>
      {(feature === "anomalies" || feature === "predictive") && data && <>
        <div className="advanced-stats">{[["Telemetry events", data.event_count], ["Ready baselines", data.baseline_ready], ["Learning baselines", data.learning], [feature === "anomalies" ? "Anomalies" : "Forecasts", feature === "anomalies" ? data.anomalies.length : data.predictions.length]].map(([label, value]) => <article className="module-card" key={label}><Activity size={18}/><strong>{value}</strong><span>{label}</span></article>)}</div>
        <div className="advanced-info"><BrainCircuit size={18}/><div><strong>Local behavioral model · {data.model}</strong><p>{data.limitations}</p><small>{data.window}</small></div></div>
        <div className="module-form"><input aria-label="Filter entities" placeholder="Search entity or metric…" value={query} onChange={e => setQuery(e.target.value)}/>{feature === "anomalies" && <select aria-label="Severity" value={severity} onChange={e => setSeverity(e.target.value)}><option value="all">All severities</option><option value="critical">Critical</option><option value="high">High</option><option value="medium">Medium</option></select>}</div>
        {feature === "anomalies" ? <div className="advanced-results">{data.anomalies.filter(item => `${item.entity} ${item.metric}`.toLowerCase().includes(query.toLowerCase()) && (severity === "all" || item.severity === severity)).map(item => <article className="module-card" key={item.id}><div className="advanced-row"><span className={`status-pill ${item.severity}`}>{item.severity}</span><strong>{item.score}/100</strong></div><h2>{item.entity}</h2><p>{item.metric.replaceAll("_", " ")}</p><div className="risk-track"><span style={{width: `${item.score}%`}}/></div><p>{item.explanation}</p><small>Observed {item.value.toLocaleString()} · baseline {item.baseline.toLocaleString()} · {item.baseline_samples} prior samples</small><details><summary>Inspect evidence</summary><p>Event: {item.id}</p><p>{new Date(item.observed_at).toLocaleString()}</p><p>{item.recommendation}</p></details></article>)}</div> : <div className="advanced-results">{data.predictions.filter(item => `${item.entity} ${item.metric}`.toLowerCase().includes(query.toLowerCase())).map(item => <article className="module-card" key={`${item.entity}:${item.metric}`}><div className="advanced-row"><span className="status-pill">{item.trend}</span><ArrowUpRight size={18}/></div><h2>{item.entity}</h2><p>{item.metric.replaceAll("_", " ")}</p><div className="forecast-score">{item.risk_score}<small>/100 priority</small></div><div className="risk-track"><span style={{width: `${item.risk_score}%`}}/></div><p>24-hour outlook · {item.confidence} confidence</p><p>{item.recommendation}</p><details><summary>{item.evidence_count} scored observations</summary><p>{item.evidence_ids.join(", ")}</p></details></article>)}</div>}
        {(feature === "anomalies" ? data.anomalies.length === 0 : data.predictions.length === 0) && <div className="empty-state">{data.event_count === 0 ? "No telemetry yet. Import observations below to start learning." : feature === "anomalies" ? "No anomalies detected in the available telemetry. Baselines need 20 earlier observations." : "No forecast available. Collect at least five scored observations within 24 hours after baseline learning."}</div>}
        <article className="module-card advanced-import"><h2>Import telemetry</h2><p>Submit equal-duration measurements for each entity and metric. Event IDs make retries safe.</p><form className="stacked-form" onSubmit={ingest}><label>Telemetry JSON<textarea required rows={7} value={input} onChange={e => setInput(e.target.value)} placeholder={'{"events":[{"id":"event-001","entity":"server-01","metric":"failed_logins","value":2,"observed_at":"2026-09-14T08:00:00Z"}]}'}/></label><small>Metrics: failed_logins, outbound_bytes, dns_requests, process_count. Maximum 500 events per batch. Optional location: latitude, longitude, name and source; use only collector-reported coordinates.</small><button disabled={working}>{working ? "Importing…" : "Import and analyze"}</button></form></article>
      </>}
      {feature === "marketplace" && catalog && <><div className="advanced-info"><Shield size={20}/><p>Curated local extensions · no external network access · changes require a tenant administrator.</p></div><div className="module-form"><input aria-label="Search plugins" placeholder="Search plugins…" value={query} onChange={e => setQuery(e.target.value)}/></div><div className="advanced-results">{catalog.plugins.filter(p => `${p.name} ${p.category}`.toLowerCase().includes(query.toLowerCase())).map(plugin => <article className="module-card" key={plugin.id}><div className="advanced-row"><Package size={24}/><span className="status-pill">{plugin.installed ? plugin.enabled ? "Enabled" : "Disabled" : "Available"}</span></div><h2>{plugin.name}</h2><small>DarkTrace X · v{plugin.version} · {plugin.category}</small><p>{plugin.description}</p><div className="tag-list">{plugin.scopes.map(scope => <span key={scope}>{scope}</span>)}</div><div className="advanced-actions"><button disabled={working || !catalog.can_manage} onClick={() => void action(async () => { await api(apiBase, `/marketplace/${plugin.id}`, "PUT", { enabled: !plugin.enabled }); refresh(); })}>{plugin.installed ? plugin.enabled ? "Disable" : "Enable" : "Install"}</button>{plugin.installed && <button disabled={working || !catalog.can_manage} onClick={() => void action(async () => { await api(apiBase, `/marketplace/${plugin.id}`, "DELETE"); refresh(); })}>Uninstall</button>}<button disabled={working || !plugin.enabled || !catalog.can_run} onClick={() => void action(async () => { setOutput(await api(apiBase, `/marketplace/${plugin.id}/run`, "POST")); })}>Run</button></div></article>)}</div>{!catalog.can_manage && <p className="selection-hint">Sign in as your tenant administrator to install, enable, or remove extensions.</p>}</>}
      {feature === "mcp" && servers && servers.servers.map(server => <article className="module-card" key={server.id}><div className="module-card-heading"><Server size={24}/><div><h2>{server.name}</h2><p>Streamable HTTP · {server.protocol} · {server.authentication}</p></div></div><div className="advanced-info"><code>{apiBase || window.location.origin}{server.endpoint}</code></div><p>Use this URL in a compatible MCP client and supply your DarkTrace X access token through its secure authentication settings.</p><div className="advanced-results">{server.tools.map(tool => <div className="advanced-tool" key={tool.name}><Shield size={18}/><h2>{tool.name}</h2><p>{tool.description}</p><span className="status-pill">Read only</span><button disabled={working} onClick={() => void action(async () => { const result = await api<{result?: unknown; error?: {message: string}}>(apiBase, "/mcp", "POST", {jsonrpc: "2.0", id: Date.now(), method: "tools/call", params: {name: tool.name, arguments: {}}}); if (result.error) throw new Error(result.error.message); setOutput(result.result); })}>Test tool</button></div>)}</div></article>)}
      {output !== null && <article className="module-card advanced-import"><h2>Execution result</h2><pre className="advanced-output">{JSON.stringify(output, null, 2)}</pre></article>}
    </>}
  </div>;
}
