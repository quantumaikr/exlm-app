"""
Model training tasks
"""

import os
import json
import traceback
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime

from celery import Task
from sqlalchemy import select

from app.core.celery_app import celery_app
from app.core.database import async_session_maker
from app.core.config import settings
from app.core.logging import logger
from app.core.training.config import TrainingConfig
from app.core.training.pipeline import run_training_pipeline
from app.core.websocket import manager
from app.models.training_job import TrainingJob, TrainingStatus
from app.models.model import Model, ModelStatus


class TrainingTask(Task):
    """Base task for training jobs"""
    
    def on_success(self, retval, task_id, args, kwargs):
        """Success callback"""
        job_id = kwargs.get("job_id")
        if job_id:
            asyncio.run(update_training_status(
                job_id, 
                TrainingStatus.COMPLETED, 
                retval
            ))
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Failure callback"""
        job_id = kwargs.get("job_id")
        if job_id:
            asyncio.run(update_training_status(
                job_id,
                TrainingStatus.FAILED,
                {"error": str(exc), "traceback": str(einfo)}
            ))


async def update_training_status(
    job_id: str, 
    status: TrainingStatus, 
    result: Optional[Dict[str, Any]] = None
):
    """Update training job status in database"""
    async with async_session_maker() as session:
        stmt = select(TrainingJob).where(TrainingJob.id == UUID(job_id))
        result_db = await session.execute(stmt)
        job = result_db.scalar_one_or_none()
        
        if job:
            job.status = status
            job.updated_at = datetime.utcnow()
            
            if result:
                job.result = result
                
                # Update model status if training completed successfully
                if status == TrainingStatus.COMPLETED and result.get("status") == "completed":
                    job.model_path = result.get("model_path")
                    job.metrics = result.get("metrics", {})
                    
                    # Create or update model record
                    if job.model_id:
                        stmt_model = select(Model).where(Model.id == job.model_id)
                        result_model = await session.execute(stmt_model)
                        model = result_model.scalar_one_or_none()
                        
                        if model:
                            model.status = ModelStatus.READY
                            model.file_path = result.get("model_path")
                            model.metrics = result.get("metrics", {})
                            model.updated_at = datetime.utcnow()
            
            await session.commit()
            
            # Send WebSocket notification
            await manager.broadcast({
                "type": f"training_{status.value}",
                "data": {
                    "job_id": job_id,
                    "status": status.value,
                    "model_id": str(job.model_id) if job.model_id else None,
                    "result": result
                }
            })


@celery_app.task(base=TrainingTask, bind=True, name="run_training_job")
def run_training_job(self, job_id: str, config_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run a training job
    
    Args:
        job_id: Training job ID
        config_dict: Training configuration dictionary
    
    Returns:
        Training results
    """
    try:
        logger.info(f"Starting training job {job_id}")
        
        # Update status to running
        asyncio.run(update_training_status(job_id, TrainingStatus.RUNNING))
        
        # Parse configuration
        config = TrainingConfig(**config_dict)
        
        # Set up progress reporting
        progress_callback = lambda current, total, message: self.update_state(
            state="PROGRESS",
            meta={
                "current": current,
                "total": total,
                "status": message,
                "job_id": job_id
            }
        )
        
        # Run training pipeline
        result = run_training_pipeline(config)
        
        logger.info(f"Training job {job_id} completed with status: {result.get('status')}")
        return result
        
    except Exception as e:
        logger.error(f"Training job {job_id} failed: {str(e)}")
        raise


@celery_app.task(name="validate_training_config")
def validate_training_config(config_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate training configuration
    
    Args:
        config_dict: Training configuration dictionary
    
    Returns:
        Validation results
    """
    try:
        # Parse configuration
        config = TrainingConfig(**config_dict)
        
        # Validate dataset exists
        dataset_path = Path(settings.UPLOAD_DIR) / "datasets" / config.dataset_id
        if not dataset_path.exists():
            return {
                "valid": False,
                "errors": [f"Dataset not found: {config.dataset_id}"]
            }
        
        # Check for data files
        data_files_exist = False
        for ext in [".jsonl", ".json"]:
            file_path = dataset_path / f"generated_data{ext}"
            if file_path.exists():
                data_files_exist = True
                break
        
        if not data_files_exist:
            return {
                "valid": False,
                "errors": ["No data files found in dataset directory"]
            }
        
        # Validate model name (basic check)
        if not config.model_name:
            return {
                "valid": False,
                "errors": ["Model name is required"]
            }
        
        # Check if method-specific config is provided
        if config.training_type.value in ["lora", "qlora", "dpo", "orpo"]:
            method_config = config.get_method_config()
            if not method_config:
                return {
                    "valid": False,
                    "errors": [f"Configuration required for {config.training_type.value} training"]
                }
        
        return {
            "valid": True,
            "errors": [],
            "warnings": [],
            "estimated_duration": estimate_training_duration(config),
            "estimated_resources": estimate_resource_requirements(config)
        }
        
    except Exception as e:
        return {
            "valid": False,
            "errors": [f"Configuration validation failed: {str(e)}"]
        }


def estimate_training_duration(config: TrainingConfig) -> Dict[str, Any]:
    """Estimate training duration based on configuration"""
    # This is a simplified estimation - in practice you'd use more sophisticated methods
    base_time_per_epoch = 30  # minutes
    
    # Adjust based on model size (simplified)
    model_size_factor = 1.0
    if "large" in config.model_name.lower() or "7b" in config.model_name.lower():
        model_size_factor = 3.0
    elif "medium" in config.model_name.lower():
        model_size_factor = 1.5
    
    # Adjust based on training type
    training_type_factor = {
        "full_finetuning": 1.0,
        "lora": 0.6,
        "qlora": 0.4,
        "dpo": 0.8,
        "orpo": 0.7
    }.get(config.training_type.value, 1.0)
    
    # Calculate estimated time
    estimated_minutes = (
        base_time_per_epoch * 
        config.num_train_epochs * 
        model_size_factor * 
        training_type_factor
    )
    
    return {
        "estimated_minutes": int(estimated_minutes),
        "estimated_hours": round(estimated_minutes / 60, 1),
        "factors": {
            "model_size_factor": model_size_factor,
            "training_type_factor": training_type_factor,
            "epochs": config.num_train_epochs
        }
    }


def estimate_resource_requirements(config: TrainingConfig) -> Dict[str, Any]:
    """Estimate resource requirements based on configuration"""
    # Simplified resource estimation
    base_gpu_memory = 8  # GB
    base_ram = 16  # GB
    
    # Adjust based on model size
    if "large" in config.model_name.lower() or "7b" in config.model_name.lower():
        gpu_memory = 24
        ram = 32
    elif "medium" in config.model_name.lower():
        gpu_memory = 16
        ram = 24
    else:
        gpu_memory = base_gpu_memory
        ram = base_ram
    
    # Adjust based on training type
    if config.training_type == "qlora":
        gpu_memory = max(8, gpu_memory // 2)  # QLoRA reduces memory usage
    elif config.training_type == "lora":
        gpu_memory = max(8, int(gpu_memory * 0.7))  # LoRA reduces memory usage
    
    # Adjust based on batch size
    batch_size_factor = config.per_device_train_batch_size / 8
    gpu_memory = int(gpu_memory * batch_size_factor)
    
    return {
        "min_gpu_memory_gb": gpu_memory,
        "min_ram_gb": ram,
        "recommended_gpu": "RTX 3090" if gpu_memory <= 24 else "A100",
        "supports_cpu_training": config.training_type in ["lora", "qlora"],
        "estimated_disk_space_gb": 5 + (gpu_memory // 4)  # Model + checkpoints
    }


async def get_training_job(job_id: str):
    """Get training job from database"""
    async with async_session_maker() as session:
        stmt = select(TrainingJob).where(TrainingJob.id == UUID(job_id))
        result = await session.execute(stmt)
        return result.scalar_one_or_none()