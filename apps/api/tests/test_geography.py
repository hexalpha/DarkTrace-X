import unittest

from pydantic import ValidationError

from app.services.detection import ReportedLocation
from app.services.geography import reported_regions


class GeographyTests(unittest.TestCase):
    def test_rejects_invalid_and_unsourced_coordinates(self):
        for changes in ({"latitude": 91}, {"longitude": -181}, {"latitude": float("nan")},
                        {"source": " "}, {"command": "anything"}):
            with self.assertRaises(ValidationError):
                ReportedLocation.model_validate({"latitude": 0, "longitude": 0, "name": "QA", "source": "QA", **changes})

    def test_no_inferred_locations_and_source_preservation(self):
        location = {"latitude": 0, "longitude": 0, "name": "QA", "source": "collector-a"}
        a = {"location": location, "observed_at": "2026-09-15T00:00:00+00:00"}
        b = {**a, "observed_at": "2026-09-15T01:00:00+00:00"}
        rows = reported_regions([{}, {"location": {"latitude": 99}}, a, b,
                                 {**a, "location": {**location, "source": "collector-b"}}])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["events"], 2)
        self.assertEqual(rows[0]["last_observed_at"], b["observed_at"])
        self.assertEqual(rows[0]["risk"], "unassessed")
        self.assertEqual(reported_regions([{"entity": "8.8.8.8"}]), [])
