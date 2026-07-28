# 运营项目初始化与内容工单优化方案 / Content-operations initialization and ticket plan

状态：第一版已实现。
Status: implemented for v1.

## 目标 / Goal

把插件拆成“先定义运营标准，再运行内容工单”的两层工作流。用户只安装一个 `codoop-autopost` 插件；每个运营项目只服务一个垂直赛道，后续的热点筛选、来源核验、草稿、审核与发布都必须遵守该项目已确认的标准。

Split the plugin into two layers: define operating standards first, then run content tickets. Users install only `codoop-autopost`; each operations workspace serves one vertical, and all later trend selection, source verification, drafting, review, and publishing must follow its confirmed standards.

## 插件内的 Skill / Skills in the plugin

```text
codoop-autopost plugin / 插件
├── codoop-autopost-init
├── codoop-content-ticket
└── grilling
```

- `codoop-autopost-init`：初始化或更新运营项目。调用 `grilling` 与用户逐题沟通，分别产出并确认 `PROJECT.md`、`VOICE.md`。/ Initializes or updates a workspace. It uses `grilling` one question at a time, then creates and confirms `PROJECT.md` and `VOICE.md`.
- `codoop-content-ticket`：创建和推进一张内容工单。它不发起定位访谈，只读取已确认的项目标准。/ Creates and advances one content ticket. It does not run positioning interviews; it reads confirmed project standards only.
- `grilling`：原名内置，不要求用户另行安装。保留其原有名称与 MIT 归属。/ Is bundled under its original name with its MIT attribution; users do not install it separately.

`codoop-content-ticket` 发现 `PROJECT.md` 或 `VOICE.md` 缺失时，必须拒绝创建、修改、排程或发布工单，并提示用户先运行 `codoop-autopost-init`。

If either `PROJECT.md` or `VOICE.md` is missing, `codoop-content-ticket` must refuse to create, change, schedule, or publish a ticket and direct the user to `codoop-autopost-init`.

## 运营项目目录 / Workspace layout

```text
content-operations/
├── config.toml
├── PROJECT.md
├── VOICE.md
└── content-tickets/
    └── C-YYYYMMDD-<slug>/
        ├── ticket.toml
        ├── discovery/
        │   ├── raw.json
        │   ├── candidates.md
        │   └── selection.md
        ├── verification/
        │   ├── evidence.md
        │   ├── claims.md
        │   └── source-snapshots/
        ├── writing/
        │   ├── brief.md
        │   ├── drafts.md
        │   └── edited.md
        ├── review/
        │   ├── final.md
        │   └── approval.md
        └── publish/
            ├── schedule.toml
            └── receipt.json
```

- `config.toml`：已启用的平台、凭据、API 地址和运行参数。第一版只启用 X；凭据不进入项目标准或工单。/ Enabled platforms, credentials, API endpoints, and runtime settings. V1 enables X only; credentials never enter standards or tickets.
- `PROJECT.md`：赛道与内容边界。/ Vertical and content boundaries.
- `VOICE.md`：语言和表达规则。/ Language and expression rules.
- `content-tickets/`：跨平台的内容工单目录；`C-` 表示 Content，不绑定 X 或单条帖子。/ Cross-platform content-ticket directory; `C-` means Content and is not tied to X or one post.
- 所有内容工单直接读取根目录的 `PROJECT.md` 与 `VOICE.md`；不保存副本或版本快照。/ All tickets read root `PROJECT.md` and `VOICE.md` directly; no copy or version snapshot is stored.

## 初始化流程 / Initialization flow

初始化不要求 Firecrawl 或 X 凭据。两份标准确认后，初始化 Skill 会创建私有 `config.toml` 模板但保留空值；用户可在需要核验或发布时再填写凭据。已有 `config.toml` 必须原样保留。

Initialization does not require Firecrawl or X credentials. After both standards are confirmed, the initialization Skill creates a private `config.toml` template with empty values; users fill credentials only when verification or publishing needs them. An existing `config.toml` must remain unchanged.

1. 用户显式运行 `codoop-autopost-init`。/ The user explicitly runs `codoop-autopost-init`.
2. Skill 使用 `grilling` 一次只提出一个问题；每题先给推荐答案、理由和例子，用户确认、修改或否决后才进入下一题。/ The Skill uses `grilling` for one question at a time, with a recommendation, rationale, and example before the user confirms, changes, or rejects it.
3. 先完成 `PROJECT.md` 的访谈和显式确认。/ Complete and explicitly confirm the `PROJECT.md` interview first.
4. 再基于已确认的项目定位，完成 `VOICE.md` 的访谈和显式确认。/ Then complete and explicitly confirm `VOICE.md` from the confirmed positioning.
5. 两份文件都确认后，初始化 Skill 创建缺失的 `config.toml` 模板并确保 `content-tickets/` 存在，才宣布项目可以创建内容工单。/ After both files are confirmed, create the missing `config.toml` template and ensure `content-tickets/` exists before declaring the workspace ready for content tickets.

不保存访谈草案。用户未明确确认前，Agent 不得写入正式 `PROJECT.md` 或 `VOICE.md`，也不得将访谈中的推测当作工单标准。

Do not save interview drafts. Before explicit user confirmation, the agent must not write final `PROJECT.md` or `VOICE.md`, nor treat interview assumptions as ticket standards.

以后修改赛道或语气时，也使用 `codoop-autopost-init` 与 `grilling`：只改赛道则只重新确认 `PROJECT.md`；只改语气则只重新确认 `VOICE.md`。

Use `codoop-autopost-init` and `grilling` for later vertical or voice changes too: reconfirm only `PROJECT.md` for a vertical change, and only `VOICE.md` for a voice change.

## `PROJECT.md` 规范 / `PROJECT.md` specification

`PROJECT.md` 回答“写什么、写给谁、不写什么”。第一版不要求内容承诺、商业目标、编辑立场或项目级来源清单。

`PROJECT.md` answers “what to write, for whom, and what not to write.” V1 does not require a content promise, business goal, editorial stance, or project-level source list.

```md
# 项目章程 / Project Charter

## 赛道定义 / Vertical definition

- 一句话定义 / One-sentence definition:
- 解释 / Explanation:
- 候选内容的相关性判断原则 / Relevance rule for candidate content:

## 主读者 / Primary reader

- 身份与场景 / Identity and context:
- 当前目标 / Current goal:
- 已有基础 / Existing knowledge:

## 内容支柱 / Content pillars

### <支柱名称 / Pillar name>

- 包含什么 / Includes:
- 不包含什么 / Excludes:

## 发现方向 / Discovery directions

- <方向名称 / Direction name>: <长期研究范围 / Durable research scope>

## 全局禁区 / Global no-go areas

- 永远不做的主题 / Never-cover topics:
- 不做的内容方式 / Excluded formats:
- 不碰的风险类别 / Excluded risk categories:
- 不做的蹭热点内容 / Irrelevant trend-chasing:
```

### 赛道定义 / Vertical definition

项目只有一个垂直赛道。赛道必须足够具体，能帮助 Agent 判断候选热点是否相关；不能使用“科技”“AI”“商业”这类过宽标签。

A workspace has one vertical. It must be specific enough for an agent to judge whether a trend is relevant; labels as broad as “technology,” “AI,” or “business” are not enough.

### 主读者 / Primary reader

只定义一个主读者画像，并且只记录三项：身份与场景、当前目标和已有基础。不要收集年龄、收入、地域等与内容判断无关的细碎人设。可以存在次要读者，但每篇内容始终优先服务主读者。

Define one primary-reader profile with three items only: identity and context, current goal, and existing knowledge. Do not collect incidental demographics such as age, income, or location. Secondary readers may exist, but every item prioritizes the primary reader.

### 内容支柱 / Content pillars

维护 3–5 个长期内容支柱。每个支柱只记录“名称、包含什么、不包含什么”，不预建选题库或 SEO 关键词库。每个热点候选都必须归入一个支柱；无法归类或落入“不包含什么”的内容不得进入工单。

Maintain three to five durable content pillars. Each records only a name, inclusions, and exclusions; do not prebuild an idea bank or SEO keyword bank. Every trend candidate must belong to a pillar; a candidate that cannot be classified or falls into an exclusion cannot enter a ticket.

### 发现方向 / Discovery directions

维护 3–5 条发现方向，每条对应一个内容支柱。它们是可长期复用的研究范围，例如“AI 编程 Agent 的能力变化、采用信号与开发者工作流”，而不是预设热点、每日选题或 SEO 关键词库。创建工单时，Agent 从一个方向生成当期简洁查询并保存为工单 `topic`；发现命令只使用这个已保存的查询。

Maintain three to five discovery directions, each linked to a content pillar. They are durable research scopes, such as “capability changes, adoption signals, and developer workflows for AI coding agents,” rather than preset trends, daily topics, or an SEO keyword bank. When creating a ticket, the Agent forms a concise current query from one direction and saves it as the ticket `topic`; the discovery command uses only that saved query.

### 全局禁区 / Global no-go areas

全局禁区是跨支柱的硬边界，例如无关蹭热点、未经证实的传闻、攻击个人或用户明确排除的高风险话题。命中任一禁区时，Agent 直接停止该候选，不进入写作、审核或发布。

Global no-go areas are hard cross-pillar boundaries, such as irrelevant trend-chasing, unverified rumors, personal attacks, or explicitly excluded high-risk topics. If a candidate hits any one of them, stop it before writing, review, or publication.

### 不放入 `PROJECT.md` 的内容 / What does not belong in `PROJECT.md`

- 平台、凭据和 API 参数：放入 `config.toml`。/ Platforms, credentials, and API settings: put them in `config.toml`.
- 语言、语气和句式：放入 `VOICE.md`。/ Language, tone, and sentence patterns: put them in `VOICE.md`.
- 关键事实的一手来源要求：插件的全局安全规则；项目只能加严，不能放宽。/ Primary-source requirements for key facts: global plugin safety rules; a project may strengthen but never weaken them.
- `SOURCES.md`：第一版不创建。/ `SOURCES.md`: do not create it in v1.

## `VOICE.md` 规范 / `VOICE.md` specification

`VOICE.md` 回答“同一个项目应该怎样说话”。它不定义赛道，不替代事实核验，也不保存用户提供的原始样本。

`VOICE.md` answers “how this project should speak.” It does not define the vertical, replace fact verification, or store raw samples supplied by the user.

```md
# 表达规范 / Voice Guide

## 使用语言 / Language

- 主要语言 / Primary language:
- 英文术语策略 / English-term policy:

## 读者距离与整体语气 / Reader distance and overall tone

- 与读者的关系 / Relationship to the reader:
- 希望呈现的语气 / Desired tone:
- 不应呈现的感觉 / Tone to avoid:

## 句式与节奏 / Sentences and rhythm

- 句子长度偏好 / Sentence-length preference:
- 开头偏好 / Opening preference:
- 常用展开结构 / Common structure:
- 第一人称和第二人称规则 / First- and second-person rules:
- 段落节奏 / Paragraph rhythm:

## 格式与符号 / Formatting and punctuation

- 列表、编号和标题 / Lists, numbering, and headings:
- Emoji、括号、破折号、引号和感叹号 / Emoji, brackets, dashes, quotes, and exclamation marks:
- 链接、引用和 CTA / Links, citations, and CTAs:

## 偏好表达 / Preferred expressions

- 常用开场、转折和结论方式 / Preferred openings, transitions, and conclusions:
- 希望多用的词语或表达特征 / Desired words or expression traits:

## 禁用表达 / Prohibited expressions

- 禁用话术、词汇、句式和格式 / Prohibited phrasing, words, patterns, and formats:

## 已确认的风格规律 / Confirmed style rules

- 可执行的抽象规则 / Actionable abstract rules:
```

用户可以提供历史帖子或其他文本作为风格样本，但这不是强制项。Agent 只从样本中抽象可执行规律，例如“先给结论再解释”“每段最多两句”“避免感叹号”；不把样本文字、事实或立场复制进 `VOICE.md`。 “专业”“有趣”“有温度”等抽象标签不能作为最终结论；Agent 必须继续追问，直到形成可在草稿中检查的具体规则。

Users may provide past posts or other text as optional voice samples. The agent extracts only actionable rules, such as “state the conclusion before explanation,” “at most two sentences per paragraph,” or “avoid exclamation marks”; it never copies sample wording, facts, or positions into `VOICE.md`. Abstract labels like “professional,” “fun,” or “warm” are not final answers; continue asking until the result is a rule that can be checked against a draft.

## 内容工单流程 / Content-ticket flow

一张内容工单只产出一个最终内容单元：一条不超过 280 字符的 X 帖子。`discovery/` 可以保存多个候选热点，但 `selection.md` 只能选择一个方向。工单必须在热点发现之前创建，让候选、筛选、证据、写作、审核和发布结果从一开始就保存在同一个 `C-...` 目录内。

One ticket produces one final content unit: one X post of at most 280 characters. `discovery/` may retain multiple candidates, but `selection.md` selects one direction. Create the ticket before discovery so candidates, selection, evidence, writing, review, and publishing results live in the same `C-...` directory from the start.

工单状态：`draft → pending → done` 或 `draft → discarded`。`draft` 用于发现、核验、写作和编辑；`pending` 表示最终稿和标准检查已完成，等待用户审核或已获批准并排程；`done` 表示发布成功，回执在 `publish/receipt.json`；`discarded` 表示重复、过时或不符合标准，理由保存在 `discovery/duplicate-check.md`。失败时保留 `pending` 状态与失败回执，不自动重试；仅在人工确认未发出帖子后，可显式重新启用。

Ticket states are `draft → pending → done` or `draft → discarded`. `draft` covers discovery, verification, writing, and editing; `pending` means the final copy and standards check are complete and it awaits review or is approved and scheduled; `done` means publishing succeeded and the receipt is in `publish/receipt.json`; `discarded` means duplicate, stale, or out of scope, with the reason in `discovery/duplicate-check.md`. On failure, retain `pending` and a failure receipt; never retry automatically; explicitly re-enable it only after a human confirms that no post was created.

### 两个标准检查点 / Two standards checkpoints

`codoop-content-ticket` 只在两个节点检查根目录的 `PROJECT.md` 与 `VOICE.md`：热点筛选完成后检查候选是否符合主读者和内容支柱且未命中全局禁区；最终稿进入人工审核前再次检查赛道边界、事实证据与表达规则。两次检查都通过，工单才可进入 `pending`。这不替代用户最终批准；发布仍需用户明确批准以及 `--live`。

`codoop-content-ticket` checks root `PROJECT.md` and `VOICE.md` at two points only: after trend selection, verify that the candidate fits the primary reader and a content pillar without hitting a global no-go; before human review, check the vertical boundary, factual evidence, and voice rules again. A ticket enters `pending` only after both pass. This never replaces final user approval; publishing still needs explicit approval and `--live`.

## 全局安全规则 / Global safety rules

- 热点发现只用于发现讨论，不可作为事实来源。/ Trend discovery finds discussion only and is not factual evidence.
- 关键事实必须尽量追溯官方公告、原始报道、论文或当事人原帖。/ Trace key facts to official announcements, original reporting, papers, or the subject's own post whenever possible.
- 每条关键主张保留 URL、来源类型、发布日期和原文摘录。/ Retain a URL, source type, publication date, and original excerpt for every key claim.
- 证据不足、来源冲突或无法确认的主张不得进入最终稿。/ Claims with insufficient, conflicting, or unconfirmable evidence cannot enter final copy.
- 明确区分可验证事实、他人观点与作者分析。/ Clearly distinguish verifiable facts, others' views, and author analysis.
- 第一版只使用 X 官方 API 发布；禁止浏览器自动化和自动互动。/ V1 publishes through the official X API only; browser automation and automated engagement are prohibited.

## 实现边界 / Implementation boundary

本方案不引入数据库、后台服务、访谈草案文件、项目级来源白名单、选题库或 SEO 关键词库。先用 Markdown 文件、现有文件工单和内置 Skill 完成闭环；复杂能力在出现真实需求后再增加。

This plan adds no database, background service, interview-draft file, project source whitelist, idea bank, or SEO keyword bank. Complete the loop with Markdown, file-based tickets, and bundled Skills first; add complexity only after a real need appears.

## 参考方法 / Reference approaches

- Content Marketing Institute：内容使命声明的核心受众、内容范围与受众收益框架。/ Content mission statements: core audience, content scope, and audience benefit.
- Google Technical Writing：明确受众、范围与非范围的写作方法。/ Clear audience, scope, and non-scope writing methods.
- `marketingskills`：以 3–5 个内容支柱约束长期选题的方式。/ Using three to five content pillars to constrain long-term topics.
- Codoop/codoop-flow：将独立 Skill 打包在一个插件中发布的目录组织方式；其 `grilling` Skill 采用逐题访谈与推荐答案的流程。/ Packaging standalone Skills into one plugin, with `grilling`'s one-question interview and recommendation pattern.
