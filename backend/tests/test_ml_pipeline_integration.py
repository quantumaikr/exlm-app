"""
ML 파이프라인 통합 테스트
"""
import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from app.core.training.config import TrainingConfig, TrainingType
from app.services.training_pipeline import training_pipeline_service
from app.services.hyperparameter_optimization import hyperparameter_optimization_service
from app.services.training_monitor import training_monitor_service
from app.models.training import TrainingJob, TrainingStatus


@pytest.mark.asyncio
async def test_training_pipeline_service():
    """학습 파이프라인 서비스 테스트"""
    # 지원되는 학습 방법 확인
    methods = await training_pipeline_service.get_supported_training_methods()
    
    assert len(methods) >= 5
    assert any(m["id"] == "lora" for m in methods)
    assert any(m["id"] == "qlora" for m in methods)
    assert any(m["id"] == "dpo" for m in methods)
    
    # LoRA 메서드 상세 확인
    lora_method = next(m for m in methods if m["id"] == "lora")
    assert lora_method["supports_quantization"] is True
    assert "default_config" in lora_method
    assert "r" in lora_method["default_config"]


@pytest.mark.asyncio
async def test_create_training_job():
    """학습 작업 생성 테스트"""
    with patch('app.services.training_pipeline.celery_app.send_task') as mock_send_task:
        mock_task = Mock()
        mock_task.id = "test-celery-task-id"
        mock_send_task.return_value = mock_task
        
        # Mock DB 세션
        mock_db = AsyncMock()
        mock_db.add = Mock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # 학습 작업 생성
        training_config = {
            "model_name": "gpt2",
            "training_type": "lora",
            "num_train_epochs": 3,
            "learning_rate": 2e-4
        }
        
        job = await training_pipeline_service.create_training_job(
            db=mock_db,
            project_id="test-project-id",
            model_id="test-model-id",
            dataset_id="test-dataset-id",
            training_config=training_config,
            user_id="test-user-id"
        )
        
        # 검증
        mock_db.add.assert_called_once()
        assert mock_db.commit.call_count == 2  # 작업 생성 + task ID 업데이트
        mock_send_task.assert_called_once()


def test_hyperparameter_search_space():
    """하이퍼파라미터 탐색 공간 테스트"""
    # LoRA 탐색 공간
    lora_space = hyperparameter_optimization_service.get_search_space(TrainingType.LORA)
    
    assert "learning_rate" in lora_space
    assert "lora_r" in lora_space
    assert "lora_alpha" in lora_space
    assert "lora_dropout" in lora_space
    
    # DPO 탐색 공간
    dpo_space = hyperparameter_optimization_service.get_search_space(TrainingType.DPO)
    
    assert "dpo_beta" in dpo_space
    assert "lora_r" not in dpo_space


def test_hyperparameter_sampling():
    """하이퍼파라미터 샘플링 테스트"""
    from optuna import create_study
    
    study = create_study()
    trial = study.ask()
    
    search_space = {
        "learning_rate": {
            "type": "loguniform",
            "low": 1e-5,
            "high": 1e-2
        },
        "batch_size": {
            "type": "categorical",
            "choices": [2, 4, 8]
        },
        "epochs": {
            "type": "int",
            "low": 1,
            "high": 5
        }
    }
    
    params = hyperparameter_optimization_service.sample_hyperparameters(trial, search_space)
    
    assert "learning_rate" in params
    assert "batch_size" in params
    assert "epochs" in params
    assert params["batch_size"] in [2, 4, 8]
    assert 1 <= params["epochs"] <= 5


@pytest.mark.asyncio
async def test_training_monitoring():
    """학습 모니터링 테스트"""
    job_id = "test-job-123"
    config = {
        "model_name": "gpt2",
        "training_type": "lora",
        "learning_rate": 2e-4
    }
    
    # Redis mock
    mock_redis = AsyncMock()
    mock_redis.setex = AsyncMock()
    mock_redis.lpush = AsyncMock()
    mock_redis.ltrim = AsyncMock()
    mock_redis.get = AsyncMock(return_value=json.dumps({
        "job_id": job_id,
        "config": config,
        "use_wandb": False,
        "use_mlflow": False
    }))
    
    with patch('app.services.training_monitor.get_redis', return_value=mock_redis):
        # 모니터링 시작
        monitoring_info = await training_monitor_service.start_monitoring(
            job_id=job_id,
            config=config,
            use_wandb=False,
            use_mlflow=False
        )
        
        assert monitoring_info["job_id"] == job_id
        assert "start_time" in monitoring_info
        
        # 메트릭 로깅
        metrics = {
            "loss": 0.5,
            "learning_rate": 2e-4,
            "epoch": 1
        }
        
        await training_monitor_service.log_metrics(
            job_id=job_id,
            metrics=metrics,
            step=100
        )
        
        # Redis 호출 확인
        mock_redis.lpush.assert_called()
        mock_redis.setex.assert_called()


@pytest.mark.asyncio
async def test_metrics_history_retrieval():
    """메트릭 히스토리 조회 테스트"""
    job_id = "test-job-123"
    
    # Mock 메트릭 데이터
    mock_metrics = [
        json.dumps({
            "timestamp": "2024-01-01T00:00:00",
            "step": 100,
            "metrics": {"loss": 0.5, "accuracy": 0.8}
        }),
        json.dumps({
            "timestamp": "2024-01-01T00:01:00",
            "step": 200,
            "metrics": {"loss": 0.4, "accuracy": 0.85}
        })
    ]
    
    mock_redis = AsyncMock()
    mock_redis.lrange = AsyncMock(return_value=mock_metrics)
    
    with patch('app.services.training_monitor.get_redis', return_value=mock_redis):
        history = await training_monitor_service.get_metrics_history(job_id, limit=10)
        
        assert len(history) == 2
        assert history[0]["metrics"]["loss"] == 0.5
        assert history[1]["metrics"]["accuracy"] == 0.85


def test_optimization_objective_creation():
    """최적화 목적 함수 생성 테스트"""
    base_config = TrainingConfig(
        model_name="gpt2",
        dataset_id="test-dataset",
        training_type=TrainingType.LORA
    )
    
    search_space = {
        "learning_rate": {
            "type": "loguniform",
            "low": 1e-5,
            "high": 1e-2
        }
    }
    
    # Mock 학습 파이프라인
    with patch('app.services.hyperparameter_optimization.run_training_pipeline') as mock_pipeline:
        mock_pipeline.return_value = {
            "status": "completed",
            "metrics": {"eval_loss": 0.3}
        }
        
        objective = hyperparameter_optimization_service.create_objective(
            base_config=base_config,
            search_space=search_space,
            evaluation_metric="eval_loss"
        )
        
        # Optuna trial mock
        from optuna import create_study
        study = create_study()
        trial = study.ask()
        
        # 목적 함수 실행
        result = objective(trial)
        
        assert result == 0.3
        mock_pipeline.assert_called_once()


@pytest.mark.asyncio
async def test_training_report_export():
    """학습 리포트 내보내기 테스트"""
    job_id = "test-job-123"
    
    # Mock 데이터
    monitoring_info = {
        "job_id": job_id,
        "config": {"model_name": "gpt2"},
        "final_metrics": {"loss": 0.2}
    }
    
    metrics_history = [
        {"step": 100, "metrics": {"loss": 0.5}},
        {"step": 200, "metrics": {"loss": 0.3}}
    ]
    
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=json.dumps(monitoring_info))
    mock_redis.lrange = AsyncMock(side_effect=[
        [json.dumps(m) for m in metrics_history],  # metrics
        []  # artifacts
    ])
    
    with patch('app.services.training_monitor.get_redis', return_value=mock_redis):
        with patch('aiofiles.open', create=True) as mock_open:
            mock_file = AsyncMock()
            mock_open.return_value.__aenter__.return_value = mock_file
            
            output_path = await training_monitor_service.export_training_report(
                job_id=job_id,
                output_path="/tmp"
            )
            
            assert job_id in output_path
            mock_file.write.assert_called_once()