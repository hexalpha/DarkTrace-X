import unittest

from pydantic import ValidationError

from app.domain.schemas import WebhookSubscription
from app.services.webhooks import validate_webhook_url


class WebhookValidationTests(unittest.TestCase):
    def test_https_only_and_no_ssrf_targets(self):
        self.assertEqual(validate_webhook_url("https://hooks.example.com/events"), "https://hooks.example.com/events")
        for value in ("http://hooks.example.com/events", "https://localhost/hook", "https://127.0.0.1/hook", "https://10.0.0.5/hook", "https://hooks.example.com/hook?token=secret", "https://user:pass@hooks.example.com/hook"):
            with self.assertRaises(ValueError):
                validate_webhook_url(value)

    def test_shared_secret_is_required_and_long_enough(self):
        with self.assertRaises(ValidationError):
            WebhookSubscription(name="SOC", url="https://hooks.example.com/events", event_types=["alert.created"], secret="short")
        item = WebhookSubscription(name="SOC", url="https://hooks.example.com/events", event_types=["alert.created"], secret="s" * 32)
        self.assertEqual(item.secret.get_secret_value(), "s" * 32)
