---
name: codoop-content-ticket
description: Claim one reviewed unverified lead, verify its primary source, run a second value review, and produce one evidence-first X post with mandatory human approval.
---

# Codoop Content Ticket / Codoop 内容工单

Run this Skill in an initialized content-operations workspace. Read root `PROJECT.md` and `VOICE.md` first. If either is missing or empty, stop and tell the user to run `codoop-autopost-init`.

Set `CONTENT_TICKET_DIR` to the installed directory containing this `SKILL.md`:

```bash
CONTENT_TICKET_DIR="<directory containing this SKILL.md>"
```

This Skill does not discover topics. It consumes one lead previously reviewed by `codoop-content-discovery`. Do not run discovery automatically when the pool is empty.

## 1. Resume or claim one lead

First inspect interrupted work:

```bash
"$CONTENT_TICKET_DIR/scripts/run.sh" list-leads --status claimed
```

Resume an existing claimed ticket before taking another lead. If there is no interrupted ticket, list available leads:

```bash
"$CONTENT_TICKET_DIR/scripts/run.sh" list-leads
```

The list is ordered by newest discovery run and then reviewer rank. Starting from the top, use `published_at`, `discovered_at`, `last_seen_at`, the event type, and `PROJECT.md` to skip any clearly stale lead. Do not delete stale records.

If no suitable lead remains, stop without side effects and report:

```text
No suitable unverified lead. Run codoop-content-discovery first.
```

Do not ask the user to choose. Atomically claim the best suitable lead:

```bash
"$CONTENT_TICKET_DIR/scripts/run.sh" claim LEAD_ID
```

If another process won the claim, refresh the list and try the next suitable lead. Repeating `claim` for an already claimed lead resumes its existing ticket and never creates a second one.

## 2. Duplicate gate before source access

Run the deterministic duplicate check. It reads the URL bound to the ticket; never substitute another URL.

```bash
"$CONTENT_TICKET_DIR/scripts/run.sh" dedupe TICKET_ID
```

If it matches a recently pending or published source, stop. If a different URL is clearly the same event without material new information, record the semantic duplicate reason:

```bash
"$CONTENT_TICKET_DIR/scripts/run.sh" discard TICKET_ID "Same event; no material new information."
```

Only a genuinely new source or material development may continue.

## 3. Verify the bound primary source

Only after the duplicate decision is clear, fetch the ticket-bound URL through Firecrawl:

```bash
"$CONTENT_TICKET_DIR/scripts/run.sh" scrape TICKET_ID
```

The command saves the source snapshot inside the ticket. Treat `discovery/raw.json` and the first `discovery/value-review.md` as unverified context, never as evidence.

Record each supported claim from the primary source:

```bash
"$CONTENT_TICKET_DIR/scripts/run.sh" evidence TICKET_ID \
  "CLAIM" "URL" "SOURCE TYPE" "EXCERPT" \
  --published-at "YYYY-MM-DD" --verified
```

Every claim used in the post needs a direct source URL, publication date, source type, and excerpt.

## 4. Fresh post-verification value review

Read the unchanged persona at:

```text
skills/_shared/agents/marketing-twitter-engager.md
```

Resolve it relative to this Skill as `../_shared/agents/marketing-twitter-engager.md`. Start exactly one fresh subagent; do not reuse the pre-verification reviewer conversation. Give it:

- the complete unchanged persona file;
- `PROJECT.md` and `VOICE.md`;
- the bound lead and first `discovery/value-review.md`;
- verified `verification/evidence.md` and the saved source snapshot;
- the task packet below.

```text
Purpose: Decide whether verified evidence now proves that this lead is worth turning into a post.

Discovery material is context, not evidence. Base factual conclusions only on verification artifacts.
First construct the strongest truthful, non-clickbait angle.
Require a real reason for the target reader to comment or share: practical utility, identity resonance, or genuine discussion.
Confirm what the linked source gives the reader that the short post cannot replace.
The earlier audience-value, breakout-trend, or human-override basis only justified verification; none guarantees writing.
Do not write the finished post, approve, schedule, publish, like, follow, reply, or send messages.
Return go, weak, or reject with a concrete reason.
```

Have it write `content-tickets/TICKET_ID/verification/value-review.md`:

```md
# Verified Value Review

- Verdict: go | weak | reject
- Confidence: low | medium | high
- First-review pass basis:
- Verified new information:
- Reader value:
- Verified click payoff:
- Strongest viable non-clickbait angle:
- Comment / share reason:
- Evidence references:
- Risks / rejection reason:
```

Record the outcome:

```bash
"$CONTENT_TICKET_DIR/scripts/run.sh" record-post-review TICKET_ID go \
  --report "content-tickets/TICKET_ID/verification/value-review.md"
```

For `weak` or `reject`, the lead moves to `content-leads/rejected` and the workflow stops before writing.

## 5. Write and submit

Only after the second review is `go`, write one X post of at most 280 characters. Follow `VOICE.md`, preserve verified meaning, and include direct source URLs rather than a bare source label.

```bash
"$CONTENT_TICKET_DIR/scripts/run.sh" write TICKET_ID "POST TEXT"
"$CONTENT_TICKET_DIR/scripts/run.sh" submit TICKET_ID
```

Submitting requests human review; it is not approval.

## 6. Human approval and publication

Only when the user explicitly approves the identified ticket:

```bash
"$CONTENT_TICKET_DIR/scripts/run.sh" approve TICKET_ID
"$CONTENT_TICKET_DIR/scripts/run.sh" schedule TICKET_ID "2026-08-01T09:00:00-07:00"
```

Inspect the due queue first. Publish only with explicit user instruction and `--live`:

```bash
"$CONTENT_TICKET_DIR/scripts/run.sh" publish-due
"$CONTENT_TICKET_DIR/scripts/run.sh" publish-due --live
```

A successful publication consumes the lead. A technical failure leaves it claimed with its receipt. Never retry automatically. Only after the user confirms that X did not create the post:

```bash
"$CONTENT_TICKET_DIR/scripts/run.sh" retry TICKET_ID --confirmed-not-published
```

Optional performance data may be recorded later:

```bash
"$CONTENT_TICKET_DIR/scripts/run.sh" record-performance TICKET_ID \
  --impressions 1000 --comments 4 --shares 8
```

Missing performance data never blocks the workflow.

## Safety rules / 安全规则

- Root `PROJECT.md` and `VOICE.md` remain the only project standards.
- A lead is unverified until primary-source evidence is recorded.
- First value review → duplicate gate → Firecrawl → second value review is mandatory.
- `breakout-trend` and `human-override` never bypass source verification or the second review.
- Human approval remains mandatory before scheduling or publishing.
- Use only the official X API. Never automate browser publishing, likes, follows, replies, or DMs.
- Keep failed publication state and require explicit, human-confirmed retry.

- 根目录 `PROJECT.md` 与 `VOICE.md` 是唯一项目标准。
- lead 只是待核验线索，不是事实。
- 第一次价值审核、重复门、Firecrawl 核验、第二次价值审核的顺序不可跳过。
- 热度例外和人工提升都不能绕过核验或二审。
- 排程和发布前必须获得明确的人工批准。
- 禁止浏览器自动发布及自动点赞、关注、回复或私信。
