"""Exchange models for the Kalshi API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DailySchedule(BaseModel):
    """Single trading session window in ET (HH:MM strings)."""

    model_config = ConfigDict(frozen=True)

    open_time: str
    close_time: str


class WeeklySchedule(BaseModel):
    """Weekly exchange schedule with per-day trading sessions."""

    model_config = ConfigDict(frozen=True)

    start_time: datetime
    end_time: datetime
    monday: list[DailySchedule]
    tuesday: list[DailySchedule]
    wednesday: list[DailySchedule]
    thursday: list[DailySchedule]
    friday: list[DailySchedule]
    saturday: list[DailySchedule]
    sunday: list[DailySchedule]


class MaintenanceWindow(BaseModel):
    """Scheduled maintenance window where trading may be unavailable."""

    model_config = ConfigDict(frozen=True)

    start_datetime: datetime
    end_datetime: datetime


class Schedule(BaseModel):
    """Exchange trading schedule container."""

    model_config = ConfigDict(frozen=True)

    standard_hours: list[WeeklySchedule]
    maintenance_windows: list[MaintenanceWindow]


class ExchangeScheduleResponse(BaseModel):
    """Response schema for `GET /exchange/schedule`."""

    model_config = ConfigDict(frozen=True)

    schedule: Schedule


class ExchangeAnnouncement(BaseModel):
    """Single exchange-wide announcement from `GET /exchange/announcements`."""

    model_config = ConfigDict(frozen=True)

    type: str
    message: str
    delivery_time: datetime
    status: str


class ExchangeAnnouncementsResponse(BaseModel):
    """Response schema for `GET /exchange/announcements`."""

    model_config = ConfigDict(frozen=True)

    announcements: list[ExchangeAnnouncement]


class UserDataTimestampResponse(BaseModel):
    """Response schema for `GET /exchange/user_data_timestamp`."""

    model_config = ConfigDict(frozen=True)

    as_of_time: datetime
