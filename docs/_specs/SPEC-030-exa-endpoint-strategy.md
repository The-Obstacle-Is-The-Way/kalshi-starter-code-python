# SPEC-030: Exa Endpoint Strategy (Cost-Bounded, Verifiable Research)

**Status:** Draft
**Priority:** P1 (Research Quality + Cost Control)
**Created:** 2026-01-10
**Owner:** Solo
**Effort:** ~1–3 days

---

## Summary

Standardize how the platform uses Exa endpoints (`/search`, `/contents`, `/findSimilar`, `/answer`, `/research`)
so that:

- the *default* path is cheap and fast,
- “deep” paths are explicit and gated,
- outputs are citation-forward and verifiable (minimize hallucination risk),
- caching is consistent and cost tracking is observable.

SSOT for Exa endpoint behavior: `../_vendor-docs/exa-api-reference.md`

---

## Goals

1. **One coherent policy** for choosing Exa endpoints based on task type + budget.
2. **Deterministic defaults** for CLI research commands (bounded calls, bounded result count).
3. **Citation-first outputs** (URLs + domains + timestamps) so humans can audit quickly.
4. **Cost controls**:
   - per-command USD budget
   - predictable request count
5. **Optionally verifiable quotes** (lightweight “trust but verify”).

---

## Non-Goals

- No “agentic” Exa orchestration beyond the Exa `/research` endpoint.
- No new ML sentiment models.
- No permanent storage of every Exa response (news pipeline already persists what it needs).

---

## Current State (SSOT)

### Implemented Exa client capabilities

`ExaClient` supports:

- `search(...)`
- `search_and_contents(...)`
- `get_contents(...)`
- `find_similar(...)`
- `answer(...)`
- `create_research_task(...)` + `wait_for_research(...)`

SSOT: `src/kalshi_research/exa/client.py`

### Existing usage patterns

- Market context research uses **Search** (news + research paper categories) with caching
  (SSOT: `src/kalshi_research/research/context.py`).
- Topic research uses **Answer + SearchAndContents** with caching
  (SSOT: `src/kalshi_research/research/topic.py`).
- News collector uses **SearchAndContents** and persists results in SQLite
  (SSOT: `src/kalshi_research/news/collector.py`).

### Observed gaps

- We do not use **Find Similar** or **Research** endpoints in any user-facing flow yet.
- There is no explicit “budget” per CLI command; cost is only reported after the fact.
- “Answer” is helpful but can hallucinate; we currently trust citations without verification.

---

## Principles (First Principles)

1. **Search is retrieval; Answer/Research is synthesis.**
   - Prefer retrieval-first for transparency and auditability.
2. **Never trust synthesis without citations.**
   - Answer/Research outputs must include URLs; otherwise treat as “non-authoritative”.
3. **Budget is a feature.**
   - If users can’t predict cost, they won’t run it at scale.
4. **Determinism beats cleverness.**
   - Default queries should be small, stable, and cache-friendly.

---

## Proposed “Endpoint Selection Policy”

Define a small policy module used by CLI and future code:

`ExaPolicy(mode, budget, recency, domains, max_results) -> ExaPlan`

### Modes

| Mode | Intended Use | Endpoints | Default Budget |
|---|---|---|---|
| `fast` | quick context, low stakes | `/search` or `/search`+contents | $0.01–$0.05 |
| `standard` | normal thesis work | `/search_and_contents` + optional `/answer` | $0.05–$0.25 |
| `deep` | high-EV or ambiguous markets | `/research` (+ follow-up `/contents`) | $0.25–$2.00 |

### Decision tree (deterministic)

1. **Need sources + snippets?** Use `/search` with `highlights=True`, `text=False`.
2. **Need readable article text for extraction?** Use `/search_and_contents` or `/contents` for top URLs.
3. **Need a short summary with citations?** Use `/answer` *only after* retrieval, and only if citations exist.
4. **Need a multi-hop report (lots of sub-questions)?** Use `/research` only in `deep` mode or when explicitly
   requested.

SSOT for endpoint semantics: `../_vendor-docs/exa-api-reference.md`

---

## Citation Verification (Optional, but recommended)

When we show a quote/highlight from Exa, we can optionally verify it:

1. Take the citation URL.
2. Fetch `contents` (clean text) for that URL.
3. Confirm the quoted substring appears in the returned text.

Verification is:

- **On by default** only for `deep` mode (low volume, higher budget).
- **Off by default** for `fast`/`standard` (to avoid doubling cost).

If verification fails:

- mark the citation as “unverified” in output,
- do not include the quote text (only include URL + title).

---

## CLI Surface Changes (Proposed)

### 1) `kalshi research context`

Add explicit policy flags:

- `--mode fast|standard|deep` (default: `standard`)
- `--budget-usd FLOAT` (default depends on mode)
- `--verify-citations/--no-verify-citations` (default: mode-based)
- `--include-domains a.com,b.com` / `--exclude-domains ...`
- `--max-news INT` / `--max-papers INT` (already exists in spirit; unify naming)

### 2) `kalshi research topic`

Current behavior is Answer + SearchAndContents.

Adjust to:

- Run retrieval first (SearchAndContents).
- Run Answer second, with a prompt that includes retrieved URLs and asks Exa Answer to cite *from those*.
  - If Exa Answer can’t be constrained that way, keep current behavior but require citations and mark
    “unverified” until verified via contents.

Add:

- `--mode`
- `--budget-usd`
- `--no-answer` (retrieve-only mode)

### 3) New: `kalshi research exa ...` (raw, optional)

Expose raw Exa operations for debugging without writing ad-hoc scripts:

- `kalshi research exa search "query" ...`
- `kalshi research exa answer "query" ...`
- `kalshi research exa research "query" ...`

These commands should output JSON only (tooling-friendly).

---

## Implementation Plan

### Phase 1: Policy + budgets

1. Add `ExaPolicy` and `ExaBudget` types (pure Python, no network).
2. Thread `mode/budget` flags through `research context` and `research topic`.
3. Enforce budgets:
   - track cumulative `cost_dollars.total` (SSOT: Exa responses include `costDollars`)
   - stop early and warn when budget would be exceeded
4. Standardize caching keys:
   - include mode + all request params in the cache key (already mostly true)
   - consider day-level bucketing for “news” queries (already used in context research)

### Phase 2: Find Similar + Deep Research (gated)

1. Add optional “expand” step using `/findSimilar`:
   - seed with top 1–3 URLs from Search
   - fetch similar URLs to diversify sources (avoid single-domain lock-in)
2. Add `/research` support behind `--mode deep`:
   - create task, poll status, return structured report
   - always return citations/URLs

### Phase 3: Optional citation verification

1. Implement `verify_citation(url, quote) -> bool` using `/contents`.
2. Enable by default in deep mode.

---

## Acceptance Criteria

- Every Exa-powered CLI command has explicit `--mode` and `--budget-usd` controls.
- Default behavior is cost-bounded and produces citations.
- Deep mode uses `/research` only when requested (explicitly or by mode), never silently.
- Caching remains effective (no accidental cache busting from unstable params).
- Unit tests cover:
  - budget enforcement logic (no network; use mocked responses)
  - cache key stability
  - citation verification logic (respx + fixture responses)
