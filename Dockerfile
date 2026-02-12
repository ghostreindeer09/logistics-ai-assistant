# ── Logistics AI Backend — Docker Image ──────────────────────────
FROM python:3.11-slim-bookworm

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TOKENIZERS_PARALLELISM=false

# System dependencies (build-essential for C extensions, libsqlite3-dev)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install CPU-only PyTorch first (reduces image size & memory usage significantly)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Copy requirements
COPY requirements.txt .

# Install other Python dependencies
RUN pip install --upgrade pip --root-user-action=ignore \
    && pip install --no-cache-dir -r requirements.txt

# Pre-download the embedding model during build (avoids download at runtime)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy backend source code
COPY backend/ ./backend/

# Copy frontend static files (served by FastAPI at /ui)
COPY frontend/ ./frontend/

# Copy .env.example as fallback defaults
COPY .env.example .env.example

# Create uploads directory
RUN mkdir -p /app/backend/uploads

# Expose port
EXPOSE 8000

# Run the FastAPI server from the backend directory
CMD ["sh", "-c", "cd /app/backend && python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
