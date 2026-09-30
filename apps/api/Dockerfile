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

# Windows checkouts often copy CRLF; that makes bash fail before migrations run.
RUN sed -i 's/\r$//' ./scripts/entrypoint.sh ./scripts/wait_for_db.py \
    && chmod +x ./scripts/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/bin/bash", "./scripts/entrypoint.sh"]
