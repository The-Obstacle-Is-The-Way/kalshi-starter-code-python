from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_golden_response(*relative_parts: str) -> dict[str, Any]:
    """
    Load a `tests/fixtures/golden/**.json` fixture and return its raw `response` object.

    Fixtures in this repo follow the pattern:

    {
      "_metadata": {...},
      "response": {...}
    }
    """
    fixture_path = _golden_root() / Path(*relative_parts)
    data = json.loads(fixture_path.read_text())
    response = data.get("response")
    if not isinstance(response, dict):
        raise TypeError(f"Golden fixture {fixture_path} missing a 'response' object.")
    return response


def _golden_root() -> Path:
    repo_root = Path(__file__).resolve().parents[1]
    return repo_root / "tests" / "fixtures" / "golden"
