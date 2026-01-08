from __future__ import annotations

import pytest

from kalshi_research.api.config import Environment, set_environment


@pytest.fixture(autouse=True)
def _reset_api_environment() -> None:
    set_environment(Environment.PRODUCTION)
    yield
    set_environment(Environment.PRODUCTION)
