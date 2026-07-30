#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PORT="${PORT:-8000}"
HOST="${HOST:-0.0.0.0}"
LOG_FILE="${LOG_FILE:-/tmp/office_supplies_${PORT}.log}"
PID_FILE="${PID_FILE:-/tmp/office_supplies_${PORT}.pid}"

cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-$ROOT_DIR/venv/bin/python}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="${PYTHON_BIN_FALLBACK:-python3}"
fi

find_listen_pid() {
  lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null | head -n 1 || true
}

start_server() {
  local pid
  pid="$(find_listen_pid)"
  if [[ -n "$pid" ]]; then
    echo "already running: pid=$pid port=$PORT"
    exit 0
  fi

  nohup setsid "$PYTHON_BIN" manage.py runserver "$HOST:$PORT" --noreload > "$LOG_FILE" 2>&1 < /dev/null &
  local new_pid=$!
  echo "$new_pid" > "$PID_FILE"
  sleep 1

  local probe
  probe="$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:${PORT}/" || true)"
  if [[ "$probe" == "000" ]]; then
    echo "start failed. check log: $LOG_FILE"
    exit 1
  fi

  echo "started: pid=$new_pid port=$PORT http=$probe"
}

stop_server() {
  local pid
  pid="$(find_listen_pid)"
  if [[ -z "$pid" ]]; then
    echo "already stopped"
    exit 0
  fi

  kill "$pid" || true
  sleep 1

  local remain
  remain="$(find_listen_pid)"
  if [[ -n "$remain" ]]; then
    kill -9 "$remain" || true
  fi

  rm -f "$PID_FILE"
  echo "stopped: port=$PORT"
}

status_server() {
  local pid
  pid="$(find_listen_pid)"
  if [[ -z "$pid" ]]; then
    echo "stopped"
    exit 1
  fi

  local probe
  probe="$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:${PORT}/" || true)"
  echo "running: pid=$pid port=$PORT http=$probe log=$LOG_FILE"
}

logs_server() {
  tail -n 50 "$LOG_FILE"
}

case "${1:-}" in
  start)
    start_server
    ;;
  stop)
    stop_server
    ;;
  restart)
    stop_server || true
    start_server
    ;;
  status)
    status_server
    ;;
  logs)
    logs_server
    ;;
  *)
    echo "usage: $0 {start|stop|restart|status|logs}"
    exit 2
    ;;
esac
