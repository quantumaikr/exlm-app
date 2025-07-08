from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID
import aiofiles
import os
from pathlib import Path

from app.api import deps
from app.core.database import get_db
from app.core.config import settings
from app.schemas.user import UserResponse
from app.models.dataset import Dataset, DatasetStatus, DatasetType
from app.models.project import Project
from app.schemas.dataset import (
    DatasetCreate,
    DatasetUpdate,
    DatasetResponse,
    DatasetListResponse,
    DataGenerationConfig,
)

router = APIRouter()


@router.get("/", response_model=DatasetListResponse)
async def get_datasets(
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(deps.get_current_active_user),
    project_id: Optional[UUID] = None,
    type: Optional[DatasetType] = None,
    status: Optional[DatasetStatus] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
) -> Any:
    """Get list of datasets"""
    # Build base query - join with projects to ensure user owns the project
    query = select(Dataset).join(Project).where(Project.user_id == current_user.id)
    
    if project_id:
        query = query.where(Dataset.project_id == project_id)
    
    if type:
        query = query.where(Dataset.type == type)
    
    if status:
        query = query.where(Dataset.status == status)
    
    if search:
        query = query.where(Dataset.name.ilike(f"%{search}%"))
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()
    
    # Apply pagination
    query = query.offset((page - 1) * limit).limit(limit)
    query = query.order_by(Dataset.created_at.desc())
    
    result = await db.execute(query)
    datasets = result.scalars().all()
    
    return DatasetListResponse(
        items=datasets,
        total=total,
        page=page,
        pages=(total + limit - 1) // limit,
    )


@router.post("/", response_model=DatasetResponse)
async def create_dataset(
    *,
    db: AsyncSession = Depends(get_db),
    dataset_in: DatasetCreate,
    current_user: UserResponse = Depends(deps.get_current_active_user),
) -> Any:
    """Create new dataset"""
    # Verify user owns the project
    result = await db.execute(
        select(Project).where(
            Project.id == dataset_in.project_id,
            Project.user_id == current_user.id
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Create dataset
    dataset = Dataset(
        **dataset_in.dict(),
        status=DatasetStatus.PENDING,
    )
    db.add(dataset)
    await db.commit()
    await db.refresh(dataset)
    
    # If type is GENERATED, trigger generation task
    if dataset.type == DatasetType.GENERATED and dataset.generation_config:
        from app.tasks.data_generation import generate_dataset
        
        # Start async generation task
        task = generate_dataset.delay(
            dataset_id=str(dataset.id),
            config=dataset.generation_config
        )
    
    return dataset


@router.post("/{dataset_id}/upload")
async def upload_dataset(
    *,
    db: AsyncSession = Depends(get_db),
    dataset_id: UUID,
    file: UploadFile = File(...),
    current_user: UserResponse = Depends(deps.get_current_active_user),
) -> Any:
    """Upload dataset file"""
    # Verify dataset exists and user has access
    result = await db.execute(
        select(Dataset).join(Project).where(
            Dataset.id == dataset_id,
            Project.user_id == current_user.id
        )
    )
    dataset = result.scalar_one_or_none()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    if dataset.type != DatasetType.UPLOADED:
        raise HTTPException(
            status_code=400,
            detail="Can only upload files for UPLOADED type datasets"
        )
    
    # Create upload directory if it doesn't exist
    upload_dir = Path(settings.UPLOAD_DIR) / "datasets" / str(dataset_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Save file
    file_path = upload_dir / file.filename
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    # Update dataset
    dataset.file_path = str(file_path)
    dataset.status = DatasetStatus.PROCESSING
    
    # Trigger processing task to analyze dataset
    from app.tasks.data_processing import process_uploaded_dataset
    
    task = process_uploaded_dataset.delay(
        dataset_id=str(dataset_id),
        file_path=str(file_path)
    )
    
    await db.commit()
    
    return {
        "message": "File uploaded successfully",
        "path": str(file_path),
        "task_id": task.id
    }


@router.post("/{dataset_id}/generate")
async def generate_dataset(
    *,
    db: AsyncSession = Depends(get_db),
    dataset_id: UUID,
    config: DataGenerationConfig,
    current_user: UserResponse = Depends(deps.get_current_active_user),
) -> Any:
    """Generate synthetic dataset"""
    # Verify dataset exists and user has access
    result = await db.execute(
        select(Dataset).join(Project).where(
            Dataset.id == dataset_id,
            Project.user_id == current_user.id
        )
    )
    dataset = result.scalar_one_or_none()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    if dataset.type != DatasetType.GENERATED:
        raise HTTPException(
            status_code=400,
            detail="Can only generate data for GENERATED type datasets"
        )
    
    if dataset.status != DatasetStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail="Dataset generation already started"
        )
    
    # Update generation config and status
    dataset.generation_config = config.dict()
    dataset.status = DatasetStatus.PROCESSING
    
    await db.commit()
    
    # Trigger Celery task for data generation
    from app.tasks.data_generation import generate_dataset as generate_dataset_task
    
    task = generate_dataset_task.delay(
        dataset_id=str(dataset_id),
        config=config.dict()
    )
    
    return {
        "message": "Dataset generation started",
        "dataset_id": dataset_id,
        "task_id": task.id
    }


@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(
    *,
    db: AsyncSession = Depends(get_db),
    dataset_id: UUID,
    current_user: UserResponse = Depends(deps.get_current_active_user),
) -> Any:
    """Get dataset by ID"""
    result = await db.execute(
        select(Dataset).join(Project).where(
            Dataset.id == dataset_id,
            Project.user_id == current_user.id
        )
    )
    dataset = result.scalar_one_or_none()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    return dataset


@router.put("/{dataset_id}", response_model=DatasetResponse)
async def update_dataset(
    *,
    db: AsyncSession = Depends(get_db),
    dataset_id: UUID,
    dataset_in: DatasetUpdate,
    current_user: UserResponse = Depends(deps.get_current_active_user),
) -> Any:
    """Update dataset"""
    result = await db.execute(
        select(Dataset).join(Project).where(
            Dataset.id == dataset_id,
            Project.user_id == current_user.id
        )
    )
    dataset = result.scalar_one_or_none()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    update_data = dataset_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(dataset, field, value)
    
    await db.commit()
    await db.refresh(dataset)
    return dataset


@router.delete("/{dataset_id}")
async def delete_dataset(
    *,
    db: AsyncSession = Depends(get_db),
    dataset_id: UUID,
    current_user: UserResponse = Depends(deps.get_current_active_user),
) -> Any:
    """Delete dataset"""
    result = await db.execute(
        select(Dataset).join(Project).where(
            Dataset.id == dataset_id,
            Project.user_id == current_user.id
        )
    )
    dataset = result.scalar_one_or_none()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Check if dataset is being used
    if dataset.status == DatasetStatus.PROCESSING:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete dataset that is currently processing"
        )
    
    # Delete associated files
    if dataset.file_path and os.path.exists(dataset.file_path):
        os.remove(dataset.file_path)
    
    await db.delete(dataset)
    await db.commit()
    
    return {"message": "Dataset deleted successfully"}