import os
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

import api
from daily import orchestrator, whatsapp_connector
from shared import send_email
from weekly import digest as weekly_digest, linkedin_connector


class RelayTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {
            "API_PATH": "https://relay.example/",
            "API_POST_PATH": "/api/messages/send",
            "BEARER_TOKEN": "relay-secret",
            "RECEIPENT_PHONE_NUMBERS": "918340412106  919876543210\n911234567890",
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)

    @patch("daily.whatsapp_connector.requests.post")
    def test_exact_payload_auth_and_whitespace_recipients(self, post):
        post.return_value.status_code = 202
        phones = whatsapp_connector.get_phone_recipients()
        whatsapp_connector.send_whatsapp("Daily email content", phones)
        post.assert_called_once_with(
            "https://relay.example/api/messages/send",
            headers={"Authorization": "Bearer relay-secret"},
            json={"recipients": ["918340412106", "919876543210", "911234567890"], "message": "Daily email content"},
            timeout=(10, 60), allow_redirects=False,
        )

    @patch("daily.whatsapp_connector.requests.post")
    def test_http_errors_and_redirects_are_not_successful_or_retried(self, post):
        for code in (302, 401, 404, 500):
            post.reset_mock()
            post.return_value.status_code = code
            with self.assertRaisesRegex(RuntimeError, str(code)):
                whatsapp_connector.send_whatsapp("News", ["911234567890"])
            self.assertEqual(post.call_count, 1)

    @patch("daily.whatsapp_connector.requests.post")
    def test_timeout_is_unconfirmed_and_not_retried(self, post):
        post.side_effect = whatsapp_connector.requests.Timeout("secret details")
        with self.assertRaisesRegex(RuntimeError, "delivery is unconfirmed") as exc:
            whatsapp_connector.send_whatsapp("News", ["911234567890"])
        self.assertNotIn("secret details", str(exc.exception))
        self.assertEqual(post.call_count, 1)

    @patch("daily.whatsapp_connector.requests.post")
    def test_missing_config_fails_before_network(self, post):
        with patch.dict(os.environ, {"BEARER_TOKEN": ""}):
            with self.assertRaises(ValueError):
                whatsapp_connector.send_whatsapp("News", ["911234567890"])
        post.assert_not_called()


class DailyTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {
            "RECIPIENT_EMAILS": "reader@example.com",
            "RECEIPENT_PHONE_NUMBERS": "911234567890",
            "API_PATH": "https://relay.example",
            "API_POST_PATH": "/api/messages/send",
            "BEARER_TOKEN": "relay-secret",
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)

    @patch("daily.orchestrator.send_whatsapp")
    @patch("daily.orchestrator.send_email")
    @patch("daily.orchestrator.store_research_result", return_value=datetime(2026, 11, 10))
    @patch("daily.orchestrator.run_topic_research", return_value="Identical content")
    def test_one_generation_archived_before_both_deliveries(self, research, store, email, whatsapp):
        calls = Mock()
        calls.attach_mock(store, "store")
        calls.attach_mock(email, "email")
        calls.attach_mock(whatsapp, "whatsapp")
        result = orchestrator.run_daily("AI")
        research.assert_called_once_with("AI")
        self.assertEqual([c[0] for c in calls.mock_calls], ["store", "email", "whatsapp"])
        self.assertEqual(store.call_args.args[1], "Identical content")
        self.assertEqual(email.call_args.args[0], "Identical content")
        whatsapp.assert_called_once_with("Identical content", ["911234567890"])
        self.assertEqual(result["deliveries"], {"email": "sent", "whatsapp": "accepted"})

    @patch("daily.orchestrator.send_whatsapp")
    @patch("daily.orchestrator.send_email", side_effect=RuntimeError("SMTP failed"))
    @patch("daily.orchestrator.store_research_result")
    @patch("daily.orchestrator.run_topic_research", return_value="News")
    def test_email_failure_still_attempts_whatsapp_and_reports_partial_result(self, research, store, email, whatsapp):
        with self.assertLogs("daily.orchestrator", level="ERROR"):
            result = orchestrator.run_daily("AI")
        whatsapp.assert_called_once()
        self.assertEqual(result["deliveries"], {
            "email": "failed_or_unconfirmed", "whatsapp": "accepted",
        })

    @patch("daily.orchestrator.send_whatsapp")
    @patch("daily.orchestrator.send_email")
    @patch("daily.orchestrator.run_topic_research", return_value="News")
    def test_whatsapp_failure_and_both_failures_are_nonfatal(self, research, email, whatsapp):
        for email_fails in (False, True):
            with self.subTest(email_fails=email_fails):
                email.reset_mock()
                whatsapp.reset_mock()
                email.side_effect = RuntimeError("Email failed") if email_fails else None
                whatsapp.side_effect = RuntimeError("Relay failed")
                with self.assertLogs("daily.orchestrator", level="ERROR"):
                    result = orchestrator.run_daily("AI", store_to_db=False)
                email.assert_called_once()
                whatsapp.assert_called_once()
                self.assertEqual(result["content"], "News")
                self.assertEqual(result["deliveries"], {
                    "email": "failed_or_unconfirmed" if email_fails else "sent",
                    "whatsapp": "failed_or_unconfirmed",
                })

    @patch("daily.whatsapp_connector.requests.post")
    @patch("daily.orchestrator.send_email")
    @patch("daily.orchestrator.run_topic_research", return_value="News")
    def test_missing_relay_config_does_not_prevent_email(self, research, email, post):
        with patch.dict(os.environ, {"BEARER_TOKEN": ""}):
            with self.assertLogs("daily.orchestrator", level="ERROR"):
                result = orchestrator.run_daily("AI", store_to_db=False)
        research.assert_called_once()
        email.assert_called_once()
        post.assert_not_called()
        self.assertEqual(result["deliveries"], {"email": "sent", "whatsapp": "failed_or_unconfirmed"})

    @patch("daily.orchestrator.send_email")
    @patch("daily.orchestrator.send_whatsapp")
    @patch("daily.orchestrator.run_topic_research", return_value="News")
    def test_whatsapp_only_and_email_only(self, research, whatsapp, email):
        orchestrator.run_daily("AI", email_enabled=False, store_to_db=False)
        email.assert_not_called()
        whatsapp.assert_called_once()
        whatsapp.reset_mock()
        orchestrator.run_daily("AI", whatsapp_enabled=False, store_to_db=False)
        email.assert_called_once()
        whatsapp.assert_not_called()

    @patch("daily.orchestrator.run_topic_research", return_value="   ")
    @patch("daily.orchestrator.store_research_result")
    @patch("daily.orchestrator.send_email")
    def test_empty_research_never_stored_or_sent(self, email, store, research):
        with self.assertRaisesRegex(RuntimeError, "empty content"):
            orchestrator.run_daily("AI")
        email.assert_not_called()
        store.assert_not_called()

    @patch("daily.orchestrator.run_topic_research")
    def test_no_channels_fails_before_research(self, research):
        with self.assertRaises(ValueError):
            orchestrator.run_daily("AI", email_enabled=False, whatsapp_enabled=False)
        research.assert_not_called()

    @patch("daily.orchestrator.send_email")
    @patch("daily.orchestrator.send_whatsapp")
    @patch("daily.orchestrator.store_research_result", side_effect=RuntimeError("DB unavailable"))
    @patch("daily.orchestrator.run_topic_research", return_value="News")
    def test_archive_failure_stops_delivery(self, research, store, whatsapp, email):
        with self.assertRaisesRegex(RuntimeError, "DB unavailable"):
            orchestrator.run_daily("AI")
        email.assert_not_called()
        whatsapp.assert_not_called()


class EmailTests(unittest.TestCase):
    @patch("shared.send_email.smtplib.SMTP")
    @patch("shared.send_email._send_via_ssl")
    def test_partial_recipient_refusal_is_reported_without_resending(self, fallback, smtp):
        smtp.return_value.__enter__.return_value.send_message.return_value = {
            "refused@example.com": (550, b"Rejected"),
        }
        with patch.dict(os.environ, {"EMAIL_PROVIDER": "gmail", "GMAIL_EMAIL": "sender@example.com", "GMAIL_APP_PASSWORD": "fake"}):
            with self.assertRaisesRegex(RuntimeError, "refused"):
                send_email.send_email("News", ["accepted@example.com", "refused@example.com"])
        fallback.assert_not_called()


class EndpointTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(api.app)
        self.environment = patch.dict(os.environ, {"BACKEND_API_TOKEN": "backend-secret"})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.headers = {"Authorization": "Bearer backend-secret"}

    @patch("api.run_daily")
    @patch("api.generate_weekly_digest")
    def test_health_and_authentication(self, weekly, daily):
        self.assertEqual(self.client.get("/health").status_code, 200)
        for endpoint in ("/daily-news", "/weekly-digest"):
            self.assertEqual(self.client.post(endpoint).status_code, 401)
            self.assertEqual(self.client.post(endpoint, headers={"Authorization": "Bearer relay-secret"}).status_code, 401)
            with patch.dict(os.environ, {"BACKEND_API_TOKEN": ""}):
                self.assertEqual(self.client.post(endpoint).status_code, 503)
        daily.assert_not_called()
        weekly.assert_not_called()

    @patch("api.run_daily", return_value={"content": "News"})
    def test_daily_options(self, daily):
        response = self.client.post("/daily-news", headers=self.headers, json={"topic": "AI", "email": False})
        self.assertEqual(response.status_code, 200)
        daily.assert_called_once_with(topic="AI", email_enabled=False, whatsapp_enabled=True)

    @patch("api.run_daily", return_value={"content": "News"})
    def test_daily_empty_body_uses_defaults(self, daily):
        self.assertEqual(self.client.post("/daily-news", headers=self.headers).status_code, 200)
        self.assertTrue(daily.call_args.kwargs["whatsapp_enabled"])

    @patch("api.run_daily")
    def test_partial_failure_response(self, daily):
        daily.return_value = {"deliveries": {"whatsapp": "accepted", "email": "failed_or_unconfirmed"}}
        response = self.client.post("/daily-news", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "completed_with_delivery_errors")
        self.assertEqual(response.json()["deliveries"]["whatsapp"], "accepted")

    @patch("api.run_daily", return_value={"deliveries": {"email": "failed_or_unconfirmed", "whatsapp": "failed_or_unconfirmed"}})
    def test_both_delivery_failures_return_success_with_channel_results(self, daily):
        response = self.client.post("/daily-news", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "completed_with_delivery_errors")
        self.assertEqual(response.json()["deliveries"], daily.return_value["deliveries"])

    @patch("api.run_daily", side_effect=RuntimeError("Research failed"))
    def test_generation_failure_still_returns_error(self, daily):
        with self.assertLogs("api", level="ERROR"):
            response = self.client.post("/daily-news", headers=self.headers)
        self.assertEqual(response.status_code, 502)

    @patch("api.generate_weekly_digest", return_value={"newsletter_title": "Weekly"})
    def test_weekly_posts_without_email_and_validates_days(self, weekly):
        response = self.client.post("/weekly-digest", headers=self.headers, json={"days": 7})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["linkedin"], "published")
        weekly.assert_called_once_with(days=7, no_email=True)
        self.assertEqual(self.client.post("/weekly-digest", headers=self.headers, json={"days": 0}).status_code, 422)

    @patch("api.generate_weekly_digest", side_effect=RuntimeError("private upstream details"))
    def test_weekly_failure_returns_error_without_leaking_details(self, weekly):
        with self.assertLogs("api", level="ERROR"):
            response = self.client.post("/weekly-digest", headers=self.headers)
        self.assertEqual(response.status_code, 502)
        self.assertNotIn("private upstream details", response.text)

    @patch("api.generate_weekly_digest", return_value=None)
    def test_weekly_no_entries_is_skipped(self, weekly):
        response = self.client.post("/weekly-digest", headers=self.headers)
        self.assertEqual(response.json()["status"], "skipped")


class WeeklyPublishingTests(unittest.TestCase):
    @patch("weekly.digest.get_recent_entries_by_calendar_days")
    @patch("weekly.digest.compile_newsletter", return_value={"linkedin_post": "Weekly digest"})
    @patch("weekly.digest.post_to_linkedin", return_value=False)
    def test_post_failure_raises(self, post, compile_newsletter, entries):
        entries.return_value = [SimpleNamespace(datetime=datetime(2026, 11, 10), topic="AI", content="News")]
        with self.assertRaisesRegex(RuntimeError, "LinkedIn publishing failed"):
            weekly_digest.generate_weekly_digest(no_email=True)

    @patch("weekly.linkedin_connector.requests.post")
    def test_required_headers_and_no_unversioned_retry(self, post):
        post.return_value = SimpleNamespace(status_code=426, text="NONEXISTENT_VERSION")
        with patch.dict(os.environ, {"LINKEDIN_ACCESS_TOKEN": "fake", "LINKEDIN_AUTHOR_URN": "urn:li:person:fake"}):
            self.assertFalse(linkedin_connector.post_to_linkedin("Weekly digest"))
        self.assertEqual(post.call_count, 1)
        headers = post.call_args.kwargs["headers"]
        self.assertEqual(headers["X-Restli-Protocol-Version"], "2.0.0")
        self.assertIn("LinkedIn-Version", headers)


if __name__ == "__main__":
    unittest.main()
