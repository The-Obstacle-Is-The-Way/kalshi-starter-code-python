# Data Directory

This directory contains local data for the Kalshi Research Platform.

## Contents
- **`kalshi.db`**: Main SQLite database storing market definitions, events, and historical data.
- **`research.db`**: Database for research-specific data (backtest results, thesis tracking).
- **`alerts.json`**: Configuration file for active price/volume alerts.
- **`theses.json`**: Storage for research theses and their outcomes.
- **`exports/`**: Directory for exported data (CSV, Parquet).

## Note
Large data files (`*.db`), temporary files (`*-shm`, `*-wal`), and local JSON data are **ignored** by git to prevent sensitive or large data from being committed.

**Do not commit production data to the repository.**
