from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from app.models.model import ModelStatus, ModelProvider


class ModelBase(BaseModel):
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    provider: Optional[ModelProvider] = None
    huggingface_model_id: Optional[str] = None
    dataset_id: Optional[UUID] = None
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)
    model_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ModelCreate(ModelBase):
    project_id: UUID


class ModelUpdate(BaseModel):
    name: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    model_metadata: Optional[Dict[str, Any]] = None
    status: Optional[ModelStatus] = None


class ModelResponse(ModelBase):
    id: UUID
    project_id: UUID
    status: ModelStatus
    metrics: Optional[Dict[str, Any]] = None
    model_path: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ModelListResponse(BaseModel):
    items: list[ModelResponse]
    total: int
    page: int
    pages: int


class HuggingFaceModelResponse(BaseModel):
    """Response model for Hugging Face model data"""
    id: str
    name: str
    full_name: str
    author: str
    downloads: int
    likes: int
    trending_score: float
    created_at: str
    updated_at: str
    private: bool
    tags: List[str]
    pipeline_tag: str
    library_name: str
    size: str
    parameters: str
    license: str
    description: str
    provider: ModelProvider
    model_index: Optional[Dict[str, Any]] = None
    config: Optional[Dict[str, Any]] = None
    card_data: Optional[Dict[str, Any]] = None
    siblings: Optional[List[Dict[str, Any]]] = None
    performance_metrics: Optional[Dict[str, Any]] = None
    requirements: Optional[Dict[str, Any]] = None


class ModelImportRequest(BaseModel):
    """Request model for importing a Hugging Face model"""
    huggingface_model_id: str
    project_id: UUID
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)