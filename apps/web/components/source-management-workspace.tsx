"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { apiRequest } from "../lib/api";

type Source = {
  id: string; name: string; url: string; source_type: string; category: string; description: string;
  crawl_policy: string; frequency_minutes: number; priority: number; trust_level: string; parser_type: string;
  tags: string[]; tenant_id: string; canonical_url: string; enabled: boolean; health: string; robots_status: string;
  last_checked_at?: string | null; last_crawled_at?: string | null; last_success_at?: string | null;
  last_failed_at?: string | null; failure_count: number; last_error?: string | null; created_at: string; updated_at: string;
};
type Crawl = { id: string; source_id: string; status: string; started_at: string; finished_at?: string | null; pages_successful: number; pages_failed: number; records_extracted: number; duplicates_found: number; error?: string | null };
type Draft = { name: string; url: string; source_type: string; category: string; description: string; crawl_policy: string; frequency_minutes: string; priority: string; trust_level: string; parser_type: string; tags: string };

const emptyDraft: Draft = { name: "", url: "", source_type: "public_threat_intel", category: "public threat intelligence", description: "", crawl_policy: "manual", frequency_minutes: "0", priority: "50", trust_level: "medium", parser_type: "html", tags: "" };

export function SourceManagementWorkspace({ apiBase }: { apiBase: string }) {
  const [sources, setSources] = useState<Source[]>([]);
  const [selected, setSelected] = useState<Source | null>(null);
  const [history, setHistory] = useState<Crawl[]>([]);
  const [draft, setDraft] = useState<Draft>(emptyDraft);
  const [role, setRole] = useState("viewer");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const [items, me] = await Promise.all([apiRequest<Source[]>(apiBase, "/sources"), apiRequest<{role: string}>(apiBase, "/auth/me")]);
      setSources(items); setRole(me.role);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to load sources"); }
    finally { setLoading(false); }
  }, [apiBase]);
  useEffect(() => { void load(); }, [load]);

  function edit(source: Source) {
    setSelected(source);
    setDraft({ name: source.name, url: source.url, source_type: source.source_type, category: source.category, description: source.description, crawl_policy: source.crawl_policy, frequency_minutes: String(source.frequency_minutes), priority: String(source.priority), trust_level: source.trust_level, parser_type: source.parser_type, tags: source.tags.join(", ") });
    setHistory([]);
    void apiRequest<Crawl[]>(apiBase, `/sources/${source.id}/crawls`).then(setHistory).catch((reason) => setError(reason instanceof Error ? reason.message : "Unable to load crawl history"));
  }
  function change(key: keyof Draft, value: string) { setDraft(current => ({ ...current, [key]: value })); }
  async function save(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(""); setNotice("");
    const body = { ...draft, frequency_minutes: Number(draft.frequency_minutes), priority: Number(draft.priority), tags: draft.tags.split(",").map(tag => tag.trim()).filter(Boolean) };
    try { await apiRequest<Source>(apiBase, selected ? `/sources/${selected.id}` : "/sources", { method: selected ? "PUT" : "POST", body: JSON.stringify(body) }); setDraft(emptyDraft); setSelected(null); setNotice(selected ? "Source updated." : "Source added."); await load(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Source could not be saved"); }
    finally { setBusy(false); }
  }
  async function action(source: Source, path: string, method = "POST") {
    setBusy(true); setError(""); setNotice("");
    try { const result = await apiRequest<Source | {valid: boolean; reason?: string | null}>(apiBase, `/sources/${source.id}/${path}`, { method }); setNotice(path === "validate" ? ((result as {valid: boolean; reason?: string | null}).valid ? "Source validation passed." : `Validation failed: ${(result as {reason?: string | null}).reason ?? "unknown reason"}`) : `${path.replaceAll("-", " ")} completed.`); await load(); if (selected?.id === source.id) { const current = (result as Source); if (current.id) setSelected(current); } }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Source action failed"); }
    finally { setBusy(false); }
  }
  async function crawl(source: Source) {
    setBusy(true); setError(""); setNotice("");
    try { const result = await apiRequest<{job: Crawl}>(apiBase, `/sources/${source.id}/crawl`, { method: "POST" }); setNotice(`Crawl ${result.job.status}. ${result.job.records_extracted} document(s) processed.`); edit(source); await load(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Crawl failed"); }
    finally { setBusy(false); }
  }
  async function archive(source: Source) {
    if (!window.confirm(`Archive source "${source.name}"? Its history is retained.`)) return;
    setBusy(true); setError(""); setNotice("");
    try { await apiRequest<void>(apiBase, `/sources/${source.id}`, { method: "DELETE" }); setNotice("Source archived; crawl history retained."); setSelected(null); await load(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Source could not be archived"); }
    finally { setBusy(false); }
  }
  const canManage = role === "lead" || role === "admin";
  const canCrawl = canManage || role === "analyst";
  const visible = sources.filter(source => `${source.name} ${source.url} ${source.category} ${source.health}`.toLowerCase().includes(query.toLowerCase()));
  const input = (label: string, key: keyof Draft, type = "text") => <label>{label}<input required={key !== "description" && key !== "tags"} type={type} value={draft[key]} onChange={event => change(key, event.target.value)} /></label>;
  return <div className="advanced-workspace"><section className="module-header"><p>SOURCE DISCOVERY · M2 CRAWLING P1</p><h1>Source management</h1><span>Manage approved public and licensed intelligence sources, validate connectivity, run crawls, and trace collected evidence.</span></section>{error && <div className="module-notice error" role="alert">{error}</div>}{notice && <div className="module-notice success" role="status">{notice}</div>}
    {canManage && <article className="module-card"><h2>{selected ? "Edit source" : "Add source"}</h2><form className="stacked-form" onSubmit={save}><div className="form-split">{input("Name", "name")}{input("URL", "url", "url")}{input("Category", "category")}{input("Description", "description")}{input("Frequency (minutes, 0 for manual)", "frequency_minutes", "number")}{input("Priority (0-100)", "priority", "number")}{input("Tags, comma separated", "tags")}{<label>Source type<select value={draft.source_type} onChange={event => change("source_type", event.target.value)}>{["public_threat_intel", "security_blog", "vendor_advisory", "cert_feed", "osint_feed", "rss", "licensed_monitoring", "custom"].map(value => <option key={value}>{value}</option>)}</select></label>}{<label>Crawl policy<select value={draft.crawl_policy} onChange={event => change("crawl_policy", event.target.value)}>{["manual", "hourly", "daily", "weekly", "custom"].map(value => <option key={value}>{value}</option>)}</select></label>}{<label>Parser<select value={draft.parser_type} onChange={event => change("parser_type", event.target.value)}>{["html", "rss", "atom", "json", "text"].map(value => <option key={value}>{value}</option>)}</select></label>}</div><div className="advanced-actions"><button disabled={busy}>{busy ? "Saving…" : selected ? "Update source" : "Add source"}</button>{selected && <button type="button" onClick={() => { setSelected(null); setDraft(emptyDraft); }}>Cancel</button>}</div></form></article>}
    <article className="module-card"><div className="module-form"><input aria-label="Search sources" placeholder="Search sources…" value={query} onChange={event => setQuery(event.target.value)} /><button type="button" disabled={loading} onClick={() => void load()}>Refresh</button></div>{loading ? <div className="module-loading">Loading sources…</div> : visible.length === 0 ? <div className="empty-state">No sources found. Add an approved source to begin.</div> : <div className="advanced-results">{visible.map(source => <article className="advanced-tool" key={source.id}><div className="advanced-row"><h2>{source.name}</h2><span className={`status-pill ${source.health.toLowerCase()}`}>{source.health}</span></div><p>{source.url}</p><p>{source.source_type} · {source.crawl_policy} · {source.enabled ? "Enabled" : "Disabled"} · {source.failure_count} recent failure(s)</p>{source.last_error && <p role="alert">Last error: {source.last_error}</p>}<div className="advanced-actions"><button disabled={!canCrawl || busy} onClick={() => void action(source, "validate")}>Test source</button><button disabled={!canCrawl || busy || !source.enabled} onClick={() => void crawl(source)}>Crawl now</button>{canManage && <><button disabled={busy} onClick={() => edit(source)}>Edit</button><button disabled={busy} onClick={() => void action(source, source.enabled ? "disable" : "enable")}>{source.enabled ? "Disable" : "Enable"}</button><button disabled={busy} onClick={() => void archive(source)}>Archive</button></>}</div><details onToggle={event => { if ((event.target as HTMLDetailsElement).open) edit(source); }}><summary>View details and crawl history</summary>{selected?.id === source.id && <div>{history.length ? history.map(job => <div className="data-row" key={job.id}><strong>{job.status}</strong><span>{job.records_extracted} records · {job.duplicates_found} duplicates</span><time>{new Date(job.started_at).toLocaleString()}</time></div>) : <p>No crawl history.</p>}</div>}</details></article>)}</div>}</article>
  </div>;
}
