"""
학습 파이프라인 서비스
"""
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
from pathlib import Path

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
)
from peft import (
    LoraConfig,
    get_peft_model,
    TaskType,
    prepare_model_for_kbit_training,
)
from datasets import Dataset, load_dataset
import torch
from accelerate import Accelerator

from app.models.training import TrainingJob, TrainingStatus
from app.models.model import Model, ModelStatus
from app.core.celery_app import celery_app
from app.core.config import settings


class TrainingPipelineService:
    """학습 파이프라인 관리 서비스"""
    
    def __init__(self):
        self.accelerator = Accelerator()
        self.training_jobs: Dict[str, Any] = {}
        
    async def create_training_job(
        self,
        db: AsyncSession,
        project_id: str,
        model_id: str,
        dataset_id: str,
        training_config: Dict[str, Any],
        user_id: str
    ) -> TrainingJob:
        """학습 작업 생성"""
        # 학습 작업 DB 엔트리 생성
        training_job = TrainingJob(
            project_id=project_id,
            model_id=model_id,
            dataset_id=dataset_id,
            config=training_config,
            status=TrainingStatus.PENDING,
            created_by=user_id,
            created_at=datetime.utcnow()
        )
        
        db.add(training_job)
        await db.commit()
        await db.refresh(training_job)
        
        # Celery 태스크 시작
        task = celery_app.send_task(
            "app.tasks.training.run_training",
            args=[training_job.id, training_config]
        )
        
        # 태스크 ID 저장
        training_job.celery_task_id = task.id
        await db.commit()
        
        logger.info(f"Created training job {training_job.id} with task {task.id}")
        return training_job
    
    async def get_supported_training_methods(self) -> List[Dict[str, Any]]:
        """지원되는 학습 방법 목록 반환"""
        return [
            {
                "id": "full_finetuning",
                "name": "Full Fine-tuning",
                "description": "전체 모델 파라미터를 학습",
                "memory_requirement": "high",
                "training_time": "long",
                "supports_quantization": False
            },
            {
                "id": "lora",
                "name": "LoRA",
                "description": "Low-Rank Adaptation을 사용한 효율적인 학습",
                "memory_requirement": "medium",
                "training_time": "medium",
                "supports_quantization": True,
                "default_config": {
                    "r": 16,
                    "lora_alpha": 32,
                    "lora_dropout": 0.1,
                    "target_modules": ["q_proj", "v_proj", "k_proj", "o_proj"]
                }
            },
            {
                "id": "qlora",
                "name": "QLoRA",
                "description": "4-bit 양자화와 LoRA를 결합한 메모리 효율적 학습",
                "memory_requirement": "low",
                "training_time": "medium",
                "supports_quantization": True,
                "default_config": {
                    "r": 16,
                    "lora_alpha": 32,
                    "lora_dropout": 0.1,
                    "bits": 4,
                    "bnb_4bit_compute_dtype": "float16",
                    "bnb_4bit_quant_type": "nf4"
                }
            },
            {
                "id": "dpo",
                "name": "DPO",
                "description": "Direct Preference Optimization",
                "memory_requirement": "medium",
                "training_time": "long",
                "supports_quantization": True,
                "requires_preference_data": True
            },
            {
                "id": "orpo",
                "name": "ORPO",
                "description": "Odds Ratio Preference Optimization",
                "memory_requirement": "medium",
                "training_time": "long",
                "supports_quantization": True,
                "requires_preference_data": True
            }
        ]
    
    def prepare_lora_model(
        self,
        model_name: str,
        lora_config: Dict[str, Any],
        load_in_8bit: bool = False,
        load_in_4bit: bool = False
    ):
        """LoRA 모델 준비"""
        # 기본 모델 로드
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            load_in_8bit=load_in_8bit,
            load_in_4bit=load_in_4bit,
            device_map="auto",
            torch_dtype=torch.float16,
            trust_remote_code=True
        )
        
        # 양자화된 모델 준비
        if load_in_8bit or load_in_4bit:
            model = prepare_model_for_kbit_training(model)
        
        # LoRA 설정
        peft_config = LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            r=lora_config.get("r", 16),
            lora_alpha=lora_config.get("lora_alpha", 32),
            lora_dropout=lora_config.get("lora_dropout", 0.1),
            target_modules=lora_config.get("target_modules", ["q_proj", "v_proj"]),
            bias="none"
        )
        
        # PEFT 모델 생성
        model = get_peft_model(model, peft_config)
        model.print_trainable_parameters()
        
        return model, peft_config
    
    def create_training_arguments(
        self,
        output_dir: str,
        training_config: Dict[str, Any]
    ) -> TrainingArguments:
        """학습 인자 생성"""
        return TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=training_config.get("num_epochs", 3),
            per_device_train_batch_size=training_config.get("batch_size", 4),
            gradient_accumulation_steps=training_config.get("gradient_accumulation_steps", 4),
            gradient_checkpointing=training_config.get("gradient_checkpointing", True),
            optim=training_config.get("optimizer", "adamw_torch"),
            learning_rate=training_config.get("learning_rate", 2e-4),
            warmup_ratio=training_config.get("warmup_ratio", 0.1),
            lr_scheduler_type=training_config.get("lr_scheduler", "cosine"),
            logging_steps=10,
            save_strategy="steps",
            save_steps=training_config.get("save_steps", 100),
            evaluation_strategy="steps",
            eval_steps=training_config.get("eval_steps", 100),
            do_eval=True,
            report_to=["tensorboard", "wandb"] if training_config.get("use_wandb", True) else ["tensorboard"],
            remove_unused_columns=False,
            fp16=training_config.get("fp16", True),
            bf16=training_config.get("bf16", False),
            load_best_model_at_end=True,
            metric_for_best_model="eval_loss",
            greater_is_better=False,
            group_by_length=True,
            push_to_hub=False,
            max_grad_norm=training_config.get("max_grad_norm", 0.3),
            warmup_steps=training_config.get("warmup_steps", 0),
            weight_decay=training_config.get("weight_decay", 0.001),
            logging_dir=f"{output_dir}/logs",
            dataloader_num_workers=4,
            run_name=training_config.get("run_name", f"training_{datetime.now().strftime('%Y%m%d_%H%M%S')}"),
        )
    
    async def update_training_status(
        self,
        db: AsyncSession,
        job_id: str,
        status: TrainingStatus,
        metrics: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ):
        """학습 상태 업데이트"""
        job = await db.get(TrainingJob, job_id)
        if not job:
            logger.error(f"Training job {job_id} not found")
            return
        
        job.status = status
        if metrics:
            job.metrics = metrics
        if error_message:
            job.error_message = error_message
        
        if status == TrainingStatus.COMPLETED:
            job.completed_at = datetime.utcnow()
        elif status == TrainingStatus.FAILED:
            job.failed_at = datetime.utcnow()
        
        await db.commit()
        logger.info(f"Updated training job {job_id} status to {status}")
    
    async def get_training_metrics(
        self,
        job_id: str
    ) -> Dict[str, Any]:
        """학습 메트릭 조회"""
        # TODO: W&B 또는 MLflow에서 실시간 메트릭 가져오기
        return {
            "loss": 0.0,
            "eval_loss": 0.0,
            "learning_rate": 0.0,
            "epoch": 0,
            "step": 0,
            "total_steps": 0
        }


# 싱글톤 인스턴스
training_pipeline_service = TrainingPipelineService()