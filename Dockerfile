# Use official Python image
FROM python:3.12-slim

# Install system dependencies for Rust and building Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Rust (needed for packages like tiktoken)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Set working directory
WORKDIR /app

# Copy Python dependencies first (for caching)
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire project
COPY . .

# Expose port
EXPOSE 8000

# Run Uvicorn pointing to the backend package
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
