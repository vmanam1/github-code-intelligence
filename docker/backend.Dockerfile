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
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Create shared data folder
RUN mkdir -p /workspace/data

# Copy code
COPY backend/app /app/app
COPY parser /app/parser

# Command to run backend
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
