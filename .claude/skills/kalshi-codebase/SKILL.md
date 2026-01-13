---
name: kalshi-codebase
description: Repo navigation and codebase structure for the Kalshi Research Platform. Use this skill for understanding where code lives, how modules are organized, and what patterns to follow.
---

# Kalshi Research Platform - Codebase Guide

Use this skill when you need a **repo map**, **where-to-change-what guidance**, or to understand the **codebase structure**.

For **Ralph Wiggum loop operation** (running autonomous iterations), use `kalshi-ralph-wiggum` instead.

## SSOT Rules (Do Not Violate)

1. **Code behavior** in `src/kalshi_research/`
2. **CLI surface** in `uv run kalshi --help` / `uv run kalshi <cmd> --help`
3. **Vendor docs** in `docs/_vendor-docs/`
4. **Internal docs/specs** in `docs/`, `docs/_specs/`

**If docs disagree with code, fix the docs** (or open a bug/spec) rather than "believing" the docs.

## Repository Map

```
kalshi-starter-code-python/
├── src/kalshi_research/           # Main package (src-layout)
│   ├── api/                       # Kalshi HTTP clients
│   │   ├── client.py              # KalshiPublicClient, KalshiClient
│   │   ├── models/                # Pydantic v2 models (frozen)
│   │   └── auth.py                # RSA signing
│   ├── data/                      # Persistence layer
│   │   ├── database.py            # DatabaseManager (async SQLite)
│   │   ├── models.py              # SQLAlchemy ORM models
│   │   ├── repositories/          # Repository pattern
│   │   ├── fetcher.py             # API → DB coordination
│   │   └── export.py              # DuckDB/Parquet export
│   ├── exa/                       # Exa API client + models
│   ├── execution/                 # Trade execution safety harness (models + guardrails)
│   ├── news/                      # News collection, sentiment
│   ├── analysis/                  # Scanner, liquidity, calibration
│   ├── research/                  # Thesis workflow, Exa research
│   ├── portfolio/                 # Position/P&L tracking
│   ├── alerts/                    # Alert conditions + monitoring
│   └── cli/                       # Typer CLI (kalshi command)
├── tests/
│   ├── unit/                      # Mirrors src/ layout
│   └── integration/               # Integration tests (live API tests opt-in via env vars/creds)
├── docs/
│   ├── _bugs/                     # Active bug reports
│   ├── _specs/                    # Active implementation specs
│   ├── _debt/                     # Technical debt tracker
│   ├── _future/                   # Blocked/deferred backlog
│   ├── _vendor-docs/              # Kalshi/Exa API references
│   └── _ralph-wiggum/             # Loop protocol reference
├── alembic/                       # Database migrations
├── data/                          # Runtime artifacts (kalshi.db)
├── PROGRESS.md                    # Ralph Wiggum state file
├── PROMPT.md                      # Ralph Wiggum loop prompt
├── CLAUDE.md                      # Agent guidance (Claude Code)
├── AGENTS.md                      # Agent guidance (all agents)
└── GEMINI.md                      # Agent guidance (Gemini)
```

## Key Patterns

### API Clients

Use async context managers:

```python
async with KalshiPublicClient() as client:
    market = await client.get_market("TICKER")
```

- `KalshiPublicClient`: Research, no auth required
- `KalshiClient`: Portfolio operations, requires API key

### Repository Pattern

Prefer repositories in `data/repositories/` for shared persistence logic:

```python
async with market_repo.session() as session:
    markets = await market_repo.get_by_event(session, event_ticker)
```

For small, one-off queries in CLI commands, direct `select()` is acceptable.

### Pydantic Models

API models in `api/models/` are frozen:

```python
model_config = ConfigDict(frozen=True)
```

Don't mutate them. Create new instances if needed.

### Testing Philosophy

- Only mock at system boundaries (HTTP via `respx`, filesystem via `tmp_path`)
- Use real Pydantic models, real in-memory SQLite
- Tests mirror `src/` structure: `tests/unit/api/`, `tests/unit/data/`, etc.

## CLI Structure

```
kalshi
├── version     # version info
├── status      # exchange status
├── data        # init, migrate, sync-markets, sync-settlements, sync-trades, snapshot, collect, export, stats, prune, vacuum
├── market      # get, list, orderbook, liquidity, history
├── scan        # opportunities, arbitrage, movers
├── alerts      # list, add, remove, monitor, trim-log
├── analysis    # calibration, correlation, metrics
├── research    # backtest, context, topic, similar, deep, thesis*, cache*
│   ├── thesis  # create, list, show, resolve, check-invalidation, suggest
│   └── cache   # clear
├── news        # track, untrack, list-tracked, collect, sentiment
└── portfolio   # sync, positions, pnl, balance, history, link, suggest-links
```

## Quality Gates

```bash
# Run before any commit
uv run pre-commit run --all-files

# Individual gates
uv run ruff check .           # Lint
uv run ruff format --check .  # Format
uv run mypy src/              # Types (strict)
uv run pytest -m "not integration and not slow"  # Fast tests
```

## Quick Navigation Commands

```bash
# Find a symbol/function
rg -n "SomeFunction" src/ tests/

# Find CLI command implementation
rg -n "def some_command" src/kalshi_research/cli/

# Find model definition
rg -n "class SomeModel" src/kalshi_research/

# Check CLI help
uv run kalshi --help
uv run kalshi market --help
```

## Maintenance Note

This repository keeps `.claude/skills/`, `.codex/skills/`, and `.gemini/skills/` in sync.
If you update this skill, apply the same change to all three copies.
