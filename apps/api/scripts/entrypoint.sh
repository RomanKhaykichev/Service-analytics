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
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
