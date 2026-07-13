import os
import sys
import shutil
import json
import traceback
import numpy as np
from typing import Dict, Any, List
import git
from celery import shared_task

# Import database models and settings from the shared backend module
from app.database import SessionLocal
from app.models import Repository, File, Class, Function, Import, RepositoryStatistics
from app.config import settings
from parser import CodeParser

# Conditional imports for search and embedding libraries to handle startup gracefully
try:
    from opensearchpy import OpenSearch
except ImportError:
    OpenSearch = None

try:
    from sentence_transformers import SentenceTransformer
    import faiss
except ImportError:
    SentenceTransformer = None
    faiss = None

# Initialize parser
parser = CodeParser()

def get_opensearch_client():
    if not OpenSearch:
        return None
    try:
        client = OpenSearch(
            hosts=[{'host': settings.OPENSEARCH_HOST, 'port': settings.OPENSEARCH_PORT}],
            http_compress=True,
            http_auth=(settings.OPENSEARCH_USER, settings.OPENSEARCH_PASSWORD),
            use_ssl=False,
            verify_certs=False,
            ssl_assert_hostname=False,
            ssl_show_warn=False,
            timeout=10
        )
        return client
    except Exception as e:
        print(f"Failed to connect to OpenSearch: {e}")
        return None

def get_embedding_model():
    if not SentenceTransformer:
        return None
    try:
        # Downloads model from Hugging Face on first run, then uses local cache
        model = SentenceTransformer("all-MiniLM-L6-v2")
        return model
    except Exception as e:
        print(f"Failed to load sentence-transformer model: {e}")
        return None

@shared_task(bind=True, name="worker_app.tasks.clone_and_index_repository")
def clone_and_index_repository(self, repo_id: str):
    """
    Main background processing pipeline:
    1. Clone repository
    2. Traverse files & Parse AST using Tree-sitter
    3. Index code text in OpenSearch
    4. Generate semantic embeddings & index in FAISS
    5. Precompute Repository Statistics
    """
    db = SessionLocal()
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        db.close()
        return f"Repository {repo_id} not found."

    try:
        # Step 1: Clone Repository
        repo.status = "CLONING"
        db.commit()
        
        clone_dir = os.path.join(settings.DATA_DIR, "repos", repo_id)
        if os.path.exists(clone_dir):
            shutil.rmtree(clone_dir)
            
        print(f"Cloning repository {repo.url} into {clone_dir}")
        git.Repo.clone_from(repo.url, clone_dir, depth=1)
        
        repo.clone_path = clone_dir
        # Extract repo name from URL if missing
        if not repo.name or repo.name == "Pending":
            repo.name = repo.url.split("/")[-1].replace(".git", "")
        db.commit()

        # Step 2: Parse AST & Populate DB
        repo.status = "PARSING"
        db.commit()
        
        supported_files = []
        # Exclude directories
        exclude_dirs = {".git", "node_modules", "venv", ".venv", "env", "__pycache__", "dist", "build"}
        
        for root, dirs, files in os.walk(clone_dir):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, clone_dir)
                _, ext = os.path.splitext(file)
                if parser.get_language_from_ext(ext):
                    supported_files.append((file_path, rel_path))

        print(f"Found {len(supported_files)} code files to parse.")
        
        # Track statistics counts
        total_loc = 0
        total_functions = 0
        total_classes = 0
        lang_distribution = {}
        largest_files_candidates = []

        for file_path, rel_path in supported_files:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                
                parsed_data = parser.parse_file(rel_path, content)
                file_size = os.path.getsize(file_path)
                lines_count = parsed_data["lines_count"]
                lang = parsed_data["language"]
                
                # Update statistics aggregates
                total_loc += lines_count
                lang_distribution[lang] = lang_distribution.get(lang, 0) + 1
                largest_files_candidates.append({
                    "path": rel_path,
                    "size": file_size,
                    "lines": lines_count
                })

                # Create File record
                db_file = File(
                    repository_id=repo_id,
                    path=rel_path,
                    language=lang,
                    size=file_size,
                    lines_count=lines_count
                )
                db.add(db_file)
                db.flush()  # Populates db_file.id

                # Save Classes
                class_map = {}  # Map name -> db Class instance
                for cls_info in parsed_data["classes"]:
                    db_class = Class(
                        file_id=db_file.id,
                        name=cls_info["name"],
                        start_line=cls_info["start_line"],
                        end_line=cls_info["end_line"],
                        body=cls_info["body"],
                        docstring=cls_info["docstring"]
                    )
                    db.add(db_class)
                    db.flush()
                    class_map[cls_info["name"]] = db_class
                    total_classes += 1

                # Save Functions
                for func_info in parsed_data["functions"]:
                    class_id = None
                    if func_info["class_name"] and func_info["class_name"] in class_map:
                        class_id = class_map[func_info["class_name"]].id
                        
                    db_func = Function(
                        file_id=db_file.id,
                        class_id=class_id,
                        name=func_info["name"],
                        signature=func_info["signature"],
                        start_line=func_info["start_line"],
                        end_line=func_info["end_line"],
                        body=func_info["body"],
                        docstring=func_info["docstring"]
                    )
                    db.add(db_func)
                    total_functions += 1

                # Save Imports
                for imp_info in parsed_data["imports"]:
                    db_import = Import(
                        file_id=db_file.id,
                        source=imp_info["source"],
                        name=imp_info["name"],
                        alias=imp_info["alias"],
                        line_number=imp_info["line_number"]
                    )
                    db.add(db_import)

            except Exception as e:
                print(f"Failed to parse and save file {rel_path}: {e}")
                
        db.commit()

        # Step 3: Indexing in OpenSearch & FAISS
        repo.status = "INDEXING"
        db.commit()

        # 3.1: OpenSearch text indexing
        opensearch_client = get_opensearch_client()
        if opensearch_client:
            index_name = f"gcip_repository_{repo_id}".lower()
            try:
                # Create index with mappings
                if not opensearch_client.indices.exists(index=index_name):
                    opensearch_client.indices.create(
                        index=index_name,
                        body={
                            "mappings": {
                                "properties": {
                                    "name": {"type": "text", "analyzer": "standard"},
                                    "type": {"type": "keyword"},
                                    "path": {"type": "keyword"},
                                    "body": {"type": "text"},
                                    "docstring": {"type": "text"},
                                    "repository_id": {"type": "keyword"}
                                }
                            }
                        }
                    )
                
                # Fetch functions and classes to index
                db_files = db.query(File).filter(File.repository_id == repo_id).all()
                file_ids = [f.id for f in db_files]
                
                classes = db.query(Class).filter(Class.file_id.in_(file_ids)).all()
                functions = db.query(Function).filter(Function.file_id.in_(file_ids)).all()
                
                # Index classes
                for cls in classes:
                    doc = {
                        "name": cls.name,
                        "type": "class",
                        "path": cls.file.path,
                        "body": cls.body,
                        "docstring": cls.docstring or "",
                        "repository_id": repo_id
                    }
                    opensearch_client.index(index=index_name, id=f"class_{cls.id}", body=doc)

                # Index functions
                for func in functions:
                    doc = {
                        "name": func.name,
                        "type": "function",
                        "path": func.file.path,
                        "body": func.body,
                        "docstring": func.docstring or "",
                        "repository_id": repo_id
                    }
                    opensearch_client.index(index=index_name, id=f"function_{func.id}", body=doc)
                
                # Index files
                for f in db_files:
                    doc = {
                        "name": os.path.basename(f.path),
                        "type": "file",
                        "path": f.path,
                        "body": f.path,  # For search matching file paths
                        "docstring": "",
                        "repository_id": repo_id
                    }
                    opensearch_client.index(index=index_name, id=f"file_{f.id}", body=doc)
                
                print("OpenSearch full-text indexing completed.")
            except Exception as e:
                print(f"Failed to index documents in OpenSearch: {e}")
        else:
            print("OpenSearch client unavailable, skipping text search indexing.")

        # 3.2: FAISS Semantic vector indexing
        embed_model = get_embedding_model()
        if embed_model and faiss:
            try:
                # Fetch all functions and classes for embedding
                db_files = db.query(File).filter(File.repository_id == repo_id).all()
                file_ids = [f.id for f in db_files]
                
                classes = db.query(Class).filter(Class.file_id.in_(file_ids)).all()
                functions = db.query(Function).filter(Function.file_id.in_(file_ids)).all()
                
                items = []  # List of dict: {"id": PK, "type": "function"/"class", "text": text_to_embed}
                for cls in classes:
                    # Construct semantic context
                    text = f"class {cls.name}\nDocstring: {cls.docstring or 'None'}\nBody:\n{cls.body}"
                    items.append({"id": cls.id, "type": "class", "text": text})
                for func in functions:
                    text = f"function {func.signature}\nDocstring: {func.docstring or 'None'}\nBody:\n{func.body}"
                    items.append({"id": func.id, "type": "function", "text": text})
                
                if items:
                    texts = [item["text"] for item in items]
                    print(f"Generating embeddings for {len(texts)} code structures...")
                    embeddings = embed_model.encode(texts, show_progress_bar=False)
                    
                    # Normalize embeddings for cosine similarity
                    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
                    # Handle division by zero
                    norms[norms == 0] = 1.0
                    embeddings = embeddings / norms
                    
                    dimension = embeddings.shape[1]
                    faiss_index = faiss.IndexFlatIP(dimension)  # Inner Product Flat Index
                    faiss_index.add(embeddings)
                    
                    # Save FAISS index file
                    index_path = os.path.join(settings.DATA_DIR, "indices", f"{repo_id}.index")
                    faiss.write_index(faiss_index, index_path)
                    
                    # Save mapping file to link FAISS offsets to DB IDs
                    meta_path = os.path.join(settings.DATA_DIR, "indices", f"{repo_id}.meta.json")
                    meta_data = {
                        "vectors": [
                            {"offset": idx, "id": item["id"], "type": item["type"]}
                            for idx, item in enumerate(items)
                        ]
                    }
                    with open(meta_path, "w", encoding="utf-8") as meta_f:
                        json.dump(meta_data, meta_f)
                    
                    print("FAISS semantic indexing completed.")
                else:
                    print("No code structures to embed.")
            except Exception as e:
                print(f"Failed to generate FAISS semantic index: {e}")
                traceback.print_exc()
        else:
            print("FAISS or SentenceTransformers unavailable, skipping semantic indexing.")

        # Step 4: Repository Statistics Calculation
        largest_files = sorted(largest_files_candidates, key=lambda x: x["size"], reverse=True)[:10]
        
        # Calculate average function size (lines)
        db_files = db.query(File).filter(File.repository_id == repo_id).all()
        file_ids = [f.id for f in db_files]
        functions = db.query(Function).filter(Function.file_id.in_(file_ids)).all()
        
        avg_func_size = 0.0
        if functions:
            total_func_lines = sum((f.end_line - f.start_line + 1) for f in functions)
            avg_func_size = float(total_func_lines) / len(functions)

        # Delete existing statistics if re-indexing
        existing_stats = db.query(RepositoryStatistics).filter(RepositoryStatistics.repository_id == repo_id).first()
        if existing_stats:
            db.delete(existing_stats)

        stats = RepositoryStatistics(
            repository_id=repo_id,
            total_files=len(supported_files),
            total_lines_of_code=total_loc,
            total_functions=total_functions,
            total_classes=total_classes,
            language_distribution=lang_distribution,
            avg_function_size=avg_func_size,
            largest_files=largest_files
        )
        db.add(stats)
        
        # Step 5: Wrap up as completed
        repo.status = "COMPLETED"
        repo.error_message = None
        db.commit()
        print(f"Repository {repo.name} indexing completed successfully.")

    except Exception as e:
        print(f"Error indexing repository {repo_id}: {e}")
        traceback.print_exc()
        repo.status = "FAILED"
        repo.error_message = f"{str(e)}\n{traceback.format_exc()}"
        db.commit()

    finally:
        db.close()
