#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v docker >/dev/null 2>&1; then
  echo "[ERROR] Docker is not installed or not in PATH." >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "[ERROR] docker compose plugin is not available." >&2
  exit 1
fi

if [ ! -f .env ]; then
  if [ -n "${DEEPSEEK_API_KEY:-}" ] && [ -n "${DASHSCOPE_API_KEY:-}" ]; then
    {
      echo "DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}"
      echo "DASHSCOPE_API_KEY=${DASHSCOPE_API_KEY}"
      echo "KEFU_DATA_DIR=/app/data"
    } > .env
    echo "[INFO] Generated .env from environment variables."
  else
    echo "[ERROR] .env not found and DEEPSEEK_API_KEY / DASHSCOPE_API_KEY are not set." >&2
    echo "Create .env or export the two keys, then run this script again." >&2
    exit 1
  fi
fi

echo "[1/2] Building and starting containers..."
docker compose up -d --build

echo "[2/2] Current status:"
docker compose ps

echo ""
echo "Done. Open: http://localhost:8000"
