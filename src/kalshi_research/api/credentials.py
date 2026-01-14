"""Helpers for resolving Kalshi API credentials from environment variables."""

from __future__ import annotations

import os

from kalshi_research.api.config import Environment, get_config


def _normalize_environment(environment: Environment | str | None) -> Environment:
    if environment is None:
        return get_config().environment
    if isinstance(environment, Environment):
        return environment
    return Environment(environment.strip().lower())


def get_kalshi_auth_env_var_names(
    *, environment: Environment | str | None = None
) -> tuple[str, str, str]:
    """Return the preferred env var names for Kalshi auth in the given environment."""
    env = _normalize_environment(environment)
    if env == Environment.DEMO:
        return (
            "KALSHI_DEMO_KEY_ID",
            "KALSHI_DEMO_PRIVATE_KEY_PATH",
            "KALSHI_DEMO_PRIVATE_KEY_B64",
        )
    return ("KALSHI_KEY_ID", "KALSHI_PRIVATE_KEY_PATH", "KALSHI_PRIVATE_KEY_B64")


def resolve_kalshi_auth_env(
    *, environment: Environment | str | None = None
) -> tuple[str | None, str | None, str | None]:
    """Resolve Kalshi auth credentials for the given environment.

    If `environment` is demo, this prefers `KALSHI_DEMO_*` variables and falls back to the
    non-prefixed variables for backward compatibility.
    """
    env = _normalize_environment(environment)

    if env == Environment.DEMO:
        key_id = os.getenv("KALSHI_DEMO_KEY_ID") or os.getenv("KALSHI_KEY_ID")
        private_key_path = os.getenv("KALSHI_DEMO_PRIVATE_KEY_PATH") or os.getenv(
            "KALSHI_PRIVATE_KEY_PATH"
        )
        private_key_b64 = os.getenv("KALSHI_DEMO_PRIVATE_KEY_B64") or os.getenv(
            "KALSHI_PRIVATE_KEY_B64"
        )
        return key_id, private_key_path, private_key_b64

    return (
        os.getenv("KALSHI_KEY_ID"),
        os.getenv("KALSHI_PRIVATE_KEY_PATH"),
        os.getenv("KALSHI_PRIVATE_KEY_B64"),
    )
