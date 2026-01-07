# BUG-010: Missing Portfolio-Thesis Link Commands (SPEC-011)

**Priority:** P4 (Trivial/Polish)
**Status:** Open
**Found:** 2026-01-07
**Spec:** SPEC-011-manual-trading-support.md

---

## Summary

SPEC-011 specified commands to link positions to theses, allowing users to track "Did my research thesis play out in my actual trades?" These commands were not implemented.

---

## Missing Commands

### 1. `kalshi portfolio link`

**Specified:**
```bash
# Link a position to a thesis
kalshi portfolio link TICKER --thesis THESIS_ID
```

**Status:** NOT IMPLEMENTED

**Impact:** Users cannot connect their research theses to actual positions.

---

### 2. `kalshi portfolio suggest-links`

**Specified:**
```bash
# Auto-suggest: "These positions might relate to thesis X"
kalshi portfolio suggest-links
```

**Status:** NOT IMPLEMENTED

**Impact:** No automatic discovery of thesis-position relationships.

---

### 3. `kalshi research thesis show --with-positions`

**Specified:**
```bash
# View thesis with linked positions
kalshi research thesis show THESIS_ID --with-positions
```

**Status:** NOT IMPLEMENTED

**Impact:** Cannot see positions alongside thesis details.

---

## Database Schema

The `Position` model already has a `thesis_id` foreign key:

```python
# src/kalshi_research/portfolio/models.py
class Position(Base):
    ...
    thesis_id: Mapped[int | None] = mapped_column(ForeignKey("theses.id"))
```

The infrastructure exists, just needs CLI exposure.

---

## Acceptance Criteria

- [ ] `kalshi portfolio link TICKER --thesis ID` updates Position.thesis_id
- [ ] `kalshi portfolio suggest-links` analyzes tickers and suggests matches
- [ ] `kalshi research thesis show ID --with-positions` displays linked positions
- [ ] Linking persists in database

---

## Implementation Notes

1. **portfolio link**: Simple UPDATE on Position table
2. **suggest-links**: Compare Position.ticker against Thesis.market_tickers
3. **thesis show --with-positions**: JOIN Position table in thesis display

---

## Priority Justification

**P4 (Trivial)** because:
- Core portfolio tracking works without linking
- This is "nice to have" research insight
- Database schema already supports it
- Low user impact if missing
