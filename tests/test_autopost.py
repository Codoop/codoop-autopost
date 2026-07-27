import importlib.util
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / ".agents/skills/codoop-autopost/scripts/autopost.py"
SPEC = importlib.util.spec_from_file_location("autopost", SCRIPT)
autopost = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(autopost)


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


if __name__ == "__main__":
    unittest.main()
