# codoop-autopost 工作流决策

[English](./workflow-decisions.md) · **简体中文**

状态：已在 `0.0.1-alpha.3` 实现。

## 目标

插件把内容运营拆成两个独立 Skill：

1. `codoop-content-discovery`：发现讨论、审核读者价值、保存未核验线索。
2. `codoop-content-ticket`：领取一条线索，完成去重、来源核验、二审、写作、人工批准和 X 发布。

核心目标是让内容给目标读者一个真实的评论或转发理由，而不是单纯最大化热度。实用价值、身份共鸣和真实讨论可以通过；标题党、误导和空洞站队不能通过。

## 组件边界

| 阶段 | 组件 | 责任 |
|---|---|---|
| 初始化 | `codoop-autopost-init` | 用 `grilling` 确认根目录 `PROJECT.md` 和 `VOICE.md`。 |
| 发现 | `codoop-content-discovery` + 内置 `last30days` | 每次运行一个项目方向，保存原始发现数据。 |
| 第一次价值审核 | 固定的 `marketing-twitter-engager.md` + fresh subagent | 不访问链接，判断是否值得消耗核验成本。 |
| 线索池 | 共享 Python CLI | 校验 ID、规范化 URL、写文件并原子移动目录。 |
| 内容工单 | `codoop-content-ticket` | 领取或恢复一条线索，不接受任意 topic。 |
| 来源核验 | 小型 Firecrawl API 客户端 | 只抓取工单绑定的一手来源，不捆绑 Firecrawl AGPL 源码。 |
| 第二次价值审核 | 同一固定角色 + 新的 fresh subagent | 根据已核验证据判断是否值得写。 |
| 发布 | X 官方 API 客户端 | 只发布明确批准并排程的内容，不自动互动。 |

智能角色负责写固定格式 Markdown；确定性 CLI 只负责状态。CLI 不解析自由格式审核文本，也不要求角色再复制一份 JSON。

## 上游角色

`skills/_shared/agents/marketing-twitter-engager.md` 是 `msitarzewski/agency-agents` Marketing Division 角色的固定、未经修改副本：

- 仓库：`https://github.com/msitarzewski/agency-agents`
- Commit：`8ef49232e02431f7ca4792b487e5a85a7939ff3a`
- 许可证：MIT，AgentLand Contributors

两个审核阶段读取同一份角色文件，但每次都启动一个新的单一 subagent，并追加当前项目背景、输入、本轮目的和限制。

插件不会创建评审委员会，不会修改角色，也不会自动从上游同步角色。

## 第一次价值审核

审核所有未被完全相同 URL 过滤掉的候选。每个候选都要先构建最强的真实、非标题党角度，再给出：

- `go`：有清晰读者价值，并且存在值得核验的点击回报假设。
- `weak`：可能可靠，但价值、具体性、时效性或点击回报不足。
- `reject`：超出项目范围、属于二手搬运或炒作，或者短帖已经可以替代全部价值。

正常 `go` 使用 `pass_basis = audience-value`。

只有所提供的 `last30days` 排名、互动或速度本身显示异常爆发时，才允许使用 `breakout-trend`。它只用于获得来源核验机会，不能绕过 `PROJECT.md`、第二次审核、人工批准或发布门禁。

发现数据不是事实证据。点击回报必须保留为假设，例如：“只有原文提供具体测试条件和失败案例时才继续。”

## 本地队列

```text
content-leads/
  available/
  claimed/
  consumed/
  rejected/
  runs/
```

- `runs/R-...` 永久保存 `run.toml`、`raw.json` 和完整 `value-review.md`。
- 只有 `go` 进入 `available`；发现阶段的 `weak` 和 `reject` 只保留在 run 中。
- 完全相同的规范化 URL 不重新审核，只更新已有线索。
- 不同 URL 的同一事件由审核角色拒绝；实质新进展可以成为新的关联线索。
- `available → claimed` 使用同一文件系统中的原子目录移动。
- 发布成功：`claimed → consumed`。
- 重复或核验后价值不足：`claimed → rejected`。
- 技术失败：保留 claimed 线索和原工单，供下次恢复。

所有记录永久保留，不使用 SQLite、消息队列、常驻服务、隐藏状态或 Git 状态机。

## 自动选择和人工提升

生产流程会先恢复中断的 claimed 工作。没有中断工作时，优先选择最新发现运行，再按该运行中的审核排名选择。

Skill 会结合日期、事件类型和项目背景跳过明显过时的线索。没有合适线索时停止，不自动启动发现。

人工可以运行：

```bash
run.sh promote RUN_ID CANDIDATE_ID --reason "原因"
```

原始运行报告保持不变，线索记录 `pass_basis = human-override`，并且仍需通过全部生产门禁。

## 不可绕过的安全门

```text
第一次价值审核 go 或人工提升
  → 原子领取
  → 重复检查 clear
  → Firecrawl 来源快照
  → verified evidence
  → fresh 核验后二审 go
  → 写作
  → 提交
  → 明确人工批准
  → 排程
  → 明确执行 publish-due --live
```

- 工单只能来自 claimed 线索，来源 URL 只能来自该线索。
- 重复检查 clear 前，Firecrawl 拒绝运行。
- 发现输出不能增加 `verified_evidence_count`。
- 二审 `weak` 或 `reject` 会丢弃工单并移动线索；写作和提交都会被阻止。
- 发布使用排它锁；成功后保存 X 帖子 ID、URL 和时间，再消费线索。
- 失败时保留 pending 工单、错误回执和 claimed 线索，不自动重试。
- 只使用 X 官方 API；禁止浏览器自动化、自动批准、点赞、关注、回复和私信。

## 表现反馈

`record-performance` 只允许对已发布工单手工记录曝光、评论和转发，并计算：

```text
(comments + shares) / impressions × 1000
```

后续发现审核会在文件存在时读取，缺失时跳过。工作流不会自动调用分析 API。

## 第一版边界

- 一条不超过 280 字符的 X 帖子。
- 一条线索只消费一次。
- 多平台生产留到后续修改 `codoop-content-ticket`。
- subagent 工具限制通过任务提示执行，不增加额外工具沙箱。
- 不设置固定的全局过期天数。

## 许可证边界

- `grilling`、`last30days`、`agency-agents` 和 X 发布路径的上游内容采用 MIT 许可证，并保留归属和许可证。
- Firecrawl 只通过 API 或兼容端点使用；插件不分发其 AGPL 服务源码。

上游项目：

- https://github.com/msitarzewski/agency-agents
- https://github.com/mvanhorn/last30days-skill
- https://github.com/alberduris/skills/tree/main/plugins/x-twitter
- https://github.com/coreyhaines31/marketingskills
- https://github.com/firecrawl/firecrawl

返回[项目中文 README](../README.zh-CN.md)。
