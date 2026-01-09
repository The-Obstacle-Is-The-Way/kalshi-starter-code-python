"""Simple file-based cache for Exa API responses."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import structlog

from kalshi_research.paths import DEFAULT_DATA_DIR

if TYPE_CHECKING:
    from pathlib import Path

logger = structlog.get_logger()


@dataclass(frozen=True)
class CacheEntry:
    """A cached response with metadata."""

    key: str
    data: dict[str, Any]
    created_at: datetime
    expires_at: datetime


class ExaCache:
    """Simple JSON-on-disk cache keyed by operation + params."""

    def __init__(
        self,
        cache_dir: Path | None = None,
        *,
        default_ttl: timedelta = timedelta(hours=24),
    ) -> None:
        self._cache_dir = cache_dir or (DEFAULT_DATA_DIR / "exa_cache")
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._default_ttl = default_ttl

    def _make_key(self, operation: str, params: dict[str, Any]) -> str:
        param_str = json.dumps(params, sort_keys=True, default=str, separators=(",", ":"))
        content = f"{operation}:{param_str}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    def _path_for_key(self, key: str) -> Path:
        return self._cache_dir / f"{key}.json"

    def get(self, operation: str, params: dict[str, Any]) -> dict[str, Any] | None:
        """Return cached data when present and not expired."""
        key = self._make_key(operation, params)
        path = self._path_for_key(key)

        if not path.exists():
            return None

        try:
            with path.open(encoding="utf-8") as f:
                entry = json.load(f)

            expires_at = datetime.fromisoformat(entry["expires_at"])
            if datetime.now(UTC) > expires_at:
                path.unlink(missing_ok=True)
                return None

            logger.debug("Exa cache hit", operation=operation, key=key)
            data = entry["data"]
            if not isinstance(data, dict):
                raise TypeError("Cached 'data' must be a dict")
            return data

        except Exception as e:
            logger.warning(
                "Exa cache read failed; evicting entry",
                operation=operation,
                key=key,
                error=str(e),
            )
            path.unlink(missing_ok=True)
            return None

    def set(
        self,
        operation: str,
        params: dict[str, Any],
        data: dict[str, Any],
        *,
        ttl: timedelta | None = None,
    ) -> None:
        """Store response data for an operation."""
        key = self._make_key(operation, params)
        path = self._path_for_key(key)

        now = datetime.now(UTC)
        ttl = ttl or self._default_ttl

        entry = {
            "key": key,
            "operation": operation,
            "params": params,
            "data": data,
            "created_at": now.isoformat(),
            "expires_at": (now + ttl).isoformat(),
        }

        with path.open("w", encoding="utf-8") as f:
            json.dump(entry, f, indent=2, default=str, sort_keys=True)

        logger.debug(
            "Exa cache set",
            operation=operation,
            key=key,
            ttl_seconds=int(ttl.total_seconds()),
        )

    def clear(self) -> int:
        """Clear all cache entries. Returns number of files removed."""
        count = 0
        for path in self._cache_dir.glob("*.json"):
            path.unlink(missing_ok=True)
            count += 1
        return count

    def clear_expired(self) -> int:
        """Clear only expired cache entries. Returns number of files removed."""
        now = datetime.now(UTC)
        count = 0

        for path in self._cache_dir.glob("*.json"):
            try:
                with path.open(encoding="utf-8") as f:
                    entry = json.load(f)
                expires_at = datetime.fromisoformat(entry["expires_at"])
                if now > expires_at:
                    path.unlink(missing_ok=True)
                    count += 1
            except Exception:
                path.unlink(missing_ok=True)
                count += 1

        return count
