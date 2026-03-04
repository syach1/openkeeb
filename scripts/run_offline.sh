#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SITE_DIR="$ROOT_DIR/offline-site"

PORT="4173"
if [[ $# -gt 0 && "$1" =~ ^[0-9]+$ ]]; then
    PORT="$1"
    shift
fi

if [[ ! -d "$SITE_DIR" ]]; then
    echo "offline-site directory not found: $SITE_DIR"
    echo "Build it first with: python build_offline_mirror.py --output-dir offline-site"
    exit 1
fi

echo "Serving offline mirror from: $SITE_DIR"
echo "Open in browser: http://127.0.0.1:${PORT}/"
echo "Press Ctrl+C to stop."

exec python "$ROOT_DIR/serve_offline.py" "$PORT" --directory "$SITE_DIR" --bind 127.0.0.1 "$@"
