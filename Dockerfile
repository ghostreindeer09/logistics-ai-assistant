# ── Logistics AI Backend — Docker Image ──────────────────────────
FROM python:3.11-slim-bullseye

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System dependencies (build-essential for C extensions, libsqlite3 for Chroma)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    libgl1-mesa-glx \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (Docker layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip --root-user-action=ignore \
    && pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY backend/ ./backend/

# Copy .env.example as fallback defaults
COPY .env.example .env.example

# Create uploads directory
RUN mkdir -p /app/backend/uploads

# Expose port
EXPOSE 8000

# Run the FastAPI server from the backend directory
# Using 'cd backend &&' so that relative imports in main.py resolve correctly
CMD ["sh", "-c", "cd /app/backend && python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
