"""Aggregate explicitly reported locations without inventing geography or risk."""
from pydantic import ValidationError

from app.services.detection import ReportedLocation


def reported_regions(events: list[dict]) -> list[dict]:
    groups: dict[tuple, dict] = {}
    for event in events:
        try:
            location = ReportedLocation.model_validate(event.get("location"))
        except ValidationError:
            continue
        key = (location.latitude, location.longitude, location.name, location.source)
        if key not in groups:
            groups[key] = {**location.model_dump(), "events": 0, "risk": "unassessed",
                           "last_observed_at": event["observed_at"]}
        group = groups[key]
        group["events"] += 1
        group["last_observed_at"] = max(group["last_observed_at"], event["observed_at"])
    return sorted(groups.values(), key=lambda row: (-row["events"], row["name"], row["source"]))[:200]
