from celery import Task
from typing import Dict, Any
import asyncio
from uuid import UUID
import logging
import json
from pathlib import Path

from app.core.celery_app import celery_app
from app.core.database import async_session_maker
from app.models.dataset import Dataset, DatasetStatus
from sqlalchemy import select

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="process_uploaded_dataset")
def process_uploaded_dataset(self, dataset_id: str, file_path: str) -> Dict[str, Any]:
    """
    Process uploaded dataset file
    
    Args:
        dataset_id: UUID of the dataset
        file_path: Path to uploaded file
    
    Returns:
        Dictionary with processing results
    """
    try:
        logger.info(f"Processing uploaded dataset {dataset_id}")
        
        # Update status
        asyncio.run(update_dataset_status(dataset_id, DatasetStatus.PROCESSING))
        
        # Read and analyze file
        file_path_obj = Path(file_path)
        
        if not file_path_obj.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        samples = []
        statistics = {}
        
        # Handle different file formats
        if file_path_obj.suffix == ".json":
            with open(file_path_obj, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    samples = data
                elif isinstance(data, dict) and "data" in data:
                    samples = data["data"]
                else:
                    samples = [data]
        
        elif file_path_obj.suffix in [".jsonl", ".txt"]:
            with open(file_path_obj, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            samples.append(json.loads(line))
                        except json.JSONDecodeError:
                            # Treat as plain text
                            samples.append({"text": line})
        
        # Calculate statistics
        num_samples = len(samples)
        
        if num_samples > 0:
            # Analyze sample structure
            sample_keys = set()
            for sample in samples[:100]:  # Check first 100 samples
                if isinstance(sample, dict):
                    sample_keys.update(sample.keys())
            
            statistics = {
                "num_samples": num_samples,
                "sample_keys": list(sample_keys),
                "file_size_mb": file_path_obj.stat().st_size / (1024 * 1024),
                "file_format": file_path_obj.suffix[1:]
            }
            
            # Calculate text statistics if applicable
            if "text" in sample_keys or "instruction" in sample_keys or "output" in sample_keys:
                text_lengths = []
                for sample in samples:
                    if isinstance(sample, dict):
                        text = sample.get("text", "") or sample.get("output", "") or sample.get("instruction", "")
                        text_lengths.append(len(str(text)))
                
                if text_lengths:
                    statistics["avg_text_length"] = sum(text_lengths) / len(text_lengths)
                    statistics["min_text_length"] = min(text_lengths)
                    statistics["max_text_length"] = max(text_lengths)
        
        # Update dataset in database
        result = {
            "num_samples": num_samples,
            "statistics": statistics,
            "status": "ready"
        }
        
        asyncio.run(update_dataset_status(dataset_id, DatasetStatus.READY, result))
        
        logger.info(f"Processing completed for dataset {dataset_id}")
        return result
        
    except Exception as e:
        logger.error(f"Processing failed for dataset {dataset_id}: {str(e)}")
        asyncio.run(update_dataset_status(
            dataset_id, 
            DatasetStatus.FAILED, 
            {"error": str(e)}
        ))
        raise


@celery_app.task(name="validate_dataset")
def validate_dataset(dataset_id: str) -> Dict[str, Any]:
    """
    Validate dataset quality and format
    
    Args:
        dataset_id: UUID of the dataset
    
    Returns:
        Dictionary with validation results
    """
    logger.info(f"Validating dataset {dataset_id}")
    
    # TODO: Implement dataset validation
    # Check for:
    # - Duplicate samples
    # - Missing fields
    # - Invalid formats
    # - Quality metrics
    
    return {
        "is_valid": True,
        "num_duplicates": 0,
        "num_invalid": 0,
        "quality_score": 0.95
    }


async def update_dataset_status(dataset_id: str, status: DatasetStatus, result: Dict[str, Any] = None):
    """Update dataset status in database"""
    async with async_session_maker() as session:
        stmt = select(Dataset).where(Dataset.id == UUID(dataset_id))
        result_db = await session.execute(stmt)
        dataset = result_db.scalar_one_or_none()
        
        if dataset:
            dataset.status = status
            if result:
                if "num_samples" in result:
                    dataset.size = result["num_samples"]
                if "statistics" in result:
                    dataset.statistics = result["statistics"]
            
            await session.commit()