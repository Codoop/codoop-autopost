---
name: codoop-content-ticket
description: Create and operate one evidence-first content ticket in an initialized codoop-autopost project. Use when discovering a topic, verifying sources, drafting, reviewing, scheduling, or publishing a single social-content item that must follow PROJECT.md and VOICE.md.
---

# Codoop Content Ticket

Run this Skill in the root of a content-operations project. Read `PROJECT.md` and `VOICE.md` first. If either is missing or empty, stop and tell the user to run `codoop-autopost-init`; do not infer a vertical or voice.

Set the command path once:

```bash
CONTENT_TICKET_DIR="${CODEX_HOME:-$HOME/.codex}/skills/codoop-content-ticket"
```

## One ticket, one content unit

Create a `C-...` ticket before discovering topics. A ticket can keep multiple discovery candidates, but `discovery/selection.md` must select one direction. The ticket produces only one final content unit: in v1, one X post or thread.

```bash
python3 "$CONTENT_TICKET_DIR/scripts/content_ticket.py" create "TOPIC"
```

## Workflow

1. Discover discussion candidates with bundled `last30days`. Save the raw output in `discovery/raw.json`; record candidates and the selected direction in `discovery/candidates.md` and `discovery/selection.md`.
2. Before source work, compare the selected direction against `PROJECT.md`. Reject it when it misses the primary reader or every content pillar, or hits a pillar exclusion or global no-go rule.
3. Use Firecrawl to inspect primary sources. Record every claim, URL, source type, date, and excerpt in `verification/`. Do not treat discovery output as evidence.
4. Write the draft and final review text with the command below. Preserve verified facts, numbers, quotations, and sources while following `VOICE.md`.

   ```bash
   python3 "$CONTENT_TICKET_DIR/scripts/content_ticket.py" write TICKET_ID "POST TEXT"
   python3 "$CONTENT_TICKET_DIR/scripts/content_ticket.py" evidence TICKET_ID "CLAIM" "URL" "SOURCE TYPE" "EXCERPT" --published-at "YYYY-MM-DD" --verified
   ```

5. Before submitting, compare the final text with both root standards again. Confirm that it fits the selected pillar and no-go rules, and that its language and format follow `VOICE.md`. Then submit it for human review:

   ```bash
   python3 "$CONTENT_TICKET_DIR/scripts/content_ticket.py" submit TICKET_ID
   ```

6. Only when the user explicitly approves the identified ticket, approve and schedule it. Do not infer approval.

   ```bash
   python3 "$CONTENT_TICKET_DIR/scripts/content_ticket.py" approve TICKET_ID
   python3 "$CONTENT_TICKET_DIR/scripts/content_ticket.py" schedule TICKET_ID "2026-08-01T09:00:00-07:00"
   ```

7. Inspect the due queue first. Publish only with explicit user instruction and `--live`.

   ```bash
   python3 "$CONTENT_TICKET_DIR/scripts/content_ticket.py" publish-due
   python3 "$CONTENT_TICKET_DIR/scripts/content_ticket.py" publish-due --live
   ```

## Safety rules

- Root `PROJECT.md` and `VOICE.md` are the only standards; do not copy them into tickets.
- A project-standard change affects all tickets because they read the root files directly.
- Require verified evidence before approval.
- Never use browser automation or automate likes, follows, replies, or DMs.
- Keep a failed publish as `pending` with its receipt; do not retry it automatically.
