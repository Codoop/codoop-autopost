---
name: codoop-autopost
description: Discover timely discussion, verify primary sources, draft in the user's voice, require explicit human approval, and safely schedule a single X post. Use when creating or operating a fact-checked social-content workflow, reviewing an X draft for publication, or publishing an explicitly approved scheduled X post.
---

# Codoop Autopost

Run the evidence-first workflow. Never treat a trending discussion as a fact. Never approve or publish without the user's explicit instruction.

## First use

This orchestration Skill includes the runtime it needs. `last30days`, `firecrawl`, `social-content`, `copy-editing`, and `x-twitter` remain independently usable sibling Skills, but none is a prerequisite. Set the main Skill directory once for the commands below:

```bash
AUTOPOST_DIR="${CODEX_HOME:-$HOME/.codex}/skills/codoop-autopost"
```

Copy `$AUTOPOST_DIR/config.example.toml` to `~/.config/codoop-autopost/config.toml`, add Firecrawl and X credentials, then restrict it to the current user (`chmod 600`). Firecrawl is required only to inspect sources; X credentials are required only for live publication. Environment variables override the file, and `CODOOP_AUTOPOST_CONFIG` can select another config path. Never write credentials to the database or a draft.

## Workflow

1. Discover candidate discussions:

   ```bash
   python3 "$AUTOPOST_DIR/scripts/autopost.py" discover "TOPIC"
   ```

   The first discovery run initializes the private `last30days` runtime automatically. Score candidates for relevance, recency, engagement, and whether primary evidence is likely available. `last30days` is discovery-only.

2. Find and inspect primary sources. Prefer official announcements, original reporting, papers, or the named person's original post. Read each candidate URL with Firecrawl:

   ```bash
   python3 "$AUTOPOST_DIR/scripts/autopost.py" scrape "URL"
   ```

   Exclude a claim if its source is secondary, unavailable, conflicting, or insufficient. Keep the claim, source URL, source type, publication date, and a short exact excerpt.

3. Draft from verified evidence only. State the audience and the author's angle before writing. Clearly distinguish verified facts, attributed outside views, and the author's analysis. Keep X text to 280 characters. Create the local draft, then attach every claim it relies on:

   ```bash
   python3 "$AUTOPOST_DIR/scripts/autopost.py" draft "TOPIC" "POST TEXT"
   python3 "$AUTOPOST_DIR/scripts/autopost.py" evidence DRAFT_ID "CLAIM" "URL" "SOURCE TYPE" "EXCERPT" --published-at "YYYY-MM-DD" --verified
   ```

   Edit for clarity and the user's voice, but do not change a fact, number, quotation, or source. If an edit needs a factual change, re-verify it first.

4. Ask for review. Do not call `approve` unless the user explicitly identifies the draft and says to approve it. Approval fails without saved verified evidence.

   ```bash
   python3 "$AUTOPOST_DIR/scripts/autopost.py" approve DRAFT_ID
   python3 "$AUTOPOST_DIR/scripts/autopost.py" schedule DRAFT_ID "2026-08-01T09:00:00-07:00"
   ```

5. Inspect the due queue before live publication:

   ```bash
   python3 "$AUTOPOST_DIR/scripts/autopost.py" publish-due
   ```

   A scheduler may invoke `x-twitter` after an explicit user instruction. A successful publication records the X ID, URL, and timestamp. A failure retains the body and error as `failed`; it is not retried automatically.

## Non-negotiable rules

- Publish only one approved X post. Do not automate likes, follows, replies, DMs, or browser activity.
- Do not use browser cookies or browser automation to publish.
- Do not infer a primary source from a trend. Cite only sources actually inspected.
- Do not silently retry a failed post or create a second post for a published draft.
