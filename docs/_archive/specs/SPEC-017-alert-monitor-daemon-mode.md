# SPEC-017: Alert Monitor Daemon Mode

**Status:** ✅ Implemented (detached subprocess + log file)
**Priority:** P3 (Deferred item; complete the CLI surface)
**Estimated Complexity:** Low–Medium
**Dependencies:** SPEC-005 (Alerts & Notifications), SPEC-010 (CLI Completeness)

---

## Implementation References

- `src/kalshi_research/cli/alerts.py` (`kalshi alerts monitor`)
- `docs/CLI_REFERENCE.md` (`kalshi alerts monitor` help/behavior)
- `docs/_archive/todo/TODO-002-remaining-work-audit.md` (Issue #2)

---

## 1. Overview

`kalshi alerts monitor` supports both foreground monitoring and daemon mode.

`--daemon` starts a detached background process that runs the same monitor loop and writes logs to `data/alert_monitor.log`.

This spec defines an **OS-friendly, testable daemon mode** that runs the monitor loop in the background and immediately returns control to the user.

### 1.1 Goals

- Implement `kalshi alerts monitor --daemon` without recursion or busy loops.
- Print a clear “started” message including PID.
- Redirect daemon stdout/stderr to a log file under `data/`.
- Preserve existing behavior for foreground mode and `--once`.

### 1.2 Non-Goals

- Full service management (systemd/launchd), auto-restart, or watchdog supervision.
- A dedicated “stop” command / pidfile management (nice-to-have; out of scope).
- Log rotation.

---

## 2. User Experience

### 2.1 CLI

Command:

```bash
kalshi alerts monitor --daemon [--interval SEC] [--max-pages N] [--once]
```

Expected behavior:

- Parent process:
  - Validates there are alerts configured (same as foreground mode).
  - Spawns a detached background process running the same command **without** `--daemon`.
  - Prints PID and log file location.
  - Exits with status code `0`.
- Daemon process:
  - Runs the same monitoring loop as foreground mode.
  - Writes all output to `data/alert_monitor.log`.

### 2.2 Stopping the daemon

- User stops the daemon with `kill <PID>` (POSIX) or Task Manager/Process Explorer (Windows).

---

## 3. Technical Design

### 3.1 Daemonization mechanism

Preferred approach: **spawn a detached subprocess** rather than `os.fork()` + manual FD manipulation.

Rationale:

- Works reliably even in environments where `fork()` is discouraged.
- Is easy to unit test by mocking `subprocess.Popen`.
- Keeps the “real” monitor loop unchanged.

### 3.2 Process launch details

- Launch command:
  - `sys.executable -m kalshi_research.cli alerts monitor ...`
  - Pass through `--interval`, `--max-pages`, and `--once`.
  - Omit `--daemon` to prevent recursion.
- Environment:
  - Ensure `KALSHI_ENVIRONMENT` is set in the daemon process to match the parent CLI environment.
- Detach:
  - POSIX: `start_new_session=True`
  - Windows: `creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP`
- Redirect IO:
  - `stdin=subprocess.DEVNULL`
  - `stdout=log_file`, `stderr=log_file` where `log_file` is opened in append mode.
- Ensure `data/` exists before opening the log file.

### 3.3 Safety and invariants

- If there are no configured alerts, `--daemon` should not spawn a process (it should behave like foreground mode: print “No alerts configured…” and exit `0`).
- If spawning fails, print an error and exit non-zero.

---

## 4. Testing Plan (TDD)

Add unit tests for `--daemon` behavior:

1. **Spawns background process**
   - Given at least one alert is configured
   - When `runner.invoke(app, ["alerts", "monitor", "--daemon", "--interval", "5"])`
   - Then:
     - `subprocess.Popen` called once with expected args
     - CLI exits `0` and prints PID/log path
2. **No spawn when no alerts configured**
   - Given `_load_alerts()` returns no conditions
   - When `--daemon` is used
   - Then:
     - `subprocess.Popen` not called
     - Output contains “No alerts configured…”

All existing tests must remain green.

---

## 5. Documentation Updates

- Update `docs/CLI_REFERENCE.md` to describe `--daemon` as implemented, including the log file path.
- Update `docs/_todo/README.md` and `docs/_archive/todo/TODO-002-remaining-work-audit.md` to mark the deferred item as completed.
