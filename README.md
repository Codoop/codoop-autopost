# codoop-autopost

一个插件完成热点发现、一手来源核验、内容草稿、人工审核和 X 定时发布的开源 Agent Skill。

它只发布人工明确批准的单条 X 帖子。不会使用浏览器自动化，不会自动回复、点赞、关注或私信。

## 安装

### Codex（Desktop 或 CLI）

从 GitHub 插件市场安装一个 `codoop-autopost` 插件，即可获得热点发现、来源核验、写作、润色和 X 发布所需能力。`last30days`、`firecrawl`、`social-content`、`copy-editing` 和 `x-twitter` 都随主插件提供。

```bash
codex plugin marketplace add Codoop/codoop-autopost
codex plugin add codoop-autopost@codoop-autopost
```

安装后重启或重新打开 Codex。也可以直接对 Codex 说：

```text
Install the codoop-autopost Codex plugin from Codoop/codoop-autopost.
```

### Claude Code

```bash
/plugin marketplace add Codoop/codoop-autopost
/plugin install codoop-autopost@codoop-autopost
```

同一 Skill Pack 也提供 `last30days`、`firecrawl`、`social-content`、`copy-editing` 和 `x-twitter` 的独立入口，方便高级用户按需使用。仓库的插件组织方式与 [codoop-flow](https://github.com/Codoop/codoop-flow) 一致。

### 本地开发备用方式

只有开发或离线调试插件时，才克隆仓库并运行 `./scripts/install-skill.sh`。

## 运营项目目录

每个账号或品牌使用一个运营项目目录。用户在这个目录中运行 Skill；它保存本次运营的工单和所有可审核的阶段产物，无需 Git。

```text
content-operations/
├── config.toml
├── tickets/
│   └── T-20260727-001-topic/
│       ├── ticket.toml
│       ├── discovery/
│       │   ├── raw.json
│       │   ├── candidates.md
│       │   └── selection.md
│       ├── verification/
│       │   ├── evidence.md
│       │   ├── claims.md
│       │   └── source-snapshots/
│       ├── writing/
│       │   ├── brief.md
│       │   ├── drafts.md
│       │   └── edited.md
│       ├── review/
│       │   ├── final.md
│       │   └── approval.md
│       └── publish/
│           ├── schedule.toml
│           └── receipt.json
```

`ticket.toml` 是一张工单的状态入口：

```toml
id = "T-20260727-001-topic"
status = "draft" # draft | pending | done
platform = "x"
```

- `draft`：收集热点、核验来源和写作。
- `pending`：最终稿已在 `review/final.md`，等待人工审核或定时发布；`ticket.toml` 会记录批准和排程时间。
- `done`：发布成功，发布信息保存在 `publish/receipt.json`。

工单目录是唯一的运营记录：不创建 `autopost.db` 或隐藏状态目录。发布时会在当前工单内短暂创建锁；进程异常中断而留下锁时，保留它供人工检查，避免意外重复发布。

## 首次使用

在每个运营项目的根目录放一份私有配置文件：

```bash
mkdir content-operations
cd content-operations
cp ~/.codex/skills/codoop-autopost/config.example.toml ./config.toml
chmod 600 ./config.toml
```

填写 `config.toml` 中的 Firecrawl 和 X OAuth 值即可。若使用其他 Agent，请从其安装目录复制同一份模板。每次运行 Skill 或定时任务都以该运营项目为工作目录，Skill 会自动读取其中的 `config.toml`。`FIRECRAWL_API_KEY`、`FIRECRAWL_API_URL` 及 X 的四个环境变量仍可覆盖配置文件，适合 CI 或服务器。若配置文件不在默认位置，可设置 `CODOOP_AUTOPOST_CONFIG`。

用户直接发起热点发现时，主 Skill 会自动下载其私有的 `last30days` MIT 运行时到 `~/.local/share/codoop-autopost/last30days`。此步骤需要 Python、Git 和网络连接。

## 安全边界

- `last30days` 只发现讨论，不构成事实来源。
- 每条关键主张必须记录 URL、来源类型、发布日期和原文摘录，并由执行者显式标记为已核验。
- 没有核验证据的草稿无法批准；没有显式批准的内容无法排程或发布。
- `publish-due` 默认是 dry-run；只有 `--live` 才调用 X 官方 API。
- Firecrawl 通过 API/兼容自托管端点调用，不捆绑其 AGPL 源码。

详细架构与许可证边界见 [workflow-decisions.md](docs/workflow-decisions.md)。
