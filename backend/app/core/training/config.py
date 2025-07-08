"""
학습 설정 모델
"""
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class TrainingType(str, Enum):
    """학습 방법 타입"""
    FULL_FINETUNING = "full_finetuning"
    LORA = "lora"
    QLORA = "qlora"
    DPO = "dpo"
    ORPO = "orpo"


class TrainingConfig(BaseModel):
    """학습 설정"""
    # 기본 설정
    model_name: str = Field(..., description="기본 모델명 (HuggingFace 모델 ID)")
    dataset_id: str = Field(..., description="데이터셋 ID")
    training_type: TrainingType = Field(TrainingType.LORA, description="학습 방법")
    
    # 학습 하이퍼파라미터
    num_train_epochs: int = Field(3, description="학습 에폭 수")
    per_device_train_batch_size: int = Field(4, description="디바이스당 학습 배치 크기")
    per_device_eval_batch_size: int = Field(4, description="디바이스당 평가 배치 크기")
    gradient_accumulation_steps: int = Field(4, description="그래디언트 누적 스텝")
    gradient_checkpointing: bool = Field(True, description="그래디언트 체크포인팅 사용")
    
    # 최적화 설정
    optim: str = Field("adamw_torch", description="옵티마이저")
    learning_rate: float = Field(2e-4, description="학습률")
    weight_decay: float = Field(0.001, description="가중치 감쇠")
    warmup_ratio: float = Field(0.1, description="웜업 비율")
    warmup_steps: int = Field(0, description="웜업 스텝 (0이면 warmup_ratio 사용)")
    lr_scheduler_type: str = Field("cosine", description="학습률 스케줄러")
    max_grad_norm: float = Field(0.3, description="최대 그래디언트 norm")
    
    # 데이터 설정
    max_seq_length: int = Field(512, description="최대 시퀀스 길이")
    validation_split_percentage: int = Field(10, description="검증 데이터 비율 (%)")
    dataloader_num_workers: int = Field(4, description="데이터로더 워커 수")
    group_by_length: bool = Field(True, description="길이별 그룹화")
    
    # 로깅 및 저장 설정
    logging_steps: int = Field(10, description="로깅 간격")
    save_steps: int = Field(100, description="저장 간격")
    eval_steps: int = Field(100, description="평가 간격")
    save_total_limit: int = Field(3, description="최대 체크포인트 저장 수")
    load_best_model_at_end: bool = Field(True, description="학습 종료 시 최고 모델 로드")
    
    # 학습 정밀도
    fp16: bool = Field(True, description="FP16 사용")
    bf16: bool = Field(False, description="BF16 사용")
    tf32: bool = Field(True, description="TF32 사용 (NVIDIA GPU)")
    
    # 기타 설정
    seed: int = Field(42, description="랜덤 시드")
    use_wandb: bool = Field(False, description="Weights & Biases 사용")
    early_stopping: bool = Field(True, description="조기 종료 사용")
    push_to_hub: bool = Field(False, description="HuggingFace Hub에 푸시")
    
    # 방법별 설정
    lora_config: Optional[Dict[str, Any]] = Field(None, description="LoRA 설정")
    dpo_config: Optional[Dict[str, Any]] = Field(None, description="DPO 설정")
    orpo_config: Optional[Dict[str, Any]] = Field(None, description="ORPO 설정")
    
    def get_method_config(self) -> Optional[Dict[str, Any]]:
        """학습 방법에 따른 설정 반환"""
        if self.training_type in [TrainingType.LORA, TrainingType.QLORA]:
            return self.lora_config
        elif self.training_type == TrainingType.DPO:
            return self.dpo_config
        elif self.training_type == TrainingType.ORPO:
            return self.orpo_config
        return None
    
    class Config:
        json_encoders = {
            TrainingType: lambda v: v.value
        }