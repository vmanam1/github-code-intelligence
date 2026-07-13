# REST API Reference

The **GitHub Code Intelligence Platform** backend exposes clean RESTful endpoints to query index metadata, search, build relationships, and get AI insights.

---

## Base URL
- **Local Dev Server**: `http://localhost:8000/api`
- **Interactive Swagger Docs**: `http://localhost:8000/docs`

---

## 1. Repository Endpoints

### Import Repository
Trigger asynchronous cloning and parsing of a public GitHub repository.

- **URL**: `/repositories/`
- **Method**: `POST`
- **Payload**:
  ```json
  {
    "url": "https://github.com/encode/django-rest-framework"
  }
  ```
- **Response (`200 OK`)**:
  ```json
  {
    "id": "e9c20a1f-0b42-49df-8b2b-f1deca09f140",
    "name": "django-rest-framework",
    "url": "https://github.com/encode/django-rest-framework",
    "clone_path": null,
    "status": "PENDING",
    "error_message": null,
    "created_at": "2026-07-13T09:47:00Z",
    "updated_at": "2026-07-13T09:47:00Z"
  }
  ```

### List Repositories
List all imported repository metadata.

- **URL**: `/repositories/`
- **Method**: `GET`
- **Response (`200 OK`)**:
  ```json
  [
    {
      "id": "e9c20a1f-0b42-49df-8b2b-f1deca09f140",
      "name": "django-rest-framework",
      "url": "https://github.com/encode/django-rest-framework",
      "clone_path": "/workspace/data/repos/e9c20a1f-0b42-49df-8b2b-f1deca09f140",
      "status": "COMPLETED",
      "error_message": null,
      "created_at": "2026-07-13T09:47:00Z",
      "updated_at": "2026-07-13T09:48:15Z"
    }
  ]
  ```

### Get Repository Details & Status
Poll the indexing state of a repository.

- **URL**: `/repositories/{id}`
- **Method**: `GET`
- **Response (`200 OK`)**:
  ```json
  {
    "id": "e9c20a1f-0b42-49df-8b2b-f1deca09f140",
    "name": "django-rest-framework",
    "url": "https://github.com/encode/django-rest-framework",
    "clone_path": "/workspace/data/repos/e9c20a1f-0b42-49df-8b2b-f1deca09f140",
    "status": "COMPLETED",
    "error_message": null,
    "created_at": "2026-07-13T09:47:00Z",
    "updated_at": "2026-07-13T09:48:15Z"
  }
  ```

### Retrieve File Content
Reads a file's content from a cloned workspace directory securely.

- **URL**: `/repositories/{id}/file`
- **Method**: `GET`
- **Query Parameters**:
  - `path` (string, required) - Relative file path (e.g. `rest_framework/views.py`)
- **Response (`200 OK`)**:
  ```json
  {
    "content": "import os\nfrom django.views import View\n..."
  }
  ```

---

## 2. Search Endpoints

### Keyword Search
Perform standard string or regex queries.

- **URL**: `/search/text`
- **Method**: `GET`
- **Query Parameters**:
  - `repository_id` (string, required)
  - `q` (string, required) - Keyword query
  - `type` (string, optional) - Filter by type: `file`, `class`, `function`
  - `limit` (integer, optional, default: 20)
- **Response (`200 OK`)**:
  ```json
  [
    {
      "id": "7820ab9c-092f-488f-a9cb-b203d98fbca1",
      "name": "APIView",
      "type": "class",
      "path": "rest_framework/views.py",
      "language": "python",
      "snippet": "class APIView(View):\n    # Core API controller class\n...",
      "score": 4.82
    }
  ]
  ```

### Semantic AI Search
Execute concept similarity search based on sentence-transformers embeddings.

- **URL**: `/search/semantic`
- **Method**: `GET`
- **Query Parameters**:
  - `repository_id` (string, required)
  - `q` (string, required) - Concept query (e.g., "oauth token validation")
  - `limit` (integer, optional, default: 10)
- **Response (`200 OK`)**:
  ```json
  [
    {
      "id": "fb28ca31-df82-411a-8c90-bdfcb29831cb",
      "name": "verify_token",
      "type": "function",
      "path": "rest_framework/authentication.py",
      "body": "def verify_token(self, token):\n    # JWT signature verification\n...",
      "docstring": "Validates the signature of the incoming JWT access token",
      "similarity": 0.8921
    }
  ]
  ```

---

## 3. Graph Endpoints

### Dependency Graph
Generate file import directed relationships.

- **URL**: `/graphs/dependency`
- **Method**: `GET`
- **Query Parameters**:
  - `repository_id` (string, required)
- **Response (`200 OK`)**:
  ```json
  {
    "nodes": [
      { "id": "file_1_uuid", "label": "main.py", "type": "file", "path": "main.py" },
      { "id": "file_2_uuid", "label": "utils.py", "type": "file", "path": "utils.py" }
    ],
    "edges": [
      { "id": "dep_file_1_uuid_file_2_uuid", "source": "file_1_uuid", "target": "file_2_uuid" }
    ]
  }
  ```

### Call Graph
Generate function execution calls.

- **URL**: `/graphs/call`
- **Method**: `GET`
- **Query Parameters**:
  - `repository_id` (string, required)
- **Response (`200 OK`)**:
  ```json
  {
    "nodes": [
      { "id": "fn_1_uuid", "label": "main", "type": "function", "path": "main.py" },
      { "id": "fn_2_uuid", "label": "add", "type": "function", "path": "utils.py" }
    ],
    "edges": [
      { "id": "call_fn_1_uuid_fn_2_uuid", "source": "fn_1_uuid", "target": "fn_2_uuid" }
    ]
  }
  ```

---

## 4. Function Endpoints

### Get Function Details
- **URL**: `/functions/{id}`
- **Method**: `GET`
- **Response (`200 OK`)**:
  ```json
  {
    "id": "fn_2_uuid",
    "file_id": "file_2_uuid",
    "class_id": null,
    "name": "add",
    "signature": "def add(self, a, b)",
    "start_line": 12,
    "end_line": 15,
    "body": "def add(self, a, b):\n    return a + b",
    "docstring": "Return sum of a and b",
    "file_path": "utils.py",
    "class_name": null
  }
  ```

### Local AI Explanation
Prompts local Ollama server to audit the code.

- **URL**: `/functions/{id}/explain`
- **Method**: `POST`
- **Response (`200 OK`)**:
  ```json
  {
    "purpose": "A utility method to calculate numeric additions.",
    "summary": "This method takes two input arguments and returns their sum.",
    "complexity": {
      "time": "O(1) - single instruction arithmetic operation",
      "space": "O(1) - no extra memory allocated"
    },
    "improvements": [],
    "potential_bugs": [],
    "security_concerns": [],
    "refactoring_suggestions": [],
    "raw_response": "..."
  }
  ```

### Duplicate Code Detection
Calculate duplicate pairs in the repository.

- **URL**: `/functions/duplicates/detect`
- **Method**: `GET`
- **Query Parameters**:
  - `repository_id` (string, required)
  - `threshold` (float, optional, default: 0.85)
- **Response (`200 OK`)**:
  ```json
  [
    {
      "function_a": {
        "id": "fn_1_uuid",
        "name": "helper_sum",
        "signature": "def helper_sum(a, b)",
        "start_line": 20,
        "end_line": 22,
        "body": "...",
        "file_path": "math/ops.py"
      },
      "function_b": {
        "id": "fn_2_uuid",
        "name": "add",
        "signature": "def add(a, b)",
        "start_line": 12,
        "end_line": 14,
        "body": "...",
        "file_path": "utils.py"
      },
      "similarity": 0.9981
    }
  ]
  ```
