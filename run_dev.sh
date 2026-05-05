#!/bin/bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [ -f ".env" ]; then
  while IFS='=' read -r key value; do
    [[ "$key" =~ ^#.*$ || -z "$key" ]] && continue
    export "$key=$value"
  done < .env
fi

uvicorn Application.API.Main_fixed:app \
  --host 0.0.0.0 \
  --port 8000 \
  --reload \
  --reload-dir "$ROOT/Application" \
  --reload-dir "$ROOT/Domain"
