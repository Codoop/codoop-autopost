---
name: last30days
description: Discover recent, high-engagement discussion candidates across public sources. 用于选题发现、趋势研究和寻找讨论线索；绝不可将结果当作已核验事实。
---

# Last30Days / 近期热点发现

Use this Skill to discover discussion candidates, not to establish facts.

此 Skill 只用于发现讨论候选，不用于确认事实。

Run the bundled `scripts/run.sh` beside this `SKILL.md`; it selects Python 3.12+.

运行与此 `SKILL.md` 同目录的内置 `scripts/run.sh`；它会选择 Python 3.12+。

```bash
<LAST30DAYS_SKILL_DIR>/scripts/run.sh --init
<LAST30DAYS_SKILL_DIR>/scripts/run.sh "TOPIC"
```

The plugin includes the MIT-licensed `last30days` v3.18.3 runtime, so neither command downloads a separate Skill. The second prints machine-readable research. Score candidates for relevance, recency, engagement, and availability of primary evidence. Hand off every surviving claim to `firecrawl` for verification. To override the bundled version with an already initialized runtime, set `CODOOP_LAST30DAYS_DIR` to its root.

插件已内置 MIT 许可的 `last30days` v3.18.3 运行时，因此两条命令都不会额外下载 Skill。第二条命令输出机器可读的研究结果。按相关性、时效性、互动度和一手证据可得性为候选评分；将所有保留主张交给 `firecrawl` 核验。若要用已初始化的运行时覆盖内置版本，将 `CODOOP_LAST30DAYS_DIR` 设为其根目录。
