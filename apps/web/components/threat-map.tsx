"use client";

import { useState } from "react";
import type { DashboardOverview } from "../lib/types";

export function ThreatMap({ regions, stale }: { regions: DashboardOverview["regions"]; stale: boolean }) {
  const [selected, setSelected] = useState<string>();
  const key = (row: DashboardOverview["regions"][number]) => JSON.stringify([row.latitude, row.longitude, row.name, row.source]);
  const active = regions.find(row => key(row) === selected) ?? regions[0];
  return <article className="glass-card threat-geography">
    <div className="card-title-row"><div><p className="card-kicker">REPORTED TELEMETRY · LAST 24 HOURS</p><h2>Threat geography</h2></div><span className="card-kicker">{stale ? "STALE" : regions.length ? "LIVE" : "UNAVAILABLE"}</span></div>
    <p>Source-reported coordinates, not verified attacker origin. Event volume does not indicate threat severity.</p>
    <svg viewBox="0 0 760 400" role="img" aria-label="Reported telemetry locations on a longitude and latitude grid">
      <rect x="20" y="20" width="720" height="360" rx="8" fill="#081727"/>
      {[-180,-120,-60,0,60,120,180].map(lon => <g key={lon}><line x1={20+(lon+180)*2} x2={20+(lon+180)*2} y1="20" y2="380" stroke="#254155"/><text x={20+(lon+180)*2} y="396" textAnchor="middle" fill="#9fb5c7" fontSize="10">{lon}°</text></g>)}
      {[-90,-60,-30,0,30,60,90].map(lat => <g key={lat}><line x1="20" x2="740" y1={20+(90-lat)*2} y2={20+(90-lat)*2} stroke="#254155"/><text x="22" y={30+(90-lat)*2} fill="#9fb5c7" fontSize="10">{lat}°</text></g>)}
      {regions.map(row => <circle key={key(row)} cx={20+(row.longitude+180)*2} cy={20+(90-row.latitude)*2} r={Math.min(12,4+Math.log2(row.events+1))} fill={active===row?"#fbbf24":"#22d3ee"} stroke="#e0f2fe" onClick={()=>setSelected(key(row))}><title>{row.name}: {row.events} events · {row.source}</title></circle>)}
    </svg>
    {!regions.length ? <p className="empty-state">No geocoded telemetry received. Import observations with a source and location in AI Anomalies.</p> : <>
      <label>Inspect reported location <select aria-label="Inspect reported location" value={active ? key(active) : ""} onChange={event=>setSelected(event.target.value)}>{regions.map(row=><option key={key(row)} value={key(row)}>{row.name} · {row.source} · {row.events} events</option>)}</select></label>
      {active && <p><strong>{active.name}</strong> · {active.latitude}°, {active.longitude}° · {active.events} observations<br/>Source: {active.source} · Last observed: {new Date(active.last_observed_at).toLocaleString()}</p>}
    </>}
    <small>Longitude runs horizontally; latitude vertically. Up to 200 locations from the latest 10,000 geocoded observations within 24 hours. No external geolocation requests.</small>
  </article>;
}
