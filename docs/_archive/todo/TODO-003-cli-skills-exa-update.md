# TODO-003: Update CLI Skills with Exa and News Commands

**Status:** Completed
**Priority:** Medium
**Created:** 2026-01-09
**Component:** `.claude/skills/kalshi-cli/`
**Completed:** 2026-01-09

---

## Summary

The CLI skills documentation in `.claude/skills/kalshi-cli/CLI-REFERENCE.md` is missing the following commands:

### Missing: `news` Commands

```
kalshi news
├── track          # Start tracking news for a market or event
├── untrack        # Stop tracking a market/event
├── list-tracked   # List tracked markets/events
├── collect        # Collect news for tracked items
└── sentiment      # Show sentiment summary for a market/event
```

### Missing: `research` Subcommands (Exa-Powered)

```
kalshi research
├── context TICKER    # Research context for a market using Exa
├── topic TOPIC       # Research a topic for thesis ideation using Exa
├── thesis            # (already documented)
└── backtest          # (already documented)
```

---

## Files to Update

1. `.claude/skills/kalshi-cli/CLI-REFERENCE.md`
   - Add `news` section with all subcommands
   - Add `research context` command
   - Add `research topic` command

2. `.claude/skills/kalshi-cli/WORKFLOWS.md`
   - Add "Exa-Powered Research Workflow" section
   - Add "News/Sentiment Monitoring Workflow" section

3. `.claude/skills/kalshi-cli/GOTCHAS.md`
   - Add "Exa API Gotchas" section (requires `EXA_API_KEY`)
   - Add "News Collection Gotchas" section

---

## Command Details to Add

### news track

```bash
uv run kalshi news track TICKER [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--event`, `-e` | False | Treat ticker as an event ticker |
| `--queries`, `-q` | Auto | Comma-separated custom search queries |
| `--db`, `-d` | `data/kalshi.db` | Path to database |

### news untrack

```bash
uv run kalshi news untrack TICKER [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--db`, `-d` | `data/kalshi.db` | Path to database |

### news list-tracked

```bash
uv run kalshi news list-tracked [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--all` | False | Include inactive tracked items |
| `--db`, `-d` | `data/kalshi.db` | Path to database |

### news collect

```bash
uv run kalshi news collect [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--ticker` | None | Specific ticker (default: all tracked) |
| `--lookback-days` | `7` | How far back to search |
| `--max-per-query` | `25` | Max articles per search query |
| `--db`, `-d` | `data/kalshi.db` | Path to database |

### news sentiment

```bash
uv run kalshi news sentiment TICKER [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--days` | `7` | Analysis period in days |
| `--db`, `-d` | `data/kalshi.db` | Path to database |

### research context

```bash
uv run kalshi research context TICKER [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--max-news` | `10` | Max news articles |
| `--max-papers` | `5` | Max research papers |
| `--days` | `30` | News recency in days |
| `--json` | False | Output as JSON |

### research topic

```bash
uv run kalshi research topic TOPIC [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--no-summary` | False | Skip LLM summary |
| `--json` | False | Output as JSON |

---

## Verification

After updating, verify:

```bash
# Check news commands work
uv run kalshi news --help
uv run kalshi news track --help
uv run kalshi news collect --help

# Check research commands work
uv run kalshi research context --help
uv run kalshi research topic --help
```
