from fastapi import APIRouter
from app.api.endpoints import repositories, search, graphs, functions, statistics

api_router = APIRouter()

api_router.include_router(repositories.router, prefix="/repositories", tags=["Repositories"])
api_router.include_router(search.router, prefix="/search", tags=["Search"])
api_router.include_router(graphs.router, prefix="/graphs", tags=["Graphs"])
api_router.include_router(functions.router, prefix="/functions", tags=["Functions"])
api_router.include_router(statistics.router, prefix="/statistics", tags=["Statistics"])
