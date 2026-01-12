# DEBT-016: Automate Fixture Drift Detection + Weekly Re-Recording

**Priority:** P2 (Important for long-term reliability)
**Status:** Open (Proposed)
**Created:** 2026-01-12
**Related:** BUG-071, BUG-072, BUG-073

---

## Summary

We currently rely on **manual script execution** and **one-time JSON fixture recording** with **console reports**. This is brittle: fixtures drift silently, regressions sneak in, and "golden data" becomes untrusted.

**Status update (2026-01-12):**
- ✅ CI now runs `scripts/validate_models_against_golden.py` on PRs (SSOT mismatch fails fast)
- 🔴 Remaining: automated re-recording + drift PRs + (optional) JSON Schema validation

We want to evolve to a "gold standard" workflow where:

- **Weekly scheduled CI job** re-records fixtures and raises drift as a PR
- Fixtures are **validated against JSON Schema** (AJV) so format changes fail fast
- **GitHub PR checks fail on drift**, so regressions can't merge quietly
- Fixtures are **versioned with timestamps** so we can audit when/why baseline changed

---

## Current vs Gold Standard

| CURRENT (Good) | GOLD STANDARD (Aspirational) |
|----------------|------------------------------|
| Manual script execution | CI job re-records weekly |
| JSON fixtures only | JSON Schema validation (AJV) |
| Console reports | GitHub PR checks fail on drift |
| One-time recording | Versioned fixtures with timestamps |

---

## Problem Statement

1. **No automated drift detection:** If Kalshi API changes, we only find out when prod breaks.
2. **No structural guarantees:** JSON fixtures may silently change shape (missing keys, new fields, wrong types).
3. **No baseline audit trail:** When fixtures do change, we don't capture *when* and *why* consistently.
4. **Manual burden:** Re-recording and verifying fixtures is easy to skip and hard to trust.

---

## Goals

- Make fixture drift **visible and enforceable** via PR checks
- Prevent invalid fixture shapes with **JSON Schema validation**
- Track fixture evolution with **timestamped/versioned** baselines
- Reduce human effort: weekly automation catches drift early

---

## Non-Goals

- Re-architecting the entire test suite
- Solving flaky upstream dependencies globally
- Backfilling perfect historical fixture provenance (start from "now")

---

## Proposed Solution

### 1. Standardize Fixture Recording

Canonical commands:
```bash
# Record all fixtures
uv run python scripts/record_api_responses.py
uv run python scripts/record_exa_responses.py

# Validate models against fixtures
uv run python scripts/validate_models_against_golden.py
```

Requirements:
- Stable ordering for arrays where possible
- Stable key ordering/formatting (use a formatter or stable stringify)
- Sanitize ephemeral fields (user_id, balance) via `sanitize_golden_fixtures.py`
- **Trading fixtures are special:** create/cancel/amend have side effects, so `record_api_responses.py` does not
  re-record them against production. For drift detection, either (a) record trading fixtures against demo, or (b) treat
  OpenAPI as SSOT for trading endpoints and exclude them from automated re-record jobs.

### 2. JSON Schema Validation

Add schemas under:
```text
schemas/fixtures/
├── market.schema.json
├── order.schema.json
├── fill.schema.json
└── ...
```

Add a validator script:
```bash
uv run python scripts/validate_fixture_schemas.py
```

Rules:
- PRs fail if fixtures do not validate
- Scheduled job fails if newly recorded fixtures do not validate

### 3. Drift Detection (PR Check)

Add a CI step that:
1. Re-records fixtures to a temp location
2. Diffs temp fixtures vs current baseline
3. Fails the PR if there is drift (non-empty diff)

Output should include:
- Concise summary (which fixtures changed)
- Path to full diff artifact (attach as CI artifact)

### 4. Weekly CI Re-record + "Drift PR"

Add a scheduled GitHub Action (weekly) that:
1. Runs `record_api_responses.py` + `validate_models_against_golden.py`
2. If there's drift, creates a PR with the updated fixtures
   - PR title: `chore(fixtures): weekly rerecord 2026-01-12`
   - Includes a CI report in the PR body (summary + notable diffs)

Implementation:
- Use `peter-evans/create-pull-request` action
- Needs repo write permissions (GITHUB_TOKEN)
- Requires API credentials stored as GitHub Secrets

---

## Fixture Versioning Strategy

### Option A (Recommended): Timestamped Snapshots + "latest" Pointer

```text
tests/fixtures/golden/
├── snapshots/
│   ├── 2026-01-12/
│   │   ├── market_single_response.json
│   │   └── ...
│   └── 2026-01-19/
│       └── ...
├── LATEST  # text file: "2026-01-12"
└── _recording_summary.json
```

Pros:
- Auditable history of baseline evolution
- Easy to compare two snapshots

Cons:
- Repo grows over time (mitigate via pruning: keep last N snapshots)

### Option B: Single Baseline + Git History Only

```text
tests/fixtures/golden/
├── market_single_response.json
└── ...
```

Pros:
- Minimal repo growth

Cons:
- Harder to inspect "when did it change?" without extra metadata

**Decision:** Start with Option A unless repo size becomes a problem.

---

## GitHub Actions Plan

### PR Workflow: `.github/workflows/fixtures-validate.yml`

```yaml
name: Validate Fixtures
on: [pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync

      # Validate existing fixtures against models
      - run: uv run python scripts/validate_models_against_golden.py

      # Check for drift (optional - requires API creds)
      # - run: uv run python scripts/record_api_responses.py --dry-run
      # - run: diff -r tests/fixtures/golden/ /tmp/fixtures-new/
```

### Scheduled Workflow: `.github/workflows/fixtures-weekly.yml`

```yaml
name: Weekly Fixture Re-record
on:
  schedule:
    - cron: '0 6 * * 1'  # Every Monday 6am UTC
  workflow_dispatch:

jobs:
  rerecord:
    permissions:
      contents: write
      pull-requests: write
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync

      - name: Record API responses
        env:
          KALSHI_KEY_ID: ${{ secrets.KALSHI_KEY_ID }}
          # Prefer base64 to avoid filesystem key management in CI.
          # See: `KalshiClient(..., private_key_b64=...)`
          KALSHI_PRIVATE_KEY_B64: ${{ secrets.KALSHI_PRIVATE_KEY_B64 }}
          KALSHI_ENVIRONMENT: prod
        # Non-interactive: prefer a dedicated flag rather than piping stdin.
        run: uv run python scripts/record_api_responses.py --env prod --yes

      - name: Sanitize fixtures
        run: uv run python scripts/sanitize_golden_fixtures.py

      - name: Validate models
        run: uv run python scripts/validate_models_against_golden.py

      - name: Create PR if drift detected
        uses: peter-evans/create-pull-request@v6
        with:
          commit-message: 'chore(fixtures): weekly rerecord'
          title: 'chore(fixtures): weekly rerecord ${{ github.run_id }}'
          body: |
            Automated fixture re-recording from production API.

            Review changes carefully - any drift may indicate API changes.
          branch: fixtures/weekly-rerecord-${{ github.run_id }}
          delete-branch: true
```

---

## Risks / Failure Modes

| Risk | Mitigation |
|------|------------|
| Flaky recording (network variance) | Retry policy with caps; fail with clear logs |
| Noisy diffs from nondeterminism | Normalize ephemeral fields; stable sorting |
| Repo bloat from snapshots | Prune old snapshots (keep last N) |
| CI write permissions issues | Drift PR only on default branch schedule |
| API credentials exposure | Use GitHub Secrets; never log credentials |

---

## Implementation Phases

### Phase 0: Document + Decide (THIS DEBT)
- [x] Align on versioning strategy (Option A vs B)
- [x] Document canonical commands & directory layout

### Phase 1: Schema Validation
- [ ] Add JSON Schema files for each fixture type
- [ ] Add `scripts/validate_fixture_schemas.py`
- [ ] Wire into PR CI

### Phase 2: Drift Check on PRs
- [ ] Add `--output-dir` flag to `record_api_responses.py`
- [ ] Add diff comparison step in CI
- [ ] Fail PR on drift + upload diff artifact

### Phase 3: Weekly Re-record + PR Automation
- [ ] Add scheduled GitHub Action workflow
- [ ] Configure GitHub Secrets for API credentials
- [ ] Auto-open PR on drift

---

## Acceptance Criteria

- [ ] PRs fail when fixtures do not validate against JSON Schema
- [ ] PRs fail when drift is detected vs baseline
- [ ] Weekly scheduled job runs successfully end-to-end
- [ ] Weekly job opens a PR when drift occurs (with clear summary)
- [ ] Fixtures are stored with timestamps (or explicit versioning)
- [ ] Drift output is readable and actionable

---

## Related

- **BUG-071**: Mocked Tests Hide API Reality (parent issue)
- **BUG-072**: API SSOT Findings
- **BUG-073**: Vendor Docs Inaccuracies
- **scripts/record_api_responses.py**: Current recording script
- **scripts/validate_models_against_golden.py**: Current validation script
- **scripts/sanitize_golden_fixtures.py**: Sanitization script
