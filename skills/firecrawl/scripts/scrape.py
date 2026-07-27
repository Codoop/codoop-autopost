#!/usr/bin/env python3
"""Read one source URL through Firecrawl's scrape API."""

import argparse
import json
import os
from urllib import request


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape a source as Markdown through Firecrawl.")
    parser.add_argument("url")
    args = parser.parse_args()
    key = os.environ.get("FIRECRAWL_API_KEY")
    if not key:
        parser.error("FIRECRAWL_API_KEY is required")
    endpoint = os.environ.get("FIRECRAWL_API_URL", "https://api.firecrawl.dev/v2").rstrip("/") + "/scrape"
    payload = json.dumps({"url": args.url, "formats": ["markdown"]}).encode()
    req = request.Request(endpoint, data=payload, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, method="POST")
    with request.urlopen(req, timeout=30) as response:
        result = json.loads(response.read())
    markdown = result.get("data", {}).get("markdown")
    if not result.get("success", True) or not markdown:
        raise RuntimeError(result.get("error") or "Firecrawl returned no markdown")
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
