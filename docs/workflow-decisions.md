# codoop-autopost 工作流决策 / Workflow decisions

状态：第一版已实现。
Status: implemented for v1.

## 目标 / Goal

发布一个可组合的 `codoop-autopost` Skill Pack。普通用户只安装一个 `codoop-autopost` 插件，即可先定义项目赛道与语气，再执行“热点发现 → 一手来源核验 → 草稿 → 人工批准 → X 定时发布”；主插件同时提供 `codoop-autopost-init`、`codoop-content-ticket`、`grilling`、`last30days`、`firecrawl`、`social-content`、`copy-editing` 和 `x-twitter` 能力，并保留它们的独立入口。

Publish a composable `codoop-autopost` Skill Pack. Regular users install one `codoop-autopost` plugin to define a project's vertical and voice, then run “trend discovery → primary-source verification → draft → human approval → scheduled X publishing.” The main plugin also includes `codoop-autopost-init`, `codoop-content-ticket`, `grilling`, `last30days`, `firecrawl`, `social-content`, `copy-editing`, and `x-twitter`, while retaining standalone entry points.

用户仍需自行提供运行环境和账户凭据：Python 3.12+、Firecrawl 服务凭据（或自托管地址）、X Developer OAuth 凭据，以及其所用 Agent/模型的凭据。

Users still provide their own runtime and account credentials: Python 3.12+, Firecrawl service credentials (or self-hosted endpoint), X Developer OAuth credentials, and credentials for their chosen agent or model.

## 组件边界 / Component boundaries

| 阶段 / Stage | codoop-autopost 内部组件 / Internal component | 上游复用策略 / Upstream reuse strategy |
| --- | --- | --- |
| 项目初始化 / Project initialization | `codoop-autopost-init` | 使用内置、原名的 `grilling` 与用户逐题确认 `PROJECT.md` 和 `VOICE.md`。/ Use bundled, original-name `grilling` to confirm `PROJECT.md` and `VOICE.md` one question at a time. |
| 内容工单 / Content ticket | `codoop-content-ticket` | 先创建一张 `C-...` 工单，再在其中完成发现、核验、写作、审核与发布。/ Create one `C-...` ticket first, then complete discovery, verification, writing, review, and publishing inside it. |
| 热点发现 / Trend discovery | `discover` | 内置并固定 MIT `last30days v3.18.3` 运行时，不额外下载 Skill；`CODOOP_LAST30DAYS_DIR` 可覆盖它。/ Bundle and pin the MIT `last30days v3.18.3` runtime with no extra Skill download; `CODOOP_LAST30DAYS_DIR` can override it. |
| 一手来源核验 / Primary-source verification | `verify` | 用小型 Firecrawl HTTP 客户端调用用户配置的 API 或兼容自托管端点；不复制或捆绑 Firecrawl 的 AGPL 源码。/ Call the configured API or compatible self-hosted endpoint through a small Firecrawl HTTP client; do not copy or bundle Firecrawl's AGPL source. |
| 写作与润色 / Writing and editing | `draft`, `edit` | 将本项目的写作、语气和事实保护规则写进本 Skill；运行时不调用外部 `social-content`、`copy-editing` Skill。/ Put project writing, voice, and fact-protection rules in this Skill; do not call external `social-content` or `copy-editing` Skills at runtime. |
| X 发布 / X publishing | `publish` | 只保留 X 官方 API 的 OAuth 发帖能力。可审计地复用/改写 `x-twitter` 的 MIT 发布路径，但不暴露搜索、互动、关注、回复或浏览器自动化能力。/ Keep only official-X-API OAuth posting. Reuse or rewrite the MIT `x-twitter` publishing path audibly, without search, engagement, follows, replies, or browser automation. |

主插件提供完整工作流；各子 Skill 也各自提供独立入口。`last30days` 运行时代码随插件发布，避免首次运行时依赖 Git 下载。

The main plugin provides the complete workflow, and each child Skill has a standalone entry point. The `last30days` runtime ships with the plugin, avoiding a Git download on first use.

## 不可绕过的安全门 / Non-bypassable safety gates

工单状态只单向流转：`draft → pending → done` 或 `draft → discarded`。
Ticket state flows in one direction only: `draft → pending → done` or `draft → discarded`.

- 仅 `verified` 的证据包可进入写作。/ Only `verified` evidence packs may enter writing.
- 每条关键主张都保存事实、URL、来源类型、发布日期和原文摘录；无法确认或来源冲突的主张不得进入草稿。/ Store fact, URL, source type, publication date, and original excerpt for every key claim; unconfirmed or conflicting claims cannot enter a draft.
- 草稿显式标记“可验证事实 / 他人观点 / 作者分析”。/ Drafts explicitly mark “verifiable fact / attributed outside view / author analysis.”
- 仅用户明确批准、已排程的 `pending` 工单可被调度器读取。/ The scheduler may read only explicitly user-approved and scheduled `pending` tickets.
- 发布前在工单目录创建排它锁；成功后保存 X 帖子 ID、URL、发布时间并置为 `done`；失败保留 `pending` 状态和错误原因，绝不自动重试。只有人工确认未发帖后，才可显式重新启用。/ Create an exclusive ticket lock before publishing; on success store X post ID, URL, and timestamp and set `done`; on failure retain `pending` and the error, with no automatic retry. Re-enable it only after a human confirms that no post was created.
- 第一版只支持 X，且只用官方 API；禁止浏览器自动化、自动互动和自动批准。/ V1 supports X only through its official API; browser automation, automated engagement, and automated approval are prohibited.
- 内容工单必须读取根目录已确认的 `PROJECT.md` 与 `VOICE.md`；缺少任一文件时拒绝操作。/ Content tickets must read confirmed root `PROJECT.md` and `VOICE.md`; refuse the action if either is missing.
- `PROJECT.md` 维护与内容支柱对应的 3–5 条发现方向；每张工单将其中一条转为保存的当期查询，发现结果写入该工单的 `discovery/raw.json`。/ `PROJECT.md` maintains three to five discovery directions linked to content pillars; each ticket turns one into a saved current query, and discovery output is written to that ticket's `discovery/raw.json`.
- 在调用 Firecrawl 前，用候选 URL 与过去 14 天 `pending`、`done` 工单的证据 URL 比较；相同规范化 URL 的工单置为 `discarded`，并在 `discovery/duplicate-check.md` 保留理由。/ Before calling Firecrawl, compare the candidate URL with evidence URLs from `pending` and `done` tickets from the previous 14 days; a matching canonical URL makes the ticket `discarded` and records the reason in `discovery/duplicate-check.md`.

## 最小可移植实现 / Minimum portable implementation

- 八个公开 Skill 入口位于 `skills/`，并由根目录的 Codex、Claude 和 Agent Skills 插件清单分别发布。/ Eight public Skill entry points live in `skills/` and are published through root plugin manifests for Codex, Claude, and Agent Skills.
- 运营项目根目录保存唯一的 `PROJECT.md` 与 `VOICE.md` 标准。每次内容操作完整保存在 `content-tickets/C-<ticket-id>/`，其中按 `discovery/`、`verification/`、`writing/`、`review/` 和 `publish/` 保存可审核产物；`ticket.toml` 维护 `draft`、`pending`、`done`、`discarded` 状态。没有 SQLite、隐藏运行时状态或标准副本。/ The workspace root contains the sole `PROJECT.md` and `VOICE.md` standards. Each operation is fully stored in `content-tickets/C-<ticket-id>/`, with reviewable artifacts in `discovery/`, `verification/`, `writing/`, `review/`, and `publish/`; `ticket.toml` maintains `draft`, `pending`, `done`, and `discarded` states. There is no SQLite, hidden runtime state, or standards copy.
- 一个 CLI/Skill 命令用于列出待审核稿、显式批准、安排发布时间以及执行 `publish-due`。/ One CLI/Skill command lists drafts awaiting review, explicitly approves, schedules, and runs `publish-due`.
- 默认 dry-run；真实发布须同时满足已批准状态和显式 `--live` 开关。/ Default to dry run; live publishing requires both approved status and explicit `--live`.
- 用户凭据放在每个运营项目根目录的 `config.toml`；环境变量可覆盖，真实凭据绝不写入工单。/ Store user credentials in each workspace root's `config.toml`; environment variables can override them, and secrets never enter a ticket.
- 定时器由用户机器的 cron/launchd 或部署环境触发 `publish-due`；Skill 不自行常驻或自行发布。/ A user-machine cron/launchd job or deployment environment triggers `publish-due`; the Skill does not run as a daemon or publish itself.

## 许可证与归属 / License and attribution

- `last30days-skill`：MIT。若打包其源码或实质性文档，保留原版权和 MIT 许可证。/ MIT. Retain original copyright and MIT license if bundling source or substantial documentation.
- `x-twitter`：MIT。若复用其代码或文档，保留原版权和 MIT 许可证；只纳入经审计的官方 API 发帖路径。/ MIT. Retain original copyright and MIT license when reusing code or documentation; include only an audited official-API publishing path.
- `social-content`、`copy-editing`：MIT。第一版优先写出本项目自己的规则；若复制实质内容，则附带版权和许可证。/ MIT. V1 prefers project-native rules; include copyright and license if copying substantial content.
- Firecrawl：AGPL-3.0。第一版仅调用其 API/兼容端点，不将其源码作为本项目的一部分；若未来自托管、修改或分发其服务，需单独完成 AGPL 合规审查。/ AGPL-3.0. V1 calls only its API or compatible endpoint and does not make its source part of this project; future self-hosting, modification, or distribution requires separate AGPL compliance review.

上游 / Upstream:

- https://github.com/mvanhorn/last30days-skill
- https://github.com/alberduris/skills/tree/main/plugins/x-twitter
- https://github.com/coreyhaines31/marketingskills
- https://github.com/firecrawl/firecrawl

## 尚待决定 / Open decisions

1. 人工审核采用纯 CLI/Markdown 队列，还是极简本地网页队列。/ Use a CLI/Markdown review queue or a minimal local web queue.
2. 首个运行目标是用户本机定时器，还是常驻服务器部署。/ Target a user-machine scheduler first or a persistent server deployment.
3. 需要支持的内容语言、目标受众和个人语气素材如何提供给 Skill。/ Decide how supported content languages, audiences, and personal voice material reach the Skill.
