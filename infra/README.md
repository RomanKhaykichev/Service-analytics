# Infrastructure

This directory contains infrastructure configuration and smoke tests for the Service Analytics service.

## Docker Compose

The main `docker-compose.yml` file in the project root defines the complete stack:

- **postgres**: PostgreSQL 16 database
- **api**: FastAPI application with automatic migrations

### Usage

```bash
# Start all services
docker compose up --build

# Start in background
docker compose up --build -d

# Stop services
docker compose down

# View logs
docker compose logs -f api
docker compose logs -f db
```

### Environment Variables

Create a `.env` file in the project root based on `.env.example`:

```bash
cp .env.example .env
```

Key variables:
- `DATABASE_URL`: PostgreSQL connection string
- `DB_SCHEMA`: Database schema (default: `app`)
- `APP_ENV`: Environment (dev/prod)
- `DEFAULT_DEV_USER_ID`: Default user ID for dev mode
- `JWT_SECRET`: JWT secret key (change in production!)

## Smoke Tests

The `smoke_test.py` script verifies that critical endpoints are working after deployment.

### Usage

```bash
# Run smoke tests (uses X-User-Id header in dev mode)
python infra/smoke_test.py

# With custom base URL
API_BASE_URL=http://localhost:8000 python infra/smoke_test.py

# With JWT token (production)
SMOKE_TEST_TOKEN=your-jwt-token python infra/smoke_test.py

# With custom user ID
SMOKE_TEST_USER_ID=your-uuid python infra/smoke_test.py
```

### Tested Endpoints

1. `GET /api/health` - Health check (no auth)
2. `GET /api/shops` - List shops (requires auth)
3. `GET /api/kpi/summary?period=30d` - KPI summary (requires auth)
4. `GET /api/charts/revenue-daily?period=30d` - Revenue chart (requires auth)
5. `GET /api/extra-expenses?period=30d` - Extra expenses (requires auth)

### Authentication

In dev mode, the script uses `X-User-Id` header (default: `00000000-0000-0000-0000-000000000001`).

In production, use `SMOKE_TEST_TOKEN` environment variable with a valid JWT token.

## Health Checks

### API Health Check

- Endpoint: `GET /api/health`
- Response: `{"ok": true}`
- No authentication required

### Database Health Check

PostgreSQL health check is configured in `docker-compose.yml` using `pg_isready`.

## Automatic Migrations

The API container automatically runs Alembic migrations on startup via `entrypoint.sh`:

1. Wait for database to be ready
2. Run `alembic upgrade head`
3. Start uvicorn server

This ensures the database schema is always up-to-date when the container starts.
