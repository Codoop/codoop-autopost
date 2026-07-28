---
name: firecrawl
description: Read source URLs through Firecrawl and extract evidence for claim verification. 在核验一手来源、记录事实主张或拒绝未经核验内容时使用。
---

# Firecrawl / 来源核验

Require `FIRECRAWL_API_KEY`. Read a URL as Markdown:

需要 `FIRECRAWL_API_KEY`。将 URL 读取为 Markdown：

Set `FIRECRAWL_SKILL_DIR` to the installed directory containing this `SKILL.md`; its bundled `scripts/run.sh` selects Python 3.12+.

将 `FIRECRAWL_SKILL_DIR` 设为包含此 `SKILL.md` 的已安装目录；其内置 `scripts/run.sh` 会选择 Python 3.12+。

```bash
<FIRECRAWL_SKILL_DIR>/scripts/run.sh "URL"
```

Classify the source before relying on it: official announcement, original reporting, paper, or the subject's original post are primary evidence. Record claim, URL, source type, publication date, and a short exact excerpt. Reject unresolved conflicts and unsupported claims.

使用前先分类来源：官方公告、原始报道、论文或当事人原帖才可作为一手证据。记录主张、URL、来源类型、发布日期和简短原文摘录；拒绝尚未解决的冲突和无证据主张。
