# Thesis System (Explanation)

The thesis system is the core differentiator of this research platform. Instead of making one-off predictions and
forgetting them, you create structured **theses** that track your reasoning, predictions, and outcomes over time.

## Why Track Theses?

Most prediction market participants:

1. Look at a market
2. Form an opinion ("I think this is underpriced")
3. Maybe bet on it
4. Forget about it
5. Never learn if they were right

This makes it impossible to improve. You can't fix what you don't measure.

The thesis system forces you to:

- **Commit to a probability** before you see the outcome
- **Document your reasoning** (bull case, bear case, key assumptions)
- **Define invalidation criteria** (what would prove you wrong?)
- **Track resolution** (did you get it right?)
- **Measure calibration** (are your 70% predictions hitting 70% of the time?)

## Thesis Lifecycle

```text
DRAFT ──► ACTIVE ──► RESOLVED
              │
              └──► ABANDONED (with reason)
```

- **Draft**: Initial creation, still refining
- **Active**: You've committed to this prediction
- **Resolved**: Market settled, outcome recorded
- **Abandoned**: You changed your mind (and documented why)

## Thesis Data Model

Each thesis captures:

```python
@dataclass(frozen=True)
class ThesisEvidence:
    url: str
    title: str
    source_domain: str
    published_date: datetime | None
    snippet: str
    supports: str  # bull, bear, neutral
    relevance_score: float
    added_at: datetime = field(default_factory=lambda: datetime.now(UTC))

@dataclass
class Thesis:
    id: str                      # Unique identifier
    title: str                   # Human-readable name
    market_tickers: list[str]    # Which Kalshi markets this covers

    # Your predictions
    your_probability: float      # 0-1, YOUR estimate
    market_probability: float    # 0-1, what Kalshi said at creation time
    confidence: float            # 0-1, how sure are you?

    # Reasoning (the important part!)
    bull_case: str               # Why it might be YES
    bear_case: str               # Why it might be NO
    key_assumptions: list[str]   # What must be true for your thesis?
    invalidation_criteria: list[str]  # What would prove you wrong?

    # Tracking
    status: ThesisStatus = ThesisStatus.DRAFT
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    resolved_at: datetime | None = None
    actual_outcome: str | None = None   # "yes", "no", or "void"
    updates: list[dict[str, Any]] = field(default_factory=list)  # Timestamped notes

    # Optional: attached Exa research
    evidence: list[ThesisEvidence] = field(default_factory=list)
    research_summary: str | None = None
    last_research_at: datetime | None = None
```

## Edge Detection

The `edge_size` property tells you how much you disagree with the market:

```python
edge_size = your_probability - market_probability
```

- Positive edge: You think YES is more likely than the market
- Negative edge: You think NO is more likely than the market
- Large absolute edge: Potential opportunity (if you're right)

## Performance Metrics

After resolution, you can compute:

### Brier Score

```python
brier_score = (your_probability - outcome)²
```

Where outcome is 1.0 for YES, 0.0 for NO.

- If `actual_outcome` is `"void"` (or any non-`yes`/`no` value), `brier_score` is `None` and excluded from averages.

- 0.0 = perfect prediction
- 0.25 = equivalent to random guessing
- 1.0 = perfectly wrong

### Was Correct

Simple binary: did your probability correctly predict the direction?

```python
was_correct = (your_probability > 0.5 and outcome == "yes") or
              (your_probability < 0.5 and outcome == "no")
```

If the thesis is unresolved, or resolves as `"void"`, `was_correct` is `None`.

## Storage

Theses are persisted to `data/theses.json` in this format:

```json
{
  "theses": [
    {
      "id": "abc123",
      "title": "Trump wins 2024",
      "market_tickers": ["PRES-2024-TRUMP"],
      "your_probability": 0.65,
      "market_probability": 0.45,
      ...
    }
  ]
}
```

The `ThesisTracker` class handles atomic saves (write to temp file, then rename) to prevent corruption.

## CLI Usage

```bash
# Create a thesis
uv run kalshi research thesis create "My prediction" \
  --markets TICK1,TICK2 \
  --your-prob 0.65 \
  --market-prob 0.55 \
  --confidence 0.8

# Create + attach Exa research evidence (requires EXA_API_KEY)
uv run kalshi research thesis create "My prediction" \
  --markets TICK1 \
  --your-prob 0.65 \
  --market-prob 0.55 \
  --confidence 0.8 \
  --with-research \
  --yes

# List all theses
uv run kalshi research thesis list --full

# View details
uv run kalshi research thesis show <ID_PREFIX>

# View details + linked positions (reads from your local DB)
uv run kalshi research thesis show <ID_PREFIX> --with-positions --db data/kalshi.db

# Resolve when market settles
uv run kalshi research thesis resolve <ID_PREFIX> --outcome yes
```

## Integration with Backtesting

Resolved theses feed into the backtesting system (see `docs/research/backtesting.md`), which calculates:

- What your P&L would have been
- Your win rate
- Aggregate Brier score
- Sharpe ratio

## Key Code

- Thesis model: `src/kalshi_research/research/thesis.py`
- CLI commands: `src/kalshi_research/cli/research.py`
- Storage path: `src/kalshi_research/paths.py` (`DEFAULT_THESES_PATH`)

## See Also

- [Backtesting](backtesting.md) - Simulate P&L from resolved theses
- [Calibration Analysis](calibration-analysis.md) - Measure prediction accuracy
- [Usage: Research](../getting-started/usage.md#research) - CLI commands
