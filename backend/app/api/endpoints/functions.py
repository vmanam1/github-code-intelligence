from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
import os
import json
import requests
import numpy as np
from app.database import get_db
from app.models import File, Function, Class
from app.schemas import FunctionResponse, AIExplanationResponse, DuplicatePairResponse
from app.config import settings

router = APIRouter()

@router.get("/{id}", response_model=FunctionResponse)
def get_function(id: str, db: Session = Depends(get_db)):
    """Retrieve details of a specific function, including its source code and path."""
    func = db.query(Function).filter(Function.id == id).first()
    if not func:
        raise HTTPException(status_code=404, detail="Function not found")
    
    # Enrich with file path
    res = FunctionResponse.from_orm(func)
    res.file_path = func.file.path
    if func.class_ctx:
        res.class_name = func.class_ctx.name
    return res

@router.post("/{id}/explain", response_model=AIExplanationResponse)
def explain_function(id: str, db: Session = Depends(get_db)):
    """
    Sends the function source code to a local Ollama model to generate an AI explanation.
    """
    func = db.query(Function).filter(Function.id == id).first()
    if not func:
        raise HTTPException(status_code=404, detail="Function not found")

    file_path = func.file.path
    class_prefix = f"class {func.class_ctx.name}:" if func.class_ctx else ""
    
    prompt = f"""You are an expert Senior Software Engineer, Architect, and Security Auditor.
Analyze the following function from file '{file_path}':

{class_prefix}
{func.body}

Provide a detailed explanation. You MUST respond ONLY in valid JSON matching this schema:
{{
  "purpose": "What is the core purpose of this function?",
  "summary": "High-level summary of what it does in 2-3 sentences.",
  "complexity": {{
    "time": "O(N) or O(1) or O(log N) - explain why",
    "space": "O(N) or O(1) - explain why"
  }},
  "improvements": ["Improvement suggestion 1", "Improvement suggestion 2"],
  "potential_bugs": ["Possible bug 1", "Possible bug 2"],
  "security_concerns": ["Security concern 1", "Security concern 2"],
  "refactoring_suggestions": ["Refactoring suggestion 1", "Refactoring suggestion 2"]
}}

Rules:
1. Return ONLY the JSON object. Do not wrap in markdown ```json blocks.
2. If list of improvements/bugs/concerns is empty, return an empty array [].
3. Ensure the JSON is well-formatted and valid.
"""

    url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/generate"
    payload = {
        "model": settings.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }

    try:
        response = requests.post(url, json=payload, timeout=60)
        if response.status_code != 200:
            raise Exception(f"Ollama server returned status code {response.status_code}")
        
        data = response.json()
        raw_text = data.get("response", "").strip()
        
        # Parse the JSON response from Ollama
        explanation = json.loads(raw_text)
        
        # Build schema compliant response
        return AIExplanationResponse(
            purpose=explanation.get("purpose", ""),
            summary=explanation.get("summary", ""),
            complexity=explanation.get("complexity", {"time": "Unknown", "space": "Unknown"}),
            improvements=explanation.get("improvements", []),
            potential_bugs=explanation.get("potential_bugs", []),
            security_concerns=explanation.get("security_concerns", []),
            refactoring_suggestions=explanation.get("refactoring_suggestions", []),
            raw_response=raw_text
        )

    except Exception as e:
        print(f"Ollama API request failed: {e}")
        # Return fallback error details
        return AIExplanationResponse(
            purpose="Failed to connect to local Ollama model.",
            summary=f"Error message: {str(e)}",
            complexity={"time": "N/A", "space": "N/A"},
            improvements=[
                "Make sure Ollama is running locally",
                f"Make sure model '{settings.OLLAMA_MODEL}' is pulled: run 'ollama pull {settings.OLLAMA_MODEL}'"
            ],
            potential_bugs=[],
            security_concerns=[],
            refactoring_suggestions=[],
            raw_response=str(e)
        )

@router.get("/duplicates/detect", response_model=List[DuplicatePairResponse])
def detect_duplicates(
    repository_id: str,
    threshold: float = Query(0.85, ge=0.5, le=1.0),
    db: Session = Depends(get_db)
):
    """
    Detect duplicate/similar functions inside the repository using FAISS vector similarities.
    Returns pairs of matching functions and their cosine similarity score.
    """
    index_path = os.path.join(settings.DATA_DIR, "indices", f"{repository_id}.index")
    meta_path = os.path.join(settings.DATA_DIR, "indices", f"{repository_id}.meta.json")

    if not os.path.exists(index_path) or not os.path.exists(meta_path):
        return []

    try:
        import faiss
    except ImportError:
        raise HTTPException(status_code=500, detail="FAISS library not installed on backend.")

    try:
        # Load index and metadata
        faiss_index = faiss.read_index(index_path)
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        vectors = meta.get("vectors", [])

        ntotal = faiss_index.ntotal
        if ntotal < 2:
            return []

        # Reconstruct all vectors from Flat index
        # We can do this by searching the entire index for every single vector in it!
        # Search the top 5 nearest neighbors for all vectors
        k_search = min(5, ntotal)
        
        # Load functions to cache them and reduce DB lookups
        db_files = db.query(File).filter(File.repository_id == repository_id).all()
        file_ids = [f.id for f in db_files]
        file_map = {f.id: f for f in db_files}
        
        db_funcs = db.query(Function).filter(Function.file_id.in_(file_ids)).all()
        func_map = {fn.id: fn for fn in db_funcs}

        # To extract vectors from index, we search the index against itself!
        # First, reconstruct the vectors to float32 matrix
        raw_vectors = np.zeros((ntotal, faiss_index.d), dtype='float32')
        for i in range(ntotal):
            raw_vectors[i] = faiss_index.reconstruct(i)

        # Search index
        D, I = faiss_index.search(raw_vectors, k_search)
        
        duplicate_pairs = []
        seen_pairs = set()

        for i in range(ntotal):
            for col in range(k_search):
                sim = D[i][col]
                j = I[i][col]
                
                # Check similarity threshold and skip self-comparison
                if j == -1 or i == j or sim < threshold:
                    continue
                
                # Sort indices to avoid counting (i, j) and (j, i) twice
                pair = (min(i, j), max(i, j))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)

                vec_a = vectors[pair[0]]
                vec_b = vectors[pair[1]]

                # Duplicate detection is only for functions
                if vec_a["type"] == "function" and vec_b["type"] == "function":
                    func_a = func_map.get(vec_a["id"])
                    func_b = func_map.get(vec_b["id"])

                    if func_a and func_b:
                        # Enrich responses
                        resp_a = FunctionResponse.from_orm(func_a)
                        resp_a.file_path = file_map[func_a.file_id].path
                        if func_a.class_ctx:
                            resp_a.class_name = func_a.class_ctx.name

                        resp_b = FunctionResponse.from_orm(func_b)
                        resp_b.file_path = file_map[func_b.file_id].path
                        if func_b.class_ctx:
                            resp_b.class_name = func_b.class_ctx.name

                        duplicate_pairs.append(DuplicatePairResponse(
                            function_a=resp_a,
                            function_b=resp_b,
                            similarity=float(sim)
                        ))

        # Sort duplicates by similarity descending
        duplicate_pairs.sort(key=lambda x: x.similarity, reverse=True)
        return duplicate_pairs

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to detect duplicates: {e}")
