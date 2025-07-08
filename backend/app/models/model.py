from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
import enum
from uuid import uuid4
from app.db.base_class import Base


class ModelStatus(str, enum.Enum):
    DRAFT = "draft"
    TRAINING = "training"
    READY = "ready"
    FAILED = "failed"
    DEPLOYED = "deployed"


class ModelProvider(str, enum.Enum):
    HUGGINGFACE = "huggingface"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    LOCAL = "local"


class Model(Base):
    __tablename__ = "models"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String, nullable=False)
    description = Column(Text)
    path = Column(String)  # Renamed from model_path
    base_model = Column(String)  # Base model name (e.g., "gpt2", "llama-7b")
    training_method = Column(String)  # Training method used (e.g., "lora", "full")
    provider = Column(Enum(ModelProvider), default=ModelProvider.HUGGINGFACE)
    status = Column(Enum(ModelStatus), default=ModelStatus.DRAFT)
    project_id = Column(PostgresUUID(as_uuid=True), ForeignKey("projects.id"))
    
    # Version management
    latest_version = Column(String)
    total_versions = Column(Integer, default=0)
    
    # Configuration and metadata
    config = Column(JSON)  # Training configuration
    model_metadata = Column(JSON)  # Additional metadata
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # User tracking
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"))
    
    # Relationships
    project = relationship("Project", back_populates="models")
    versions = relationship("ModelVersion", back_populates="model", cascade="all, delete-orphan")
    evaluations = relationship("ModelEvaluation", back_populates="model")
    benchmark_results = relationship("BenchmarkResult", back_populates="model")
    creator = relationship("User", back_populates="created_models")


class ModelVersion(Base):
    __tablename__ = "model_versions"
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    model_id = Column(PostgresUUID(as_uuid=True), ForeignKey("models.id"), nullable=False)
    version = Column(String, nullable=False)  # Version tag (e.g., "v1.0", "v2.0-beta")
    description = Column(Text)
    
    # File tracking
    path = Column(String, nullable=False)  # Path to version files
    model_hash = Column(String)  # SHA256 hash of model files
    commit_hash = Column(String)  # Git commit hash if using version control
    
    # Training information
    training_job_id = Column(PostgresUUID(as_uuid=True), ForeignKey("training_jobs.id"))
    metrics = Column(JSON)  # Training metrics for this version
    
    # Metadata
    version_metadata = Column(JSON)  # Additional version metadata
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # User tracking
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"))
    
    # Relationships
    model = relationship("Model", back_populates="versions")
    training_job = relationship("TrainingJob")
    creator = relationship("User")