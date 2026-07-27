# codoop-autopost

一个证据优先的 X 内容工作流 Skill：发现近期讨论、核验一手来源、生成待审核稿，并且只在人工批准后按计划发布。

## 安全边界

- `last30days` 只用于发现讨论，不构成事实来源。
- 每条用于草稿的关键主张都必须保存 URL、来源类型、发布日期和原文摘录。
- 未保存核验证据的草稿不能批准；未明确批准的草稿不能排程或发布。
- 默认 `publish-due` 是 dry-run。只有 `--live` 才会调用 X 官方 API。
- 只支持发单条 X 帖子。不执行浏览器自动化、自动回复、点赞、关注或私信。

## 使用

Skill 位于 `.agents/skills/codoop-autopost`。首次使用时初始化它私有的 `last30days` 运行时：

```bash
python3 .agents/skills/codoop-autopost/scripts/bootstrap.py
```

发现讨论：

```bash
python3 .agents/skills/codoop-autopost/scripts/autopost.py discover "AI agents"
```

来源核验需要 `FIRECRAWL_API_KEY`；实时发帖还需要自己的 X OAuth 1.0a 凭据：`X_CONSUMER_KEY`、`X_CONSUMER_SECRET`、`X_ACCESS_TOKEN`、`X_ACCESS_SECRET`。凭据不会写入 SQLite。

完整的工作流、状态机、许可证边界和待定决策见 [workflow-decisions.md](docs/workflow-decisions.md)。
