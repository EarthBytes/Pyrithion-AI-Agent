#!/bin/sh
set -e

wait_for() {
  host="$1"
  port="$2"
  name="$3"
  echo "Waiting for $name at $host:$port..."
  for i in $(seq 1 30); do
    if curl -sf "http://$host:$port" >/dev/null 2>&1 || nc -z "$host" "$port" >/dev/null 2>&1; then
      echo "$name is ready."
      return 0
    fi
    sleep 2
  done
  echo "Timed out waiting for $name"
  exit 1
}

wait_for postgres 5432 postgres
wait_for qdrant 6333 qdrant

python scripts/init_db.py || true
python scripts/load_docs.py || true

exec "$@"
