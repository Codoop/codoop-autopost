---
name: codoop-autopost-init
description: Initialize or update a codoop-autopost content-operations project. Use when setting a project's vertical, primary reader, content pillars, exclusions, language, voice, or writing rules before any content tickets are created.
---

# Codoop Autopost Initialization

Use this Skill only in the root of a content-operations project. It creates or updates the two human-approved standards that `codoop-content-ticket` must read:

- `PROJECT.md`: what the project writes about.
- `VOICE.md`: how the project writes.

Do not ask for Firecrawl or X credentials. They belong in `config.toml` and are not required for initialization.

## Interview rules

Use the bundled `grilling` Skill for the interview. Ask one question at a time. Give a recommendation, reason, and a concrete example before asking for the user's answer. Treat every recommendation as unconfirmed until the user accepts it.

Do not write either final file while its interview is in progress. Do not save a draft interview transcript. After the user explicitly confirms the complete document, write it and then move to the next document.

If only one standard is being changed, interview and replace only that file.

## Build `PROJECT.md`

Ask until all of these are specific and confirmed:

1. One vertical-sentence definition and its relevance rule.
2. One primary reader: identity and context, current goal, and existing knowledge.
3. Three to five content pillars. Each pillar has a name, what it includes, and what it excludes.
4. Global no-go topics, formats, risk categories, and irrelevant trend-chasing.

Do not add a content promise, business goal, editorial stance, platform configuration, credentials, source whitelist, or detailed demographic persona unless the user later explicitly asks for them.

## Build `VOICE.md`

After `PROJECT.md` is confirmed, ask until all of these are specific and confirmed:

1. Main language and English-term policy.
2. Reader distance, desired tone, and tone to avoid.
3. Sentence length, opening pattern, structure, pronoun use, and paragraph or thread rhythm.
4. Lists, headings, emoji, punctuation, links, citations, and CTA preferences.
5. Preferred expressions and prohibited expressions.
6. Concrete style rules derived from the conversation or optional user-provided samples.

Accept examples as optional input. Extract only reusable rules; never copy a sample's facts, opinions, or text into `VOICE.md`.

## Finish

After both documents are confirmed, ensure `content-tickets/` exists. State that the project is ready for `codoop-content-ticket`. Never create a content ticket during initialization.
