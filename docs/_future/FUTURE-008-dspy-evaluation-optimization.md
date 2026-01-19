# FUTURE-008: DSPy Evaluation & Prompt Optimization

**Status:** Backlog (requires historical prediction data)
**Priority:** Medium-High
**Created:** 2026-01-19
**Blocked By:** Need 100+ resolved predictions with outcomes for optimization
**Owner:** Solo

---

## Summary

Integrate [DSPy](https://dspy.ai/) (Stanford NLP) to enable systematic evaluation and automatic prompt optimization for the LLM synthesizer. DSPy treats LLM pipelines as programs to be compiled and optimized, rather than brittle prompt chains.

**Why DSPy?** The current synthesizer (SPEC-042) uses a hand-crafted prompt. DSPy would:
1. Define custom metrics (calibration, Brier score) to evaluate prediction quality
2. Automatically optimize prompts against historical outcomes
3. Detect and fix error propagation in the research → synthesis → verification pipeline

---

## Compatibility

### Pydantic Integration

DSPy is **fully compatible** with Pydantic:

- [DSPy adapters](https://dspy.ai/learn/programming/adapters/) support Pydantic `BaseModel` as output types
- `ChatAdapter` and `JSONAdapter` work with Pydantic schemas for structured output validation
- [Existing patterns](https://gist.github.com/seanchatmangpt/7e25b66ebffdedba7310d9c90f377463) show DSPy signatures can be created from Pydantic models

Our existing schemas (`AnalysisResult`, `ResearchSummary`, `Factor`) can be reused directly.

### Version Requirements

```toml
# pyproject.toml (when implementing)
[project.optional-dependencies]
dspy = [
    "dspy-ai>=2.5.0",  # Check latest for Pydantic 2.x compatibility
]
```

**Note:** Historical Pydantic version conflicts existed (dspy-ai 2.4.5 required pydantic==2.5.0). Verify compatibility with our current Pydantic version before adding.

---

## Use Case: Synthesizer Calibration

### Current State (SPEC-042)

```
Research (Exa) → Synthesizer (Claude) → Verification (rules)
                      ↑
              Hand-crafted prompt
              No systematic optimization
```

### Future State (with DSPy)

```
Research (Exa) → DSPy Module → Verification
                      ↑
              Auto-optimized prompt
              Trained on historical outcomes
              Calibration metric feedback
```

---

## Implementation Plan

### Phase 1: Data Collection (NOW)

Before DSPy can optimize anything, we need labeled data:

1. Store every `AnalysisResult` prediction in the database
2. Link predictions to market resolutions (when markets close)
3. Calculate Brier scores for each prediction
4. Target: **100+ resolved predictions with outcomes**

**Schema addition:**
```python
class PredictionLog(Base):
    """Historical prediction log for DSPy training."""
    __tablename__ = "prediction_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(50), index=True)
    predicted_prob: Mapped[int]  # 0-100
    market_prob: Mapped[float]   # At prediction time
    confidence: Mapped[str]      # low/medium/high
    reasoning: Mapped[str]
    factors_json: Mapped[str]    # JSON blob
    predicted_at: Mapped[datetime]

    # Filled after resolution
    actual_outcome: Mapped[bool | None]  # True=YES, False=NO
    resolved_at: Mapped[datetime | None]
    brier_score: Mapped[float | None]    # (predicted - actual)^2
```

### Phase 2: DSPy Integration

Once we have training data:

```python
import dspy
from kalshi_research.agent.schemas import AnalysisResult

class ProbabilityEstimate(dspy.Signature):
    """Estimate probability for a prediction market outcome."""
    market_info: str = dspy.InputField(desc="Market title, close time, current price")
    research_factors: str = dspy.InputField(desc="Research factors from Exa")

    probability: int = dspy.OutputField(desc="0-100 probability estimate for YES")
    confidence: str = dspy.OutputField(desc="low, medium, or high")
    reasoning: str = dspy.OutputField(desc="Explanation citing research factors")

class CalibratedSynthesizer(dspy.Module):
    """DSPy module wrapping our synthesizer logic."""

    def __init__(self):
        self.predict = dspy.ChainOfThought(ProbabilityEstimate)

    def forward(self, market_info: str, research_factors: str) -> AnalysisResult:
        result = self.predict(market_info=market_info, research_factors=research_factors)
        return AnalysisResult(
            ticker=...,
            predicted_prob=result.probability,
            confidence=result.confidence,
            reasoning=result.reasoning,
            ...
        )
```

### Phase 3: Optimization

```python
def calibration_metric(example, prediction, trace=None):
    """Brier score-based calibration metric."""
    pred_prob = prediction.probability / 100
    actual = 1.0 if example.actual_outcome else 0.0
    brier = (pred_prob - actual) ** 2
    # Lower Brier = better calibration. DSPy maximizes, so return inverted.
    return 1.0 - brier

# Load historical data
trainset = load_prediction_history()  # PredictionLog records with outcomes

# Optimize
optimizer = dspy.MIPROv2(metric=calibration_metric)
optimized_synthesizer = optimizer.compile(
    CalibratedSynthesizer(),
    trainset=trainset,
)

# Save optimized program
optimized_synthesizer.save("optimized_synthesizer.json")
```

---

## DSPy Optimizers (Reference)

| Optimizer | Best For | How It Works |
|-----------|----------|--------------|
| **MIPROv2** | General optimization | Bootstraps high-scoring traces, teaches model what "good" looks like |
| **SIMBA** | Identifying failures | Samples challenging examples, generates self-improvement rules |
| **GEPA** | Prompt refinement | Reflects on trajectories, proposes prompt improvements |
| **BootstrapFinetune** | Distillation | Converts prompt-based program to finetuned weights |

---

## Evaluation Metrics

### Primary: Brier Score

Standard for probability calibration:
```
Brier = (predicted_probability - actual_outcome)^2
```
- Perfect prediction: 0
- Random (50%): 0.25
- Always wrong: 1.0

### Secondary: Calibration Curve

For N predictions at confidence level C%, approximately C% should resolve YES.

```python
def calibration_error(predictions: list[PredictionLog]) -> float:
    """Expected Calibration Error (ECE)."""
    bins = defaultdict(list)
    for p in predictions:
        bin_idx = p.predicted_prob // 10  # 0-9, 10-19, ..., 90-100
        bins[bin_idx].append(p)

    ece = 0.0
    for bin_idx, preds in bins.items():
        bin_center = (bin_idx * 10 + 5) / 100
        actual_rate = sum(p.actual_outcome for p in preds) / len(preds)
        ece += len(preds) * abs(actual_rate - bin_center)

    return ece / len(predictions)
```

---

## Acceptance Criteria

- [ ] `PredictionLog` table created (Alembic migration)
- [ ] `kalshi agent analyze` stores predictions in DB
- [ ] Script to backfill resolutions from settled markets
- [ ] 100+ predictions with outcomes collected
- [ ] DSPy optional dependency added (`[dspy]` extra)
- [ ] `CalibratedSynthesizer` module implemented
- [ ] MIPROv2 optimization run on training data
- [ ] A/B comparison: original vs optimized Brier scores
- [ ] CLI flag to use optimized synthesizer: `--optimized`

---

## Files to Create/Modify

| File | Action |
|------|--------|
| `src/kalshi_research/data/models.py` | Add `PredictionLog` model |
| `alembic/versions/xxx_add_prediction_log.py` | Migration |
| `src/kalshi_research/agent/prediction_logger.py` | New: log predictions |
| `src/kalshi_research/agent/dspy_synthesizer.py` | New: DSPy module |
| `scripts/optimize_synthesizer.py` | New: run optimization |
| `pyproject.toml` | Add `[dspy]` optional dependency |

---

## References

- [DSPy Official Site](https://dspy.ai/)
- [DSPy GitHub](https://github.com/stanfordnlp/dspy)
- [DSPy Optimizers](https://dspy.ai/learn/optimization/optimizers/)
- [DSPy Metrics](https://dspy.ai/learn/evaluation/metrics/)
- [Human-Aligned LLM Evaluation with DSPy](https://explosion.ai/blog/human-aligned-llm-evaluation-dspy)
- [DSPy + Pydantic Signatures](https://gist.github.com/seanchatmangpt/7e25b66ebffdedba7310d9c90f377463)
- [Pydantic-AI Optimizer Request](https://github.com/pydantic/pydantic-ai/issues/3179)
- [SPEC-042: LLM Synthesizer Implementation](../_specs/SPEC-042-llm-synthesizer-implementation.md)
