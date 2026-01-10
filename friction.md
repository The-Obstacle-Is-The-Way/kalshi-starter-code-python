# Friction Log

**Session:** 2026-01-09
**Purpose:** Track CLI friction, bugs, and issues encountered during research session

---

## Confirmed Issues

### 1. BUG-047: Portfolio positions sync shows 0 despite portfolio_value > 0

**Encountered:** 2026-01-09 18:15
**Command:** `uv run kalshi portfolio positions`
**Output:** "No open positions found"
**But:** `portfolio balance` shows portfolio_value = 8822 ($88.22)

**Impact:** Cannot see current positions through CLI. Must query Kalshi API directly or check trades table.

**Workaround:** Calculate net positions from trades table:
```sql
SELECT ticker, side, SUM(CASE WHEN action='buy' THEN quantity ELSE -quantity END) as net
FROM trades GROUP BY ticker, side HAVING net > 0;
```

**Status:** Known bug, tracked in [`docs/_archive/bugs/BUG-047-portfolio-positions-sync.md`](docs/_archive/bugs/BUG-047-portfolio-positions-sync.md)

---

## CLI Friction Notes

### Ticker Truncation
- `portfolio history` truncates long tickers with `...`
- Need to query database for full tickers
- Example: `KXNFLAFCCHAMP-25-…` should be queried from `trades` table

---

## Commands That Worked Well

- `kalshi portfolio balance` - Clean output
- `kalshi portfolio history -n 50` - Shows trades correctly

---

## To Investigate

- [ ] Why positions sync fails but balance works
- [ ] Full ticker names for truncated entries

---

## Market Scan Friction

### Scanner Shows Illiquid Garbage
- `kalshi scan opportunities` returns multivariate sports markets with 0 volume and 98¢ spreads
- Need better filtering to exclude KXMVE (multivariate) markets
- Should prioritize by volume AND spread quality

### Database Sync Dominated by Sports Parlays
- `data sync-markets --max-pages 10` syncs 10,000 markets
- ~15,000 are KXMVE (multivariate sports parlays)
- Interesting political/economic markets not captured in default sync
- **Workaround:** Query API directly with `mve_filter=exclude`

### Missing Category Filter
- `markets` table has `category` column but it's empty
- Cannot filter by Politics/Economics/AI in database
- Need to use event_ticker patterns (KXFED, KXTRUMP, KXBTC, etc.)

---

## API Notes

### Useful Event Ticker Patterns
- `KXFED*` - Federal Reserve markets
- `KXTRUMP*` - Trump administration markets
- `KXBTCD-*` - Bitcoin daily price markets
- `KXOAIANTH*` - OpenAI vs Anthropic
- `KXSB-*` - Super Bowl
- `KXNCAAFSPREAD-*` - College football spreads

### Good Query for Non-Sports Markets

```bash
# Use mve_filter=exclude to skip multivariate parlays
GET /markets?status=open&limit=500&mve_filter=exclude
```

---

## Metacognitive Reflection: Exa Integration Gap (2026-01-09)

### The Core Problem (Session Evidence)

In this session, the user asked: "Find mispriced markets and give me top 3 trade recommendations."

**What I (Claude) did:**

1. Queried Kalshi API for markets
2. Scanned for volume, spreads, prices
3. Found interesting markets (Fed Chair, Bitcoin, Trump cabinet)
4. **Gave probability estimates and trade recommendations**

**What I did NOT do:**

- Use Exa to research ANY of the markets
- Validate probability estimates with real-time news/sources
- Ground my recommendations in actual research

**Result:** My "recommendations" were based on vibes from training data, NOT structured research.

### Why This Matters

The user's whole thesis is: "Beat vibes-only gamblers with actual signal."

But in this session, I WAS the vibes-only gambler. I gave recommendations like:

- "OpenAI IPO at 34% seems mispriced because..." (no research, just training data)
- "Pete Hegseth departure at 32% seems low because..." (no news search, just vibes)

This is the EXACT problem the user identified in prior brainstorming:

> "Claude Code is doing all that. And as it does that, it's putting in information that it gleans into its context... I think it just has a hard time parsing all that information."

### Architectural Gap

**Current state:**

```text
User query → Claude Code → runs CLI → gets market data → Claude synthesizes (VIBES)
```

**Needed state:**

```text
User query → Claude Code → runs CLI → gets market data → Exa research → Structured synthesis → Validated output
```

### Exa Integration Questions (Unresolved)

1. **Is Exa wired into CLI?** - Need to check if `kalshi research context` or `kalshi news` commands use Exa
2. **Did I have access to Exa MCP?** - Unclear if Exa MCP was available in this session
3. **Why didn't I use it?** - Either not available, not prompted, or I defaulted to training data

### Open Questions for Architecture

From user's brainstorming with Deep Research agent:

> "Should Exa be:
> (A) A CLI command that Claude Code calls and gets raw results?
> (B) Integrated directly into a 'Research Agent' that handles search + summarization?
> (C) Called via MCP so any agent harness can use it natively?"

### Next Steps

- [ ] Verify Exa integration status in codebase
- [ ] Test `kalshi research context TICKER` command
- [ ] Test `kalshi news collect` command
- [ ] Determine if Exa MCP is configured
- [ ] Design structured synthesis pipeline per DeepMind paper recommendations

### Key Insight

The friction is NOT in the Kalshi API integration (that works well).
The friction is in the **research → synthesis → structured output** pipeline.

Without this, Claude just vibes on market data - which defeats the entire purpose of the tool.
