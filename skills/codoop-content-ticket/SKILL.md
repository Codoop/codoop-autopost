---
name: codoop-content-ticket
description: Create and operate one evidence-first content ticket in an initialized codoop-autopost project. 用于发现选题、核验来源、起草、审核、排程或发布必须遵守 PROJECT.md 和 VOICE.md 的单条社媒内容。
---

# Codoop Content Ticket / Codoop 内容工单

Run this Skill in the root of a content-operations project. Read `PROJECT.md` and `VOICE.md` first. If either is missing or empty, stop and tell the user to run `codoop-autopost-init`; do not infer a vertical or voice.

在内容运营项目根目录运行此 Skill。先读取 `PROJECT.md` 与 `VOICE.md`；任一文件缺失或为空时，立即停止并提示用户运行 `codoop-autopost-init`，不得自行推断赛道或语气。

Set `CONTENT_TICKET_DIR` to the installed directory containing this `SKILL.md`; do not assume `~/.codex/skills`, because marketplace plugins use their own cache path. Its bundled `scripts/run.sh` selects Python 3.12+.

将 `CONTENT_TICKET_DIR` 设为包含此 `SKILL.md` 的已安装目录；不要假设它位于 `~/.codex/skills`，因为 Marketplace 插件使用自己的缓存路径。其内置 `scripts/run.sh` 会选择 Python 3.12+。

```bash
CONTENT_TICKET_DIR="<directory containing this SKILL.md>"
```

## One ticket, one content unit

## 一张工单，一个内容单元

Create a `C-...` ticket before discovering topics. Read `PROJECT.md` and choose one of its discovery directions; turn it into a concise current research query and pass that query as `TOPIC`. A ticket can keep multiple discovery candidates, but `discovery/selection.md` must select one direction. The ticket produces one X post of at most 280 characters.

在发现热点前创建一张 `C-...` 工单。先读取 `PROJECT.md` 并选择其中一个发现方向，将其改写为简洁的当期研究查询，再将该查询作为 `TOPIC` 传入。工单可保留多个发现候选，但 `discovery/selection.md` 必须选定一个方向。每张工单只产出一条不超过 280 字符的 X 帖子。

```bash
"$CONTENT_TICKET_DIR/scripts/run.sh" create "TOPIC"
```

## Workflow

## 工作流

1. Discover discussion candidates with bundled `last30days` for the ticket's stored `TOPIC`. The command saves raw output in `discovery/raw.json`; record candidates and the selected direction in `discovery/candidates.md` and `discovery/selection.md`.

   ```bash
   "$CONTENT_TICKET_DIR/scripts/run.sh" discover TICKET_ID
   ```
2. Before any Firecrawl call, run the duplicate gate with the selected candidate URL. It compares the canonical URL with evidence URLs in `pending` and `done` tickets from the previous 14 days and saves `discovery/duplicate-check.md`. A match changes the ticket to `discarded`; stop immediately. For a different URL that is clearly the same event without material new information, record the reason and discard it. Only a new source or material development may continue.

   ```bash
   "$CONTENT_TICKET_DIR/scripts/run.sh" dedupe TICKET_ID "CANDIDATE_URL"
   "$CONTENT_TICKET_DIR/scripts/run.sh" discard TICKET_ID "Same event; no material new information."
   ```

3. Before source work, compare the selected direction against `PROJECT.md`. Reject it when it misses the primary reader or every content pillar, or hits a pillar exclusion or global no-go rule.
4. Use Firecrawl to inspect only surviving primary sources. Record every claim, URL, source type, date, and excerpt in `verification/`. Do not treat discovery output as evidence.
5. Write the draft and final review text with the command below. Preserve verified facts, numbers, quotations, and sources while following `VOICE.md`.

   ```bash
   "$CONTENT_TICKET_DIR/scripts/run.sh" write TICKET_ID "POST TEXT"
   "$CONTENT_TICKET_DIR/scripts/run.sh" evidence TICKET_ID "CLAIM" "URL" "SOURCE TYPE" "EXCERPT" --published-at "YYYY-MM-DD" --verified
   ```

6. Before submitting, compare the final text with both root standards again. Confirm that it fits the selected pillar and no-go rules, and that its language and format follow `VOICE.md`. Then submit it for human review:

   ```bash
   "$CONTENT_TICKET_DIR/scripts/run.sh" submit TICKET_ID
   ```

7. Only when the user explicitly approves the identified ticket, approve and schedule it. Do not infer approval.

   ```bash
   "$CONTENT_TICKET_DIR/scripts/run.sh" approve TICKET_ID
   "$CONTENT_TICKET_DIR/scripts/run.sh" schedule TICKET_ID "2026-08-01T09:00:00-07:00"
   ```

8. Inspect the due queue first. Publish only with explicit user instruction and `--live`.

   ```bash
   "$CONTENT_TICKET_DIR/scripts/run.sh" publish-due
   "$CONTENT_TICKET_DIR/scripts/run.sh" publish-due --live
   ```

If publishing fails, preserve the ticket and receipt. Only after the user has checked that X did not create the post, manually re-enable it; the old failure receipt is archived in `publish/attempts/`.

```bash
"$CONTENT_TICKET_DIR/scripts/run.sh" retry TICKET_ID --confirmed-not-published
```

工作流中文说明：

1. 针对工单保存的 `TOPIC`，使用内置 `last30days` 发现讨论候选。该命令会将原始输出存入 `discovery/raw.json`，并将候选与选定方向记录在 `discovery/candidates.md` 和 `discovery/selection.md`：`"$CONTENT_TICKET_DIR/scripts/run.sh" discover TICKET_ID`。
2. 调用任何 Firecrawl 前，对选定候选 URL 运行重复门。它会与过去 14 天 `pending` 和 `done` 工单的证据 URL 比较规范化 URL，并写入 `discovery/duplicate-check.md`。命中时工单变为 `discarded`，必须立即停止。若 URL 不同但明显是同一事件且没有实质新信息，记录理由并丢弃；只有新来源或实质新进展才能继续：`"$CONTENT_TICKET_DIR/scripts/run.sh" dedupe TICKET_ID "CANDIDATE_URL"`；`"$CONTENT_TICKET_DIR/scripts/run.sh" discard TICKET_ID "同一事件，没有实质新信息。"`。
3. 开始来源工作前，将选定方向与 `PROJECT.md` 对照。若不符合主读者或任何内容支柱，或命中支柱排除项或全局禁区，应拒绝该方向。
4. 只使用 Firecrawl 检查通过重复门的一手来源。在 `verification/` 中记录每条主张、URL、来源类型、日期和摘录；不得把发现结果当作证据。
5. 用上述命令写入草稿和最终审核文本。遵守 `VOICE.md`，且保留已核验事实、数字、引文和来源；所有来源须直接写出 URL，不能只写 `Source: 名称`。
6. 提交前再次将最终文本与两份根目录标准对照；确认符合选定支柱和禁区规则，且语言与格式遵守 `VOICE.md`，随后提交人工审核。
7. 只有用户明确批准指定工单时，才可批准并排程；绝不可推断批准。
8. 先检查到期队列。只有获得用户明确指令且带 `--live` 时才可发布。

发布失败时保留工单和回执。只有用户确认 X 没有创建帖子后，才可手动重新启用；旧失败回执会归档到 `publish/attempts/`：`"$CONTENT_TICKET_DIR/scripts/run.sh" retry TICKET_ID --confirmed-not-published`。

## Safety rules

## 安全规则

- Root `PROJECT.md` and `VOICE.md` are the only standards; do not copy them into tickets.
- A project-standard change affects all tickets because they read the root files directly.
- Require verified evidence before approval.
- Run the duplicate gate before Firecrawl; a `discarded` ticket cannot be edited, approved, scheduled, or published.
- Never use browser automation or automate likes, follows, replies, or DMs.
- Keep a failed publish as `pending` with its receipt; never retry automatically. Use `retry ... --confirmed-not-published` only after human inspection.

- 根目录 `PROJECT.md` 与 `VOICE.md` 是唯一标准；不得复制到工单内。
- 项目标准变更会影响所有工单，因为它们直接读取根目录文件。
- 批准前必须具备已核验证据。
- 必须在 Firecrawl 前运行重复门；`discarded` 工单不得编辑、批准、排程或发布。
- 禁止浏览器自动化，以及自动点赞、关注、回复或私信。
- 发布失败时保留带回执的 `pending` 状态；不得自动重试。只有人工检查后才可使用 `retry ... --confirmed-not-published`。
