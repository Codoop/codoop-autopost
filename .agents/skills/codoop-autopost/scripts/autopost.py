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
import sqlite3
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable
from urllib import parse, request


STATUSES = {"drafted", "approved", "scheduled", "publishing", "published", "failed"}


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


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
    def from_env(cls) -> "XPublisher":
        keys = ("X_CONSUMER_KEY", "X_CONSUMER_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET")
        values = [os.environ.get(key, "") for key in keys]
        if not all(values):
            raise RuntimeError("X_CONSUMER_KEY, X_CONSUMER_SECRET, X_ACCESS_TOKEN, and X_ACCESS_SECRET are required")
        return cls(*values)

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
    return [sys.executable, str(script), topic, "--emit=json", "--save-dir", ".codoop-autopost/research"]


def discover(topic: str) -> dict:
    configured = os.environ.get("CODOOP_LAST30DAYS_DIR")
    root = Path(configured) if configured else Path(__file__).parents[1] / "vendor" / "last30days"
    script = root / "scripts" / "last30days.py"
    if not script.is_file():
        raise RuntimeError("last30days is not initialized; run scripts/bootstrap.py or set CODOOP_LAST30DAYS_DIR")
    result = subprocess.run(last30days_argv(topic, script), capture_output=True, text=True, check=False, timeout=300)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "last30days failed")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"last30days did not return JSON: {error}") from error


class Store:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS drafts (
                    id TEXT PRIMARY KEY,
                    topic TEXT NOT NULL,
                    body TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    status TEXT NOT NULL,
                    scheduled_at TEXT,
                    published_id TEXT,
                    published_url TEXT,
                    published_at TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS evidence (
                    id TEXT PRIMARY KEY,
                    draft_id TEXT NOT NULL REFERENCES drafts(id),
                    claim TEXT NOT NULL,
                    url TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    published_at TEXT,
                    excerpt TEXT NOT NULL,
                    verified INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                );
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def create_draft(self, topic: str, body: str) -> dict:
        if not topic.strip() or not body.strip():
            raise ValueError("topic and body are required")
        now = utc_now()
        item = {
            "id": str(uuid.uuid4()),
            "topic": topic.strip(),
            "body": body.strip(),
            "content_hash": hashlib.sha256(body.strip().encode()).hexdigest(),
            "status": "drafted",
            "created_at": now,
            "updated_at": now,
        }
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO drafts (id, topic, body, content_hash, status, created_at, updated_at) "
                "VALUES (:id, :topic, :body, :content_hash, :status, :created_at, :updated_at)",
                item,
            )
        return self.get(item["id"])

    def get(self, draft_id: str) -> dict:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM drafts WHERE id = ?", (draft_id,)).fetchone()
        if row is None:
            raise ValueError(f"unknown draft: {draft_id}")
        return dict(row)

    def list(self, status: str | None = None) -> list[dict]:
        if status and status not in STATUSES:
            raise ValueError(f"unknown status: {status}")
        query, values = "SELECT * FROM drafts", ()
        if status:
            query, values = f"{query} WHERE status = ?", (status,)
        with self._connect() as connection:
            return [dict(row) for row in connection.execute(f"{query} ORDER BY created_at DESC", values)]

    def add_evidence(
        self, draft_id: str, claim: str, url: str, source_type: str, published_at: str | None, excerpt: str
    ) -> dict:
        self._require_status(draft_id, "drafted")
        if not all(value.strip() for value in (claim, url, source_type, excerpt)):
            raise ValueError("claim, url, source type, and excerpt are required")
        item = {
            "id": str(uuid.uuid4()),
            "draft_id": draft_id,
            "claim": claim.strip(),
            "url": url.strip(),
            "source_type": source_type.strip(),
            "published_at": published_at,
            "excerpt": excerpt.strip(),
            "created_at": utc_now(),
        }
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO evidence (id, draft_id, claim, url, source_type, published_at, excerpt, created_at) "
                "VALUES (:id, :draft_id, :claim, :url, :source_type, :published_at, :excerpt, :created_at)",
                item,
            )
        return item

    def approve(self, draft_id: str) -> dict:
        self._require_status(draft_id, "drafted")
        with self._connect() as connection:
            evidence = connection.execute(
                "SELECT 1 FROM evidence WHERE draft_id = ? AND verified = 1 LIMIT 1", (draft_id,)
            ).fetchone()
            if evidence is None:
                raise ValueError("verified evidence is required before approval")
            connection.execute("UPDATE drafts SET status = 'approved', updated_at = ? WHERE id = ?", (utc_now(), draft_id))
        return self.get(draft_id)

    def schedule(self, draft_id: str, when: datetime) -> dict:
        self._require_status(draft_id, "approved")
        if when.tzinfo is None:
            raise ValueError("scheduled time must include a timezone")
        with self._connect() as connection:
            connection.execute(
                "UPDATE drafts SET status = 'scheduled', scheduled_at = ?, updated_at = ? WHERE id = ?",
                (when.astimezone(UTC).isoformat(), utc_now(), draft_id),
            )
        return self.get(draft_id)

    def due(self, now: datetime | None = None) -> list[dict]:
        now_text = (now or datetime.now(UTC)).astimezone(UTC).isoformat()
        with self._connect() as connection:
            return [dict(row) for row in connection.execute(
                "SELECT * FROM drafts WHERE status = 'scheduled' AND scheduled_at <= ? ORDER BY scheduled_at", (now_text,)
            )]

    def publish_due(self, publisher: Callable[[str], dict], now: datetime | None = None) -> list[dict]:
        due = self.due(now)
        completed = []
        for item in due:
            with self._connect() as connection:
                changed = connection.execute(
                    "UPDATE drafts SET status = 'publishing', updated_at = ? WHERE id = ? AND status = 'scheduled'",
                    (utc_now(), item["id"]),
                ).rowcount
            if not changed:
                continue
            try:
                response = publisher(item["body"])
                remote_id, remote_url = response["id"], response["url"]
                with self._connect() as connection:
                    connection.execute(
                        "UPDATE drafts SET status = 'published', published_id = ?, published_url = ?, "
                        "published_at = ?, error = NULL, updated_at = ? WHERE id = ?",
                        (remote_id, remote_url, utc_now(), utc_now(), item["id"]),
                    )
                completed.append(self.get(item["id"]))
            except Exception as error:
                with self._connect() as connection:
                    connection.execute(
                        "UPDATE drafts SET status = 'failed', error = ?, updated_at = ? WHERE id = ?",
                        (str(error), utc_now(), item["id"]),
                    )
        return completed

    def _require_status(self, draft_id: str, expected: str) -> None:
        actual = self.get(draft_id)["status"]
        if actual != expected:
            raise ValueError(f"draft must be {expected}, not {actual}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage locally approved X posts.")
    parser.add_argument("--db", type=Path, default=Path(".codoop-autopost/autopost.db"))
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("draft")
    create.add_argument("topic")
    create.add_argument("body")
    evidence = commands.add_parser("evidence")
    evidence.add_argument("draft_id")
    evidence.add_argument("claim")
    evidence.add_argument("url")
    evidence.add_argument("source_type")
    evidence.add_argument("excerpt")
    evidence.add_argument("--published-at")
    approve = commands.add_parser("approve")
    approve.add_argument("draft_id")
    schedule = commands.add_parser("schedule")
    schedule.add_argument("draft_id")
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
    store = Store(args.db)
    if args.command == "draft":
        result = store.create_draft(args.topic, args.body)
    elif args.command == "evidence":
        result = store.add_evidence(args.draft_id, args.claim, args.url, args.source_type, args.published_at, args.excerpt)
    elif args.command == "approve":
        result = store.approve(args.draft_id)
    elif args.command == "schedule":
        result = store.schedule(args.draft_id, datetime.fromisoformat(args.when))
    elif args.command == "scrape":
        api_key = os.environ.get("FIRECRAWL_API_KEY", "")
        if not api_key:
            raise RuntimeError("FIRECRAWL_API_KEY is required")
        result = {"url": args.url, "markdown": Firecrawl(os.environ.get("FIRECRAWL_API_URL", "https://api.firecrawl.dev/v2"), api_key).scrape(args.url)}
    elif args.command == "discover":
        result = discover(args.topic)
    elif args.command == "publish-due":
        if not args.live:
            result = {"dry_run": True, "due": store.due()}
        else:
            result = store.publish_due(XPublisher.from_env().post)
    else:
        result = store.list(args.status)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
