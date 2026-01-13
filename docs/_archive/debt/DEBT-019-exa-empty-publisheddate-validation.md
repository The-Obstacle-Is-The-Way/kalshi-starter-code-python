# DEBT-019: Exa Empty `publishedDate` Validation Bug

**Priority:** P2 (Breaks CLI research commands)
**Status:** ✅ Resolved
**Found:** 2026-01-12
**Fixed:** 2026-01-13
**Source:** Live testing of `kalshi research topic` command
**Fixed In:** d2e21ff
**Archived:** 2026-01-13

---

## Summary

The Exa API sometimes returns an empty string `""` for `publishedDate` field in search results. Our Pydantic model expects `datetime | None`, which fails validation when given an empty string.

**Error observed:**
```text
ValidationError: 2 validation errors for SearchResponse
results.9.publishedDate
  Input should be a valid datetime or date, input is too short
  [type=datetime_from_date_parsing, input_value='', input_type=str]
results.10.publishedDate
  Input should be a valid datetime or date, input is too short
  [type=datetime_from_date_parsing, input_value='', input_type=str]
```

---

## Root Cause

**SSOT:** `src/kalshi_research/exa/models/search.py:68`

```python
published_date: datetime | None = Field(default=None, alias="publishedDate")
```

The model expects either:
- A valid ISO 8601 datetime string (e.g., `"2026-01-12T00:00:00.000Z"`)
- `null` / missing field (becomes `None`)

But Exa API sometimes returns:
- `"publishedDate": ""` (empty string)

Pydantic tries to parse `""` as a datetime and fails.

---

## Impact

- `kalshi research topic` fails mid-execution when search results include empty dates
- The Answer portion succeeds (cached separately), but SearchAndContents fails validation
- User sees a traceback instead of clean research output

---

## Fix

Add a Pydantic `field_validator` to coerce empty/whitespace strings to `None`:

```python
from pydantic import field_validator

class SearchResult(BaseModel):
    # ... existing fields ...
    published_date: datetime | None = Field(default=None, alias="publishedDate")

    @field_validator("published_date", mode="before")
    @classmethod
    def coerce_empty_published_date(cls, v: object) -> object:
        if isinstance(v, str) and not v.strip():
            return None
        return v
```

**Files to update:**
- `src/kalshi_research/exa/models/search.py` - `SearchResult`
- `src/kalshi_research/exa/models/answer.py` - `Citation`

---

## Affected Models

| Model | File | Field |
|-------|------|-------|
| `SearchResult` | `exa/models/search.py:68` | `published_date` |
| `Citation` | `exa/models/answer.py:21` | `published_date` |

---

## Test Cases

Add a golden fixture regression case with empty `publishedDate`:

```json
{
  "results": [
    {
      "id": "https://example.com/article",
      "title": "Test Article",
      "url": "https://example.com/article",
      "publishedDate": "",
      "author": null
    }
  ]
}
```

---

## Verification

- Unit tests: `uv run pytest tests/unit/exa/test_models.py -v`
- Golden fixture validation:
  - `tests/fixtures/golden/exa/search_empty_published_date_response.json`
  - `uv run python scripts/validate_models_against_golden.py`
- CLI regression (requires `EXA_API_KEY`): `uv run kalshi research topic "<query>" --no-summary --json`

## Cross-References

| Item | Relationship |
|------|--------------|
| DEBT-018 | Test SSOT - add golden fixture for edge case |
| SPEC-030 | Exa endpoint strategy - affected by this bug |
| `_vendor-docs/exa-api-reference.md` | SSOT for Exa API behavior |
