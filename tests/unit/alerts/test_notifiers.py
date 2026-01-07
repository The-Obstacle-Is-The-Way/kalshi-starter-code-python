"""Tests for alert notifiers."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import httpx

from kalshi_research.alerts.conditions import Alert, AlertCondition, AlertStatus, ConditionType
from kalshi_research.alerts.notifiers import ConsoleNotifier, FileNotifier, WebhookNotifier


def _make_alert() -> Alert:
    condition = AlertCondition(
        id="cond-1",
        condition_type=ConditionType.PRICE_ABOVE,
        ticker="TEST-TICKER",
        threshold=0.6,
        label="price TEST-TICKER > 0.6",
    )
    return Alert(
        id="alert-1",
        condition=condition,
        triggered_at=datetime.now(UTC),
        status=AlertStatus.TRIGGERED,
        current_value=0.61,
        market_data={"foo": "bar"},
    )


def test_console_notifier_prints_panel() -> None:
    alert = _make_alert()
    notifier = ConsoleNotifier()

    with patch.object(notifier._console, "print") as mock_print:
        notifier.notify(alert)

    assert mock_print.call_count == 1


def test_file_notifier_writes_jsonl(tmp_path) -> None:
    alert = _make_alert()
    out = tmp_path / "alerts.jsonl"

    notifier = FileNotifier(out)
    notifier.notify(alert)

    lines = out.read_text().splitlines()
    assert len(lines) == 1

    record = json.loads(lines[0])
    assert record["id"] == "alert-1"
    assert record["condition_id"] == "cond-1"
    assert record["condition_type"] == ConditionType.PRICE_ABOVE.value
    assert record["ticker"] == "TEST-TICKER"
    assert record["threshold"] == 0.6
    assert record["current_value"] == 0.61
    assert record["market_data"] == {"foo": "bar"}


def test_webhook_notifier_posts_payload() -> None:
    alert = _make_alert()

    mock_client = MagicMock()
    mock_client.post.return_value = MagicMock()

    with patch("kalshi_research.alerts.notifiers.httpx.Client") as mock_client_cls:
        mock_client_cls.return_value.__enter__.return_value = mock_client
        notifier = WebhookNotifier("https://example.com/webhook")
        notifier.notify(alert)

    mock_client.post.assert_called_once()
    (url,) = mock_client.post.call_args.args
    assert url == "https://example.com/webhook"


def test_webhook_notifier_swallows_http_errors() -> None:
    alert = _make_alert()

    mock_client = MagicMock()
    mock_client.post.side_effect = httpx.HTTPError("boom")

    with patch("kalshi_research.alerts.notifiers.httpx.Client") as mock_client_cls:
        mock_client_cls.return_value.__enter__.return_value = mock_client
        notifier = WebhookNotifier("https://example.com/webhook")
        notifier.notify(alert)


def test_webhook_notifier_swallows_non_2xx_status() -> None:
    alert = _make_alert()

    request = httpx.Request("POST", "https://example.com/webhook")
    response = httpx.Response(500, request=request)
    status_error = httpx.HTTPStatusError("boom", request=request, response=response)

    response_mock = MagicMock()
    response_mock.raise_for_status.side_effect = status_error

    mock_client = MagicMock()
    mock_client.post.return_value = response_mock

    with patch("kalshi_research.alerts.notifiers.httpx.Client") as mock_client_cls:
        mock_client_cls.return_value.__enter__.return_value = mock_client
        notifier = WebhookNotifier("https://example.com/webhook")
        notifier.notify(alert)

    response_mock.raise_for_status.assert_called_once()
