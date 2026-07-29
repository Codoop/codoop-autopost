# codoop-autopost Workflow Decisions

**English** · [简体中文](./workflow-decisions.zh-CN.md)

Status: implemented in `0.0.1-alpha.4`.

## Goal

The plugin separates content operations into two independent Skills:

1. `codoop-content-discovery` discovers discussions, reviews reader value, and saves unverified leads.
2. `codoop-content-ticket` claims one lead and performs dedupe, source verification, a second review, writing, human approval, and X publishing.

The core objective is a real reason for the target reader to comment or share, not raw heat maximization. Practical utility, identity resonance, and genuine discussion may pass; clickbait, misleading framing, and empty stance-bait may not.

## Component boundaries

| Stage | Component | Responsibility |
|---|---|---|
| Initialization | `codoop-autopost-init` | Confirm root `PROJECT.md` and `VOICE.md` with `grilling`. |
| Discovery | `codoop-content-discovery` + bundled `last30days` | Run one project direction and preserve raw discovery data. |
| First value review | Pinned `marketing-twitter-engager.md` + fresh subagent | Decide whether verification is worth its cost without opening links. |
| Lead pool | Shared Python CLI | Validate IDs, admit only a reviewed `go`, canonicalize URLs, write files, and move directories atomically. |
| Content ticket | `codoop-content-ticket` | Claim or resume one lead; never accept an arbitrary topic. |
| Source verification | Small Firecrawl API client | Fetch only the bound primary source without bundling Firecrawl AGPL source. |
| Second value review | Same pinned persona + new fresh subagent | Decide whether writing is worthwhile from verified evidence. |
| Publishing | Official X API client | Publish only explicitly approved scheduled content; never automate engagement. |

The intelligent role writes fixed-format Markdown; the deterministic CLI handles state only. Before admitting a lead, it checks the selected candidate's fixed table row for `go`; it does not interpret review prose or require duplicate JSON.

## Upstream persona

`skills/_shared/agents/marketing-twitter-engager.md` is a pinned unchanged copy of the `msitarzewski/agency-agents` Marketing Division persona:

- Repository: `https://github.com/msitarzewski/agency-agents`
- Commit: `8ef49232e02431f7ca4792b487e5a85a7939ff3a`
- License: MIT, AgentLand Contributors

Both review stages read the same role file but start a new single subagent and append current project context, inputs, purpose, and constraints.

The plugin does not create a reviewer committee, modify the persona, or automatically synchronize it from upstream.

## First value review

Review every candidate not removed as an exact URL repeat. For each candidate, first construct its strongest truthful non-clickbait angle, then return:

- `go`: clear reader value and a click-payoff hypothesis worth verifying.
- `weak`: possibly credible, but insufficient value, specificity, timeliness, or payoff.
- `reject`: out of scope, derivative, hype, or fully replaceable by the short post.

A normal `go` uses `pass_basis = audience-value`.

`breakout-trend` is allowed only when supplied `last30days` ranking, engagement, or velocity itself shows exceptional breakout attention. It buys verification only and cannot bypass `PROJECT.md`, the second review, human approval, or publication gates.

Discovery data is not factual evidence. Click payoff remains a hypothesis, such as: “continue only if the source provides concrete test conditions and failure cases.”

## Local queue

```text
content-leads/
  available/
  claimed/
  consumed/
  rejected/
  runs/
```

- `runs/R-...` permanently preserves `run.toml`, `raw.json`, and the full `value-review.md`.
- Only a candidate explicitly marked `go` in the saved review table enters `available`; discovery-stage `weak` and `reject` remain in the run.
- Exact canonical URL repeats refresh the existing lead instead of being reviewed again.
- The reviewer rejects same-event different-URL duplicates; material developments may become new related leads.
- `available → claimed` uses an atomic same-filesystem directory move.
- Successful publication moves `claimed → consumed`.
- Duplicate or insufficient verified value moves `claimed → rejected`.
- Technical failure retains the claimed lead and original ticket for recovery.

Records are retained indefinitely without SQLite, a message queue, a daemon, hidden state, or a Git-driven state machine.

## Automatic selection and human promotion

Scheduled discovery triggers the complete Agent Skill, not its `start-discovery` collection command. The Skill selects a least-recently-used direction and a query distinct from the preceding run without user input, then starts a fresh review subagent.

Production first resumes interrupted claimed work. Otherwise it selects the newest discovery run first and reviewer rank within the run.

The Skill skips clearly stale leads using dates, event type, and project context. With no suitable lead it stops and never starts discovery automatically.

A human may run:

```bash
run.sh promote RUN_ID CANDIDATE_ID --reason "REASON"
```

The original run report remains unchanged, the lead uses `pass_basis = human-override`, and every production gate still applies.

## Non-bypassable safety gates

```text
first value-review go or human override
  → atomic claim
  → duplicate clear
  → Firecrawl snapshot
  → verified evidence
  → fresh post-verification review go
  → write
  → submit
  → explicit human approval
  → schedule
  → explicit publish-due --live
```

- Tickets can only come from claimed leads, and their source URL comes only from that lead.
- Firecrawl refuses to run before duplicate clearance.
- Discovery output cannot increase `verified_evidence_count`.
- A second-review `weak` or `reject` discards the ticket and moves the lead; writing and submission are blocked.
- Publishing uses an exclusive lock; success stores the X post ID, URL, and time, then consumes the lead.
- Failure retains the pending ticket, error receipt, and claimed lead with no automatic retry.
- Publishing uses the official X API only. Browser automation, auto-approval, likes, follows, replies, and direct messages are prohibited.

## Performance feedback

`record-performance` manually records impressions, comments, and shares only for published tickets and calculates:

```text
(comments + shares) / impressions × 1000
```

Later discovery reviews read the file when present and skip it when absent. There is no automatic analytics API.

## First-version boundaries

- One X post of at most 280 characters.
- One lead is consumed once.
- Multi-platform production is deferred to a later `codoop-content-ticket` change.
- Subagent tool limits are prompt-enforced; there is no extra tool sandbox.
- There is no fixed global expiry age.

## License boundaries

- Upstream material from `grilling`, `last30days`, `agency-agents`, and the X publishing path is MIT-licensed with attribution and license retained.
- Firecrawl is used through its API or a compatible endpoint; the plugin does not distribute Firecrawl's AGPL service source.

Upstream projects:

- https://github.com/msitarzewski/agency-agents
- https://github.com/mvanhorn/last30days-skill
- https://github.com/alberduris/skills/tree/main/plugins/x-twitter
- https://github.com/coreyhaines31/marketingskills
- https://github.com/firecrawl/firecrawl

Return to the [project README](../README.md).
