"""Data export utilities for DuckDB/Parquet."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Allowed tables for export (prevents SQL injection via table names)
ALLOWED_TABLES = frozenset({"price_snapshots", "markets", "events", "settlements"})


def export_to_parquet(
    sqlite_path: str | Path,
    output_dir: str | Path,
    tables: list[str] | None = None,
) -> None:
    """
    Export SQLite data to partitioned Parquet files for efficient analysis.

    Uses DuckDB for high-performance data transfer.

    Args:
        sqlite_path: Path to SQLite database file
        output_dir: Directory to write Parquet files
        tables: List of tables to export (default: all)

    Raises:
        FileNotFoundError: If SQLite database doesn't exist
        ValueError: If paths contain invalid characters
        ValueError: If an invalid table name is requested
    """
    import duckdb

    sqlite_path = Path(sqlite_path).resolve()
    output_dir = Path(output_dir).resolve()

    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite database not found: {sqlite_path}")

    # Validate paths don't contain SQL injection characters
    for path in [sqlite_path, output_dir]:
        if any(c in str(path) for c in ["'", '"', ";", "--"]):
            raise ValueError(f"Invalid characters in path: {path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    conn = duckdb.connect()
    try:
        # Install and load SQLite extension
        conn.execute("INSTALL sqlite; LOAD sqlite;")

        # Attach SQLite database (paths are validated above)
        conn.execute(f"ATTACH '{sqlite_path}' AS kalshi (TYPE SQLITE);")

        # Default tables to export
        if tables is None:
            tables = list(ALLOWED_TABLES)

        # Validate table names (defense-in-depth against SQL injection)
        for table in tables:
            if table not in ALLOWED_TABLES:
                raise ValueError(f"Invalid table name: {table}. Allowed: {ALLOWED_TABLES}")

        for table in tables:
            table_dir = output_dir / table

            if table == "price_snapshots":
                # Partition snapshots by month for efficient time-based queries
                conn.execute(f"""
                    COPY (
                        SELECT *, strftime(snapshot_time, '%Y-%m') as month
                        FROM kalshi.{table}
                    ) TO '{table_dir}'
                    (FORMAT PARQUET, PARTITION_BY (month), OVERWRITE_OR_IGNORE true);
                """)
            else:
                # Export other tables as single files
                conn.execute(f"""
                    COPY kalshi.{table} TO '{table_dir}.parquet'
                    (FORMAT PARQUET);
                """)

            logger.info("Exported %s to Parquet: %s", table, table_dir)

    finally:
        conn.close()


def export_to_csv(
    sqlite_path: str | Path,
    output_dir: str | Path,
    tables: list[str] | None = None,
) -> None:
    """
    Export SQLite data to CSV files.

    Args:
        sqlite_path: Path to SQLite database file
        output_dir: Directory to write CSV files
        tables: List of tables to export (default: all)

    Raises:
        FileNotFoundError: If SQLite database doesn't exist
        ValueError: If paths contain invalid characters
        ValueError: If an invalid table name is requested
    """
    import duckdb

    sqlite_path = Path(sqlite_path).resolve()
    output_dir = Path(output_dir).resolve()

    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite database not found: {sqlite_path}")

    # Validate paths don't contain SQL injection characters
    for path in [sqlite_path, output_dir]:
        if any(c in str(path) for c in ["'", '"', ";", "--"]):
            raise ValueError(f"Invalid characters in path: {path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    conn = duckdb.connect()
    try:
        conn.execute("INSTALL sqlite; LOAD sqlite;")
        conn.execute(f"ATTACH '{sqlite_path}' AS kalshi (TYPE SQLITE);")

        if tables is None:
            tables = list(ALLOWED_TABLES)

        # Validate table names (defense-in-depth against SQL injection)
        for table in tables:
            if table not in ALLOWED_TABLES:
                raise ValueError(f"Invalid table name: {table}. Allowed: {ALLOWED_TABLES}")

        for table in tables:
            output_file = output_dir / f"{table}.csv"
            conn.execute(f"""
                COPY kalshi.{table} TO '{output_file}'
                (FORMAT CSV, HEADER true);
            """)
            logger.info("Exported %s to CSV: %s", table, output_file)

    finally:
        conn.close()


def query_parquet(
    parquet_dir: str | Path,
    query: str,
) -> list[tuple[object, ...]]:
    """
    Run a SQL query against exported Parquet files.

    Args:
        parquet_dir: Directory containing Parquet exports
        query: SQL query to execute (use 'snapshots', 'markets', etc. as table names)

    Returns:
        Query results as list of tuples
    """
    import duckdb

    parquet_dir = Path(parquet_dir).resolve()

    conn = duckdb.connect()
    try:
        # Create views for each exported table
        snapshots_path = parquet_dir / "price_snapshots" / "**" / "*.parquet"
        markets_path = parquet_dir / "markets.parquet"
        events_path = parquet_dir / "events.parquet"
        settlements_path = parquet_dir / "settlements.parquet"

        conn.execute(f"CREATE VIEW snapshots AS SELECT * FROM '{snapshots_path}'")
        if markets_path.exists():
            conn.execute(f"CREATE VIEW markets AS SELECT * FROM '{markets_path}'")
        if events_path.exists():
            conn.execute(f"CREATE VIEW events AS SELECT * FROM '{events_path}'")
        if settlements_path.exists():
            conn.execute(f"CREATE VIEW settlements AS SELECT * FROM '{settlements_path}'")

        result = conn.execute(query).fetchall()
        return result

    finally:
        conn.close()
