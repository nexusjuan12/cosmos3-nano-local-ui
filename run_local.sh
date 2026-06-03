#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
mkdir -p logs outputs

backend_mode="${1:-generator}"

case "$backend_mode" in
  generator)
    backend_cmd="./serve_generator.sh"
    ;;
  reasoner)
    backend_cmd="./serve_reasoner.sh"
    ;;
  ui-only)
    exec ./start_ui.sh
    ;;
  *)
    echo "Usage: $0 [generator|reasoner|ui-only]" >&2
    exit 2
    ;;
esac

if [[ ! -d .venv-cosmos3 ]]; then
  echo "Missing .venv-cosmos3. Run ./install.sh --backend-only first." >&2
  exit 1
fi

echo "Starting Cosmos3 ${backend_mode} backend..."
"$backend_cmd" > "logs/${backend_mode}.log" 2>&1 &
backend_pid=$!
echo "$backend_pid" > "logs/${backend_mode}.pid"

cleanup() {
  if kill -0 "$backend_pid" 2>/dev/null; then
    kill "$backend_pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT

echo "Backend log: logs/${backend_mode}.log"
echo "Starting UI..."
./start_ui.sh
