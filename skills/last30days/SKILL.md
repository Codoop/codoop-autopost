---
name: last30days
description: Discover recent, high-engagement discussion candidates across public sources. Use for topic discovery, trend research, and finding discussion leads; never use its results as verified facts.
---

# Last30Days

Use this Skill to discover discussion candidates, not to establish facts.

```bash
python3 scripts/last30days.py --init
python3 scripts/last30days.py "TOPIC"
```

The first command downloads the MIT-licensed upstream runtime to the user's data directory. The second prints machine-readable research. Score candidates for relevance, recency, engagement, and availability of primary evidence. Hand off every surviving claim to `firecrawl` for verification.
