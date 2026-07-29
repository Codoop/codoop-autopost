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
CONTENT_DISCOVERY_RUNNER = Path(__file__).parents[1] / "skills/codoop-content-discovery/scripts/run.sh"
VENDORED_LAST30DAYS = Path(__file__).parents[1] / "skills/last30days/vendor/scripts/last30days.py"
LAST30DAYS_RUNNER = Path(__file__).parents[1] / "skills/last30days/scripts/run.sh"
INIT_CONFIG_RUNNER = Path(__file__).parents[1] / "skills/codoop-autopost-init/scripts/run.sh"
FIRECRAWL_RUNNER = Path(__file__).parents[1] / "skills/firecrawl/scripts/run.sh"
X_TWITTER_RUNNER = Path(__file__).parents[1] / "skills/x-twitter/scripts/run.sh"
INSTALLER = Path(__file__).parents[1] / "scripts/install-skill.sh"
SPEC = importlib.util.spec_from_file_location("autopost", SCRIPT)
autopost = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(autopost)


def enqueue_test_lead(store, workspace, url="https://example.com/news", title="AI research"):
    candidate_id = f"candidate-{os.urandom(4).hex()}"
    result = {
        "generated_at": "2026-07-28T10:00:00+00:00",
        "results": [{
            "candidate_id": candidate_id,
            "title": title,
            "source": "test",
            "url": url,
            "published_at": "2026-07-28T09:00:00+00:00",
            "summary": "Unverified discovery summary",
            "engagement": 10,
        }],
    }
    with patch.object(autopost, "discover", return_value=result):
        run = store.start_discovery("AI tools", f"{title} {url}")
    review = workspace / "content-leads" / "runs" / run["id"] / "value-review.md"
    review.write_text(f"# Value Review\n\n| 1 | {candidate_id} | go | audience-value |\n")
    store.complete_discovery(run["id"], [f"{candidate_id}:audience-value"])
    return next(lead for lead in store.list_leads("available") if lead["candidate_id"] == candidate_id)


def claim_test_ticket(store, workspace, url="https://example.com/news", title="AI research", body=""):
    lead = enqueue_test_lead(store, workspace, url, title)
    ticket = store.claim(lead["id"])
    if not body:
        return ticket
    store.dedupe(ticket["id"])
    store.scrape_source(ticket["id"], lambda source_url: f"# Primary source\n\n{source_url}")
    store.add_evidence(
        ticket["id"], "Verified claim", ticket["source_url"], "primary source", "2026-07-28", "Original text", True
    )
    report = workspace / "content-tickets" / ticket["id"] / "verification" / "value-review.md"
    report.write_text("# Verified Value Review\n\n- Verdict: go\n")
    store.record_post_review(ticket["id"], "go", report)
    return store.write_draft(ticket["id"], body)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.workspace = Path(self.directory.name)
        (self.workspace / "PROJECT.md").write_text("# Project\n")
        (self.workspace / "VOICE.md").write_text("# Voice\n")
        self.store = autopost.TicketStore(self.workspace)
        self.draft = claim_test_ticket(self.store, self.workspace, body="A verified claim.")

    def tearDown(self):
        self.directory.cleanup()

    def test_post_review_requires_verified_evidence(self):
        ticket = claim_test_ticket(self.store, self.workspace, "https://example.com/no-evidence")
        self.store.dedupe(ticket["id"])
        self.store.scrape_source(ticket["id"], lambda url: "# Source")
        report = self.workspace / "content-tickets" / ticket["id"] / "verification" / "value-review.md"
        report.write_text("# Verified Value Review\n\n- Verdict: go\n")

        with self.assertRaisesRegex(ValueError, "verified evidence"):
            self.store.record_post_review(ticket["id"], "go", report)

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
            self.store.write_draft(self.draft["id"], "x" * 281)

    def test_evidence_requires_publication_date_and_explicit_verification(self):
        ticket = claim_test_ticket(self.store, self.workspace, "https://example.com/evidence")
        self.store.dedupe(ticket["id"])
        self.store.scrape_source(ticket["id"], lambda url: "# Source")
        with self.assertRaisesRegex(ValueError, "publication date"):
            self.store.add_evidence(
                ticket["id"], "A claim", "https://example.com/evidence", "official announcement", None, "Original text", True
            )
        self.store.add_evidence(
            ticket["id"], "A claim", "https://example.com/evidence", "official announcement", "2026-07-26", "Original text", False
        )
        report = self.workspace / "content-tickets" / ticket["id"] / "verification" / "value-review.md"
        report.write_text("# Verified Value Review\n\n- Verdict: go\n")
        with self.assertRaisesRegex(ValueError, "verified evidence"):
            self.store.record_post_review(ticket["id"], "go", report)

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
        self.assertEqual(self.store.list_leads("claimed"), [])
        self.assertEqual(self.store.list_leads("consumed")[0]["ticket_id"], self.draft["id"])
        receipt = self.workspace / "content-tickets" / self.draft["id"] / "publish" / "receipt.json"
        self.assertEqual(json.loads(receipt.read_text())["status"], "published")
        self.assertEqual(self.store.publish_due(lambda body: self.fail("must not publish twice")), [])
        performance = self.store.record_performance(self.draft["id"], 1000, 4, 8)
        self.assertEqual(performance["interactions_per_1000_impressions"], 12.0)
        self.assertTrue((receipt.parent / "performance.toml").is_file())

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
        self.assertEqual(self.store.list_leads("claimed")[0]["ticket_id"], self.draft["id"])
        self.assertEqual(self.store.publish_due(lambda body: self.fail("must not retry failed post")), [])

    def test_lead_move_error_after_x_success_does_not_turn_the_receipt_into_a_failure(self):
        self.store.submit(self.draft["id"])
        self.store.approve(self.draft["id"])
        self.store.schedule(self.draft["id"], datetime.now(UTC) - timedelta(seconds=1))

        with patch.object(self.store, "move_lead", side_effect=RuntimeError("filesystem unavailable")):
            published = self.store.publish_due(lambda body: {"id": "123", "url": "https://x.com/me/status/123"})

        receipt = self.workspace / "content-tickets" / self.draft["id"] / "publish" / "receipt.json"
        outcome = json.loads(receipt.read_text())
        self.assertEqual([item["id"] for item in published], [self.draft["id"]])
        self.assertEqual(outcome["status"], "published")
        self.assertEqual(outcome["lead_transition_error"], "filesystem unavailable")
        self.assertEqual(self.store.get(self.draft["id"])["status"], "done")

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
            with patch.object(autopost, "discover", return_value={"results": []}):
                store.start_discovery("AI tools", "AI research")

    def test_due_queue_requires_current_project_standards(self):
        (self.workspace / "VOICE.md").unlink()

        with self.assertRaisesRegex(ValueError, "codoop-autopost-init"):
            self.store.due()

    def test_claimed_ticket_can_be_written_later(self):
        ticket = claim_test_ticket(self.store, self.workspace, "https://example.com/later")

        self.assertEqual(ticket["body"], "")
        self.assertNotEqual((self.workspace / "content-tickets" / ticket["id"] / "discovery" / "raw.json").read_text(), "{}\n")
        with self.assertRaisesRegex(ValueError, "duplicate check"):
            self.store.write_draft(ticket["id"], "A verified claim.")
        self.store.dedupe(ticket["id"])
        self.store.scrape_source(ticket["id"], lambda url: "# Source")
        self.store.add_evidence(
            ticket["id"], "A claim", ticket["source_url"], "primary source", "2026-07-28", "Excerpt", True
        )
        report = self.workspace / "content-tickets" / ticket["id"] / "verification" / "value-review.md"
        report.write_text("# Verified Value Review\n\n- Verdict: go\n")
        self.store.record_post_review(ticket["id"], "go", report)
        written = self.store.write_draft(ticket["id"], "A verified claim.")

        self.assertEqual(written["body"], "A verified claim.")
        self.assertEqual(
            (self.workspace / "content-tickets" / ticket["id"] / "review" / "final.md").read_text(),
            "A verified claim.\n",
        )

    def test_claimed_ticket_keeps_the_discovery_run_and_first_value_review(self):
        ticket = self.workspace / "content-tickets" / self.draft["id"]
        raw = json.loads((ticket / "discovery" / "raw.json").read_text())

        self.assertEqual(raw["results"][0]["title"], "AI research")
        self.assertIn("# Value Review", (ticket / "discovery" / "value-review.md").read_text())
        self.assertIn("lead_id", self.store.get(self.draft["id"]))

    def test_dedupe_discards_a_recent_pending_ticket_with_the_same_source_url(self):
        previous = claim_test_ticket(
            self.store, self.workspace, "https://example.com/previous", "Previous topic", "A prior verified post."
        )
        self.store.add_evidence(
            previous["id"], "A claim", "https://example.com/news", "official announcement", "2026-07-26", "Original text", True
        )
        self.store.submit(previous["id"])
        self.store.approve(previous["id"])

        result = self.store.dedupe(self.draft["id"])

        ticket = self.workspace / "content-tickets" / self.draft["id"]
        self.assertEqual(result["decision"], "discarded")
        self.assertEqual(result["matches"][0]["ticket_id"], previous["id"])
        self.assertEqual(self.store.get(self.draft["id"])["status"], "discarded")
        self.assertIn("Decision: discarded", (ticket / "discovery" / "duplicate-check.md").read_text())
        with self.assertRaisesRegex(ValueError, "draft"):
            self.store.write_draft(self.draft["id"], "Must not continue")

    def test_dedupe_keeps_a_new_source_in_draft(self):
        result = self.store.dedupe(self.draft["id"])

        self.assertEqual(result["decision"], "clear")
        self.assertEqual(self.store.get(self.draft["id"])["status"], "draft")

    def test_discard_records_a_reason_before_source_verification(self):
        discarded = self.store.discard(self.draft["id"], "Same event as a recent post with a different source URL.")

        self.assertEqual(discarded["status"], "discarded")
        check = self.workspace / "content-tickets" / self.draft["id"] / "discovery" / "duplicate-check.md"
        self.assertIn("Same event as a recent post", check.read_text())

    def test_cli_claim_does_not_allow_writing_before_verification(self):
        lead = enqueue_test_lead(self.store, self.workspace, "https://example.com/cli")
        created = subprocess.run(
            [sys.executable, str(SCRIPT), "--workspace", str(self.workspace), "claim", lead["id"]],
            capture_output=True,
            check=True,
            text=True,
        )
        ticket = json.loads(created.stdout)
        written = subprocess.run(
            [sys.executable, str(SCRIPT), "--workspace", str(self.workspace), "write", ticket["id"], "A verified claim."],
            capture_output=True,
            text=True,
        )

        self.assertEqual(ticket["body"], "")
        self.assertEqual(ticket["lead_id"], lead["id"])
        self.assertNotEqual(written.returncode, 0)
        self.assertIn("duplicate check", written.stderr)


class LeadWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.workspace = Path(self.directory.name)
        (self.workspace / "PROJECT.md").write_text("# Project\n")
        (self.workspace / "VOICE.md").write_text("# Voice\n")
        self.store = autopost.TicketStore(self.workspace)

    def tearDown(self):
        self.directory.cleanup()

    def _start(self, url: str = "https://example.com/new?utm_source=x", engagement: int = 12) -> dict:
        result = {
            "generated_at": "2026-07-28T10:00:00+00:00",
            "results": [
                {
                    "candidate_id": "candidate-1",
                    "title": "Useful development",
                    "source": "reddit",
                    "url": url,
                    "published_at": "2026-07-28T09:00:00+00:00",
                    "summary": "Discovery-only summary",
                    "engagement": engagement,
                },
                {
                    "candidate_id": "candidate-2",
                    "title": "Weak development",
                    "source": "x",
                    "url": "https://example.com/weak",
                    "published_at": "2026-07-28T08:00:00+00:00",
                    "summary": "Everything fits in the post",
                    "engagement": 999,
                },
            ],
        }
        with patch.object(autopost, "discover", return_value=result):
            return self.store.start_discovery("AI tools", f"AI tools workflow {url}")

    def _review(self, run_id: str) -> None:
        path = self.workspace / "content-leads" / "runs" / run_id / "value-review.md"
        path.write_text(
            "# Value Review\n\n"
            "| 1 | candidate-1 | go | audience-value |\n"
            "| 2 | candidate-2 | weak | none |\n"
        )

    def test_discovery_run_enqueues_only_explicit_go_candidates(self):
        started = self._start()
        self._review(started["id"])

        completed = self.store.complete_discovery(started["id"], ["candidate-1:audience-value"])

        self.assertEqual(started["review_candidate_ids"], ["candidate-1", "candidate-2"])
        self.assertEqual(completed["status"], "complete")
        leads = self.store.list_leads("available")
        self.assertEqual([lead["candidate_id"] for lead in leads], ["candidate-1"])
        self.assertEqual(leads[0]["canonical_url"], "https://example.com/new")
        self.assertEqual(leads[0]["pass_basis"], "audience-value")
        self.assertEqual(leads[0]["original_verdict"], "go")
        self.assertTrue((self.workspace / "content-leads" / "runs" / started["id"] / "raw.json").is_file())

    def test_discovery_run_with_no_go_candidates_completes_without_a_lead(self):
        started = self._start()
        review = self.workspace / "content-leads" / "runs" / started["id"] / "value-review.md"
        review.write_text(
            "# Value Review\n\nNo candidate is worth source verification in this discovery run.\n"
        )

        completed = self.store.complete_discovery(started["id"], [])

        self.assertEqual(completed["status"], "complete")
        self.assertEqual(self.store.list_leads("available"), [])

    def test_discovery_does_not_enqueue_a_candidate_without_a_go_review(self):
        started = self._start()
        review = self.workspace / "content-leads" / "runs" / started["id"] / "value-review.md"
        review.write_text("# Value Review\n\n| 1 | candidate-1 | weak | none |\n")

        with self.assertRaisesRegex(ValueError, "go verdict"):
            self.store.complete_discovery(started["id"], ["candidate-1:audience-value"])

    def test_discovery_rejects_the_previous_normalized_query(self):
        started = self._start()

        with patch.object(autopost, "discover", return_value={"results": []}):
            with self.assertRaisesRegex(ValueError, "previous discovery query"):
                self.store.start_discovery("AI tools", f"  {started['query'].upper()}  ")

    def test_repeated_canonical_url_updates_existing_lead_without_re_review(self):
        first = self._start()
        self._review(first["id"])
        self.store.complete_discovery(first["id"], ["candidate-1:audience-value"])
        original = self.store.list_leads("available")[0]

        second = self._start("https://EXAMPLE.com/new/?utm_campaign=again", engagement=200)

        leads = self.store.list_leads("available")
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0]["id"], original["id"])
        self.assertNotEqual(leads[0]["last_seen_at"], original["last_seen_at"])
        self.assertEqual(leads[0]["engagement"], "200")
        self.assertEqual(second["review_candidate_ids"], ["candidate-2"])

    def test_claim_is_atomic_and_rerun_resumes_the_same_ticket(self):
        started = self._start()
        self._review(started["id"])
        self.store.complete_discovery(started["id"], ["candidate-1:audience-value"])
        lead_id = self.store.list_leads("available")[0]["id"]

        ticket = self.store.claim(lead_id)
        resumed = self.store.claim(lead_id)

        self.assertEqual(resumed["id"], ticket["id"])
        self.assertEqual(ticket["lead_id"], lead_id)
        self.assertEqual(self.store.list_leads("available"), [])
        claimed = self.store.list_leads("claimed")
        self.assertEqual(claimed[0]["ticket_id"], ticket["id"])

    def test_claimed_lead_moves_to_rejected_or_consumed_with_a_reason_and_time(self):
        started = self._start()
        self._review(started["id"])
        self.store.complete_discovery(started["id"], ["candidate-1:audience-value"])
        first_lead = self.store.list_leads("available")[0]
        first_ticket = self.store.claim(first_lead["id"])

        rejected = self.store.move_lead(first_ticket["id"], "rejected", "Verified source had no unique payoff.")

        self.assertEqual(rejected["status"], "rejected")
        self.assertIn("rejected_at", rejected)
        self.assertEqual(rejected["status_reason"], "Verified source had no unique payoff.")

        second_run = self._start("https://example.com/another")
        self._review(second_run["id"])
        self.store.complete_discovery(second_run["id"], ["candidate-1:breakout-trend"])
        second_lead = self.store.list_leads("available")[0]
        second_ticket = self.store.claim(second_lead["id"])

        consumed = self.store.move_lead(second_ticket["id"], "consumed", "Published.")

        self.assertEqual(consumed["status"], "consumed")
        self.assertIn("published_at", consumed)

    def test_dedupe_and_scrape_are_bound_to_the_claimed_lead_url(self):
        started = self._start()
        self._review(started["id"])
        self.store.complete_discovery(started["id"], ["candidate-1:audience-value"])
        lead = self.store.list_leads("available")[0]
        ticket = self.store.claim(lead["id"])

        with self.assertRaisesRegex(ValueError, "duplicate check"):
            self.store.scrape_source(ticket["id"], lambda url: "# Must not run")

        duplicate = self.store.dedupe(ticket["id"])
        scraped = self.store.scrape_source(ticket["id"], lambda url: f"# Source\n\n{url}")

        self.assertEqual(duplicate["decision"], "clear")
        self.assertEqual(scraped["url"], lead["canonical_url"])
        snapshot = self.workspace / "content-tickets" / ticket["id"] / "verification" / "source-snapshots" / "source.md"
        self.assertIn(lead["canonical_url"], snapshot.read_text())

    def test_writing_requires_bound_source_evidence_and_a_go_post_review(self):
        started = self._start()
        self._review(started["id"])
        self.store.complete_discovery(started["id"], ["candidate-1:breakout-trend"])
        ticket = self.store.claim(self.store.list_leads("available")[0]["id"])
        report = self.workspace / "content-tickets" / ticket["id"] / "verification" / "value-review.md"
        report.write_text("# Verified Value Review\n\n- Verdict: go\n")

        with self.assertRaisesRegex(ValueError, "duplicate check"):
            self.store.write_draft(ticket["id"], "Must not write yet.")
        self.store.dedupe(ticket["id"])
        self.store.scrape_source(ticket["id"], lambda url: "# Verified source")
        with self.assertRaisesRegex(ValueError, "verified evidence"):
            self.store.record_post_review(ticket["id"], "go", report)
        self.store.add_evidence(
            ticket["id"], "Verified claim", ticket["source_url"], "primary source", "2026-07-28", "Source excerpt", True
        )
        self.store.record_post_review(ticket["id"], "go", report)

        written = self.store.write_draft(ticket["id"], "Now the value is verified.")

        self.assertEqual(written["body"], "Now the value is verified.")
        self.assertEqual(written["post_value_verdict"], "go")

    def test_failed_post_review_rejects_the_lead_before_writing(self):
        started = self._start()
        self._review(started["id"])
        self.store.complete_discovery(started["id"], ["candidate-1:breakout-trend"])
        ticket = self.store.claim(self.store.list_leads("available")[0]["id"])
        self.store.dedupe(ticket["id"])
        self.store.scrape_source(ticket["id"], lambda url: "# Verified source")
        self.store.add_evidence(
            ticket["id"], "Verified claim", ticket["source_url"], "primary source", "2026-07-28", "Source excerpt", True
        )
        report = self.workspace / "content-tickets" / ticket["id"] / "verification" / "value-review.md"
        report.write_text("# Verified Value Review\n\n- Verdict: weak\n- Reason: no unique payoff\n")

        reviewed = self.store.record_post_review(ticket["id"], "weak", report)

        self.assertEqual(reviewed["status"], "discarded")
        self.assertEqual(self.store.list_leads("claimed"), [])
        self.assertEqual(self.store.list_leads("rejected")[0]["pass_basis"], "breakout-trend")
        with self.assertRaisesRegex(ValueError, "draft"):
            self.store.write_draft(ticket["id"], "Must not write.")

    def test_human_override_preserves_the_run_review_and_requires_a_reason(self):
        started = self._start()
        self._review(started["id"])
        self.store.complete_discovery(started["id"], ["candidate-1:audience-value"])
        review = self.workspace / "content-leads" / "runs" / started["id"] / "value-review.md"
        original_review = review.read_text()

        with self.assertRaisesRegex(ValueError, "reason"):
            self.store.promote(started["id"], "candidate-2", "")
        promoted = self.store.promote(started["id"], "candidate-2", "Human sees a timely audience question.")

        self.assertEqual(review.read_text(), original_review)
        self.assertEqual(promoted["pass_basis"], "human-override")
        self.assertEqual(promoted["override_reason"], "Human sees a timely audience question.")
        self.assertEqual(promoted["original_verdict"], "preserved-in-run-review")

    def test_performance_can_only_be_recorded_for_a_published_ticket(self):
        started = self._start()
        self._review(started["id"])
        self.store.complete_discovery(started["id"], ["candidate-1:audience-value"])
        ticket = self.store.claim(self.store.list_leads("available")[0]["id"])

        with self.assertRaisesRegex(ValueError, "published"):
            self.store.record_performance(ticket["id"], 1000, 4, 8)


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
        self.assertTrue((root / "codoop-content-discovery" / "SKILL.md").is_file())
        self.assertTrue((root / "grilling" / "SKILL.md").is_file())
        self.assertTrue(CONTENT_TICKET_SCRIPT.is_file())
        self.assertTrue((root / "codoop-autopost-init" / "config.example.toml").is_file())
        self.assertTrue(INIT_CONFIG_SCRIPT.is_file())
        init_instructions = (root / "codoop-autopost-init" / "SKILL.md").read_text()
        self.assertIn("Configuration handoff", init_instructions)
        self.assertIn("X Developer Console", init_instructions)

    def test_discovery_skill_uses_one_fresh_unmodified_role_with_preverification_limits(self):
        root = Path(__file__).parents[1] / "skills"
        instructions = (root / "codoop-content-discovery" / "SKILL.md").read_text()

        self.assertIn("_shared/agents/marketing-twitter-engager.md", instructions)
        self.assertIn("fresh subagent", instructions)
        self.assertIn("Do not use Firecrawl, a browser, web search, or URL fetching", instructions)
        self.assertIn("review every candidate ID", instructions)
        self.assertIn("least recently used direction", instructions)
        self.assertIn("Never schedule `scripts/run.sh start-discovery` directly", instructions)
        self.assertIn("Do not ask the user", instructions)
        self.assertIn("query matches the prior run", instructions)
        self.assertIn("different URL", instructions)
        self.assertIn("breakout-trend", instructions)
        self.assertIn("No candidate is worth source verification in this discovery run.", instructions)

    def test_discovery_wrapper_exposes_run_and_lead_commands(self):
        result = subprocess.run([str(CONTENT_DISCOVERY_RUNNER), "--help"], capture_output=True, text=True)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("start-discovery", result.stdout)
        self.assertIn("complete-discovery", result.stdout)
        self.assertIn("list-leads", result.stdout)
        self.assertIn("record-post-review", result.stdout)
        self.assertIn("promote", result.stdout)
        self.assertIn("record-performance", result.stdout)

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
            self.assertTrue((workspace / "content-leads").is_dir())
            self.assertTrue((workspace / "content-tickets").is_dir())
            config.write_text('marker = "keep"\n')
            subprocess.run([sys.executable, str(INIT_CONFIG_SCRIPT), "--workspace", str(workspace)], check=True)
            self.assertEqual(config.read_text(), 'marker = "keep"\n')

    def test_content_ticket_wrapper_uses_the_ticket_workflow(self):
        result = subprocess.run([str(CONTENT_TICKET_RUNNER), "--help"], capture_output=True, text=True)

        self.assertEqual(result.returncode, 0)
        self.assertIn("claim", result.stdout)
        self.assertNotIn("{create,", result.stdout)
        rejected = subprocess.run(
            [str(CONTENT_TICKET_RUNNER), "create", "arbitrary topic"], capture_output=True, text=True
        )
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("invalid choice", rejected.stderr)

    def test_content_ticket_skill_claims_from_the_pool_without_running_discovery(self):
        instructions = (Path(__file__).parents[1] / "skills/codoop-content-ticket/SKILL.md").read_text()

        self.assertIn("list-leads", instructions)
        self.assertIn("claim", instructions)
        self.assertIn("Do not run discovery automatically", instructions)
        self.assertIn("No suitable unverified lead", instructions)

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

    def test_development_installer_includes_discovery_and_the_shared_reviewer(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                ["bash", str(INSTALLER), "--agent", "codex", "--skill", "all"],
                capture_output=True,
                text=True,
                env={**os.environ, "CODEX_HOME": directory},
            )
            installed = Path(directory) / "skills"

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((installed / "codoop-content-discovery" / "SKILL.md").is_file())
            self.assertTrue((installed / "_shared" / "agents" / "marketing-twitter-engager.md").is_file())

    def test_marketplace_manifests_expose_content_discovery(self):
        root = Path(__file__).parents[1]
        claude = json.loads((root / ".claude-plugin" / "marketplace.json").read_text())
        agents = json.loads((root / ".agents" / "plugins" / "marketplace.json").read_text())

        self.assertIn("codoop-content-discovery", {plugin["name"] for plugin in claude["plugins"]})
        self.assertIn("codoop-content-discovery", {plugin["name"] for plugin in agents["plugins"]})

    def test_social_content_requires_direct_source_urls(self):
        instructions = (Path(__file__).parents[1] / "skills/social-content/SKILL.md").read_text()

        self.assertIn("[Source: Name](https://...)", instructions)


if __name__ == "__main__":
    unittest.main()
