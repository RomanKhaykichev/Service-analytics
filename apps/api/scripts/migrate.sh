#!/bin/bash
set -e

echo "=========================================="
echo "Service Analytics API - Running Migrations"
echo "=========================================="

# Change to API directory (where alembic.ini is located)
cd "$(dirname "$0")/.." || exit 1

# Run migrations
echo "Running: python -m alembic upgrade head"
python -m alembic upgrade head

if [ $? -eq 0 ]; then
    echo "=========================================="
    echo "✅ Migrations completed successfully!"
    echo "=========================================="
    exit 0
else
    echo "=========================================="
    echo "❌ Migration failed!"
    echo "=========================================="
    exit 1
fi
