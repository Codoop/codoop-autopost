---
name: x-twitter
description: Publish an explicitly approved single X post through the official X API using the user's OAuth credentials. 仅用于发布用户明确批准的单条 X 帖子；禁止浏览器自动化、回复、点赞、关注或私信。
---

# X Twitter / X 发布

Require all four environment variables: `X_CONSUMER_KEY`, `X_CONSUMER_SECRET`, `X_ACCESS_TOKEN`, and `X_ACCESS_SECRET`.

需要四个环境变量：`X_CONSUMER_KEY`、`X_CONSUMER_SECRET`、`X_ACCESS_TOKEN` 和 `X_ACCESS_SECRET`。

Only publish when the user explicitly approves the exact text. Pass the explicit approval flag:

只有用户明确批准完全一致的正文后才可发布；传入明确的批准标志：

Set `X_TWITTER_SKILL_DIR` to the installed directory containing this `SKILL.md`; its bundled `scripts/run.sh` selects Python 3.12+.

将 `X_TWITTER_SKILL_DIR` 设为包含此 `SKILL.md` 的已安装目录；其内置 `scripts/run.sh` 会选择 Python 3.12+。

```bash
<X_TWITTER_SKILL_DIR>/scripts/run.sh --approved "POST TEXT"
```

The script only sends `POST /2/tweets`. Record its returned post ID, URL, and timestamp in the calling workflow. Do not use this Skill for any other X action.

脚本只会发送 `POST /2/tweets`。在调用工作流中记录返回的帖子 ID、URL 和时间戳；不得将此 Skill 用于任何其他 X 操作。
