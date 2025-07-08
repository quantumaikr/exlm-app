"""
하이퍼파라미터 최적화 서비스
"""
import json
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import numpy as np

import optuna
from optuna import Trial
from optuna.samplers import TPESampler
from optuna.pruners import MedianPruner
from loguru import logger

from app.core.training.config import TrainingConfig, TrainingType
from app.core.training.pipeline import run_training_pipeline


class HyperparameterOptimizationService:
    """하이퍼파라미터 최적화 서비스"""
    
    def __init__(self):
        self.studies: Dict[str, optuna.Study] = {}
    
    def create_study(
        self,
        study_name: str,
        direction: str = "minimize",
        sampler: Optional[optuna.samplers.BaseSampler] = None,
        pruner: Optional[optuna.pruners.BasePruner] = None,
        storage: Optional[str] = None
    ) -> optuna.Study:
        """Optuna 스터디 생성"""
        if sampler is None:
            sampler = TPESampler(seed=42)
        
        if pruner is None:
            pruner = MedianPruner(n_startup_trials=5, n_warmup_steps=5)
        
        study = optuna.create_study(
            study_name=study_name,
            direction=direction,
            sampler=sampler,
            pruner=pruner,
            storage=storage,
            load_if_exists=True
        )
        
        self.studies[study_name] = study
        return study
    
    def get_search_space(
        self,
        training_type: TrainingType,
        custom_ranges: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """학습 방법에 따른 탐색 공간 정의"""
        # 기본 하이퍼파라미터 범위
        base_space = {
            "learning_rate": {
                "type": "loguniform",
                "low": 1e-5,
                "high": 1e-2
            },
            "per_device_train_batch_size": {
                "type": "categorical",
                "choices": [2, 4, 8, 16]
            },
            "gradient_accumulation_steps": {
                "type": "categorical",
                "choices": [1, 2, 4, 8]
            },
            "num_train_epochs": {
                "type": "int",
                "low": 1,
                "high": 10
            },
            "warmup_ratio": {
                "type": "uniform",
                "low": 0.0,
                "high": 0.2
            },
            "weight_decay": {
                "type": "loguniform",
                "low": 1e-4,
                "high": 1e-1
            },
            "max_grad_norm": {
                "type": "uniform",
                "low": 0.1,
                "high": 1.0
            }
        }
        
        # LoRA/QLoRA 특화 파라미터
        if training_type in [TrainingType.LORA, TrainingType.QLORA]:
            base_space.update({
                "lora_r": {
                    "type": "categorical",
                    "choices": [4, 8, 16, 32, 64]
                },
                "lora_alpha": {
                    "type": "categorical",
                    "choices": [8, 16, 32, 64, 128]
                },
                "lora_dropout": {
                    "type": "uniform",
                    "low": 0.0,
                    "high": 0.3
                }
            })
        
        # DPO 특화 파라미터
        elif training_type == TrainingType.DPO:
            base_space.update({
                "dpo_beta": {
                    "type": "loguniform",
                    "low": 0.01,
                    "high": 1.0
                }
            })
        
        # ORPO 특화 파라미터
        elif training_type == TrainingType.ORPO:
            base_space.update({
                "orpo_beta": {
                    "type": "loguniform",
                    "low": 0.01,
                    "high": 1.0
                }
            })
        
        # 커스텀 범위 적용
        if custom_ranges:
            for param, range_config in custom_ranges.items():
                base_space[param] = range_config
        
        return base_space
    
    def sample_hyperparameters(
        self,
        trial: Trial,
        search_space: Dict[str, Any]
    ) -> Dict[str, Any]:
        """하이퍼파라미터 샘플링"""
        params = {}
        
        for param_name, config in search_space.items():
            param_type = config["type"]
            
            if param_type == "uniform":
                params[param_name] = trial.suggest_float(
                    param_name,
                    config["low"],
                    config["high"]
                )
            elif param_type == "loguniform":
                params[param_name] = trial.suggest_float(
                    param_name,
                    config["low"],
                    config["high"],
                    log=True
                )
            elif param_type == "int":
                params[param_name] = trial.suggest_int(
                    param_name,
                    config["low"],
                    config["high"]
                )
            elif param_type == "categorical":
                params[param_name] = trial.suggest_categorical(
                    param_name,
                    config["choices"]
                )
        
        return params
    
    def create_objective(
        self,
        base_config: TrainingConfig,
        search_space: Dict[str, Any],
        evaluation_metric: str = "eval_loss",
        progress_callback: Optional[Callable] = None
    ) -> Callable[[Trial], float]:
        """목적 함수 생성"""
        
        def objective(trial: Trial) -> float:
            # 하이퍼파라미터 샘플링
            hyperparams = self.sample_hyperparameters(trial, search_space)
            
            # 기본 설정에 샘플링된 하이퍼파라미터 적용
            config_dict = base_config.dict()
            
            # 일반 하이퍼파라미터 업데이트
            for param, value in hyperparams.items():
                if param.startswith("lora_"):
                    if "lora_config" not in config_dict:
                        config_dict["lora_config"] = {}
                    config_dict["lora_config"][param.replace("lora_", "")] = value
                elif param.startswith("dpo_"):
                    if "dpo_config" not in config_dict:
                        config_dict["dpo_config"] = {}
                    config_dict["dpo_config"][param.replace("dpo_", "")] = value
                elif param.startswith("orpo_"):
                    if "orpo_config" not in config_dict:
                        config_dict["orpo_config"] = {}
                    config_dict["orpo_config"][param.replace("orpo_", "")] = value
                else:
                    config_dict[param] = value
            
            # 학습 실행
            try:
                updated_config = TrainingConfig(**config_dict)
                result = run_training_pipeline(
                    updated_config,
                    progress_callback=progress_callback
                )
                
                # 평가 메트릭 추출
                metrics = result.get("metrics", {})
                metric_value = metrics.get(evaluation_metric, float('inf'))
                
                # 중간 결과 보고
                trial.report(metric_value, step=1)
                
                # Pruning 체크
                if trial.should_prune():
                    raise optuna.TrialPruned()
                
                return metric_value
                
            except Exception as e:
                logger.error(f"Trial {trial.number} failed: {str(e)}")
                # 실패한 경우 최악의 값 반환
                return float('inf') if search_space.get("direction", "minimize") == "minimize" else float('-inf')
        
        return objective
    
    def optimize(
        self,
        study_name: str,
        base_config: TrainingConfig,
        n_trials: int = 20,
        search_space: Optional[Dict[str, Any]] = None,
        evaluation_metric: str = "eval_loss",
        direction: str = "minimize",
        timeout: Optional[float] = None,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """하이퍼파라미터 최적화 실행"""
        # 탐색 공간 설정
        if search_space is None:
            search_space = self.get_search_space(base_config.training_type)
        
        # 스터디 생성 또는 가져오기
        if study_name not in self.studies:
            study = self.create_study(study_name, direction=direction)
        else:
            study = self.studies[study_name]
        
        # 목적 함수 생성
        objective = self.create_objective(
            base_config,
            search_space,
            evaluation_metric,
            progress_callback
        )
        
        # 최적화 실행
        logger.info(f"Starting hyperparameter optimization: {study_name}")
        study.optimize(
            objective,
            n_trials=n_trials,
            timeout=timeout,
            n_jobs=1  # 병렬 실행은 GPU 메모리 문제 방지를 위해 비활성화
        )
        
        # 결과 정리
        best_trial = study.best_trial
        best_params = best_trial.params
        
        # LoRA/DPO/ORPO 파라미터 재구성
        restructured_params = {}
        lora_config = {}
        dpo_config = {}
        orpo_config = {}
        
        for param, value in best_params.items():
            if param.startswith("lora_"):
                lora_config[param.replace("lora_", "")] = value
            elif param.startswith("dpo_"):
                dpo_config[param.replace("dpo_", "")] = value
            elif param.startswith("orpo_"):
                orpo_config[param.replace("orpo_", "")] = value
            else:
                restructured_params[param] = value
        
        if lora_config:
            restructured_params["lora_config"] = lora_config
        if dpo_config:
            restructured_params["dpo_config"] = dpo_config
        if orpo_config:
            restructured_params["orpo_config"] = orpo_config
        
        result = {
            "best_params": restructured_params,
            "best_value": best_trial.value,
            "best_trial_number": best_trial.number,
            "n_trials": len(study.trials),
            "optimization_history": [
                {
                    "trial_number": trial.number,
                    "value": trial.value,
                    "params": trial.params,
                    "state": trial.state.name
                }
                for trial in study.trials
            ],
            "study_name": study_name,
            "direction": direction,
            "evaluation_metric": evaluation_metric
        }
        
        logger.info(f"Optimization completed. Best value: {best_trial.value}")
        logger.info(f"Best parameters: {json.dumps(restructured_params, indent=2)}")
        
        return result
    
    def get_param_importance(
        self,
        study_name: str
    ) -> Dict[str, float]:
        """파라미터 중요도 분석"""
        if study_name not in self.studies:
            raise ValueError(f"Study {study_name} not found")
        
        study = self.studies[study_name]
        importance = optuna.importance.get_param_importances(study)
        
        return importance
    
    def visualize_optimization_history(
        self,
        study_name: str,
        save_path: Optional[str] = None
    ) -> None:
        """최적화 히스토리 시각화"""
        if study_name not in self.studies:
            raise ValueError(f"Study {study_name} not found")
        
        study = self.studies[study_name]
        
        # Optuna 시각화 도구 사용
        import optuna.visualization as vis
        
        # 최적화 히스토리
        fig = vis.plot_optimization_history(study)
        if save_path:
            fig.write_html(f"{save_path}/optimization_history.html")
        
        # 파라미터 중요도
        fig = vis.plot_param_importances(study)
        if save_path:
            fig.write_html(f"{save_path}/param_importances.html")
        
        # 파라미터 관계
        fig = vis.plot_parallel_coordinate(study)
        if save_path:
            fig.write_html(f"{save_path}/parallel_coordinate.html")
    
    def get_pareto_front_trials(
        self,
        study_name: str,
        objectives: List[str]
    ) -> List[optuna.trial.FrozenTrial]:
        """파레토 프론트 트라이얼 반환 (다목적 최적화)"""
        if study_name not in self.studies:
            raise ValueError(f"Study {study_name} not found")
        
        study = self.studies[study_name]
        
        # 각 목표에 대한 값 추출
        values = []
        for trial in study.trials:
            if trial.state == optuna.trial.TrialState.COMPLETE:
                trial_values = []
                for obj in objectives:
                    if obj in trial.user_attrs:
                        trial_values.append(trial.user_attrs[obj])
                    else:
                        trial_values.append(float('inf'))
                values.append(trial_values)
        
        # 파레토 프론트 계산
        pareto_trials = []
        for i, trial in enumerate(study.trials):
            if trial.state != optuna.trial.TrialState.COMPLETE:
                continue
            
            is_pareto = True
            for j, other_trial in enumerate(study.trials):
                if i == j or other_trial.state != optuna.trial.TrialState.COMPLETE:
                    continue
                
                # 다른 트라이얼이 모든 목표에서 더 좋거나 같은지 확인
                dominates = all(
                    values[j][k] <= values[i][k] for k in range(len(objectives))
                ) and any(
                    values[j][k] < values[i][k] for k in range(len(objectives))
                )
                
                if dominates:
                    is_pareto = False
                    break
            
            if is_pareto:
                pareto_trials.append(trial)
        
        return pareto_trials


# 싱글톤 인스턴스
hyperparameter_optimization_service = HyperparameterOptimizationService()