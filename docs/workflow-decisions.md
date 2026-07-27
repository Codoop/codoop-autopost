# codoop-autopost 工作流决策

状态：第一版已实现。

## 目标

发布一个可组合的 `codoop-autopost` Skill Pack。普通用户只安装一个 `codoop-autopost` 插件，即可先定义项目赛道与语气，再执行“热点发现 → 一手来源核验 → 草稿 → 人工批准 → X 定时发布”；主插件同时提供 `codoop-autopost-init`、`codoop-content-ticket`、`grilling`、`last30days`、`firecrawl`、`social-content`、`copy-editing` 和 `x-twitter` 能力，并保留它们的独立入口。

用户仍需自行提供运行环境和账户凭据：Python、Firecrawl 服务凭据（或自托管地址）、X Developer OAuth 凭据，以及其所用 Agent/模型的凭据。

## 组件边界

| 阶段 | codoop-autopost 内部组件 | 上游复用策略 |
| --- | --- | --- |
| 项目初始化 | `codoop-autopost-init` | 使用内置、原名的 `grilling` 与用户逐题确认 `PROJECT.md` 和 `VOICE.md`。 |
| 内容工单 | `codoop-content-ticket` | 先创建一张 `C-...` 工单，再在其中完成发现、核验、写作、审核与发布。 |
| 热点发现 | `discover` | 用户直接发起发现时，主插件自动拉取并固定 `last30days` 的 MIT 运行时到用户数据目录 `~/.local/share/codoop-autopost/last30days`。 |
| 一手来源核验 | `verify` | 用一个小型 Firecrawl HTTP 客户端调用用户配置的 API 或兼容自托管端点；不复制或捆绑 Firecrawl 的 AGPL 源码。 |
| 写作与润色 | `draft`、`edit` | 将适合本项目的写作、语气和事实保护规则写进本 Skill；不在运行时调用外部 `social-content`、`copy-editing` Skill。 |
| X 发布 | `publish` | 只保留 X 官方 API 的 OAuth 发帖能力。可审计地复用/改写 `x-twitter` 的 MIT 发布路径，但不暴露搜索、互动、关注、回复或浏览器自动化能力。 |

主插件提供完整工作流；各子 Skill 也各自提供独立入口。`last30days` 的上游运行时仍初始化到用户数据目录，避免将供应商代码写入插件缓存。

## 不可绕过的安全门

工单状态只单向流转：

`draft → pending → done`

- 仅 `verified` 的证据包可进入写作。
- 每条关键主张都保存事实、URL、来源类型、发布日期和原文摘录；无法确认或来源冲突的主张不得进入草稿。
- 草稿显式标记“可验证事实 / 他人观点 / 作者分析”。
- 仅用户明确批准、已排程的 `pending` 工单可被调度器读取。
- 发布前在工单目录创建排它锁；成功后保存 X 帖子 ID、URL、发布时间并置为 `done`；失败保留 `pending` 状态和错误原因，绝不静默重试或重复发布。
- 第一版只支持 X，且只用官方 API；禁止浏览器自动化、自动互动和自动批准。
- 内容工单必须读取根目录已确认的 `PROJECT.md` 与 `VOICE.md`；缺少任一文件时拒绝操作。

## 最小可移植实现

- 六个公开 Skill 入口位于 `skills/`，并由根目录的 Codex、Claude 和 Agent Skills 插件清单分别发布。
- 运营项目根目录保存唯一的 `PROJECT.md` 与 `VOICE.md` 标准。每次内容操作完整保存在 `content-tickets/C-<ticket-id>/`，其中按 `discovery/`、`verification/`、`writing/`、`review/` 和 `publish/` 保存可审核产物；`ticket.toml` 维护 `draft`、`pending`、`done` 状态。没有 SQLite、隐藏运行时状态或标准副本。
- 一个 CLI/Skill 命令用于列出待审核稿、显式批准、安排发布时间以及执行 `publish-due`。
- 默认 dry-run；真实发布须同时满足已批准状态和显式 `--live` 开关。
- 用户凭据放在每个运营项目根目录的 `config.toml`；环境变量可覆盖，真实凭据绝不写入工单。
- 定时器由用户机器的 cron/launchd 或部署环境触发 `publish-due`；Skill 不自行常驻或自行发布。

## 许可证与归属

- `last30days-skill`：MIT。若打包其源码或实质性文档，保留原版权和 MIT 许可证。
- `x-twitter`：MIT。若复用其代码或文档，保留原版权和 MIT 许可证；只纳入经审计的官方 API 发帖路径。
- `social-content`、`copy-editing`：MIT。第一版优先写出本项目自己的规则；若复制实质内容，则附带版权和许可证。
- Firecrawl：AGPL-3.0。第一版仅调用其 API/兼容端点，不将其源码作为本项目的一部分；若未来自托管、修改或分发其服务，需单独完成 AGPL 合规审查。

上游：

- https://github.com/mvanhorn/last30days-skill
- https://github.com/alberduris/skills/tree/main/plugins/x-twitter
- https://github.com/coreyhaines31/marketingskills
- https://github.com/firecrawl/firecrawl

## 尚待决定

1. 人工审核采用纯 CLI/Markdown 队列，还是极简本地网页队列。
2. 首个运行目标是用户本机定时器，还是常驻服务器部署。
3. 需要支持的内容语言、目标受众和个人语气素材如何提供给 Skill。
