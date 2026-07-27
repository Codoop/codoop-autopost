#!/usr/bin/env python3
"""Safe local state for codoop-autopost."""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import secrets
import subprocess
import sys
import tomllib
import uuid
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Callable
from urllib import parse, request


STATUSES = {"draft", "pending", "done"}


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
    root = Path(configured) if configured else Path(
        os.environ.get("CODOOP_AUTOPOST_HOME", Path.home() / ".local" / "share" / "codoop-autopost")
    ) / "last30days"
    return root / "skills" / "last30days" / "scripts" / "last30days.py"


def ensure_discovery_runtime() -> Path:
    script = discovery_script()
    if script.is_file():
        return script
    if os.environ.get("CODOOP_LAST30DAYS_DIR"):
        raise RuntimeError("CODOOP_LAST30DAYS_DIR must point to an initialized last30days runtime")
    subprocess.run([sys.executable, str(Path(__file__).with_name("bootstrap.py"))], check=True, timeout=300)
    return script


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
        self.tickets = workspace / "tickets"
        self.tickets.mkdir(parents=True, exist_ok=True)

    def create_ticket(self, topic: str, body: str) -> dict:
        if not topic.strip() or not body.strip():
            raise ValueError("topic and body are required")
        if len(body.strip()) > 280:
            raise ValueError("X posts must be 280 characters or fewer")
        now = utc_now()
        ticket_id = f"T-{datetime.now(UTC):%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:8]}"
        directory = self.tickets / ticket_id
        directory.mkdir()
        for stage in ("discovery", "verification", "writing", "review", "publish"):
            (directory / stage).mkdir()
        (directory / "verification" / "source-snapshots").mkdir()
        self._write_text(directory / "writing" / "drafts.md", f"{body.strip()}\n")
        self._write_text(directory / "writing" / "edited.md", f"{body.strip()}\n")
        self._write_text(directory / "writing" / "brief.md", f"# Brief\n\nTopic: {topic.strip()}\n")
        self._write_text(directory / "review" / "final.md", f"{body.strip()}\n")
        self._write_text(directory / "review" / "approval.md", "")
        self._write_text(directory / "discovery" / "candidates.md", "# Candidates\n")
        self._write_text(directory / "discovery" / "selection.md", "# Selection\n")
        self._write_text(directory / "verification" / "evidence.md", "# Evidence\n")
        self._write_text(directory / "verification" / "claims.md", "# Claims\n")
        item = {
            "id": ticket_id,
            "topic": topic.strip(),
            "body": body.strip(),
            "platform": "x",
            "content_hash": hashlib.sha256(body.strip().encode()).hexdigest(),
            "status": "draft",
            "verified_evidence_count": 0,
            "created_at": now,
            "updated_at": now,
        }
        self._write_ticket(directory, item)
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
        if not all(value.strip() for value in (claim, url, source_type, excerpt)):
            raise ValueError("claim, url, source type, and excerpt are required")
        if not published_at or not published_at.strip():
            raise ValueError("publication date is required")
        try:
            date.fromisoformat(published_at)
        except ValueError as error:
            raise ValueError("publication date must use YYYY-MM-DD") from error
        directory = self._directory(ticket_id)
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

    def submit(self, ticket_id: str) -> dict:
        item = self._require_status(ticket_id, "draft")
        final = self._directory(ticket_id) / "review" / "final.md"
        if not final.is_file() or not final.read_text().strip():
            raise ValueError("review/final.md is required before submission")
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

    def due(self, now: datetime | None = None) -> list[dict]:
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
                receipt = {"status": "published", "id": response["id"], "url": response["url"], "published_at": utc_now()}
                self._write_json(directory / "publish" / "receipt.json", receipt)
                item["status"] = "done"
                item["published_at"] = receipt["published_at"]
                item["updated_at"] = utc_now()
                self._write_ticket(directory, item)
                completed.append(self.get(item["id"]))
            except Exception as error:
                self._write_json(directory / "publish" / "receipt.json", {"status": "failed", "error": str(error), "attempted_at": utc_now()})
            finally:
                # ponytail: a crash leaves this lock for manual inspection, preventing an unsafe duplicate X post.
                lock.unlink(missing_ok=True)
        return completed

    def _require_status(self, ticket_id: str, expected: str) -> dict:
        item = self.get(ticket_id)
        if item["status"] != expected:
            raise ValueError(f"ticket must be {expected}, not {item['status']}")
        return item

    def _directory(self, ticket_id: str) -> Path:
        if Path(ticket_id).name != ticket_id or ticket_id in {".", ".."}:
            raise ValueError("invalid ticket id")
        return self.tickets / ticket_id

    @staticmethod
    def _write_text(path: Path, content: str) -> None:
        temporary = path.with_name(f".{path.name}.tmp")
        temporary.write_text(content)
        temporary.replace(path)

    def _write_ticket(self, directory: Path, item: dict) -> None:
        keys = (
            "id", "topic", "body", "platform", "content_hash", "status", "verified_evidence_count", "approved_at", "scheduled_at",
            "published_at", "created_at", "updated_at",
        )
        lines = []
        for key in keys:
            if key not in item:
                continue
            value = item[key]
            lines.append(f"{key} = {value}" if isinstance(value, int) else f"{key} = {json.dumps(str(value), ensure_ascii=False)}")
        self._write_text(directory / "ticket.toml", "\n".join(lines) + "\n")

    def _write_json(self, path: Path, value: dict) -> None:
        self._write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage locally approved X posts.")
    parser.add_argument("--workspace", type=Path, default=Path.cwd(), help="Content-operations workspace (default: current directory).")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("draft")
    create.add_argument("topic")
    create.add_argument("body")
    evidence = commands.add_parser("evidence")
    evidence.add_argument("ticket_id")
    evidence.add_argument("claim")
    evidence.add_argument("url")
    evidence.add_argument("source_type")
    evidence.add_argument("excerpt")
    evidence.add_argument("--published-at")
    evidence.add_argument("--verified", action="store_true", help="Confirm this evidence was checked against the source.")
    submit = commands.add_parser("submit", help="Move a reviewed ticket to pending human approval.")
    submit.add_argument("ticket_id")
    approve = commands.add_parser("approve")
    approve.add_argument("ticket_id")
    schedule = commands.add_parser("schedule")
    schedule.add_argument("ticket_id")
    schedule.add_argument("when", help="ISO-8601 timestamp with timezone")
    listing = commands.add_parser("list")
    listing.add_argument("--status", choices=sorted(STATUSES))
    scrape = commands.add_parser("scrape", help="Read a candidate primary source through Firecrawl.")
    scrape.add_argument("url")
    discover_command = commands.add_parser("discover", help="Find recent discussion candidates with bundled last30days.")
    discover_command.add_argument("topic")
    due = commands.add_parser("publish-due", help="Publish due, approved posts only with --live.")
    due.add_argument("--live", action="store_true")
    args = parser.parse_args()
    if args.command == "draft":
        result = TicketStore(args.workspace).create_ticket(args.topic, args.body)
    elif args.command == "evidence":
        result = TicketStore(args.workspace).add_evidence(
            args.ticket_id, args.claim, args.url, args.source_type, args.published_at, args.excerpt, args.verified
        )
    elif args.command == "submit":
        result = TicketStore(args.workspace).submit(args.ticket_id)
    elif args.command == "approve":
        result = TicketStore(args.workspace).approve(args.ticket_id)
    elif args.command == "schedule":
        result = TicketStore(args.workspace).schedule(args.ticket_id, datetime.fromisoformat(args.when))
    elif args.command == "scrape":
        settings = Settings.load()
        api_key = settings.firecrawl_api_key
        if not api_key:
            raise RuntimeError("FIRECRAWL_API_KEY is required")
        result = {"url": args.url, "markdown": Firecrawl(settings.firecrawl_api_url, api_key).scrape(args.url)}
    elif args.command == "discover":
        result = discover(args.topic)
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
