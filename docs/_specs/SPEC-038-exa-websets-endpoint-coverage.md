# SPEC-038: Exa Websets API Coverage (Monitoring + Alerts Foundation)

**Status:** Draft
**Priority:** P2 (Future automation + monitoring; not required for core CLI today)
**Created:** 2026-01-12
**Owner:** Solo
**Related:** `docs/_specs/SPEC-030-exa-endpoint-strategy.md`, `docs/_future/FUTURE-001-exa-research-agent.md`

---

## Summary

Exa “Search API” (SSOT: `exa-openapi-spec.yaml`) is already fully implemented and golden-validated in our codebase.

Exa also publishes a separate **Websets API** (SSOT: `exa-websets-spec.yaml`) for:

- long-running monitored searches,
- webhooks/events,
- building structured “web sets” of sources/items with enrichment.

These capabilities align with future plans:

- continuous research pipelines,
- “new market alerts” and scheduled scans,
- more reproducible, stateful research outputs.

This spec defines a bounded, testable plan to add Websets support **without** destabilizing the current system.

---

## SSOT

1. Websets OpenAPI spec: `https://raw.githubusercontent.com/exa-labs/openapi-spec/refs/heads/master/exa-websets-spec.yaml`
2. Search OpenAPI spec: `https://raw.githubusercontent.com/exa-labs/openapi-spec/refs/heads/master/exa-openapi-spec.yaml`
3. Local vendor reference: `docs/_vendor-docs/exa-api-reference.md`

---

## Current State

Implemented + golden-validated (Search API):

- `POST /search`
- `POST /contents`
- `POST /findSimilar`
- `POST /answer`
- `POST /research/v1` + `GET /research/v1/{researchId}`

No Websets endpoints are implemented in `src/kalshi_research/exa/` today.

---

## Scope (Minimal, High-Value Websets Subset)

Websets OpenAPI includes 23 paths under `/v0/...`. We will not implement all at once.

### Phase 1 (P2): Core Webset lifecycle + items/searches

Implement enough to:
- create a webset,
- add searches,
- list items,
- cancel long-running jobs safely.

Candidate endpoints:

- `POST /v0/websets`
- `POST /v0/websets/preview` (optional, debug UX)
- `GET /v0/websets/{id}`
- `POST /v0/websets/{id}/cancel`
- `GET /v0/websets/{webset}/items`
- `GET /v0/websets/{webset}/items/{id}`
- `POST /v0/websets/{webset}/searches`
- `GET /v0/websets/{webset}/searches/{id}`
- `POST /v0/websets/{webset}/searches/{id}/cancel`

### Phase 2 (P2/P3): Monitors + runs (alerts foundation)

Implement:
- `POST /v0/monitors`
- `GET /v0/monitors/{id}`
- `GET /v0/monitors/{monitor}/runs`
- `GET /v0/monitors/{monitor}/runs/{id}`

### Phase 3 (P3): Webhooks + events

Implement:
- `POST /v0/webhooks`
- `GET /v0/webhooks/{id}`
- `GET /v0/webhooks/{id}/attempts`
- `GET /v0/events` / `GET /v0/events/{id}`

---

## Implementation Requirements (SSOT-grade)

### 1) New client module

- Add `src/kalshi_research/exa/websets_client.py` (or `exa/websets/` package) that mirrors the existing `ExaClient`
  design:
  - single `_request()` helper with retries,
  - Pydantic request/response models,
  - explicit base URL and auth.

### 2) Golden fixtures for Websets

Add new fixtures under:

`tests/fixtures/golden/exa_websets/`

Recording approach:
- Add `scripts/record_exa_websets_responses.py` which:
  - creates a small webset and immediately cancels if needed,
  - records raw responses as fixtures with `_metadata`,
  - writes an `_recording_summary.json`.

Because Websets endpoints are stateful, recording MUST:
- use deterministic names (prefix like `ssot-fixture-...`),
- clean up resources at the end of the run,
- include a `--yes` flag for any write operations.

### 3) SSOT validator integration

Update `scripts/validate_models_against_golden.py` with a new mapping section:

- `exa_websets/<fixture>.json -> <WebsetsModel>`

### 4) Tests

- Add `tests/unit/exa/test_websets_golden_fixtures.py` to validate fixtures parse.
- Add `tests/unit/exa/test_websets_client.py` using `respx` and golden fixtures for responses (no inline dicts).

---

## Acceptance Criteria

- [x] Websets client + models exist for Phase 1 endpoints.
- [x] Websets fixtures recorded and stored under `tests/fixtures/golden/exa_websets/`.
- [x] `scripts/validate_models_against_golden.py` validates Websets fixtures.
- [x] Unit tests use golden fixtures for all success-path mocks.
- [x] No Websets logic is required by default CLI flows (kept behind explicit commands/flags).
