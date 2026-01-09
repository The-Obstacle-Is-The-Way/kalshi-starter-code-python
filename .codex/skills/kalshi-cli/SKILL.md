---
name: kalshi-cli
description: Run and troubleshoot the Kalshi Research Platform CLI safely (Typer app), including env var setup, common command patterns, and where SSOT lives for flags/options.
---

# Kalshi CLI

## Golden rules (SSOT)

1. Treat `uv run kalshi --help` and `uv run kalshi <command> --help` as the only source of truth for flags/options.
2. Don’t assume a `--search` flag exists anywhere; use SQLite queries when you need filtering.
3. Prefer public endpoints unless you explicitly need authenticated portfolio features.

## Quick start

```bash
uv sync --all-extras
uv run kalshi --help
uv run kalshi data init
uv run kalshi data sync-markets --max-pages 1
uv run kalshi scan opportunities --filter close-race --max-pages 1
```

## Environment variables (auth only)

Authenticated commands (e.g. `kalshi portfolio ...`) require:

- `KALSHI_KEY_ID`
- `KALSHI_PRIVATE_KEY_PATH` or `KALSHI_PRIVATE_KEY_B64`
- Optional: `KALSHI_RATE_TIER` (`basic|advanced|premier|prime`)
- Optional: `KALSHI_ENVIRONMENT` (`prod|demo`, default `prod`)

The CLI auto-loads `.env` from repo root.

## Daemon mode note

Background/daemon processes use `python -m kalshi_research.cli ...` (implemented by `src/kalshi_research/cli/__main__.py`).

## References (read these when stuck)

- CLI index (SSOT map): `docs/developer/cli-reference.md`
- Full CLI command reference: `.claude/skills/kalshi-cli/CLI-REFERENCE.md`
- Configuration/env vars: `docs/developer/configuration.md`
