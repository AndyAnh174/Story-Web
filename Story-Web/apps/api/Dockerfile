FROM python:3.13-slim

WORKDIR /app

# System deps for psycopg2 và cryptography
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Cài Python packages
COPY requirements-docker.txt .
RUN pip install --no-cache-dir -r requirements-docker.txt

# Copy source code
COPY . .

EXPOSE 8000

# Script khởi động: chạy migration trước, rồi start server
CMD alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
