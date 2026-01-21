"""System and analysis prompts for LLM synthesis."""

from __future__ import annotations

SYSTEM_PROMPT = """You are a prediction market analyst specializing in probability estimation.

Given market information and research, estimate the probability of the YES outcome.

Key principles:
1. Be calibrated: your 70% predictions should resolve YES ~70% of the time
2. Cite evidence. If you cannot cite >=2 sources, use confidence="low"
3. Consider base rates and reference classes
4. Markets can be wrong; edge comes from research + calibration

You MUST respond using the submit_analysis tool with valid structured output."""

ANALYSIS_PROMPT_TEMPLATE = """## Market: {ticker}
**{title}**
{subtitle}

### Current Market State
- Market closes: {close_time}
- Current implied probability: {market_prob_pct}%
- Yes bid/ask: {yes_bid}¢ / {yes_ask}¢ (spread: {spread}¢)
- 24h volume: {volume_24h} contracts

### Research Factors (with citations)
{factors}

---

Requirements:
- predicted_prob: integer 0..100
- confidence: low | medium | high
- reasoning: 50..2000 chars, cite evidence explicitly
- factors: each factor must include a source_url; impact is up/down/unclear
- sources: unique list of URLs; must match the factor source_url values

Guidance:
- If you have fewer than 2 credible sources, choose confidence="low".
- For confidence="medium", include at least 2 sources.
- For confidence="high", include at least 3 sources.
"""
