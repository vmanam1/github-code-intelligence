from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import api_router
from app.database import engine, Base
import os

# Create PostgreSQL/SQLite database tables on startup
try:
    print("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables initialized successfully.")
except Exception as e:
    print(f"Failed to auto-create database tables: {e}")

app = FastAPI(
    title="GitHub Code Intelligence Platform API",
    description="Local-first code analysis, syntax tree parsing, OpenSearch indexing, FAISS semantic search, and Ollama function explanation.",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json"
)

# Enable CORS for frontend client calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify front-end hosts
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Router
app.include_router(api_router, prefix="/api")

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "GitHub Code Intelligence Platform Backend API",
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
