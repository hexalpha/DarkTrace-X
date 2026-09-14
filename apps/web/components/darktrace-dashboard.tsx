"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  Activity, Bell, Bot, ChevronDown, Command, Crosshair, Database, FileSearch,
  Globe2, Languages, Moon, Network, Orbit, PanelLeftClose, Radar, Search,
  Settings2, Shield, Sparkles, Sun, TriangleAlert, Workflow, Zap
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { copy, type Language } from "../lib/i18n";
import type { DashboardOverview } from "../lib/types";

// Same-origin is the secure deployment default; local dev may override these public values.
const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "";

const demoOverview: DashboardOverview = {
  protected_assets: 1284,
  active_alerts: 42,
  critical_alerts: 3,
  iocs_tracked: 24891,
  risk_score: 71,
  enrichment_coverage: 94.8,
  event_rate: 1824,
  attack_timeline: [
    { hour: "00:00", events: 480, risk: 22 }, { hour: "04:00", events: 612, risk: 36 },
    { hour: "08:00", events: 1048, risk: 58 }, { hour: "12:00", events: 1743, risk: 71 },
    { hour: "16:00", events: 1384, risk: 63 }, { hour: "20:00", events: 1824, risk: 71 }
  ],
  regions: [
    { name: "North America", events: 643, risk: "high" }, { name: "Europe", events: 498, risk: "medium" },
    { name: "Asia Pacific", events: 511, risk: "critical" }, { name: "Other", events: 172, risk: "low" }
  ]
};

const nav: { label: keyof typeof copy.en; icon: LucideIcon; badge?: string }[] = [
  { label: "overview", icon: Orbit }, { label: "intelligence", icon: Database }, { label: "hunt", icon: Crosshair },
  { label: "exposure", icon: Radar, badge: "3" }, { label: "graph", icon: Network }, { label: "reports", icon: FileSearch }
];

const priorityItems = [
  { severity: "critical", time: "09m", title: "Credential exposure correlated", detail: "Approved breach source · 12 evidence items", score: 96 },
  { severity: "high", time: "27m", title: "Outbound beacon anomaly", detail: "FINANCE-API-02 · T1071.001", score: 84 },
  { severity: "high", time: "1h", title: "Internet-facing exploit signal", detail: "CVE-2026-24817 · asset overlap", score: 78 },
  { severity: "medium", time: "2h", title: "Phishing infrastructure overlap", detail: "Brand watch · 3 linked domains", score: 64 }
];

const tactics = [
  ["RECON", "T1595", "External scan", "observed"],
  ["ACCESS", "T1566", "Phishing", "observed"],
  ["EXECUTE", "T1059", "Command shell", "watch"],
  ["PERSIST", "T1078", "Valid accounts", "watch"],
  ["EXFIL", "T1041", "Web service", "clear"]
];

function compactNumber(value: number) {
  return new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(value);
}

export function DarkTraceDashboard() {
  const [language, setLanguage] = useState<Language>("en");
  const [light, setLight] = useState(false);
  const [overview, setOverview] = useState<DashboardOverview>(demoOverview);
  const [activeNav, setActiveNav] = useState("overview");
  const [pulse, setPulse] = useState(demoOverview.event_rate);
  const [prompt, setPrompt] = useState("");
  const [assistantReply, setAssistantReply] = useState("I’ve correlated the current priority queue. Three items need analyst validation: credential exposure, beacon behavior, and the internet-facing exploit signal.");
  const [isThinking, setIsThinking] = useState(false);
  const t = copy[language];

  useEffect(() => {
    document.documentElement.classList.toggle("light", light);
  }, [light]);

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${apiUrl}/api/v1/dashboard/overview`, { signal: controller.signal })
      .then((response) => response.ok ? response.json() : Promise.reject(new Error("Dashboard API unavailable")))
      .then((data: DashboardOverview) => { setOverview(data); setPulse(data.event_rate); })
      .catch(() => undefined);
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const socketUrl = process.env.NEXT_PUBLIC_WS_URL ?? `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}/ws/events`;
    const socket = new WebSocket(socketUrl);
    socket.onmessage = (event) => {
      const data = JSON.parse(event.data) as { type?: string; events_per_minute?: number };
      if (data.type === "telemetry.pulse" && data.events_per_minute) setPulse(data.events_per_minute);
    };
    return () => socket.close();
  }, []);

  const statCards = useMemo(() => [
    { label: "Protected assets", value: overview.protected_assets.toLocaleString(), delta: "+2.4%", icon: Shield, tone: "cyan" },
    { label: "Active alerts", value: overview.active_alerts.toString(), delta: `${overview.critical_alerts} critical`, icon: TriangleAlert, tone: "rose" },
    { label: "Tracked IOCs", value: compactNumber(overview.iocs_tracked), delta: "94.8% enriched", icon: Search, tone: "violet" },
    { label: "Event velocity", value: compactNumber(pulse), delta: "events / min", icon: Activity, tone: "emerald" }
  ], [overview, pulse]);

  async function askAssistant(event: FormEvent) {
    event.preventDefault();
    const question = prompt.trim();
    if (!question || isThinking) return;
    setPrompt("");
    setIsThinking(true);
    try {
      const response = await fetch(`${apiUrl}/api/v1/ai/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: question, language })
      });
      const data = await response.json() as { message?: string; detail?: { message?: string } };
      setAssistantReply(data.message ?? data.detail?.message ?? "The assistant could not complete that request right now.");
    } catch {
      setAssistantReply("The AI control plane is offline. Your existing investigation and evidence remain available.");
    } finally {
      setIsThinking(false);
    }
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand-lockup">
          <div className="brand-mark"><Shield size={19} strokeWidth={2.5} /></div>
          <div><span className="brand-name">DARKTRACE</span><span className="brand-x">X</span></div>
          <button className="icon-button sidebar-collapse" aria-label="Collapse navigation"><PanelLeftClose size={16} /></button>
        </div>
        <div className="tenant-switcher"><span className="tenant-dot" /> <span>Northstar Global</span><ChevronDown size={14} /></div>
        <nav className="primary-nav" aria-label="Primary navigation">
          <p className="nav-caption">OPERATIONS</p>
          {nav.map(({ label, icon: Icon, badge }) => (
            <button className={`nav-item ${activeNav === label ? "active" : ""}`} onClick={() => setActiveNav(label)} key={label}>
              <Icon size={17} /><span>{t[label]}</span>{badge && <b>{badge}</b>}
            </button>
          ))}
          <p className="nav-caption nav-caption-lower">SYSTEM</p>
          <button className="nav-item"><Settings2 size={17} /><span>{t.settings}</span></button>
        </nav>
        <div className="operator-card">
          <div className="operator-avatar">AS</div>
          <div><strong>Aarav Sharma</strong><span>Senior Analyst</span></div>
          <ChevronDown size={14} />
        </div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div className="crumb"><span>Operations</span><i>/</i><strong>{t.command}</strong></div>
          <div className="topbar-actions">
            <div className="search-shortcut"><Search size={16} /><span>Search intelligence</span><kbd><Command size={11} /> K</kbd></div>
            <button className="icon-button" aria-label="Toggle language" onClick={() => setLanguage(language === "en" ? "hi" : "en")}><Languages size={17} /><span className="language-code">{language.toUpperCase()}</span></button>
            <button className="icon-button" aria-label="Toggle color mode" onClick={() => setLight(!light)}>{light ? <Moon size={17} /> : <Sun size={17} />}</button>
            <button className="notification-button" aria-label="Notifications"><Bell size={18} /><span /></button>
          </div>
        </header>

        <div className="dashboard-scroll">
          <section className="welcome-row">
            <div>
              <div className="eyebrow"><span className="pulse-dot" /> {t.live} <i>·</i> UTC +05:30</div>
              <h1>Defend with <em>clarity.</em></h1>
              <p>Signal-rich intelligence for decisive security operations.</p>
            </div>
            <div className="posture-chip"><span>Posture score</span><strong>{overview.risk_score}</strong><div className="posture-track"><i style={{ width: `${overview.risk_score}%` }} /></div><small>Guarded</small></div>
          </section>

          <section className="stat-grid">
            {statCards.map(({ label, value, delta, icon: Icon, tone }) => (
              <article className="stat-card" key={label}>
                <div className={`stat-icon ${tone}`}><Icon size={18} /></div>
                <div className="stat-copy"><span>{label}</span><strong>{value}</strong><small>{delta}</small></div>
                <div className={`corner-orbit ${tone}`} />
              </article>
            ))}
          </section>

          <section className="main-grid">
            <article className="glass-card map-card">
              <div className="card-title-row"><div><p className="card-kicker">REAL-TIME CORRELATION</p><h2>{t.global}</h2></div><button className="pill-button"><Globe2 size={14} /> Global <ChevronDown size={13} /></button></div>
              <div className="map-frame">
                <div className="map-scanline" />
                <svg className="world-map" viewBox="0 0 820 340" role="img" aria-label="Real-time global threat map">
                  <defs>
                    <radialGradient id="mapGlow"><stop stopColor="#5eead4" stopOpacity=".36"/><stop offset="1" stopColor="#5eead4" stopOpacity="0"/></radialGradient>
                    <linearGradient id="attackArc" x1="0" x2="1"><stop stopColor="#fb7185" stopOpacity=".1"/><stop offset=".5" stopColor="#fb7185"/><stop offset="1" stopColor="#22d3ee" stopOpacity=".2"/></linearGradient>
                  </defs>
                  <g className="map-grid"><path d="M0 85H820M0 170H820M0 255H820"/><path d="M102 0V340M205 0V340M307 0V340M410 0V340M512 0V340M615 0V340M717 0V340"/></g>
                  <g className="continents"><path d="M80 70l75-30 65 18 16 42-37 21-19 45-56 8-28-43-35-14z"/><path d="M230 155l48 10 34 63-21 83-38-18-10-60-31-42z"/><path d="M390 65l67-23 97 23 45 53-36 34-46-12-41 34-56-18-39-44z"/><path d="M476 166l63 8 54 48-22 69-72-8-37-63z"/><path d="M635 218l83 8 38 42-28 39-73-10-30-42z"/></g>
                  <motion.path d="M165 122 Q345 4 553 126" fill="none" stroke="url(#attackArc)" strokeWidth="1.5" strokeDasharray="5 6" initial={{ pathLength: 0, opacity: 0 }} animate={{ pathLength: 1, opacity: 1 }} transition={{ duration: 2, repeat: Infinity, repeatType: "reverse" }}/>
                  <motion.path d="M675 253 Q500 54 266 177" fill="none" stroke="url(#attackArc)" strokeWidth="1.2" strokeDasharray="4 7" initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 3, repeat: Infinity, repeatType: "reverse", delay: .4 }}/>
                  {[[165,122,"critical"],[553,126,"high"],[266,177,"medium"],[675,253,"high"],[498,219,"critical"]].map(([cx, cy, severity], index) => <g key={index}><circle cx={cx} cy={cy} r="33" fill="url(#mapGlow)"/><motion.circle cx={cx} cy={cy} r="5" className={`map-node ${severity}`} animate={{ r: [4, 7, 4], opacity: [.75, 1, .75] }} transition={{ duration: 2.2, repeat: Infinity, delay: index * .22 }}/></g>)}
                </svg>
                <div className="map-legend"><span><i className="critical" /> Critical</span><span><i className="high" /> High</span><span><i className="medium" /> Medium</span></div>
                <div className="map-readout"><Activity size={14} /><div><b>{pulse.toLocaleString()}</b><span>EVENTS / MIN</span></div></div>
              </div>
              <div className="region-strip">{overview.regions.map((region) => <div key={region.name}><span className={`risk-dot ${region.risk}`} /> <b>{region.name}</b><strong>{region.events}</strong></div>)}</div>
            </article>

            <article className="glass-card queue-card">
              <div className="card-title-row"><div><p className="card-kicker">ANALYST FOCUS</p><h2>{t.queue}</h2></div><button className="link-button">View all</button></div>
              <div className="queue-list">{priorityItems.map((item) => <button className="queue-item" key={item.title}><span className={`severity-bar ${item.severity}`} /><div className="queue-content"><div><span className={`severity-label ${item.severity}`}>{item.severity}</span><time>{item.time}</time></div><strong>{item.title}</strong><p>{item.detail}</p></div><div className="queue-score">{item.score}</div></button>)}</div>
              <button className="triage-button"><Zap size={16} /> Start guided triage</button>
            </article>
          </section>

          <section className="lower-grid">
            <article className="glass-card timeline-card">
              <div className="card-title-row"><div><p className="card-kicker">LAST 24 HOURS</p><h2>Attack signal timeline</h2></div><div className="chart-key"><span><i /> Events</span><span><i /> Risk</span></div></div>
              <div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><AreaChart data={overview.attack_timeline} margin={{ top: 8, left: -24, right: 3, bottom: 0 }}><defs><linearGradient id="areaGradient" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="#22d3ee" stopOpacity=".36"/><stop offset="100%" stopColor="#22d3ee" stopOpacity="0"/></linearGradient></defs><XAxis dataKey="hour" axisLine={false} tickLine={false} tick={{ fill: "#6f829f", fontSize: 11 }}/><YAxis axisLine={false} tickLine={false} tick={{ fill: "#6f829f", fontSize: 11 }} /><Tooltip contentStyle={{ background: "#10192a", border: "1px solid #24354f", borderRadius: 10 }} labelStyle={{ color: "#d6e5f5" }} itemStyle={{ color: "#6ee7f9" }} /><Area type="monotone" dataKey="events" stroke="#22d3ee" strokeWidth={2} fill="url(#areaGradient)" /><Area type="monotone" dataKey="risk" stroke="#a78bfa" strokeWidth={1.5} fill="transparent" /></AreaChart></ResponsiveContainer></div>
            </article>

            <article className="glass-card chain-card">
              <div className="card-title-row"><div><p className="card-kicker">MITRE ATT&CK</p><h2>Observed attack chain</h2></div><button className="icon-button compact" aria-label="Open intelligence graph"><Network size={16} /></button></div>
              <div className="attack-chain">{tactics.map(([phase, id, behavior, state], index) => <div className="chain-row" key={phase}><span className={`chain-node ${state}`}><span>{index + 1}</span></span><div><b>{phase}</b><strong>{behavior}</strong><small>{id}</small></div>{index < tactics.length - 1 && <i className="chain-link" />}</div>)}</div>
            </article>
          </section>

          <section className="assistant-section">
            <article className="assistant-card">
              <div className="assistant-orb"><Bot size={20} /></div>
              <div className="assistant-heading"><div><p className="card-kicker">CONTEXT-AWARE · SOURCE-GROUNDED</p><h2>{t.assistant}</h2></div><span className="ready-indicator"><i /> Ready</span></div>
              <p className="assistant-answer">{isThinking ? "Reviewing the selected investigation context…" : assistantReply}</p>
              <form className="assistant-form" onSubmit={askAssistant}><Sparkles size={17} /><input value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder={t.ask} aria-label={t.ask} /><button type="submit" disabled={isThinking}>{isThinking ? "Thinking" : t.synthesize}</button></form>
              <div className="assistant-suggestions"><span>Try:</span><button type="button" onClick={() => setPrompt("Summarize the critical credential exposure alert.")}>Summarize credential exposure</button><button type="button" onClick={() => setPrompt("Explain the risk and mitigation for the newest CVE.")}>Explain latest CVE</button></div>
            </article>
          </section>
        </div>
      </section>
    </main>
  );
}
