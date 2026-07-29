<div align="center">

# codoop-autopost

[English](./README.md) · **简体中文**

**先找到值得讨论的内容，再完成核验与发布**

![Codex Plugin](https://img.shields.io/badge/Codex-plugin-111827)
![Claude Code Plugin](https://img.shields.io/badge/Claude%20Code-plugin-8A63D2)
![Python](https://img.shields.io/badge/python-3.12%2B-blue)
![Local files](https://img.shields.io/badge/state-local%20files-brightgreen)
![License](https://img.shields.io/badge/license-MIT-green)

</div>

**codoop-autopost** 是一个把选题发现和内容生产拆开的本地内容运营插件。

它先判断近期讨论是否能给目标读者一个真实的评论、转发或继续阅读理由。只有值得投入核验成本的未核验线索，才会进入来源核验、第二次价值审核、写作、人工批准和 X 发布。

工作流不会通过浏览器自动发布，也不会自动回复、点赞、关注或私信。所有运营状态都保存在普通本地文件中，不需要 Git 或数据库。

## 工作流

```text
codoop-autopost-init
  → codoop-content-discovery
      → last30days
      → 核验前价值审核
      → content-leads/available
  → codoop-content-ticket
      → 原子领取线索
      → 重复检查
      → Firecrawl 一手来源核验
      → 核验后价值审核
      → 写作
      → 人工批准
      → X 官方 API
```

两条主流程互相独立：

- `codoop-content-discovery` 每次轮换运行 `PROJECT.md` 中的一个发现方向，审核全部新候选，只把 `go` 保存到线索池。
- `codoop-content-ticket` 领取一条未使用线索，完成核验和 fresh 二审，再准备一条等待人工批准的 X 帖子。

`weak` 和 `reject` 会永久保留在发现运行报告里，但不会继续消耗 Firecrawl 和写作成本。

## 安装

### Codex

```bash
codex plugin marketplace add Codoop/codoop-autopost
codex plugin add codoop-autopost@codoop-autopost
```

### Claude Code

```text
/plugin marketplace add Codoop/codoop-autopost
/plugin install codoop-autopost@codoop-autopost
```

安装后重启 Agent。主插件包含：

- `codoop-autopost-init`
- `codoop-content-discovery`
- `codoop-content-ticket`
- `grilling`
- `last30days`
- `firecrawl`
- `social-content`
- `copy-editing`
- `x-twitter`

本地开发或离线调试时运行：

```bash
./scripts/install-skill.sh
```

## 内容运营项目目录

每个账号或品牌使用一个独立目录：

```text
content-operations/
├── config.toml
├── PROJECT.md
├── VOICE.md
├── content-leads/
│   ├── available/
│   │   └── L-.../lead.toml
│   ├── claimed/
│   ├── consumed/
│   ├── rejected/
│   └── runs/
│       └── R-.../
│           ├── run.toml
│           ├── raw.json
│           └── value-review.md
└── content-tickets/
    └── C-.../
        ├── ticket.toml
        ├── discovery/
        │   ├── raw.json
        │   ├── selection.md
        │   ├── value-review.md
        │   └── duplicate-check.md
        ├── verification/
        │   ├── evidence.md
        │   ├── claims.md
        │   ├── value-review.md
        │   └── source-snapshots/source.md
        ├── writing/
        ├── review/
        └── publish/
            ├── schedule.toml
            ├── receipt.json
            └── performance.toml
```

`content-leads` 是未核验内容线索队列，不是事实库。所有发现运行和线索都会永久保留。

同一个规范化 URL 再次出现时，工作流只更新 `last_seen_at` 和互动数据，不创建新线索。领取过程使用原子目录移动，因此同一条线索不会生成两张新工单。

## 快速开始

### 1. 初始化项目

```text
使用 codoop-autopost-init 初始化这个内容运营项目。
```

初始化通过一次一个问题的访谈，生成项目唯一的 `PROJECT.md` 和 `VOICE.md`。两份标准确认前，发现和生产都会拒绝运行。

它还会创建私有 `config.toml` 模板，但不会要求你在聊天中提供密钥：

- 从 [Firecrawl 控制台](https://www.firecrawl.dev/) 获取 `firecrawl.api_key`，用于读取一手来源。
- 从 [X Developer Console](https://developer.x.com/en/portal/dashboard) 获取四项 X OAuth 值；App 需要用户写权限。

环境变量可以覆盖配置文件。真实密钥不得进入聊天、项目标准、线索、工单、截图或 Git。

### 2. 填充线索池

```text
使用 codoop-content-discovery 发现并审核内容线索。
```

审核使用固定版本、未经修改的 `agency-agents` Marketing `Twitter Engager` 角色。每次运行都会启动一个 fresh subagent，只追加当前项目背景和本轮任务目的。

定时发现必须触发 Agent 执行完整 Skill，不能直接调底层 `start-discovery` 命令；后者只收集原始候选，无法启动审核 subagent。发现会自动选择方向和与上一轮不同的 query，不等待用户输入。

核验前审核者不能打开链接、调用 Firecrawl，也不能把发现摘要当作事实。

通过依据：

- `audience-value`：候选有具体读者收益，并且存在值得核验的点击回报假设。
- `breakout-trend`：`last30days` 数据本身显示异常爆发热度；它只用于获得来源核验机会。
- `human-override`：人工明确提升一个已审核候选，并记录原因。

这些依据都不能绕过项目边界、来源核验、第二次价值审核或人工发布批准。

### 3. 生产一条帖子

```text
使用 codoop-content-ticket 领取最佳可用线索，并准备一条等待批准的帖子。
```

生产流程自动选择最新发现运行中排名最高且没有明显过时的线索。领取新线索前，它会优先恢复中断的 claimed 工单。

如果池中没有合适线索，生产流程会停止并提示先运行发现。它不会自动启动另一条流水线。

## 不可绕过的门禁

- 只有第一次审核表中明确标为 `go` 的候选，或带理由的人工提升，才可以进入 `available`。
- 重复检查 clear 之前不能调用 Firecrawl。
- 一手来源快照和显式 verified evidence 都存在后，才能进行第二次审核。
- 所有通过依据都必须在写作前通过 fresh 二审。
- 没有二审 `go` 就不能 `write` 或 `submit`。
- 排程和发布前必须获得明确人工批准。
- `publish-due` 默认 dry-run；只有明确指令和 `--live` 才调用 X 官方 API。
- 发布失败会保留回执和 claimed 线索，不自动重试。

## 可选表现反馈

发布后可以手工记录曝光、评论和转发：

```bash
run.sh record-performance TICKET_ID \
  --impressions 1000 --comments 4 --shares 8
```

工作流会计算每千次曝光互动，并在后续发现审核中读取已有表现文件。缺失数据不会阻塞流程，也不会自动调用分析 API。

## 文档

- [工作流决策](./docs/workflow-decisions.zh-CN.md)
- [项目初始化与内容工作流设计](./docs/project-initialization-optimization-plan.zh-CN.md)
- [变更记录（英文）](./CHANGELOG.md)

## 第一版范围

- 每条已消费线索只生成一条不超过 280 字符的 X 帖子。
- 只使用 X 官方 API。
- 只使用本地文件，不使用数据库、常驻服务或 Git 状态机。
- 多平台内容生产明确留到后续版本。
