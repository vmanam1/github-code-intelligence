import os
import re
from sqlalchemy.orm import Session
from typing import Dict, List, Any, Set
from ..models import File, Import, Function
from ..schemas import GraphNode, GraphEdge, GraphResponse
from parser.tree_sitter_parser import CodeParser

class GraphService:
    """Performs static analysis to build dependency graphs and function call graphs."""

    @staticmethod
    def build_dependency_graph(db: Session, repository_id: str) -> GraphResponse:
        """
        Builds a file-level dependency graph by resolving imports to files in the repository.
        """
        files = db.query(File).filter(File.repository_id == repository_id).all()
        file_map = {f.id: f for f in files}
        
        # Build index of paths to quickly find target files
        # Key: cleaned path (e.g., "utils/helper"), Value: File
        path_to_file = {}
        for f in files:
            clean_path = os.path.splitext(f.path)[0].replace("\\", "/")
            path_to_file[clean_path] = f
            # Also register basename just in case of relative/imprecise imports
            base_name = os.path.splitext(os.path.basename(f.path))[0]
            if base_name not in path_to_file:
                path_to_file[base_name] = f

        nodes = []
        edges = []
        edge_set = set()  # Avoid duplicates

        # Create nodes
        for f in files:
            nodes.append(GraphNode(
                id=f.id,
                label=f.path,
                type="file",
                path=f.path
            ))

            # Query imports for this file
            imports = db.query(Import).filter(Import.file_id == f.id).all()
            for imp in imports:
                target_file = None
                
                # Try absolute resolution: import app.services.repo_service
                source_clean = imp.source.replace(".", "/").strip("/")
                name_clean = imp.name.replace(".", "/").strip("/")
                
                # Check source_clean / name_clean against path_to_file
                if source_clean in path_to_file:
                    target_file = path_to_file[source_clean]
                elif f"{source_clean}/{name_clean}" in path_to_file:
                    target_file = path_to_file[f"{source_clean}/{name_clean}"]
                elif name_clean in path_to_file:
                    target_file = path_to_file[name_clean]
                
                # Try relative resolution for imports like './helper'
                if not target_file:
                    file_dir = os.path.dirname(f.path).replace("\\", "/")
                    rel_source = f"{file_dir}/{name_clean}".strip("/")
                    if rel_source in path_to_file:
                        target_file = path_to_file[rel_source]
                    elif f"{file_dir}/{source_clean}".strip("/") in path_to_file:
                        target_file = path_to_file[f"{file_dir}/{source_clean}".strip("/")]

                # Add directed edge if resolved
                if target_file and target_file.id != f.id:
                    edge_key = (f.id, target_file.id)
                    if edge_key not in edge_set:
                        edge_set.add(edge_key)
                        edges.append(GraphEdge(
                            id=f"dep_{f.id}_{target_file.id}",
                            source=f.id,
                            target=target_file.id
                        ))

        return GraphResponse(nodes=nodes, edges=edges)

    @staticmethod
    def build_call_graph(db: Session, repository_id: str) -> GraphResponse:
        """
        Builds a function-level call graph using AST parsing to detect invokes.
        """
        db_files = db.query(File).filter(File.repository_id == repository_id).all()
        file_ids = [f.id for f in db_files]
        file_map = {f.id: f for f in db_files}

        functions = db.query(Function).filter(Function.file_id.in_(file_ids)).all()
        func_map = {f.id: f for f in functions}
        
        # Index function names defined in the repo
        # Key: name, Value: List of functions (since names can be duplicated in different files/classes)
        func_by_name: Dict[str, List[Function]] = {}
        for func in functions:
            func_by_name.setdefault(func.name, []).append(func)

        nodes = []
        edges = []
        edge_set = set()

        # Create nodes
        for func in functions:
            # Format label as "class.func" or just "func"
            label = f"{func.class_ctx.name}.{func.name}" if func.class_ctx else func.name
            nodes.append(GraphNode(
                id=func.id,
                label=label,
                type="function",
                path=file_map[func.file_id].path
            ))

            # Detect function calls in the body.
            # We use a fast, robust regex matching function calls `identifier(...)`
            # and verify if the identifier matches a function defined in our repository.
            called_names = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', func.body)
            
            for name in called_names:
                # Skip common language builtins
                if name in ("print", "len", "range", "str", "int", "list", "dict", "set", "super", "self", "defn", "func", "if", "for", "while", "return"):
                    continue
                
                if name in func_by_name:
                    # Potential call matches
                    for target_func in func_by_name[name]:
                        # Skip self-recursion calls to avoid messy loops
                        if target_func.id == func.id:
                            continue
                            
                        # If class methods, check if they are in the same file to narrow down false positives
                        if target_func.file_id == func.file_id:
                            edge_key = (func.id, target_func.id)
                            if edge_key not in edge_set:
                                edge_set.add(edge_key)
                                edges.append(GraphEdge(
                                    id=f"call_{func.id}_{target_func.id}",
                                    source=func.id,
                                    target=target_func.id
                                ))
                        elif not func.class_id and not target_func.class_id:
                            # Global function calls across files
                            edge_key = (func.id, target_func.id)
                            if edge_key not in edge_set:
                                edge_set.add(edge_key)
                                edges.append(GraphEdge(
                                    id=f"call_{func.id}_{target_func.id}",
                                    source=func.id,
                                    target=target_func.id
                                ))

        return GraphResponse(nodes=nodes, edges=edges)
