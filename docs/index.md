# Documentation

This repo follows a Diataxis-style layout:

- **Tutorials**: learn by doing
- **How-to**: task-oriented guides
- **Reference**: precise, scannable facts (CLI/API/config)
- **Explanation**: mental models + architecture

## Start Here

- `docs/getting-started/quickstart.md` — get a working local pipeline in minutes.
- `docs/developer/cli-reference.md` — command index (SSOT = `kalshi --help`).
- `docs/developer/configuration.md` — environments, `.env`, credentials, and live-test toggles.

## Tutorials

- `docs/getting-started/quickstart.md`

## How-to

- `docs/getting-started/usage.md` — workflows (data pipeline, scanning, alerts, portfolio, analysis, research).
- `docs/developer/testing.md` — run unit/integration/e2e; live API gates; coverage.

## Reference

- `docs/developer/cli-reference.md`
- `docs/developer/configuration.md`
- `docs/developer/python-api.md`
- `docs/_vendor-docs/kalshi-api-reference.md` — upstream Kalshi API reference (vendor docs).

## Explanation

- `docs/architecture/overview.md` — how the pieces fit together (module map + diagrams).
- `docs/architecture/data-pipeline.md` — DB schema + fetch/snapshot/export flow.
- `docs/architecture/cli.md` — Typer app wiring + daemon spawning.

## Internal Specs & Bug Tracker

- `docs/_specs/README.md` — design specs index + status table.
- `docs/_bugs/README.md` — bug tracker + audit report.
