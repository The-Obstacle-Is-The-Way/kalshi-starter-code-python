"""Unit tests for ResearchTaskState persistence."""

import json
from pathlib import Path

import pytest

from kalshi_research.agent.state import ResearchTaskState


@pytest.fixture
def temp_state_dir(tmp_path: Path) -> Path:
    """Create a temporary state directory."""
    return tmp_path / "agent_state"


def test_save_and_load_research_task(temp_state_dir: Path) -> None:
    """Test saving and loading research task state."""
    state = ResearchTaskState(state_dir=temp_state_dir)

    # Save task state
    state.save_research_task(
        ticker="TEST-01JAN25",
        research_id="task-123",
        instructions="Research on test topic",
    )

    # Load it back
    loaded = state.load_research_task("TEST-01JAN25")

    assert loaded is not None
    assert loaded["ticker"] == "TEST-01JAN25"
    assert loaded["research_id"] == "task-123"
    assert loaded["instructions"] == "Research on test topic"
    assert "created_at" in loaded


def test_load_nonexistent_task(temp_state_dir: Path) -> None:
    """Test loading a task that doesn't exist returns None."""
    state = ResearchTaskState(state_dir=temp_state_dir)

    loaded = state.load_research_task("NONEXISTENT-TICKER")

    assert loaded is None


def test_clear_research_task(temp_state_dir: Path) -> None:
    """Test clearing research task state."""
    state = ResearchTaskState(state_dir=temp_state_dir)

    # Save task
    state.save_research_task(
        ticker="TEST-01JAN25",
        research_id="task-456",
        instructions="Test instructions",
    )

    # Verify it exists
    assert state.load_research_task("TEST-01JAN25") is not None

    # Clear it
    state.clear_research_task("TEST-01JAN25")

    # Verify it's gone
    assert state.load_research_task("TEST-01JAN25") is None


def test_state_file_path_sanitization(temp_state_dir: Path) -> None:
    """Test that ticker with path characters is sanitized."""
    state = ResearchTaskState(state_dir=temp_state_dir)

    # Save task with ticker containing path separators
    state.save_research_task(
        ticker="TEST/WITH/SLASHES",
        research_id="task-789",
        instructions="Test",
    )

    # Should be able to load it back
    loaded = state.load_research_task("TEST/WITH/SLASHES")
    assert loaded is not None
    assert loaded["research_id"] == "task-789"


def test_multiple_tickers_isolated(temp_state_dir: Path) -> None:
    """Test that different tickers have isolated state."""
    state = ResearchTaskState(state_dir=temp_state_dir)

    # Save state for two different tickers
    state.save_research_task(
        ticker="TICKER-A",
        research_id="task-a",
        instructions="Instructions A",
    )
    state.save_research_task(
        ticker="TICKER-B",
        research_id="task-b",
        instructions="Instructions B",
    )

    # Each should load independently
    loaded_a = state.load_research_task("TICKER-A")
    loaded_b = state.load_research_task("TICKER-B")

    assert loaded_a is not None
    assert loaded_a["research_id"] == "task-a"
    assert loaded_b is not None
    assert loaded_b["research_id"] == "task-b"

    # Clearing one shouldn't affect the other
    state.clear_research_task("TICKER-A")
    assert state.load_research_task("TICKER-A") is None
    assert state.load_research_task("TICKER-B") is not None


def test_default_state_dir_creation() -> None:
    """Test that default state dir is created if it doesn't exist."""
    # Use default path but don't create it first
    state = ResearchTaskState()

    # Save should create the directory
    state.save_research_task(
        ticker="TEST",
        research_id="test-id",
        instructions="test",
    )

    # Should be able to load it
    loaded = state.load_research_task("TEST")
    assert loaded is not None

    # Clean up
    state.clear_research_task("TEST")


def test_save_research_task_handles_write_failure(
    temp_state_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test save_research_task swallows filesystem write errors."""
    state = ResearchTaskState(state_dir=temp_state_dir)

    def raise_os_error(_self: Path, *_args: object, **_kwargs: object) -> int:
        raise OSError("no space left on device")

    monkeypatch.setattr(Path, "write_text", raise_os_error)

    state.save_research_task(
        ticker="TEST-FAIL",
        research_id="task-999",
        instructions="Test",
    )

    assert not state._get_state_file("TEST-FAIL").exists()


def test_load_research_task_handles_read_failure(
    temp_state_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test load_research_task returns None on filesystem read errors."""
    state = ResearchTaskState(state_dir=temp_state_dir)

    state_file = state._get_state_file("TEST-READ-FAIL")
    state_file.write_text(json.dumps({"research_id": "task-1"}))

    def raise_os_error(_self: Path, *_args: object, **_kwargs: object) -> str:
        raise OSError("permission denied")

    monkeypatch.setattr(Path, "read_text", raise_os_error)

    assert state.load_research_task("TEST-READ-FAIL") is None


def test_load_research_task_handles_invalid_json(temp_state_dir: Path) -> None:
    """Test load_research_task returns None when JSON is corrupted."""
    state = ResearchTaskState(state_dir=temp_state_dir)

    state_file = state._get_state_file("TEST-BAD-JSON")
    state_file.write_text("{not valid json")

    assert state.load_research_task("TEST-BAD-JSON") is None


def test_load_research_task_rejects_non_dict_schema(temp_state_dir: Path) -> None:
    """Test load_research_task rejects valid JSON that isn't an object."""
    state = ResearchTaskState(state_dir=temp_state_dir)

    state_file = state._get_state_file("TEST-NON-DICT")
    state_file.write_text(json.dumps(["not", "a", "dict"]))

    assert state.load_research_task("TEST-NON-DICT") is None


def test_load_research_task_rejects_missing_research_id(temp_state_dir: Path) -> None:
    """Test load_research_task rejects dicts without research_id."""
    state = ResearchTaskState(state_dir=temp_state_dir)

    state_file = state._get_state_file("TEST-MISSING-ID")
    state_file.write_text(json.dumps({"ticker": "TEST-MISSING-ID"}))

    assert state.load_research_task("TEST-MISSING-ID") is None


def test_clear_research_task_handles_delete_failure(
    temp_state_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test clear_research_task swallows filesystem delete errors."""
    state = ResearchTaskState(state_dir=temp_state_dir)
    state.save_research_task(
        ticker="TEST-UNLINK-FAIL",
        research_id="task-2",
        instructions="Test",
    )
    state_file = state._get_state_file("TEST-UNLINK-FAIL")
    assert state_file.exists()

    def raise_os_error(_self: Path, *_args: object, **_kwargs: object) -> None:
        raise OSError("device busy")

    monkeypatch.setattr(Path, "unlink", raise_os_error)

    state.clear_research_task("TEST-UNLINK-FAIL")
    assert state_file.exists()


def test_clear_research_task_noop_when_missing(temp_state_dir: Path) -> None:
    """Test clear_research_task is a no-op when file is missing."""
    state = ResearchTaskState(state_dir=temp_state_dir)
    state.clear_research_task("DOES-NOT-EXIST")
