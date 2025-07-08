"""
모델 평가 Celery 작업
"""
from typing import Dict, Any
from uuid import UUID
from celery import Task

from app.core.celery_app import celery_app
from app.services.model_evaluation import model_evaluation_service
from app.models.evaluation import EvaluationStatus
from app.core.database import async_session_maker
from loguru import logger


class EvaluationTask(Task):
    """평가 작업 기본 클래스"""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """작업 실패 시 처리"""
        evaluation_id = args[0] if args else None
        if evaluation_id:
            # 비동기 컨텍스트에서 동기 함수 호출
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def update_status():
                async with async_session_maker() as db:
                    await model_evaluation_service.update_evaluation_status(
                        db=db,
                        evaluation_id=UUID(evaluation_id),
                        status=EvaluationStatus.FAILED,
                        error_message=str(exc)
                    )
            
            loop.run_until_complete(update_status())
            loop.close()


@celery_app.task(base=EvaluationTask, bind=True, name="app.tasks.evaluation.run_model_evaluation")
def run_model_evaluation(self, evaluation_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """모델 평가 실행"""
    import asyncio
    
    logger.info(f"Starting evaluation task for {evaluation_id}")
    
    # 비동기 함수를 동기적으로 실행
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def _run_evaluation():
        async with async_session_maker() as db:
            # 상태를 RUNNING으로 업데이트
            await model_evaluation_service.update_evaluation_status(
                db=db,
                evaluation_id=UUID(evaluation_id),
                status=EvaluationStatus.RUNNING
            )
        
        # 평가 실행
        result = await model_evaluation_service.run_evaluation(
            evaluation_id=evaluation_id,
            config=config
        )
        
        # 결과에 따라 상태 업데이트
        async with async_session_maker() as db:
            if result["status"] == "completed":
                await model_evaluation_service.update_evaluation_status(
                    db=db,
                    evaluation_id=UUID(evaluation_id),
                    status=EvaluationStatus.COMPLETED,
                    results=result["results"]
                )
            else:
                await model_evaluation_service.update_evaluation_status(
                    db=db,
                    evaluation_id=UUID(evaluation_id),
                    status=EvaluationStatus.FAILED,
                    error_message=result.get("error", "Unknown error")
                )
        
        return result
    
    try:
        result = loop.run_until_complete(_run_evaluation())
        return result
    finally:
        loop.close()


@celery_app.task(name="app.tasks.evaluation.run_batch_evaluation")
def run_batch_evaluation(evaluation_ids: list[str], config: Dict[str, Any]) -> Dict[str, Any]:
    """배치 평가 실행"""
    results = {}
    
    for eval_id in evaluation_ids:
        try:
            result = run_model_evaluation.apply_async(
                args=[eval_id, config],
                queue="evaluation"
            )
            results[eval_id] = {"task_id": result.id, "status": "queued"}
        except Exception as e:
            results[eval_id] = {"error": str(e), "status": "failed"}
    
    return results


@celery_app.task(name="app.tasks.evaluation.cleanup_old_evaluations")
def cleanup_old_evaluations(days: int = 30) -> Dict[str, int]:
    """오래된 평가 정리"""
    import asyncio
    from datetime import datetime, timedelta
    from sqlalchemy import and_, or_
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def _cleanup():
        async with async_session_maker() as db:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # 완료되거나 실패한 오래된 평가 조회
            from app.models.evaluation import ModelEvaluation
            query = db.query(ModelEvaluation).filter(
                and_(
                    ModelEvaluation.created_at < cutoff_date,
                    or_(
                        ModelEvaluation.status == EvaluationStatus.COMPLETED,
                        ModelEvaluation.status == EvaluationStatus.FAILED,
                        ModelEvaluation.status == EvaluationStatus.CANCELLED
                    )
                )
            )
            
            evaluations = await db.execute(query)
            old_evaluations = evaluations.scalars().all()
            
            count = len(old_evaluations)
            
            # 평가 결과 파일 삭제
            for evaluation in old_evaluations:
                # 여기에 실제 파일 삭제 로직 추가
                pass
            
            # 데이터베이스 레코드 삭제
            for evaluation in old_evaluations:
                await db.delete(evaluation)
            
            await db.commit()
            
            return {"deleted_evaluations": count}
    
    try:
        result = loop.run_until_complete(_cleanup())
        return result
    finally:
        loop.close()