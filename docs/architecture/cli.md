# CLI Architecture (Explanation)

This doc explains how the Typer CLI is wired, how global configuration is applied, and how daemon mode works.

## Layout

The CLI lives in `src/kalshi_research/cli/` (a package, not a single file):

```text
src/kalshi_research/cli/
├── __init__.py   # app, global callback, sub-app registration
├── __main__.py   # enables `python -m kalshi_research.cli ...`
├── utils.py      # shared Rich console + JSON helpers
├── client_factory.py  # KalshiPublicClient/KalshiClient factories
├── agent.py
├── browse.py
├── series.py
├── event.py
├── mve.py
├── status.py
├── data/
├── market/
├── scan/
├── alerts/
├── analysis.py
├── research/
├── portfolio/
└── news.py
```

## Global config (`--env` + `.env`)

At CLI startup:

1. `.env` is loaded (searching upward from CWD).
2. The API environment is determined by precedence:

```text
--env/-e flag  >  KALSHI_ENVIRONMENT  >  "prod"
```

Invalid values exit with an error (no silent fallback).

## Async boundary

Most commands are implemented as a small sync wrapper that calls `run_async(...)` (which uses `asyncio.run(...)`)
internally. This keeps the CLI ergonomic while allowing the underlying clients/DB to stay async.

## Alerts daemon mode

`kalshi alerts monitor --daemon` spawns a detached child process:

```text
parent: kalshi alerts monitor --daemon
  └─ spawns: python -m kalshi_research.cli alerts monitor ...
```

Daemon mode relies on `src/kalshi_research/cli/__main__.py` so Python can execute the CLI package as a module.
