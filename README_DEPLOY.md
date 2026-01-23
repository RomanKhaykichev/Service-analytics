# Deployment Guide

Production-ready Docker deployment for Service Analytics.

## Quick Start (Local)

### Prerequisites

- Docker Desktop (Windows/Mac) or Docker + Docker Compose (Linux)
- Git

### Steps

1. **Clone the repository** (if not already done):
   ```bash
   git clone <repository-url>
   cd Service-analytics
   ```

2. **Create `.env` file**:
   ```bash
   cp .env.example .env
   ```

3. **Edit `.env`** (optional, defaults work for local development):
   ```env
   PGDATABASE=service_analytics
   PGUSER=postgres
   PGPASSWORD=your_secure_password
   BACKEND_PORT=8000
   ```

4. **Start services**:
   ```bash
   docker compose up -d --build
   ```

5. **Check status**:
   ```bash
   docker compose ps
   ```

6. **View logs**:
   ```bash
   # All services
   docker compose logs -f
   
   # Backend only
   docker compose logs -f backend
   
   # Database only
   docker compose logs -f db
   ```

7. **Verify backend is running**:
   ```bash
   curl http://localhost:8000/health
   ```
   Expected response: `{"ok":true}`

### Stop Services

```bash
docker compose down
```

To remove volumes (⚠️ deletes database data):
```bash
docker compose down -v
```

## Running Import Script

The import script `import/import_batch.py` can be run inside the backend container:

```bash
# Copy your Excel files to a directory (e.g., ./data/)
# Then run import inside the container
docker compose exec backend python /app/import/import_batch.py \
  --email your@email.com \
  --file /app/import/data/your_file.xlsx
```

Or mount a local directory with your files:

```bash
# Add to docker-compose.yml volumes for backend:
# - ./data:/app/data:ro

# Then run:
docker compose exec backend python /app/import/import_batch.py \
  --email your@email.com \
  --file /app/data/your_file.xlsx
```

## Deployment to VPS

### Prerequisites

- Ubuntu 20.04+ / Debian 11+ / CentOS 8+ (or similar Linux)
- Root or sudo access
- Domain name (optional, for reverse proxy)

### Step 1: Install Docker

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Log out and back in for group changes to take effect
```

### Step 2: Clone Repository

```bash
cd /opt  # or /home/your-user, or wherever you prefer
git clone <repository-url> service-analytics
cd service-analytics
```

### Step 3: Configure Environment

```bash
cp .env.example .env
nano .env  # or use your preferred editor
```

**Important settings for production:**

```env
# Database - use strong passwords!
PGDATABASE=service_analytics
PGUSER=postgres
PGPASSWORD=<strong_random_password>

# Backend port (or use reverse proxy)
BACKEND_PORT=8000

# Environment
APP_ENV=production
ENV=production
```

### Step 4: Start Services

```bash
docker compose up -d --build
```

### Step 5: Verify

```bash
# Check services are running
docker compose ps

# Check backend health
curl http://localhost:8000/health

# View logs
docker compose logs -f
```

### Step 6: Configure Firewall

```bash
# Ubuntu/Debian (ufw)
sudo ufw allow 8000/tcp
sudo ufw allow 22/tcp  # SSH
sudo ufw enable

# Or for specific IP only:
sudo ufw allow from <your-ip> to any port 8000
```

### Step 7: Reverse Proxy (Optional but Recommended)

Using Nginx:

```bash
sudo apt install nginx
```

Create `/etc/nginx/sites-available/service-analytics`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable and restart:

```bash
sudo ln -s /etc/nginx/sites-available/service-analytics /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

For HTTPS (Let's Encrypt):

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### Step 8: Auto-start on Boot

Docker Compose services should auto-start, but verify:

```bash
# Check if docker service is enabled
sudo systemctl status docker
sudo systemctl enable docker

# For docker-compose services, they should restart automatically
# (restart: unless-stopped in docker-compose.yml)
```

## Database Migrations

### Automatic Migrations

Migrations are **automatically applied** when the API container starts via the `entrypoint.sh` script. This ensures the database schema is always up-to-date.

**How it works:**
1. Container starts → `entrypoint.sh` runs
2. Script waits for database to be ready (with retry)
3. Runs `alembic upgrade head` to apply all pending migrations
4. Starts the API server

**Manual migration commands:**

```bash
# Check current migration version
docker compose exec api python -m alembic current

# View migration history
docker compose exec api python -m alembic history

# Apply migrations manually (if needed)
docker compose exec api python -m alembic upgrade head

# Rollback one migration (if needed)
docker compose exec api python -m alembic downgrade -1
```

### Creating New Migrations

**Important**: Always create migrations through Alembic, never modify the database schema directly.

```bash
# Create a new migration
docker compose exec api python -m alembic revision -m "description of changes"

# Auto-generate migration from model changes (if using SQLAlchemy models)
docker compose exec api python -m alembic revision --autogenerate -m "description"
```

Then edit the generated file in `apps/api/alembic/versions/` to ensure it's correct.

### Backup Before Migrations

**Always backup the database before applying migrations in production:**

```bash
# Create backup
docker compose exec db pg_dump -U postgres service_analytics > backup_before_migration_$(date +%Y%m%d_%H%M%S).sql

# Or with compression
docker compose exec db pg_dump -U postgres -Fc service_analytics > backup_$(date +%Y%m%d_%H%M%S).dump
```

### Migration Troubleshooting

1. **Migration fails on startup:**
   - Check logs: `docker compose logs api | grep -i migration`
   - Verify DATABASE_URL is correct
   - Check database connectivity: `docker compose exec api python -c "from app.db import engine; engine.connect()"`

2. **Migration already applied error:**
   - Check alembic_version table: `docker compose exec db psql -U postgres -d service_analytics -c "SELECT * FROM app.alembic_version;"`
   - If migration is listed but not applied, check for SQL errors in migration file

3. **Schema mismatch:**
   - Ensure `DB_SCHEMA` env var matches the schema used in migrations (default: `app`)
   - Check: `docker compose exec api python -c "from app.settings import get_settings; print(get_settings().DB_SCHEMA)"`

## Maintenance

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f db

# Last 100 lines
docker compose logs --tail=100 backend
```

### Restart Services

```bash
# Restart all
docker compose restart

# Restart specific service
docker compose restart backend
```

### Update Application

```bash
# Pull latest code
git pull

# Rebuild and restart
docker compose up -d --build
```

### Database Backup

**Always backup before migrations or major updates:**

```bash
# Create backup (plain SQL)
docker compose exec db pg_dump -U postgres service_analytics > backup_$(date +%Y%m%d_%H%M%S).sql

# Create backup (compressed custom format)
docker compose exec db pg_dump -U postgres -Fc service_analytics > backup_$(date +%Y%m%d_%H%M%S).dump

# Restore backup (plain SQL)
docker compose exec -T db psql -U postgres service_analytics < backup_20240101_120000.sql

# Restore backup (compressed)
docker compose exec -T db pg_restore -U postgres -d service_analytics backup_20240101_120000.dump
```

**Automated backup script (recommended for production):**

Create a cron job or systemd timer to run backups daily:

```bash
#!/bin/bash
# backup.sh
BACKUP_DIR="/backups/service-analytics"
mkdir -p "$BACKUP_DIR"
docker compose exec -T db pg_dump -U postgres -Fc service_analytics > "$BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).dump"
# Keep last 30 days
find "$BACKUP_DIR" -name "backup_*.dump" -mtime +30 -delete
```

### Database Access

```bash
# Connect to database
docker compose exec db psql -U postgres -d service_analytics

# Or from host (if port 5432 is exposed)
psql -h localhost -U postgres -d service_analytics
```

## Troubleshooting

### Backend won't start

1. Check logs: `docker compose logs backend`
2. Verify database is healthy: `docker compose ps`
3. Check environment variables: `docker compose exec backend env | grep PG`

### Database connection errors

1. Verify database is running: `docker compose ps db`
2. Check database logs: `docker compose logs db`
3. Verify credentials in `.env` match database settings
4. Ensure backend waits for database: check `depends_on` in docker-compose.yml

### Migrations not applying

**Important**: Migrations are automatically applied on container startup via `entrypoint.sh`.

1. Check migration logs: `docker compose logs api | grep -i migration`
2. Manually run migrations if needed:
   ```bash
   docker compose exec api python -m alembic upgrade head
   ```
3. Check current migration status:
   ```bash
   docker compose exec api python -m alembic current
   ```
4. View migration history:
   ```bash
   docker compose exec api python -m alembic history
   ```

### Port already in use

If port 8000 is already in use:

1. Change `BACKEND_PORT` in `.env` to another port (e.g., 8001)
2. Restart: `docker compose up -d`

### Import script not found

The import script is mounted as a volume. If it's not accessible:

1. Verify volume mount in `docker-compose.yml`
2. Check file exists: `docker compose exec backend ls -la /app/import/`

## Smoke Tests

After deployment, run smoke tests to verify endpoints:

```bash
# Run smoke tests (requires SMOKE_TEST_TOKEN if testing authenticated endpoints)
docker compose exec api python scripts/smoke.py

# Or from host (if API is accessible)
export API_BASE_URL=http://localhost:8000
export SMOKE_TEST_TOKEN=your_jwt_token_here
python apps/api/scripts/smoke.py
```

The smoke test checks:
- `/health` endpoint
- `/api/shops` (if token provided)
- `/api/kpi/summary` (if token provided)
- `/api/extra-expenses` (if token provided)

## Production Checklist

- [ ] Strong database password set in `.env`
- [ ] Firewall configured (only necessary ports open)
- [ ] Reverse proxy configured (Nginx/Caddy)
- [ ] HTTPS enabled (Let's Encrypt)
- [ ] Regular backups scheduled (before migrations!)
- [ ] Database migrations tested in staging
- [ ] Smoke tests passing after deployment
- [ ] Monitoring/logging set up (optional)
- [ ] Domain DNS configured (if using domain)
- [ ] Environment variables secured (not in git)
- [ ] `DB_SCHEMA` env var matches schema in migrations (default: `app`)

## Support

For issues or questions:
- Check logs: `docker compose logs api`
- Review migration status: `docker compose exec api python -m alembic current`
- Verify database: `docker compose exec db psql -U postgres -d service_analytics -c "\dt app.*"`
- Run smoke tests: `docker compose exec api python scripts/smoke.py`
