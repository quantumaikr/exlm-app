"""
실제 학습 파이프라인 구현
"""
import os
import json
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
    EarlyStoppingCallback,
    TrainerCallback,
)
from peft import (
    LoraConfig,
    get_peft_model,
    TaskType,
    prepare_model_for_kbit_training,
)
from datasets import load_dataset, Dataset
from trl import DPOTrainer
# ORPOTrainer, ORPOConfig - 현재 trl 버전에서 지원되지 않음
import wandb
from loguru import logger

from app.core.config import settings
from app.core.training.config import TrainingConfig, TrainingType


class ProgressCallback(TrainerCallback):
    """학습 진행상황 콜백"""
    
    def __init__(self, total_steps: int, callback=None):
        self.total_steps = total_steps
        self.callback = callback
        self.current_step = 0
    
    def on_log(self, args, state, control, logs=None, **kwargs):
        if state.global_step > self.current_step:
            self.current_step = state.global_step
            if self.callback:
                self.callback(
                    self.current_step,
                    self.total_steps,
                    f"Step {self.current_step}/{self.total_steps}"
                )


def run_training_pipeline(
    config: TrainingConfig,
    progress_callback: Optional[callable] = None
) -> Dict[str, Any]:
    """
    학습 파이프라인 실행
    
    Args:
        config: 학습 설정
        progress_callback: 진행상황 콜백 함수
        
    Returns:
        학습 결과
    """
    try:
        # 출력 디렉토리 설정
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(settings.MODEL_STORAGE_PATH) / f"{config.model_name}_{timestamp}"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Starting training pipeline: {config.training_type.value}")
        logger.info(f"Output directory: {output_dir}")
        
        # 데이터셋 로드
        dataset = load_and_prepare_dataset(config)
        
        # 학습 방법에 따른 처리
        if config.training_type == TrainingType.FULL_FINETUNING:
            result = run_full_finetuning(config, dataset, output_dir, progress_callback)
        elif config.training_type in [TrainingType.LORA, TrainingType.QLORA]:
            result = run_lora_training(config, dataset, output_dir, progress_callback)
        elif config.training_type == TrainingType.DPO:
            result = run_dpo_training(config, dataset, output_dir, progress_callback)
        elif config.training_type == TrainingType.ORPO:
            result = run_orpo_training(config, dataset, output_dir, progress_callback)
        else:
            raise ValueError(f"Unsupported training type: {config.training_type}")
        
        # 학습 결과에 추가 정보 포함
        result.update({
            "model_path": str(output_dir / "final_model"),
            "output_dir": str(output_dir),
            "timestamp": timestamp,
            "config": config.dict()
        })
        
        return result
        
    except Exception as e:
        logger.error(f"Training pipeline failed: {str(e)}")
        raise


def load_and_prepare_dataset(config: TrainingConfig) -> Dataset:
    """데이터셋 로드 및 준비"""
    dataset_path = Path(settings.UPLOAD_DIR) / "datasets" / config.dataset_id
    
    # 데이터 파일 찾기
    data_file = None
    for ext in [".jsonl", ".json", ".csv", ".parquet"]:
        file_path = dataset_path / f"generated_data{ext}"
        if file_path.exists():
            data_file = str(file_path)
            break
    
    if not data_file:
        # 기본 데이터 파일명으로 시도
        for ext in [".jsonl", ".json", ".csv", ".parquet"]:
            file_path = dataset_path / f"data{ext}"
            if file_path.exists():
                data_file = str(file_path)
                break
    
    if not data_file:
        raise ValueError(f"No data file found in {dataset_path}")
    
    logger.info(f"Loading dataset from: {data_file}")
    
    # 파일 형식에 따른 로드
    if data_file.endswith(".jsonl") or data_file.endswith(".json"):
        dataset = load_dataset("json", data_files=data_file)
    elif data_file.endswith(".csv"):
        dataset = load_dataset("csv", data_files=data_file)
    elif data_file.endswith(".parquet"):
        dataset = load_dataset("parquet", data_files=data_file)
    else:
        raise ValueError(f"Unsupported file format: {data_file}")
    
    # 데이터셋 분할 (train/validation)
    if "train" not in dataset:
        dataset = dataset["train"]
        
    if config.validation_split_percentage > 0:
        split_dataset = dataset.train_test_split(
            test_size=config.validation_split_percentage / 100,
            seed=config.seed
        )
        return split_dataset
    
    return {"train": dataset, "validation": None}


def run_full_finetuning(
    config: TrainingConfig,
    dataset: Dict[str, Dataset],
    output_dir: Path,
    progress_callback: Optional[callable] = None
) -> Dict[str, Any]:
    """전체 파인튜닝 실행"""
    logger.info("Running full fine-tuning")
    
    # 토크나이저 로드
    tokenizer = AutoTokenizer.from_pretrained(config.model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    # 모델 로드
    model = AutoModelForCausalLM.from_pretrained(
        config.model_name,
        torch_dtype=torch.float16 if config.fp16 else torch.float32,
        device_map="auto",
        trust_remote_code=True
    )
    
    # 데이터 전처리
    def preprocess_function(examples):
        return tokenize_texts(examples, tokenizer, config.max_seq_length)
    
    tokenized_dataset = dataset.map(
        preprocess_function,
        batched=True,
        remove_columns=dataset["train"].column_names
    )
    
    # 데이터 콜레이터
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,
    )
    
    # 학습 인자
    training_args = create_training_arguments(config, output_dir)
    
    # 콜백 설정
    callbacks = []
    if config.early_stopping:
        callbacks.append(EarlyStoppingCallback(early_stopping_patience=3))
    if progress_callback:
        total_steps = len(tokenized_dataset["train"]) // config.per_device_train_batch_size * config.num_train_epochs
        callbacks.append(ProgressCallback(total_steps, progress_callback))
    
    # 트레이너 생성
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset["train"],
        eval_dataset=tokenized_dataset.get("validation"),
        tokenizer=tokenizer,
        data_collator=data_collator,
        callbacks=callbacks
    )
    
    # 학습 실행
    train_result = trainer.train()
    
    # 모델 저장
    final_model_path = output_dir / "final_model"
    trainer.save_model(str(final_model_path))
    tokenizer.save_pretrained(str(final_model_path))
    
    # 메트릭 저장
    metrics = {
        "train_loss": train_result.training_loss,
        "train_runtime": train_result.metrics["train_runtime"],
        "train_samples_per_second": train_result.metrics["train_samples_per_second"],
        "epoch": train_result.metrics["epoch"],
    }
    
    with open(output_dir / "training_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    
    return {
        "status": "completed",
        "metrics": metrics,
        "model_path": str(final_model_path)
    }


def run_lora_training(
    config: TrainingConfig,
    dataset: Dict[str, Dataset],
    output_dir: Path,
    progress_callback: Optional[callable] = None
) -> Dict[str, Any]:
    """LoRA/QLoRA 학습 실행"""
    logger.info(f"Running {config.training_type.value} training")
    
    # 토크나이저 로드
    tokenizer = AutoTokenizer.from_pretrained(config.model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    # 양자화 설정
    load_in_4bit = config.training_type == TrainingType.QLORA
    bnb_config = None
    
    if load_in_4bit:
        from transformers import BitsAndBytesConfig
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )
    
    # 모델 로드
    model = AutoModelForCausalLM.from_pretrained(
        config.model_name,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
        torch_dtype=torch.float16,
    )
    
    # 양자화된 모델 준비
    if load_in_4bit:
        model = prepare_model_for_kbit_training(model)
    
    # LoRA 설정
    lora_config = config.lora_config or {}
    peft_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=lora_config.get("r", 16),
        lora_alpha=lora_config.get("lora_alpha", 32),
        lora_dropout=lora_config.get("lora_dropout", 0.1),
        target_modules=lora_config.get("target_modules", ["q_proj", "v_proj", "k_proj", "o_proj"]),
        bias="none",
    )
    
    # PEFT 모델 생성
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()
    
    # 데이터 전처리
    def preprocess_function(examples):
        return tokenize_texts(examples, tokenizer, config.max_seq_length)
    
    tokenized_dataset = dataset.map(
        preprocess_function,
        batched=True,
        remove_columns=dataset["train"].column_names
    )
    
    # 데이터 콜레이터
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,
    )
    
    # 학습 인자
    training_args = create_training_arguments(config, output_dir)
    
    # 콜백 설정
    callbacks = []
    if config.early_stopping:
        callbacks.append(EarlyStoppingCallback(early_stopping_patience=3))
    if progress_callback:
        total_steps = len(tokenized_dataset["train"]) // config.per_device_train_batch_size * config.num_train_epochs
        callbacks.append(ProgressCallback(total_steps, progress_callback))
    
    # 트레이너 생성
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset["train"],
        eval_dataset=tokenized_dataset.get("validation"),
        tokenizer=tokenizer,
        data_collator=data_collator,
        callbacks=callbacks
    )
    
    # 학습 실행
    train_result = trainer.train()
    
    # 모델 저장
    final_model_path = output_dir / "final_model"
    trainer.save_model(str(final_model_path))
    tokenizer.save_pretrained(str(final_model_path))
    
    # 메트릭 저장
    metrics = {
        "train_loss": train_result.training_loss,
        "train_runtime": train_result.metrics["train_runtime"],
        "train_samples_per_second": train_result.metrics["train_samples_per_second"],
        "epoch": train_result.metrics["epoch"],
    }
    
    with open(output_dir / "training_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    
    return {
        "status": "completed",
        "metrics": metrics,
        "model_path": str(final_model_path)
    }


def run_dpo_training(
    config: TrainingConfig,
    dataset: Dict[str, Dataset],
    output_dir: Path,
    progress_callback: Optional[callable] = None
) -> Dict[str, Any]:
    """DPO (Direct Preference Optimization) 학습 실행"""
    logger.info("Running DPO training")
    
    # DPO는 preference 데이터가 필요함
    # dataset은 chosen과 rejected 응답을 포함해야 함
    
    # 토크나이저 로드
    tokenizer = AutoTokenizer.from_pretrained(config.model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    # 모델 로드 (GPU 설정 자동 감지)
    from app.core.config import settings
    model = AutoModelForCausalLM.from_pretrained(
        config.model_name,
        torch_dtype=settings.torch_dtype,
        device_map="auto" if settings.is_gpu_available else None,
        trust_remote_code=True
    )
    
    # DPO 설정
    dpo_config = config.dpo_config or {}
    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=config.num_train_epochs,
        per_device_train_batch_size=config.per_device_train_batch_size,
        gradient_accumulation_steps=config.gradient_accumulation_steps,
        learning_rate=config.learning_rate,
        warmup_ratio=config.warmup_ratio,
        logging_steps=config.logging_steps,
        save_steps=config.save_steps,
        eval_steps=config.eval_steps,
        evaluation_strategy="steps" if dataset.get("validation") else "no",
        save_total_limit=config.save_total_limit,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        fp16=settings.is_gpu_available,  # GPU에서만 fp16 사용
        bf16=config.bf16,
        report_to=["tensorboard", "wandb"] if config.use_wandb else ["tensorboard"],
        remove_unused_columns=False,
    )
    
    # DPO 트레이너 생성
    dpo_trainer = DPOTrainer(
        model=model,
        ref_model=model,
        args=training_args,
        beta=dpo_config.get("beta", 0.1),
        train_dataset=dataset["train"],
        eval_dataset=dataset.get("validation"),
        tokenizer=tokenizer,
        max_prompt_length=dpo_config.get("max_prompt_length", 512),
        max_length=config.max_seq_length,
    )
    
    # 학습 실행
    train_result = dpo_trainer.train()
    
    # 모델 저장
    final_model_path = output_dir / "final_model"
    dpo_trainer.save_model(str(final_model_path))
    tokenizer.save_pretrained(str(final_model_path))
    
    # 메트릭 저장
    metrics = {
        "train_loss": train_result.training_loss if hasattr(train_result, 'training_loss') else None,
        "train_runtime": train_result.metrics["train_runtime"],
        "epoch": train_result.metrics["epoch"],
    }
    
    return {
        "status": "completed",
        "metrics": metrics,
        "model_path": str(final_model_path)
    }


def run_orpo_training(
    config: TrainingConfig,
    dataset: Dict[str, Dataset],
    output_dir: Path,
    progress_callback: Optional[callable] = None
) -> Dict[str, Any]:
    """ORPO (Odds Ratio Preference Optimization) 학습 실행"""
    logger.warning("ORPO training is not supported in current trl version. Falling back to DPO training.")
    
    # ORPO 대신 DPO 학습을 사용
    return run_dpo_training(config, dataset, output_dir, progress_callback)


def create_training_arguments(config: TrainingConfig, output_dir: Path) -> TrainingArguments:
    """학습 인자 생성"""
    return TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=config.num_train_epochs,
        per_device_train_batch_size=config.per_device_train_batch_size,
        per_device_eval_batch_size=config.per_device_eval_batch_size,
        gradient_accumulation_steps=config.gradient_accumulation_steps,
        gradient_checkpointing=config.gradient_checkpointing,
        optim=config.optim,
        learning_rate=config.learning_rate,
        warmup_ratio=config.warmup_ratio,
        warmup_steps=config.warmup_steps,
        lr_scheduler_type=config.lr_scheduler_type,
        logging_dir=str(output_dir / "logs"),
        logging_steps=config.logging_steps,
        save_strategy="steps",
        save_steps=config.save_steps,
        eval_steps=config.eval_steps,
        evaluation_strategy="steps" if config.validation_split_percentage > 0 else "no",
        save_total_limit=config.save_total_limit,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        fp16=config.fp16,
        bf16=config.bf16,
        tf32=True,
        dataloader_num_workers=config.dataloader_num_workers,
        remove_unused_columns=False,
        label_names=["labels"],
        report_to=["tensorboard", "wandb"] if config.use_wandb else ["tensorboard"],
        run_name=f"{config.model_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        push_to_hub=False,
        group_by_length=config.group_by_length,
        length_column_name="length",
        max_grad_norm=config.max_grad_norm,
        weight_decay=config.weight_decay,
        seed=config.seed,
    )


def tokenize_texts(examples: Dict[str, Any], tokenizer, max_length: int) -> Dict[str, Any]:
    """텍스트 토큰화"""
    # 다양한 데이터 형식 지원
    if "text" in examples:
        texts = examples["text"]
    elif "instruction" in examples and "output" in examples:
        # Alpaca 형식
        texts = []
        for i in range(len(examples["instruction"])):
            instruction = examples["instruction"][i]
            output = examples["output"][i]
            text = f"### Instruction:\n{instruction}\n\n### Response:\n{output}"
            texts.append(text)
    elif "prompt" in examples and "completion" in examples:
        # OpenAI 형식
        texts = []
        for i in range(len(examples["prompt"])):
            prompt = examples["prompt"][i]
            completion = examples["completion"][i]
            text = f"{prompt}{completion}"
            texts.append(text)
    elif "messages" in examples:
        # Chat 형식
        texts = []
        for messages in examples["messages"]:
            text = ""
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "system":
                    text += f"System: {content}\n"
                elif role == "user":
                    text += f"Human: {content}\n"
                elif role == "assistant":
                    text += f"Assistant: {content}\n"
            texts.append(text.strip())
    else:
        raise ValueError("Unsupported dataset format")
    
    # 토큰화
    model_inputs = tokenizer(
        texts,
        max_length=max_length,
        padding="max_length",
        truncation=True,
        return_tensors="pt"
    )
    
    # labels는 input_ids의 복사본
    model_inputs["labels"] = model_inputs["input_ids"].clone()
    
    return model_inputs