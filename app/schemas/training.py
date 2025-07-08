"""
학습 관련 스키마
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.training import TrainingStatus
from app.core.training.config import TrainingType


class TrainingMethodInfo(BaseModel):
    """학습 방법 정보"""
    id: str
    name: str
    description: str
    memory_requirement: str
    training_time: str
    supports_quantization: bool
    requires_preference_data: Optional[bool] = False
    default_config: Optional[Dict[str, Any]] = None


class TrainingConfig(BaseModel):
    """학습 설정 스키마"""
    project_id: UUID
    dataset_id: UUID
    base_model_id: Optional[UUID] = None
    model_name: str = Field(..., description="HuggingFace 모델 ID")
    training_type: TrainingType
    
    # 하이퍼파라미터
    num_train_epochs: int = 3
    per_device_train_batch_size: int = 4
    per_device_eval_batch_size: int = 4
    gradient_accumulation_steps: int = 4
    gradient_checkpointing: bool = True
    
    # 최적화 설정
    learning_rate: float = 2e-4
    weight_decay: float = 0.001
    warmup_ratio: float = 0.1
    max_grad_norm: float = 0.3
    
    # 데이터 설정
    max_seq_length: int = 512
    validation_split_percentage: int = 10
    
    # 방법별 설정
    lora_config: Optional[Dict[str, Any]] = None
    dpo_config: Optional[Dict[str, Any]] = None
    orpo_config: Optional[Dict[str, Any]] = None
    
    # 기타 설정
    use_wandb: bool = False
    early_stopping: bool = True


class TrainingJobCreate(BaseModel):
    """학습 작업 생성"""
    project_id: UUID
    dataset_id: UUID
    base_model_id: Optional[UUID] = None
    config: Dict[str, Any]


class TrainingJobUpdate(BaseModel):
    """학습 작업 업데이트"""
    status: Optional[TrainingStatus] = None


class TrainingMetrics(BaseModel):
    """학습 메트릭"""
    loss: Optional[float] = None
    eval_loss: Optional[float] = None
    learning_rate: Optional[float] = None
    epoch: Optional[int] = None
    step: Optional[int] = None
    total_steps: Optional[int] = None
    train_runtime: Optional[float] = None
    train_samples_per_second: Optional[float] = None
    eval_runtime: Optional[float] = None
    eval_samples_per_second: Optional[float] = None
    perplexity: Optional[float] = None


class TrainingJobResponse(BaseModel):
    """학습 작업 응답"""
    id: UUID
    project_id: UUID
    model_id: Optional[UUID]
    dataset_id: UUID
    config: Dict[str, Any]
    training_type: str
    status: TrainingStatus
    celery_task_id: Optional[str]
    output_path: Optional[str]
    metrics: Optional[Dict[str, Any]]
    error_message: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    failed_at: Optional[datetime]
    updated_at: datetime
    created_by: UUID
    
    class Config:
        from_attributes = True