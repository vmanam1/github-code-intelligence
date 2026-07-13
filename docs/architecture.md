# System Architecture & Design Choices

The **GitHub Code Intelligence Platform** is structured as a decoupled, multi-tier, local-first application designed for scalability, low latency, and ease of deployment.

---

## 1. Modular Subsystems

### AST Parser Layer
- **Technology**: Tree-sitter & `tree-sitter-languages`
- **Design Decision**: Rather than building manual regex expressions or using language-specific tools (which require compiling complex dependencies), we utilize the unified precompiled AST parser bindings. It parses code files into an Abstract Syntax Tree (AST) within microseconds.
- **Languages Mapped**: Python, JavaScript, TypeScript, Go, C++, and Java.

### Relational Database
- **Technology**: PostgreSQL (with SQLite support for local integration testing)
- **Database Schema**: Fully normalized tables containing `Repository`, `File`, `Class`, `Function`, and `Import` records. Cascades are set up so deleting a repository automatically wipes all nested child records.

### Text Indexing & Keyword Search
- **Technology**: OpenSearch
- **Design Decision**: OpenSearch handles full-text lookup with fuzzy matches, highlights, and analyzer tokens. To guarantee usability even if OpenSearch is offline or initializing, the query service implements a strict database fallback matching paths/bodies via `ILIKE` operators.

### Vector Embeddings & Semantic Search
- **Technology**: sentence-transformers (`all-MiniLM-L6-v2`) and FAISS
- **Design Decision**: We generate 384-dimensional cosine embeddings using Hugging Face's lightweight `all-MiniLM-L6-v2` model. FAISS Flat Inner Product index (`faiss.IndexFlatIP`) is used to store normalized vectors in memory, delivering similarity search results in sub-millisecond times. Index files and mappings are persisted directly to a shared directory.

### Asynchronous Processing
- **Technology**: Celery & Redis
- **Design Decision**: Cloning and indexing repositories can take seconds to minutes. Running these on the request thread would cause HTTP timeouts. Celery delegates these workloads to background worker processes, communicating via a Redis broker.

### Local AI Agent
- **Technology**: Ollama API
- **Design Decision**: In order to run completely locally without paid tokens or internet dependencies, the application makes REST calls to Ollama. JSON schema enforcement (`"format": "json"`) is enabled during generation to guarantee responses match our API interfaces.

---

## 2. Shared Data Directory Layout

Backend and worker containers share access to `./data` via Docker volumes:
- `/workspace/data/repos/{repo_id}/`: The directory containing cloned git repositories.
- `/workspace/data/indices/{repo_id}.index`: Serialized FAISS index.
- `/workspace/data/indices/{repo_id}.meta.json`: JSON metadata mapping FAISS offsets to PostgreSQL primary keys.

---

## 3. Core Security Considerations

- **Path Traversal Prevention**: The `GET /repositories/{id}/file` endpoint resolves paths inside `repo.clone_path` safely:
  ```python
  base_dir = os.path.abspath(repo.clone_path)
  target_path = os.path.abspath(os.path.join(base_dir, path))
  if not target_path.startswith(base_dir):
      raise HTTPException(status_code=403, detail="Forbidden")
  ```
- **Local Isolation**: All model execution (Ollama, Sentence-Transformers) and indexing run on the local machine without reporting code signatures or files to external APIs.
