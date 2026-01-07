"""
Tests for data export - basic path validation tests.
"""

from __future__ import annotations

import tempfile

import pytest

from kalshi_research.data.export import export_to_csv, export_to_parquet


class TestExportValidation:
    """Test export path validation."""

    def test_export_parquet_file_not_found(self) -> None:
        """Export raises error for missing database."""
        with pytest.raises(FileNotFoundError, match="not found"):
            export_to_parquet(
                sqlite_path="/nonexistent/path.db",
                output_dir="/tmp/output",
            )

    def test_export_csv_file_not_found(self) -> None:
        """Export raises error for missing database."""
        with pytest.raises(FileNotFoundError, match="not found"):
            export_to_csv(
                sqlite_path="/nonexistent/path.db",
                output_dir="/tmp/output",
            )

    def test_export_parquet_invalid_path(self) -> None:
        """Export raises error for paths with invalid characters."""
        with (
            tempfile.NamedTemporaryFile(suffix=".db") as f,
            pytest.raises(ValueError, match="Invalid characters"),
        ):
            export_to_parquet(
                sqlite_path=f.name,
                output_dir="/tmp/'; DROP TABLE users; --/output",
            )

    def test_export_csv_invalid_path(self) -> None:
        """Export raises error for paths with invalid characters."""
        with (
            tempfile.NamedTemporaryFile(suffix=".db") as f,
            pytest.raises(ValueError, match="Invalid characters"),
        ):
            export_to_csv(
                sqlite_path=f.name,
                output_dir="/tmp/'; DROP TABLE users; --/output",
            )
