from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Repository
from app.schemas import RepositoryCreate, RepositoryResponse
from app.services.repo_service import RepositoryService
from celery import Celery
import os

router = APIRouter()

# Instantiate Celery client to trigger tasks
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
celery_client = Celery("code_intelligence_tasks", broker=REDIS_URL, backend=REDIS_URL)

@router.post("/", response_model=RepositoryResponse)
def import_repository(payload: RepositoryCreate, db: Session = Depends(get_db)):
    """Import a new GitHub repository and trigger parsing & indexing in the background."""
    url = payload.url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        raise HTTPException(status_code=400, detail="Invalid repository URL. Must start with http:// or https://")
    
    # Check if repository already exists in database
    existing_repo = db.query(Repository).filter(Repository.url == url).first()
    if existing_repo:
        # If it failed or completed, let's trigger a re-index instead of creating a duplicate
        if existing_repo.status in ("FAILED", "COMPLETED"):
            existing_repo.status = "PENDING"
            db.commit()
            celery_client.send_task("app.tasks.clone_and_index_repository", args=[existing_repo.id])
            return existing_repo
        return existing_repo

    # Derive temporary name from URL
    name = url.split("/")[-1].replace(".git", "")
    if not name:
        name = "Pending"
        
    repo = RepositoryService.create_repository(db, name, url)
    
    # Trigger Celery background task
    try:
        celery_client.send_task("app.tasks.clone_and_index_repository", args=[repo.id])
    except Exception as e:
        print(f"Failed to queue celery task: {e}")
        # Mark as FAILED immediately if Celery is down
        RepositoryService.update_status(db, repo.id, "FAILED", f"Celery connection failed: {e}")
        
    return repo

@router.get("/", response_model=List[RepositoryResponse])
def list_repositories(db: Session = Depends(get_db)):
    """List all imported repositories and their index status."""
    return RepositoryService.list_repositories(db)

@router.get("/{id}", response_model=RepositoryResponse)
def get_repository(id: str, db: Session = Depends(get_db)):
    """Get the indexing status and metadata of a specific repository."""
    repo = RepositoryService.get_repository(db, id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo

@router.post("/{id}/index", response_model=RepositoryResponse)
def reindex_repository(id: str, db: Session = Depends(get_db)):
    """Trigger manually re-indexing of a repository."""
    repo = RepositoryService.get_repository(db, id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    repo.status = "PENDING"
    repo.error_message = None
    db.commit()
    
    try:
        celery_client.send_task("app.tasks.clone_and_index_repository", args=[repo.id])
    except Exception as e:
        RepositoryService.update_status(db, repo.id, "FAILED", f"Celery connection failed: {e}")
        
    return repo

@router.delete("/{id}")
def delete_repository(id: str, db: Session = Depends(get_db)):
    """Delete a repository from database, full-text index, and remove cloned files from disk."""
    success = RepositoryService.delete_repository(db, id)
    if not success:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    # Try deleting OpenSearch index in background
    try:
        from opensearchpy import OpenSearch
        host = os.getenv("OPENSEARCH_HOST", "localhost")
        port = int(os.getenv("OPENSEARCH_PORT", 9200))
        user = os.getenv("OPENSEARCH_USER", "admin")
        password = os.getenv("OPENSEARCH_PASSWORD", "AdminPassword123!")
        
        client = OpenSearch(
            hosts=[{'host': host, 'port': port}],
            http_auth=(user, password),
            use_ssl=False,
            verify_certs=False,
            ssl_assert_hostname=False,
            ssl_show_warn=False,
            timeout=5
        )
        index_name = f"gcip_repository_{id}".lower()
        if client.indices.exists(index=index_name):
            client.indices.delete(index=index_name)
    except Exception as e:
        print(f"Failed to delete OpenSearch index: {e}")

    return {"detail": "Repository deleted successfully"}

@router.get("/{id}/file")
def get_repository_file(id: str, path: str, db: Session = Depends(get_db)):
    """Retrieve file content from disk safely, validating path containment."""
    repo = RepositoryService.get_repository(db, id)
    if not repo or not repo.clone_path:
        raise HTTPException(status_code=404, detail="Repository clone path not set or repository not found")
        
    # Standard security check for path traversal
    base_dir = os.path.abspath(repo.clone_path)
    target_path = os.path.abspath(os.path.join(base_dir, path))
    
    if not target_path.startswith(base_dir):
        raise HTTPException(status_code=403, detail="Path traversal forbidden")
        
    if not os.path.exists(target_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    try:
        with open(target_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file contents: {e}")
