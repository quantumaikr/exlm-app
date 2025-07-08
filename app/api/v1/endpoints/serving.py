"""
모델 서빙 API 엔드포인트
"""
from typing import List, Dict, Any, Optional
from uuid import UUID
import asyncio
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.api.deps import get_current_active_user, get_db
from app.models.user import User
from app.models.model import Model, ModelStatus
from app.models.project import Project
from app.schemas.serving import (
    ServingConfig,
    ServingStatus,
    GenerationRequest,
    GenerationResponse,
    ModelServingInfo
)
from app.core.permissions import check_project_permission, ProjectPermission
from app.services.model_serving import model_serving_service
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/models/{model_id}/serve", response_model=ModelServingInfo)
async def start_model_serving(
    model_id: UUID,
    config: ServingConfig,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> ModelServingInfo:
    """
    모델 서빙 시작
    
    Args:
        model_id: 모델 ID
        config: 서빙 설정
        
    Returns:
        서빙 정보
    """
    # 모델 존재 확인
    model = await db.get(Model, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    # 프로젝트 권한 확인
    project = await db.get(Project, model.project_id)
    await check_project_permission(
        db, project, current_user, ProjectPermission.WRITE
    )
    
    # 모델 상태 확인
    if model.status != ModelStatus.READY:
        raise HTTPException(
            status_code=400,
            detail="Model is not ready for serving"
        )
    
    # 서빙 시작
    try:
        serving_info = await model_serving_service.start_serving(
            model_id=str(model_id),
            model_path=model.model_path,
            config=config.dict(),
            user_id=str(current_user.id)
        )
        
        # 모델 상태 업데이트
        model.status = ModelStatus.SERVING
        model.serving_config = config.dict()
        model.serving_started_at = datetime.utcnow()
        await db.commit()
        
        return ModelServingInfo(**serving_info)
        
    except Exception as e:
        logger.error(f"Failed to start model serving: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start model serving: {str(e)}"
        )


@router.get("/models/{model_id}/serve", response_model=ModelServingInfo)
async def get_serving_status(
    model_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> ModelServingInfo:
    """
    모델 서빙 상태 조회
    
    Args:
        model_id: 모델 ID
        
    Returns:
        서빙 정보
    """
    # 모델 존재 확인
    model = await db.get(Model, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    # 프로젝트 권한 확인
    project = await db.get(Project, model.project_id)
    await check_project_permission(
        db, project, current_user, ProjectPermission.READ
    )
    
    # 서빙 상태 조회
    try:
        serving_info = await model_serving_service.get_serving_status(
            model_id=str(model_id)
        )
        
        if not serving_info:
            raise HTTPException(
                status_code=404,
                detail="Model is not currently serving"
            )
        
        return ModelServingInfo(**serving_info)
        
    except Exception as e:
        logger.error(f"Failed to get serving status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get serving status: {str(e)}"
        )


@router.delete("/models/{model_id}/serve")
async def stop_model_serving(
    model_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    모델 서빙 중지
    
    Args:
        model_id: 모델 ID
        
    Returns:
        중지 결과
    """
    # 모델 존재 확인
    model = await db.get(Model, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    # 프로젝트 권한 확인
    project = await db.get(Project, model.project_id)
    await check_project_permission(
        db, project, current_user, ProjectPermission.WRITE
    )
    
    # 서빙 중지
    try:
        await model_serving_service.stop_serving(model_id=str(model_id))
        
        # 모델 상태 업데이트
        model.status = ModelStatus.READY
        model.serving_config = None
        model.serving_started_at = None
        await db.commit()
        
        return {"message": "Model serving stopped successfully"}
        
    except Exception as e:
        logger.error(f"Failed to stop model serving: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop model serving: {str(e)}"
        )


@router.post("/models/{model_id}/generate", response_model=GenerationResponse)
async def generate_text(
    model_id: UUID,
    request: GenerationRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> GenerationResponse:
    """
    텍스트 생성
    
    Args:
        model_id: 모델 ID
        request: 생성 요청
        
    Returns:
        생성된 텍스트
    """
    # 모델 존재 확인
    model = await db.get(Model, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    # 프로젝트 권한 확인
    project = await db.get(Project, model.project_id)
    await check_project_permission(
        db, project, current_user, ProjectPermission.READ
    )
    
    # 모델이 서빙 중인지 확인
    if model.status != ModelStatus.SERVING:
        raise HTTPException(
            status_code=400,
            detail="Model is not currently serving"
        )
    
    # 텍스트 생성
    try:
        result = await model_serving_service.generate_text(
            model_id=str(model_id),
            prompt=request.prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
            stop=request.stop
        )
        
        return GenerationResponse(**result)
        
    except Exception as e:
        logger.error(f"Failed to generate text: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate text: {str(e)}"
        )


@router.get("/serving/models", response_model=List[ModelServingInfo])
async def list_serving_models(
    project_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> List[ModelServingInfo]:
    """
    서빙 중인 모델 목록 조회
    
    Args:
        project_id: 프로젝트 ID (선택)
        
    Returns:
        서빙 중인 모델 목록
    """
    try:
        # 사용자가 접근 가능한 프로젝트 필터
        user_projects = []
        if project_id:
            project = await db.get(Project, project_id)
            if project and await check_project_permission(
                db, project, current_user, ProjectPermission.READ
            ):
                user_projects = [str(project_id)]
        else:
            # 사용자의 모든 프로젝트
            from sqlalchemy import select
            stmt = select(Project.id).where(
                Project.user_id == current_user.id
            )
            result = await db.execute(stmt)
            user_projects = [str(p[0]) for p in result]
        
        # 서빙 중인 모델 조회
        serving_models = await model_serving_service.list_serving_models(
            project_ids=user_projects
        )
        
        return [ModelServingInfo(**model) for model in serving_models]
        
    except Exception as e:
        logger.error(f"Failed to list serving models: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list serving models: {str(e)}"
        )


@router.get("/serving/metrics")
async def get_serving_metrics(
    model_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    서빙 메트릭 조회
    
    Args:
        model_id: 모델 ID (선택)
        
    Returns:
        서빙 메트릭
    """
    try:
        if model_id:
            # 특정 모델 메트릭
            model = await db.get(Model, model_id)
            if not model:
                raise HTTPException(status_code=404, detail="Model not found")
            
            project = await db.get(Project, model.project_id)
            await check_project_permission(
                db, project, current_user, ProjectPermission.READ
            )
            
            metrics = await model_serving_service.get_model_metrics(
                model_id=str(model_id)
            )
        else:
            # 전체 메트릭
            metrics = await model_serving_service.get_overall_metrics()
        
        return metrics
        
    except Exception as e:
        logger.error(f"Failed to get serving metrics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get serving metrics: {str(e)}"
        )


@router.post("/models/{model_id}/batch-generate")
async def batch_generate_text(
    model_id: UUID,
    requests: List[GenerationRequest],
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> List[GenerationResponse]:
    """
    배치 텍스트 생성
    
    Args:
        model_id: 모델 ID
        requests: 생성 요청 목록
        
    Returns:
        생성된 텍스트 목록
    """
    # 모델 존재 확인
    model = await db.get(Model, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    # 프로젝트 권한 확인
    project = await db.get(Project, model.project_id)
    await check_project_permission(
        db, project, current_user, ProjectPermission.READ
    )
    
    # 모델이 서빙 중인지 확인
    if model.status != ModelStatus.SERVING:
        raise HTTPException(
            status_code=400,
            detail="Model is not currently serving"
        )
    
    # 배치 텍스트 생성
    try:
        results = await model_serving_service.batch_generate_text(
            model_id=str(model_id),
            requests=[req.dict() for req in requests]
        )
        
        return [GenerationResponse(**result) for result in results]
        
    except Exception as e:
        logger.error(f"Failed to batch generate text: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to batch generate text: {str(e)}"
        ) 