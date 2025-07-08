from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.db.base_class import Base


class DatasetType(str, enum.Enum):
    UPLOADED = "uploaded"
    GENERATED = "generated"
    MIXED = "mixed"


class DatasetStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class DatasetFormat(str, enum.Enum):
    JSON = "json"
    JSONL = "jsonl"
    CSV = "csv"
    TSV = "tsv"
    PARQUET = "parquet"
    ALPACA = "alpaca"
    SHAREGPT = "sharegpt"


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    project_id = Column(Integer, ForeignKey("projects.id"))
    type = Column(Enum(DatasetType), default=DatasetType.UPLOADED)
    format = Column(Enum(DatasetFormat), default=DatasetFormat.JSONL)
    status = Column(Enum(DatasetStatus), default=DatasetStatus.PENDING)
    size = Column(Integer)  # Size in bytes
    samples_count = Column(Integer)  # Number of samples
    file_path = Column(String)  # Path to dataset file
    generation_config = Column(JSON)  # Config for generated datasets
    preprocessing_config = Column(JSON)  # Config for preprocessing
    statistics = Column(JSON)  # Dataset statistics
    quality_metrics = Column(JSON)  # Quality evaluation metrics
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="datasets")