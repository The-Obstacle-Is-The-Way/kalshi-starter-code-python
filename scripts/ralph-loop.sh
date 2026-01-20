#!/bin/bash
# Ralph Wiggum Loop - runs Claude Code iterations until all tasks complete

cd /Users/ray/Desktop/CLARITY-DIGITAL-TWIN/kalshi-starter-code-python

MAX=50
for i in $(seq 1 $MAX); do
  echo "=== Iteration $i/$MAX ==="
  claude --dangerously-skip-permissions -p "$(cat PROMPT.md)"

  if ! grep -q "^\- \[ \]" PROGRESS.md; then
    echo "All tasks complete!"
    break
  fi

  sleep 2
done

echo "Loop finished."
