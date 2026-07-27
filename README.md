# codoop-autopost

一个可独立安装的开源 Agent Skill：从热点发现到一手来源核验、内容草稿、人工审核和 X 定时发布。

它只发布人工明确批准的单条 X 帖子。不会使用浏览器自动化，不会自动回复、点赞、关注或私信。

## 安装

克隆仓库后，运行一次安装脚本。用户只安装 `codoop-autopost`，不需要单独安装 last30days、Firecrawl、social-content、copy-editing 或 x-twitter Skill。

```bash
git clone https://github.com/Codoop/codoop-autopost.git
cd codoop-autopost
./scripts/install-skill.sh --agent codex
```

Claude Code 使用：

```bash
./scripts/install-skill.sh --agent claude
```

仓库同时提供 Codex、Claude Code 和 Agent Skills 市场清单，组织方式与 [codoop-flow](https://github.com/Codoop/codoop-flow) 一致。

## 首次使用

Skill 首次运行时把私有的 `last30days` MIT 运行时初始化到 `~/.local/share/codoop-autopost/last30days`：

```bash
python3 ~/.codex/skills/codoop-autopost/scripts/bootstrap.py
```

若安装到其他 Agent 路径，请使用对应的 Skill 目录。`FIRECRAWL_API_KEY` 仅在核验来源时需要；真实发布还需要 X 官方 OAuth 1.0a 凭据：`X_CONSUMER_KEY`、`X_CONSUMER_SECRET`、`X_ACCESS_TOKEN`、`X_ACCESS_SECRET`。

## 安全边界

- `last30days` 只发现讨论，不构成事实来源。
- 每条关键主张必须记录 URL、来源类型、发布日期和原文摘录。
- 没有核验证据的草稿无法批准；没有显式批准的内容无法排程或发布。
- `publish-due` 默认是 dry-run；只有 `--live` 才调用 X 官方 API。
- Firecrawl 通过 API/兼容自托管端点调用，不捆绑其 AGPL 源码。

详细架构与许可证边界见 [workflow-decisions.md](docs/workflow-decisions.md)。
