# Folder: engine-python/Dockerfile

# Stage 1: Builder
FROM python:3.12-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.12-slim

WORKDIR /app

# Install runtime system dependencies
RUN apt-get update && apt-get install -y \
    poppler-utils \
    ffmpeg libsm6 libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed python packages from builder
COPY --from=builder /root/.local /root/.local

# Update PATH to include installed packages
ENV PATH=/root/.local/bin:$PATH

# Copy app code
COPY . .

# Start server
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]