"""
학습 작업 모델
"""
import enum
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

from sqlalchemy import Column, String, DateTime, Enum, JSON, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class TrainingStatus(str, enum.Enum):
    """학습 상태"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TrainingJob(Base):
    """학습 작업 모델"""
    __tablename__ = "training_jobs"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=UUID.uuid4)
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    model_id = Column(PG_UUID(as_uuid=True), ForeignKey("models.id"), nullable=True)
    dataset_id = Column(PG_UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=False)
    
    # 학습 설정
    config = Column(JSON, nullable=False)
    training_type = Column(String(50), nullable=False)
    
    # 상태 관리
    status = Column(Enum(TrainingStatus), default=TrainingStatus.PENDING, nullable=False)
    celery_task_id = Column(String(255), nullable=True)
    
    # 결과
    output_path = Column(Text, nullable=True)
    metrics = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # 시간 정보
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 생성자
    created_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # 관계
    project = relationship("Project", back_populates="training_jobs")
    model = relationship("Model", back_populates="training_jobs")
    dataset = relationship("Dataset", back_populates="training_jobs")
    creator = relationship("User", back_populates="training_jobs")
    
    def __repr__(self):
        return f"<TrainingJob {self.id} - {self.status}>"