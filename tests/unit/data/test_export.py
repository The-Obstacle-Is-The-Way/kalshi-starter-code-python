from unittest.mock import MagicMock, patch

import pytest

from kalshi_research.data.export import export_to_csv, export_to_parquet, query_parquet


@patch("duckdb.connect")
def test_export_to_parquet_success(mock_connect, tmp_path):
    mock_conn = MagicMock()
    mock_connect.return_value = mock_conn

    db_path = tmp_path / "test.db"
    db_path.touch()
    output_dir = tmp_path / "exports"

    export_to_parquet(db_path, output_dir)

    mock_connect.assert_called_once()
    assert mock_conn.execute.call_count >= 3


def test_export_to_parquet_invalid_path(tmp_path):
    db_path = tmp_path / "test.db"
    db_path.touch()
    # Check for invalid characters check, NOT file not found
    with pytest.raises(ValueError, match="Invalid characters"):
        export_to_parquet(db_path, "bad;path")


def test_export_to_parquet_db_not_found():
    with pytest.raises(FileNotFoundError):
        export_to_parquet("nonexistent.db", "out")


@patch("duckdb.connect")
def test_export_to_parquet_rejects_invalid_table_name(mock_connect, tmp_path):
    mock_conn = MagicMock()
    mock_connect.return_value = mock_conn

    db_path = tmp_path / "test.db"
    db_path.touch()
    output_dir = tmp_path / "exports"

    with pytest.raises(ValueError, match="Invalid table name"):
        export_to_parquet(db_path, output_dir, tables=["not_a_table"])


@patch("duckdb.connect")
def test_export_to_csv_success(mock_connect, tmp_path):
    mock_conn = MagicMock()
    mock_connect.return_value = mock_conn

    db_path = tmp_path / "test.db"
    db_path.touch()
    output_dir = tmp_path / "exports"

    export_to_csv(db_path, output_dir)

    mock_connect.assert_called_once()
    assert mock_conn.execute.call_count >= 3


def test_export_to_csv_invalid_path(tmp_path):
    db_path = tmp_path / "test.db"
    db_path.touch()
    with pytest.raises(ValueError, match="Invalid characters"):
        export_to_csv(db_path, "bad;path")


def test_export_to_csv_db_not_found():
    with pytest.raises(FileNotFoundError):
        export_to_csv("nonexistent.db", "out")


@patch("duckdb.connect")
def test_export_to_csv_rejects_invalid_table_name(mock_connect, tmp_path):
    mock_conn = MagicMock()
    mock_connect.return_value = mock_conn

    db_path = tmp_path / "test.db"
    db_path.touch()
    output_dir = tmp_path / "exports"

    with pytest.raises(ValueError, match="Invalid table name"):
        export_to_csv(db_path, output_dir, tables=["not_a_table"])


def test_export_to_parquet_rejects_invalid_sqlite_path(tmp_path):
    db_path = tmp_path / "bad;name.db"
    db_path.touch()
    with pytest.raises(ValueError, match="Invalid characters"):
        export_to_parquet(db_path, tmp_path / "out")


def test_query_parquet_rejects_invalid_path():
    with pytest.raises(ValueError, match="Invalid characters"):
        query_parquet("bad;path", "SELECT 1")


@patch("duckdb.connect")
def test_query_parquet_creates_views_for_existing_exports(mock_connect, tmp_path):
    mock_conn = MagicMock()
    mock_connect.return_value = mock_conn
    mock_conn.execute.return_value.fetchall.return_value = [("ok",)]

    (tmp_path / "markets.parquet").touch()
    (tmp_path / "events.parquet").touch()
    # settlements.parquet intentionally absent to cover the conditional branch.

    rows = query_parquet(tmp_path, "SELECT 1")

    assert rows == [("ok",)]
    executed = [call.args[0] for call in mock_conn.execute.call_args_list]
    assert any("CREATE VIEW snapshots" in q for q in executed)
    assert any("CREATE VIEW markets" in q for q in executed)
    assert any("CREATE VIEW events" in q for q in executed)
    assert not any("CREATE VIEW settlements" in q for q in executed)
