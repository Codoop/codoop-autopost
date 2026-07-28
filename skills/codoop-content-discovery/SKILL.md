---
name: codoop-content-discovery
description: Discover recent discussion candidates, review their audience value with the shared agency-agents persona, and save only worthwhile unverified leads.
---

# Codoop Content Discovery

Use this Skill to fill the local `content-leads` pool. It discovers and judges unverified leads; it does not verify sources, write posts, approve content, schedule publication, publish, or interact with social accounts.

Set `CONTENT_DISCOVERY_DIR` to the installed directory containing this `SKILL.md`; do not assume a fixed Codex or Claude installation path:

```bash
CONTENT_DISCOVERY_DIR="<directory containing this SKILL.md>"
```

## Inputs

From the workspace root, read:

- `PROJECT.md`
- `VOICE.md`
- prior `content-leads/runs/*/run.toml`
- optional `content-tickets/*/publish/performance.toml`

The unchanged reviewer persona is:

```text
skills/_shared/agents/marketing-twitter-engager.md
```

Resolve it relative to this Skill as `../_shared/agents/marketing-twitter-engager.md`. Read that whole file verbatim. Never edit, summarize into a replacement persona, or fork it.

## Workflow

1. Confirm `PROJECT.md` and `VOICE.md` exist and are non-empty.
2. Identify the discovery directions in `PROJECT.md`. Compare them with prior run metadata, then choose the least recently used direction. Run exactly one direction per invocation.
3. Turn that direction into one concise current research query and start the run:

   ```bash
   "$CONTENT_DISCOVERY_DIR/scripts/run.sh" start-discovery "DIRECTION" "QUERY"
   ```

4. Read the returned `id`, `review_candidate_ids`, and the saved `content-leads/runs/RUN_ID/raw.json`. Exact canonical-URL repeats have already been removed from `review_candidate_ids` and their existing lead has been refreshed.
   Treat a different URL about the same event as a semantic duplicate unless it contains a material new development. Reject the duplicate; for a material development, record its relationship to the older event in the review.
5. Start exactly one fresh subagent for this review. Give it, in this order:

   - the complete unchanged persona file;
   - the current `PROJECT.md` and `VOICE.md`;
   - optional historical performance data when present;
   - this run's raw discovery output;
   - the exact list of candidate IDs it must review;
   - the task packet below.

   Do not reuse an earlier reviewer conversation. The subagent must review every candidate ID returned for review; do not cap the review at a Top N.
6. Have the subagent write `content-leads/runs/RUN_ID/value-review.md` using the required format.
7. Inspect the report for completeness. Pass only ranked `go` candidates to the deterministic CLI:

   ```bash
   "$CONTENT_DISCOVERY_DIR/scripts/run.sh" complete-discovery RUN_ID \
     "CANDIDATE_ID:audience-value" \
     "CANDIDATE_ID:breakout-trend"
   ```

   Omit all selections when there is no `go`.

## Pre-verification reviewer task packet

Append the following task context after the unchanged persona:

```text
Purpose: Decide which discovery candidates are worth spending source-verification effort on.

This is a pre-verification value review. Discovery fields are leads, not facts.
Do not use Firecrawl, a browser, web search, or URL fetching.
Do not claim that a linked page contains details you have not inspected.
Do not write a finished post, approve, schedule, publish, like, follow, reply, or send messages.

Primary objective: find a truthful reason the project's target reader would want to comment on or share the eventual post. Practical utility, identity resonance, or genuine discussion can qualify. Clickbait, misleading framing, empty outrage, and meaningless stance-bait cannot.

For each candidate:
1. State what appears new for this project's audience.
2. State what judgment, workflow, tool choice, or understanding it may change.
3. State the expected click payoff as a hypothesis to verify later.
4. First attempt the strongest viable non-clickbait post angle.
5. Check PROJECT.md pillars and no-go boundaries.
6. Give go, weak, or reject.

Hard gate: if you cannot describe what the reader may gain from the source that a short post cannot replace, do not pass it on audience value.

A normal go uses pass_basis audience-value.
A candidate may use pass_basis breakout-trend only when the supplied last30days ranking, engagement, or velocity data itself shows exceptional breakout attention. Breakout attention never overrides PROJECT.md boundaries and only buys source verification, not writing or publication.

The AISI “Cheating behaviour in frontier model evaluations” pattern is weak by default when the discovery summary already contains the whole useful conclusion. It may be go only when discovery data reasonably predicts unique concrete model behavior, test conditions, failure cases, or reusable agent acceptance practices to verify.
```

## Required `value-review.md`

```md
# Value Review

## Run

- Direction:
- Query:
- Reviewed candidate IDs:
- Evidence status: Discovery data only; no linked source was opened.

## Recommended candidate

- Candidate ID:
- Verdict: go | weak | reject
- Pass basis: audience-value | breakout-trend | none
- Confidence: low | medium | high
- Project pillar:
- Why it matters now:
- Reader value:
- Expected click payoff (hypothesis; must be verified later):
- Strongest viable non-clickbait angle:
- Comment / share reason:
- Risks / reasons to reject:

## Ranked candidates

| Rank | Candidate ID | Verdict | Pass basis | Reader value | Click-payoff hypothesis | Comment/share reason | Reason |
|---|---|---|---|---|---|---|---|

## Rejected candidates

- Candidate ID:
- URL:
- Reason:
```

Every reviewed ID must appear exactly once in the ranked table. When there is no `go`, include this exact sentence:

```text
No candidate is worth source verification in this discovery run.
```

## Human override

Do not silently upgrade a `weak` or `reject`. A human override is a separate explicit CLI action with a non-empty reason; it preserves the original report and records `pass_basis = human-override`.

## Output

Report the run ID, counts by verdict, and the IDs added to `content-leads/available`. Do not call the production Skill automatically.
