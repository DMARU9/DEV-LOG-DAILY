#!/bin/bash
# log_terminal.sh — Terminal History収集用関数
# .bashrc に source して使用

# --- 設定 (必要に応じて変更) ---
LOG_ROOT="/mnt/f/TAKUMI/knowledge"
PROJECT=$(basename "$(git rev-parse --show-toplevel 2>/dev/null)" || echo "unknown")

TERMINAL_LOG_DIR="$LOG_ROOT/logs/terminal/$PROJECT"

# --- コマンド実行時のログ収集関数 ---
log_terminal_command() {
  local exit_code=$?

  # 直前のコマンドを取得（history番号とスペースを除去）
  local last_cmd
  if command -v history &>/dev/null; then
    last_cmd=$(history 1 | sed 's/^[ ]*[0-9]\+[ ]*//')
  else
    return 0
  fi

  # 空コマンドや履歴がない場合はスキップ
  [ -z "$last_cmd" ] && return 0

  local timestamp
  timestamp=$(date -Iseconds)
  local cwd
  cwd=$(pwd)
  local git_branch
  git_branch=$(git symbolic-ref --short HEAD 2>/dev/null || echo "detached")

  # JSONL形式で追記（改行をエスケープ）
  last_cmd=$(echo "$last_cmd" | sed 's/\\/\\\\/g; s/"/\\"/g')

  mkdir -p "$TERMINAL_LOG_DIR"
  local date_str
  date_str=$(date +%Y-%m-%d)
  echo "{\"timestamp\":\"$timestamp\",\"command\":\"$last_cmd\",\"exit_code\":$exit_code,\"cwd\":\"$cwd\",\"git_branch\":\"$git_branch\"}" \
    >> "$TERMINAL_LOG_DIR/history_${date_str}.jsonl"
}

# --- bash用設定 ---
if [[ "${BASH_VERSION:-}" ]]; then
  # PROMPT_COMMANDが未定義の場合は空文字列で初期化
  if [ -z "$PROMPT_COMMAND" ]; then
    PROMPT_COMMAND=""
  fi

  # 既存のPROMPT_COMMANDを保持して追加
  case "$PROMPT_COMMAND" in
    *"log_terminal_command"* ) ;;  # 既に登録済みなら何もしない
    * ) PROMPT_COMMAND="log_terminal_command;${PROMPT_COMMAND}" ;;
  esac

  echo "[terminal-log] bash hook registered (exit_code, cwd, git_branch付き)" >&2
fi
