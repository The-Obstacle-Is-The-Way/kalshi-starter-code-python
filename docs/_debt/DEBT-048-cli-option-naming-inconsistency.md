# DEBT-048: CLI Option Naming Inconsistency

## Priority: P3 (Low)

## Summary
Different CLI commands use different option names for the same concept (limiting results), causing user confusion and errors.

## Examples

| Command | Option | Notes |
|---------|--------|-------|
| `market search` | `--top/-n` | Long option differs from `market list` |
| `market list` | `--limit/-n` | Long option differs from `market search` |
| `scan opportunities` | `--top/-n` | Matches `market search` |
| `event list` | `--limit` | Matches `mve list` |
| `mve list` | `--limit` | Matches `event list` |

## Impact
- Users (and agents) guess wrong and get errors
- Inconsistent UX across the CLI
- Error: `No such option: --limit` when using `--top` command, and vice versa

## Recommended Fix
Standardize on one option name across all commands. Options:
1. Use `--limit` everywhere (more descriptive)
2. Use `--top` everywhere (shorter)
3. Support both as aliases

## Discovered
2026-01-21 during stress test session

## Status
Open - Low priority UX debt
