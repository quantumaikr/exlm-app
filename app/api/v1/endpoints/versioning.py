"""
모델 버전 관리 API 엔드포인트
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.schemas.user import UserResponse
from app.schemas.versioning import (
    VersionCreate, VersionResponse, VersionComparison,
    VersionExport
)
from app.services.model_versioning import model_versioning_service

router = APIRouter()


@router.post("/models/{model_id}/versions", response_model=VersionResponse)
async def create_model_version(
    model_id: UUID,
    version_data: VersionCreate,
    current_user: UserResponse = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(deps.get_db)
):
    """모델 버전 생성"""
    try:
        version = await model_versioning_service.create_model_version(
            db=db,
            model_id=model_id,
            version_tag=version_data.version,
            description=version_data.description,
            training_job_id=version_data.training_job_id,
            metrics=version_data.metrics,
            user_id=current_user.id
        )
        
        return VersionResponse.from_orm(version)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/models/{model_id}/versions", response_model=List[VersionResponse])
async def list_model_versions(
    model_id: UUID,
    include_metrics: bool = True,
    current_user: UserResponse = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(deps.get_db)
):
    """모델 버전 목록 조회"""
    versions = await model_versioning_service.list_model_versions(
        db=db,
        model_id=model_id,
        include_metrics=include_metrics
    )
    
    return [VersionResponse.from_orm(v) for v in versions]


@router.get("/models/{model_id}/versions/{version}", response_model=VersionResponse)
async def get_model_version(
    model_id: UUID,
    version: str,
    current_user: UserResponse = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(deps.get_db)
):
    """특정 버전 조회"""
    version_obj = await model_versioning_service.get_model_version(
        db=db,
        model_id=model_id,
        version=version
    )
    
    if not version_obj:
        raise HTTPException(status_code=404, detail="Version not found")
    
    return VersionResponse.from_orm(version_obj)


@router.post("/models/{model_id}/versions/compare", response_model=VersionComparison)
async def compare_versions(
    model_id: UUID,
    version1: str,
    version2: str,
    current_user: UserResponse = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(deps.get_db)
):
    """두 버전 비교"""
    try:
        comparison = await model_versioning_service.compare_versions(
            db=db,
            model_id=model_id,
            version1=version1,
            version2=version2
        )
        
        return VersionComparison(**comparison)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/models/{model_id}/versions/{version}/rollback")
async def rollback_to_version(
    model_id: UUID,
    version: str,
    current_user: UserResponse = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(deps.get_db)
):
    """특정 버전으로 롤백"""
    try:
        model = await model_versioning_service.rollback_to_version(
            db=db,
            model_id=model_id,
            version=version,
            user_id=current_user.id
        )
        
        return {
            "message": f"Successfully rolled back to version {version}",
            "model_id": str(model.id),
            "current_version": model.latest_version
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/models/{model_id}/versions/{version}")
async def delete_version(
    model_id: UUID,
    version: str,
    force: bool = False,
    current_user: User = Depends(deps.get_current_active_super_user),
    db: AsyncSession = Depends(deps.get_db)
):
    """버전 삭제 (관리자 전용)"""
    try:
        await model_versioning_service.delete_version(
            db=db,
            model_id=model_id,
            version=version,
            force=force
        )
        
        return {"message": f"Version {version} deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/models/{model_id}/versions/{version}/export")
async def export_version(
    model_id: UUID,
    version: str,
    export_data: VersionExport,
    current_user: UserResponse = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(deps.get_db)
):
    """버전 내보내기"""
    try:
        export_path = await model_versioning_service.export_version(
            db=db,
            model_id=model_id,
            version=version,
            export_format=export_data.format,
            output_path=export_data.output_path
        )
        
        return {
            "export_path": export_path,
            "format": export_data.format
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))