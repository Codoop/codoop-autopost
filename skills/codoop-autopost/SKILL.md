---
name: codoop-autopost
description: Discover timely discussion, verify primary sources, draft in the user's voice, require explicit human approval, and safely schedule a single X post. Use when creating or operating a fact-checked social-content workflow, reviewing an X draft for publication, or publishing an explicitly approved scheduled X post.
---

# Codoop Autopost

Run the evidence-first workflow. Never treat a trending discussion as a fact. Never approve or publish without the user's explicit instruction.

## First use

This orchestration Skill ships with independently usable sibling Skills: `codoop-last30days`, `codoop-firecrawl`, `codoop-social-content`, `codoop-copy-editing`, and `codoop-x-twitter`. Set `SKILLS_DIR` to the directory where the pack was installed, then initialize the discovery runtime once:

```bash
SKILLS_DIR="${CODEX_HOME:-$HOME/.codex}/skills"
python3 "$SKILLS_DIR/codoop-last30days/scripts/last30days.py" --init
```

`FIRECRAWL_API_KEY` is required only to inspect sources. `X_CONSUMER_KEY`, `X_CONSUMER_SECRET`, `X_ACCESS_TOKEN`, and `X_ACCESS_SECRET` are required only for live publication. Use `FIRECRAWL_API_URL` for a compatible self-hosted endpoint. Never write credentials to the database or a draft.

## Workflow

1. Discover candidate discussions:

   ```bash
   python3 "$SKILLS_DIR/codoop-last30days/scripts/last30days.py" "TOPIC"
   ```

   Score candidates for relevance, recency, engagement, and whether primary evidence is likely available. `last30days` is discovery-only.

2. Find and inspect primary sources. Prefer official announcements, original reporting, papers, or the named person's original post. Read each candidate URL with Firecrawl:

   ```bash
   python3 "$SKILLS_DIR/codoop-firecrawl/scripts/scrape.py" "URL"
   ```

   Exclude a claim if its source is secondary, unavailable, conflicting, or insufficient. Keep the claim, source URL, source type, publication date, and a short exact excerpt.

3. Draft from verified evidence only. State the audience and the author's angle before writing. Clearly distinguish verified facts, attributed outside views, and the author's analysis. Keep X text to 280 characters. Create the local draft, then attach every claim it relies on:

   ```bash
   python3 .agents/skills/codoop-autopost/scripts/autopost.py draft "TOPIC" "POST TEXT"
   python3 .agents/skills/codoop-autopost/scripts/autopost.py evidence DRAFT_ID "CLAIM" "URL" "SOURCE TYPE" "EXCERPT" --published-at "YYYY-MM-DD"
   ```

   Edit for clarity and the user's voice, but do not change a fact, number, quotation, or source. If an edit needs a factual change, re-verify it first.

4. Ask for review. Do not call `approve` unless the user explicitly identifies the draft and says to approve it. Approval fails without saved verified evidence.

   ```bash
   python3 .agents/skills/codoop-autopost/scripts/autopost.py approve DRAFT_ID
   python3 .agents/skills/codoop-autopost/scripts/autopost.py schedule DRAFT_ID "2026-08-01T09:00:00-07:00"
   ```

5. Inspect the due queue before live publication:

   ```bash
   python3 .agents/skills/codoop-autopost/scripts/autopost.py publish-due
   ```

   A scheduler may invoke `codoop-x-twitter` after an explicit user instruction. A successful publication records the X ID, URL, and timestamp. A failure retains the body and error as `failed`; it is not retried automatically.

## Non-negotiable rules

- Publish only one approved X post. Do not automate likes, follows, replies, DMs, or browser activity.
- Do not use browser cookies or browser automation to publish.
- Do not infer a primary source from a trend. Cite only sources actually inspected.
- Do not silently retry a failed post or create a second post for a published draft.
