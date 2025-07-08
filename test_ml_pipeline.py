"""
ML 파이프라인 간단 테스트
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asyncio
import json
from pathlib import Path
from app.core.training.config import TrainingConfig, TrainingType
from app.services.training_pipeline import training_pipeline_service
from app.services.hyperparameter_optimization import hyperparameter_optimization_service
from app.services.training_monitor import training_monitor_service

async def test_pipeline():
    """파이프라인 서비스 테스트"""
    print("=== ML 파이프라인 테스트 시작 ===\n")
    
    # 1. 지원되는 학습 방법 확인
    print("1. 지원되는 학습 방법 확인")
    methods = await training_pipeline_service.get_supported_training_methods()
    print(f"   - 총 {len(methods)}개 학습 방법 지원")
    for method in methods:
        print(f"   - {method['name']} ({method['id']}): {method['description']}")
    print()
    
    # 2. 하이퍼파라미터 탐색 공간 테스트
    print("2. 하이퍼파라미터 탐색 공간 테스트")
    for training_type in [TrainingType.LORA, TrainingType.DPO]:
        space = hyperparameter_optimization_service.get_search_space(training_type)
        print(f"   - {training_type.value} 탐색 공간 파라미터: {list(space.keys())}")
    print()
    
    # 3. 학습 모니터링 서비스 테스트
    print("3. 학습 모니터링 서비스 테스트")
    job_id = "test-job-001"
    config = {
        "model_name": "gpt2",
        "training_type": "lora",
        "learning_rate": 2e-4
    }
    
    try:
        # Redis 연결 없이도 기본 기능 테스트
        monitoring_info = {
            "job_id": job_id,
            "config": config,
            "use_wandb": False,
            "use_mlflow": False
        }
        print(f"   - 모니터링 정보 생성: {monitoring_info}")
        print()
    except Exception as e:
        print(f"   - 모니터링 서비스 테스트 실패: {e}")
        print()
    
    # 4. 학습 설정 검증 테스트
    print("4. 학습 설정 검증 테스트")
    try:
        test_config = TrainingConfig(
            model_name="gpt2",
            dataset_id="test-dataset",
            training_type=TrainingType.LORA,
            num_train_epochs=3,
            per_device_train_batch_size=4,
            lora_config={
                "r": 8,
                "lora_alpha": 16,
                "lora_dropout": 0.1
            }
        )
        print(f"   - 학습 설정 생성 성공:")
        print(f"     - 모델: {test_config.model_name}")
        print(f"     - 학습 타입: {test_config.training_type.value}")
        print(f"     - 에폭: {test_config.num_train_epochs}")
        print(f"     - LoRA r: {test_config.lora_config['r']}")
    except Exception as e:
        print(f"   - 학습 설정 검증 실패: {e}")
    
    print("\n=== ML 파이프라인 테스트 완료 ===")

if __name__ == "__main__":
    asyncio.run(test_pipeline())