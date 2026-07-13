from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import RepositoryStatistics
from app.schemas import RepositoryStatisticsResponse

router = APIRouter()

@router.get("/", response_model=RepositoryStatisticsResponse)
def get_repository_statistics(repository_id: str, db: Session = Depends(get_db)):
    """Fetch precomputed metrics and code characteristics for a repository."""
    stats = db.query(RepositoryStatistics).filter(RepositoryStatistics.repository_id == repository_id).first()
    if not stats:
        raise HTTPException(
            status_code=404, 
            detail="Statistics not found. Verify indexing has completed successfully."
        )
    return stats
