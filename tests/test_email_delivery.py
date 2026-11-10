"""Exercise delivery failures without contacting providers or sending email."""
import os
import unittest
from unittest.mock import patch

import requests

from shared import send_email
from daily import whatsapp_connector


class EmailDeliveryTests(unittest.TestCase):
    def setUp(self):
        environment = patch.dict(os.environ, {
            "EMAIL_PROVIDER": "resend",
            "RESEND_API_KEY": "test-secret",
            "EMAIL_FROM": "News <news@example.com>",
            "GMAIL_EMAIL": "",
            "GMAIL_APP_PASSWORD": "",
        })
        environment.start()
        self.addCleanup(environment.stop)

    @patch("shared.send_email._send_via_starttls")
    @patch("shared.send_email.requests.post")
    def test_https_sends_original_text_without_gmail_credentials(self, post, smtp):
        post.return_value.status_code = 200
        post.return_value.json.return_value = {"id": "email-id"}
        send_email.send_email("Daily news", ["reader@example.com"], "AI news")
        post.assert_called_once_with(
            "https://api.resend.com/emails",
            headers={"Authorization": "Bearer test-secret"},
            json={"from": "News <news@example.com>", "to": ["reader@example.com"],
                  "subject": "AI news", "text": "Daily news"},
            timeout=(10, 20), allow_redirects=False,
        )
        smtp.assert_not_called()

    @patch("shared.send_email._send_via_starttls")
    @patch("shared.send_email.requests.post")
    def test_http_failures_never_retry_or_fall_back(self, post, smtp):
        for status in (302, 401, 403, 422, 429, 500):
            with self.subTest(status=status):
                post.reset_mock()
                post.return_value.status_code = status
                with self.assertRaisesRegex(RuntimeError, str(status)) as exc:
                    send_email.send_email("News", ["reader@example.com"])
                self.assertNotIn("test-secret", str(exc.exception))
                post.assert_called_once()
        smtp.assert_not_called()

    @patch("shared.send_email._send_via_starttls")
    @patch("shared.send_email.requests.post")
    def test_timeout_is_unconfirmed_without_retry_or_fallback(self, post, smtp):
        post.side_effect = requests.Timeout("private details")
        with self.assertRaisesRegex(RuntimeError, "unconfirmed") as exc:
            send_email.send_email("News", ["reader@example.com"])
        self.assertNotIn("private details", str(exc.exception))
        post.assert_called_once()
        smtp.assert_not_called()

    @patch("shared.send_email.requests.post")
    def test_success_requires_acceptance_id(self, post):
        post.return_value.status_code = 200
        for result in ({}, None, []):
            post.return_value.json.return_value = result
            with self.assertRaisesRegex(RuntimeError, "unconfirmed"):
                send_email.send_email("News", ["reader@example.com"])
        post.return_value.json.side_effect = ValueError("bad JSON")
        with self.assertRaisesRegex(RuntimeError, "unconfirmed"):
            send_email.send_email("News", ["reader@example.com"])

    @patch("shared.send_email.requests.post")
    def test_invalid_config_does_not_send(self, post):
        for setting in ("RESEND_API_KEY", "EMAIL_FROM"):
            with patch.dict(os.environ, {setting: ""}):
                with self.assertRaisesRegex(RuntimeError, "requires"):
                    send_email.send_email("News", ["reader@example.com"])
        with patch.dict(os.environ, {"EMAIL_PROVIDER": "typo"}):
            with self.assertRaisesRegex(ValueError, "EMAIL_PROVIDER"):
                send_email.send_email("News", ["reader@example.com"])
        with self.assertRaisesRegex(ValueError, "recipient"):
            send_email.send_email("News", [])
        post.assert_not_called()

    @patch("shared.send_email._send_via_ssl", side_effect=OSError(101, "Network is unreachable"))
    @patch("shared.send_email._send_via_starttls", side_effect=OSError(101, "Network is unreachable"))
    def test_blocked_smtp_reports_railway_remediation(self, starttls, ssl):
        with patch.dict(os.environ, {"EMAIL_PROVIDER": "", "GMAIL_EMAIL": "sender@example.com",
                                     "GMAIL_APP_PASSWORD": "fake"}):
            with self.assertRaisesRegex(RuntimeError, "Railway requires Pro") as exc:
                send_email.send_email("News", ["reader@example.com"])
        self.assertIn("EMAIL_PROVIDER=resend", str(exc.exception))

    def test_smtp_refusal_keeps_recipient_specific_error(self):
        error = send_email.smtplib.SMTPRecipientsRefused({"reader@example.com": (550, b"Rejected")})
        with self.assertRaisesRegex(RuntimeError, "refused one or more"):
            send_email._raise_helpful_smtp_error(error)

    @patch("daily.whatsapp_connector.requests.post")
    def test_relay_404_explains_configuration_without_retry(self, post):
        post.return_value.status_code = 404
        with patch.dict(os.environ, {"API_PATH": "https://relay.example", "API_POST_PATH": "/send",
                                     "BEARER_TOKEN": "relay-secret"}):
            with self.assertRaisesRegex(RuntimeError, "HTTP 404.*API_PATH.*API_POST_PATH") as exc:
                whatsapp_connector.send_whatsapp("News", ["911234567890"])
        post.assert_called_once()
        self.assertNotIn("relay-secret", str(exc.exception))


if __name__ == "__main__":
    unittest.main()
