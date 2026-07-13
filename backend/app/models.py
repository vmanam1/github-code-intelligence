import uuid
from sqlalchemy import Column, String, Integer, Float, ForeignKey, DateTime, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Repository(Base):
    __tablename__ = "repositories"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    url = Column(String(1024), nullable=False)
    clone_path = Column(String(1024), nullable=True)
    status = Column(String(50), nullable=False, default="PENDING")  # PENDING, CLONING, PARSING, INDEXING, COMPLETED, FAILED
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    files = relationship("File", back_populates="repository", cascade="all, delete-orphan")
    statistics = relationship("RepositoryStatistics", back_populates="repository", uselist=False, cascade="all, delete-orphan")


class File(Base):
    __tablename__ = "files"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    repository_id = Column(String(36), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    path = Column(String(1024), nullable=False)
    language = Column(String(50), nullable=False)
    size = Column(Integer, nullable=False)
    lines_count = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    repository = relationship("Repository", back_populates="files")
    classes = relationship("Class", back_populates="file", cascade="all, delete-orphan")
    functions = relationship("Function", back_populates="file", cascade="all, delete-orphan")
    imports = relationship("Import", back_populates="file", cascade="all, delete-orphan")


class Class(Base):
    __tablename__ = "classes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    file_id = Column(String(36), ForeignKey("files.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    start_line = Column(Integer, nullable=False)
    end_line = Column(Integer, nullable=False)
    body = Column(Text, nullable=False)
    docstring = Column(Text, nullable=True)

    # Relationships
    file = relationship("File", back_populates="classes")
    functions = relationship("Function", back_populates="class_ctx", cascade="all, delete-orphan")


class Function(Base):
    __tablename__ = "functions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    file_id = Column(String(36), ForeignKey("files.id", ondelete="CASCADE"), nullable=False)
    class_id = Column(String(36), ForeignKey("classes.id", ondelete="CASCADE"), nullable=True)
    name = Column(String(255), nullable=False)
    signature = Column(Text, nullable=False)
    start_line = Column(Integer, nullable=False)
    end_line = Column(Integer, nullable=False)
    body = Column(Text, nullable=False)
    docstring = Column(Text, nullable=True)

    # Relationships
    file = relationship("File", back_populates="functions")
    class_ctx = relationship("Class", back_populates="functions")


class Import(Base):
    __tablename__ = "imports"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    file_id = Column(String(36), ForeignKey("files.id", ondelete="CASCADE"), nullable=False)
    source = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    alias = Column(String(255), nullable=True)
    line_number = Column(Integer, nullable=False)

    # Relationships
    file = relationship("File", back_populates="imports")


class RepositoryStatistics(Base):
    __tablename__ = "repository_statistics"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    repository_id = Column(String(36), ForeignKey("repositories.id", ondelete="CASCADE"), unique=True, nullable=False)
    total_files = Column(Integer, nullable=False, default=0)
    total_lines_of_code = Column(Integer, nullable=False, default=0)
    total_functions = Column(Integer, nullable=False, default=0)
    total_classes = Column(Integer, nullable=False, default=0)
    language_distribution = Column(JSON, nullable=False, default=dict)
    avg_function_size = Column(Float, nullable=False, default=0.0)
    largest_files = Column(JSON, nullable=False, default=list)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    repository = relationship("Repository", back_populates="statistics")
