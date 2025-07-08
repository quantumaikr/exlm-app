"""
학습 관련 API 엔드포인트
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from app.api.deps import get_current_active_user, get_db
from app.models.user import User
from app.models.project import Project
from app.models.training import TrainingJob, TrainingStatus
from app.models.dataset import Dataset
from app.models.model import Model
from app.schemas.training import (
    TrainingJobCreate,
    TrainingJobResponse,
    TrainingJobUpdate,
    TrainingMethodInfo,
    TrainingMetrics,
    TrainingConfig as TrainingConfigSchema
)
from app.core.permissions import check_project_permission, ProjectPermission
from app.services.training_pipeline import training_pipeline_service
from app.tasks.training import run_training_job, validate_training_config

router = APIRouter()


@router.get("/methods", response_model=List[TrainingMethodInfo])
async def get_training_methods(
    current_user: User = Depends(get_current_active_user)
) -> List[TrainingMethodInfo]:
    """
    지원되는 학습 방법 목록 조회
    
    Returns:
        지원되는 학습 방법 목록
    """
    methods = await training_pipeline_service.get_supported_training_methods()
    return methods


@router.post("/validate-config", response_model=Dict[str, Any])
async def validate_config(
    config: TrainingConfigSchema,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    학습 설정 검증
    
    Args:
        config: 학습 설정
        
    Returns:
        검증 결과
    """
    # 프로젝트 권한 확인
    project = await db.get(Project, config.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    await check_project_permission(
        db, project, current_user, ProjectPermission.WRITE
    )
    
    # 데이터셋 존재 확인
    dataset = await db.get(Dataset, config.dataset_id)
    if not dataset or dataset.project_id != project.id:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # 모델 존재 확인 (선택적)
    if config.base_model_id:
        model = await db.get(Model, config.base_model_id)
        if not model or model.project_id != project.id:
            raise HTTPException(status_code=404, detail="Model not found")
    
    # 비동기 태스크로 검증 실행
    result = validate_training_config.apply_async(
        args=[config.dict()]
    )
    
    return result.get()


@router.post("/jobs", response_model=TrainingJobResponse)
async def create_training_job(
    job_data: TrainingJobCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> TrainingJobResponse:
    """
    학습 작업 생성
    
    Args:
        job_data: 학습 작업 생성 데이터
        
    Returns:
        생성된 학습 작업
    """
    # 프로젝트 권한 확인
    project = await db.get(Project, job_data.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    await check_project_permission(
        db, project, current_user, ProjectPermission.WRITE
    )
    
    # 데이터셋 확인
    dataset = await db.get(Dataset, job_data.dataset_id)
    if not dataset or dataset.project_id != project.id:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # 학습 작업 생성
    training_job = await training_pipeline_service.create_training_job(
        db=db,
        project_id=str(project.id),
        model_id=str(job_data.base_model_id) if job_data.base_model_id else None,
        dataset_id=str(dataset.id),
        training_config=job_data.config,
        user_id=str(current_user.id)
    )
    
    return TrainingJobResponse.from_orm(training_job)


@router.get("/jobs", response_model=List[TrainingJobResponse])
async def list_training_jobs(
    project_id: Optional[UUID] = Query(None),
    status: Optional[TrainingStatus] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> List[TrainingJobResponse]:
    """
    학습 작업 목록 조회
    
    Args:
        project_id: 프로젝트 ID (선택)
        status: 상태 필터 (선택)
        skip: 건너뛸 항목 수
        limit: 조회할 항목 수
        
    Returns:
        학습 작업 목록
    """
    query = select(TrainingJob)
    
    # 프로젝트 필터
    if project_id:
        project = await db.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        await check_project_permission(
            db, project, current_user, ProjectPermission.READ
        )
        query = query.where(TrainingJob.project_id == project_id)
    else:
        # 사용자가 접근 가능한 프로젝트의 작업만 조회
        user_project_stmt = select(Project.id).where(
            or_(
                Project.owner_id == current_user.id,
                Project.members.any(id=current_user.id)
            )
        )
        user_projects = await db.execute(user_project_stmt)
        project_ids = [p[0] for p in user_projects]
        query = query.where(TrainingJob.project_id.in_(project_ids))
    
    # 상태 필터
    if status:
        query = query.where(TrainingJob.status == status)
    
    # 정렬 및 페이징
    query = query.order_by(TrainingJob.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    jobs = result.scalars().all()
    
    return [TrainingJobResponse.from_orm(job) for job in jobs]


@router.get("/jobs/{job_id}", response_model=TrainingJobResponse)
async def get_training_job(
    job_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> TrainingJobResponse:
    """
    학습 작업 상세 조회
    
    Args:
        job_id: 학습 작업 ID
        
    Returns:
        학습 작업 상세 정보
    """
    job = await db.get(TrainingJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Training job not found")
    
    # 프로젝트 권한 확인
    project = await db.get(Project, job.project_id)
    await check_project_permission(
        db, project, current_user, ProjectPermission.READ
    )
    
    return TrainingJobResponse.from_orm(job)


@router.patch("/jobs/{job_id}", response_model=TrainingJobResponse)
async def update_training_job(
    job_id: UUID,
    update_data: TrainingJobUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> TrainingJobResponse:
    """
    학습 작업 업데이트 (취소 등)
    
    Args:
        job_id: 학습 작업 ID
        update_data: 업데이트 데이터
        
    Returns:
        업데이트된 학습 작업
    """
    job = await db.get(TrainingJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Training job not found")
    
    # 프로젝트 권한 확인
    project = await db.get(Project, job.project_id)
    await check_project_permission(
        db, project, current_user, ProjectPermission.WRITE
    )
    
    # 상태 업데이트
    if update_data.status:
        # 진행 중인 작업만 취소 가능
        if update_data.status == TrainingStatus.CANCELLED:
            if job.status not in [TrainingStatus.PENDING, TrainingStatus.RUNNING]:
                raise HTTPException(
                    status_code=400,
                    detail="Only pending or running jobs can be cancelled"
                )
            
            # Celery 태스크 취소
            if job.celery_task_id:
                from app.core.celery_app import celery_app
                celery_app.control.revoke(job.celery_task_id, terminate=True)
        
        job.status = update_data.status
        job.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(job)
    
    return TrainingJobResponse.from_orm(job)


@router.get("/jobs/{job_id}/metrics", response_model=TrainingMetrics)
async def get_training_metrics(
    job_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> TrainingMetrics:
    """
    학습 메트릭 조회
    
    Args:
        job_id: 학습 작업 ID
        
    Returns:
        학습 메트릭
    """
    job = await db.get(TrainingJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Training job not found")
    
    # 프로젝트 권한 확인
    project = await db.get(Project, job.project_id)
    await check_project_permission(
        db, project, current_user, ProjectPermission.READ
    )
    
    # 실시간 메트릭 조회
    metrics = await training_pipeline_service.get_training_metrics(str(job_id))
    
    return TrainingMetrics(**metrics)


@router.get("/jobs/{job_id}/logs", response_model=List[str])
async def get_training_logs(
    job_id: UUID,
    tail: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> List[str]:
    """
    학습 로그 조회
    
    Args:
        job_id: 학습 작업 ID
        tail: 마지막 n개 라인
        
    Returns:
        학습 로그
    """
    job = await db.get(TrainingJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Training job not found")
    
    # 프로젝트 권한 확인
    project = await db.get(Project, job.project_id)
    await check_project_permission(
        db, project, current_user, ProjectPermission.READ
    )
    
    # TODO: 실제 로그 파일에서 읽기
    # 임시로 빈 리스트 반환
    return []


@router.post("/jobs/{job_id}/download-model", response_model=Dict[str, str])
async def download_trained_model(
    job_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    학습된 모델 다운로드 URL 생성
    
    Args:
        job_id: 학습 작업 ID
        
    Returns:
        다운로드 URL
    """
    job = await db.get(TrainingJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Training job not found")
    
    if job.status != TrainingStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail="Training job is not completed yet"
        )
    
    if not job.output_path:
        raise HTTPException(
            status_code=404,
            detail="No model output found for this job"
        )
    
    # 프로젝트 권한 확인
    project = await db.get(Project, job.project_id)
    await check_project_permission(
        db, project, current_user, ProjectPermission.READ
    )
    
    # TODO: 실제 다운로드 URL 생성 (S3 presigned URL 등)
    download_url = f"/api/v1/training/download/{job_id}"
    
    return {"download_url": download_url}