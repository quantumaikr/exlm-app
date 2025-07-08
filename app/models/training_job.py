from sqlalchemy import Column, String, Integer, Float, JSON, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
import enum

from app.db.base_class import Base


class TrainingStatus(str, enum.Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TrainingJob(Base):
    __tablename__ = "training_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    
    # Status
    status = Column(Enum(TrainingStatus), default=TrainingStatus.PENDING)
    progress = Column(Float, default=0.0)  # 0-100
    
    # Configuration
    base_model = Column(String, nullable=False)
    training_method = Column(String, nullable=False)  # "lora", "full", "qlora"
    hyperparameters = Column(JSON, default={})
    
    # Resources
    gpu_type = Column(String)
    gpu_count = Column(Integer, default=1)
    
    # Metrics
    current_epoch = Column(Integer, default=0)
    total_epochs = Column(Integer)
    current_step = Column(Integer, default=0)
    total_steps = Column(Integer)
    loss = Column(Float)
    learning_rate = Column(Float)
    metrics = Column(JSON, default={})
    
    # Logs
    logs = Column(JSON, default=[])
    error_message = Column(String)
    
    # Celery task
    task_id = Column(String, unique=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign keys
    model_id = Column(UUID(as_uuid=True), ForeignKey("models.id", ondelete="CASCADE"))
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="SET NULL"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    
    # Relationships
    model = relationship("Model", back_populates="training_jobs")
    dataset = relationship("Dataset")
    user = relationship("User")