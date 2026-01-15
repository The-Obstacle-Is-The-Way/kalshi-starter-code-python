"""Unit tests for Kalshi credential resolution."""

from __future__ import annotations

from kalshi_research.api.config import Environment
from kalshi_research.api.credentials import get_kalshi_auth_env_var_names, resolve_kalshi_auth_env


def test_get_kalshi_auth_env_var_names_normalizes_environment() -> None:
    assert get_kalshi_auth_env_var_names(environment=Environment.DEMO) == (
        "KALSHI_DEMO_KEY_ID",
        "KALSHI_DEMO_PRIVATE_KEY_PATH",
        "KALSHI_DEMO_PRIVATE_KEY_B64",
    )
    assert get_kalshi_auth_env_var_names(environment="  dEmO  ") == (
        "KALSHI_DEMO_KEY_ID",
        "KALSHI_DEMO_PRIVATE_KEY_PATH",
        "KALSHI_DEMO_PRIVATE_KEY_B64",
    )
    assert get_kalshi_auth_env_var_names(environment=Environment.PRODUCTION) == (
        "KALSHI_KEY_ID",
        "KALSHI_PRIVATE_KEY_PATH",
        "KALSHI_PRIVATE_KEY_B64",
    )


def test_resolve_kalshi_auth_env_demo_prefers_demo_vars(monkeypatch) -> None:
    monkeypatch.setenv("KALSHI_KEY_ID", "prod-key-id")
    monkeypatch.setenv("KALSHI_PRIVATE_KEY_PATH", "/tmp/prod.pem")
    monkeypatch.setenv("KALSHI_PRIVATE_KEY_B64", "prod-b64")

    monkeypatch.setenv("KALSHI_DEMO_KEY_ID", "demo-key-id")
    monkeypatch.setenv("KALSHI_DEMO_PRIVATE_KEY_PATH", "/tmp/demo.pem")
    monkeypatch.setenv("KALSHI_DEMO_PRIVATE_KEY_B64", "demo-b64")

    key_id, private_key_path, private_key_b64 = resolve_kalshi_auth_env(environment="demo")
    assert (key_id, private_key_path, private_key_b64) == (
        "demo-key-id",
        "/tmp/demo.pem",
        "demo-b64",
    )


def test_resolve_kalshi_auth_env_demo_falls_back_to_prod_vars(monkeypatch) -> None:
    monkeypatch.delenv("KALSHI_DEMO_KEY_ID", raising=False)
    monkeypatch.delenv("KALSHI_DEMO_PRIVATE_KEY_PATH", raising=False)
    monkeypatch.delenv("KALSHI_DEMO_PRIVATE_KEY_B64", raising=False)

    monkeypatch.setenv("KALSHI_KEY_ID", "prod-key-id")
    monkeypatch.setenv("KALSHI_PRIVATE_KEY_PATH", "/tmp/prod.pem")
    monkeypatch.setenv("KALSHI_PRIVATE_KEY_B64", "prod-b64")

    key_id, private_key_path, private_key_b64 = resolve_kalshi_auth_env(
        environment=Environment.DEMO
    )
    assert (key_id, private_key_path, private_key_b64) == (
        "prod-key-id",
        "/tmp/prod.pem",
        "prod-b64",
    )
