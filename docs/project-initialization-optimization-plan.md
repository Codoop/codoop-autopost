# Project Initialization and Content Workflow Design

**English** · [简体中文](./project-initialization-optimization-plan.zh-CN.md)

Status: implemented in `0.0.1-alpha.3`.

## Purpose

Initialization defines one content-operations workspace before discovery or production begins. The plugin then keeps topic discovery separate from content production:

```text
initialize standards
  → discover and review leads
  → save worthwhile unverified leads
  → claim one unused lead
  → verify, write, approve, and publish
```

This separation lets discovery collect several useful opportunities without creating a content ticket for every candidate.

## Skill structure

```text
codoop-autopost
├── codoop-autopost-init
├── codoop-content-discovery
├── codoop-content-ticket
└── supporting bundled Skills
```

- `codoop-autopost-init` confirms the project charter and voice guide.
- `codoop-content-discovery` runs `last30days`, reviews every new candidate, and stores only worthwhile leads.
- `codoop-content-ticket` claims one unused lead and runs the evidence-first production workflow.
- Bundled supporting Skills provide interviewing, discovery, source reading, editing, and official X publishing.

Discovery and production refuse to run when `PROJECT.md` or `VOICE.md` is missing.

## Initialization boundary

The initialization Skill:

1. Uses `grilling` to ask one question at a time.
2. Confirms `PROJECT.md` before writing it.
3. Confirms `VOICE.md` before writing it.
4. Creates a private `config.toml` template only when missing.
5. Ensures `content-leads/` and `content-tickets/` exist.

It does not discover topics, create tickets, verify sources, or ask users to paste secrets into chat. Existing configuration values remain unchanged.

Later changes use the same Skill: a positioning change reconfirms `PROJECT.md`; a voice-only change reconfirms `VOICE.md`.

## `PROJECT.md` contract

`PROJECT.md` answers what the project covers, whom it serves, and what it excludes:

```md
# Project Charter

## Vertical definition
## Primary reader
## Content pillars
## Discovery directions
## Global no-go areas
```

- Define one specific vertical rather than a broad label such as “AI” or “technology.”
- Define one primary reader using identity and context, current goal, and existing knowledge.
- Maintain three to five durable content pillars with explicit inclusions and exclusions.
- Maintain three to five reusable discovery directions connected to those pillars.
- Record hard cross-pillar exclusions such as irrelevant trend-chasing, unverified rumors, personal attacks, or user-excluded risks.

Platform credentials, voice rules, daily topic ideas, SEO keyword banks, and project-level source whitelists do not belong in `PROJECT.md`.

## `VOICE.md` contract

`VOICE.md` answers how the project should speak:

```md
# Voice Guide

## Language
## Reader distance and overall tone
## Sentences and rhythm
## Formatting and punctuation
## Preferred expressions
## Prohibited expressions
## Confirmed style rules
```

Users may optionally provide writing samples. The Skill extracts checkable rules from them; it does not copy their wording, facts, or positions. Labels such as “professional” or “interesting” are too vague until converted into rules that can be checked against a draft.

## Workspace layout

```text
content-operations/
├── config.toml
├── PROJECT.md
├── VOICE.md
├── content-leads/
│   ├── available/
│   ├── claimed/
│   ├── consumed/
│   ├── rejected/
│   └── runs/
└── content-tickets/
```

`content-leads/` is a permanent local queue of unverified leads and discovery reports. `content-tickets/` stores evidence, writing, review, scheduling, publication receipts, and optional performance data for claimed leads.

The workflow uses local files and atomic directory moves. It requires no database, background service, hidden state, or Git-based state machine.

## Handoff between workflows

### Discovery

Each discovery run selects one project discovery direction, saves the raw `last30days` result, and asks a fresh review subagent to evaluate every new candidate. The reviewer uses the pinned upstream Marketing `Twitter Engager` persona plus the current project context and task instructions.

The reviewer cannot open candidate links or treat discovery summaries as facts. A normal candidate enters `content-leads/available` only when it receives `go`; `weak` and `reject` remain in the permanent run report. Exceptional measured attention may use the limited `breakout-trend` pass basis, and a human may explicitly promote a reviewed candidate with a recorded reason.

### Production

Production resumes interrupted claimed work first. Otherwise it automatically claims the best non-stale lead from the newest run. The same lead cannot be claimed twice.

The ticket then performs duplicate checking, primary-source verification through Firecrawl, a fresh post-verification value review, writing, explicit human approval, and official X API publishing. If no suitable lead exists, production stops and asks for another discovery run; it never starts discovery automatically.

## Safety invariants

- Discovery data is a lead, not factual evidence.
- Firecrawl cannot run before a lead is claimed and duplicate clearance passes.
- Writing cannot begin without a saved primary-source snapshot, explicit verified evidence, and a second-review `go`.
- `breakout-trend` and human promotion buy verification only; they bypass no later gate.
- Publication requires explicit human approval and an explicit live command.
- Browser publishing and automated replies, likes, follows, or direct messages are prohibited.
- A successfully published lead is consumed and cannot create another ticket.
- Failed publication retains the ticket, receipt, and claimed lead for manual recovery.

## Current scope

The current producer creates one X post of at most 280 characters per lead. Multi-platform production is intentionally deferred; it can later reuse the same lead pool and evidence workflow without changing discovery.

See [Workflow Decisions](./workflow-decisions.md) for the detailed state and review rules, or return to the [project README](../README.md).
