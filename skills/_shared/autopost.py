#!/usr/bin/env python3
"""Safe local state for codoop-autopost."""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import subprocess
import sys
import tomllib
import uuid
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Callable
from urllib import parse, request


STATUSES = {"draft", "pending", "done", "discarded"}
LEAD_STATUSES = {"available", "claimed", "consumed", "rejected"}
PASS_BASES = {"audience-value", "breakout-trend", "human-override"}
SOURCE_LABEL = re.compile(r"^\s*Sources?\s*:", re.IGNORECASE)
URL = re.compile(r"https?://\S+")
DUPLICATE_WINDOW_DAYS = 14


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class Settings:
    def __init__(
        self,
        firecrawl_api_key: str,
        firecrawl_api_url: str,
        x_consumer_key: str,
        x_consumer_secret: str,
        x_access_token: str,
        x_access_secret: str,
    ):
        self.firecrawl_api_key = firecrawl_api_key
        self.firecrawl_api_url = firecrawl_api_url
        self.x_consumer_key = x_consumer_key
        self.x_consumer_secret = x_consumer_secret
        self.x_access_token = x_access_token
        self.x_access_secret = x_access_secret

    @property
    def x_credentials(self) -> tuple[str, str, str, str]:
        return self.x_consumer_key, self.x_consumer_secret, self.x_access_token, self.x_access_secret

    @classmethod
    def load(cls, path: Path | None = None) -> "Settings":
        configured_path = os.environ.get("CODOOP_AUTOPOST_CONFIG")
        config_path = path or (Path(configured_path) if configured_path else Path.cwd() / "config.toml")
        if config_path.is_file():
            with config_path.open("rb") as file:
                config = tomllib.load(file)
        else:
            config = {}

        def value(section: str, key: str, environment: str, default: str = "") -> str:
            group = config.get(section, {})
            if not isinstance(group, dict):
                raise RuntimeError(f"invalid [{section}] configuration")
            configured = os.environ.get(environment) or group.get(key, default)
            if not isinstance(configured, str):
                raise RuntimeError(f"{section}.{key} must be a string")
            return configured

        return cls(
            value("firecrawl", "api_key", "FIRECRAWL_API_KEY"),
            value("firecrawl", "api_url", "FIRECRAWL_API_URL", "https://api.firecrawl.dev/v2"),
            value("x", "consumer_key", "X_CONSUMER_KEY"),
            value("x", "consumer_secret", "X_CONSUMER_SECRET"),
            value("x", "access_token", "X_ACCESS_TOKEN"),
            value("x", "access_secret", "X_ACCESS_SECRET"),
        )


class Firecrawl:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def scrape(self, url: str) -> str:
        payload = json.dumps({"url": url, "formats": ["markdown"]}).encode()
        response = self._post("/scrape", payload)
        markdown = response.get("data", {}).get("markdown")
        if not isinstance(markdown, str) or not markdown.strip():
            raise RuntimeError("Firecrawl returned no markdown")
        return markdown

    def _post(self, path: str, payload: bytes) -> dict:
        req = request.Request(
            f"{self.base_url}{path}", data=payload,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}, method="POST",
        )
        with request.urlopen(req, timeout=30) as response:
            body = json.loads(response.read())
        if not body.get("success", True):
            raise RuntimeError(body.get("error") or "Firecrawl request failed")
        return body


class XPublisher:
    endpoint = "https://api.x.com/2/tweets"

    def __init__(self, consumer_key: str, consumer_secret: str, access_token: str, access_secret: str):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.access_token = access_token
        self.access_secret = access_secret

    @classmethod
    def from_settings(cls, settings: Settings) -> "XPublisher":
        if not all(settings.x_credentials):
            raise RuntimeError("X_CONSUMER_KEY, X_CONSUMER_SECRET, X_ACCESS_TOKEN, and X_ACCESS_SECRET are required")
        return cls(*settings.x_credentials)

    def post(self, body: str) -> dict:
        if not body.strip():
            raise ValueError("post body is required")
        if len(body) > 280:
            raise ValueError("X posts must be 280 characters or fewer")
        payload = json.dumps({"text": body}).encode()
        oauth = {
            "oauth_consumer_key": self.consumer_key,
            "oauth_nonce": secrets.token_hex(16),
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": str(int(datetime.now(UTC).timestamp())),
            "oauth_token": self.access_token,
            "oauth_version": "1.0",
        }
        encoded = "&".join(
            f"{parse.quote(key, safe='~')}={parse.quote(value, safe='~')}" for key, value in sorted(oauth.items())
        )
        base = "&".join(("POST", parse.quote(self.endpoint, safe="~"), parse.quote(encoded, safe="~")))
        key = f"{parse.quote(self.consumer_secret, safe='~')}&{parse.quote(self.access_secret, safe='~')}"
        oauth["oauth_signature"] = base64.b64encode(hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()).decode()
        authorization = "OAuth " + ", ".join(
            f'{parse.quote(key, safe="~")}="{parse.quote(value, safe="~")}"' for key, value in sorted(oauth.items())
        )
        req = request.Request(
            self.endpoint, data=payload,
            headers={"Authorization": authorization, "Content-Type": "application/json"}, method="POST",
        )
        with request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read()).get("data", {})
        post_id = data.get("id")
        if not post_id:
            raise RuntimeError("X returned no post id")
        return {"id": post_id, "url": f"https://x.com/i/web/status/{post_id}"}


def last30days_argv(topic: str, script: Path) -> list[str]:
    return [sys.executable, str(script), topic, "--emit=json"]


def discovery_script() -> Path:
    configured = os.environ.get("CODOOP_LAST30DAYS_DIR")
    if configured:
        return Path(configured) / "skills" / "last30days" / "scripts" / "last30days.py"
    return Path(__file__).parents[1] / "last30days" / "vendor" / "scripts" / "last30days.py"


def ensure_discovery_runtime() -> Path:
    script = discovery_script()
    if script.is_file():
        return script
    if os.environ.get("CODOOP_LAST30DAYS_DIR"):
        raise RuntimeError("CODOOP_LAST30DAYS_DIR must point to an initialized last30days runtime")
    raise RuntimeError("bundled last30days runtime is missing; reinstall codoop-autopost")


def discover(topic: str) -> dict:
    script = ensure_discovery_runtime()
    result = subprocess.run(last30days_argv(topic, script), capture_output=True, text=True, check=False, timeout=300)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "last30days failed")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"last30days did not return JSON: {error}") from error


class TicketStore:
    """One auditable content-operation folder per post; no separate database."""

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.tickets = workspace / "content-tickets"
        self.tickets.mkdir(parents=True, exist_ok=True)
        self.leads = workspace / "content-leads"
        self.runs = self.leads / "runs"
        for name in (*sorted(LEAD_STATUSES), "runs"):
            (self.leads / name).mkdir(parents=True, exist_ok=True)

    def start_discovery(self, direction: str, query: str) -> dict:
        self.require_standards()
        if not direction.strip() or not query.strip():
            raise ValueError("direction and query are required")
        query = query.strip()
        if self._normalized_query(query) == self._normalized_query(self._latest_discovery_query()):
            raise ValueError("query must differ from the previous discovery query")
        result = discover(query)
        candidates = self._candidate_results(result)
        now = utc_now()
        review_ids = []
        seen_urls = set()
        for candidate in candidates:
            canonical = self._canonical_url(str(candidate.get("url", "")))
            existing = self._find_lead_by_url(canonical)
            if existing:
                existing["last_seen_at"] = now
                existing["engagement"] = json.dumps(candidate.get("engagement", ""), ensure_ascii=False, sort_keys=True)
                existing["updated_at"] = now
                self._write_mapping(self._lead_directory(existing["id"], existing["status"]) / "lead.toml", existing)
            elif canonical not in seen_urls:
                review_ids.append(candidate["candidate_id"])
                seen_urls.add(canonical)
        run_id = f"R-{datetime.now(UTC):%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:8]}"
        directory = self.runs / run_id
        directory.mkdir()
        self._write_json(directory / "raw.json", result)
        run = {
            "id": run_id,
            "direction": direction.strip(),
            "query": query,
            "status": "reviewing",
            "review_candidate_ids": json.dumps(review_ids, ensure_ascii=False),
            "discovered_at": now,
            "created_at": now,
            "updated_at": now,
        }
        self._write_mapping(directory / "run.toml", run)
        return {**run, "review_candidate_ids": review_ids}

    def complete_discovery(self, run_id: str, selections: list[str]) -> dict:
        run = self.get_run(run_id)
        if run["status"] != "reviewing":
            raise ValueError(f"discovery run must be reviewing, not {run['status']}")
        directory = self._run_directory(run_id)
        review = directory / "value-review.md"
        if not review.is_file() or not review.read_text().strip():
            raise ValueError("value-review.md is required before completing discovery")
        review_text = review.read_text()
        result = json.loads((directory / "raw.json").read_text())
        candidates = {item["candidate_id"]: item for item in self._candidate_results(result)}
        eligible = set(json.loads(run.get("review_candidate_ids", "[]")))
        now = utc_now()
        for rank, selection in enumerate(selections, start=1):
            try:
                candidate_id, pass_basis = selection.rsplit(":", 1)
            except ValueError as error:
                raise ValueError("selections must use CANDIDATE_ID:PASS_BASIS") from error
            if candidate_id not in eligible or candidate_id not in candidates:
                raise ValueError(f"candidate was not eligible for review: {candidate_id}")
            if pass_basis not in PASS_BASES - {"human-override"}:
                raise ValueError(f"invalid discovery pass basis: {pass_basis}")
            if f"| {candidate_id} | go |" not in review_text:
                raise ValueError("selected discovery candidate must have a go verdict in value-review.md")
            candidate = candidates[candidate_id]
            canonical = self._canonical_url(str(candidate["url"]))
            if self._find_lead_by_url(canonical):
                continue
            lead_id = f"L-{datetime.now(UTC):%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:8]}"
            lead = {
                "id": lead_id,
                "run_id": run_id,
                "candidate_id": candidate_id,
                "title": str(candidate.get("title", "")).strip(),
                "source": str(candidate.get("source", "")).strip(),
                "url": str(candidate["url"]).strip(),
                "canonical_url": canonical,
                "summary": str(candidate.get("summary", "")).strip(),
                "published_at": str(candidate.get("published_at", "")).strip(),
                "engagement": json.dumps(candidate.get("engagement", ""), ensure_ascii=False, sort_keys=True),
                "review_rank": rank,
                "original_verdict": "go",
                "pass_basis": pass_basis,
                "status": "available",
                "discovered_at": run["discovered_at"],
                "last_seen_at": now,
                "created_at": now,
                "updated_at": now,
            }
            lead_directory = self._lead_directory(lead_id, "available")
            lead_directory.mkdir()
            self._write_mapping(lead_directory / "lead.toml", lead)
        run["status"] = "complete"
        run["completed_at"] = now
        run["updated_at"] = now
        self._write_mapping(directory / "run.toml", run)
        return self.get_run(run_id)

    def get_run(self, run_id: str) -> dict:
        path = self._run_directory(run_id) / "run.toml"
        if not path.is_file():
            raise ValueError(f"unknown discovery run: {run_id}")
        return self._read_toml(path)

    def list_leads(self, status: str = "available") -> list[dict]:
        if status not in LEAD_STATUSES:
            raise ValueError(f"unknown lead status: {status}")
        directory = self.leads / status
        items = [
            self._read_toml(path / "lead.toml")
            for path in directory.iterdir()
            if path.is_dir() and (path / "lead.toml").is_file()
        ]
        return sorted(items, key=lambda item: (item["discovered_at"], -int(item["review_rank"])), reverse=True)

    def promote(self, run_id: str, candidate_id: str, reason: str) -> dict:
        if not reason.strip():
            raise ValueError("human override reason is required")
        run = self.get_run(run_id)
        if run["status"] != "complete":
            raise ValueError("discovery run must be complete before promotion")
        directory = self._run_directory(run_id)
        review = directory / "value-review.md"
        if not review.is_file() or not review.read_text().strip():
            raise ValueError("original value review is required")
        result = json.loads((directory / "raw.json").read_text())
        candidates = {item["candidate_id"]: item for item in self._candidate_results(result)}
        if candidate_id not in candidates:
            raise ValueError(f"unknown candidate in discovery run: {candidate_id}")
        candidate = candidates[candidate_id]
        canonical = self._canonical_url(str(candidate["url"]))
        if self._find_lead_by_url(canonical):
            raise ValueError("candidate URL already has a lead")
        now = utc_now()
        lead_id = f"L-{datetime.now(UTC):%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:8]}"
        lead = {
            "id": lead_id,
            "run_id": run_id,
            "candidate_id": candidate_id,
            "title": str(candidate.get("title", "")).strip(),
            "source": str(candidate.get("source", "")).strip(),
            "url": str(candidate["url"]).strip(),
            "canonical_url": canonical,
            "summary": str(candidate.get("summary", "")).strip(),
            "published_at": str(candidate.get("published_at", "")).strip(),
            "engagement": json.dumps(candidate.get("engagement", ""), ensure_ascii=False, sort_keys=True),
            "review_rank": 9999,
            "original_verdict": "preserved-in-run-review",
            "original_review": str(review.relative_to(self.workspace)),
            "pass_basis": "human-override",
            "override_reason": reason.strip(),
            "status": "available",
            "promoted_at": now,
            "discovered_at": run["discovered_at"],
            "last_seen_at": now,
            "created_at": now,
            "updated_at": now,
        }
        lead_directory = self._lead_directory(lead_id, "available")
        lead_directory.mkdir()
        self._write_mapping(lead_directory / "lead.toml", lead)
        return lead

    def _create_ticket(self, topic: str, lead: dict) -> dict:
        self.require_standards()
        if not topic.strip():
            raise ValueError("topic is required")
        body = ""
        now = utc_now()
        ticket_id = f"C-{datetime.now(UTC):%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:8]}"
        directory = self.tickets / ticket_id
        directory.mkdir()
        for stage in ("discovery", "verification", "writing", "review", "publish"):
            (directory / stage).mkdir()
        (directory / "verification" / "source-snapshots").mkdir()
        self._write_text(directory / "writing" / "drafts.md", f"{body}\n")
        self._write_text(directory / "writing" / "edited.md", f"{body}\n")
        self._write_text(directory / "writing" / "brief.md", f"# Brief\n\nTopic: {topic.strip()}\n")
        self._write_text(directory / "review" / "final.md", f"{body}\n")
        self._write_text(directory / "review" / "approval.md", "")
        self._write_text(directory / "discovery" / "raw.json", "{}\n")
        self._write_text(directory / "discovery" / "candidates.md", "# Candidates\n")
        self._write_text(directory / "discovery" / "selection.md", "# Selection\n")
        self._write_text(directory / "discovery" / "value-review.md", "# Value Review\n")
        self._write_text(directory / "discovery" / "duplicate-check.md", "# Duplicate check\n")
        self._write_text(directory / "verification" / "evidence.md", "# Evidence\n")
        self._write_text(directory / "verification" / "claims.md", "# Claims\n")
        self._write_text(directory / "verification" / "value-review.md", "# Verified Value Review\n")
        item = {
            "id": ticket_id,
            "topic": topic.strip(),
            "body": body,
            "platform": "x",
            "content_hash": hashlib.sha256(body.encode()).hexdigest(),
            "status": "draft",
            "verified_evidence_count": 0,
            "created_at": now,
            "updated_at": now,
        }
        item.update({
            "lead_id": lead["id"],
            "source_url": lead["canonical_url"],
            "pass_basis": lead["pass_basis"],
        })
        run_directory = self._run_directory(lead["run_id"])
        self._write_text(directory / "discovery" / "raw.json", (run_directory / "raw.json").read_text())
        self._write_text(directory / "discovery" / "value-review.md", (run_directory / "value-review.md").read_text())
        self._write_text(
            directory / "discovery" / "selection.md",
            f"# Selection\n\n- Lead ID: {lead['id']}\n- Candidate ID: {lead['candidate_id']}\n- URL: {lead['canonical_url']}\n",
        )
        self._write_ticket(directory, item)
        return self.get(ticket_id)

    def claim(self, lead_id: str) -> dict:
        self.require_standards()
        available = self._lead_directory(lead_id, "available")
        claimed = self._lead_directory(lead_id, "claimed")
        if available.is_dir():
            try:
                available.rename(claimed)
            except OSError:
                if available.exists() or not claimed.is_dir():
                    raise
        if not claimed.is_dir():
            raise ValueError(f"lead is not available or claimed: {lead_id}")
        lead = self._read_toml(claimed / "lead.toml")
        if lead.get("ticket_id"):
            ticket = self.get(lead["ticket_id"])
            if ticket["status"] == "done":
                self.move_lead(ticket["id"], "consumed", "Reconciled from a published ticket.")
            elif ticket["status"] == "discarded":
                self.move_lead(ticket["id"], "rejected", "Reconciled from a discarded ticket.")
            return ticket
        lock = claimed / "claim.lock"
        try:
            descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as error:
            raise RuntimeError("lead claim is already in progress") from error
        os.close(descriptor)
        try:
            ticket = self._create_ticket(lead["title"], lead)
            now = utc_now()
            lead.update({
                "status": "claimed",
                "ticket_id": ticket["id"],
                "claimed_at": now,
                "updated_at": now,
            })
            self._write_mapping(claimed / "lead.toml", lead)
            return ticket
        finally:
            lock.unlink(missing_ok=True)

    def move_lead(self, ticket_id: str, status: str, reason: str) -> dict:
        if status not in {"rejected", "consumed"}:
            raise ValueError("claimed leads can only move to rejected or consumed")
        if not reason.strip():
            raise ValueError("lead status reason is required")
        lead = next((item for item in self.list_leads("claimed") if item.get("ticket_id") == ticket_id), None)
        if not lead:
            raise ValueError(f"ticket has no claimed lead: {ticket_id}")
        source = self._lead_directory(lead["id"], "claimed")
        target = self._lead_directory(lead["id"], status)
        source.rename(target)
        now = utc_now()
        lead["status"] = status
        lead["status_reason"] = reason.strip()
        lead[f"{'published' if status == 'consumed' else 'rejected'}_at"] = now
        lead["updated_at"] = now
        self._write_mapping(target / "lead.toml", lead)
        return lead

    def write_draft(self, ticket_id: str, body: str) -> dict:
        item = self._require_status(ticket_id, "draft")
        self._require_write_gate(ticket_id, item)
        body = body.strip()
        if not body:
            raise ValueError("post body is required")
        if len(body) > 280:
            raise ValueError("X posts must be 280 characters or fewer")
        directory = self._directory(ticket_id)
        for path in ("writing/drafts.md", "writing/edited.md", "review/final.md"):
            self._write_text(directory / path, f"{body}\n")
        item["body"] = body
        item["content_hash"] = hashlib.sha256(body.encode()).hexdigest()
        item["updated_at"] = utc_now()
        self._write_ticket(directory, item)
        return self.get(ticket_id)

    def dedupe(self, ticket_id: str) -> dict:
        item = self._require_status(ticket_id, "draft")
        if not item.get("lead_id") or not item.get("source_url"):
            raise ValueError("ticket must be created from a claimed lead")
        candidate = self._canonical_url(item["source_url"])
        matches = self._recent_source_matches(ticket_id, candidate)
        directory = self._directory(ticket_id)
        if matches:
            self._write_duplicate_check(directory, "discarded", candidate, matches, "Same source URL appeared in a recent pending or published ticket.")
            item["status"] = "discarded"
            item["discarded_at"] = utc_now()
            self.move_lead(ticket_id, "rejected", "Same source URL appeared in a recent pending or published ticket.")
        else:
            self._write_duplicate_check(directory, "clear", candidate, (), "No matching source URL in recent pending or published tickets.")
        item["updated_at"] = utc_now()
        self._write_ticket(directory, item)
        return {"decision": "discarded" if matches else "clear", "matches": matches, "ticket": self.get(ticket_id)}

    def scrape_source(self, ticket_id: str, scrape: Callable[[str], str]) -> dict:
        item = self._require_status(ticket_id, "draft")
        if not item.get("lead_id") or not item.get("source_url"):
            raise ValueError("ticket must be created from a claimed lead")
        duplicate_check = self._directory(ticket_id) / "discovery" / "duplicate-check.md"
        if "Decision: clear" not in duplicate_check.read_text():
            raise ValueError("duplicate check must be clear before source verification")
        markdown = scrape(item["source_url"])
        if not isinstance(markdown, str) or not markdown.strip():
            raise RuntimeError("source verification returned no markdown")
        snapshot = self._directory(ticket_id) / "verification" / "source-snapshots" / "source.md"
        self._write_text(snapshot, markdown.rstrip() + "\n")
        return {"ticket_id": ticket_id, "url": item["source_url"], "snapshot": str(snapshot)}

    def discard(self, ticket_id: str, reason: str) -> dict:
        item = self._require_status(ticket_id, "draft")
        if not reason.strip():
            raise ValueError("discard reason is required")
        directory = self._directory(ticket_id)
        self._write_duplicate_check(directory, "discarded", None, (), reason.strip())
        item["status"] = "discarded"
        item["discarded_at"] = utc_now()
        item["updated_at"] = utc_now()
        self._write_ticket(directory, item)
        if item.get("lead_id"):
            self.move_lead(ticket_id, "rejected", reason.strip())
        return self.get(ticket_id)

    def get(self, ticket_id: str) -> dict:
        directory = self._directory(ticket_id)
        path = directory / "ticket.toml"
        if not path.is_file():
            raise ValueError(f"unknown ticket: {ticket_id}")
        with path.open("rb") as file:
            item = tomllib.load(file)
        if item.get("status") not in STATUSES:
            raise RuntimeError(f"invalid ticket status: {item.get('status')}")
        receipt = directory / "publish" / "receipt.json"
        if receipt.is_file():
            try:
                outcome = json.loads(receipt.read_text())
                if outcome.get("status") == "failed":
                    item["error"] = outcome.get("error", "publication failed")
            except json.JSONDecodeError:
                raise RuntimeError(f"invalid publish receipt: {receipt}") from None
        return item

    def list(self, status: str | None = None) -> list[dict]:
        if status and status not in STATUSES:
            raise ValueError(f"unknown status: {status}")
        items = [self.get(path.name) for path in self.tickets.iterdir() if path.is_dir() and (path / "ticket.toml").is_file()]
        return sorted((item for item in items if not status or item["status"] == status), key=lambda item: item["created_at"], reverse=True)

    def add_evidence(
        self, ticket_id: str, claim: str, url: str, source_type: str, published_at: str | None, excerpt: str, verified: bool
    ) -> dict:
        item = self._require_status(ticket_id, "draft")
        directory = self._directory(ticket_id)
        if not item.get("lead_id") or "Decision: clear" not in (directory / "discovery" / "duplicate-check.md").read_text():
            raise ValueError("duplicate check must be clear before evidence")
        if not (directory / "verification" / "source-snapshots" / "source.md").is_file():
            raise ValueError("source snapshot is required before evidence")
        if not all(value.strip() for value in (claim, url, source_type, excerpt)):
            raise ValueError("claim, url, source type, and excerpt are required")
        if not published_at or not published_at.strip():
            raise ValueError("publication date is required")
        try:
            date.fromisoformat(published_at)
        except ValueError as error:
            raise ValueError("publication date must use YYYY-MM-DD") from error
        entry = (
            f"\n## {utc_now()}\n\n- Claim: {claim.strip()}\n- URL: {url.strip()}\n"
            f"- Source type: {source_type.strip()}\n- Published: {published_at.strip()}\n"
            f"- Verified: {'yes' if verified else 'no'}\n\n> {excerpt.strip()}\n"
        )
        with (directory / "verification" / "evidence.md").open("a") as file:
            file.write(entry)
        if verified:
            item["verified_evidence_count"] = int(item.get("verified_evidence_count", 0)) + 1
        item["updated_at"] = utc_now()
        self._write_ticket(directory, item)
        return self.get(ticket_id)

    def record_post_review(self, ticket_id: str, verdict: str, report: Path) -> dict:
        item = self._require_status(ticket_id, "draft")
        if verdict not in {"go", "weak", "reject"}:
            raise ValueError("post-review verdict must be go, weak, or reject")
        if int(item.get("verified_evidence_count", 0)) < 1:
            raise ValueError("verified evidence is required before post review")
        expected = self._directory(ticket_id) / "verification" / "value-review.md"
        if report.resolve() != expected.resolve() or not expected.is_file() or not expected.read_text().strip():
            raise ValueError("verification/value-review.md is required")
        now = utc_now()
        item["post_value_verdict"] = verdict
        item["post_value_reviewed_at"] = now
        item["updated_at"] = now
        if verdict != "go":
            item["status"] = "discarded"
            item["discarded_at"] = now
            self._write_ticket(self._directory(ticket_id), item)
            self.move_lead(ticket_id, "rejected", f"Post-verification value review: {verdict}.")
        else:
            self._write_ticket(self._directory(ticket_id), item)
        return self.get(ticket_id)

    def submit(self, ticket_id: str) -> dict:
        item = self._require_status(ticket_id, "draft")
        self._require_write_gate(ticket_id, item)
        final = self._directory(ticket_id) / "review" / "final.md"
        if not final.is_file() or not final.read_text().strip():
            raise ValueError("review/final.md is required before submission")
        if any(SOURCE_LABEL.match(line) and not URL.search(line) for line in final.read_text().splitlines()):
            raise ValueError("source labels in review/final.md must include a direct URL")
        item["status"] = "pending"
        item["updated_at"] = utc_now()
        self._write_ticket(self._directory(ticket_id), item)
        return self.get(ticket_id)

    def approve(self, ticket_id: str) -> dict:
        item = self._require_status(ticket_id, "pending")
        if int(item.get("verified_evidence_count", 0)) < 1:
            raise ValueError("verified evidence is required before approval")
        item["approved_at"] = utc_now()
        item["updated_at"] = utc_now()
        self._write_text(self._directory(ticket_id) / "review" / "approval.md", f"Approved at {item['approved_at']}\n")
        self._write_ticket(self._directory(ticket_id), item)
        return self.get(ticket_id)

    def schedule(self, ticket_id: str, when: datetime) -> dict:
        item = self._require_status(ticket_id, "pending")
        if not item.get("approved_at"):
            raise ValueError("ticket must be approved before scheduling")
        if when.tzinfo is None:
            raise ValueError("scheduled time must include a timezone")
        scheduled_at = when.astimezone(UTC).isoformat()
        item["scheduled_at"] = scheduled_at
        item["updated_at"] = utc_now()
        self._write_text(self._directory(ticket_id) / "publish" / "schedule.toml", f"platform = \"x\"\nscheduled_at = {json.dumps(scheduled_at)}\n")
        self._write_ticket(self._directory(ticket_id), item)
        return self.get(ticket_id)

    def retry(self, ticket_id: str) -> dict:
        item = self._require_status(ticket_id, "pending")
        directory = self._directory(ticket_id)
        receipt = directory / "publish" / "receipt.json"
        if not receipt.is_file():
            raise ValueError("a failed publish receipt is required before retrying")
        try:
            failure = json.loads(receipt.read_text())
        except json.JSONDecodeError:
            raise RuntimeError(f"invalid publish receipt: {receipt}") from None
        if failure.get("status") != "failed":
            raise ValueError("only a failed publish can be retried")
        attempts = directory / "publish" / "attempts"
        attempts.mkdir(exist_ok=True)
        self._write_json(attempts / f"failed-{utc_now().replace(':', '-')}.json", failure)
        receipt.unlink()
        item["retried_at"] = utc_now()
        item["updated_at"] = utc_now()
        self._write_ticket(directory, item)
        return self.get(ticket_id)

    def record_performance(self, ticket_id: str, impressions: int, comments: int, shares: int) -> dict:
        item = self.get(ticket_id)
        if item["status"] != "done" or not item.get("published_at"):
            raise ValueError("performance can only be recorded for a published ticket")
        values = (impressions, comments, shares)
        if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
            raise ValueError("performance metrics must be integers")
        if impressions <= 0 or comments < 0 or shares < 0:
            raise ValueError("impressions must be positive and interactions cannot be negative")
        performance = {
            "ticket_id": ticket_id,
            "recorded_at": utc_now(),
            "impressions": impressions,
            "comments": comments,
            "shares": shares,
            "total_interactions": comments + shares,
            "interactions_per_1000_impressions": round((comments + shares) * 1000 / impressions, 3),
        }
        self._write_mapping(self._directory(ticket_id) / "publish" / "performance.toml", performance)
        return performance

    def due(self, now: datetime | None = None) -> list[dict]:
        self.require_standards()
        current = (now or datetime.now(UTC)).astimezone(UTC)
        due = []
        for item in self.list("pending"):
            receipt = self._directory(item["id"]) / "publish" / "receipt.json"
            if receipt.is_file() and json.loads(receipt.read_text()).get("status") == "failed":
                continue
            scheduled_at = item.get("scheduled_at")
            if item.get("approved_at") and scheduled_at and datetime.fromisoformat(scheduled_at).astimezone(UTC) <= current:
                due.append(item)
        return sorted(due, key=lambda item: item["scheduled_at"])

    def publish_due(self, publisher: Callable[[str], dict], now: datetime | None = None) -> list[dict]:
        self.require_standards()
        completed = []
        for item in self.due(now):
            directory = self._directory(item["id"])
            lock = directory / "publish" / "publish.lock"
            try:
                descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                continue
            os.close(descriptor)
            try:
                response = publisher(item["body"])
            except Exception as error:
                self._write_json(directory / "publish" / "receipt.json", {"status": "failed", "error": str(error), "attempted_at": utc_now()})
            else:
                receipt = {"status": "published", "id": response["id"], "url": response["url"], "published_at": utc_now()}
                self._write_json(directory / "publish" / "receipt.json", receipt)
                item["status"] = "done"
                item["published_at"] = receipt["published_at"]
                item["updated_at"] = utc_now()
                self._write_ticket(directory, item)
                if item.get("lead_id"):
                    try:
                        self.move_lead(item["id"], "consumed", "Published successfully.")
                    except Exception as error:
                        receipt["lead_transition_error"] = str(error)
                        self._write_json(directory / "publish" / "receipt.json", receipt)
                completed.append(self.get(item["id"]))
            finally:
                # ponytail: a crash leaves this lock for manual inspection, preventing an unsafe duplicate X post.
                lock.unlink(missing_ok=True)
        return completed

    def _require_status(self, ticket_id: str, expected: str) -> dict:
        self.require_standards()
        item = self.get(ticket_id)
        if item["status"] != expected:
            raise ValueError(f"ticket must be {expected}, not {item['status']}")
        return item

    def _require_write_gate(self, ticket_id: str, item: dict) -> None:
        directory = self._directory(ticket_id)
        if not item.get("lead_id"):
            raise ValueError("ticket must be created from a claimed lead")
        if "Decision: clear" not in (directory / "discovery" / "duplicate-check.md").read_text():
            raise ValueError("duplicate check must be clear before writing")
        if not (directory / "verification" / "source-snapshots" / "source.md").is_file():
            raise ValueError("source snapshot is required before writing")
        if int(item.get("verified_evidence_count", 0)) < 1:
            raise ValueError("verified evidence is required before writing")
        if item.get("post_value_verdict") != "go":
            raise ValueError("a go post-verification value review is required before writing")

    def _directory(self, ticket_id: str) -> Path:
        if Path(ticket_id).name != ticket_id or ticket_id in {".", ".."}:
            raise ValueError("invalid ticket id")
        return self.tickets / ticket_id

    def _run_directory(self, run_id: str) -> Path:
        if Path(run_id).name != run_id or not run_id.startswith("R-"):
            raise ValueError("invalid discovery run id")
        return self.runs / run_id

    def _lead_directory(self, lead_id: str, status: str) -> Path:
        if Path(lead_id).name != lead_id or not lead_id.startswith("L-"):
            raise ValueError("invalid lead id")
        if status not in LEAD_STATUSES:
            raise ValueError(f"unknown lead status: {status}")
        return self.leads / status / lead_id

    @staticmethod
    def _candidate_results(result: dict) -> list[dict]:
        candidates = result.get("results")
        if not isinstance(candidates, list):
            raise ValueError("last30days output must contain a results list")
        valid = []
        for candidate in candidates:
            if not isinstance(candidate, dict):
                raise ValueError("last30days candidates must be objects")
            if not str(candidate.get("candidate_id", "")).strip():
                raise ValueError("last30days candidate_id is required")
            if not str(candidate.get("url", "")).strip():
                raise ValueError("last30days candidate URL is required")
            valid.append(candidate)
        return valid

    def _find_lead_by_url(self, canonical_url: str) -> dict | None:
        # ponytail: linear local-file scan; add an index only if lead volume makes discovery measurably slow.
        for status in LEAD_STATUSES:
            for lead in self.list_leads(status):
                if lead["canonical_url"] == canonical_url:
                    return lead
        return None

    def _latest_discovery_query(self) -> str:
        runs = [
            self._read_toml(path / "run.toml")
            for path in self.runs.iterdir()
            if path.is_dir() and (path / "run.toml").is_file()
        ]
        return max(runs, key=lambda run: run["created_at"]).get("query", "") if runs else ""

    @staticmethod
    def _normalized_query(query: str) -> str:
        return re.sub(r"\W+", " ", query.casefold()).strip()

    @staticmethod
    def _canonical_url(value: str) -> str:
        parsed = parse.urlsplit(value.strip().rstrip(".,;:)]}"))
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("candidate URL must be an absolute http(s) URL")
        query = [(key, item) for key, item in parse.parse_qsl(parsed.query, keep_blank_values=True) if not key.lower().startswith("utm_") and key.lower() not in {"fbclid", "gclid"}]
        path = parsed.path.rstrip("/") or "/"
        return parse.urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, parse.urlencode(sorted(query)), ""))

    def _recent_source_matches(self, ticket_id: str, candidate_url: str) -> list[dict]:
        cutoff = datetime.now(UTC) - timedelta(days=DUPLICATE_WINDOW_DAYS)
        matches = []
        for item in self.list():
            if item["id"] == ticket_id or item["status"] not in {"pending", "done"}:
                continue
            if datetime.fromisoformat(item["created_at"]).astimezone(UTC) < cutoff:
                continue
            evidence = self._directory(item["id"]) / "verification" / "evidence.md"
            if not evidence.is_file():
                continue
            urls = set()
            for value in URL.findall(evidence.read_text()):
                try:
                    urls.add(self._canonical_url(value))
                except ValueError:
                    continue
            if candidate_url in urls:
                matches.append({"ticket_id": item["id"], "status": item["status"], "url": candidate_url})
        return matches

    @staticmethod
    def _write_duplicate_check(directory: Path, decision: str, candidate_url: str | None, matches: list[dict] | tuple, reason: str) -> None:
        lines = ["# Duplicate check", "", f"Decision: {decision}"]
        if candidate_url:
            lines.append(f"Candidate URL: {candidate_url}")
        lines.extend((f"Window: previous {DUPLICATE_WINDOW_DAYS} days", "", "## Matches"))
        if matches:
            lines.extend(f"- {item['ticket_id']} ({item['status']}): {item['url']}" for item in matches)
        else:
            lines.append("- None")
        lines.extend(("", "## Reason", reason, ""))
        TicketStore._write_text(directory / "discovery" / "duplicate-check.md", "\n".join(lines))

    def require_standards(self) -> None:
        missing = [name for name in ("PROJECT.md", "VOICE.md") if not (self.workspace / name).is_file() or not (self.workspace / name).read_text().strip()]
        if missing:
            raise ValueError("PROJECT.md and VOICE.md must be confirmed first; run codoop-autopost-init")

    @staticmethod
    def _write_text(path: Path, content: str) -> None:
        temporary = path.with_name(f".{path.name}.tmp")
        temporary.write_text(content)
        temporary.replace(path)

    def _write_ticket(self, directory: Path, item: dict) -> None:
        keys = (
            "id", "lead_id", "topic", "source_url", "pass_basis", "body", "platform", "content_hash", "status",
            "verified_evidence_count", "post_value_verdict", "post_value_reviewed_at", "approved_at", "scheduled_at",
            "published_at", "discovered_at", "retried_at", "discarded_at", "created_at", "updated_at",
        )
        lines = []
        for key in keys:
            if key not in item:
                continue
            value = item[key]
            lines.append(f"{key} = {value}" if isinstance(value, int) else f"{key} = {json.dumps(str(value), ensure_ascii=False)}")
        self._write_text(directory / "ticket.toml", "\n".join(lines) + "\n")

    @staticmethod
    def _read_toml(path: Path) -> dict:
        with path.open("rb") as file:
            return tomllib.load(file)

    def _write_mapping(self, path: Path, item: dict) -> None:
        lines = []
        for key, value in item.items():
            if value is None:
                continue
            if isinstance(value, bool):
                rendered = "true" if value else "false"
            elif isinstance(value, (int, float)):
                rendered = str(value)
            else:
                rendered = json.dumps(str(value), ensure_ascii=False)
            lines.append(f"{key} = {rendered}")
        self._write_text(path, "\n".join(lines) + "\n")

    def _write_json(self, path: Path, value: dict) -> None:
        self._write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage locally approved X posts.")
    parser.add_argument("--workspace", type=Path, default=Path.cwd(), help="Content-operations workspace (default: current directory).")
    commands = parser.add_subparsers(dest="command", required=True)
    start_discovery = commands.add_parser("start-discovery", help="Run last30days and create a standalone discovery run.")
    start_discovery.add_argument("direction")
    start_discovery.add_argument("query")
    complete_discovery = commands.add_parser("complete-discovery", help="Complete a reviewed run and enqueue its go candidates.")
    complete_discovery.add_argument("run_id")
    complete_discovery.add_argument("selections", nargs="*", metavar="CANDIDATE_ID:PASS_BASIS")
    promote = commands.add_parser("promote", help="Explicitly promote one reviewed candidate with a human reason.")
    promote.add_argument("run_id")
    promote.add_argument("candidate_id")
    promote.add_argument("--reason", required=True)
    list_leads = commands.add_parser("list-leads", help="List unverified content leads.")
    list_leads.add_argument("--status", choices=sorted(LEAD_STATUSES), default="available")
    claim = commands.add_parser("claim", help="Atomically claim a lead and create or resume its content ticket.")
    claim.add_argument("lead_id")
    write = commands.add_parser("write", help="Write the current draft and final review text for a content ticket.")
    write.add_argument("ticket_id")
    write.add_argument("body")
    evidence = commands.add_parser("evidence")
    evidence.add_argument("ticket_id")
    evidence.add_argument("claim")
    evidence.add_argument("url")
    evidence.add_argument("source_type")
    evidence.add_argument("excerpt")
    evidence.add_argument("--published-at")
    evidence.add_argument("--verified", action="store_true", help="Confirm this evidence was checked against the source.")
    post_review = commands.add_parser("record-post-review", help="Record the fresh post-verification value verdict.")
    post_review.add_argument("ticket_id")
    post_review.add_argument("verdict", choices=("go", "weak", "reject"))
    post_review.add_argument("--report", type=Path, required=True)
    submit = commands.add_parser("submit", help="Move a reviewed ticket to pending human approval.")
    submit.add_argument("ticket_id")
    approve = commands.add_parser("approve")
    approve.add_argument("ticket_id")
    schedule = commands.add_parser("schedule")
    schedule.add_argument("ticket_id")
    schedule.add_argument("when", help="ISO-8601 timestamp with timezone")
    retry = commands.add_parser("retry", help="Manually re-enable a failed, approved, scheduled post.")
    retry.add_argument("ticket_id")
    retry.add_argument("--confirmed-not-published", action="store_true")
    performance = commands.add_parser("record-performance", help="Manually record published post performance.")
    performance.add_argument("ticket_id")
    performance.add_argument("--impressions", type=int, required=True)
    performance.add_argument("--comments", type=int, default=0)
    performance.add_argument("--shares", type=int, default=0)
    listing = commands.add_parser("list")
    listing.add_argument("--status", choices=sorted(STATUSES))
    scrape = commands.add_parser("scrape", help="Read the claimed ticket's primary source through Firecrawl.")
    scrape.add_argument("ticket_id")
    dedupe = commands.add_parser("dedupe", help="Check the claimed ticket's source URL for recent use.")
    dedupe.add_argument("ticket_id")
    discard = commands.add_parser("discard", help="Record a human or Agent duplicate decision before source verification.")
    discard.add_argument("ticket_id")
    discard.add_argument("reason")
    due = commands.add_parser("publish-due", help="Publish due, approved posts only with --live.")
    due.add_argument("--live", action="store_true")
    args = parser.parse_args()
    if args.command == "start-discovery":
        result = TicketStore(args.workspace).start_discovery(args.direction, args.query)
    elif args.command == "complete-discovery":
        result = TicketStore(args.workspace).complete_discovery(args.run_id, args.selections)
    elif args.command == "promote":
        result = TicketStore(args.workspace).promote(args.run_id, args.candidate_id, args.reason)
    elif args.command == "list-leads":
        result = TicketStore(args.workspace).list_leads(args.status)
    elif args.command == "claim":
        result = TicketStore(args.workspace).claim(args.lead_id)
    elif args.command == "write":
        result = TicketStore(args.workspace).write_draft(args.ticket_id, args.body)
    elif args.command == "evidence":
        result = TicketStore(args.workspace).add_evidence(
            args.ticket_id, args.claim, args.url, args.source_type, args.published_at, args.excerpt, args.verified
        )
    elif args.command == "record-post-review":
        result = TicketStore(args.workspace).record_post_review(args.ticket_id, args.verdict, args.report)
    elif args.command == "submit":
        result = TicketStore(args.workspace).submit(args.ticket_id)
    elif args.command == "approve":
        result = TicketStore(args.workspace).approve(args.ticket_id)
    elif args.command == "schedule":
        result = TicketStore(args.workspace).schedule(args.ticket_id, datetime.fromisoformat(args.when))
    elif args.command == "retry":
        if not args.confirmed_not_published:
            raise RuntimeError("retry requires --confirmed-not-published after human inspection")
        result = TicketStore(args.workspace).retry(args.ticket_id)
    elif args.command == "record-performance":
        result = TicketStore(args.workspace).record_performance(
            args.ticket_id, args.impressions, args.comments, args.shares
        )
    elif args.command == "scrape":
        settings = Settings.load()
        api_key = settings.firecrawl_api_key
        if not api_key:
            raise RuntimeError("FIRECRAWL_API_KEY is required")
        firecrawl = Firecrawl(settings.firecrawl_api_url, api_key)
        result = TicketStore(args.workspace).scrape_source(args.ticket_id, firecrawl.scrape)
    elif args.command == "dedupe":
        result = TicketStore(args.workspace).dedupe(args.ticket_id)
    elif args.command == "discard":
        result = TicketStore(args.workspace).discard(args.ticket_id, args.reason)
    elif args.command == "publish-due":
        store = TicketStore(args.workspace)
        if not args.live:
            result = {"dry_run": True, "due": store.due()}
        else:
            result = store.publish_due(XPublisher.from_settings(Settings.load()).post)
    else:
        result = TicketStore(args.workspace).list(args.status)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
