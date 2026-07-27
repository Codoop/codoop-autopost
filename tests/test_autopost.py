import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).parents[1] / "skills/codoop-autopost/scripts/autopost.py"
BOOTSTRAP = Path(__file__).parents[1] / "skills/codoop-autopost/scripts/bootstrap.py"
SPEC = importlib.util.spec_from_file_location("autopost", SCRIPT)
autopost = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(autopost)
BOOTSTRAP_SPEC = importlib.util.spec_from_file_location("bootstrap", BOOTSTRAP)
bootstrap = importlib.util.module_from_spec(BOOTSTRAP_SPEC)
BOOTSTRAP_SPEC.loader.exec_module(bootstrap)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.store = autopost.Store(Path(self.directory.name) / "autopost.db")
        self.draft = self.store.create_draft("AI research", "A verified claim.")

    def tearDown(self):
        self.directory.cleanup()

    def test_draft_requires_verified_evidence_before_approval(self):
        with self.assertRaisesRegex(ValueError, "verified evidence"):
            self.store.approve(self.draft["id"])

    def test_approved_draft_can_be_scheduled_and_published_once(self):
        self.store.add_evidence(
            self.draft["id"], "A claim", "https://example.com/news", "official announcement", "2026-07-26", "Original text"
        )
        self.store.approve(self.draft["id"])
        self.store.schedule(self.draft["id"], datetime.now(UTC) - timedelta(seconds=1))

        published = self.store.publish_due(lambda body: {"id": "123", "url": "https://x.com/me/status/123"})

        self.assertEqual([item["id"] for item in published], [self.draft["id"]])
        self.assertEqual(self.store.get(self.draft["id"])["status"], "published")
        self.assertEqual(self.store.publish_due(lambda body: self.fail("must not publish twice")), [])

    def test_failed_publish_keeps_draft_and_error(self):
        self.store.add_evidence(
            self.draft["id"], "A claim", "https://example.com/news", "official announcement", "2026-07-26", "Original text"
        )
        self.store.approve(self.draft["id"])
        self.store.schedule(self.draft["id"], datetime.now(UTC) - timedelta(seconds=1))

        self.store.publish_due(lambda body: (_ for _ in ()).throw(RuntimeError("X unavailable")))

        item = self.store.get(self.draft["id"])
        self.assertEqual(item["status"], "failed")
        self.assertEqual(item["error"], "X unavailable")
        self.assertEqual(item["body"], "A verified claim.")

    def test_due_queue_excludes_future_posts(self):
        self.store.add_evidence(
            self.draft["id"], "A claim", "https://example.com/news", "official announcement", "2026-07-26", "Original text"
        )
        self.store.approve(self.draft["id"])
        self.store.schedule(self.draft["id"], datetime.now(UTC) + timedelta(days=1))

        self.assertEqual(self.store.due(), [])


class ExternalAdapterTests(unittest.TestCase):
    def test_firecrawl_scrape_sends_bearer_token_and_returns_markdown(self):
        class Response:
            def read(self):
                return json.dumps({"success": True, "data": {"markdown": "# Primary source"}}).encode()

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        with patch.object(autopost.request, "urlopen", return_value=Response()) as urlopen:
            result = autopost.Firecrawl("https://firecrawl.example/v2", "secret").scrape("https://example.com/news")

        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://firecrawl.example/v2/scrape")
        self.assertEqual(request.get_header("Authorization"), "Bearer secret")
        self.assertEqual(json.loads(request.data)["url"], "https://example.com/news")
        self.assertEqual(result, "# Primary source")

    def test_x_publisher_rejects_posts_over_280_characters(self):
        publisher = autopost.XPublisher("key", "secret", "token", "token-secret")

        with self.assertRaisesRegex(ValueError, "280"):
            publisher.post("x" * 281)

    def test_last30days_command_uses_machine_readable_output(self):
        command = autopost.last30days_argv("AI agents", Path("/tmp/last30days.py"))

        self.assertEqual(command[-4:], ["AI agents", "--emit=json", "--save-dir", ".codoop-autopost/research"])

    def test_bootstrap_help_does_not_download_a_vendor(self):
        result = subprocess.run([sys.executable, str(BOOTSTRAP), "--help"], capture_output=True, text=True)

        self.assertEqual(result.returncode, 0)
        self.assertIn("Initialize the bundled last30days runtime", result.stdout)

    def test_vendor_runtime_lives_outside_the_installed_skill(self):
        self.assertEqual(bootstrap.vendor_dir(Path("/tmp/codoop-data")), Path("/tmp/codoop-data/last30days"))


if __name__ == "__main__":
    unittest.main()
