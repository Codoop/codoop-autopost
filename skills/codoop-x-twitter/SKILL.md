---
name: codoop-x-twitter
description: Publish an explicitly approved single X post through the official X API using the user's OAuth credentials. Use only for a user-approved post; never use for browser automation, replies, likes, follows, or direct messages.
---

# Codoop X Publisher

Require all four environment variables: `X_CONSUMER_KEY`, `X_CONSUMER_SECRET`, `X_ACCESS_TOKEN`, and `X_ACCESS_SECRET`.

Only publish when the user explicitly approves the exact text. Pass the explicit approval flag:

```bash
python3 scripts/publish.py --approved "POST TEXT"
```

The script only sends `POST /2/tweets`. Record its returned post ID, URL, and timestamp in the calling workflow. Do not use this Skill for any other X action.
