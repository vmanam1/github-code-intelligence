FROM python:3.12-slim

# Install system dependencies (Git, build tools, libgomp for FAISS)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install python packages
COPY worker/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Create shared data folder
RUN mkdir -p /workspace/data

# Copy code
COPY worker/app /app/worker_app
COPY parser /app/parser
COPY backend/app /app/app

# Set PYTHONPATH to search inside workspace
ENV PYTHONPATH="/app:${PYTHONPATH}"

# Command to run worker
CMD ["celery", "-A", "worker_app.celery_app", "worker", "--loglevel=info", "-P", "solo"]
