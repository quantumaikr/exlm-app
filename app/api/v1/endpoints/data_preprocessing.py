"""Data preprocessing API endpoints."""
from typing import Any, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
import json
import os
import aiofiles
from pathlib import Path

from app.db.deps import get_db
from app.models.user import User
from app.api.deps import get_current_user
from app.schemas.dataset import (
    PreprocessingJobCreate,
    PreprocessingJobResponse,
    DatasetResponse,
    PreprocessingConfig,
    DatasetFormat
)
from app.services.data_preprocessing import data_preprocessing_service
from app.crud import dataset as dataset_crud
from app.core.config import settings
from app.db.redis import redis_client


router = APIRouter()


async def update_job_progress(job_id: str, progress: float, status: str, stats: Optional[dict] = None):
    """Update preprocessing job progress in Redis."""
    job_data = {
        "progress": progress,
        "status": status,
        "statistics": stats
    }
    await redis_client.setex(
        f"preprocessing_job:{job_id}",
        3600,  # 1 hour TTL
        json.dumps(job_data)
    )


async def preprocess_dataset_task(
    dataset_id: UUID,
    job_id: str,
    file_path: str,
    format: DatasetFormat,
    config: PreprocessingConfig,
    model_name: Optional[str],
    db: AsyncSession
):
    """Background task for dataset preprocessing."""
    try:
        # Update progress
        await update_job_progress(job_id, 10, "processing")
        
        # Run preprocessing
        processed_dataset, stats = await data_preprocessing_service.preprocess_dataset(
            file_path=file_path,
            format=format,
            config=config,
            model_name=model_name
        )
        
        # Update progress
        await update_job_progress(job_id, 50, "processing", stats)
        
        # Save processed dataset
        output_dir = Path(settings.DATA_DIR) / "processed" / str(dataset_id)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if hasattr(processed_dataset, "save_to_disk"):
            # HuggingFace dataset
            processed_dataset.save_to_disk(str(output_dir))
        else:
            # Save as JSONL
            output_file = output_dir / "processed.jsonl"
            async with aiofiles.open(output_file, 'w') as f:
                for item in processed_dataset:
                    await f.write(json.dumps(item) + "\n")
        
        # Update dataset in database
        dataset = await dataset_crud.get(db, id=dataset_id)
        if dataset:
            dataset.statistics = stats
            dataset.status = "ready"
            dataset.samples_count = stats["total_samples"] - stats["removed_samples"]
            await db.commit()
        
        # Update job as completed
        await update_job_progress(job_id, 100, "completed", stats)
        
    except Exception as e:
        # Update job as failed
        await update_job_progress(job_id, 0, "failed", {"error": str(e)})
        raise


@router.post("/preprocess", response_model=PreprocessingJobResponse)
async def create_preprocessing_job(
    job_data: PreprocessingJobCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """Create a new preprocessing job for a dataset."""
    # Get dataset
    dataset = await dataset_crud.get(db, id=job_data.dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Check permissions
    # TODO: Add proper permission checking
    
    # Generate job ID
    job_id = str(UUID())
    
    # Create initial job status
    await update_job_progress(job_id, 0, "pending")
    
    # Start background task
    background_tasks.add_task(
        preprocess_dataset_task,
        dataset_id=dataset.id,
        job_id=job_id,
        file_path=dataset.file_path,
        format=dataset.format or DatasetFormat.JSONL,
        config=job_data.config,
        model_name=None,  # TODO: Get from project settings
        db=db
    )
    
    return PreprocessingJobResponse(
        id=job_id,
        dataset_id=dataset.id,
        config=job_data.config,
        status="pending",
        progress=0,
        created_at=dataset.created_at,
        updated_at=dataset.updated_at
    )


@router.get("/preprocess/{job_id}", response_model=PreprocessingJobResponse)
async def get_preprocessing_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """Get preprocessing job status."""
    # Get job data from Redis
    job_data = await redis_client.get(f"preprocessing_job:{job_id}")
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_info = json.loads(job_data)
    
    return PreprocessingJobResponse(
        id=job_id,
        dataset_id=UUID("00000000-0000-0000-0000-000000000000"),  # TODO: Store in Redis
        config=PreprocessingConfig(),  # TODO: Store in Redis
        status=job_info["status"],
        progress=job_info["progress"],
        statistics=job_info.get("statistics"),
        created_at=dataset.created_at,  # TODO: Store in Redis
        updated_at=dataset.updated_at
    )


@router.post("/analyze-quality/{dataset_id}")
async def analyze_dataset_quality(
    dataset_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """Analyze quality metrics of a dataset."""
    # Get dataset
    dataset = await dataset_crud.get(db, id=dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Load processed dataset
    processed_dir = Path(settings.DATA_DIR) / "processed" / str(dataset_id)
    if not processed_dir.exists():
        raise HTTPException(
            status_code=400, 
            detail="Dataset not preprocessed. Please run preprocessing first."
        )
    
    # Load dataset (simplified for now)
    data = []
    jsonl_file = processed_dir / "processed.jsonl"
    if jsonl_file.exists():
        async with aiofiles.open(jsonl_file, 'r') as f:
            async for line in f:
                if line.strip():
                    data.append(json.loads(line))
    
    # Create a simple dataset object
    from datasets import Dataset
    hf_dataset = Dataset.from_list(data)
    
    # Analyze quality
    quality_report = await data_preprocessing_service.analyze_dataset_quality(hf_dataset)
    
    # Update dataset with quality metrics
    dataset.quality_metrics = quality_report
    await db.commit()
    
    return quality_report


@router.post("/upload-and-preprocess", response_model=DatasetResponse)
async def upload_and_preprocess_dataset(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    project_id: UUID = Form(...),
    format: DatasetFormat = Form(DatasetFormat.JSONL),
    preprocessing_config: Optional[str] = Form(None),  # JSON string
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """Upload a dataset file and optionally preprocess it."""
    # Parse preprocessing config
    config = None
    if preprocessing_config:
        try:
            config_dict = json.loads(preprocessing_config)
            config = PreprocessingConfig(**config_dict)
        except:
            raise HTTPException(
                status_code=400,
                detail="Invalid preprocessing configuration"
            )
    
    # Save uploaded file
    upload_dir = Path(settings.DATA_DIR) / "uploads" / str(project_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = upload_dir / file.filename
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    # Create dataset record
    dataset_data = {
        "name": name,
        "description": description,
        "project_id": project_id,
        "format": format,
        "file_path": str(file_path),
        "size": len(content),
        "status": "processing" if config else "ready",
        "type": "uploaded"
    }
    
    dataset = await dataset_crud.create(db, obj_in=dataset_data)
    
    # Start preprocessing if config provided
    if config:
        job_id = str(UUID())
        await update_job_progress(job_id, 0, "pending")
        
        background_tasks.add_task(
            preprocess_dataset_task,
            dataset_id=dataset.id,
            job_id=job_id,
            file_path=str(file_path),
            format=format,
            config=config,
            model_name=None,
            db=db
        )
    
    return DatasetResponse(
        id=dataset.id,
        project_id=dataset.project_id,
        name=dataset.name,
        description=dataset.description,
        type=dataset.type,
        format=dataset.format,
        status=dataset.status,
        size=dataset.size,
        file_path=dataset.file_path,
        created_at=dataset.created_at,
        updated_at=dataset.updated_at
    )