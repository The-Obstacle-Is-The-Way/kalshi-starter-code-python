# SPEC-033: Exa Research Agent (Cost-Bounded, Reproducible)

**Status:** Draft
**Priority:** P1 (High leverage research automation)
**Created:** 2026-01-10
**Owner:** Solo
**Effort:** ~2–5 days (Phase 1), ~1 week (Phase 2)

---

## Summary

Promote `docs/_future/FUTURE-001-exa-research-agent.md` into an implementation-ready spec that:

- provides a **single research agent** (no multi-agent) that orchestrates Exa calls,
- produces structured, citation-first outputs for downstream analysis agents (SPEC-032),
- enforces **budget limits** and supports deterministic replay (cache keys + plan serialization),
- integrates with existing Exa tooling already in this repo (SSOT: `src/kalshi_research/exa/client.py`).

This is not “LLM agent magic”; it is a **deterministic planner + bounded tool calls**.

---

## Goals

1. A `ResearchAgent` that can run a **multi-step Exa workflow** for a given market ticker.
2. Outputs a structured `ResearchSummary` compatible with SPEC-032.
3. Enforces a per-run **USD budget**, stopping early with partial results rather than failing.
4. Supports **depth levels** (quick/standard/deep) with predictable request counts.
5. Clear CLI interface with JSON output suitable for automation.

---

## Non-Goals

- No autonomous trading.
- No “LLM decides what tools to call” planning in Phase 1.
- No requirement to use Exa MCP server (MCP remains a complementary interactive tool).

---

## SSOT

- Exa endpoint semantics and cost fields: `docs/_vendor-docs/exa-api-reference.md`
- Exa client in code: `src/kalshi_research/exa/client.py`
- Existing Exa research utilities (can be reused): `src/kalshi_research/research/context.py`
- Endpoint policy spec: `docs/_specs/SPEC-030-exa-endpoint-strategy.md`

---

## Design

### 1) Deterministic planning (no LLM planner)

Define a deterministic plan builder:

- input: `Market` (from `KalshiPublicClient.get_market`)
- output: `ResearchPlan` (serializable)

Depth levels map to fixed steps:

| Depth | Exa calls | Includes |
|---|---:|---|
| `quick` | ~2–4 | 1–2 searches + minimal summarization |
| `standard` | ~4–8 | news + background + (optional) expert search |
| `deep` | ~6–12 | standard + Exa `/research` task (async) |

The plan is deterministic given:

- market title + ticker
- depth
- recency window
- include/exclude domains

### 2) Execution with budget enforcement

Track cost via Exa responses:

- `SearchResponse.cost_dollars.total`
- `AnswerResponse.cost_dollars.total`
- `ResearchTask.cost_dollars.total` (when completed)

Stop early when the next step would exceed `budget_usd`:

- mark remaining steps as skipped
- produce partial `ResearchSummary` with an explicit `budget_exhausted=True` indicator (schema field)

### 3) Output schema

The agent outputs:

- `ResearchSummary` (SPEC-032) plus optional debug details:
  - phases/steps executed
  - per-step costs
  - query list

No free-form prose reports are required for machine use; Markdown output is an optional formatter.

### 4) Optional citation verification (Phase 2)

For `deep` depth:

- verify that key quoted “highlights” exist in `/contents` text
- if verification fails, keep URL but drop the quote

This follows SPEC-030’s “trust but verify” policy.

---

## Module Layout

```txt
src/kalshi_research/agent/
  research_agent.py         # planning + execution (this spec)
  research_models.py        # Pydantic models for plan/result
  reporter.py               # Markdown formatter (optional)
```

Prefer Pydantic models (not dataclasses) for:

- stable JSON output
- validation
- future compatibility with structured LLM outputs (if we later synthesize factors)

---

## CLI Surface

Add `kalshi agent research`:

```bash
uv run kalshi agent research TICKER \
  --depth quick|standard|deep \
  --budget-usd 0.50 \
  --json \
  --output report.json
```

CLI requirements:

- JSON output is default (single object).
- `--output` writes to file.
- Progress output only when `--json` is not set.

---

## Testing

Unit tests (no network):

- plan creation per depth (step counts + expected endpoint types)
- budget enforcement (stop before exceeding)
- stable serialization/deserialization of `ResearchPlan`

Integration tests (optional, require EXA_API_KEY):

- smoke test `agent research` returns valid JSON and non-zero cost

---

## Implementation Plan

### Phase 1 (core agent + CLI)

1. Implement plan builder (deterministic).
2. Implement step executor using existing `ExaClient`.
3. Map results into `ResearchSummary` (factors derived from highlights + URLs).
4. Add `kalshi agent research` command.

### Phase 2 (verification + richer synthesis)

1. Optional citation verification for deep runs.
2. Optional structured factor extraction via a synthesis model (separate from Exa Answer).

---

## Acceptance Criteria

- `kalshi agent research TICKER --json` returns valid JSON even when Exa fails (empty results, `total_cost_usd=0.0`).
- Budget enforcement is deterministic and never exceeds the requested budget by more than a single step’s cost.
- Outputs include URLs for all factors; no factor exists without a source URL.

---

## References

- Backlog seed: `docs/_future/FUTURE-001-exa-research-agent.md`
- Exa endpoint SSOT: `docs/_vendor-docs/exa-api-reference.md`
- Exa policy: `docs/_specs/SPEC-030-exa-endpoint-strategy.md`
- Agent orchestration: `docs/_specs/SPEC-032-agent-system-orchestration.md`
