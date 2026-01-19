"""Rule-based verification for agent analysis outputs.

Verification is intentionally non-agentic by default:
- Schema validation via Pydantic catches gross failures
- Rule-based checks enforce domain constraints
- No LLM calls in Phase 1
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .schemas import AnalysisResult, VerificationReport

from .schemas import VerificationReport as VR


def verify_analysis(analysis: AnalysisResult) -> VerificationReport:
    """Run rule-based verification on an AnalysisResult.

    Checks:
    - predicted_prob range (0..100, enforced by schema)
    - sources are unique and subset of factor URLs
    - minimum citation count for medium/high confidence
    - reasoning length bounds
    - consistency checks (predicted_prob not always identical to market_prob)

    Args:
        analysis: The analysis result to verify

    Returns:
        VerificationReport with pass/fail status and issues list
    """
    issues: list[str] = []
    checked_sources: list[str] = []

    # Check 1: Schema validation (already done by Pydantic, but verify in-bounds)
    if not (0 <= analysis.predicted_prob <= 100):
        issues.append(f"predicted_prob out of range: {analysis.predicted_prob} (expected 0..100)")

    if not (0.0 <= analysis.market_prob <= 1.0):
        issues.append(f"market_prob out of range: {analysis.market_prob} (expected 0..1)")

    # Check 2: Confidence level must be valid
    valid_confidence = {"low", "medium", "high"}
    if analysis.confidence not in valid_confidence:
        issues.append(
            f"Invalid confidence level: {analysis.confidence!r} (expected: {valid_confidence})"
        )

    # Check 3: Sources should be unique
    checked_sources.extend(analysis.sources)
    if len(analysis.sources) != len(set(analysis.sources)):
        issues.append("Duplicate URLs found in sources list")

    # Check 4: All sources should appear in factor URLs
    factor_urls = {f.source_url for f in analysis.factors}
    for url in analysis.sources:
        if url not in factor_urls:
            issues.append(f"Source URL not found in any factor: {url}")

    # Check 5: Minimum citation count for medium/high confidence
    min_citations = {"low": 0, "medium": 2, "high": 3}
    required = min_citations.get(analysis.confidence, 0)
    if len(analysis.sources) < required:
        issues.append(
            f"Insufficient citations for {analysis.confidence!r} confidence: "
            f"found {len(analysis.sources)}, expected >= {required}"
        )

    # Check 6: Reasoning length bounds (prevent huge dumps or empty reasoning)
    reasoning_len = len(analysis.reasoning)
    if reasoning_len < 50:
        issues.append(f"Reasoning too short: {reasoning_len} chars (minimum 50)")
    if reasoning_len > 2000:
        issues.append(f"Reasoning too long: {reasoning_len} chars (maximum 2000)")

    # Check 7: Consistency check - predicted_prob should differ meaningfully from market
    # This prevents "always return market price" gaming.
    # Use round() instead of int() to avoid false positives at boundaries (e.g., 99.9 → 99).
    market_prob_pct = round(analysis.market_prob * 100)
    if analysis.predicted_prob == market_prob_pct and analysis.confidence == "high":
        issues.append(
            "Predicted probability identical to market with high confidence "
            "(possible overfitting or lack of signal)"
        )

    # Check 8: Impact values must be valid if present
    valid_impacts = {"up", "down", "unclear", None}
    for i, factor in enumerate(analysis.factors):
        if factor.impact not in valid_impacts:
            issues.append(
                f"Factor {i}: invalid impact value {factor.impact!r} (expected: {valid_impacts})"
            )

    # Determine pass/fail and escalation suggestion
    passed = len(issues) == 0
    suggested_escalation = not passed  # Suggest escalation if any rules failed

    return VR(
        passed=passed,
        issues=issues,
        checked_sources=checked_sources,
        suggested_escalation=suggested_escalation,
    )
