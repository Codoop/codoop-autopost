import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).parents[1] / "skills/_shared/autopost.py"
CONTENT_TICKET_SCRIPT = Path(__file__).parents[1] / "skills/codoop-content-ticket/scripts/content_ticket.py"
INIT_CONFIG_SCRIPT = Path(__file__).parents[1] / "skills/codoop-autopost-init/scripts/init_config.py"
PYTHON_RUNNER = Path(__file__).parents[1] / "skills/_shared/run-python.sh"
CONTENT_TICKET_RUNNER = Path(__file__).parents[1] / "skills/codoop-content-ticket/scripts/run.sh"
VENDORED_LAST30DAYS = Path(__file__).parents[1] / "skills/last30days/vendor/scripts/last30days.py"
LAST30DAYS_RUNNER = Path(__file__).parents[1] / "skills/last30days/scripts/run.sh"
INIT_CONFIG_RUNNER = Path(__file__).parents[1] / "skills/codoop-autopost-init/scripts/run.sh"
FIRECRAWL_RUNNER = Path(__file__).parents[1] / "skills/firecrawl/scripts/run.sh"
X_TWITTER_RUNNER = Path(__file__).parents[1] / "skills/x-twitter/scripts/run.sh"
INSTALLER = Path(__file__).parents[1] / "scripts/install-skill.sh"
SPEC = importlib.util.spec_from_file_location("autopost", SCRIPT)
autopost = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(autopost)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.workspace = Path(self.directory.name)
        (self.workspace / "PROJECT.md").write_text("# Project\n")
        (self.workspace / "VOICE.md").write_text("# Voice\n")
        self.store = autopost.TicketStore(self.workspace)
        self.draft = self.store.create_ticket("AI research", "A verified claim.")

    def tearDown(self):
        self.directory.cleanup()

    def test_draft_requires_verified_evidence_before_approval(self):
        self.store.submit(self.draft["id"])
        with self.assertRaisesRegex(ValueError, "verified evidence"):
            self.store.approve(self.draft["id"])

    def test_submit_rejects_a_bare_source_label(self):
        self.store.write_draft(self.draft["id"], "A verified claim.\n\nSource: OpenAI")

        with self.assertRaisesRegex(ValueError, "direct URL"):
            self.store.submit(self.draft["id"])

    def test_ticket_keeps_all_stage_artifacts_in_its_folder(self):
        ticket = self.workspace / "content-tickets" / self.draft["id"]

        self.assertEqual(self.draft["status"], "draft")
        self.assertTrue(self.draft["id"].startswith("C-"))
        self.assertTrue((ticket / "ticket.toml").is_file())
        for path in ("discovery", "verification", "writing", "review", "publish"):
            self.assertTrue((ticket / path).is_dir())
        self.assertTrue((ticket / "discovery" / "duplicate-check.md").is_file())
        self.assertEqual((ticket / "writing" / "drafts.md").read_text(), "A verified claim.\n")
        self.assertEqual((ticket / "review" / "final.md").read_text(), "A verified claim.\n")

    def test_draft_rejects_text_over_x_limit(self):
        with self.assertRaisesRegex(ValueError, "280"):
            self.store.create_ticket("AI research", "x" * 281)

    def test_evidence_requires_publication_date_and_explicit_verification(self):
        with self.assertRaisesRegex(ValueError, "publication date"):
            self.store.add_evidence(
                self.draft["id"], "A claim", "https://example.com/news", "official announcement", None, "Original text", True
            )
        self.store.add_evidence(
            self.draft["id"], "A claim", "https://example.com/news", "official announcement", "2026-07-26", "Original text", False
        )
        self.store.submit(self.draft["id"])
        with self.assertRaisesRegex(ValueError, "verified evidence"):
            self.store.approve(self.draft["id"])

    def test_approved_draft_can_be_scheduled_and_published_once(self):
        self.store.add_evidence(
            self.draft["id"], "A claim", "https://example.com/news", "official announcement", "2026-07-26", "Original text", True
        )
        self.store.submit(self.draft["id"])
        self.store.approve(self.draft["id"])
        self.store.schedule(self.draft["id"], datetime.now(UTC) - timedelta(seconds=1))

        published = self.store.publish_due(lambda body: {"id": "123", "url": "https://x.com/me/status/123"})

        self.assertEqual([item["id"] for item in published], [self.draft["id"]])
        self.assertEqual(self.store.get(self.draft["id"])["status"], "done")
        receipt = self.workspace / "content-tickets" / self.draft["id"] / "publish" / "receipt.json"
        self.assertEqual(json.loads(receipt.read_text())["status"], "published")
        self.assertEqual(self.store.publish_due(lambda body: self.fail("must not publish twice")), [])

    def test_failed_publish_keeps_draft_and_error(self):
        self.store.add_evidence(
            self.draft["id"], "A claim", "https://example.com/news", "official announcement", "2026-07-26", "Original text", True
        )
        self.store.submit(self.draft["id"])
        self.store.approve(self.draft["id"])
        self.store.schedule(self.draft["id"], datetime.now(UTC) - timedelta(seconds=1))

        self.store.publish_due(lambda body: (_ for _ in ()).throw(RuntimeError("X unavailable")))

        item = self.store.get(self.draft["id"])
        self.assertEqual(item["status"], "pending")
        self.assertEqual(item["error"], "X unavailable")
        self.assertEqual(item["body"], "A verified claim.")
        self.assertEqual(self.store.publish_due(lambda body: self.fail("must not retry failed post")), [])

    def test_human_confirmed_retry_archives_a_failure_and_reenables_the_ticket(self):
        self.store.add_evidence(
            self.draft["id"], "A claim", "https://example.com/news", "official announcement", "2026-07-26", "Original text", True
        )
        self.store.submit(self.draft["id"])
        self.store.approve(self.draft["id"])
        self.store.schedule(self.draft["id"], datetime.now(UTC) - timedelta(seconds=1))
        self.store.publish_due(lambda body: (_ for _ in ()).throw(RuntimeError("X unavailable")))

        retried = self.store.retry(self.draft["id"])

        ticket = self.workspace / "content-tickets" / self.draft["id"]
        self.assertEqual(retried["status"], "pending")
        self.assertIn("retried_at", retried)
        self.assertFalse((ticket / "publish" / "receipt.json").exists())
        attempts = list((ticket / "publish" / "attempts").glob("failed-*.json"))
        self.assertEqual(json.loads(attempts[0].read_text())["error"], "X unavailable")
        self.assertEqual([item["id"] for item in self.store.due()], [self.draft["id"]])

    def test_due_queue_excludes_future_posts(self):
        self.store.add_evidence(
            self.draft["id"], "A claim", "https://example.com/news", "official announcement", "2026-07-26", "Original text", True
        )
        self.store.submit(self.draft["id"])
        self.store.approve(self.draft["id"])
        self.store.schedule(self.draft["id"], datetime.now(UTC) + timedelta(days=1))

        self.assertEqual(self.store.due(), [])

    def test_publish_lock_prevents_a_second_publisher_from_sending(self):
        self.store.add_evidence(
            self.draft["id"], "A claim", "https://example.com/news", "official announcement", "2026-07-26", "Original text", True
        )
        self.store.submit(self.draft["id"])
        self.store.approve(self.draft["id"])
        self.store.schedule(self.draft["id"], datetime.now(UTC) - timedelta(seconds=1))
        lock = self.workspace / "content-tickets" / self.draft["id"] / "publish" / "publish.lock"
        lock.write_text("another publisher")

        self.assertEqual(self.store.publish_due(lambda body: self.fail("must not publish while locked")), [])

    def test_creating_a_ticket_requires_confirmed_project_standards(self):
        workspace = Path(self.directory.name) / "missing-standards"
        store = autopost.TicketStore(workspace)

        with self.assertRaisesRegex(ValueError, "codoop-autopost-init"):
            store.create_ticket("AI research", "A verified claim.")

    def test_due_queue_requires_current_project_standards(self):
        (self.workspace / "VOICE.md").unlink()

        with self.assertRaisesRegex(ValueError, "codoop-autopost-init"):
            self.store.due()

    def test_ticket_can_be_created_before_discovery_and_written_later(self):
        ticket = self.store.create_ticket("AI research")

        self.assertEqual(ticket["body"], "")
        self.assertEqual((self.workspace / "content-tickets" / ticket["id"] / "discovery" / "raw.json").read_text(), "{}\n")
        written = self.store.write_draft(ticket["id"], "A verified claim.")

        self.assertEqual(written["body"], "A verified claim.")
        self.assertEqual(
            (self.workspace / "content-tickets" / ticket["id"] / "review" / "final.md").read_text(),
            "A verified claim.\n",
        )

    def test_discovery_uses_the_ticket_topic_and_saves_raw_output(self):
        result = {"results": [{"title": "A discussion", "url": "https://example.com"}]}

        with patch.object(autopost, "discover", return_value=result) as discover:
            saved = self.store.discover(self.draft["id"])

        ticket = self.workspace / "content-tickets" / self.draft["id"]
        discover.assert_called_once_with("AI research")
        self.assertEqual(saved, result)
        self.assertEqual(json.loads((ticket / "discovery" / "raw.json").read_text()), result)
        self.assertIn("discovered_at", self.store.get(self.draft["id"]))

    def test_dedupe_discards_a_recent_pending_ticket_with_the_same_source_url(self):
        previous = self.store.create_ticket("Previous topic")
        self.store.write_draft(previous["id"], "A prior verified post.")
        self.store.add_evidence(
            previous["id"], "A claim", "https://example.com/news", "official announcement", "2026-07-26", "Original text", True
        )
        self.store.submit(previous["id"])
        self.store.approve(previous["id"])

        result = self.store.dedupe(self.draft["id"], "https://example.com/news?utm_source=last30days")

        ticket = self.workspace / "content-tickets" / self.draft["id"]
        self.assertEqual(result["decision"], "discarded")
        self.assertEqual(result["matches"][0]["ticket_id"], previous["id"])
        self.assertEqual(self.store.get(self.draft["id"])["status"], "discarded")
        self.assertIn("Decision: discarded", (ticket / "discovery" / "duplicate-check.md").read_text())
        with self.assertRaisesRegex(ValueError, "draft"):
            self.store.write_draft(self.draft["id"], "Must not continue")

    def test_dedupe_keeps_a_new_source_in_draft(self):
        result = self.store.dedupe(self.draft["id"], "https://example.com/new-source")

        self.assertEqual(result["decision"], "clear")
        self.assertEqual(self.store.get(self.draft["id"])["status"], "draft")

    def test_discard_records_a_reason_before_source_verification(self):
        discarded = self.store.discard(self.draft["id"], "Same event as a recent post with a different source URL.")

        self.assertEqual(discarded["status"], "discarded")
        check = self.workspace / "content-tickets" / self.draft["id"] / "discovery" / "duplicate-check.md"
        self.assertIn("Same event as a recent post", check.read_text())

    def test_cli_creates_an_empty_content_ticket_before_writing(self):
        created = subprocess.run(
            [sys.executable, str(SCRIPT), "--workspace", str(self.workspace), "create", "AI research"],
            capture_output=True,
            check=True,
            text=True,
        )
        ticket = json.loads(created.stdout)
        written = subprocess.run(
            [sys.executable, str(SCRIPT), "--workspace", str(self.workspace), "write", ticket["id"], "A verified claim."],
            capture_output=True,
            check=True,
            text=True,
        )

        self.assertEqual(ticket["body"], "")
        self.assertEqual(json.loads(written.stdout)["body"], "A verified claim.")


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

        self.assertEqual(command[-2:], ["AI agents", "--emit=json"])

    def test_discovery_uses_the_vendored_runtime_without_downloading(self):
        with patch.dict(os.environ, {"CODOOP_LAST30DAYS_DIR": ""}):
            script = autopost.ensure_discovery_runtime()

        self.assertEqual(script, VENDORED_LAST30DAYS)
        self.assertTrue(script.is_file())

    def test_configuration_reads_file_and_allows_environment_override(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text('[firecrawl]\napi_key = "file-key"\napi_url = "https://firecrawl.example/v2"\n\n[x]\nconsumer_key = "consumer"\nconsumer_secret = "secret"\naccess_token = "token"\naccess_secret = "access-secret"\n')
            with patch.dict(os.environ, {"CODOOP_AUTOPOST_CONFIG": str(path), "FIRECRAWL_API_KEY": "environment-key"}):
                settings = autopost.Settings.load()

        self.assertEqual(settings.firecrawl_api_key, "environment-key")
        self.assertEqual(settings.firecrawl_api_url, "https://firecrawl.example/v2")
        self.assertEqual(settings.x_credentials, ("consumer", "secret", "token", "access-secret"))

    def test_configuration_reads_workspace_config_by_default(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "config.toml").write_text('[firecrawl]\napi_key = "workspace-key"\n')
            previous_directory = Path.cwd()
            try:
                os.chdir(directory)
                with patch.dict(os.environ, {}, clear=True):
                    settings = autopost.Settings.load()
            finally:
                os.chdir(previous_directory)

        self.assertEqual(settings.firecrawl_api_key, "workspace-key")

    def test_python_runner_honors_an_explicit_compatible_interpreter(self):
        self.assertGreaterEqual(sys.version_info[:2], (3, 12))
        result = subprocess.run(
            [str(PYTHON_RUNNER), "-c", "import sys; print('.'.join(map(str, sys.version_info[:2])))"],
            capture_output=True,
            check=True,
            text=True,
            env={**os.environ, "CODOOP_AUTOPOST_PYTHON": sys.executable},
        )

        self.assertGreaterEqual(tuple(map(int, result.stdout.strip().split("."))), (3, 12))


class PluginSkillTests(unittest.TestCase):
    def test_plugin_bundles_init_ticket_and_grilling_skills(self):
        root = Path(__file__).parents[1] / "skills"

        self.assertTrue((root / "codoop-autopost-init" / "SKILL.md").is_file())
        self.assertTrue((root / "codoop-content-ticket" / "SKILL.md").is_file())
        self.assertTrue((root / "grilling" / "SKILL.md").is_file())
        self.assertTrue(CONTENT_TICKET_SCRIPT.is_file())
        self.assertTrue((root / "codoop-autopost-init" / "config.example.toml").is_file())
        self.assertTrue(INIT_CONFIG_SCRIPT.is_file())
        init_instructions = (root / "codoop-autopost-init" / "SKILL.md").read_text()
        self.assertIn("Configuration handoff", init_instructions)
        self.assertIn("X Developer Console", init_instructions)

    def test_init_config_creates_a_private_template_without_overwriting_existing_values(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            result = subprocess.run(
                [sys.executable, str(INIT_CONFIG_SCRIPT), "--workspace", str(workspace)],
                capture_output=True,
                check=True,
                text=True,
            )
            config = workspace / "config.toml"
            self.assertIn("Created", result.stdout)
            self.assertIn('[firecrawl]', config.read_text())
            self.assertEqual(config.stat().st_mode & 0o777, 0o600)
            config.write_text('marker = "keep"\n')
            subprocess.run([sys.executable, str(INIT_CONFIG_SCRIPT), "--workspace", str(workspace)], check=True)
            self.assertEqual(config.read_text(), 'marker = "keep"\n')

    def test_content_ticket_wrapper_uses_the_ticket_workflow(self):
        result = subprocess.run([str(CONTENT_TICKET_RUNNER), "--help"], capture_output=True, text=True)

        self.assertEqual(result.returncode, 0)
        self.assertIn("Create an empty content ticket", result.stdout)

    def test_last30days_runner_uses_the_vendored_runtime(self):
        result = subprocess.run([str(LAST30DAYS_RUNNER), "--init"], capture_output=True, text=True)

        self.assertEqual(result.returncode, 0)
        self.assertIn(str(VENDORED_LAST30DAYS.parents[1]), result.stdout)
        self.assertTrue((VENDORED_LAST30DAYS.parents[1] / "LICENSE").is_file())

    def test_standalone_launchers_do_not_need_the_shared_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for runner in (INIT_CONFIG_RUNNER, FIRECRAWL_RUNNER, X_TWITTER_RUNNER):
                skill = runner.parents[1]
                installed = root / skill.name
                shutil.copytree(skill, installed)
                result = subprocess.run([str(installed / "scripts" / "run.sh"), "--help"], capture_output=True, text=True)

                self.assertEqual(result.returncode, 0, result.stderr)

    def test_development_installer_copies_the_shared_runtime_for_content_tickets(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                ["bash", str(INSTALLER), "--agent", "codex", "--skill", "codoop-content-ticket"],
                capture_output=True,
                text=True,
                env={**os.environ, "CODEX_HOME": directory},
            )
            installed = Path(directory) / "skills"

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((installed / "_shared" / "autopost.py").is_file())
            help_result = subprocess.run(
                [str(installed / "codoop-content-ticket" / "scripts" / "run.sh"), "--help"], capture_output=True, text=True
            )
            self.assertEqual(help_result.returncode, 0, help_result.stderr)

    def test_social_content_requires_direct_source_urls(self):
        instructions = (Path(__file__).parents[1] / "skills/social-content/SKILL.md").read_text()

        self.assertIn("[Source: Name](https://...)", instructions)


if __name__ == "__main__":
    unittest.main()
