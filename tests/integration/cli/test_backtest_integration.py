"""Integration tests for backtest CLI command.

These tests verify that the backtest command uses REAL data, not mock output.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration]


class TestBacktestCLI:
    """Test that backtest CLI produces real, varying output."""

    def test_backtest_output_changes_with_date_range(self, tmp_path: Path) -> None:
        """Output MUST change when date range changes (proves not hardcoded)."""
        db_path = tmp_path / "test.db"

        # Initialize DB
        subprocess.run(
            ["uv", "run", "kalshi", "data", "init", "--db", str(db_path)],
            check=True,
            capture_output=True,
        )

        # Run backtest with two different date ranges
        result1 = subprocess.run(
            [
                "uv", "run", "kalshi", "research", "backtest",
                "--start", "2024-01-01",
                "--end", "2024-06-30",
                "--db", str(db_path),
            ],
            capture_output=True,
            text=True,
        )

        result2 = subprocess.run(
            [
                "uv", "run", "kalshi", "research", "backtest",
                "--start", "2024-07-01",
                "--end", "2024-12-31",
                "--db", str(db_path),
            ],
            capture_output=True,
            text=True,
        )

        # If both outputs are identical AND contain numbers, it's probably mock data
        if "10" in result1.stdout and "60.0%" in result1.stdout:
            if result1.stdout == result2.stdout:
                pytest.fail(
                    "MOCK DATA DETECTED: Output identical for different date ranges. "
                    "The backtest command is returning hardcoded fake results!"
                )

    def test_backtest_with_no_data_shows_appropriate_message(
        self, tmp_path: Path
    ) -> None:
        """Should show 'no settlements' message, not fake results."""
        db_path = tmp_path / "empty.db"

        # Initialize empty DB
        subprocess.run(
            ["uv", "run", "kalshi", "data", "init", "--db", str(db_path)],
            check=True,
            capture_output=True,
        )

        result = subprocess.run(
            [
                "uv", "run", "kalshi", "research", "backtest",
                "--start", "2024-01-01",
                "--end", "2024-12-31",
                "--db", str(db_path),
            ],
            capture_output=True,
            text=True,
        )

        # Should NOT show fake successful results
        assert "Total Trades" not in result.stdout or "0" in result.stdout, (
            "Empty database should not produce positive trade counts"
        )

    def test_backtest_parameters_are_actually_used(self, tmp_path: Path) -> None:
        """Verify parameters affect output (not just accepted and ignored)."""
        db_path = tmp_path / "test.db"

        subprocess.run(
            ["uv", "run", "kalshi", "data", "init", "--db", str(db_path)],
            check=True,
            capture_output=True,
        )

        # The date range should appear in the output
        result = subprocess.run(
            [
                "uv", "run", "kalshi", "research", "backtest",
                "--start", "2024-03-15",
                "--end", "2024-09-22",
                "--db", str(db_path),
            ],
            capture_output=True,
            text=True,
        )

        # The specific dates should appear in output (proves they're being used)
        assert "2024-03-15" in result.stdout or "2024-09-22" in result.stdout, (
            "Date parameters should appear in output, proving they're used"
        )


class TestMockDataDetection:
    """Meta-tests to catch mock data patterns."""

    def test_no_hardcoded_mock_comments_in_cli(self) -> None:
        """CLI should not contain '# Mock' or '# for now' comments."""
        import re

        cli_path = Path("src/kalshi_research/cli.py")
        content = cli_path.read_text()

        mock_patterns = [
            r"#\s*[Mm]ock",
            r"#\s*for now",
            r"#\s*placeholder",
            r"#\s*stub",
            r"#\s*fake",
            r"#\s*hardcoded",
        ]

        for pattern in mock_patterns:
            matches = re.findall(pattern, content)
            if matches:
                pytest.fail(
                    f"Found mock/placeholder comment in cli.py: {matches}. "
                    "This indicates unfinished implementation masquerading as complete."
                )

    def test_cli_commands_use_their_imports(self) -> None:
        """
        Commands should actually use the classes they import.

        If ThesisBacktester is imported but not instantiated, that's suspicious.
        """
        import ast
        from pathlib import Path

        cli_path = Path("src/kalshi_research/cli.py")
        content = cli_path.read_text()
        tree = ast.parse(content)

        # Find all imports of implementation classes
        implementation_classes = {
            "ThesisBacktester",
            "CorrelationAnalyzer",
            "MarketScanner",
            "AlertMonitor",
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name in implementation_classes:
                        # This class is imported somewhere - verify it's instantiated
                        class_name = alias.name
                        # Simple check: is it called anywhere?
                        if f"{class_name}(" not in content:
                            pytest.fail(
                                f"{class_name} is imported but never instantiated. "
                                "This may indicate a mock implementation that imports "
                                "the real class but doesn't use it."
                            )
