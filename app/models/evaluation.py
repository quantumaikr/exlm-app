"""
평가 관련 데이터베이스 모델
"""
import enum
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4

from sqlalchemy import Column, String, DateTime, Enum, JSON, ForeignKey, Text, Float
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class EvaluationStatus(str, enum.Enum):
    """평가 상태"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ModelEvaluation(Base):
    """모델 평가"""
    __tablename__ = "model_evaluations"
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    model_id = Column(PostgresUUID(as_uuid=True), ForeignKey("models.id"), nullable=False)
    dataset_id = Column(PostgresUUID(as_uuid=True), ForeignKey("datasets.id"), nullable=True)
    
    # 평가 설정
    metrics = Column(JSON, nullable=False)  # 평가할 메트릭 목록
    config = Column(JSON, nullable=True)    # 추가 설정
    
    # 상태
    status = Column(Enum(EvaluationStatus), default=EvaluationStatus.PENDING, nullable=False)
    celery_task_id = Column(String, nullable=True)
    
    # 결과
    results = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 관계
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    model = relationship("Model", back_populates="evaluations")
    dataset = relationship("Dataset", back_populates="evaluations")
    creator = relationship("User", back_populates="model_evaluations")


class BenchmarkResult(Base):
    """벤치마크 결과"""
    __tablename__ = "benchmark_results"
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    model_id = Column(PostgresUUID(as_uuid=True), ForeignKey("models.id"), nullable=False)
    evaluation_id = Column(PostgresUUID(as_uuid=True), ForeignKey("model_evaluations.id"), nullable=True)
    
    # 벤치마크 정보
    benchmark_name = Column(String, nullable=False)  # mmlu, human_eval, truthfulqa 등
    benchmark_version = Column(String, nullable=True)
    
    # 결과
    scores = Column(JSON, nullable=False)  # 세부 점수들
    overall_score = Column(Float, nullable=True)  # 전체 점수
    benchmark_metadata = Column(JSON, nullable=True)  # 추가 메타데이터
    
    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # 관계
    model = relationship("Model", back_populates="benchmark_results")
    evaluation = relationship("ModelEvaluation")


class EvaluationComparison(Base):
    """모델 비교 평가"""
    __tablename__ = "evaluation_comparisons"
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # 비교 설정
    model_ids = Column(JSON, nullable=False)  # 비교할 모델 ID 목록
    dataset_id = Column(PostgresUUID(as_uuid=True), ForeignKey("datasets.id"), nullable=False)
    metrics = Column(JSON, nullable=False)    # 비교할 메트릭 목록
    
    # 결과
    evaluation_ids = Column(JSON, nullable=True)  # 각 모델의 평가 ID
    comparison_results = Column(JSON, nullable=True)  # 비교 분석 결과
    
    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 관계
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    dataset = relationship("Dataset")
    creator = relationship("User")