import unittest

from pydantic import ValidationError

from app.domain.schemas import ReportSchedule
from app.services.report_schedules import validate_schedule


class ReportScheduleTests(unittest.TestCase):
    def test_valid_schedule_is_bounded_and_normalized(self):
        payload = ReportSchedule(name="Daily brief", cron="0 8 * * 1-5", format="pdf", recipients=["SOC@example.com", "soc@example.com"])
        self.assertEqual(validate_schedule(payload), ["soc@example.com"])

    def test_rejects_command_like_cron_and_invalid_recipients(self):
        for cron, recipients in (("0 8 * * 1;curl", ["soc@example.com"]), ("0 8 * * x", ["soc@example.com"]), ("0 8 * * *", ["not-an-email"]), ("0 8 * * *", ["soc@example"]) ):
            payload = ReportSchedule(name="Schedule", cron=cron, format="pdf", recipients=recipients)
            with self.assertRaises(ValueError):
                validate_schedule(payload)
