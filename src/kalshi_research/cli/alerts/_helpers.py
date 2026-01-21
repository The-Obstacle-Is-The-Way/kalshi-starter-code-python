"""Shared helpers for alert CLI commands."""

import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from kalshi_research.cli.utils import (
    atomic_write_json,
    load_json_storage_file,
)
from kalshi_research.paths import DEFAULT_ALERT_LOG, DEFAULT_ALERTS_PATH

_ALERT_MONITOR_LOG_PATH = DEFAULT_ALERT_LOG


def get_alerts_file() -> Path:
    """Get path to alerts storage file."""
    return DEFAULT_ALERTS_PATH


def load_alerts() -> dict[str, Any]:
    """Load alerts from storage."""
    alerts_file = get_alerts_file()
    return load_json_storage_file(path=alerts_file, kind="Alerts", required_list_key="conditions")


def save_alerts(data: dict[str, Any]) -> None:
    """Save alerts to storage."""
    alerts_file = get_alerts_file()
    atomic_write_json(alerts_file, data)


def spawn_alert_monitor_daemon(
    *,
    interval: int,
    once: bool,
    max_pages: int | None,
    environment: str,
    output_file: Path | None,
    webhook_url: str | None,
) -> tuple[int, Path]:
    """Spawn the alert monitor as a detached background daemon.

    Returns:
        Tuple of (pid, log_path) for the spawned daemon.

    Raises:
        RuntimeError: If daemon fails to start or log file is locked.
    """
    import errno
    import os

    args = [
        sys.executable,
        "-m",
        "kalshi_research.cli",
        "alerts",
        "monitor",
        "--interval",
        str(interval),
    ]
    if max_pages is not None:
        args.extend(["--max-pages", str(max_pages)])
    if once:
        args.append("--once")
    if output_file is not None:
        args.extend(["--output-file", str(output_file)])
    if webhook_url is not None:
        args.extend(["--webhook-url", webhook_url])

    daemon_env = dict(os.environ)
    daemon_env["KALSHI_ENVIRONMENT"] = environment
    daemon_env.setdefault("PYTHONUNBUFFERED", "1")

    _ALERT_MONITOR_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _ALERT_MONITOR_LOG_PATH.open("a") as log_file:
        if sys.platform != "win32":
            import fcntl

            try:
                fcntl.flock(log_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                if exc.errno in (errno.EACCES, errno.EAGAIN):
                    raise RuntimeError(
                        "Alert monitor daemon appears to already be running (log file is locked): "
                        f"{_ALERT_MONITOR_LOG_PATH}"
                    ) from None
                raise

        popen_kwargs: dict[str, Any] = {
            "stdin": subprocess.DEVNULL,
            "stdout": log_file,
            "stderr": log_file,
            "env": daemon_env,
        }
        if sys.platform == "win32":
            popen_kwargs["creationflags"] = int(getattr(subprocess, "DETACHED_PROCESS", 0)) | int(
                getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            )
        else:
            popen_kwargs["start_new_session"] = True

        proc = subprocess.Popen(args, **popen_kwargs)

    # Quick sanity check: if the child dies immediately (import error, bad args),
    # don't claim the daemon started successfully.
    time.sleep(0.25)
    returncode = proc.poll()
    if isinstance(returncode, int) and (returncode != 0 or not once):
        raise RuntimeError(
            f"Daemon exited immediately with code {returncode}. See logs: {_ALERT_MONITOR_LOG_PATH}"
        )

    return proc.pid, _ALERT_MONITOR_LOG_PATH
