"""Exchange status endpoint mixin."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kalshi_research.api.models.exchange import (
    ExchangeAnnouncementsResponse,
    ExchangeScheduleResponse,
)


class ExchangeMixin:
    """Mixin providing exchange-related endpoints."""

    if TYPE_CHECKING:
        # Implemented by ClientBase
        async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]: ...

    async def get_exchange_status(self) -> dict[str, Any]:
        """Check if exchange is operational."""
        result: dict[str, Any] = await self._get("/exchange/status")
        return result

    async def get_exchange_schedule(self) -> ExchangeScheduleResponse:
        """Fetch the exchange schedule (standard hours + maintenance windows)."""
        data = await self._get("/exchange/schedule")
        return ExchangeScheduleResponse.model_validate(data)

    async def get_exchange_announcements(self) -> ExchangeAnnouncementsResponse:
        """Fetch exchange-wide announcements."""
        data = await self._get("/exchange/announcements")
        return ExchangeAnnouncementsResponse.model_validate(data)
