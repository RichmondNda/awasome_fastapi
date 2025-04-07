# ─────────────────────────────
# STAGE 1: Build dependencies
# ─────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# System deps (if needed for wheels)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy only what we need for installing dependencies
COPY requirements.txt .

# Install dependencies into a clean folder
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt

# ─────────────────────────────
# STAGE 2: Final minimal image
# ─────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Copy installed dependencies from builder
COPY --from=builder /install /usr/local

# Copy app source code
COPY ./app /app

# Copy .env if needed at runtime (or use env vars in docker-compose)
# COPY .env .

EXPOSE 8000

# Start FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
