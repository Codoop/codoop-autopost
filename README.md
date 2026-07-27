# codoop-autopost

一个可独立安装的开源 Agent Skill：从热点发现到一手来源核验、内容草稿、人工审核和 X 定时发布。

它只发布人工明确批准的单条 X 帖子。不会使用浏览器自动化，不会自动回复、点赞、关注或私信。

## 安装

克隆仓库后，只安装主工作流即可运行完整流程；不需要另装任何依赖 Skill。

```bash
git clone https://github.com/Codoop/codoop-autopost.git
cd codoop-autopost
./scripts/install-skill.sh --agent codex --skill codoop-autopost
```

如需把六个 Skill 都安装为独立入口：

```bash
./scripts/install-skill.sh --agent codex
```

Claude Code 使用：

```bash
./scripts/install-skill.sh --agent claude
```

Skill Pack 包含：`codoop-autopost`、`last30days`、`firecrawl`、`social-content`、`copy-editing`、`x-twitter`。后五项可单独安装，但不是 `codoop-autopost` 的前置条件。仓库同时提供 Codex、Claude Code 和 Agent Skills 市场清单，组织方式与 [codoop-flow](https://github.com/Codoop/codoop-flow) 一致。

## 首次使用

在每个运营项目的根目录放一份私有配置文件：

```bash
mkdir content-operations
cd content-operations
cp ~/.codex/skills/codoop-autopost/config.example.toml ./config.toml
chmod 600 ./config.toml
```

填写 `config.toml` 中的 Firecrawl 和 X OAuth 值即可。若使用其他 Agent，请从其安装目录复制同一份模板。每次运行 Skill 或定时任务都以该运营项目为工作目录，Skill 会自动读取其中的 `config.toml`。`FIRECRAWL_API_KEY`、`FIRECRAWL_API_URL` 及 X 的四个环境变量仍可覆盖配置文件，适合 CI 或服务器。若配置文件不在默认位置，可设置 `CODOOP_AUTOPOST_CONFIG`。

首次运行热点发现时，主 Skill 会自动下载其私有的 `last30days` MIT 运行时到 `~/.local/share/codoop-autopost/last30days`；用户无需安装或初始化 `last30days` Skill。此步骤需要 Python、Git 和网络连接。

## 安全边界

- `last30days` 只发现讨论，不构成事实来源。
- 每条关键主张必须记录 URL、来源类型、发布日期和原文摘录，并由执行者显式标记为已核验。
- 没有核验证据的草稿无法批准；没有显式批准的内容无法排程或发布。
- `publish-due` 默认是 dry-run；只有 `--live` 才调用 X 官方 API。
- Firecrawl 通过 API/兼容自托管端点调用，不捆绑其 AGPL 源码。

详细架构与许可证边界见 [workflow-decisions.md](docs/workflow-decisions.md)。
