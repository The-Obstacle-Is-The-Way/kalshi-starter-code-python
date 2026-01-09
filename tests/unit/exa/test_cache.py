from __future__ import annotations

import json
from datetime import timedelta
from typing import TYPE_CHECKING

from kalshi_research.exa.cache import ExaCache

if TYPE_CHECKING:
    from pathlib import Path


def test_cache_round_trip(tmp_path: Path) -> None:
    cache = ExaCache(tmp_path, default_ttl=timedelta(hours=1))
    params = {"query": "hello", "num_results": 3}
    payload = {"requestId": "req_1", "results": []}

    cache.set("search", params, payload)
    cached = cache.get("search", {"num_results": 3, "query": "hello"})

    assert cached == payload


def test_cache_expired_entry_is_evicted(tmp_path: Path) -> None:
    cache = ExaCache(tmp_path, default_ttl=timedelta(hours=1))
    params = {"query": "hello"}
    payload = {"requestId": "req_1", "results": []}

    cache.set("search", params, payload, ttl=timedelta(seconds=-1))
    assert cache.get("search", params) is None
    assert cache.clear() == 0


def test_cache_corrupt_entry_is_evicted(tmp_path: Path) -> None:
    cache = ExaCache(tmp_path, default_ttl=timedelta(hours=1))
    params = {"query": "hello"}
    cache.set("search", params, {"ok": True})

    # Corrupt the first cache file.
    files = list(tmp_path.glob("*.json"))
    assert len(files) == 1
    files[0].write_text("{broken json", encoding="utf-8")

    assert cache.get("search", params) is None
    assert not files[0].exists()


def test_clear_expired_only_removes_expired(tmp_path: Path) -> None:
    cache = ExaCache(tmp_path, default_ttl=timedelta(hours=1))

    cache.set("search", {"query": "expired"}, {"ok": True}, ttl=timedelta(seconds=-1))
    cache.set("search", {"query": "active"}, {"ok": True})

    removed = cache.clear_expired()
    assert removed == 1

    active_files = list(tmp_path.glob("*.json"))
    assert len(active_files) == 1

    entry = json.loads(active_files[0].read_text(encoding="utf-8"))
    assert entry["params"]["query"] == "active"
