# Documentation

This repo follows a Diataxis-style layout:

- **Tutorials**: learn by doing
- **How-to**: task-oriented guides
- **Reference**: precise, scannable facts (CLI/API/config)
- **Explanation**: mental models + architecture

## Start Here

- `docs/tutorials/quickstart.md` — get a working local pipeline in minutes.
- `docs/reference/cli-reference.md` — command index (SSOT = `kalshi --help`).
- `docs/reference/configuration.md` — environments, `.env`, credentials, and live-test toggles.

## Tutorials

- `docs/tutorials/quickstart.md`

## How-to

- `docs/how-to/usage.md` — workflows (data pipeline, scanning, alerts, portfolio, analysis, research).
- `docs/how-to/testing.md` — run unit/integration/e2e; live API gates; coverage.

## Reference

- `docs/reference/cli-reference.md`
- `docs/reference/configuration.md`
- `docs/reference/python-api.md`
- `docs/kalshi-docs/OFFICIAL-API-REFERENCE.md` — upstream Kalshi API reference (vendor docs).

## Explanation

- `docs/explanation/architecture.md` — how the pieces fit together (module map + diagrams).
- `docs/explanation/data-pipeline.md` — DB schema + fetch/snapshot/export flow.
- `docs/explanation/cli-architecture.md` — Typer app wiring + daemon spawning.

## Internal Specs & Bug Tracker

- `docs/_specs/README.md` — design specs index + status table.
- `docs/_bugs/README.md` — bug tracker + audit report.
