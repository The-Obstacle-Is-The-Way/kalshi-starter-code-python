# Friction Log

**Session:** 2026-01-09
**Purpose:** Track CLI friction, bugs, and issues encountered during research session
**Status:** Mostly resolved. Remaining items consolidated in [DEBT-014](DEBT-014-friction-residuals.md).

---

## Confirmed Issues

### 1. ~~BUG-047: Portfolio positions sync shows 0 despite portfolio_value > 0~~

**Status:** ✅ **FIXED** (2026-01-10) - See [`docs/_archive/bugs/BUG-047-portfolio-positions-sync.md`](../_archive/bugs/BUG-047-portfolio-positions-sync.md)

---

## CLI Friction Notes

### ~~Ticker Truncation~~

**Status:** ✅ **IMPLEMENTED** (2026-01-11) - See [SPEC-035](../specs/SPEC-035-ticker-display-enhancement.md)

Use `--full` / `-F` flag on `market list`, `scan opportunities`, `scan movers` to show full tickers/titles.

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

### ~~Scanner Shows Illiquid Garbage~~

**Status:** ✅ **ADDRESSED** (2026-01-11) - Use `--no-sports` or `--category` flags on `scan opportunities`.

### Database Sync Dominated by Sports Parlays

**Status:** ⚠️ **PARTIAL** - Tracked in [DEBT-014](DEBT-014-friction-residuals.md) Item 1.

- `data sync-markets` still doesn't expose `--mve-filter` flag
- **Workaround:** Query API directly with `mve_filter=exclude` or use `scan`/`market list` with filtering

### ~~Missing Category Filter~~
- ✅ **Resolved (2026-01-11):** Category filtering now works for both:
  - `kalshi market list --category ...`
  - `kalshi scan opportunities --category ...` / `--no-sports`

**Root cause (why it looked “impossible”):**
- `GET /markets` has no server-side category filter, and its pagination is dominated by Sports multivariate markets.
- Early implementations that fetched “first N markets” + used event_ticker prefix heuristics produced false
  negatives (e.g., `--category ai` returning no results despite Science/Tech markets existing).

**Fix:**
- Use `GET /events?with_nested_markets=true` as the SSOT and filter on `Event.category` (case-insensitive),
  then flatten nested markets.
- This also avoids the “sports parlay pagination trap” because `/events` excludes multivariate events.

**Residual risk:**
- Kalshi OpenAPI notes `Event.category` is deprecated in favor of series-level category; if Kalshi removes it,
  migrate SSOT to `Series.category`.

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

**Status:** 📝 **DESIGN DOC** - Tracked in [DEBT-014](DEBT-014-friction-residuals.md) Items 2-4.

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

**Status:** 📝 **HISTORICAL LESSON** - Informs [DEBT-014](DEBT-014-friction-residuals.md) Item 3 (Adversarial Research).

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

### Critical Context: Bet Was Placed BEFORE Exa Integration

**Timeline:**

| Event | Timestamp |
|-------|-----------|
| Indiana thesis created | 2026-01-09 03:10:01 UTC |
| Exa implemented (commit c285248) | 2026-01-09 07:15:00 UTC |

The thesis was created **4 hours before** Exa was integrated. When we ran `kalshi research context` on this market AFTER Exa was live, it immediately surfaced:

> "The Hoosiers have a clear edge, having already beaten the Ducks 30-20 in their previous matchup."

**Exa would have caught this.** The system wasn't broken - it was incomplete.

### The Silver Lining

This $17.76 loss is:
- **Tuition** for learning how Kalshi works
- **Data** for improving the system
- **Documented friction** that will prevent future losses
- **Proof that Exa integration works** (when it's actually used)

> "We're paying money into education... This is good data."

---

## Strategic Insights: Information Arbitrage Framework (2026-01-09)

**Status:** 📝 **DESIGN PRINCIPLES** - Informs [DEBT-014](DEBT-014-friction-residuals.md) Items 2-4.

### Insight 1: New Markets = Maximum Edge

The best information arbitrage exists when:
- Markets are **brand new** (crowd hasn't priced in information yet)
- We have **domain knowledge** the market hasn't absorbed
- The close date is far enough for resolution uncertainty

**System Requirement:**
- Alert system for newly opened markets
- Filter by categories we have domain knowledge in (AI, politics, tech)
- Surface markets where we can research faster than the crowd prices

### Insight 2: Always Consider Both Sides (Adversarial Forcing)

**The Problem:**
If user prompts "Is X a good bet?", Claude only considers the bull case. This creates confirmation bias.

**The Solution:**
FORCE both bull AND bear research on EVERY recommendation:

```text
WRONG: "User asks about X" → Claude researches X → "Yes, X looks good"
RIGHT: "User asks about X" → Claude researches BOTH sides → "Bull case: ... Bear case: ..." → Recommendation based on weight of evidence
```

**System Requirement:**
- Every thesis MUST have bull_case AND bear_case populated
- Before any recommendation, surface the 3 strongest counter-arguments
- Refuse to recommend if counter-evidence is stronger than supporting evidence

### Insight 3: Bet When Evidence is Lopsided (Not Just "Edge")

**The Problem:**
We were looking for "edge" (your probability vs market probability). But edge alone isn't enough if the evidence is uncertain.

**The Solution:**
Only recommend when:
1. We have clear, current information (via Exa research)
2. The evidence strongly favors one direction
3. The market hasn't absorbed this information yet

**Signal Strength Tiers:**

| Tier | Evidence Quality | Recommendation |
|------|------------------|----------------|
| **Strong** | Multiple recent sources confirm thesis, no counter-evidence | Recommend bet |
| **Moderate** | Some supporting evidence, some counter | Surface both, let user decide |
| **Weak** | Training data only, no current research | REFUSE to recommend |
| **Disqualified** | Counter-evidence stronger than thesis | Recommend AGAINST or refuse |

### Insight 4: Alert System for New Market Opportunities

**What We Need:**

1. **New Market Scanner** - Detect markets opened in last 24-48 hours
2. **Domain Filter** - Focus on categories with edge potential (AI, politics, economics)
3. **Quick Research** - Run Exa on new markets immediately
4. **Information Asymmetry Check** - Do we know something the market hasn't priced?

**Proposed CLI Command:**

```bash
# Scan for new markets with quick research
kalshi scan new-markets --hours 24 --categories politics,ai,tech --research
```

### Implementation Checklist (For Skills/Prompts)

Add to `.claude/skills/kalshi-cli/` and mirrors:

```markdown
## Pre-Bet Research Protocol

Before ANY bet recommendation:

1. [ ] Run `kalshi research context <TICKER>` to get current news
2. [ ] Identify 3 strongest BULL arguments
3. [ ] Identify 3 strongest BEAR arguments
4. [ ] Check: Is evidence lopsided or balanced?
5. [ ] Check: Is this based on research or training data?
6. [ ] If sports/breaking news with no live data: REFUSE to recommend
7. [ ] If evidence is balanced: Surface both sides, let user decide
8. [ ] If evidence is lopsided: Recommend direction evidence supports

## New Market Opportunity Protocol

Best edge exists on new markets. Check:

1. [ ] When was market created? (newer = less efficient)
2. [ ] Do we have domain knowledge here?
3. [ ] Has the market absorbed obvious information?
4. [ ] Can we research faster than crowd prices?
```

### Key Principle

> **"We should bet when we clearly have information that fairly heavily favors us, when the market hasn't decided yet."**

This means:
- New markets (crowd hasn't priced in)
- Clear evidence in one direction (not 50/50)
- We've done the research (not vibes)

---
