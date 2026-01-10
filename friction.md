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

---

## Case Study: Indiana Spread Bet Failure (2026-01-09)

### The Loss

**Market:** `KXNCAAFSPREAD-26JAN09OREIND-IND3` (Indiana -3.5 vs Oregon)
**Position:** 37 YES contracts at ~48¢
**Result:** Oregon won. Loss: **$17.76**
**Thesis ID:** `fd501d1b` (resolved as LOSS)

### What Went Wrong

Claude (Opus 4.5) surfaced this as an "upside bet" based on:
- Spread analysis
- Volume patterns
- Price movement

**What Claude FAILED to surface:**

1. **Indiana was UNDEFEATED** - The most basic fact about the team
2. **No adversarial research** - Didn't check Oregon's recent performance
3. **No live game context** - User watched one quarter and saw Oregon "looked like absolute shit"
4. **Sports domain blindness** - Training data ≠ current season performance

### User's Direct Feedback

> "If you're supposed to be the one going to AGI, you're the one who surfaced that. I was depending on you for the edge. And now I know that you're totally unreliable. It makes me question this whole system we're building."

> "What is the whole point of this system if I'm going based on vibes, bro?"

### The Architectural Lesson

**Current failure mode:**

```text
User asks for edge → Claude scans markets → Claude gives "recommendation" (VIBES) → User loses money
```

**Required safeguard:**

```text
User asks for edge → Claude scans markets → ADVERSARIAL CHECK → Research BOTH sides →
Surface disqualifying facts → THEN recommend (or refuse to recommend)
```

### Specific Gaps Exposed

| Gap | Description | Fix Required |
|-----|-------------|--------------|
| **No adversarial weighting** | Claude recommends without checking counter-thesis | Force both bull AND bear research before ANY recommendation |
| **No domain expertise check** | Claude has no current sports knowledge | Either integrate live sports data OR refuse sports bets entirely |
| **No "basic facts" gate** | Missed that Indiana was undefeated | Pre-flight check: "What are the 3 most important facts about this market?" |
| **No confidence calibration** | Gave recommendation with false confidence | Require explicit uncertainty disclosure: "I have NO current data on this" |

### Implications for Agent Orchestration

When we build the multi-agent system, we need:

1. **Adversarial Agent** - Dedicated agent that argues AGAINST every recommendation
2. **Domain Guard** - Refuses to recommend on domains with stale training data (sports, breaking news)
3. **Basic Facts Gate** - Before any recommendation, surface 3-5 basic facts and ask: "Does this change my thesis?"
4. **Confidence Disclosure** - Explicit statement: "This is based on [research/training data/vibes]"

### Future Skill/Prompt Engineering

Add to agent skills (`.claude/skills/`, etc.):

```markdown
## Pre-Recommendation Checklist

Before making ANY trade recommendation:

1. [ ] What are the 3 most important facts about this market?
2. [ ] What is the strongest argument AGAINST this position?
3. [ ] Is this based on current research or training data?
4. [ ] If training data only: REFUSE to recommend, surface uncertainty instead
5. [ ] If sports/breaking news: REQUIRE live data source or refuse
```

### The Silver Lining

This $17.76 loss is:
- **Tuition** for learning how Kalshi works
- **Data** for improving the system
- **Documented friction** that will prevent future losses

> "We're paying money into education... This is good data."

---
