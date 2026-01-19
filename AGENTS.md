# Repository Guidelines

This file provides guidance to AI coding agents (Claude Code, OpenAI Codex, Gemini CLI, etc.) when working with this repository.

## Project Intent (Avoid Over-Engineering)

This repository is an **internal, single-user research CLI** (plus local SQLite cache) for a solo trader.
It is **not** a multi-user production service.

- Prefer **simple, testable** changes over “enterprise patterns”.
- Do **not** add service infrastructure (circuit breakers, Prometheus/Otel, request tracing, DI) unless a SPEC/BUG
  explicitly requires it.
- Keep dependencies minimal; focus on correctness, clear UX, and robust error handling.

## Agent Skills

This repository includes Agent Skills for enhanced CLI navigation and documentation auditing:

| Skill | Purpose |
|-------|---------|
| `kalshi-cli` | CLI commands, database queries, workflows, gotchas |
| `kalshi-codebase` | Repo navigation and codebase structure |
| `kalshi-ralph-wiggum` | Ralph Wiggum autonomous loop operation |
| `kalshi-doc-audit` | Documentation auditing against SSOT |

Skills are located in agent-specific directories (all identical content):
- `.claude/skills/` - Claude Code
- `.codex/skills/` - OpenAI Codex CLI
- `.gemini/skills/` - Gemini CLI

## CRITICAL: Commit Safety Protocol

**NEVER commit code without running quality gates first.** A previous incident introduced syntax corruption (`时不时` instead of `import`) that broke the entire codebase. This was caused by committing without pre-commit hooks installed.

### MANDATORY Before ANY Commit

```bash
# 1. FIRST: Ensure pre-commit hooks are installed (do this ONCE after clone)
uv run pre-commit install

# 2. ALWAYS run pre-commit before staging/committing
uv run pre-commit run --all-files

# 3. If pre-commit passes, THEN commit
git add . && git commit -m "Your message"

# 4. NEVER use --no-verify to bypass hooks
# git commit --no-verify  # <- FORBIDDEN
```

### Pre-commit Will Automatically Check

1. **Python syntax validation** (`check-ast`) - Catches encoding corruption
2. **Ruff linting** - Code quality and style
3. **Ruff formatting** - Consistent formatting
4. **Mypy type checking** - Static type safety
5. **Unit tests** - Quick smoke test

### FORBIDDEN Patterns

- **NO `# type: ignore`** - Fix the type error properly
- **NO untyped `Any`** - Use specific types (exception: JSON dicts as `dict[str, Any]`)
- **NO `--no-verify` commits** - Always run pre-commit hooks
- **NO manual git commits without pre-commit** - Always verify first

## Project Structure & Module Organization

- `src/kalshi_research/`: main package (src-layout)
  - `api/`: Kalshi HTTP clients + Pydantic models
  - `data/`: async SQLite/SQLAlchemy persistence, repositories, exports
  - `exa/`: Exa API client for research
  - `news/`: News collection and sentiment analysis
  - `analysis/`, `research/`, `alerts/`, `portfolio/`: domain modules
  - `cli/`: Typer CLI package entrypoint (`kalshi`)
- `tests/`: `unit/` mirrors `src/`; `integration/` covers DB/migrations/CLI (live API tests are opt-in via env vars/creds)
- `docs/`: usage guides plus specs/bug tracker (`docs/_specs/`, `docs/_bugs/`)
- `alembic/`, `alembic.ini`: database migrations
- `data/`: local runtime artifacts (e.g., `data/kalshi.db`, exports)

## Build, Test, and Development Commands

Preferred dependency manager is `uv` (see `uv.lock`):

```bash
uv sync --all-extras              # install dev + research extras
uv run pre-commit install         # CRITICAL: Install commit hooks
uv run kalshi --help              # run CLI without global install
uv run ruff check .               # lint (CI)
uv run ruff format --check .      # format check (CI); drop --check to format
uv run mypy src/                  # strict type checking (CI)
uv run pytest -m "not integration and not slow"  # fast local suite (CI-like)
```

## Coding Style & Naming Conventions

- Python 3.11+, 4-space indentation; `ruff` is the formatter/linter (line length 100).
- Names: `snake_case` for functions/variables, `PascalCase` for classes, `test_*.py` for tests.
- Keep boundaries clear: HTTP logic stays in `api/`; DB access goes through `data/repositories/`.

## Testing Guidelines

- `pytest` + `pytest-asyncio` (see markers in `pyproject.toml`: `unit`, `integration`, `slow`).
- Prefer testing real domain logic; only mock at system boundaries (HTTP, filesystem).
- Put new tests under `tests/unit/<module>/...` to match the `src/` layout.

## Commit & Pull Request Guidelines

- **ALWAYS run `uv run pre-commit run --all-files` before committing**
- Use atomic commits; follow the repo's common pattern: `[BUG-###] Fix: ...`, `[SPEC-###] Implement: ...`, `[FEATURE] Add: ...`, `[QUALITY-###] Fix: ...`.
- PRs should include: what changed, how it was tested (commands run), and any user-facing doc updates (often `docs/getting-started/usage.md` / `docs/getting-started/quickstart.md`).
- Before review, ensure local checks match CI: `ruff`, `mypy`, and `pytest` are green.

## Security & Configuration Tips

- Copy `.env.example` → `.env`; never commit `.env`, API keys, or private key material.
- Public endpoints work without creds; portfolio features/integration tests require Kalshi creds (prod: `KALSHI_KEY_ID` + `KALSHI_PRIVATE_KEY_*`; demo: `KALSHI_DEMO_KEY_ID` + `KALSHI_DEMO_PRIVATE_KEY_*` (falls back to prod vars)).
- Exa-powered commands require `EXA_API_KEY`.

## Runtime Environment & API Access

**Agents CAN and SHOULD read `.env`** to understand the configured environment. While `.env` is gitignored (never commit it), reading it is necessary to:

- Determine if `KALSHI_ENVIRONMENT` is set to `prod` or `demo`
- Verify API credentials are configured before running authenticated commands
- Avoid confusion about which environment is active

### Environment Behavior

| `KALSHI_ENVIRONMENT` | API Base URL                 | Real Money? |
|----------------------|------------------------------|-------------|
| `prod` (default)     | `api.elections.kalshi.com`   | **YES**     |
| `demo`               | `demo-api.kalshi.co`         | No (paper)  |

### Kalshi Price Fields (CRITICAL)

Kalshi deprecated integer cent fields in favor of `*_dollars` string fields (subpenny pricing migration, Nov 2025). **Always use `*_dollars` fields** (e.g., `yes_bid_dollars`, `yes_ask_dollars`, `last_price_dollars`) - never rely on cent-based fields like `yes_bid`, `yes_ask`, `last_price`. See `docs/_vendor-docs/kalshi-api-reference.md` for details.

### Safe Operations (READ-ONLY)

These commands are safe to run anytime - they only read data:

```bash
uv run kalshi market list              # Public endpoint, no auth needed
uv run kalshi market get TICKER        # Public endpoint, no auth needed
uv run kalshi scan opportunities       # Public endpoint, no auth needed
uv run kalshi portfolio sync           # Authenticated READ from Kalshi API
uv run kalshi portfolio positions      # Reads local DB cache (run sync first!)
uv run kalshi portfolio pnl            # Reads local DB cache
```

**Important:** `portfolio positions` reads from the **local database cache**, not the live API. Always run `portfolio sync` first to pull the latest data from Kalshi.

### Cost-Incurring Operations (USE CAUTION)

These operations may incur real costs:

- **Order placement** (`create_order`) - Real money on prod environment
- **Exa API calls** (`research context`, `research topic`, `research similar`, `research deep`, `research thesis create --with-research`, `research thesis check-invalidation`, `research thesis suggest`, `news collect`) - Exa API usage costs

### Pre-flight Checklist for Authenticated Commands

Before running portfolio or authenticated commands:

1. Read `.env` to confirm `KALSHI_ENVIRONMENT` is set correctly
2. Verify creds for that environment are configured (prod: `KALSHI_KEY_ID` + `KALSHI_PRIVATE_KEY_*`; demo: `KALSHI_DEMO_KEY_ID` + `KALSHI_DEMO_PRIVATE_KEY_*` (falls back to prod vars))
3. Run `uv run kalshi portfolio sync` to populate local DB
4. Then run read commands like `portfolio positions`

## Database Safety (Do Not Destroy State)

- **NEVER delete `data/kalshi.db`** to "fix" issues (e.g. `database disk image is malformed`).
- Diagnose first (`sqlite3 data/kalshi.db "PRAGMA integrity_check;"`) and recover when needed (`sqlite3 data/kalshi.db ".recover" | sqlite3 data/recovered.db`).
- `data/exa_cache/` is disposable cache; the SQLite DB is not.
- **SQLite concurrency:** Avoid running two write-heavy commands simultaneously (e.g., two `data sync-markets` in parallel). SQLite locks the entire DB on write; concurrent writers will get "database is locked" errors.
- See the skills GOTCHAS.md for the full "Critical Anti-Patterns" section.

## LLM Synthesizer (Agent System)

The agent analysis workflow (`kalshi agent analyze`) uses an LLM to synthesize probability estimates from research.

### Frontier Models (2026)

| Provider | Model | Model ID | Use Case |
|----------|-------|----------|----------|
| **Anthropic** | Claude Sonnet 4.5 | `claude-sonnet-4-5-20250929` | Primary synthesizer (SPEC-042) |
| **Anthropic** | Claude Opus 4.5 | `claude-opus-4-5-20251101` | Complex reasoning (if needed) |

**Do NOT use deprecated models** like `gpt-4o-mini`, `claude-3-sonnet`, etc. Always use the latest frontier models.

### Configuration

```bash
# Set synthesizer backend (default: anthropic)
export KALSHI_SYNTHESIZER_BACKEND=anthropic
export ANTHROPIC_API_KEY=your_key_here

# Run analysis with real LLM
uv run kalshi agent analyze TICKER --mode standard
```

See [SPEC-042](docs/_specs/SPEC-042-llm-synthesizer-implementation.md) for implementation details.

## Documentation Tracking

When you find drift, bugs, or technical debt, record them in the appropriate tracker:

- Active bugs: `docs/_bugs/README.md`
- Active specs: `docs/_specs/README.md`
- Backlog (blocked/deferred): `docs/_future/README.md`
- Technical debt: `docs/_debt/README.md`

## Ralph Wiggum Loop (Optional)

This repo supports the Ralph Wiggum autonomous loop via the root state files:

- `PROGRESS.md` — loop state (task queue + work log)
- `PROMPT.md` — iteration prompt
- Reference: `docs/_ralph-wiggum/protocol.md`
