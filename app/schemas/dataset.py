from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from enum import Enum


class DatasetType(str, Enum):
    UPLOADED = "uploaded"
    GENERATED = "generated"
    MIXED = "mixed"


class DatasetFormat(str, Enum):
    """Supported dataset formats."""
    JSON = "json"
    JSONL = "jsonl"
    CSV = "csv"
    TSV = "tsv"
    PARQUET = "parquet"
    ALPACA = "alpaca"
    SHAREGPT = "sharegpt"


class DatasetStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class PreprocessingConfig(BaseModel):
    """Configuration for dataset preprocessing."""
    clean_text: bool = True
    remove_duplicates: bool = True
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    filter_languages: Optional[List[str]] = None
    add_metadata: bool = True
    target_format: Optional[DatasetFormat] = None
    train_test_split: bool = True
    test_split_ratio: float = 0.1
    required_fields: Optional[List[str]] = None


class DatasetBase(BaseModel):
    name: str
    description: Optional[str] = None
    type: DatasetType = DatasetType.UPLOADED
    format: Optional[DatasetFormat] = None


class DatasetCreate(DatasetBase):
    project_id: UUID
    generation_config: Optional[Dict[str, Any]] = None
    preprocessing_config: Optional[PreprocessingConfig] = None


class DatasetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class DatasetStatistics(BaseModel):
    """Dataset statistics."""
    total_samples: int
    avg_input_length: float
    avg_output_length: float
    language_distribution: Dict[str, int]
    quality_distribution: Dict[str, int]
    removed_samples: int = 0
    
    model_config = ConfigDict(from_attributes=True)


class QualityMetrics(BaseModel):
    """Quality metrics for dataset."""
    overall_score: float = Field(..., ge=0, le=10)
    completeness: float = Field(..., ge=0, le=10)
    accuracy: float = Field(..., ge=0, le=10)
    relevance: float = Field(..., ge=0, le=10)
    consistency: float = Field(..., ge=0, le=10)
    diversity: float = Field(..., ge=0, le=10)
    toxicity: float = Field(..., ge=0, le=1)
    total_samples: int
    high_quality_samples: int
    low_quality_samples: int
    average_length: float
    vocabulary_size: int
    duplicate_rate: float
    
    model_config = ConfigDict(from_attributes=True)


class DatasetResponse(DatasetBase):
    id: UUID
    project_id: UUID
    status: DatasetStatus
    size: Optional[int] = None
    file_path: Optional[str] = None
    samples_count: Optional[int] = None
    generation_config: Optional[Dict[str, Any]] = None
    preprocessing_config: Optional[PreprocessingConfig] = None
    statistics: Optional[DatasetStatistics] = None
    quality_metrics: Optional[QualityMetrics] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DatasetListResponse(BaseModel):
    items: list[DatasetResponse]
    total: int
    page: int
    pages: int


class DataGenerationConfig(BaseModel):
    provider: str  # "openai", "anthropic", "google"
    model: str
    prompt_template: str
    num_samples: int = Field(100, gt=0, le=10000)
    temperature: float = Field(0.7, ge=0, le=2)
    max_tokens: Optional[int] = Field(None, gt=0)
    system_prompt: Optional[str] = None
    variables: Optional[Dict[str, Any]] = None
    quality_filter: bool = True
    min_quality_score: float = Field(7.0, ge=0, le=10)
    domain_keywords: Optional[list[str]] = None
    
    model_config = ConfigDict(from_attributes=True)


class DataSampleBase(BaseModel):
    """Base schema for data sample."""
    instruction: Optional[str] = None
    input: Optional[str] = None
    output: Optional[str] = None
    response: Optional[str] = None
    text: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(from_attributes=True)


class DataSampleCreate(DataSampleBase):
    """Schema for creating data sample."""
    dataset_id: UUID


class DataSampleUpdate(BaseModel):
    """Schema for updating data sample."""
    instruction: Optional[str] = None
    input: Optional[str] = None
    output: Optional[str] = None
    response: Optional[str] = None
    text: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(from_attributes=True)


class DataSampleResponse(DataSampleBase):
    """Response schema for data sample."""
    id: UUID
    dataset_id: UUID
    quality_score: Optional[float] = None
    category: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class PreprocessingJobCreate(BaseModel):
    """Schema for creating preprocessing job."""
    dataset_id: UUID
    config: PreprocessingConfig
    
    model_config = ConfigDict(from_attributes=True)


class PreprocessingJobResponse(BaseModel):
    """Response schema for preprocessing job."""
    id: UUID
    dataset_id: UUID
    config: PreprocessingConfig
    status: str  # 'pending', 'processing', 'completed', 'failed'
    progress: float = Field(..., ge=0, le=100)
    statistics: Optional[DatasetStatistics] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)