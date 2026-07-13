from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import json
import numpy as np
from app.database import get_db
from app.models import File, Class, Function
from app.schemas import SearchResult, SemanticSearchResult
from app.config import settings

router = APIRouter()

# Global cache for the embedding model in the backend process
_embed_model = None

def get_backend_embedding_model():
    global _embed_model
    if _embed_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _embed_model = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception as e:
            print(f"Backend failed to load embedding model: {e}")
    return _embed_model

@router.get("/text", response_model=List[SearchResult])
def text_search(
    repository_id: str,
    q: str,
    type: Optional[str] = Query(None, description="Filter by type: file, class, function"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Perform a keyword search inside code structures.
    Uses OpenSearch if available, otherwise falls back to a PostgreSQL LIKE query.
    """
    if not q.strip():
        return []

    # 1. Try OpenSearch
    opensearch_client = None
    try:
        from opensearchpy import OpenSearch
        opensearch_client = OpenSearch(
            hosts=[{'host': settings.OPENSEARCH_HOST, 'port': settings.OPENSEARCH_PORT}],
            http_auth=(settings.OPENSEARCH_USER, settings.OPENSEARCH_PASSWORD),
            use_ssl=False,
            verify_certs=False,
            ssl_assert_hostname=False,
            ssl_show_warn=False,
            timeout=3
        )
    except Exception:
        pass

    results = []

    if opensearch_client and opensearch_client.ping():
        index_name = f"gcip_repository_{repository_id}".lower()
        try:
            query_body = {
                "size": limit,
                "query": {
                    "bool": {
                        "must": [
                            {
                                "multi_match": {
                                    "query": q,
                                    "fields": ["name^3", "body", "docstring^2", "path"]
                                }
                            },
                            {"term": {"repository_id": repository_id}}
                        ]
                    }
                }
            }
            if type:
                query_body["query"]["bool"]["must"].append({"term": {"type": type}})

            search_res = opensearch_client.search(index=index_name, body=query_body)
            hits = search_res.get("hits", {}).get("hits", [])
            
            for hit in hits:
                source = hit["_source"]
                # Generate a short snippet
                body = source.get("body", "")
                snippet_lines = body.splitlines()[:5]
                snippet = "\n".join(snippet_lines)
                
                results.append(SearchResult(
                    id=hit["_id"].split("_")[-1],
                    name=source.get("name", ""),
                    type=source.get("type", "file"),
                    path=source.get("path", ""),
                    language=os.path.splitext(source.get("path", ""))[1].replace(".", ""),
                    snippet=snippet,
                    score=hit["_score"]
                ))
            return results
        except Exception as e:
            print(f"OpenSearch query failed: {e}. Falling back to PostgreSQL.")

    # 2. Fallback to PostgreSQL (LIKE search)
    print("Running database keyword search fallback.")
    db_files = db.query(File).filter(File.repository_id == repository_id).all()
    file_ids = [f.id for f in db_files]
    file_map = {f.id: f for f in db_files}

    # If filtering by files specifically
    if type == "file" or not type:
        matches = db.query(File).filter(
            File.repository_id == repository_id,
            File.path.ilike(f"%{q}%")
        ).limit(limit).all()
        for f in matches:
            results.append(SearchResult(
                id=f.id,
                name=os.path.basename(f.path),
                type="file",
                path=f.path,
                language=f.language,
                snippet=f.path,
                score=1.0
            ))

    # Classes search
    if (type == "class" or not type) and len(results) < limit:
        matches = db.query(Class).filter(
            Class.file_id.in_(file_ids),
            (Class.name.ilike(f"%{q}%") | Class.body.ilike(f"%{q}%") | Class.docstring.ilike(f"%{q}%"))
        ).limit(limit - len(results)).all()
        for c in matches:
            snippet = "\n".join(c.body.splitlines()[:5])
            results.append(SearchResult(
                id=c.id,
                name=c.name,
                type="class",
                path=file_map[c.file_id].path,
                language=file_map[c.file_id].language,
                snippet=snippet,
                score=0.9
            ))

    # Functions search
    if (type == "function" or not type) and len(results) < limit:
        matches = db.query(Function).filter(
            Function.file_id.in_(file_ids),
            (Function.name.ilike(f"%{q}%") | Function.body.ilike(f"%{q}%") | Function.docstring.ilike(f"%{q}%"))
        ).limit(limit - len(results)).all()
        for fn in matches:
            snippet = "\n".join(fn.body.splitlines()[:5])
            results.append(SearchResult(
                id=fn.id,
                name=fn.name,
                type="function",
                path=file_map[fn.file_id].path,
                language=file_map[fn.file_id].language,
                snippet=snippet,
                score=0.8
            ))

    return results[:limit]


@router.get("/semantic", response_model=List[SemanticSearchResult])
def semantic_search(
    repository_id: str,
    q: str,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Perform a vector similarity search using sentence-transformers and FAISS.
    """
    if not q.strip():
        return []

    index_path = os.path.join(settings.DATA_DIR, "indices", f"{repository_id}.index")
    meta_path = os.path.join(settings.DATA_DIR, "indices", f"{repository_id}.meta.json")

    if not os.path.exists(index_path) or not os.path.exists(meta_path):
        raise HTTPException(status_code=404, detail="Semantic index not found for this repository. Prepare index first.")

    # Load model and FAISS libraries
    embed_model = get_backend_embedding_model()
    try:
        import faiss
    except ImportError:
        raise HTTPException(status_code=500, detail="FAISS library is not installed on server.")

    if not embed_model:
        raise HTTPException(status_code=500, detail="Embedding model not loaded on server.")

    try:
        # Load index and metadata
        faiss_index = faiss.read_index(index_path)
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        vectors = meta.get("vectors", [])

        # Generate query vector
        query_vector = embed_model.encode([q])
        # Normalize vector for cosine similarity
        query_vector = query_vector / np.linalg.norm(query_vector, axis=1, keepdims=True)

        # Query FAISS
        # D: Distances (Inner Product is Cosine Similarity on normalized vectors)
        # I: Offsets (Index inside FAISS)
        k = min(limit, faiss_index.ntotal)
        if k == 0:
            return []
            
        D, I = faiss_index.search(query_vector, k)
        
        results = []
        distances = D[0]
        indices = I[0]

        for sim, offset in zip(distances, indices):
            if offset == -1 or offset >= len(vectors):
                continue
            
            vec_info = vectors[offset]
            entity_id = vec_info["id"]
            entity_type = vec_info["type"]

            # Load details from PostgreSQL
            if entity_type == "class":
                cls = db.query(Class).filter(Class.id == entity_id).first()
                if cls:
                    results.append(SemanticSearchResult(
                        id=cls.id,
                        name=cls.name,
                        type="class",
                        path=cls.file.path,
                        body=cls.body,
                        docstring=cls.docstring,
                        similarity=float(sim)
                    ))
            elif entity_type == "function":
                func = db.query(Function).filter(Function.id == entity_id).first()
                if func:
                    results.append(SemanticSearchResult(
                        id=func.id,
                        name=func.name,
                        type="function",
                        path=func.file.path,
                        body=func.body,
                        docstring=func.docstring,
                        similarity=float(sim)
                    ))

        return results
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Semantic search query execution failed: {e}")
