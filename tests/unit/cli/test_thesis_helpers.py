from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def test_find_thesis_by_id_matches_prefix() -> None:
    from kalshi_research.cli.research.thesis._helpers import _find_thesis_by_id

    theses = [
        {"id": "abc123", "title": "A"},
        {"id": "def456", "title": "B"},
    ]

    assert _find_thesis_by_id(theses, "abc") == {"id": "abc123", "title": "A"}


def test_find_thesis_by_id_returns_none_when_missing() -> None:
    from kalshi_research.cli.research.thesis._helpers import _find_thesis_by_id

    theses = [{"id": "abc123", "title": "A"}]

    assert _find_thesis_by_id(theses, "zzz") is None


def test_render_thesis_evidence_prints_groups_and_truncates_snippet() -> None:
    from kalshi_research.cli.research.thesis._helpers import _render_thesis_evidence

    long_snippet = "x" * 200
    evidence = [
        {
            "supports": "bull",
            "title": "Bull item",
            "source_domain": "example.com",
            "snippet": long_snippet,
        },
        {
            "supports": "bear",
            "title": "Bear item",
            "source_domain": "example.com",
            "snippet": "short",
        },
        {
            "supports": "neutral",
            "title": "Neutral item",
            "source_domain": "example.com",
            "snippet": "",
        },
    ]

    with patch("kalshi_research.cli.research.thesis._helpers.console.print") as mock_print:
        _render_thesis_evidence(evidence)

    printed = "\n".join(str(call.args[0]) for call in mock_print.call_args_list if call.args)
    assert "Bull Evidence" in printed
    assert "Bear Evidence" in printed
    assert "Neutral Evidence" in printed
    assert long_snippet[:180] + "..." in printed


def test_print_invalidation_signals_formats_severity_and_optional_fields() -> None:
    from kalshi_research.cli.research.thesis._helpers import _print_invalidation_signals
    from kalshi_research.research.invalidation import InvalidationSeverity, InvalidationSignal

    signals = [
        InvalidationSignal(
            severity=InvalidationSeverity.HIGH,
            title="High signal",
            url="https://example.com/high",
            source_domain="example.com",
            published_at=datetime(2026, 1, 1, tzinfo=UTC),
            reason="Reason",
            snippet="Snippet",
        ),
        InvalidationSignal(
            severity=InvalidationSeverity.MEDIUM,
            title="Med signal",
            url="https://example.com/med",
            source_domain="example.com",
            published_at=None,
            reason="",
            snippet="",
        ),
        InvalidationSignal(
            severity=InvalidationSeverity.LOW,
            title="Low signal",
            url="https://example.com/low",
            source_domain="example.com",
            published_at=None,
            reason="Reason",
            snippet="Snippet",
        ),
    ]

    with patch("kalshi_research.cli.research.thesis._helpers.console.print") as mock_print:
        _print_invalidation_signals(signals, severity_enum=InvalidationSeverity)

    printed = "\n".join(str(call.args[0]) for call in mock_print.call_args_list if call.args)
    assert "[HIGH]" in printed
    assert "[MEDIUM]" in printed
    assert "[LOW]" in printed


@pytest.mark.asyncio
async def test_fetch_and_render_linked_positions_prints_no_positions() -> None:
    from kalshi_research.cli.research.thesis._helpers import _fetch_and_render_linked_positions

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)

    @asynccontextmanager
    async def mock_open_db_session(_db_path: Path):
        yield mock_session

    with (
        patch("kalshi_research.cli.db.open_db_session", mock_open_db_session),
        patch("kalshi_research.cli.research.thesis._helpers.console.print") as mock_print,
    ):
        await _fetch_and_render_linked_positions("thesis-1", Path("fake.db"))

    printed = "\n".join(str(call.args[0]) for call in mock_print.call_args_list if call.args)
    assert "No positions linked" in printed


@pytest.mark.asyncio
async def test_fetch_and_render_linked_positions_formats_pnl_and_avg_price() -> None:
    from kalshi_research.cli.research.thesis._helpers import _fetch_and_render_linked_positions

    pos_up = MagicMock()
    pos_up.ticker = "TEST-UP"
    pos_up.side = "yes"
    pos_up.quantity = 10
    pos_up.avg_price_cents = 55
    pos_up.unrealized_pnl_cents = 123

    pos_down = MagicMock()
    pos_down.ticker = "TEST-DOWN"
    pos_down.side = "no"
    pos_down.quantity = 5
    pos_down.avg_price_cents = 0
    pos_down.unrealized_pnl_cents = -50

    pos_none = MagicMock()
    pos_none.ticker = "TEST-NONE"
    pos_none.side = "yes"
    pos_none.quantity = 1
    pos_none.avg_price_cents = 0
    pos_none.unrealized_pnl_cents = None

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [pos_up, pos_down, pos_none]

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)

    @asynccontextmanager
    async def mock_open_db_session(_db_path: Path):
        yield mock_session

    with (
        patch("kalshi_research.cli.db.open_db_session", mock_open_db_session),
        patch("kalshi_research.cli.research.thesis._helpers.console.print") as mock_print,
    ):
        await _fetch_and_render_linked_positions("thesis-1", Path("fake.db"))

    printed = "\n".join(str(call.args[0]) for call in mock_print.call_args_list if call.args)
    assert "Linked Positions" in printed
