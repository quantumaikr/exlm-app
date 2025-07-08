"""
버전 관리 관련 스키마
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

from pydantic import BaseModel, Field


class VersionCreate(BaseModel):
    """버전 생성"""
    version: str = Field(..., description="Version tag (e.g., v1.0, v2.0-beta)")
    description: Optional[str] = None
    training_job_id: Optional[UUID] = None
    metrics: Optional[Dict[str, Any]] = None


class VersionResponse(BaseModel):
    """버전 응답"""
    id: UUID
    model_id: UUID
    version: str
    description: Optional[str]
    path: str
    model_hash: Optional[str]
    commit_hash: Optional[str]
    training_job_id: Optional[UUID]
    metrics: Optional[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]]
    created_at: datetime
    created_by: UUID
    
    class Config:
        orm_mode = True


class VersionComparison(BaseModel):
    """버전 비교 결과"""
    model_id: str
    versions: Dict[str, str]
    timestamps: Dict[str, str]
    file_changes: Dict[str, Any]
    metric_comparison: Dict[str, Any]
    config_changes: Dict[str, Any]
    git_diff: Optional[Dict[str, Any]] = None


class VersionExport(BaseModel):
    """버전 내보내기"""
    format: str = Field(default="huggingface", description="Export format: huggingface, onnx, archive")
    output_path: Optional[str] = None