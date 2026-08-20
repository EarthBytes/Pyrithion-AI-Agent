#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [ ! -f .env ]; then
  echo "No .env found. Running setup first..."
  bash scripts/setup.sh
  exit 0
fi

docker compose -f docker/docker-compose.yml --env-file .env up --build --force-recreate
