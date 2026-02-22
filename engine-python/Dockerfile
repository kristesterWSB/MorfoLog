# Folder: engine-python/Dockerfile

# Use Python 3.12 (simple single-stage build to avoid path/permission issues in Cloud Run)
FROM python:3.12-slim

# Prevent Python from writing pyc files to disc (as Cloud Run file system is read-only)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    poppler-utils \
    ffmpeg libsm6 libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Start server. Use the PORT environment variable if provided by the platform (Cloud Run sets PORT).
# We use python server.py because server.py handles PORT env var and binds to 0.0.0.0
CMD ["python", "server.py"]