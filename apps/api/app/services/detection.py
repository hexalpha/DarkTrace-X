"""Explainable, chronological behavioral baselines; no remote model or fabricated evidence."""
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from statistics import median
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class ReportedLocation(BaseModel):
    """Collector-supplied evidence; never inferred from an IP or model output."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)
    name: str = Field(min_length=1, max_length=120)
    source: str = Field(min_length=1, max_length=160)


class TelemetryEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=80)
    entity: str = Field(min_length=1, max_length=160)
    metric: Literal["failed_logins", "outbound_bytes", "dns_requests", "process_count"]
    value: float = Field(ge=0, le=1e15, allow_inf_nan=False)
    observed_at: AwareDatetime
    location: ReportedLocation | None = None

    @model_validator(mode="after")
    def valid_time(self):
        if self.observed_at > datetime.now(UTC) + timedelta(minutes=5):
            raise ValueError("Telemetry cannot be more than five minutes in the future")
        return self


class TelemetryBatch(BaseModel):
    events: list[TelemetryEvent] = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def unique_ids(self):
        if len({event.id for event in self.events}) != len(self.events):
            raise ValueError("Event IDs must be unique within a batch")
        return self


def analyze(events: list[dict], now: datetime | None = None) -> dict:
    now = now or datetime.now(UTC)
    groups = defaultdict(list)
    findings, predictions = [], []
    ordered = sorted(events, key=lambda e: (datetime.fromisoformat(e["observed_at"]), e["id"]))
    for event in ordered:
        groups[(event["entity"], event["metric"])].append(event)
    ready = 0
    for (entity, metric), samples in groups.items():
        history, scores = [], []
        # Equal-time observations never train each other.
        time_batches = defaultdict(list)
        for event in samples:
            time_batches[datetime.fromisoformat(event["observed_at"])].append(event)
        for timestamp in sorted(time_batches):
            batch = time_batches[timestamp]
            for event in batch:
                if len(history) >= 20:
                    baseline = median(history[-200:])
                    mad = median(abs(v - baseline) for v in history[-200:])
                    scale = max(1.4826 * mad, abs(baseline) * .05, 1.0)
                    deviation = max(0, (event["value"] - baseline) / scale)
                    score = round(min(100, deviation * 10), 1)
                    scores.append((event, score))
                    if deviation >= 3.5:
                        findings.append({**event, "score": score, "baseline": round(baseline, 2),
                            "deviation": round(deviation, 2), "baseline_samples": min(200, len(history)),
                            "severity": "critical" if score >= 80 else "high" if score >= 60 else "medium",
                            "explanation": f"{metric} exceeded its prior median by {deviation:.1f} robust deviations.",
                            "recommendation": "Validate the source event, compare approved activity, and investigate the affected entity."})
            history.extend(e["value"] for e in batch)
        if len(history) >= 20:
            ready += 1
        recent = [(e, s) for e, s in scores if now - timedelta(hours=24) <= datetime.fromisoformat(e["observed_at"]) <= now]
        if len(recent) >= 5:
            values = [s for _, s in recent[-20:]]
            level = values[0]
            for score in values[1:]:
                level = .3 * score + .7 * level
            midpoint = len(values) // 2
            trend = median(values[midpoint:]) - median(values[:midpoint])
            risk = round(max(0, min(100, level + max(0, trend) * .5)), 1)
            predictions.append({"entity": entity, "metric": metric, "risk_score": risk,
                "trend": "rising" if trend > 5 else "falling" if trend < -5 else "stable",
                "horizon_hours": 24, "evidence_count": len(recent), "evidence_ids": [e["id"] for e, _ in recent[-20:]],
                "confidence": "limited" if len(recent) < 20 else "moderate",
                "recommendation": "Review recent anomalies and increase monitoring." if risk >= 35 else "Continue monitoring and collecting baseline telemetry."})
    return {"model": "robust-mad-ewma-v1", "event_count": len(events), "baseline_ready": ready,
        "last_observed_at": ordered[-1]["observed_at"] if ordered else None,
        "learning": len(groups) - ready, "generated_at": now.isoformat(),
        "anomalies": sorted(findings, key=lambda e: (e["observed_at"], e["score"]), reverse=True)[:200],
        "predictions": sorted(predictions, key=lambda p: p["risk_score"], reverse=True),
        "limitations": "Risk is a heuristic priority score, not a calibrated breach probability. Requires 20 earlier samples per entity/metric and five scored samples in 24h for forecasts. Use equal-duration telemetry buckets; seasonality is not modeled."}
