# Changelog

All notable changes to Codoop-autopost will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.0.1-alpha.2] - 2026-07-27

### Added

- `codoop-autopost-init` creates a missing private `config.toml` template after project standards are confirmed and never overwrites an existing configuration.

### Changed

- Explain Firecrawl and X OAuth configuration purposes, official acquisition paths, and secret-handling rules at the end of initialization without requesting secrets in the interview.
- Move the configuration template into the initialization Skill and ignore real `config.toml` files by default.
- Make maintained user and Skill documentation bilingual in Chinese and English; keep this changelog English-only.
- Bundle the MIT-licensed `last30days v3.18.3` runtime, eliminating its separate download and its incomplete-download failure mode.
- Add `run.sh` launchers that select Python 3.12+ or honor `CODOOP_AUTOPOST_PYTHON`.
- Require direct source URLs in social-content review sources instead of bare source names.
- Save each ticket's bundled-last30days JSON output to `discovery/raw.json` and derive its query from a `PROJECT.md` discovery direction.
- Make Firecrawl, X publishing, and initialization launchers independent of the shared plugin runtime; make the development installer copy that runtime for content-ticket use.
- Add an explicit human-confirmed retry path that archives a failed publishing receipt before re-enabling a pending ticket.
- Clarify the v1 scope as one X post of at most 280 characters, not threads.
- Add a pre-Firecrawl duplicate gate that discards candidates matching a source URL used by a recent pending or published ticket and records the result locally.

## [0.0.1-alpha.1] - 2026-07-27

### Added

- Bundle project initialization, content tickets, trend discovery, source verification, editing, and X publishing in one plugin.
- Add `codoop-autopost-init` to confirm root `PROJECT.md` and `VOICE.md` through a one-question-at-a-time interview.
- Add `codoop-content-ticket` to retain each content ticket's complete workflow artifacts in `content-tickets/C-...`.
- Publish through the official X API only after explicit human approval.

### Changed

- Store ticket states and publishing receipts entirely in local files, without a database.
- Remove optional Skill UI metadata and unnecessary macOS/Python local files.
