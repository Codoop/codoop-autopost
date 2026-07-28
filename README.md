# codoop-autopost

一个插件先定义运营项目的赛道和语气，再完成热点发现、一手来源核验、内容草稿、人工审核和 X 定时发布。

One plugin defines a content project's vertical and voice, then runs trend discovery, primary-source verification, drafting, human review, and scheduled X publishing.

它只发布人工明确批准的单条 X 帖子。不会使用浏览器自动化，不会自动回复、点赞、关注或私信。

It publishes only explicitly human-approved X posts. It never uses browser automation or performs automated replies, likes, follows, or direct messages.

## 安装 / Installation

### Codex（Desktop 或 CLI）/ Codex (Desktop or CLI)

从 GitHub 插件市场安装一个 `codoop-autopost` 插件，即可获得项目初始化、内容工单、热点发现、来源核验、写作、润色和 X 发布所需能力。`codoop-autopost-init`、`codoop-content-ticket`、`grilling`、`last30days`、`firecrawl`、`social-content`、`copy-editing` 和 `x-twitter` 都随主插件提供。

Install one `codoop-autopost` plugin from the GitHub marketplace to get project initialization, content tickets, trend discovery, source verification, writing, editing, and X publishing. `codoop-autopost-init`, `codoop-content-ticket`, `grilling`, `last30days`, `firecrawl`, `social-content`, `copy-editing`, and `x-twitter` are bundled with the main plugin.

```bash
codex plugin marketplace add Codoop/codoop-autopost
codex plugin add codoop-autopost@codoop-autopost
```

安装后请完全重启 Codex。也可以直接对 Codex 说：

Fully restart Codex after installation. You can also tell Codex:

```text
Install the codoop-autopost Codex plugin from Codoop/codoop-autopost.
```

### Claude Code

```bash
/plugin marketplace add Codoop/codoop-autopost
/plugin install codoop-autopost@codoop-autopost
```

同一 Skill Pack 也提供独立入口，方便高级用户按需使用；`grilling` 保留原名并附带 MIT 归属。仓库的插件组织方式与 [codoop-flow](https://github.com/Codoop/codoop-flow) 一致。

The same Skill Pack also exposes standalone entries for advanced users. `grilling` keeps its original name and MIT attribution. The plugin structure follows [codoop-flow](https://github.com/Codoop/codoop-flow).

### 本地开发备用方式 / Local-development fallback

只有开发或离线调试插件时，才克隆仓库并运行 `./scripts/install-skill.sh`。

Clone the repository and run `./scripts/install-skill.sh` only for development or offline plugin debugging.

## 运营项目目录 / Content-operations workspace

每个账号或品牌使用一个运营项目目录。用户在这个目录中运行 Skill；它保存本次运营的工单和所有可审核的阶段产物，无需 Git。

Use one content-operations workspace per account or brand. Run the Skills in this directory; it stores each ticket and every reviewable artifact, with no Git requirement.

```text
content-operations/
├── config.toml
├── PROJECT.md
├── VOICE.md
└── content-tickets/
    └── C-20260727-topic/
        ├── ticket.toml
        ├── discovery/
        │   ├── raw.json
        │   ├── candidates.md
        │   ├── selection.md
        │   └── duplicate-check.md
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

`ticket.toml` 是一张工单的状态入口：

`ticket.toml` is the status entry point for a ticket:

```toml
id = "C-20260727-topic"
status = "draft" # draft | pending | done | discarded
platform = "x"
```

- `draft`：收集热点、核验来源和写作。/ Collect trends, verify sources, and write.
- `pending`：最终稿已在 `review/final.md`，等待人工审核或定时发布；`ticket.toml` 会记录批准和排程时间。/ The final copy is in `review/final.md`, awaiting human review or scheduled publishing; `ticket.toml` records approval and schedule times.
- `done`：发布成功，发布信息保存在 `publish/receipt.json`。/ Publishing succeeded; the receipt is stored in `publish/receipt.json`.
- `discarded`：选题重复、过时或不符合项目标准，不会进入核验、写作或发布；理由保存在 `discovery/duplicate-check.md`。/ The topic is duplicate, stale, or outside the project standard; it never enters verification, writing, or publishing, and the reason is in `discovery/duplicate-check.md`.

根目录的 `PROJECT.md` 与 `VOICE.md` 是所有工单唯一的标准来源；工单不保存副本。工单目录是唯一的运营记录：不创建 `autopost.db` 或隐藏状态目录。发布时会在当前工单内短暂创建锁；进程异常中断而留下锁时，保留它供人工检查，避免意外重复发布。

Root `PROJECT.md` and `VOICE.md` are the only standards for every ticket; tickets never store copies. Ticket folders are the only operational record: there is no `autopost.db` or hidden state directory. Publishing creates a temporary lock in its ticket; retain a lock left after an interrupted process for human inspection to prevent accidental duplicate posting.

## 首次使用 / First use

先在运营项目根目录运行项目初始化。它使用内置的 `grilling` 与你逐题确认赛道、主读者、内容支柱、发现方向、禁区和表达规则，分别生成 `PROJECT.md` 与 `VOICE.md`。发现方向是长期研究范围，而非选题或关键词库；每张工单从中选择一个方向并形成当期查询。两份文件确认前，不能创建内容工单。

Run project initialization in the workspace root. It uses bundled `grilling` to confirm the vertical, primary reader, content pillars, discovery directions, exclusions, and voice one question at a time, then creates `PROJECT.md` and `VOICE.md`. Discovery directions are durable research scopes, not an idea or keyword bank; each ticket selects one and forms a current query. No content ticket can be created before both are confirmed.

```text
Use codoop-autopost-init to set up this content-operations project.
```

初始化完成时，`codoop-autopost-init` 会在项目根目录创建私有的 `config.toml` 模板；已有文件不会被改动，也不会要求你当场填写密钥。它会说明以下配置：

When initialization finishes, `codoop-autopost-init` creates a private `config.toml` template in the workspace root. It preserves an existing file and never asks you to provide secrets during setup. It explains these settings:

- `firecrawl.api_key`：用于读取一手来源并核验事实。在 [Firecrawl](https://www.firecrawl.dev/) 创建账号后，从其控制台获取；`api_url` 保持默认值，除非使用兼容的自托管端点。/ Reads primary sources and verifies facts. Create an account at [Firecrawl](https://www.firecrawl.dev/) and obtain the key from its dashboard; keep the default `api_url` unless you use a compatible self-hosted endpoint.
- `x.consumer_key`、`x.consumer_secret`：你的 X Developer App 身份。/ Identify your X Developer App.
- `x.access_token`、`x.access_secret`：授权插件代表该 X 账号发帖。在 [X Developer Console](https://developer.x.com/en/portal/dashboard) 创建或选择 App，开启带写权限的用户认证，然后生成 Keys and Tokens；更改 App 权限后重新生成用户令牌。/ Authorize the plugin to post as the X account. In the [X Developer Console](https://developer.x.com/en/portal/dashboard), create or select an App, enable user authentication with write permission, and generate Keys and Tokens; regenerate user tokens after changing App permissions.

`config.toml` 已被 Git 忽略，不能放入工单、聊天记录或截图。每次运行 Skill 或定时任务都以该运营项目为工作目录，Skill 会自动读取其中的 `config.toml`。`FIRECRAWL_API_KEY`、`FIRECRAWL_API_URL` 及 X 的四个环境变量仍可覆盖配置文件，适合 CI 或服务器。若配置文件不在默认位置，可设置 `CODOOP_AUTOPOST_CONFIG`。

`config.toml` is Git-ignored and must not appear in tickets, chats, or screenshots. Run each Skill or scheduler from the workspace so it reads this file automatically. `FIRECRAWL_API_KEY`, `FIRECRAWL_API_URL`, and the four X environment variables can override it for CI or servers. Set `CODOOP_AUTOPOST_CONFIG` if the file lives elsewhere.

项目初始化完成后，使用 `codoop-content-ticket` 创建一张 `C-...` 工单。它会先创建工单，再发现热点，因此候选、筛选、核验、稿件、审核和发布回执都保存在同一目录。热点发现使用插件内置的 `last30days v3.18.3` MIT 运行时，不会额外下载 Skill；运行仍需要 Python 3.12+ 和网络连接。内置 `run.sh` 会选择兼容的 Python，否则说明如何提供。

After initialization, use `codoop-content-ticket` to create a `C-...` ticket. It creates the ticket before discovery, so candidates, selection, verification, drafts, review, and publishing receipts all live together. Trend discovery uses the plugin's bundled MIT-licensed `last30days v3.18.3` runtime and does not download another Skill; it still needs Python 3.12+ and network access. Bundled `run.sh` launchers select a compatible Python or explain how to provide one.

## 安全边界 / Safety boundaries

- `last30days` 只发现讨论，不构成事实来源。/ `last30days` finds discussions only; it is not a factual source.
- 每条关键主张必须记录 URL、来源类型、发布日期和原文摘录，并由执行者显式标记为已核验。/ Record a URL, source type, publication date, and original excerpt for each key claim, and explicitly mark it verified.
- 热点筛选完成和最终稿进入人工审核前，都必须检查根目录 `PROJECT.md` 与 `VOICE.md`。/ Check root `PROJECT.md` and `VOICE.md` after trend selection and before a final draft enters human review.
- 选定候选 URL 必须先通过过去 14 天已发布/待发布工单的重复检查；重复内容不得调用 Firecrawl。/ A selected candidate URL must pass a duplicate check against the previous 14 days of published or pending tickets; duplicates must not call Firecrawl.
- 没有核验证据的草稿无法批准；没有显式批准的内容无法排程或发布。/ Drafts without verified evidence cannot be approved; content without explicit approval cannot be scheduled or published.
- `publish-due` 默认是 dry-run；只有 `--live` 才调用 X 官方 API。/ `publish-due` defaults to dry run; only `--live` calls the official X API.
- Firecrawl 通过 API/兼容自托管端点调用，不捆绑其 AGPL 源码。/ Firecrawl is called through its API or a compatible self-hosted endpoint; its AGPL source is not bundled.

详细架构与许可证边界见 [workflow-decisions.md](docs/workflow-decisions.md)。

See [workflow-decisions.md](docs/workflow-decisions.md) for architecture and licensing boundaries.
