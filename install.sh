#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

mode="${1:---all}"

case "$mode" in
  --all|--ui-only|--backend-only)
    ;;
  *)
    echo "Usage: $0 [--all|--ui-only|--backend-only]" >&2
    exit 2
    ;;
esac

install_ui() {
  python3 -m pip install -U -r requirements.txt
}

if [[ "$mode" == "--all" || "$mode" == "--ui-only" ]]; then
  install_ui
fi

if [[ "$mode" == "--all" || "$mode" == "--backend-only" ]]; then
  ./install_backend.sh
fi

echo
echo "Install complete."
echo "Authenticate with Hugging Face before generation if needed:"
echo "  source .venv-cosmos3/bin/activate && hf auth login"
echo
echo "Start video generation backend:"
echo "  ./serve_generator.sh"
echo
echo "Start UI:"
echo "  ./start_ui.sh"
