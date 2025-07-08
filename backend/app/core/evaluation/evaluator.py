"""
모델 평가 및 검증 모듈
"""
import json
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import numpy as np

import torch
from transformers import (
    AutoModelForCausalLM, AutoTokenizer,
    GenerationConfig, TextGenerationPipeline
)
from datasets import Dataset
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
import evaluate
from loguru import logger


class EvaluationMetric(str, Enum):
    """평가 메트릭 유형"""
    PERPLEXITY = "perplexity"
    BLEU = "bleu"
    ROUGE = "rouge"
    METEOR = "meteor"
    ACCURACY = "accuracy"
    F1_SCORE = "f1_score"
    EXACT_MATCH = "exact_match"
    HUMAN_EVAL = "human_eval"
    MMLU = "mmlu"
    TRUTHFULQA = "truthfulqa"


@dataclass
class EvaluationConfig:
    """평가 설정"""
    model_path: str
    dataset_path: Optional[str] = None
    metrics: List[EvaluationMetric] = None
    batch_size: int = 8
    max_samples: Optional[int] = None
    device: str = "cuda" if torch.cuda.is_available() else "cpu"
    generation_config: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metrics is None:
            self.metrics = [EvaluationMetric.PERPLEXITY]
        
        if self.generation_config is None:
            self.generation_config = {
                "max_new_tokens": 128,
                "temperature": 0.7,
                "top_p": 0.9,
                "do_sample": True
            }


@dataclass
class EvaluationResult:
    """평가 결과"""
    model_path: str
    dataset_name: Optional[str]
    metrics: Dict[str, float]
    generation_samples: Optional[List[Dict[str, str]]] = None
    error_analysis: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class ModelEvaluator:
    """모델 평가기"""
    
    def __init__(self, config: EvaluationConfig):
        self.config = config
        self.model = None
        self.tokenizer = None
        self.evaluation_metrics = {}
        
        # 평가 메트릭 초기화
        self._initialize_metrics()
    
    def _initialize_metrics(self):
        """평가 메트릭 초기화"""
        if EvaluationMetric.BLEU in self.config.metrics:
            self.evaluation_metrics["bleu"] = evaluate.load("bleu")
        
        if EvaluationMetric.ROUGE in self.config.metrics:
            self.evaluation_metrics["rouge"] = evaluate.load("rouge")
        
        if EvaluationMetric.METEOR in self.config.metrics:
            self.evaluation_metrics["meteor"] = evaluate.load("meteor")
    
    def load_model(self):
        """모델 및 토크나이저 로드"""
        logger.info(f"Loading model from {self.config.model_path}")
        
        self.tokenizer = AutoTokenizer.from_pretrained(self.config.model_path)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.config.model_path,
            device_map="auto" if self.config.device == "cuda" else None,
            torch_dtype=torch.float16 if self.config.device == "cuda" else torch.float32
        )
        
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        self.model.eval()
    
    def evaluate(
        self,
        dataset: Optional[Dataset] = None,
        test_prompts: Optional[List[str]] = None
    ) -> EvaluationResult:
        """모델 평가 실행"""
        if self.model is None:
            self.load_model()
        
        results = {
            "model_path": self.config.model_path,
            "dataset_name": None,
            "metrics": {},
            "generation_samples": [],
            "error_analysis": {},
            "metadata": {
                "device": self.config.device,
                "batch_size": self.config.batch_size
            }
        }
        
        # 각 메트릭별 평가 실행
        for metric in self.config.metrics:
            if metric == EvaluationMetric.PERPLEXITY:
                if dataset:
                    ppl = self._calculate_perplexity(dataset)
                    results["metrics"]["perplexity"] = ppl
            
            elif metric == EvaluationMetric.ACCURACY:
                if dataset and "label" in dataset.column_names:
                    acc = self._calculate_accuracy(dataset)
                    results["metrics"]["accuracy"] = acc
            
            elif metric in [EvaluationMetric.BLEU, EvaluationMetric.ROUGE]:
                if dataset and "output" in dataset.column_names:
                    scores = self._calculate_generation_metrics(dataset, metric)
                    results["metrics"].update(scores)
        
        # 샘플 생성 테스트
        if test_prompts:
            samples = self._generate_samples(test_prompts)
            results["generation_samples"] = samples
        
        # 에러 분석
        if dataset:
            results["error_analysis"] = self._analyze_errors(dataset)
        
        return EvaluationResult(**results)
    
    def _calculate_perplexity(self, dataset: Dataset) -> float:
        """펄플렉시티 계산"""
        logger.info("Calculating perplexity...")
        
        total_loss = 0
        total_tokens = 0
        
        with torch.no_grad():
            for i in range(0, len(dataset), self.config.batch_size):
                batch = dataset[i:i + self.config.batch_size]
                
                # 토큰화
                encodings = self.tokenizer(
                    batch["text"] if "text" in batch else batch["input"],
                    truncation=True,
                    padding=True,
                    max_length=512,
                    return_tensors="pt"
                ).to(self.config.device)
                
                # Forward pass
                outputs = self.model(**encodings, labels=encodings["input_ids"])
                loss = outputs.loss
                
                # 손실 누적
                total_loss += loss.item() * encodings["input_ids"].shape[0]
                total_tokens += encodings["attention_mask"].sum().item()
        
        # 평균 손실에서 펄플렉시티 계산
        avg_loss = total_loss / len(dataset)
        perplexity = torch.exp(torch.tensor(avg_loss)).item()
        
        logger.info(f"Perplexity: {perplexity:.2f}")
        return perplexity
    
    def _calculate_accuracy(self, dataset: Dataset) -> float:
        """정확도 계산"""
        logger.info("Calculating accuracy...")
        
        predictions = []
        labels = []
        
        for i in range(0, len(dataset), self.config.batch_size):
            batch = dataset[i:i + self.config.batch_size]
            
            # 예측 생성
            batch_predictions = self._generate_predictions(batch["input"])
            predictions.extend(batch_predictions)
            labels.extend(batch["label"])
        
        # 정확도 계산
        accuracy = accuracy_score(labels, predictions)
        logger.info(f"Accuracy: {accuracy:.4f}")
        
        return accuracy
    
    def _calculate_generation_metrics(
        self,
        dataset: Dataset,
        metric_type: EvaluationMetric
    ) -> Dict[str, float]:
        """생성 메트릭 계산 (BLEU, ROUGE 등)"""
        logger.info(f"Calculating {metric_type.value}...")
        
        predictions = []
        references = []
        
        # 샘플링
        if self.config.max_samples and len(dataset) > self.config.max_samples:
            indices = np.random.choice(len(dataset), self.config.max_samples, replace=False)
            dataset = dataset.select(indices)
        
        # 예측 생성
        for i in range(0, len(dataset), self.config.batch_size):
            batch = dataset[i:i + self.config.batch_size]
            
            # 입력 텍스트에서 출력 생성
            inputs = batch["input"] if "input" in batch else batch["text"]
            outputs = self._generate_texts(inputs)
            
            predictions.extend(outputs)
            references.extend([[ref] for ref in batch["output"]])
        
        # 메트릭 계산
        if metric_type == EvaluationMetric.BLEU:
            metric = self.evaluation_metrics["bleu"]
            results = metric.compute(predictions=predictions, references=references)
            return {
                "bleu": results["bleu"],
                "bleu_1": results["precisions"][0],
                "bleu_2": results["precisions"][1],
                "bleu_3": results["precisions"][2],
                "bleu_4": results["precisions"][3]
            }
        
        elif metric_type == EvaluationMetric.ROUGE:
            metric = self.evaluation_metrics["rouge"]
            results = metric.compute(predictions=predictions, references=references)
            return {
                "rouge1": results["rouge1"],
                "rouge2": results["rouge2"],
                "rougeL": results["rougeL"]
            }
        
        return {}
    
    def _generate_predictions(self, inputs: List[str]) -> List[Any]:
        """분류 예측 생성"""
        predictions = []
        
        for text in inputs:
            encoding = self.tokenizer(
                text,
                truncation=True,
                max_length=512,
                return_tensors="pt"
            ).to(self.config.device)
            
            with torch.no_grad():
                outputs = self.model(**encoding)
                logits = outputs.logits[0, -1, :]  # 마지막 토큰의 로짓
                pred = torch.argmax(logits).item()
                predictions.append(pred)
        
        return predictions
    
    def _generate_texts(self, prompts: List[str]) -> List[str]:
        """텍스트 생성"""
        generated_texts = []
        
        for prompt in prompts:
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.config.device)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    **self.config.generation_config,
                    pad_token_id=self.tokenizer.pad_token_id
                )
            
            generated = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            # 프롬프트 제거
            generated = generated[len(prompt):].strip()
            generated_texts.append(generated)
        
        return generated_texts
    
    def _generate_samples(self, prompts: List[str]) -> List[Dict[str, str]]:
        """샘플 생성"""
        samples = []
        
        for prompt in prompts:
            generated = self._generate_texts([prompt])[0]
            samples.append({
                "prompt": prompt,
                "generated": generated
            })
        
        return samples
    
    def _analyze_errors(self, dataset: Dataset) -> Dict[str, Any]:
        """에러 분석"""
        analysis = {
            "total_samples": len(dataset),
            "error_types": {},
            "difficult_samples": []
        }
        
        # 간단한 에러 분석 (실제로는 더 복잡한 분석 필요)
        if "label" in dataset.column_names:
            # 일부 샘플만 분석
            sample_size = min(100, len(dataset))
            sample_indices = np.random.choice(len(dataset), sample_size, replace=False)
            
            for idx in sample_indices:
                sample = dataset[int(idx)]
                # 예측과 실제 라벨 비교 로직 추가 필요
                pass
        
        return analysis
    
    def benchmark_model(
        self,
        benchmark_name: str = "mmlu"
    ) -> Dict[str, float]:
        """벤치마크 평가"""
        logger.info(f"Running {benchmark_name} benchmark...")
        
        if benchmark_name == "mmlu":
            return self._evaluate_mmlu()
        elif benchmark_name == "human_eval":
            return self._evaluate_human_eval()
        elif benchmark_name == "truthfulqa":
            return self._evaluate_truthfulqa()
        else:
            raise ValueError(f"Unknown benchmark: {benchmark_name}")
    
    def _evaluate_mmlu(self) -> Dict[str, float]:
        """MMLU (Massive Multitask Language Understanding) 평가"""
        # 실제 구현에서는 MMLU 데이터셋을 로드하여 평가
        # 여기서는 더미 결과 반환
        return {
            "mmlu_average": 0.65,
            "mmlu_stem": 0.58,
            "mmlu_humanities": 0.72,
            "mmlu_social_sciences": 0.68,
            "mmlu_other": 0.62
        }
    
    def _evaluate_human_eval(self) -> Dict[str, float]:
        """HumanEval 코드 생성 평가"""
        # 실제 구현에서는 HumanEval 데이터셋을 사용
        return {
            "pass@1": 0.45,
            "pass@10": 0.68,
            "pass@100": 0.82
        }
    
    def _evaluate_truthfulqa(self) -> Dict[str, float]:
        """TruthfulQA 평가"""
        # 실제 구현에서는 TruthfulQA 데이터셋을 사용
        return {
            "truthfulqa_mc1": 0.42,
            "truthfulqa_mc2": 0.58,
            "truthfulqa_generation": 0.35
        }
    
    def compare_models(
        self,
        model_paths: List[str],
        dataset: Dataset
    ) -> Dict[str, EvaluationResult]:
        """여러 모델 비교 평가"""
        results = {}
        
        for model_path in model_paths:
            # 새 설정으로 평가
            config = EvaluationConfig(
                model_path=model_path,
                metrics=self.config.metrics,
                batch_size=self.config.batch_size,
                device=self.config.device
            )
            
            evaluator = ModelEvaluator(config)
            result = evaluator.evaluate(dataset)
            results[model_path] = result
        
        return results