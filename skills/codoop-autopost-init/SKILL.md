---
name: codoop-autopost-init
description: Initialize or update a codoop-autopost content-operations project. 在创建内容工单前，用于确定或更新项目赛道、主读者、内容支柱、禁区、语言、语气和写作规则。
---

# Codoop Autopost Initialization / Codoop Autopost 初始化

Use this Skill only in the root of a content-operations project. It creates or updates the two human-approved standards that `codoop-content-ticket` must read:

仅在内容运营项目根目录使用此 Skill。它创建或更新 `codoop-content-ticket` 必须读取的两份经人工确认的标准：

- `PROJECT.md`: what the project writes about.
- `VOICE.md`: how the project writes.

It also creates the private `config.toml` template when it is missing.

缺少时，它还会创建私有的 `config.toml` 模板。

Do not ask for Firecrawl or X credentials. They belong in `config.toml` and are not required for initialization.

不要询问 Firecrawl 或 X 凭据。它们属于 `config.toml`，不是初始化的前置条件。

## Interview rules

## 访谈规则

Use the bundled `grilling` Skill for the interview. Ask one question at a time. Give a recommendation, reason, and a concrete example before asking for the user's answer. Treat every recommendation as unconfirmed until the user accepts it.

使用内置 `grilling` Skill 进行访谈。一次只问一个问题；在请求用户回答前，先给出推荐、理由和具体示例。用户接受前，所有推荐都视为未确认。

Do not write either final file while its interview is in progress. Do not save a draft interview transcript. After the user explicitly confirms the complete document, write it and then move to the next document.

访谈进行中不得写入任一正式文件，也不得保存访谈草稿。只有用户明确确认完整文档后才可写入，然后再处理下一份文件。

If only one standard is being changed, interview and replace only that file.

若只修改一份标准，只访谈并替换对应文件。

## Build `PROJECT.md`

## 构建 `PROJECT.md`

Ask until all of these are specific and confirmed:

持续提问，直到以下事项都足够具体且已确认：

1. One vertical-sentence definition and its relevance rule.
2. One primary reader: identity and context, current goal, and existing knowledge.
3. Three to five content pillars. Each pillar has a name, what it includes, and what it excludes.
4. Global no-go topics, formats, risk categories, and irrelevant trend-chasing.
5. Three to five discovery directions, each linked to a content pillar. Describe a durable research scope, not an event list or SEO keyword bank.

1. 一句赛道定义及其相关性判断规则。
2. 一位主读者：身份与场景、当前目标和已有基础。
3. 三到五个内容支柱；每个支柱都包含名称、包含范围和排除范围。
4. 全局禁区：主题、内容形式、风险类别和无关蹭热点。
5. 三到五条发现方向，每条对应一个内容支柱。它描述长期研究范围，不是事件清单或 SEO 关键词库。

Do not add a content promise, business goal, editorial stance, platform configuration, credentials, source whitelist, or detailed demographic persona unless the user later explicitly asks for them.

除非用户后来明确要求，否则不得加入内容承诺、商业目标、编辑立场、平台配置、凭据、来源白名单或细碎的人口统计画像。

## Build `VOICE.md`

## 构建 `VOICE.md`

After `PROJECT.md` is confirmed, ask until all of these are specific and confirmed:

在 `PROJECT.md` 确认后，持续提问，直到以下事项都足够具体且已确认：

1. Main language and English-term policy.
2. Reader distance, desired tone, and tone to avoid.
3. Sentence length, opening pattern, structure, pronoun use, and paragraph rhythm.
4. Lists, headings, emoji, punctuation, links, citations, and CTA preferences.
5. Preferred expressions and prohibited expressions.
6. Concrete style rules derived from the conversation or optional user-provided samples.

1. 主要语言与英文术语策略。
2. 与读者的距离、希望呈现的语气和应避免的语气。
3. 句子长度、开头方式、结构、人称使用以及段落节奏。
4. 列表、标题、Emoji、标点、链接、引用和 CTA 偏好。
5. 偏好表达与禁用表达。
6. 从对话或用户可选样本中提炼的具体风格规则。

Accept examples as optional input. Extract only reusable rules; never copy a sample's facts, opinions, or text into `VOICE.md`.

将示例视为可选输入。只提炼可复用的规则；绝不可把示例中的事实、观点或原文复制进 `VOICE.md`。

## Finish

## 完成

After both documents are confirmed, ensure `content-tickets/` exists. Then run the bundled `scripts/run.sh` beside this `SKILL.md`, with `--workspace .`; it selects Python 3.12+ before calling `init_config.py`.

两份文件确认后，确保 `content-tickets/` 存在。随后运行与此 `SKILL.md` 同目录的 `scripts/run.sh --workspace .`；它会选择 Python 3.12+ 并调用 `init_config.py`。

- If `config.toml` is missing, create it from `config.example.toml` and make it owner-readable only where the operating system supports file modes.
- If it already exists, preserve it unchanged. Never display, read back, or place its values in a ticket.
- Explain the configuration handoff below. Do not ask the user to provide any value during initialization; empty values are valid until the matching capability is used. Environment variables can override this file for automation.

- 若缺少 `config.toml`，从 `config.example.toml` 创建，并在操作系统支持时将其权限设为仅所有者可读。
- 若文件已经存在，原样保留。绝不可显示、读回或把其中的值写入工单。
- 说明下方的配置交接。初始化时不要要求用户提供任何值；相应能力尚未使用前，空值是有效的。自动化时可用环境变量覆盖该文件。

### Configuration handoff

### 配置交接

Tell the user:

向用户说明：

- `[firecrawl].api_key` lets the workflow read primary-source URLs for evidence verification. Create a Firecrawl account and obtain an API key from its dashboard: <https://www.firecrawl.dev/>. Keep the default `api_url` unless using a compatible self-hosted endpoint.
- `[x].consumer_key` and `[x].consumer_secret` identify the user's X Developer App. `[x].access_token` and `[x].access_secret` authorize this workflow to post as the user's X account. In the [X Developer Console](https://developer.x.com/en/portal/dashboard), create or select an App, enable user authentication with write permission, then generate its Keys and Tokens. Regenerate the user tokens if the App's permissions change.
- These values are secrets: never paste them into the chat, a ticket, `PROJECT.md`, `VOICE.md`, Git, or screenshots. Store them only in the local `config.toml` or provide them as environment variables for a trusted scheduler.

- `[firecrawl].api_key` 让工作流读取一手来源 URL 以核验证据。在 <https://www.firecrawl.dev/> 创建 Firecrawl 账号并从控制台获取 API key；除非使用兼容的自托管端点，否则保留默认 `api_url`。
- `[x].consumer_key` 和 `[x].consumer_secret` 用于识别用户的 X Developer App。`[x].access_token` 和 `[x].access_secret` 授权工作流代表该 X 账号发帖。在 [X Developer Console](https://developer.x.com/en/portal/dashboard) 创建或选择 App，开启带写权限的用户认证，然后生成 Keys and Tokens；若 App 权限变化，重新生成用户令牌。
- 这些值是密钥：绝不可粘贴到聊天、工单、`PROJECT.md`、`VOICE.md`、Git 或截图中。只存放在本地 `config.toml`，或以环境变量提供给可信的定时器。

State that the project is ready for `codoop-content-ticket`. Never create a content ticket during initialization.

说明项目已经可以使用 `codoop-content-ticket`。初始化期间绝不可创建内容工单。
