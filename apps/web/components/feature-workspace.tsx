"use client";
import { apiFetch } from "../lib/api";



import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from "react";

import {

  Bot, BrainCircuit, CheckCircle2, CircleAlert, Download, FileDown, GitBranch,

  LoaderCircle, Play, Plus, Radar, RefreshCw,

  ShieldAlert, SlidersHorizontal, Sparkles, SquareTerminal

} from "lucide-react";



import { OperationsWorkspace } from "./operations-workspace";
import { SourceManagementWorkspace } from "./source-management-workspace";
import { ProcessingWorkspace, type ProcessingFeature } from "./processing-workspace";

import { IntelligenceGraph } from "./intelligence-graph";

import { AdvancedWorkspace, type AdvancedFeature } from "./advanced-workspace";

export type FeatureKey = "administration" | AdvancedFeature | "overview" | "intelligence" | "hunt" | "exposure" | "sources" | "documents" | "entities" | "events" | "crawls" | "assets" | "graph" | "cves" | "actors" | "alerts" | "aiStudio" | "automations" | "reports" | "settings";



type Props = { feature: Exclude<FeatureKey, "overview">; apiBase: string };

type FetchState<T> = { data: T; loading: boolean; error: string | null };

type Provider = { id: string; configured: boolean; default_model: string };

type Automation = { id: string; name: string; trigger: string; provider: string; model?: string | null; instruction: string; enabled: boolean; last_run_at?: string | null };



const featureMeta: Record<Exclude<FeatureKey, "overview" | "administration" | AdvancedFeature>, { eyebrow: string; title: string; description: string }> = {

  intelligence: { eyebrow: "IOC & REPUTATION", title: "Threat intelligence workbench", description: "Validate indicators against tenant correlation data and preserve source-aware analyst context." },

  hunt: { eyebrow: "HYPOTHESIS-DRIVEN", title: "Threat hunting", description: "Run scoped, defensible hunts against intelligence that belongs to your workspace." },

  exposure: { eyebrow: "APPROVED SOURCES", title: "Exposure watch", description: "Review brand, domain, and organization mentions from permitted and licensed intelligence sources." },
  sources: { eyebrow: "SOURCE DISCOVERY", title: "Source management", description: "Validate, monitor, crawl, and audit approved public or licensed intelligence sources." },
  documents: { eyebrow: "THREAT PROCESSING", title: "Collected documents", description: "Inspect normalized source content and preserve crawl provenance." },
  entities: { eyebrow: "THREAT PROCESSING", title: "Extracted entities", description: "Search deterministic entities with confidence and observation timing." },
  events: { eyebrow: "THREAT PROCESSING", title: "Threat events", description: "Review evidence-backed detections produced by the processing pipeline." },
  crawls: { eyebrow: "SOURCE OPERATIONS", title: "Crawl jobs", description: "Monitor crawl status, output counts, duplicates, and errors." },

  assets: { eyebrow: "ATTACK SURFACE", title: "Asset discovery", description: "Prioritize owned assets by exposure, service footprint, and correlated risk." },

    graph: { eyebrow: "RELATIONSHIPS", title: "Intelligence graph", description: "Explore correlations across assets, actors, observables, and ATT&CK techniques." },

    cves: { eyebrow: "EXPLOITED VULNERABILITIES", title: "CVE dashboard", description: "Review current CISA KEV records that have actually been ingested into your tenant workspace." },

    actors: { eyebrow: "EVIDENCE-BASED ATTRIBUTION", title: "Threat actor profiles", description: "Profiles require traceable approved-source references; the platform does not invent attribution." },

  alerts: { eyebrow: "DETECTION CONTROL", title: "Alert center", description: "Review the queue and define governed correlation rules for your response teams." },

  aiStudio: { eyebrow: "MODEL CONTROL PLANE", title: "AI SOC Studio", description: "Select a cloud or offline model, inspect local runtimes, and ask source-aware defensive questions." },

  automations: { eyebrow: "HUMAN-GOVERNED", title: "AI automations", description: "Create manual or event-triggered AI playbooks. Generated output never performs external side effects automatically." },

  reports: { eyebrow: "EVIDENCE EXPORT", title: "Reporting center", description: "Generate PDF, DOCX, or XLSX intelligence exports from tenant-scoped evidence." },

  settings: { eyebrow: "RUNTIME CONFIGURATION", title: "Platform settings", description: "Inspect provider readiness and connect approved model runtimes without exposing secrets in the browser." }

};



function apiPath(apiBase: string, path: string) {

  return `${apiBase}${path}`;

}



async function requestJson<T>(apiBase: string, path: string, init?: RequestInit): Promise<T> {


  const response = await apiFetch(apiPath(apiBase, path), { ...init, headers: { "Content-Type": "application/json",  ...(init?.headers ?? {}) } });

  const payload = await response.json().catch(() => ({}));

  if (!response.ok) throw new Error(typeof payload.detail === "string" ? payload.detail : payload.detail?.message ?? "The service could not complete this request.");

  return payload as T;

}



function useResource<T>(apiBase: string, path: string, initial: T) {

  const [state, setState] = useState<FetchState<T>>({ data: initial, loading: true, error: null });

  const refresh = () => {

    setState((current) => ({ ...current, loading: true, error: null }));

    requestJson<T>(apiBase, path).then((data) => setState({ data, loading: false, error: null })).catch((error: Error) => setState((current) => ({ ...current, loading: false, error: error.message })));

  };

  useEffect(refresh, [apiBase, path]);

  return { ...state, refresh };

}



function WorkspaceHeader({ feature }: { feature: Exclude<FeatureKey, "overview" | "administration" | AdvancedFeature> }) {

  const meta = featureMeta[feature];

  return <section className="module-header"><p>{meta.eyebrow}</p><h1>{meta.title}</h1><span>{meta.description}</span></section>;

}



function Loading({ label = "Loading workspace data…" }: { label?: string }) {

  return <div className="module-loading"><LoaderCircle size={18} className="spin" /> {label}</div>;

}



function ErrorNotice({ message }: { message: string }) {

  return <div className="module-notice error"><CircleAlert size={16} /> {message}</div>;

}



function StatusPill({ value }: { value: string | boolean }) {

  const status = String(value).toLowerCase();

  return <span className={`status-pill ${status}`}>{typeof value === "boolean" ? (value ? "configured" : "not configured") : value}</span>;

}



function Hunt({ apiBase }: { apiBase: string }) {

  const [hypothesis, setHypothesis] = useState("Loader infrastructure may overlap with our telemetry");

  const [query, setQuery] = useState("loader");

  const [result, setResult] = useState<Record<string, unknown> | null>(null);

  const [working, setWorking] = useState(false);

  async function run(event: FormEvent) { event.preventDefault(); setWorking(true); try { setResult(await requestJson(apiBase, "/api/v1/hunts", { method: "POST", body: JSON.stringify({ hypothesis, query, time_range_hours: 24 }) })); } catch (error) { setResult({ error: error instanceof Error ? error.message : "Hunt failed" }); } finally { setWorking(false); } }

  return <><WorkspaceHeader feature="hunt" /><article className="module-card hunt-card"><div className="module-card-heading"><Radar size={18} /><div><h2>New hypothesis hunt</h2><p>Queries only local, tenant-scoped intelligence in this runtime.</p></div></div><form className="stacked-form" onSubmit={run}><label>Hypothesis<textarea value={hypothesis} onChange={(event) => setHypothesis(event.target.value)} /></label><label>Correlation query<input value={query} onChange={(event) => setQuery(event.target.value)} /></label><button disabled={working}><Play size={15} /> {working ? "Running hunt…" : "Run defensive hunt"}</button></form>{result && <div className="result-panel">{"error" in result ? <ErrorNotice message={String(result.error)} /> : <><div><StatusPill value={String(result.status)} /><strong>{String(result.findings)} finding(s)</strong></div><p>{String(result.recommended_next_step)}</p><div className="tag-list">{Array.isArray(result.matching_indicators) && (result.matching_indicators as Record<string, unknown>[]).map((ioc) => <span key={String(ioc.id)}>{String(ioc.type)} · {String(ioc.value)}</span>)}</div></>}</div>}</article></>;

}



function CVEs({ apiBase }: { apiBase: string }) {

  const { data, loading, error, refresh } = useResource<Record<string, unknown>[]>(apiBase, "/api/v1/cve/dashboard", []);

  return <><WorkspaceHeader feature="cves" /><article className="module-card"><div className="module-card-heading"><ShieldAlert size={18} /><div><h2>CISA KEV intelligence</h2><p>Only records ingested from the approved public feed are displayed.</p></div><button className="table-refresh" onClick={refresh} aria-label="Refresh CVE dashboard"><RefreshCw size={14} /></button></div>{loading ? <Loading /> : error ? <ErrorNotice message={error} /> : <div className="data-table">{data.length ? data.map((item) => <div className="alert-row" key={String(item.id)}><StatusPill value={String(item.severity)} /><div><strong>{String(item.external_id)}</strong><span>{String(item.title)}</span></div><b>CISA KEV</b></div>) : <div className="empty-state">No CVEs ingested. Use Exposure Watch → Ingest CISA KEV.</div>}</div>}</article></>;

}



function Actors({ apiBase }: { apiBase: string }) {

  const profiles = useResource<Record<string, unknown>[]>(apiBase, "/api/v1/threat-actors/verified", []);

  const [name, setName] = useState(""); const [summary, setSummary] = useState(""); const [sources, setSources] = useState(""); const [notice, setNotice] = useState(""); const [working, setWorking] = useState(false);

  async function create(event: FormEvent) { event.preventDefault(); setWorking(true); setNotice(""); try { await requestJson(apiBase, "/api/v1/threat-actors", { method: "POST", body: JSON.stringify({ name, summary, sources: sources.split(",").map((item) => item.trim()).filter(Boolean) }) }); setName(""); setSummary(""); setSources(""); profiles.refresh(); setNotice("Profile indexed with its evidence references."); } catch (reason) { setNotice(reason instanceof Error ? reason.message : "Profile could not be indexed"); } finally { setWorking(false); } }

  return <><WorkspaceHeader feature="actors" /><div className="module-grid two"><article className="module-card"><div className="module-card-heading"><GitBranch size={18} /><div><h2>Verified profiles</h2><p>Analyst-owned intelligence with source references.</p></div></div>{profiles.loading ? <Loading /> : profiles.error ? <ErrorNotice message={profiles.error} /> : <div className="mention-list">{profiles.data.length ? profiles.data.map((item) => <div className="mention-card" key={String(item.id)}><div><StatusPill value="evidence backed" /><h2>{String(item.name)}</h2><p>{String(item.summary)}</p></div><aside><strong>Sources</strong><span>{Array.isArray(item.sources) ? item.sources.join(", ") : "—"}</span></aside></div>) : <div className="empty-state">No profiles are indexed yet.</div>}</div>}</article><article className="module-card"><div className="module-card-heading"><Plus size={18} /><div><h2>Index analyst profile</h2><p>Provide an approved report or evidence source.</p></div></div><form className="stacked-form" onSubmit={create}><label>Profile name<input required value={name} onChange={(event) => setName(event.target.value)} /></label><label>Evidence-based summary<textarea required value={summary} onChange={(event) => setSummary(event.target.value)} /></label><label>Sources (comma-separated)<input required value={sources} onChange={(event) => setSources(event.target.value)} placeholder="Approved report URL or internal case ID" /></label><button disabled={working}>{working ? "Indexing…" : "Create profile"}</button></form>{notice && <div className="module-notice success"><CheckCircle2 size={16} /> {notice}</div>}</article></div></>;

}



function AIStudio({ apiBase }: { apiBase: string }) {

  const { data, loading, error } = useResource<{ default: string; providers: Provider[] }>(apiBase, "/api/v1/ai/providers", { default: "local", providers: [] });

  const [mode, setMode] = useState<"online" | "offline" | "automation">("offline");

  const [provider, setProvider] = useState("local");

  const [model, setModel] = useState("");

  const [question, setQuestion] = useState("Summarize the current defensive posture and suggest safe analyst checks.");

  const [answer, setAnswer] = useState("");

  const [scans, setScans] = useState<Record<string, unknown>[]>([]);

  const [working, setWorking] = useState(false);

  const [modelFile, setModelFile] = useState<{ name: string; size: number; format: string } | null>(null);

  useEffect(() => { if (!model && data.providers.length) { const selected = data.providers.find((item) => item.id === provider) ?? data.providers[0]; setProvider(selected.id); setModel(selected.default_model); } }, [data, model, provider]);

  const discoveredModels = useMemo(() => scans.flatMap((scan) => Array.isArray(scan.models) ? (scan.models as string[]).map((name) => ({ provider: String(scan.provider), name })) : []), [scans]);

  async function scan() { setWorking(true); try { setScans(await requestJson<Record<string, unknown>[]>(apiBase, "/api/v1/ai/models/scan")); } catch (error) { setAnswer(error instanceof Error ? error.message : "Local scan failed"); } finally { setWorking(false); } }

  function selectModelFile(event: ChangeEvent<HTMLInputElement>) {

    const file = event.currentTarget.files?.[0];

    if (!file) return;

    const format = file.name.includes(".") ? file.name.slice(file.name.lastIndexOf(".")).toLowerCase() : "";

    if (![".gguf", ".ggml", ".bin", ".safetensors", ".onnx"].includes(format)) {

      setModelFile(null);

      setAnswer("Choose a supported local model file: GGUF, GGML, BIN, SafeTensors, or ONNX.");

      return;

    }

    setAnswer("");

    setModelFile({ name: file.name, size: file.size, format: format.slice(1).toUpperCase() });

  }

  async function chat(event: FormEvent) { event.preventDefault(); setWorking(true); setAnswer(""); try { const result = await requestJson<Record<string, unknown>>(apiBase, "/api/v1/ai/chat", { method: "POST", body: JSON.stringify({ message: question, provider, model: model || undefined, language: "en" }) }); setAnswer(String(result.message)); } catch (error) { setAnswer(error instanceof Error ? error.message : "AI request failed"); } finally { setWorking(false); } }

    async function automate(event: FormEvent) { event.preventDefault(); setWorking(true); setAnswer(""); try { const playbook = await requestJson<Automation>(apiBase, "/api/v1/automations", { method: "POST", body: JSON.stringify({ name: `AI Studio task · ${new Date().toLocaleTimeString()}`, trigger: "manual", provider, model: model || undefined, instruction: "Produce a concise defensive analyst task result from the supplied approved context. State evidence, uncertainty, and safe validation steps. Do not perform external actions." }) }); const result = await requestJson<Record<string, unknown>>(apiBase, `/api/v1/automations/${playbook.id}/run`, { method: "POST", body: JSON.stringify({ context: { analyst_task: question, source: "AI Studio manual automation" } }) }); setAnswer(String(result.output)); } catch (reason) { setAnswer(reason instanceof Error ? reason.message : "Automation failed"); } finally { setWorking(false); } }

    const onlineProviders = data.providers.filter((item) => item.id === "external");

    const localProviders = data.providers.filter((item) => item.id === "local");

    const selectProvider = (item: Provider) => { setProvider(item.id); setModel(item.default_model); };

    const selectorTitle = mode === "online" ? "Online model selector" : mode === "offline" ? "Offline model selector" : "Automation model selector";

    const selectorDescription = mode === "online"

      ? "Use server-side API keys; keys never enter the browser."

      : mode === "offline"

        ? "Scan models you downloaded and started on your own computer."

        : "Select a local runtime, then run a governed AI task.";

    return (

      <>

        <WorkspaceHeader feature="aiStudio" />

        <div className="ai-mode-tabs">

          <button className={mode === "online" ? "active" : ""} onClick={() => { setMode("online"); selectProvider(data.providers.find((item) => item.id === "external") ?? { id: "external", configured: false, default_model: "" }); }}><Sparkles size={15} /> External AI</button>

          <button className={mode === "offline" ? "active" : ""} onClick={() => { setMode("offline"); selectProvider(data.providers.find((item) => item.id === "local") ?? { id: "local", configured: false, default_model: "" }); }}><SquareTerminal size={15} /> Local Qwen</button>

          <button className={mode === "automation" ? "active" : ""} onClick={() => { setMode("automation"); selectProvider(data.providers.find((item) => item.id === "local") ?? { id: "local", configured: false, default_model: "" }); }}><Play size={15} /> Local automation</button>

        </div>

        <div className="module-grid ai-grid">

          <article className="module-card">

            <div className="module-card-heading">

              <BrainCircuit size={18} />

              <div><h2>{selectorTitle}</h2><p>{selectorDescription}</p></div>

              {mode !== "online" && <button className="table-refresh" onClick={scan} disabled={working} aria-label="Scan local models"><RefreshCw size={14} /></button>}

            </div>

            {loading ? <Loading /> : error ? <ErrorNotice message={error} /> : (

              <>

                {mode === "online" && (

                  <>

                    <div className="provider-grid">{onlineProviders.map((item) => (

                      <button key={item.id} className={`provider-choice ${provider === item.id ? "selected" : ""}`} onClick={() => selectProvider(item)}><Bot size={15} /><span>{item.id.replace("_", " ")}</span><StatusPill value={item.configured} /></button>

                    ))}</div>

                    <p className="selection-hint">Add provider keys only in server environment or your managed secret store, then restart the API.</p>

                  </>

                )}

                {mode !== "online" && (

                  <>

                    <div className="provider-grid">{localProviders.map((item) => (

                      <button key={item.id} className={`provider-choice ${provider === item.id ? "selected" : ""}`} onClick={() => selectProvider(item)}><Bot size={15} /><span>{item.id.replace("_", " ")}</span><StatusPill value={item.configured} /></button>

                    ))}</div>

                    <div className="local-runtimes">

                      {scans.length ? scans.map((scan) => <div key={String(scan.provider)}><StatusPill value={Boolean(scan.reachable)} /><strong>{String(scan.provider)}</strong><span>{String(scan.detail)}</span></div>) : <div><strong>Qwen runtime</strong><span>The bundled local model is managed by the DarkTrace worker.</span></div>}

                    </div>

                    {mode === "offline" && <div className="model-file-picker">

                      <label htmlFor="local-model-file"><span>Choose model file</span><input id="local-model-file" type="file" accept=".gguf,.ggml,.bin,.safetensors,.onnx" onChange={selectModelFile} /></label>

                      {modelFile ? <div className="selected-model-file"><strong>{modelFile.name}</strong><span>{modelFile.format} · {(modelFile.size / 1024 / 1024).toFixed(1)} MB</span><p>Selected locally. Load it in LM Studio or import it into Ollama, then select Scan to use the running model.</p></div> : <p className="selection-hint">Select a GGUF, GGML, BIN, SafeTensors, or ONNX model from your file manager. The file remains on your device.</p>}

                    </div>}

                  </>

                )}

                <label className="inline-label">Selected model

                  <select value={model} onChange={(event) => setModel(event.target.value)}>

                    <option value="">Provider default</option>

                    {data.providers.filter((item) => item.id === provider).map((item) => <option value={item.default_model} key={item.default_model}>{item.default_model}</option>)}

                    {discoveredModels.filter((item) => item.provider === provider).map((item) => <option value={item.name} key={item.name}>{item.name}</option>)}

                  </select>

                </label>

              </>

            )}

          </article>

          <article className="module-card ai-chat-card">

            <div className="module-card-heading"><Sparkles size={18} /><div><h2>{mode === "automation" ? "Run governed task" : "Ask selected model"}</h2><p>{mode === "automation" ? "Creates a reviewable draft only; it never performs external actions." : "Defensive analysis only; every answer is labeled by provider."}</p></div></div>

            <form className="stacked-form" onSubmit={mode === "automation" ? automate : chat}>

              <textarea value={question} onChange={(event) => setQuestion(event.target.value)} />

              <button disabled={working || !provider}>{working ? "Generating…" : mode === "automation" ? `Automate with ${provider}` : `Run ${provider}`}</button>

            </form>

            {answer && <div className="ai-output"><SquareTerminal size={16} /><pre>{answer}</pre></div>}

          </article>

        </div>

      </>

    );

  }



function Automations({ apiBase }: { apiBase: string }) {

  const { data, loading, error, refresh } = useResource<Automation[]>(apiBase, "/api/v1/automations", []);

  const [output, setOutput] = useState(""); const [working, setWorking] = useState<string | null>(null);

  const [provider, setProvider] = useState("lm_studio"); const [model, setModel] = useState("");

  const [name, setName] = useState("Local analyst brief");

  const [instruction, setInstruction] = useState("Create a concise defensive triage brief. State evidence, uncertainty, safe validation steps, and escalation priority. Do not take external actions.");

  async function run(item: Automation) { setWorking(item.id); setOutput(""); try { const result = await requestJson<Record<string, unknown>>(apiBase, `/api/v1/automations/${item.id}/run`, { method: "POST", body: JSON.stringify({ context: { analyst_instruction: item.instruction } }) }); setOutput(String(result.output)); refresh(); } catch (error) { setOutput(error instanceof Error ? error.message : "Automation failed"); } finally { setWorking(null); } }

  async function create(event: FormEvent) { event.preventDefault(); setWorking("create"); setOutput(""); try { await requestJson(apiBase, "/api/v1/automations", { method: "POST", body: JSON.stringify({ name, trigger: "manual", provider, model: model || undefined, instruction }) }); refresh(); setOutput("Playbook created. Run it from the list after reviewing its configuration."); } catch (error) { setOutput(error instanceof Error ? error.message : "Playbook creation failed"); } finally { setWorking(null); } }

  return <><WorkspaceHeader feature="automations" /><div className="module-grid two"><article className="module-card"><div className="module-card-heading"><Play size={18} /><div><h2>Playbooks</h2><p>Run manually or attach an approved event trigger.</p></div></div>{loading ? <Loading /> : error ? <ErrorNotice message={error} /> : <div className="automation-list">{data.map((item) => <div className="automation-row" key={item.id}><div><StatusPill value={item.enabled} /><h2>{item.name}</h2><p>{item.trigger} · {item.provider}{item.model ? ` · ${item.model}` : ""}</p></div><button onClick={() => run(item)} disabled={working !== null}>{working === item.id ? "Running…" : "Run"}</button></div>)}</div>}<form className="stacked-form automation-create" onSubmit={create}><h2>New governed playbook</h2><label>Name<input value={name} onChange={(event) => setName(event.target.value)} /></label><div className="form-split"><label>Provider<select value={provider} onChange={(event) => setProvider(event.target.value)}><option value="lm_studio">LM Studio (local)</option><option value="ollama">Ollama (local)</option><option value="vllm">vLLM (local)</option><option value="llama_cpp">llama.cpp (local)</option><option value="openai">OpenAI</option><option value="gemini">Google Gemini</option><option value="anthropic">Anthropic Claude</option><option value="groq">Groq</option><option value="openrouter">OpenRouter</option><option value="custom">Custom endpoint</option></select></label><label>Model <input value={model} placeholder="Optional provider default" onChange={(event) => setModel(event.target.value)} /></label></div><label>Defensive instruction<textarea value={instruction} onChange={(event) => setInstruction(event.target.value)} /></label><button disabled={working !== null}>{working === "create" ? "Creating…" : "Create playbook"}</button></form></article><article className="module-card"><div className="module-card-heading"><SquareTerminal size={18} /><div><h2>Automation output</h2><p>Generated text requires analyst review before action.</p></div></div>{output ? <div className="ai-output"><pre>{output}</pre></div> : <div className="empty-state">Choose a playbook, then run it with your configured instruction.</div>}</article></div></>;

}



function Reports({ apiBase }: { apiBase: string }) {

  const [working, setWorking] = useState<string | null>(null); const [notice, setNotice] = useState("");

  async function download(format: "pdf" | "docx" | "xlsx") { setWorking(format); setNotice(""); try { const response = await apiFetch(apiPath(apiBase, `/api/v1/reports/${format}`), { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ title: "DarkTrace X Intelligence Brief" }) }); if (!response.ok) throw new Error("Report export failed"); const blob = await response.blob(); const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = `darktracex-brief.${format}`; link.click(); URL.revokeObjectURL(url); setNotice(`${format.toUpperCase()} report generated.`); } catch (error) { setNotice(error instanceof Error ? error.message : "Report export failed"); } finally { setWorking(null); } }

  return <><WorkspaceHeader feature="reports" /><article className="module-card report-card"><div className="report-visual"><FileDown size={34} /><span>INTEL<br/>BRIEF</span></div><div><h2>Export a defensible intelligence brief</h2><p>Every export is generated from tenant-scoped alert evidence, selected indicators, and current CVE intelligence.</p><div className="report-actions">{(["pdf", "docx", "xlsx"] as const).map((format) => <button key={format} onClick={() => download(format)} disabled={working !== null}><Download size={15} /> {working === format ? "Preparing…" : format.toUpperCase()}</button>)}</div>{notice && <div className="module-notice success"><CheckCircle2 size={16} /> {notice}</div>}</div></article></>;

}



function Settings({ apiBase }: { apiBase: string }) {

  const { data, loading, error } = useResource<{ default: string; providers: Provider[] }>(apiBase, "/api/v1/ai/providers", { default: "local", providers: [] });

    return <><WorkspaceHeader feature="settings" /><button onClick={()=>window.dispatchEvent(new Event("darktrace:ai-settings"))}>AI Models · Copilot settings</button><div className="module-grid two"><article className="module-card"><div className="module-card-heading"><SlidersHorizontal size={18} /><div><h2>AI readiness</h2><p>Local Qwen is primary. External AI is optional and server-configured.</p></div></div>{loading ? <Loading /> : error ? <ErrorNotice message={error} /> : <div className="provider-status-list">{data.providers.map((provider) => <div key={provider.id}><Bot size={15} /><strong>{provider.id === "local" ? "Local Qwen" : "External AI"}</strong><span>{provider.default_model}</span><StatusPill value={provider.configured} /></div>)}</div>}</article><article className="module-card"><div className="module-card-heading"><ShieldAlert size={18} /><div><h2>Safe configuration</h2><p>External keys remain server-side and are never returned to browser JavaScript.</p></div></div><div className="settings-copy"><p>Use <code>.env.local</code> for local development or a managed secret store in production.</p><p>External AI is never selected automatically and receives no prompts unless explicitly enabled.</p><p>Automations generate draft analysis only. Notifications, blocking actions, and exports require an authorized user or a separately approved integration.</p></div></article></div></>;

}



export function FeatureWorkspace({ feature, apiBase }: Props) {

  switch (feature) {

    case "administration": return <OperationsWorkspace feature={feature} apiBase={apiBase} />;

    case "anomalies": case "predictive": case "mcp": case "marketplace": return <AdvancedWorkspace key={feature} feature={feature} apiBase={apiBase} />;

    case "intelligence": return <OperationsWorkspace key={feature} feature={feature} apiBase={apiBase} />;

    case "hunt": return <Hunt apiBase={apiBase} />;

    case "exposure": return <OperationsWorkspace key={feature} feature={feature} apiBase={apiBase} />;

    case "sources": return <SourceManagementWorkspace apiBase={apiBase} />;
    case "documents": case "entities": case "events": case "crawls": return <ProcessingWorkspace feature={feature as ProcessingFeature} apiBase={apiBase} />;

    case "assets": return <OperationsWorkspace key={feature} feature={feature} apiBase={apiBase} />;

    case "graph": return <IntelligenceGraph apiBase={apiBase} />;

    case "cves": return <CVEs apiBase={apiBase} />;

    case "actors": return <Actors apiBase={apiBase} />;

    case "alerts": return <OperationsWorkspace key={feature} feature={feature} apiBase={apiBase} />;

    case "aiStudio": return <AIStudio apiBase={apiBase} />;

    case "automations": return <Automations apiBase={apiBase} />;

    case "reports": return <Reports apiBase={apiBase} />;

    case "settings": return <Settings apiBase={apiBase} />;

  }

}

