from sqlalchemy import Column, String, Text, ForeignKey, DateTime, JSON, Enum, Integer
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import enum

from app.core.database import Base


class DeploymentStatus(str, enum.Enum):
    PENDING = "pending"
    DEPLOYING = "deploying"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"


class DeploymentType(str, enum.Enum):
    VLLM = "vllm"
    TGI = "tgi"
    FASTAPI = "fastapi"


class Deployment(Base):
    __tablename__ = "deployments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(Text)
    model_id = Column(UUID(as_uuid=True), ForeignKey("models.id"), nullable=False)
    type = Column(Enum(DeploymentType), default=DeploymentType.VLLM)
    status = Column(Enum(DeploymentStatus), default=DeploymentStatus.PENDING)
    endpoint_url = Column(String)
    api_key = Column(String)
    config = Column(JSON)  # Deployment configuration
    replicas = Column(Integer, default=1)
    resources = Column(JSON)  # CPU, memory, GPU requirements
    metrics = Column(JSON)  # Usage metrics
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    model = relationship("Model", backref="deployments")