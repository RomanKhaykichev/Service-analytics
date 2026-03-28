#!/bin/bash
set -e

echo "=========================================="
echo "Service Analytics API - Starting..."
echo "=========================================="

# Wait for database to be ready (with retry)
echo "Waiting for database to be ready..."
RETRIES=30
until python -c "import psycopg2; psycopg2.connect('${DATABASE_URL}')" 2>/dev/null || [ $RETRIES -eq 0 ]; do
  echo "Waiting for database... $RETRIES retries left"
  RETRIES=$((RETRIES-1))
  sleep 2
done

if [ $RETRIES -eq 0 ]; then
  echo "ERROR: Database is not available after 60 seconds"
  exit 1
fi

echo "Database is ready!"

# Run migrations
echo "=========================================="
echo "Running Alembic migrations..."
echo "=========================================="
cd /app
python -m alembic upgrade head

if [ $? -ne 0 ]; then
  echo "ERROR: Migration failed!"
  exit 1
fi

echo "Migrations completed successfully!"

# Start the API
echo "=========================================="
echo "Starting API server..."
echo "=========================================="
# Behind nginx/Cloudflare: --proxy-headers + --forwarded-allow-ips so request.url/scheme see HTTPS.
# FORWARDED_ALLOW_IPS: comma-separated; default loopback + RFC1918 (Docker bridge). Set to * only on isolated networks.
UVICORN_PROXY_HEADERS="${UVICORN_PROXY_HEADERS:-1}"
FORWARDED_ALLOW_IPS="${FORWARDED_ALLOW_IPS:-127.0.0.1,172.16.0.0/12,10.0.0.0/8}"
if [ "$UVICORN_PROXY_HEADERS" = "1" ] || [ "$UVICORN_PROXY_HEADERS" = "true" ] || [ "$UVICORN_PROXY_HEADERS" = "yes" ]; then
  echo "Uvicorn: --proxy-headers --forwarded-allow-ips=$FORWARDED_ALLOW_IPS"
  exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips "$FORWARDED_ALLOW_IPS"
else
  exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
fi
