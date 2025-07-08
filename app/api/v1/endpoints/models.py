from typing import Any, Optional, List, Dict
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from uuid import UUID
from datetime import datetime
import asyncio

from app.api import deps
from app.core.database import get_db
from app.schemas.user import UserResponse
from app.models.model import Model, ModelStatus, ModelProvider
from app.models.project import Project, ProjectMember
from app.schemas.model import (
    ModelCreate,
    ModelUpdate,
    ModelResponse,
    ModelListResponse,
    HuggingFaceModelResponse,
    ModelImportRequest,
)
from app.services.huggingface import huggingface_service
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/", response_model=ModelListResponse)
async def get_models(
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(deps.get_current_active_user),
    project_id: Optional[UUID] = None,
    status: Optional[ModelStatus] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
) -> Any:
    """Get list of models"""
    # Build base query - join with projects to ensure user owns the project
    query = select(Model).join(Project).where(Project.user_id == current_user.id)
    
    if project_id:
        query = query.where(Model.project_id == project_id)
    
    if status:
        query = query.where(Model.status == status)
    
    if search:
        query = query.where(Model.name.ilike(f"%{search}%"))
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()
    
    # Apply pagination
    query = query.offset((page - 1) * limit).limit(limit)
    query = query.order_by(Model.created_at.desc())
    
    result = await db.execute(query)
    models = result.scalars().all()
    
    return ModelListResponse(
        items=models,
        total=total,
        page=page,
        pages=(total + limit - 1) // limit,
    )


@router.post("/", response_model=ModelResponse)
async def create_model(
    *,
    db: AsyncSession = Depends(get_db),
    model_in: ModelCreate,
    current_user: UserResponse = Depends(deps.get_current_active_user),
) -> Any:
    """Create new model"""
    # Verify user owns the project
    result = await db.execute(
        select(Project).where(
            Project.id == model_in.project_id,
            Project.user_id == current_user.id
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Create model
    model = Model(
        **model_in.dict(),
        status=ModelStatus.PENDING,
    )
    db.add(model)
    await db.commit()
    await db.refresh(model)
    return model


@router.get("/{model_id}", response_model=ModelResponse)
async def get_model(
    *,
    db: AsyncSession = Depends(get_db),
    model_id: UUID,
    current_user: UserResponse = Depends(deps.get_current_active_user),
) -> Any:
    """Get model by ID"""
    result = await db.execute(
        select(Model).join(Project).where(
            Model.id == model_id,
            Project.user_id == current_user.id
        )
    )
    model = result.scalar_one_or_none()
    
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    return model


@router.put("/{model_id}", response_model=ModelResponse)
async def update_model(
    *,
    db: AsyncSession = Depends(get_db),
    model_id: UUID,
    model_in: ModelUpdate,
    current_user: UserResponse = Depends(deps.get_current_active_user),
) -> Any:
    """Update model"""
    result = await db.execute(
        select(Model).join(Project).where(
            Model.id == model_id,
            Project.user_id == current_user.id
        )
    )
    model = result.scalar_one_or_none()
    
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    update_data = model_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(model, field, value)
    
    await db.commit()
    await db.refresh(model)
    return model


@router.delete("/{model_id}")
async def delete_model(
    *,
    db: AsyncSession = Depends(get_db),
    model_id: UUID,
    current_user: UserResponse = Depends(deps.get_current_active_user),
) -> Any:
    """Delete model"""
    result = await db.execute(
        select(Model).join(Project).where(
            Model.id == model_id,
            Project.user_id == current_user.id
        )
    )
    model = result.scalar_one_or_none()
    
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    # Check if model is being used
    if model.status == ModelStatus.TRAINING:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete model that is currently training"
        )
    
    await db.delete(model)
    await db.commit()
    
    return {"message": "Model deleted successfully"}


@router.get("/huggingface/search", response_model=List[HuggingFaceModelResponse])
async def search_huggingface_models(
    query: Optional[str] = None,
    task: Optional[str] = None,
    library: Optional[str] = None,
    language: Optional[str] = None,
    sort: str = Query("trending", regex="^(trending|downloads|likes|created)$"),
    limit: int = Query(20, ge=1, le=100),
    current_user: UserResponse = Depends(deps.get_current_active_user)
) -> List[HuggingFaceModelResponse]:
    """Search models on Hugging Face Hub"""
    
    async with huggingface_service as hf:
        models = await hf.search_models(
            query=query,
            task=task,
            library=library,
            language=language,
            sort=sort,
            limit=limit
        )
    
    return [HuggingFaceModelResponse(**model) for model in models]


@router.get("/huggingface/trending", response_model=List[HuggingFaceModelResponse])
async def get_trending_models(
    task: Optional[str] = None,
    limit: int = Query(10, ge=1, le=50),
    current_user: UserResponse = Depends(deps.get_current_active_user)
) -> List[HuggingFaceModelResponse]:
    """Get trending models from Hugging Face"""
    
    async with huggingface_service as hf:
        models = await hf.get_trending_models(task=task, limit=limit)
    
    return [HuggingFaceModelResponse(**model) for model in models]


@router.get("/huggingface/{model_id:path}", response_model=HuggingFaceModelResponse)
async def get_huggingface_model(
    model_id: str,
    current_user: UserResponse = Depends(deps.get_current_active_user)
) -> HuggingFaceModelResponse:
    """Get Hugging Face model details"""
    
    async with huggingface_service as hf:
        model = await hf.get_model_details(model_id)
    
    if not model:
        raise HTTPException(status_code=404, detail="Model not found on Hugging Face")
    
    return HuggingFaceModelResponse(**model)


@router.post("/import", response_model=ModelResponse)
async def import_huggingface_model(
    request: ModelImportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(deps.get_current_active_user)
) -> ModelResponse:
    """Import a model from Hugging Face to project"""
    
    # Check project access
    result = await db.execute(
        select(Project).where(
            Project.id == request.project_id,
            or_(
                Project.user_id == current_user.id,
                select(ProjectMember).where(
                    ProjectMember.project_id == request.project_id,
                    ProjectMember.user_id == current_user.id
                ).exists()
            )
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get model info from Hugging Face
    async with huggingface_service as hf:
        hf_model = await hf.get_model_details(request.huggingface_model_id)
    
    if not hf_model:
        raise HTTPException(status_code=404, detail="Model not found on Hugging Face")
    
    # Check if already imported
    result = await db.execute(
        select(Model).where(
            Model.project_id == request.project_id,
            Model.huggingface_model_id == request.huggingface_model_id
        )
    )
    existing_model = result.scalar_one_or_none()
    
    if existing_model:
        raise HTTPException(status_code=400, detail="Model already imported to this project")
    
    # Create model
    model = Model(
        name=hf_model["name"],
        display_name=hf_model["full_name"],
        description=hf_model["description"],
        provider=hf_model["provider"],
        huggingface_model_id=request.huggingface_model_id,
        project_id=request.project_id,
        status=ModelStatus.PENDING,
        config=request.config or {},
        metadata={
            "size": hf_model["size"],
            "parameters": hf_model["parameters"],
            "license": hf_model["license"],
            "tags": hf_model["tags"],
            "requirements": hf_model.get("requirements", {}),
            "performance_metrics": hf_model.get("performance_metrics", {}),
        }
    )
    
    db.add(model)
    await db.commit()
    await db.refresh(model)
    
    # Start download in background
    background_tasks.add_task(download_model, str(model.id), request.huggingface_model_id)
    
    return model


@router.post("/{model_id}/train")
async def start_training(
    *,
    db: AsyncSession = Depends(get_db),
    model_id: UUID,
    current_user: UserResponse = Depends(deps.get_current_active_user),
) -> Any:
    """Start model training"""
    result = await db.execute(
        select(Model).join(Project).where(
            Model.id == model_id,
            Project.user_id == current_user.id
        )
    )
    model = result.scalar_one_or_none()
    
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    if model.status != ModelStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail="Model is not in pending state"
        )
    
    # Start training task with Celery
    from app.tasks.model_training import train_model
    
    model.status = ModelStatus.TRAINING
    await db.commit()
    
    # Get model configuration
    config = model.config or {}
    
    # Start async training task
    task = train_model.delay(model_id=str(model_id), config=config)
    
    return {
        "message": "Training started",
        "model_id": model_id,
        "task_id": task.id
    }


async def download_model(model_id: str, huggingface_model_id: str):
    """Download model in background (implementation needed)"""
    try:
        logger.info(f"Starting download for model {huggingface_model_id}")
        
        # TODO: Implement actual model download logic
        # 1. Get file list from Hugging Face Hub
        # 2. Download each file
        # 3. Save to local storage
        # 4. Update progress
        
        # Simulation
        await asyncio.sleep(10)
        
        # Update model status
        async with AsyncSession(get_db.engine) as db:
            result = await db.execute(
                select(Model).where(Model.id == model_id)
            )
            model = result.scalar_one_or_none()
            if model:
                model.status = ModelStatus.READY
                model.model_metadata["download_completed_at"] = datetime.utcnow().isoformat()
                await db.commit()
                logger.info(f"Model {huggingface_model_id} download completed")
            
    except Exception as e:
        logger.error(f"Failed to download model {huggingface_model_id}: {e}")
        
        # Update error status
        async with AsyncSession(get_db.engine) as db:
            result = await db.execute(
                select(Model).where(Model.id == model_id)
            )
            model = result.scalar_one_or_none()
            if model:
                model.status = ModelStatus.ERROR
                model.model_metadata["error"] = str(e)
                await db.commit()