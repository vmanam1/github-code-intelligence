# Developer Setup & Troubleshooting Guide

Follow this guide to run the **GitHub Code Intelligence Platform** for local development or within Docker.

---

## 1. Quick Start: Docker Compose (Recommended)

Docker Compose starts all core components (PostgreSQL, Redis, OpenSearch, Ollama, Celery, FastAPI, React) with zero local configuration.

```bash
# 1. Clone the project
git clone https://github.com/vmanam1/github-code-intelligence.git
cd github-code-intelligence

# 2. Copy environment template
cp .env.example .env

# 3. Start the cluster
docker-compose up --build
```

---

## 2. Local Host Setup (Bare Metal Dev)

If you wish to run the backend and frontend directly on your local system:

### A. Prerequisites
- **Python**: version 3.10 to 3.12
- **Node.js**: version 18 or 20
- **Docker**: to run backing databases (Postgres, Redis, OpenSearch)

### B. Launch Backing Services
You can run only the backing services using Docker Compose:
```bash
docker-compose up -d db redis opensearch
```

### C. Backend Setup
1. Create a Python virtual environment:
   ```bash
   cd backend
   python -m venv venv
   source venv/Scripts/activate  # On Windows: venv\Scripts\activate
   ```
2. Install Python packages:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy environment configuration and configure settings:
   Set `POSTGRES_HOST=localhost`, `REDIS_URL=redis://localhost:6379/0`, `OPENSEARCH_HOST=localhost`, and `OLLAMA_BASE_URL=http://localhost:11434` inside your `.env` file at the project root.
4. Run database migrations:
   ```bash
   alembic upgrade head
   ```
5. Start the FastAPI development server:
   ```bash
   python app/main.py
   ```

### D. Celery Worker Setup
1. Open a new terminal tab and activate virtual environment inside the `worker` directory:
   ```bash
   cd worker
   source venv/Scripts/activate
   pip install -r requirements.txt
   ```
2. Set PYTHONPATH to include backend app directory:
   ```bash
   # On Windows (PowerShell):
   $env:PYTHONPATH="V:\github-code-intelligence\backend"
   # On Linux/macOS:
   export PYTHONPATH="/path/to/github-code-intelligence/backend"
   ```
3. Run the Celery worker process:
   ```bash
   # On Windows (force solo execution pool):
   celery -A app.celery_app worker --loglevel=info -P solo
   # On Linux/macOS:
   celery -A app.celery_app worker --loglevel=info
   ```

### E. Frontend Setup
1. Navigate to the frontend folder:
   ```bash
   cd frontend
   npm install
   ```
2. Start the Vite development server:
   ```bash
   npm run dev
   ```
3. Open browser: `http://localhost:5173`

---

## 3. Configuring Ollama Local AI

The platform uses Ollama to run LLMs completely locally.

1. **Install Ollama**: Download and install from [ollama.com](https://ollama.com).
2. **Pull the Default Model**:
   By default, the platform is configured to use `qwen2.5-coder:1.5b`. Pull it in your host command prompt:
   ```bash
   ollama pull qwen2.5-coder:1.5b
   ```
3. **Using Alternative Models**:
   If you have a powerful GPU and wish to use larger models like `deepseek-coder:6.7b` or `qwen2.5-coder:7b`:
   - Pull the model: `ollama pull deepseek-coder:6.7b`
   - Update `OLLAMA_MODEL` in your `.env` file:
     ```env
     OLLAMA_MODEL=deepseek-coder:6.7b
     ```
   - Restart the backend/worker services.

---

## 4. Troubleshooting Common Issues

### A. OpenSearch Container Fails: "max virtual memory areas vm.max_map_count is too low"
By default, OpenSearch requires the host's virtual memory limits to be configured.
- **Linux**: Set limit temporarily:
  ```bash
  sudo sysctl -w vm.max_map_count=262144
  ```
  To make it permanent, add `vm.max_map_count=262144` to `/etc/sysctl.conf`.
- **Windows (WSL2)**: Open PowerShell and run:
  ```powershell
  wsl -d docker-desktop
  sysctl -w vm.max_map_count=262144
  ```

### B. Celery Tasks Stalled: "Celery connection refused"
If Celery cannot connect to Redis, make sure the Redis service container is running and healthy:
- Check container status: `docker ps`
- Ping redis: `redis-cli ping` (should output `PONG`)

### C. Tree-Sitter Fails to Import: "ValueError: Parsing failed"
If Tree-sitter fails to parse, make sure you have the exact compatible versions of `tree-sitter` and `tree-sitter-languages` installed:
- Compatible Host Configuration: `tree-sitter==0.21.3` and `tree-sitter-languages==1.10.2`.
