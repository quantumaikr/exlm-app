from sqlalchemy import Column, String, Text, ForeignKey, DateTime, JSON, Enum
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import enum

from app.core.database import Base


class PipelineStatus(str, enum.Enum):
    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Pipeline(Base):
    __tablename__ = "pipelines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(Text)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    model_id = Column(UUID(as_uuid=True), ForeignKey("models.id"))
    status = Column(Enum(PipelineStatus), default=PipelineStatus.DRAFT)
    config = Column(JSON, nullable=False)  # Pipeline configuration
    steps = Column(JSON)  # Pipeline steps and their status
    results = Column(JSON)  # Pipeline execution results
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

    # Relationships
    project = relationship("Project", backref="pipelines")
    model = relationship("Model", backref="pipelines")