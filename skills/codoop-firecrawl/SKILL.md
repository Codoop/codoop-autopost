---
name: codoop-firecrawl
description: Read source URLs through Firecrawl and extract evidence for claim verification. Use when verifying a primary source, recording a factual claim, or rejecting unverified content.
---

# Codoop Firecrawl

Require `FIRECRAWL_API_KEY`. Read a URL as Markdown:

```bash
python3 scripts/scrape.py "URL"
```

Classify the source before relying on it: official announcement, original reporting, paper, or the subject's original post are primary evidence. Record claim, URL, source type, publication date, and a short exact excerpt. Reject unresolved conflicts and unsupported claims.
