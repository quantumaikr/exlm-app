"""
학습 모니터링 서비스
"""
import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
import aiofiles

from loguru import logger
import wandb
import mlflow
from mlflow.tracking import MlflowClient

from app.core.config import settings
from app.core.redis import get_redis
from app.core.websocket import manager as ws_manager


class TrainingMonitorService:
    """학습 모니터링 서비스"""
    
    def __init__(self):
        self.redis_key_prefix = "training_monitor:"
        self.metric_history_limit = 1000
        self.mlflow_client = None
        self._init_mlflow()
    
    def _init_mlflow(self):
        """MLflow 초기화"""
        try:
            mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
            self.mlflow_client = MlflowClient()
        except Exception as e:
            logger.warning(f"Failed to initialize MLflow: {e}")
    
    async def start_monitoring(
        self,
        job_id: str,
        config: Dict[str, Any],
        use_wandb: bool = False,
        use_mlflow: bool = True
    ) -> Dict[str, Any]:
        """모니터링 시작"""
        monitoring_info = {
            "job_id": job_id,
            "start_time": datetime.utcnow().isoformat(),
            "config": config,
            "use_wandb": use_wandb,
            "use_mlflow": use_mlflow,
            "wandb_run_id": None,
            "mlflow_run_id": None
        }
        
        # W&B 초기화
        if use_wandb:
            try:
                wandb_run = wandb.init(
                    project=settings.WANDB_PROJECT or "exlm-training",
                    name=f"job_{job_id}",
                    config=config,
                    tags=[config.get("model_name", "unknown"), config.get("training_type", "unknown")]
                )
                monitoring_info["wandb_run_id"] = wandb_run.id
            except Exception as e:
                logger.error(f"Failed to initialize W&B: {e}")
        
        # MLflow 실행 시작
        if use_mlflow and self.mlflow_client:
            try:
                experiment_name = settings.MLFLOW_EXPERIMENT or "exlm-training"
                experiment = mlflow.set_experiment(experiment_name)
                
                run = mlflow.start_run(
                    run_name=f"job_{job_id}",
                    tags={
                        "model_name": config.get("model_name", "unknown"),
                        "training_type": config.get("training_type", "unknown"),
                        "job_id": job_id
                    }
                )
                monitoring_info["mlflow_run_id"] = run.info.run_id
                
                # 하이퍼파라미터 로깅
                mlflow.log_params(self._flatten_dict(config))
            except Exception as e:
                logger.error(f"Failed to start MLflow run: {e}")
        
        # Redis에 모니터링 정보 저장
        redis = await get_redis()
        await redis.setex(
            f"{self.redis_key_prefix}{job_id}:info",
            86400,  # 24시간 TTL
            json.dumps(monitoring_info)
        )
        
        return monitoring_info
    
    async def log_metrics(
        self,
        job_id: str,
        metrics: Dict[str, Any],
        step: Optional[int] = None
    ) -> None:
        """메트릭 로깅"""
        timestamp = datetime.utcnow().isoformat()
        
        # Redis에 저장
        redis = await get_redis()
        metric_entry = {
            "timestamp": timestamp,
            "step": step,
            "metrics": metrics
        }
        
        # 메트릭 히스토리에 추가
        await redis.lpush(
            f"{self.redis_key_prefix}{job_id}:metrics",
            json.dumps(metric_entry)
        )
        
        # 히스토리 크기 제한
        await redis.ltrim(
            f"{self.redis_key_prefix}{job_id}:metrics",
            0,
            self.metric_history_limit - 1
        )
        
        # 최신 메트릭 업데이트
        await redis.setex(
            f"{self.redis_key_prefix}{job_id}:latest_metrics",
            86400,
            json.dumps(metrics)
        )
        
        # 모니터링 정보 가져오기
        info_str = await redis.get(f"{self.redis_key_prefix}{job_id}:info")
        if info_str:
            monitoring_info = json.loads(info_str)
            
            # W&B 로깅
            if monitoring_info.get("use_wandb") and monitoring_info.get("wandb_run_id"):
                try:
                    wandb.log(metrics, step=step)
                except Exception as e:
                    logger.error(f"Failed to log to W&B: {e}")
            
            # MLflow 로깅
            if monitoring_info.get("use_mlflow") and monitoring_info.get("mlflow_run_id"):
                try:
                    for key, value in metrics.items():
                        if isinstance(value, (int, float)):
                            mlflow.log_metric(key, value, step=step)
                except Exception as e:
                    logger.error(f"Failed to log to MLflow: {e}")
        
        # WebSocket으로 실시간 전송
        await ws_manager.broadcast({
            "type": "training_metrics",
            "data": {
                "job_id": job_id,
                "timestamp": timestamp,
                "step": step,
                "metrics": metrics
            }
        })
    
    async def log_artifact(
        self,
        job_id: str,
        artifact_path: str,
        artifact_type: str = "model",
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """아티팩트 로깅"""
        artifact_info = {
            "path": artifact_path,
            "type": artifact_type,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Redis에 아티팩트 정보 저장
        redis = await get_redis()
        await redis.lpush(
            f"{self.redis_key_prefix}{job_id}:artifacts",
            json.dumps(artifact_info)
        )
        
        # 모니터링 정보 가져오기
        info_str = await redis.get(f"{self.redis_key_prefix}{job_id}:info")
        if info_str:
            monitoring_info = json.loads(info_str)
            
            # W&B 아티팩트 로깅
            if monitoring_info.get("use_wandb"):
                try:
                    artifact = wandb.Artifact(
                        f"{job_id}_{artifact_type}",
                        type=artifact_type,
                        metadata=metadata
                    )
                    artifact.add_file(artifact_path)
                    wandb.log_artifact(artifact)
                except Exception as e:
                    logger.error(f"Failed to log artifact to W&B: {e}")
            
            # MLflow 아티팩트 로깅
            if monitoring_info.get("use_mlflow") and monitoring_info.get("mlflow_run_id"):
                try:
                    mlflow.log_artifact(artifact_path)
                    if metadata:
                        mlflow.log_dict(metadata, f"{artifact_type}_metadata.json")
                except Exception as e:
                    logger.error(f"Failed to log artifact to MLflow: {e}")
    
    async def get_metrics_history(
        self,
        job_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """메트릭 히스토리 조회"""
        redis = await get_redis()
        
        # Redis에서 메트릭 히스토리 가져오기
        metrics_data = await redis.lrange(
            f"{self.redis_key_prefix}{job_id}:metrics",
            0,
            limit - 1
        )
        
        metrics_history = []
        for metric_str in metrics_data:
            try:
                metrics_history.append(json.loads(metric_str))
            except json.JSONDecodeError:
                continue
        
        return metrics_history
    
    async def get_latest_metrics(
        self,
        job_id: str
    ) -> Optional[Dict[str, Any]]:
        """최신 메트릭 조회"""
        redis = await get_redis()
        metrics_str = await redis.get(f"{self.redis_key_prefix}{job_id}:latest_metrics")
        
        if metrics_str:
            return json.loads(metrics_str)
        return None
    
    async def complete_monitoring(
        self,
        job_id: str,
        final_metrics: Optional[Dict[str, Any]] = None,
        status: str = "completed"
    ) -> None:
        """모니터링 완료"""
        redis = await get_redis()
        
        # 모니터링 정보 가져오기
        info_str = await redis.get(f"{self.redis_key_prefix}{job_id}:info")
        if not info_str:
            return
        
        monitoring_info = json.loads(info_str)
        
        # 완료 정보 업데이트
        monitoring_info.update({
            "end_time": datetime.utcnow().isoformat(),
            "status": status,
            "final_metrics": final_metrics
        })
        
        # Redis 업데이트
        await redis.setex(
            f"{self.redis_key_prefix}{job_id}:info",
            86400 * 7,  # 7일간 보관
            json.dumps(monitoring_info)
        )
        
        # W&B 종료
        if monitoring_info.get("use_wandb"):
            try:
                if final_metrics:
                    wandb.summary.update(final_metrics)
                wandb.finish()
            except Exception as e:
                logger.error(f"Failed to finish W&B run: {e}")
        
        # MLflow 종료
        if monitoring_info.get("use_mlflow") and monitoring_info.get("mlflow_run_id"):
            try:
                if final_metrics:
                    for key, value in final_metrics.items():
                        if isinstance(value, (int, float)):
                            mlflow.log_metric(f"final_{key}", value)
                
                mlflow.end_run(status=status.upper())
            except Exception as e:
                logger.error(f"Failed to end MLflow run: {e}")
    
    async def export_training_report(
        self,
        job_id: str,
        output_path: str
    ) -> str:
        """학습 리포트 내보내기"""
        redis = await get_redis()
        
        # 모니터링 정보 가져오기
        info_str = await redis.get(f"{self.redis_key_prefix}{job_id}:info")
        if not info_str:
            raise ValueError(f"No monitoring info found for job {job_id}")
        
        monitoring_info = json.loads(info_str)
        
        # 메트릭 히스토리 가져오기
        metrics_history = await self.get_metrics_history(job_id, limit=self.metric_history_limit)
        
        # 아티팩트 정보 가져오기
        artifacts_data = await redis.lrange(
            f"{self.redis_key_prefix}{job_id}:artifacts",
            0,
            -1
        )
        artifacts = []
        for artifact_str in artifacts_data:
            try:
                artifacts.append(json.loads(artifact_str))
            except json.JSONDecodeError:
                continue
        
        # 리포트 생성
        report = {
            "job_id": job_id,
            "monitoring_info": monitoring_info,
            "metrics_history": metrics_history,
            "artifacts": artifacts,
            "report_generated_at": datetime.utcnow().isoformat()
        }
        
        # 파일로 저장
        output_file = Path(output_path) / f"training_report_{job_id}.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        async with aiofiles.open(output_file, 'w') as f:
            await f.write(json.dumps(report, indent=2))
        
        logger.info(f"Training report exported to {output_file}")
        return str(output_file)
    
    def _flatten_dict(
        self,
        d: Dict[str, Any],
        parent_key: str = '',
        sep: str = '.'
    ) -> Dict[str, Any]:
        """중첩된 딕셔너리를 평면화"""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)
    
    async def compare_runs(
        self,
        job_ids: List[str]
    ) -> Dict[str, Any]:
        """여러 학습 실행 비교"""
        redis = await get_redis()
        comparisons = {}
        
        for job_id in job_ids:
            # 모니터링 정보
            info_str = await redis.get(f"{self.redis_key_prefix}{job_id}:info")
            if not info_str:
                continue
            
            info = json.loads(info_str)
            
            # 최종 메트릭
            final_metrics = info.get("final_metrics", {})
            
            comparisons[job_id] = {
                "config": info.get("config", {}),
                "final_metrics": final_metrics,
                "status": info.get("status", "unknown"),
                "start_time": info.get("start_time"),
                "end_time": info.get("end_time")
            }
        
        return comparisons


# 싱글톤 인스턴스
training_monitor_service = TrainingMonitorService()