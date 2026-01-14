"""
Scheduler tests - test async scheduling with real asyncio.

These tests verify the scheduler runs tasks at correct intervals.
"""

from __future__ import annotations

import asyncio

import pytest

from kalshi_research.data.scheduler import DataScheduler


class TestDataScheduler:
    """Test DataScheduler functionality."""

    @pytest.mark.asyncio
    async def test_schedule_once_runs_task(self) -> None:
        """A one-time task runs after the specified delay."""
        results: list[str] = []

        async def task() -> None:
            results.append("ran")

        scheduler = DataScheduler()
        await scheduler.schedule_once("test", task, delay_seconds=0.01)
        await scheduler.start()

        # Give time for task to run
        await asyncio.sleep(0.05)
        await scheduler.stop()

        assert results == ["ran"]

    @pytest.mark.asyncio
    async def test_schedule_interval_runs_multiple_times(self) -> None:
        """An interval task runs multiple times."""
        results: list[int] = []
        counter = {"value": 0}

        async def task() -> None:
            counter["value"] += 1
            results.append(counter["value"])

        scheduler = DataScheduler()
        await scheduler.schedule_interval("test", task, interval_seconds=1)
        await scheduler.start()

        # Run for ~2.5 seconds with 1-second interval - should get ~3 runs
        await asyncio.sleep(2.5)
        await scheduler.stop()

        # Should have run at least 2 times
        assert len(results) >= 2

    @pytest.mark.asyncio
    async def test_scheduler_waits_for_start(self) -> None:
        """Tasks don't run until scheduler.start() is called."""
        results: list[str] = []

        async def task() -> None:
            results.append("ran")

        scheduler = DataScheduler()
        await scheduler.schedule_interval("test", task, interval_seconds=1)

        # Don't start, wait a bit
        await asyncio.sleep(0.1)

        assert len(results) == 0  # No runs yet

        # Now start
        await scheduler.start()
        await asyncio.sleep(0.1)
        await scheduler.stop()

        # Should have run after start
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_scheduler_stops_cleanly(self) -> None:
        """Scheduler stops all tasks when stop() is called."""
        results: list[int] = []
        counter = {"value": 0}

        async def task() -> None:
            counter["value"] += 1
            results.append(counter["value"])

        scheduler = DataScheduler()
        await scheduler.schedule_interval("test", task, interval_seconds=1)
        await scheduler.start()

        await asyncio.sleep(1.1)  # One run
        await scheduler.stop()

        count_at_stop = len(results)
        await asyncio.sleep(2)  # Wait more

        # Count shouldn't increase after stop
        assert len(results) == count_at_stop

    @pytest.mark.asyncio
    async def test_scheduler_handles_task_errors(self) -> None:
        """Scheduler continues running even if a task fails."""
        attempts = 0
        first_attempt_event = asyncio.Event()

        async def failing_task() -> None:
            nonlocal attempts
            attempts += 1
            first_attempt_event.set()
            raise RuntimeError("Task failed!")

        scheduler = DataScheduler()
        await scheduler.schedule_interval("test", failing_task, interval_seconds=1)
        await scheduler.start()

        try:
            await asyncio.wait_for(first_attempt_event.wait(), timeout=5)
            assert attempts >= 1

            assert scheduler.tasks, "Scheduler did not create any background tasks"
            runner_task = scheduler.tasks[0]
            if runner_task.done():
                if runner_task.cancelled():
                    raise AssertionError("Scheduler task was cancelled after task exception")
                raise AssertionError(
                    f"Scheduler task stopped after task exception: {runner_task.exception()!r}"
                )
        finally:
            await scheduler.stop()

    @pytest.mark.asyncio
    async def test_scheduler_context_manager(self) -> None:
        """Scheduler works as async context manager."""
        results: list[str] = []

        async def task() -> None:
            results.append("ran")

        scheduler = DataScheduler()
        await scheduler.schedule_once("test", task, delay_seconds=0)

        async with scheduler:
            await asyncio.sleep(0.05)

        assert results == ["ran"]

    @pytest.mark.asyncio
    async def test_multiple_tasks(self) -> None:
        """Multiple tasks can be scheduled concurrently."""
        results: dict[str, int] = {"task1": 0, "task2": 0}

        async def task1() -> None:
            results["task1"] += 1

        async def task2() -> None:
            results["task2"] += 1

        scheduler = DataScheduler()
        await scheduler.schedule_interval("task1", task1, interval_seconds=1)
        await scheduler.schedule_interval("task2", task2, interval_seconds=1)
        await scheduler.start()

        await asyncio.sleep(1.1)
        await scheduler.stop()

        assert results["task1"] >= 1
        assert results["task2"] >= 1
