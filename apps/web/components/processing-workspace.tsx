"use client";

import { useCallback, useEffect, useState } from "react";
import { FileSearch, Network, RefreshCw, TriangleAlert, Workflow } from "lucide-react";
import { apiRequest } from "../lib/api";

export type ProcessingFeature = "documents" | "entities" | "events" | "crawls";
type DocumentRow = { id: string; source_id: string; crawl_id: string; canonical_url: string; title: string; content_hash: string; collected_at: string; normalized_text?: string | null };
type EntityRow = { id: string; entity_type: string; value: string; confidence: number; extraction_method: string; first_seen: string; last_seen: string };
type EventRow = { id: string; event_type: string; source_id: string; document_id: string; severity: string; confidence: number; reason: string; evidence: Record<string, unknown> };
type CrawlRow = { id: string; source_id: string; status: string; started_at: string; pages_failed: number; records_extracted: number; duplicates_found: number; error?: string | null; retry_count?:number; duration_ms?:number; finished_at?:string };

const meta: Record<ProcessingFeature, { title: string; description: string }> = {
  documents: { title: "Collected documents", description: "Inspect normalized source content and preserve crawl provenance." },
  entities: { title: "Extracted entities", description: "Search deterministic entities with confidence and observation timing." },
  events: { title: "Threat events", description: "Review evidence-backed detections produced by the processing pipeline." },
  crawls: { title: "Crawl jobs", description: "Monitor crawl status, output counts, duplicates, and errors." },
};

export function ProcessingWorkspace({ feature, apiBase }: { feature: ProcessingFeature; apiBase: string }) {
  const [rows, setRows] = useState<Array<DocumentRow | EntityRow | EventRow | CrawlRow>>([]);
  const [query, setQuery] = useState("");
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [details,setDetails]=useState<Record<string,{normalized_text:string;entities:unknown[];events:unknown[];alerts:unknown[]}>>({});

  const load = useCallback(async (nextOffset = 0, searchQuery = "") => {
    setLoading(true);
    setError("");
    try {
      const path = feature === "documents"
        ? `/documents?limit=50&offset=${nextOffset}`
        : feature === "entities"
          ? `/entities?limit=50&offset=${nextOffset}&q=${encodeURIComponent(searchQuery)}`
          : feature === "events"
            ? `/events?limit=50&offset=${nextOffset}`
            : `/crawls?limit=50&offset=${nextOffset}`;
      setRows(await apiRequest<Array<DocumentRow | EntityRow | EventRow | CrawlRow>>(apiBase, path));
      setOffset(nextOffset);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to load processing data");
    } finally {
      setLoading(false);
    }
  }, [feature, apiBase]);

  useEffect(() => { void load(0); }, [load]);

  const filtered = rows.filter(row => JSON.stringify(row).toLowerCase().includes(query.toLowerCase()));
  const Icon = feature === "documents" ? FileSearch : feature === "entities" ? Network : feature === "events" ? TriangleAlert : Workflow;

  function renderRow(row: DocumentRow | EntityRow | EventRow | CrawlRow) {
    if (feature === "documents") {
      const document = row as DocumentRow;
      return <><h2>{document.title}</h2><p>{document.canonical_url}</p><details onToggle={e=>{if(e.currentTarget.open&&!details[document.id])void apiRequest<{normalized_text:string;entities:unknown[];events:unknown[];alerts:unknown[]}>(apiBase,"/documents/"+document.id).then(data=>setDetails(old=>({...old,[document.id]:data}))).catch(error=>setError(String(error)));}}><summary>Read document and evidence</summary><p style={{whiteSpace:"pre-wrap"}}>{details[document.id]?.normalized_text || document.normalized_text || "Loading document…"}</p>{details[document.id]&&<pre className="advanced-output">{JSON.stringify({entities:details[document.id].entities,events:details[document.id].events,alerts:details[document.id].alerts},null,2)}</pre>}<a href={apiBase+"/api/v1/documents/"+document.id+"/raw"}>Download original source</a></details><p>Source {document.source_id} · Crawl {document.crawl_id}</p><small>Collected {new Date(document.collected_at).toLocaleString()} · hash {document.content_hash}</small></>;
    }
    if (feature === "entities") {
      const entity = row as EntityRow;
      return <><h2>{entity.value}</h2><p>{entity.entity_type} · {entity.confidence}% confidence</p><small>First seen {new Date(entity.first_seen).toLocaleString()} · last seen {new Date(entity.last_seen).toLocaleString()} · {entity.extraction_method}</small></>;
    }
    if (feature === "events") {
      const event = row as EventRow;
      return <><h2>{event.event_type}</h2><p>{event.severity} · {event.confidence}% confidence · {event.reason}</p><small>Document {event.document_id} · source {event.source_id}</small><details><summary>Evidence</summary><pre className="advanced-output">{JSON.stringify(event.evidence, null, 2)}</pre></details></>;
    }
    const crawl = row as CrawlRow;
    return <><h2>{crawl.id}</h2><p>{crawl.status} · source {crawl.source_id}</p><p>{crawl.records_extracted} documents · {crawl.duplicates_found} duplicates · {crawl.pages_failed} failures</p><p>Retries {crawl.retry_count??0} · Duration {crawl.duration_ms??"unavailable"} ms</p><small>Started {new Date(crawl.started_at).toLocaleString()}{crawl.error ? ` · ${crawl.error}` : ""}</small></>;
  }

  return <div className="advanced-workspace">
    <section className="module-header"><p>THREAT PROCESSING</p><h1>{meta[feature].title}</h1><span>{meta[feature].description}</span></section>
    {error && <div className="module-notice error" role="alert">{error}</div>}
    <article className="module-card">
      <div className="module-form"><input aria-label={`Search ${feature}`} placeholder={`Filter ${feature}...`} value={query} onChange={event => setQuery(event.target.value)} /><button type="button" onClick={() => void load(0,query)} disabled={loading}><RefreshCw size={14} /> Refresh</button></div>
      {loading ? <div className="module-loading">Loading {feature}...</div> : filtered.length === 0 ? <div className="empty-state">No {feature} recorded for this workspace.</div> : <div className="advanced-results">{filtered.map(row => <article className="advanced-tool" key={String(row.id)}><div className="module-card-heading"><Icon size={17} /><div>{renderRow(row)}</div></div></article>)}</div>}
      {(offset > 0 || rows.length === 50) && <div className="advanced-actions"><button type="button" disabled={loading || offset === 0} onClick={() => void load(Math.max(0, offset - 50),query)}>Previous</button><button type="button" disabled={loading || rows.length < 50} onClick={() => void load(offset + 50,query)}>Next</button></div>}
    </article>
  </div>;
}
