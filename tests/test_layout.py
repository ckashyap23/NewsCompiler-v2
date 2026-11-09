"""Check package entry points and resource locations after restructuring."""
import json
import subprocess
import sys
import unittest
from unittest.mock import patch

from daily import orchestrator, topic_research
from shared import paths, send_email
from weekly import digest, newsletter_compiler


class PackageLayoutTests(unittest.TestCase):
    def test_resources_are_resolved_from_repository_root(self):
        self.assertEqual(topic_research.DEFAULT_SKILL_PATH.parent.parent.parent, paths.REPO_ROOT)
        self.assertTrue(topic_research.DEFAULT_SKILL_PATH.is_file())
        self.assertTrue(newsletter_compiler.DEFAULT_SKILL_PATH.is_file())
        self.assertTrue(newsletter_compiler.DEFAULT_SCHEMA_PATH.is_file())
        self.assertEqual(send_email.ENV_PATH, paths.REPO_ROOT / ".env")
        json.loads(newsletter_compiler.DEFAULT_SCHEMA_PATH.read_text(encoding="utf-8"))

    def test_module_entry_points_show_help_without_running_jobs(self):
        for module in ("daily.orchestrator", "weekly.digest", "shared.send_email"):
            with self.subTest(module=module):
                result = subprocess.run(
                    [sys.executable, "-m", module, "--help"], cwd=paths.REPO_ROOT,
                    capture_output=True, text=True, timeout=30,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("usage:", result.stdout.lower())

    @patch("daily.orchestrator.run")
    def test_daily_cli_reports_partial_failure_as_nonzero(self, run):
        run.side_effect = orchestrator.DailyDeliveryError({"deliveries": {"email": "sent", "whatsapp": "failed_or_unconfirmed"}})
        with patch.object(sys, "argv", ["daily.orchestrator", "--topic", "AI", "reader@example.com"]):
            self.assertEqual(orchestrator.main(), 1)

    @patch("weekly.digest.generate_weekly_digest", side_effect=RuntimeError("Posting failed"))
    def test_weekly_cli_reports_failure_as_nonzero(self, generate):
        with patch.object(sys, "argv", ["weekly.digest", "--no-email"]):
            self.assertEqual(digest.main(), 1)


if __name__ == "__main__":
    unittest.main()
