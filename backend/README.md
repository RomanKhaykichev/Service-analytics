# Service Analytics Backend API

FastAPI backend for Service Analytics dashboard.

## Setup (PowerShell)

```powershell
# Navigate to project root
cd SERVICE-ANALYTICS

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r backend\requirements.txt

# Set PYTHONPATH
$env:PYTHONPATH="backend"

# Run server
uvicorn app.main:app --reload --port 8000
```

Server will be available at: http://localhost:8000

API docs: http://localhost:8000/docs

## Environment Variables

Create `.env` file in project root:

```
PGHOST=localhost
PGPORT=5432
PGDATABASE=your_db_name
PGUSER=your_db_user
PGPASSWORD=your_db_password
```

## Authentication

All API endpoints require `X-User-Id` header with UUID string.

Example:

```powershell
$headers = @{
    "X-User-Id" = "123e4567-e89b-12d3-a456-426614174000"
}

Invoke-RestMethod -Uri "http://localhost:8000/api/shops" -Headers $headers
```

Or with curl:

```bash
curl -H "X-User-Id: 123e4567-e89b-12d3-a456-426614174000" http://localhost:8000/api/shops
```

## API Endpoints

- `GET /health` - Health check
- `GET /api/shops` - List shops
- `GET /api/kpi/global` - Global YTD revenue
- `GET /api/kpi?period=30d&shop_id=...` - Filtered KPI metrics
- `GET /api/charts/revenue-daily?period=30d&shop_id=...` - Daily revenue chart
- `GET /api/charts/stock-current?shop_id=...&limit=200` - Current stock snapshot
- `GET /api/products?period=30d&shop_id=...&q=...&sort=revenue&order=desc&limit=100&offset=0` - Products list
- `GET /api/products/{barcode}?period=30d&shop_id=UUID` - Product detail

## Period Values

- `7d` - Last 7 days
- `30d` - Last 30 days
- `60d` - Last 60 days
- `90d` - Last 90 days
- `all` - All data from 1900-01-01

## Sort Options (products)

- `revenue` - By revenue
- `profit` - By profit
- `returns` - By returns quantity
- `stock` - By stock quantity
- `turnover` - By turnover days
