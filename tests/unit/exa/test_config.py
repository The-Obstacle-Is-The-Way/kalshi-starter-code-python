from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from kalshi_research.exa.config import ExaConfig


def test_from_env_requires_api_key() -> None:
    with patch.dict(os.environ, {}, clear=True), pytest.raises(ValueError, match="EXA_API_KEY"):
        ExaConfig.from_env()


def test_from_env_loads_defaults() -> None:
    with patch.dict(os.environ, {"EXA_API_KEY": "test-key"}, clear=True):
        cfg = ExaConfig.from_env()

    assert cfg.api_key == "test-key"
    assert cfg.base_url == "https://api.exa.ai"
    assert cfg.timeout_seconds == 30.0
