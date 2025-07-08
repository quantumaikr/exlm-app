from celery import Task
from typing import Dict, Any
import asyncio
from uuid import UUID
import logging

from app.core.celery_app import celery_app
from app.core.database import async_session_maker
from app.models.model import Model, ModelStatus
from sqlalchemy import select

logger = logging.getLogger(__name__)


class CallbackTask(Task):
    """Task that runs callbacks on success/failure"""
    
    def on_success(self, retval, task_id, args, kwargs):
        """Success callback"""
        model_id = kwargs.get("model_id")
        if model_id:
            asyncio.run(update_model_status(model_id, ModelStatus.COMPLETED, retval))
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Failure callback"""
        model_id = kwargs.get("model_id")
        if model_id:
            asyncio.run(update_model_status(
                model_id, 
                ModelStatus.FAILED, 
                {"error": str(exc), "traceback": str(einfo)}
            ))


async def update_model_status(model_id: str, status: ModelStatus, result: Dict[str, Any] = None):
    """Update model status in database"""
    async with async_session_maker() as session:
        stmt = select(Model).where(Model.id == UUID(model_id))
        result_db = await session.execute(stmt)
        model = result_db.scalar_one_or_none()
        
        if model:
            model.status = status
            if result and status == ModelStatus.COMPLETED:
                model.metrics = result.get("metrics", {})
                model.model_path = result.get("model_path")
            elif result and status == ModelStatus.FAILED:
                model.metrics = {"error": result.get("error")}
            
            await session.commit()


@celery_app.task(base=CallbackTask, bind=True, name="train_model")
def train_model(self, model_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Train a model with given configuration
    
    Args:
        model_id: UUID of the model
        config: Training configuration
    
    Returns:
        Dictionary with training results
    """
    try:
        logger.info(f"Starting training for model {model_id}")
        
        # Update status to training
        asyncio.run(update_model_status(model_id, ModelStatus.TRAINING))
        
        # TODO: Implement actual training logic
        # This is a placeholder that simulates training
        import time
        
        # Simulate training phases
        phases = ["Loading data", "Preprocessing", "Training", "Evaluating", "Saving model"]
        for i, phase in enumerate(phases):
            self.update_state(
                state="PROGRESS",
                meta={
                    "current": i + 1,
                    "total": len(phases),
                    "status": phase
                }
            )
            time.sleep(2)  # Simulate work
        
        # Simulate training results
        result = {
            "metrics": {
                "loss": 0.234,
                "accuracy": 0.912,
                "f1_score": 0.897,
                "training_time": "2h 15m"
            },
            "model_path": f"/models/{model_id}/model.bin"
        }
        
        logger.info(f"Training completed for model {model_id}")
        return result
        
    except Exception as e:
        logger.error(f"Training failed for model {model_id}: {str(e)}")
        raise


@celery_app.task(name="evaluate_model")
def evaluate_model(model_id: str, test_data_path: str) -> Dict[str, Any]:
    """
    Evaluate a trained model
    
    Args:
        model_id: UUID of the model
        test_data_path: Path to test dataset
    
    Returns:
        Dictionary with evaluation metrics
    """
    logger.info(f"Evaluating model {model_id}")
    
    # TODO: Implement actual evaluation logic
    # Placeholder implementation
    return {
        "test_loss": 0.312,
        "test_accuracy": 0.889,
        "test_f1_score": 0.876,
        "confusion_matrix": [[120, 15], [12, 153]]
    }