<div align="center">

# codoop-autopost

**English** · [简体中文](./README.zh-CN.md)

**Discover content worth discussing, then verify it before publishing**

![Codex Plugin](https://img.shields.io/badge/Codex-plugin-111827)
![Claude Code Plugin](https://img.shields.io/badge/Claude%20Code-plugin-8A63D2)
![Python](https://img.shields.io/badge/python-3.12%2B-blue)
![Local files](https://img.shields.io/badge/state-local%20files-brightgreen)
![License](https://img.shields.io/badge/license-MIT-green)

</div>

**codoop-autopost** is a local content-operations plugin that separates topic discovery from content production.

It first reviews whether a recent discussion gives the target reader a real reason to comment, share, or continue reading. Only worthwhile unverified leads enter source verification, a second value review, writing, human approval, and X publishing.

The workflow never publishes through browser automation and never automates replies, likes, follows, or direct messages. Operational state lives in ordinary local files, with no Git or database requirement.

## Workflow

```text
codoop-autopost-init
  → codoop-content-discovery
      → last30days
      → pre-verification value review
      → content-leads/available
  → codoop-content-ticket
      → atomic lead claim
      → duplicate gate
      → Firecrawl primary-source verification
      → post-verification value review
      → draft
      → human approval
      → official X API
```

The two main workflows are independent:

- `codoop-content-discovery` rotates through one `PROJECT.md` discovery direction per run, reviews every new candidate, and saves only `go` candidates to the lead pool.
- `codoop-content-ticket` claims one unused lead, verifies it, runs a fresh second value review, and prepares one X post for explicit human approval.

`weak` and `reject` candidates remain permanently in the discovery-run report without consuming Firecrawl or writing effort.

## Install

### Codex

```bash
codex plugin marketplace add Codoop/codoop-autopost
codex plugin add codoop-autopost@codoop-autopost
```

### Claude Code

```text
/plugin marketplace add Codoop/codoop-autopost
/plugin install codoop-autopost@codoop-autopost
```

Restart the Agent after installation. The main plugin bundles:

- `codoop-autopost-init`
- `codoop-content-discovery`
- `codoop-content-ticket`
- `grilling`
- `last30days`
- `firecrawl`
- `social-content`
- `copy-editing`
- `x-twitter`

For local development or offline plugin debugging:

```bash
./scripts/install-skill.sh
```

## Content-operations workspace

Use one workspace per account or brand:

```text
content-operations/
├── config.toml
├── PROJECT.md
├── VOICE.md
├── content-leads/
│   ├── available/
│   │   └── L-.../lead.toml
│   ├── claimed/
│   ├── consumed/
│   ├── rejected/
│   └── runs/
│       └── R-.../
│           ├── run.toml
│           ├── raw.json
│           └── value-review.md
└── content-tickets/
    └── C-.../
        ├── ticket.toml
        ├── discovery/
        │   ├── raw.json
        │   ├── selection.md
        │   ├── value-review.md
        │   └── duplicate-check.md
        ├── verification/
        │   ├── evidence.md
        │   ├── claims.md
        │   ├── value-review.md
        │   └── source-snapshots/source.md
        ├── writing/
        ├── review/
        └── publish/
            ├── schedule.toml
            ├── receipt.json
            └── performance.toml
```

`content-leads` is an unverified-content-lead queue, not a fact database. Runs and leads are retained indefinitely.

When the same canonical URL appears again, the workflow refreshes `last_seen_at` and engagement instead of creating another lead. Claiming uses an atomic directory move, so the same lead cannot create two new tickets.

## Quick start

### 1. Initialize the project

```text
Use codoop-autopost-init to set up this content-operations project.
```

Initialization creates the workspace's sole `PROJECT.md` and `VOICE.md` through a one-question-at-a-time interview. Discovery and production refuse to run until both are confirmed.

It also creates a private `config.toml` template without asking for secrets in chat:

- Obtain `firecrawl.api_key` from the [Firecrawl dashboard](https://www.firecrawl.dev/) to read primary sources.
- Obtain the four X OAuth values from the [X Developer Console](https://developer.x.com/en/portal/dashboard); the App needs user write permission.

Environment variables can override the configuration file. Never place real secrets in chat, project standards, leads, tickets, screenshots, or Git.

### 2. Fill the lead pool

```text
Use codoop-content-discovery to discover and review content leads.
```

The review uses a pinned, unchanged copy of the `agency-agents` Marketing `Twitter Engager` persona. Every run starts one fresh subagent and appends only current project context and task purpose.

For scheduled discovery, trigger an Agent task that runs this whole Skill. Do not schedule the low-level `start-discovery` command: it only collects raw candidates and cannot start the review subagent. Discovery chooses its direction and a query distinct from the previous run automatically; it does not wait for user input.

The pre-verification reviewer cannot open links, call Firecrawl, or treat discovery summaries as facts.

Pass bases:

- `audience-value`: the candidate has a concrete reader benefit and a click-payoff hypothesis worth verifying.
- `breakout-trend`: supplied `last30days` data shows exceptional breakout attention. This buys source verification only.
- `human-override`: a human explicitly promotes a reviewed candidate and records a reason.

None of these bypasses project boundaries, source verification, the second value review, or human publication approval.

### 3. Produce one post

```text
Use codoop-content-ticket to claim the best available lead and prepare one post for approval.
```

Production automatically selects the highest-ranked, non-stale lead from the newest discovery run. It resumes interrupted claimed work before taking another lead.

If the pool has no suitable lead, production stops and asks for a discovery run. It never starts discovery automatically.

## Non-bypassable gates

- Only a candidate explicitly marked `go` in the saved first-review table, or a reasoned human promotion, can enter `available`.
- Firecrawl cannot run before duplicate clearance.
- The saved primary-source snapshot and explicit verified evidence must exist before the second review.
- Every pass basis must pass a fresh second review before writing.
- No second-review `go` means no `write` or `submit`.
- Scheduling and publishing require explicit human approval.
- `publish-due` defaults to dry-run; only explicit instruction with `--live` calls the official X API.
- A failed publication preserves its receipt and claimed lead, with no automatic retry.

## Optional performance feedback

After publication, impressions, comments, and shares can be recorded manually:

```bash
run.sh record-performance TICKET_ID \
  --impressions 1000 --comments 4 --shares 8
```

The workflow calculates interactions per 1,000 impressions and includes existing performance files in later discovery context. Missing data blocks nothing, and no analytics API is called automatically.

## Documentation

- [Workflow decisions](./docs/workflow-decisions.md)
- [Project initialization and content workflow design](./docs/project-initialization-optimization-plan.md)
- [Changelog](./CHANGELOG.md)

## Scope

- One X post of at most 280 characters per consumed lead.
- Official X API only.
- Local files only; no database, daemon, or Git-driven state machine.
- Multi-platform production is intentionally deferred.
