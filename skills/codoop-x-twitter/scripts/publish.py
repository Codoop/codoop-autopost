#!/usr/bin/env python3
"""Publish one explicitly approved X post through the official API."""

import argparse
import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import UTC, datetime
from urllib import parse, request


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish one approved X post.")
    parser.add_argument("--approved", action="store_true")
    parser.add_argument("text")
    args = parser.parse_args()
    if not args.approved:
        parser.error("--approved is required")
    if not args.text.strip() or len(args.text) > 280:
        parser.error("text must contain 1 to 280 characters")
    keys = ("X_CONSUMER_KEY", "X_CONSUMER_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET")
    consumer_key, consumer_secret, token, token_secret = (os.environ.get(key, "") for key in keys)
    if not all((consumer_key, consumer_secret, token, token_secret)):
        parser.error("X OAuth credentials are required")
    endpoint = "https://api.x.com/2/tweets"
    oauth = {"oauth_consumer_key": consumer_key, "oauth_nonce": secrets.token_hex(16), "oauth_signature_method": "HMAC-SHA1", "oauth_timestamp": str(int(datetime.now(UTC).timestamp())), "oauth_token": token, "oauth_version": "1.0"}
    encoded = "&".join(f"{parse.quote(key, safe='~')}={parse.quote(value, safe='~')}" for key, value in sorted(oauth.items()))
    base = "&".join(("POST", parse.quote(endpoint, safe="~"), parse.quote(encoded, safe="~")))
    signing_key = f"{parse.quote(consumer_secret, safe='~')}&{parse.quote(token_secret, safe='~')}"
    oauth["oauth_signature"] = base64.b64encode(hmac.new(signing_key.encode(), base.encode(), hashlib.sha1).digest()).decode()
    authorization = "OAuth " + ", ".join(f'{parse.quote(key, safe="~")}="{parse.quote(value, safe="~")}"' for key, value in sorted(oauth.items()))
    req = request.Request(endpoint, data=json.dumps({"text": args.text}).encode(), headers={"Authorization": authorization, "Content-Type": "application/json"}, method="POST")
    with request.urlopen(req, timeout=30) as response:
        post_id = json.loads(response.read()).get("data", {}).get("id")
    if not post_id:
        raise RuntimeError("X returned no post id")
    print(json.dumps({"id": post_id, "url": f"https://x.com/i/web/status/{post_id}", "published_at": datetime.now(UTC).isoformat()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
