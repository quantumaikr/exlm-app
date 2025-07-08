"""
모델 평가 API 엔드포인트
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.schemas.user import UserResponse
from app.schemas.evaluation import (
    EvaluationCreate, EvaluationUpdate, EvaluationResponse,
    ComparisonCreate, ComparisonResponse
)
from app.services.model_evaluation import model_evaluation_service

router = APIRouter()


@router.post("/evaluations", response_model=EvaluationResponse)
async def create_evaluation(
    evaluation_data: EvaluationCreate,
    background_tasks: BackgroundTasks,
    current_user: UserResponse = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(deps.get_db)
):
    """모델 평가 생성"""
    try:
        evaluation = await model_evaluation_service.create_evaluation(
            db=db,
            model_id=evaluation_data.model_id,
            dataset_id=evaluation_data.dataset_id,
            metrics=evaluation_data.metrics,
            config=evaluation_data.config,
            user_id=current_user.id
        )
        
        return EvaluationResponse.from_orm(evaluation)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/evaluations/{evaluation_id}", response_model=EvaluationResponse)
async def get_evaluation(
    evaluation_id: UUID,
    current_user: UserResponse = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(deps.get_db)
):
    """평가 조회"""
    evaluation = await model_evaluation_service.get_evaluation(db, evaluation_id)
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    
    return EvaluationResponse.from_orm(evaluation)


@router.get("/evaluations", response_model=List[EvaluationResponse])
async def list_evaluations(
    model_id: Optional[UUID] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: UserResponse = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(deps.get_db)
):
    """평가 목록 조회"""
    evaluations = await model_evaluation_service.list_evaluations(
        db=db,
        model_id=model_id,
        status=status,
        limit=limit,
        offset=offset
    )
    
    return [EvaluationResponse.from_orm(e) for e in evaluations]


@router.put("/evaluations/{evaluation_id}/status")
async def update_evaluation_status(
    evaluation_id: UUID,
    update_data: EvaluationUpdate,
    current_user: User = Depends(deps.get_current_active_super_user),
    db: AsyncSession = Depends(deps.get_db)
):
    """평가 상태 업데이트 (관리자 전용)"""
    evaluation = await model_evaluation_service.update_evaluation_status(
        db=db,
        evaluation_id=evaluation_id,
        status=update_data.status,
        results=update_data.results,
        error_message=update_data.error_message
    )
    
    return EvaluationResponse.from_orm(evaluation)


@router.post("/comparisons", response_model=ComparisonResponse)
async def create_model_comparison(
    comparison_data: ComparisonCreate,
    current_user: UserResponse = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(deps.get_db)
):
    """모델 비교 평가 생성"""
    if len(comparison_data.model_ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 models required for comparison")
    
    try:
        comparison = await model_evaluation_service.compare_models(
            db=db,
            model_ids=comparison_data.model_ids,
            dataset_id=comparison_data.dataset_id,
            metrics=comparison_data.metrics,
            user_id=current_user.id
        )
        
        return ComparisonResponse(**comparison)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/comparisons/{comparison_id}", response_model=dict)
async def get_comparison_results(
    comparison_id: str,
    current_user: UserResponse = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(deps.get_db)
):
    """비교 결과 조회"""
    try:
        results = await model_evaluation_service.get_comparison_results(db, comparison_id)
        return results
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/evaluations/{evaluation_id}/export")
async def export_evaluation_report(
    evaluation_id: UUID,
    format: str = "json",
    current_user: UserResponse = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(deps.get_db)
):
    """평가 리포트 내보내기"""
    try:
        report_path = await model_evaluation_service.export_evaluation_report(
            db=db,
            evaluation_id=evaluation_id,
            format=format
        )
        
        return {"report_path": report_path}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))