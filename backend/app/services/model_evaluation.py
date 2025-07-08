"""
모델 평가 서비스
"""
import json
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.celery_app import celery_app
from app.core.evaluation.evaluator import (
    ModelEvaluator, EvaluationConfig, EvaluationMetric, EvaluationResult
)
from app.models.model import Model
from app.models.evaluation import ModelEvaluation, EvaluationStatus
from app.core.redis import get_redis
from datasets import load_dataset, Dataset


class ModelEvaluationService:
    """모델 평가 서비스"""
    
    def __init__(self):
        self.evaluation_cache = {}
    
    async def create_evaluation(
        self,
        db: AsyncSession,
        model_id: UUID,
        dataset_id: Optional[UUID] = None,
        metrics: List[str] = None,
        config: Optional[Dict[str, Any]] = None,
        user_id: UUID = None
    ) -> ModelEvaluation:
        """평가 작업 생성"""
        # 모델 조회
        model = await db.get(Model, model_id)
        if not model:
            raise ValueError(f"Model {model_id} not found")
        
        # 기본 메트릭 설정
        if not metrics:
            metrics = ["perplexity", "bleu", "rouge"]
        
        # 평가 설정 생성
        eval_config = {
            "model_path": model.path,
            "metrics": metrics,
            "batch_size": config.get("batch_size", 8) if config else 8,
            "max_samples": config.get("max_samples") if config else None,
            "generation_config": config.get("generation_config") if config else None
        }
        
        if dataset_id:
            eval_config["dataset_id"] = str(dataset_id)
        
        # 평가 레코드 생성
        evaluation = ModelEvaluation(
            id=uuid4(),
            model_id=model_id,
            dataset_id=dataset_id,
            metrics=metrics,
            config=eval_config,
            status=EvaluationStatus.PENDING,
            created_by=user_id,
            created_at=datetime.utcnow()
        )
        
        db.add(evaluation)
        await db.commit()
        await db.refresh(evaluation)
        
        # Celery 작업 생성
        task = celery_app.send_task(
            "app.tasks.evaluation.run_model_evaluation",
            args=[str(evaluation.id), eval_config],
            queue="evaluation"
        )
        
        evaluation.celery_task_id = task.id
        await db.commit()
        
        logger.info(f"Created evaluation {evaluation.id} for model {model_id}")
        return evaluation
    
    async def get_evaluation(
        self,
        db: AsyncSession,
        evaluation_id: UUID
    ) -> Optional[ModelEvaluation]:
        """평가 조회"""
        return await db.get(ModelEvaluation, evaluation_id)
    
    async def list_evaluations(
        self,
        db: AsyncSession,
        model_id: Optional[UUID] = None,
        status: Optional[EvaluationStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ModelEvaluation]:
        """평가 목록 조회"""
        query = select(ModelEvaluation)
        
        if model_id:
            query = query.where(ModelEvaluation.model_id == model_id)
        
        if status:
            query = query.where(ModelEvaluation.status == status)
        
        query = query.order_by(ModelEvaluation.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def update_evaluation_status(
        self,
        db: AsyncSession,
        evaluation_id: UUID,
        status: EvaluationStatus,
        results: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> ModelEvaluation:
        """평가 상태 업데이트"""
        evaluation = await db.get(ModelEvaluation, evaluation_id)
        if not evaluation:
            raise ValueError(f"Evaluation {evaluation_id} not found")
        
        evaluation.status = status
        
        if status == EvaluationStatus.RUNNING:
            evaluation.started_at = datetime.utcnow()
        elif status == EvaluationStatus.COMPLETED:
            evaluation.completed_at = datetime.utcnow()
            if results:
                evaluation.results = results
        elif status == EvaluationStatus.FAILED:
            evaluation.failed_at = datetime.utcnow()
            evaluation.error_message = error_message
        
        evaluation.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(evaluation)
        
        # Redis 캐시 업데이트
        await self._update_cache(evaluation)
        
        return evaluation
    
    async def run_evaluation(
        self,
        evaluation_id: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """평가 실행 (Celery 작업)"""
        try:
            # 평가 설정 생성
            eval_config = EvaluationConfig(
                model_path=config["model_path"],
                metrics=[EvaluationMetric(m) for m in config["metrics"]],
                batch_size=config.get("batch_size", 8),
                max_samples=config.get("max_samples"),
                generation_config=config.get("generation_config")
            )
            
            # 데이터셋 로드
            dataset = None
            if "dataset_id" in config:
                dataset_path = Path(settings.UPLOAD_DIR) / "datasets" / config["dataset_id"]
                if dataset_path.exists():
                    # JSONL 파일 로드
                    data_file = dataset_path / "data.jsonl"
                    if data_file.exists():
                        dataset = load_dataset("json", data_files=str(data_file))["train"]
            
            # 평가 실행
            evaluator = ModelEvaluator(eval_config)
            result = evaluator.evaluate(dataset)
            
            # 벤치마크 실행 (선택적)
            benchmark_results = {}
            if config.get("run_benchmarks", False):
                for benchmark in ["mmlu", "human_eval", "truthfulqa"]:
                    try:
                        benchmark_results[benchmark] = evaluator.benchmark_model(benchmark)
                    except Exception as e:
                        logger.error(f"Benchmark {benchmark} failed: {e}")
            
            # 결과 정리
            evaluation_results = {
                "metrics": result.metrics,
                "generation_samples": result.generation_samples[:10] if result.generation_samples else [],
                "error_analysis": result.error_analysis,
                "benchmark_results": benchmark_results,
                "metadata": {
                    "evaluation_id": evaluation_id,
                    "completed_at": datetime.utcnow().isoformat(),
                    "model_path": config["model_path"],
                    "dataset_name": result.dataset_name
                }
            }
            
            return {
                "status": "completed",
                "results": evaluation_results
            }
            
        except Exception as e:
            logger.error(f"Evaluation failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    async def compare_models(
        self,
        db: AsyncSession,
        model_ids: List[UUID],
        dataset_id: UUID,
        metrics: List[str],
        user_id: UUID
    ) -> Dict[str, Any]:
        """모델 비교 평가"""
        comparison_id = str(uuid4())
        comparison_results = {
            "comparison_id": comparison_id,
            "model_ids": [str(mid) for mid in model_ids],
            "dataset_id": str(dataset_id),
            "metrics": metrics,
            "evaluations": {},
            "created_at": datetime.utcnow().isoformat()
        }
        
        # 각 모델에 대해 평가 생성
        for model_id in model_ids:
            evaluation = await self.create_evaluation(
                db=db,
                model_id=model_id,
                dataset_id=dataset_id,
                metrics=metrics,
                user_id=user_id
            )
            comparison_results["evaluations"][str(model_id)] = str(evaluation.id)
        
        # Redis에 비교 정보 저장
        redis = await get_redis()
        await redis.setex(
            f"model_comparison:{comparison_id}",
            86400,  # 24시간 TTL
            json.dumps(comparison_results)
        )
        
        return comparison_results
    
    async def get_comparison_results(
        self,
        db: AsyncSession,
        comparison_id: str
    ) -> Dict[str, Any]:
        """비교 결과 조회"""
        redis = await get_redis()
        comparison_data = await redis.get(f"model_comparison:{comparison_id}")
        
        if not comparison_data:
            raise ValueError(f"Comparison {comparison_id} not found")
        
        comparison = json.loads(comparison_data)
        
        # 각 평가 결과 조회
        results = {}
        all_completed = True
        
        for model_id, eval_id in comparison["evaluations"].items():
            evaluation = await self.get_evaluation(db, UUID(eval_id))
            if evaluation:
                results[model_id] = {
                    "status": evaluation.status.value,
                    "results": evaluation.results if evaluation.results else None
                }
                if evaluation.status != EvaluationStatus.COMPLETED:
                    all_completed = False
        
        # 비교 분석
        analysis = {}
        if all_completed:
            analysis = self._analyze_comparison(results)
        
        return {
            "comparison_id": comparison_id,
            "model_ids": comparison["model_ids"],
            "dataset_id": comparison["dataset_id"],
            "metrics": comparison["metrics"],
            "results": results,
            "analysis": analysis,
            "all_completed": all_completed
        }
    
    def _analyze_comparison(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """모델 비교 분석"""
        analysis = {
            "best_models": {},
            "metric_rankings": {},
            "improvements": {}
        }
        
        # 각 메트릭별 최고 모델 찾기
        all_metrics = set()
        for model_results in results.values():
            if model_results.get("results") and model_results["results"].get("metrics"):
                all_metrics.update(model_results["results"]["metrics"].keys())
        
        for metric in all_metrics:
            scores = []
            for model_id, model_results in results.items():
                if model_results.get("results") and model_results["results"].get("metrics"):
                    score = model_results["results"]["metrics"].get(metric)
                    if score is not None:
                        scores.append((model_id, score))
            
            if scores:
                # 메트릭에 따라 정렬 방향 결정
                reverse = metric not in ["perplexity", "loss"]  # 낮을수록 좋은 메트릭
                sorted_scores = sorted(scores, key=lambda x: x[1], reverse=reverse)
                
                analysis["metric_rankings"][metric] = [
                    {"model_id": mid, "score": score} for mid, score in sorted_scores
                ]
                analysis["best_models"][metric] = sorted_scores[0][0]
                
                # 개선율 계산
                if len(sorted_scores) > 1:
                    best_score = sorted_scores[0][1]
                    worst_score = sorted_scores[-1][1]
                    if worst_score != 0:
                        improvement = abs((best_score - worst_score) / worst_score) * 100
                        analysis["improvements"][metric] = f"{improvement:.1f}%"
        
        return analysis
    
    async def _update_cache(self, evaluation: ModelEvaluation):
        """Redis 캐시 업데이트"""
        redis = await get_redis()
        cache_key = f"evaluation:{evaluation.id}"
        
        cache_data = {
            "id": str(evaluation.id),
            "model_id": str(evaluation.model_id),
            "status": evaluation.status.value,
            "metrics": evaluation.metrics,
            "results": evaluation.results,
            "created_at": evaluation.created_at.isoformat() if evaluation.created_at else None,
            "completed_at": evaluation.completed_at.isoformat() if evaluation.completed_at else None
        }
        
        await redis.setex(
            cache_key,
            3600,  # 1시간 TTL
            json.dumps(cache_data)
        )
    
    async def export_evaluation_report(
        self,
        db: AsyncSession,
        evaluation_id: UUID,
        format: str = "json"
    ) -> str:
        """평가 리포트 내보내기"""
        evaluation = await self.get_evaluation(db, evaluation_id)
        if not evaluation:
            raise ValueError(f"Evaluation {evaluation_id} not found")
        
        # 모델 정보 조회
        model = await db.get(Model, evaluation.model_id)
        
        report = {
            "evaluation_id": str(evaluation.id),
            "model_info": {
                "id": str(model.id),
                "name": model.name,
                "base_model": model.base_model,
                "training_method": model.training_method
            },
            "evaluation_config": evaluation.config,
            "metrics_evaluated": evaluation.metrics,
            "results": evaluation.results,
            "status": evaluation.status.value,
            "timestamps": {
                "created_at": evaluation.created_at.isoformat() if evaluation.created_at else None,
                "started_at": evaluation.started_at.isoformat() if evaluation.started_at else None,
                "completed_at": evaluation.completed_at.isoformat() if evaluation.completed_at else None
            }
        }
        
        # 리포트 저장
        output_dir = Path(settings.MODEL_STORAGE_PATH) / "evaluation_reports"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if format == "json":
            output_file = output_dir / f"evaluation_report_{evaluation_id}.json"
            with open(output_file, "w") as f:
                json.dump(report, f, indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        logger.info(f"Exported evaluation report to {output_file}")
        return str(output_file)


# 싱글톤 인스턴스
model_evaluation_service = ModelEvaluationService()