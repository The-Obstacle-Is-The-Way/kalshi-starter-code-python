from __future__ import annotations


def test_configure_structlog_warns_on_invalid_log_level(monkeypatch, capfd) -> None:
    from kalshi_research.logging import configure_structlog

    monkeypatch.setenv("KALSHI_LOG_LEVEL", "not-a-level")
    configure_structlog()

    captured = capfd.readouterr()
    assert "Invalid KALSHI_LOG_LEVEL" in captured.err
