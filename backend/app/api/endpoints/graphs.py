from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import GraphResponse
from app.services.graph_service import GraphService

router = APIRouter()

@router.get("/dependency", response_model=GraphResponse)
def get_dependency_graph(repository_id: str, db: Session = Depends(get_db)):
    """Fetch the file-level import dependency graph for a repository."""
    try:
        return GraphService.build_dependency_graph(db, repository_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to build dependency graph: {e}")

@router.get("/call", response_model=GraphResponse)
def get_call_graph(repository_id: str, db: Session = Depends(get_db)):
    """Fetch the function-level call graph for a repository."""
    try:
        return GraphService.build_call_graph(db, repository_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to build call graph: {e}")
