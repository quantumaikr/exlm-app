"""Data quality evaluation API endpoints."""
from typing import Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
import json
from pathlib import Path
import aiofiles

from app.db.deps import get_db
from app.models.user import User
from app.api.deps import get_current_user
from app.schemas.dataset import QualityMetrics, DataSampleBase
from app.services.data_quality import data_quality_service
from app.crud import dataset as dataset_crud
from app.core.config import settings
from app.db.redis import redis_client


router = APIRouter()


async def evaluate_quality_task(
    dataset_id: UUID,
    job_id: str,
    db: AsyncSession
):
    """Background task for quality evaluation."""
    try:
        # Update progress
        await redis_client.setex(
            f"quality_job:{job_id}",
            3600,
            json.dumps({"status": "processing", "progress": 10})
        )
        
        # Get dataset
        dataset = await dataset_crud.get(db, id=dataset_id)
        if not dataset:
            raise ValueError("Dataset not found")
        
        # Load dataset samples
        samples = []
        
        # Try processed data first
        processed_dir = Path(settings.DATA_DIR) / "processed" / str(dataset_id)
        jsonl_file = processed_dir / "processed.jsonl"
        
        if jsonl_file.exists():
            async with aiofiles.open(jsonl_file, 'r') as f:
                async for line in f:
                    if line.strip():
                        samples.append(json.loads(line))
        elif dataset.file_path and Path(dataset.file_path).exists():
            # Fallback to original file
            async with aiofiles.open(dataset.file_path, 'r') as f:
                if dataset.file_path.endswith('.jsonl'):
                    async for line in f:
                        if line.strip():
                            samples.append(json.loads(line))
                else:
                    content = await f.read()
                    data = json.loads(content)
                    if isinstance(data, list):
                        samples = data
                    else:
                        samples = [data]
        
        if not samples:
            raise ValueError("No samples found in dataset")
        
        # Update progress
        await redis_client.setex(
            f"quality_job:{job_id}",
            3600,
            json.dumps({"status": "processing", "progress": 30})
        )
        
        # Evaluate quality
        quality_metrics = await data_quality_service.evaluate_dataset_quality(samples)
        
        # Update progress
        await redis_client.setex(
            f"quality_job:{job_id}",
            3600,
            json.dumps({"status": "processing", "progress": 80})
        )
        
        # Identify issues
        quality_issues = await data_quality_service.identify_quality_issues(samples, quality_metrics)
        
        # Update dataset with quality metrics
        dataset.quality_metrics = quality_metrics.model_dump()
        await db.commit()
        
        # Mark job as completed
        await redis_client.setex(
            f"quality_job:{job_id}",
            3600,
            json.dumps({
                "status": "completed",
                "progress": 100,
                "metrics": quality_metrics.model_dump(),
                "issues": quality_issues
            })
        )
        
    except Exception as e:
        # Mark job as failed
        await redis_client.setex(
            f"quality_job:{job_id}",
            3600,
            json.dumps({
                "status": "failed",
                "progress": 0,
                "error": str(e)
            })
        )
        raise


@router.post("/{dataset_id}/evaluate")
async def evaluate_dataset_quality(
    dataset_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """Start quality evaluation for a dataset."""
    # Get dataset
    dataset = await dataset_crud.get(db, id=dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Check permissions (TODO: implement proper permission checking)
    
    # Generate job ID
    job_id = str(UUID())
    
    # Start background task
    background_tasks.add_task(
        evaluate_quality_task,
        dataset_id=dataset_id,
        job_id=job_id,
        db=db
    )
    
    return {
        "job_id": job_id,
        "status": "started",
        "message": "Quality evaluation started"
    }


@router.get("/{dataset_id}/quality")
async def get_dataset_quality(
    dataset_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """Get quality metrics for a dataset."""
    # Get dataset
    dataset = await dataset_crud.get(db, id=dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    if not dataset.quality_metrics:
        raise HTTPException(
            status_code=404,
            detail="Quality metrics not available. Please run quality evaluation first."
        )
    
    return dataset.quality_metrics


@router.get("/job/{job_id}")
async def get_quality_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user)
) -> Any:
    """Get quality evaluation job status."""
    # Get job data from Redis
    job_data = await redis_client.get(f"quality_job:{job_id}")
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return json.loads(job_data)


@router.post("/{dataset_id}/evaluate-sample")
async def evaluate_sample_quality(
    dataset_id: UUID,
    sample: DataSampleBase,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """Evaluate quality of a single data sample."""
    # Get dataset to verify it exists
    dataset = await dataset_crud.get(db, id=dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Evaluate sample
    metrics = await data_quality_service.evaluate_sample_quality(sample.model_dump())
    
    return {
        "metrics": metrics,
        "overall_quality": metrics.get("quality", 0)
    }


@router.get("/{dataset_id}/issues")
async def get_quality_issues(
    dataset_id: UUID,
    severity: Optional[str] = None,
    issue_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """Get quality issues for a dataset."""
    # Get dataset
    dataset = await dataset_crud.get(db, id=dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    if not dataset.quality_metrics:
        raise HTTPException(
            status_code=404,
            detail="Quality analysis not available. Please run quality evaluation first."
        )
    
    # Load samples to identify issues
    samples = []
    processed_dir = Path(settings.DATA_DIR) / "processed" / str(dataset_id)
    jsonl_file = processed_dir / "processed.jsonl"
    
    if jsonl_file.exists():
        async with aiofiles.open(jsonl_file, 'r') as f:
            async for line in f:
                if line.strip():
                    samples.append(json.loads(line))
    
    # Get quality issues
    quality_metrics = QualityMetrics(**dataset.quality_metrics)
    issues = await data_quality_service.identify_quality_issues(samples, quality_metrics)
    
    # Filter by severity and type if requested
    if severity:
        issues = [i for i in issues if i.get("severity") == severity]
    if issue_type:
        issues = [i for i in issues if i.get("type") == issue_type]
    
    return {
        "dataset_id": str(dataset_id),
        "total_issues": len(issues),
        "issues": issues
    }


@router.get("/{dataset_id}/samples/low-quality")
async def get_low_quality_samples(
    dataset_id: UUID,
    limit: int = 10,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """Get samples with low quality scores."""
    # Get dataset
    dataset = await dataset_crud.get(db, id=dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Load and evaluate samples
    samples = []
    processed_dir = Path(settings.DATA_DIR) / "processed" / str(dataset_id)
    jsonl_file = processed_dir / "processed.jsonl"
    
    if jsonl_file.exists():
        async with aiofiles.open(jsonl_file, 'r') as f:
            async for line in f:
                if line.strip():
                    samples.append(json.loads(line))
    
    # Evaluate each sample and sort by quality
    evaluated_samples = []
    for idx, sample in enumerate(samples[:1000]):  # Limit for efficiency
        metrics = await data_quality_service.evaluate_sample_quality(sample)
        evaluated_samples.append({
            "index": idx,
            "sample": sample,
            "quality_score": metrics.get("quality", 0),
            "metrics": metrics
        })
    
    # Sort by quality score (ascending)
    evaluated_samples.sort(key=lambda x: x["quality_score"])
    
    # Apply pagination
    paginated = evaluated_samples[offset:offset + limit]
    
    return {
        "total": len(evaluated_samples),
        "limit": limit,
        "offset": offset,
        "samples": paginated
    }