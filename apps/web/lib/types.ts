export type TimelinePoint = { hour: string; events: number; risk: number };

export type DashboardOverview = {
  protected_assets: number;
  active_alerts: number;
  critical_alerts: number;
  iocs_tracked: number;
  risk_score: number;
  enrichment_coverage: number;
  event_rate: number;
  attack_timeline: TimelinePoint[];
  regions: { name: string; events: number; risk: string; latitude: number; longitude: number; source: string; last_observed_at: string }[];
};
