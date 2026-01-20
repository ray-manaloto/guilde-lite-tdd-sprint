#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="${ROOT_DIR}/.run"
PID_DIR="${RUN_DIR}/pids"
LOG_DIR="${RUN_DIR}/logs"

mkdir -p "${PID_DIR}" "${LOG_DIR}"

BACKEND_PORT="${BACKEND_PORT:-8000}"
AGENT_WEB_PORT="${AGENT_WEB_PORT:-8001}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
FRONTEND_CMD="${FRONTEND_CMD:-}"
DEVCTL_MODE="${DEVCTL_MODE:-}"

frontend_cmd="${FRONTEND_CMD}"
if [[ -z "${frontend_cmd}" ]]; then
  frontend_cmd="node ./node_modules/next/dist/bin/next dev -p ${FRONTEND_PORT}"
fi

declare -a SERVICES=("backend" "agent-web" "frontend")
declare -A SERVICE_DIRS
declare -A SERVICE_CMDS
declare -A SERVICE_PORTS
declare -A SERVICE_MATCH

SERVICE_DIRS["backend"]="${ROOT_DIR}/backend"
SERVICE_CMDS["backend"]="uv run uvicorn app.main:app --reload --port ${BACKEND_PORT}"
SERVICE_PORTS["backend"]="${BACKEND_PORT}"
SERVICE_MATCH["backend"]="uvicorn app.main:app"

SERVICE_DIRS["agent-web"]="${ROOT_DIR}/backend"
SERVICE_CMDS["agent-web"]="uv run guilde_lite_tdd_sprint agent web --port ${AGENT_WEB_PORT}"
SERVICE_PORTS["agent-web"]="${AGENT_WEB_PORT}"
SERVICE_MATCH["agent-web"]="guilde_lite_tdd_sprint"

SERVICE_DIRS["frontend"]="${ROOT_DIR}/frontend"
SERVICE_CMDS["frontend"]="${frontend_cmd}"
SERVICE_PORTS["frontend"]="${FRONTEND_PORT}"
SERVICE_MATCH["frontend"]="next"

TMUX_SESSION="${TMUX_SESSION:-guilde-lite-dev}"

pid_file() {
  echo "${PID_DIR}/$1.pid"
}

log_file() {
  echo "${LOG_DIR}/$1.log"
}

is_running() {
  local pid="$1"
  if [[ -z "${pid}" ]]; then
    return 1
  fi
  kill -0 "${pid}" >/dev/null 2>&1
}

find_pid_on_port() {
  local port="$1"
  local match="$2"
  if ! command -v lsof >/dev/null 2>&1; then
    return 1
  fi
  local pid
  while read -r pid; do
    if [[ -z "${pid}" ]]; then
      continue
    fi
    local cmd
    cmd="$(ps -p "${pid}" -o command=)"
    if [[ "${cmd}" == *"${match}"* ]]; then
      echo "${pid}"
      return 0
    fi
  done < <(lsof -ti "tcp:${port}" 2>/dev/null || true)
  return 1
}

start_service() {
  local name="$1"
  local pid_path
  local log_path
  local dir
  local cmd
  pid_path="$(pid_file "${name}")"
  log_path="$(log_file "${name}")"
  dir="${SERVICE_DIRS[${name}]}"
  cmd="${SERVICE_CMDS[${name}]}"

  if [[ -f "${pid_path}" ]]; then
    local pid
    pid="$(cat "${pid_path}")"
    if is_running "${pid}"; then
      echo "${name}: already running (pid ${pid})"
      return 0
    fi
    rm -f "${pid_path}"
  fi

  local port_pid
  port_pid="$(find_pid_on_port "${SERVICE_PORTS[${name}]}" "${SERVICE_MATCH[${name}]}" || true)"
  if [[ -n "${port_pid}" ]]; then
    echo "${name}: running on port ${SERVICE_PORTS[${name}]} (pid ${port_pid})"
    return 0
  fi

  (
    cd "${dir}" || exit 1
    nohup bash -lc "exec ${cmd}" >"${log_path}" 2>&1 </dev/null &
    echo $! >"${pid_path}"
  )

  sleep 0.4
  local new_pid
  new_pid="$(cat "${pid_path}")"
  if ! is_running "${new_pid}"; then
    echo "${name}: failed to start. Last log lines:"
    tail -n 20 "${log_path}" || true
    rm -f "${pid_path}"
    return 1
  fi
  echo "${name}: started (pid ${new_pid}) on port ${SERVICE_PORTS[${name}]}"
}

stop_service() {
  local name="$1"
  local pid_path
  pid_path="$(pid_file "${name}")"
  if [[ ! -f "${pid_path}" ]]; then
    local port_pid
    port_pid="$(find_pid_on_port "${SERVICE_PORTS[${name}]}" "${SERVICE_MATCH[${name}]}" || true)"
    if [[ -n "${port_pid}" ]]; then
      kill "${port_pid}" >/dev/null 2>&1 || true
      echo "${name}: stopped unmanaged process (pid ${port_pid})"
      return 0
    fi
    echo "${name}: not running"
    return 0
  fi

  local pid
  pid="$(cat "${pid_path}")"
  if ! is_running "${pid}"; then
    local port_pid
    port_pid="$(find_pid_on_port "${SERVICE_PORTS[${name}]}" "${SERVICE_MATCH[${name}]}" || true)"
    if [[ -n "${port_pid}" ]]; then
      kill "${port_pid}" >/dev/null 2>&1 || true
      echo "${name}: stopped unmanaged process (pid ${port_pid})"
      rm -f "${pid_path}"
      return 0
    fi
    echo "${name}: not running"
    rm -f "${pid_path}"
    return 0
  fi

  kill "${pid}" >/dev/null 2>&1 || true
  for _ in {1..20}; do
    if ! is_running "${pid}"; then
      break
    fi
    sleep 0.2
  done

  if is_running "${pid}"; then
    kill -9 "${pid}" >/dev/null 2>&1 || true
  fi

  rm -f "${pid_path}"
  echo "${name}: stopped"
}

status_service() {
  local name="$1"
  local pid_path
  pid_path="$(pid_file "${name}")"
  if [[ -f "${pid_path}" ]]; then
    local pid
    pid="$(cat "${pid_path}")"
    if is_running "${pid}"; then
      echo "${name}: running (pid ${pid}) port ${SERVICE_PORTS[${name}]} log $(log_file "${name}")"
      return 0
    fi
    rm -f "${pid_path}"
  fi
  local port_pid
  port_pid="$(find_pid_on_port "${SERVICE_PORTS[${name}]}" "${SERVICE_MATCH[${name}]}" || true)"
  if [[ -n "${port_pid}" ]]; then
    echo "${name}: running (pid ${port_pid}) port ${SERVICE_PORTS[${name}]} (unmanaged)"
    return 0
  fi
  echo "${name}: stopped"
}

logs_service() {
  local name="$1"
  local log_path
  log_path="$(log_file "${name}")"
  if [[ ! -f "${log_path}" ]]; then
    echo "${name}: no log file"
    return 1
  fi
  tail -n 200 -f "${log_path}"
}

tmux_available() {
  command -v tmux >/dev/null 2>&1
}

tmux_mode() {
  if [[ -n "${DEVCTL_MODE}" ]]; then
    [[ "${DEVCTL_MODE}" == "tmux" ]]
    return
  fi
  tmux_available
}

tmux_session_exists() {
  tmux has-session -t "${TMUX_SESSION}" >/dev/null 2>&1
}

tmux_start() {
  if tmux_session_exists; then
    echo "tmux session '${TMUX_SESSION}' already running"
    return 0
  fi
  tmux new-session -d -s "${TMUX_SESSION}" -n backend \
    "cd ${SERVICE_DIRS[backend]} && ${SERVICE_CMDS[backend]}"
  tmux new-window -t "${TMUX_SESSION}" -n agent-web \
    "cd ${SERVICE_DIRS[agent-web]} && ${SERVICE_CMDS[agent-web]}"
  tmux new-window -t "${TMUX_SESSION}" -n frontend \
    "cd ${SERVICE_DIRS[frontend]} && ${SERVICE_CMDS[frontend]}"
  tmux select-window -t "${TMUX_SESSION}:backend"
  echo "tmux session '${TMUX_SESSION}' started"
}

tmux_stop() {
  if tmux_session_exists; then
    tmux kill-session -t "${TMUX_SESSION}"
    echo "tmux session '${TMUX_SESSION}' stopped"
    return 0
  fi
  return 1
}

tmux_status() {
  if tmux_session_exists; then
    echo "tmux session '${TMUX_SESSION}' is running"
    tmux list-windows -t "${TMUX_SESSION}"
    return 0
  fi
  echo "tmux session '${TMUX_SESSION}' is not running"
  return 1
}

tmux_logs() {
  local name="$1"
  if ! tmux_session_exists; then
    echo "tmux session '${TMUX_SESSION}' is not running"
    return 1
  fi
  tmux select-window -t "${TMUX_SESSION}:${name}"
  tmux attach -t "${TMUX_SESSION}"
}

usage() {
  cat <<EOF
Usage: $(basename "$0") <start|stop|restart|status|logs> [service]

Services: ${SERVICES[*]}
Environment overrides:
  BACKEND_PORT (default ${BACKEND_PORT})
  AGENT_WEB_PORT (default ${AGENT_WEB_PORT})
  FRONTEND_PORT (default ${FRONTEND_PORT})
  FRONTEND_CMD (override frontend command)
  DEVCTL_MODE (tmux|background)
  TMUX_SESSION (default ${TMUX_SESSION})
EOF
}

cmd="${1:-}"
service="${2:-}"

if [[ -z "${cmd}" ]]; then
  usage
  exit 1
fi

targets=("${SERVICES[@]}")
if [[ -n "${service}" ]]; then
  if [[ ! " ${SERVICES[*]} " =~ " ${service} " ]]; then
    echo "Unknown service: ${service}"
    usage
    exit 1
  fi
  targets=("${service}")
fi

case "${cmd}" in
  start)
    if tmux_mode; then
      tmux_start
    else
      for name in "${targets[@]}"; do
        start_service "${name}"
      done
    fi
    ;;
  stop)
    if tmux_mode; then
      if ! tmux_stop; then
        for name in "${targets[@]}"; do
          stop_service "${name}"
        done
      fi
    else
      for name in "${targets[@]}"; do
        stop_service "${name}"
      done
    fi
    ;;
  restart)
    if tmux_mode; then
      tmux_stop || true
      tmux_start
    else
      for name in "${targets[@]}"; do
        stop_service "${name}"
        start_service "${name}"
      done
    fi
    ;;
  status)
    if tmux_mode; then
      tmux_status || true
    else
      for name in "${targets[@]}"; do
        status_service "${name}"
      done
    fi
    ;;
  logs)
    if [[ -z "${service}" ]]; then
      echo "Select a service to tail logs."
      usage
      exit 1
    fi
    if tmux_mode; then
      tmux_logs "${service}"
    else
      logs_service "${service}"
    fi
    ;;
  *)
    usage
    exit 1
    ;;
esac
