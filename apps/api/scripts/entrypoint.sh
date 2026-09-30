#!/bin/bash
set -e

echo "=========================================="
echo "Service Analytics API - Starting..."
echo "=========================================="

echo "Waiting for database to be ready..."
python /app/scripts/wait_for_db.py

echo "=========================================="
echo "Running Alembic migrations..."
echo "=========================================="
cd /app
python -m alembic upgrade head

echo "Migrations completed successfully!"

echo "=========================================="
echo "Starting API server..."
echo "=========================================="
UVICORN_PROXY_HEADERS="${UVICORN_PROXY_HEADERS:-1}"
FORWARDED_ALLOW_IPS="${FORWARDED_ALLOW_IPS:-127.0.0.1,172.16.0.0/12,10.0.0.0/8}"
if [ "$UVICORN_PROXY_HEADERS" = "1" ] || [ "$UVICORN_PROXY_HEADERS" = "true" ] || [ "$UVICORN_PROXY_HEADERS" = "yes" ]; then
  echo "Uvicorn: --proxy-headers --forwarded-allow-ips=$FORWARDED_ALLOW_IPS"
  exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips "$FORWARDED_ALLOW_IPS"
else
  exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
fi
