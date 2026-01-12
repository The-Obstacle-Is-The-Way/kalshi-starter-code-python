# BUG-065: `amend_order()` Incomplete Implementation

**Priority:** P3 (was P2 - downgraded after verification)
**Status:** Open
**Found:** 2026-01-12
**Verified:** 2026-01-12

---

## Summary

The `amend_order()` method has a minimal implementation. Vendor docs suggest additional required fields, but this has **NOT been verified against the actual API**.

**CONTEXT:** After verification:
1. **Not used in CLI** - no user exposure
2. **Unit test uses minimal payload** - test at line 93 expects `{"order_id": "...", "yes_price": 55}`
3. **Vendor doc "required" fields are unverified** - may work without them

---

## Verification Results

**Is amend_order used anywhere?**

```bash
grep -r "amend_order" src/kalshi_research/cli/
# Result: No matches found
```

**Unit test expectation:** `tests/unit/api/test_trading.py:93`
```python
assert kwargs["json"] == {"order_id": "oid-123", "yes_price": 55}
```

---

## Current State

**Location:** `src/kalshi_research/api/client.py:830-907`

**Current signature:**
```python
async def amend_order(
    self,
    order_id: str,
    price: int | None = None,
    count: int | None = None,
    dry_run: bool = False,
) -> OrderResponse
```

**Sends to API:** `{"order_id": "...", "yes_price": ..., "count": ...}`

---

## Potentially Missing Fields (UNVERIFIED)

The vendor docs I created claim these are required, but this needs API verification:

| Field | Claimed | Actual Need | Notes |
|-------|---------|-------------|-------|
| `ticker` | Required | Unknown | Server may infer from order_id |
| `side` | Required | Unknown | Server may infer from order_id |
| `action` | Required | Unknown | Server may infer from order_id |
| `client_order_id` | Required | Unknown | Only if using client IDs |
| `updated_client_order_id` | Required | Unknown | Only if using client IDs |

**Dollar-price alternatives (useful for API completeness):**
- `yes_price_dollars` (string) - Alternative to cents
- `no_price_dollars` (string) - Alternative to cents

---

## Risk Assessment

**Why P3:**
- Not exposed via CLI
- Unit test assumes minimal payload works
- "Required" fields may be server-inferred
- Pure API completeness issue

**Verification needed:**
- Test `amend_order` against demo API with minimal payload
- Confirm if additional fields are truly required or just recommended

---

## Fix (If Needed After Verification)

If API verification shows fields are required:

1. Add missing parameters to method signature
2. Update request body construction
3. Add tests

---

## Test Plan

- [ ] Test against demo API with minimal payload
- [ ] If fails, add required fields
- [ ] Add dollar-price alternatives for future-proofing

---

## Lessons Learned

Vendor docs I wrote may be stricter than actual API behavior. Always verify against actual API before claiming "required" fields.
