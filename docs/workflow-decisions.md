# codoop-autopost 工作流决策

状态：已确认架构方向，待实现。

## 目标

发布一个可组合的 `codoop-autopost` Skill Pack。用户既可安装整包执行“热点发现 → 一手来源核验 → 草稿 → 人工批准 → X 定时发布”，也可单独安装和使用 `last30days`、`firecrawl`、`social-content`、`copy-editing` 或 `x-twitter`。

用户仍需自行提供运行环境和账户凭据：Python、Firecrawl 服务凭据（或自托管地址）、X Developer OAuth 凭据，以及其所用 Agent/模型的凭据。

## 组件边界

| 阶段 | codoop-autopost 内部组件 | 上游复用策略 |
| --- | --- | --- |
| 热点发现 | `discover` | 首次发现时自动拉取并固定 `last30days` 的 MIT 运行时到用户数据目录 `~/.local/share/codoop-autopost/last30days`；不要求用户额外安装或初始化该 Skill。 |
| 一手来源核验 | `verify` | 用一个小型 Firecrawl HTTP 客户端调用用户配置的 API 或兼容自托管端点；不复制或捆绑 Firecrawl 的 AGPL 源码。 |
| 写作与润色 | `draft`、`edit` | 将适合本项目的写作、语气和事实保护规则写进本 Skill；不在运行时调用外部 `social-content`、`copy-editing` Skill。 |
| X 发布 | `publish` | 只保留 X 官方 API 的 OAuth 发帖能力。可审计地复用/改写 `x-twitter` 的 MIT 发布路径，但不暴露搜索、互动、关注、回复或浏览器自动化能力。 |

主 Skill 只编排公开的子 Skill；它们也各自是完整的公开入口。`last30days` 的上游运行时仍初始化到用户数据目录，避免将供应商代码写入插件缓存。

## 不可绕过的安全门

状态只能单向流转：

`discovered → verified → drafted → approved → scheduled → publishing → published | failed`

- 仅 `verified` 的证据包可进入写作。
- 每条关键主张都保存事实、URL、来源类型、发布日期和原文摘录；无法确认或来源冲突的主张不得进入草稿。
- 草稿显式标记“可验证事实 / 他人观点 / 作者分析”。
- 仅用户明确批准的 `approved` 内容可被调度；调度器只读取 `approved` 或 `scheduled` 内容。
- 发布前写入幂等键和内容哈希；成功后保存 X 帖子 ID、URL、发布时间；失败保留正文、状态和错误原因，绝不静默重试或重复发布。
- 第一版只支持 X，且只用官方 API；禁止浏览器自动化、自动互动和自动批准。

## 最小可移植实现

- 六个公开 Skill 入口位于 `skills/`，并由根目录的 Codex、Claude 和 Agent Skills 插件清单分别发布。
- 一个本地 SQLite 文件保存证据、草稿、批准和发布记录；热点候选由 `last30days` 输出供人工筛选。
- 一个 CLI/Skill 命令用于列出待审核稿、显式批准、安排发布时间以及执行 `publish-due`。
- 默认 dry-run；真实发布须同时满足已批准状态和显式 `--live` 开关。
- 用户凭据放在 `~/.config/codoop-autopost/config.toml`；环境变量可覆盖，真实凭据绝不写入仓库或 SQLite。
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
