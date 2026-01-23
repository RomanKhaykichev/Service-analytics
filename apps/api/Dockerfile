FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency file
COPY apps/api/requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY apps/api/app/ ./app/
COPY apps/api/alembic/ ./alembic/
COPY apps/api/alembic.ini ./
COPY apps/api/scripts/ ./scripts/

# Make entrypoint executable
RUN chmod +x ./scripts/entrypoint.sh

# Expose port
EXPOSE 8000

# Use entrypoint script (runs migrations before starting API)
ENTRYPOINT ["./scripts/entrypoint.sh"]
