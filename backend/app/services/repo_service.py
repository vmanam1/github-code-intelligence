import os
import shutil
from sqlalchemy.orm import Session
from typing import List, Optional
from ..models import Repository, File, Class, Function, Import, RepositoryStatistics
from ..config import settings

class RepositoryService:
    """Manages repository records, file data, and cleanup operations."""

    @staticmethod
    def create_repository(db: Session, name: str, url: str) -> Repository:
        """Create a new pending repository record."""
        repo = Repository(
            name=name,
            url=url,
            status="PENDING"
        )
        db.add(repo)
        db.commit()
        db.refresh(repo)
        return repo

    @staticmethod
    def get_repository(db: Session, repo_id: str) -> Optional[Repository]:
        """Fetch a repository by ID."""
        return db.query(Repository).filter(Repository.id == repo_id).first()

    @staticmethod
    def list_repositories(db: Session) -> List[Repository]:
        """List all imported repositories."""
        return db.query(Repository).order_by(Repository.created_at.desc()).all()

    @staticmethod
    def update_status(db: Session, repo_id: str, status: str, error_message: Optional[str] = None) -> Optional[Repository]:
        """Update repository indexing status."""
        repo = db.query(Repository).filter(Repository.id == repo_id).first()
        if repo:
            repo.status = status
            if error_message:
                repo.error_message = error_message
            db.commit()
            db.refresh(repo)
        return repo

    @staticmethod
    def delete_repository(db: Session, repo_id: str) -> bool:
        """Delete repository metadata, records, and cloned files from disk."""
        repo = db.query(Repository).filter(Repository.id == repo_id).first()
        if not repo:
            return False

        # 1. Remove cloned repository files on disk
        if repo.clone_path and os.path.exists(repo.clone_path):
            try:
                shutil.rmtree(repo.clone_path)
            except Exception as e:
                print(f"Failed to delete repository directory {repo.clone_path}: {e}")

        # 2. Remove serialized FAISS index
        faiss_index_path = os.path.join(settings.DATA_DIR, "indices", f"{repo_id}.index")
        if os.path.exists(faiss_index_path):
            try:
                os.remove(faiss_index_path)
            except Exception as e:
                print(f"Failed to delete FAISS index {faiss_index_path}: {e}")

        # 3. Delete from DB (cascades will clean up files, classes, functions, imports, stats)
        db.delete(repo)
        db.commit()
        return True
