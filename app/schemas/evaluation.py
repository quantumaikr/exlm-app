"""
평가 관련 스키마
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.evaluation import EvaluationStatus


class EvaluationCreate(BaseModel):
    """평가 생성"""
    model_id: UUID
    dataset_id: Optional[UUID] = None
    metrics: List[str] = Field(default=["perplexity", "bleu", "rouge"])
    config: Optional[Dict[str, Any]] = None


class EvaluationUpdate(BaseModel):
    """평가 업데이트"""
    status: EvaluationStatus
    results: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class EvaluationResponse(BaseModel):
    """평가 응답"""
    id: UUID
    model_id: UUID
    dataset_id: Optional[UUID]
    metrics: List[str]
    config: Optional[Dict[str, Any]]
    status: EvaluationStatus
    celery_task_id: Optional[str]
    results: Optional[Dict[str, Any]]
    error_message: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    failed_at: Optional[datetime]
    created_by: UUID
    
    class Config:
        orm_mode = True


class ComparisonCreate(BaseModel):
    """모델 비교 생성"""
    model_ids: List[UUID]
    dataset_id: UUID
    metrics: List[str] = Field(default=["perplexity", "bleu", "rouge", "accuracy"])


class ComparisonResponse(BaseModel):
    """비교 응답"""
    comparison_id: str
    model_ids: List[str]
    dataset_id: str
    metrics: List[str]
    evaluations: Dict[str, str]  # model_id -> evaluation_id mapping
    created_at: str


class BenchmarkResultResponse(BaseModel):
    """벤치마크 결과"""
    id: UUID
    model_id: UUID
    benchmark_name: str
    benchmark_version: Optional[str]
    scores: Dict[str, float]
    overall_score: Optional[float]
    metadata: Optional[Dict[str, Any]]
    created_at: datetime
    
    class Config:
        orm_mode = True