from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

# Repository Schemas
class RepositoryCreate(BaseModel):
    url: str

class RepositoryResponse(BaseModel):
    id: str
    name: str
    url: str
    clone_path: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# File, Class, Function, Import Schemas
class FileResponse(BaseModel):
    id: str
    path: str
    language: str
    size: int
    lines_count: int

    class Config:
        from_attributes = True

class ClassResponse(BaseModel):
    id: str
    name: str
    start_line: int
    end_line: int
    body: str
    docstring: Optional[str] = None

    class Config:
        from_attributes = True

class FunctionResponse(BaseModel):
    id: str
    file_id: str
    class_id: Optional[str] = None
    name: str
    signature: str
    start_line: int
    end_line: int
    body: str
    docstring: Optional[str] = None
    file_path: Optional[str] = None  # Helper for display
    class_name: Optional[str] = None

    class Config:
        from_attributes = True

class ImportResponse(BaseModel):
    id: str
    source: str
    name: str
    alias: Optional[str] = None
    line_number: int

    class Config:
        from_attributes = True

# Statistics Schemas
class RepositoryStatisticsResponse(BaseModel):
    repository_id: str
    total_files: int
    total_lines_of_code: int
    total_functions: int
    total_classes: int
    language_distribution: Dict[str, int]
    avg_function_size: float
    largest_files: List[Dict[str, Any]]
    updated_at: datetime

    class Config:
        from_attributes = True

# Search & Graph Schemas
class SearchResultMatch(BaseModel):
    line_number: int
    content: str
    is_match: bool

class SearchResult(BaseModel):
    id: str
    name: str
    type: str  # file, class, function
    path: str
    language: str
    snippet: str
    score: float

class SemanticSearchResult(BaseModel):
    id: str
    name: str
    type: str  # function, class, file
    path: str
    body: str
    docstring: Optional[str] = None
    similarity: float

class GraphNode(BaseModel):
    id: str
    label: str
    type: str  # file, class, function
    path: Optional[str] = None

class GraphEdge(BaseModel):
    id: str
    source: str
    target: str

class GraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]

# AI Schemas
class AIExplanationResponse(BaseModel):
    purpose: str
    summary: str
    complexity: Dict[str, str]  # time, space
    improvements: List[str]
    potential_bugs: List[str]
    security_concerns: List[str]
    refactoring_suggestions: List[str]
    raw_response: str

# Duplicate Detection Schemas
class DuplicatePairResponse(BaseModel):
    function_a: FunctionResponse
    function_b: FunctionResponse
    similarity: float
