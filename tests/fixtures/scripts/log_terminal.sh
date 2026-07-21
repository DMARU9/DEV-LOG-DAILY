#!/bin/bash
# log_terminal.sh — Test fixture (simplified)
LOG_ROOT="/tmp/test-logs"
PROJECT="test-project"
TERMINAL_LOG_DIR="$LOG_ROOT/logs/terminal/$PROJECT"
log_terminal_command() {
  local exit_code=$?
  local last_cmd="echo hello"
  local timestamp
  timestamp=$(date -Iseconds)
  local cwd
  cwd=$(pwd)
  mkdir -p "$TERMINAL_LOG_DIR"
  local date_str
  date_str=$(date +%Y-%m-%d)
  echo "{\"timestamp\":\"$timestamp\",\"command\":\"$last_cmd\",\"exit_code\":$exit_code,\"cwd\":\"$cwd\"}" \
    >> "$TERMINAL_LOG_DIR/history_${date_str}.jsonl"
}
