"""Async scheduler for data collection tasks with drift correction."""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

logger = structlog.get_logger()


class DataScheduler:
    """
    Async scheduler for data collection tasks with drift correction.

    Uses monotonic time to prevent drift from execution time or
    system clock changes.
    """

    def __init__(self) -> None:
        """Initialize the scheduler."""
        self.tasks: list[asyncio.Task[None]] = []
        self.running = False

    async def schedule_interval(
        self,
        name: str,
        func: Callable[[], Awaitable[None]],
        interval_seconds: int,
    ) -> None:
        """
        Schedule a function to run at fixed intervals.

        Corrects for execution time drift using monotonic clock.

        Args:
            name: Human-readable name for logging
            func: Async function to call
            interval_seconds: Interval between runs in seconds
        """

        async def runner() -> None:
            # Use monotonic time for drift correction (safer than wall clock)
            next_run = time.monotonic()
            while True:
                if not self.running:
                    # Allow scheduling before start(); tasks will wait until running = True.
                    await asyncio.sleep(0.1)
                    next_run = time.monotonic()
                    continue

                now = time.monotonic()
                if now >= next_run:
                    try:
                        logger.info("Running scheduled task", task_name=name)
                        await func()
                        logger.info("Scheduled task completed", task_name=name)
                    except Exception:
                        logger.exception("Scheduled task failed", task_name=name)

                    # Calculate next run time
                    next_run += interval_seconds
                    # If we fell way behind, skip intervals to catch up
                    while next_run <= time.monotonic():
                        next_run += interval_seconds

                # Sleep until next run
                sleep_duration = max(0, next_run - time.monotonic())
                await asyncio.sleep(sleep_duration)

        task = asyncio.create_task(runner())
        self.tasks.append(task)

    async def schedule_once(
        self,
        name: str,
        func: Callable[[], Awaitable[None]],
        delay_seconds: float = 0,
    ) -> None:
        """
        Schedule a function to run once after a delay.

        Args:
            name: Human-readable name for logging
            func: Async function to call
            delay_seconds: Delay before running
        """

        async def runner() -> None:
            await asyncio.sleep(delay_seconds)
            if self.running:
                try:
                    logger.info("Running one-time task", task_name=name)
                    await func()
                    logger.info("One-time task completed", task_name=name)
                except Exception:
                    logger.exception("One-time task failed", task_name=name)

        task = asyncio.create_task(runner())
        self.tasks.append(task)

    async def start(self) -> None:
        """Start the scheduler."""
        self.running = True
        logger.info("Scheduler started")

    async def stop(self) -> None:
        """Stop all scheduled tasks."""
        self.running = False
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()
        logger.info("Scheduler stopped")

    async def __aenter__(self) -> DataScheduler:
        """Enter async context manager."""
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit async context manager."""
        await self.stop()
