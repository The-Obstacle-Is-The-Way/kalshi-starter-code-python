#!/usr/bin/env bash
# Ralph Wiggum Loop (repo-local operator script)
#
# Default tmux session name: kalshi-ralph (to avoid collisions with other repos).
# Override via:
#   RALPH_TMUX_SESSION=my-session ./scripts/ralph-loop.sh start
#
# Typical usage:
#   ./scripts/ralph-loop.sh start   # start (or re-attach) in tmux
#   ./scripts/ralph-loop.sh attach  # attach to existing session
#   ./scripts/ralph-loop.sh stop    # kill session
#
# Advanced:
#   ./scripts/ralph-loop.sh run     # run loop in current terminal/tmux pane

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

DEFAULT_SESSION="kalshi-ralph"
SESSION_NAME="${RALPH_TMUX_SESSION:-${DEFAULT_SESSION}}"

COMMAND="${1:-start}"

usage() {
  cat <<EOF
Usage: $(basename "$0") [command]

Commands:
  start   Start (or re-attach) the Ralph loop in a tmux session (default)
  attach  Attach to the tmux session
  stop    Kill the tmux session
  status  Show session status + last pane output
  run     Run the loop in the current terminal (no tmux management)

Environment:
  RALPH_TMUX_SESSION   tmux session name (default: ${DEFAULT_SESSION})
  RALPH_MAX            max iterations (default: 50)
  RALPH_SLEEP_SECONDS  sleep between iterations (default: 2)
EOF
}

require_tmux() {
  if ! command -v tmux >/dev/null 2>&1; then
    echo "Error: tmux is required for '${COMMAND}'. Install tmux or run: $0 run" >&2
    exit 1
  fi
}

run_loop() {
  cd "${REPO_ROOT}"

  if ! command -v claude >/dev/null 2>&1; then
    echo "Error: 'claude' (Claude Code CLI) not found in PATH." >&2
    exit 1
  fi

  if [[ ! -f "PROMPT.md" || ! -f "PROGRESS.md" ]]; then
    echo "Error: PROMPT.md / PROGRESS.md not found in repo root: ${REPO_ROOT}" >&2
    exit 1
  fi

  local max="${RALPH_MAX:-50}"
  local sleep_seconds="${RALPH_SLEEP_SECONDS:-2}"

  for i in $(seq 1 "${max}"); do
    echo "=== Iteration ${i}/${max} ==="
    claude --dangerously-skip-permissions -p "$(cat PROMPT.md)"

    if ! grep -q "^\- \[ \]" PROGRESS.md; then
      echo "All tasks complete!"
      break
    fi

    sleep "${sleep_seconds}"
  done

  echo "Loop finished."
}

case "${COMMAND}" in
  start)
    require_tmux
    if [[ -z "${TMUX-}" ]]; then
      if ! tmux has-session -t "${SESSION_NAME}" 2>/dev/null; then
        tmux new-session -d -s "${SESSION_NAME}" "${SCRIPT_DIR}/ralph-loop.sh run"
      fi
      exec tmux attach -t "${SESSION_NAME}"
    fi
    run_loop
    ;;
  attach)
    require_tmux
    exec tmux attach -t "${SESSION_NAME}"
    ;;
  stop)
    require_tmux
    tmux kill-session -t "${SESSION_NAME}"
    ;;
  status)
    require_tmux
    if tmux has-session -t "${SESSION_NAME}" 2>/dev/null; then
      tmux ls | grep -E "^${SESSION_NAME}:" || true
      echo "---"
      tmux capture-pane -pt "${SESSION_NAME}" -S -200 || true
    else
      echo "No tmux session named '${SESSION_NAME}'." >&2
      exit 1
    fi
    ;;
  run)
    run_loop
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
