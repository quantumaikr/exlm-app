"""
학습 파이프라인 테스트
"""
import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from app.core.training.config import TrainingConfig, TrainingType
from app.core.training.pipeline import (
    run_training_pipeline,
    load_and_prepare_dataset,
    tokenize_texts,
    create_training_arguments
)


@pytest.fixture
def sample_config():
    """샘플 학습 설정"""
    return TrainingConfig(
        model_name="gpt2",
        dataset_id="test-dataset",
        training_type=TrainingType.LORA,
        num_train_epochs=1,
        per_device_train_batch_size=2,
        max_seq_length=128,
        validation_split_percentage=20,
        lora_config={
            "r": 8,
            "lora_alpha": 16,
            "lora_dropout": 0.1,
            "target_modules": ["q_proj", "v_proj"]
        }
    )


@pytest.fixture
def sample_dataset():
    """샘플 데이터셋 생성"""
    with tempfile.TemporaryDirectory() as temp_dir:
        dataset_dir = Path(temp_dir) / "datasets" / "test-dataset"
        dataset_dir.mkdir(parents=True)
        
        # 샘플 데이터 생성
        data = [
            {"text": "This is a test text."},
            {"text": "Another sample text for training."},
            {"text": "Machine learning is awesome!"},
            {"text": "Natural language processing with transformers."},
        ]
        
        data_file = dataset_dir / "data.jsonl"
        with open(data_file, "w") as f:
            for item in data:
                f.write(json.dumps(item) + "\n")
        
        yield dataset_dir


def test_tokenize_texts():
    """텍스트 토큰화 테스트"""
    from transformers import AutoTokenizer
    
    tokenizer = AutoTokenizer.from_pretrained("gpt2")
    tokenizer.pad_token = tokenizer.eos_token
    
    # 일반 텍스트 형식
    examples = {
        "text": ["Hello world", "Test text"]
    }
    result = tokenize_texts(examples, tokenizer, max_length=32)
    
    assert "input_ids" in result
    assert "attention_mask" in result
    assert "labels" in result
    assert result["input_ids"].shape[1] == 32
    
    # Alpaca 형식
    examples = {
        "instruction": ["What is AI?", "Explain ML"],
        "output": ["AI is artificial intelligence", "ML is machine learning"]
    }
    result = tokenize_texts(examples, tokenizer, max_length=64)
    
    assert "input_ids" in result
    assert result["input_ids"].shape[1] == 64


def test_load_and_prepare_dataset(sample_config, sample_dataset, monkeypatch):
    """데이터셋 로드 및 준비 테스트"""
    # 환경 설정
    monkeypatch.setattr("app.core.config.settings.UPLOAD_DIR", sample_dataset.parent.parent)
    
    dataset = load_and_prepare_dataset(sample_config)
    
    assert "train" in dataset
    assert "validation" in dataset
    assert len(dataset["train"]) == 3  # 80% of 4 samples
    assert len(dataset["validation"]) == 1  # 20% of 4 samples


def test_create_training_arguments(sample_config, tmp_path):
    """학습 인자 생성 테스트"""
    output_dir = tmp_path / "output"
    args = create_training_arguments(sample_config, output_dir)
    
    assert args.num_train_epochs == sample_config.num_train_epochs
    assert args.per_device_train_batch_size == sample_config.per_device_train_batch_size
    assert args.learning_rate == sample_config.learning_rate
    assert args.fp16 == sample_config.fp16
    assert str(output_dir) in args.output_dir


@patch("app.core.training.pipeline.AutoModelForCausalLM")
@patch("app.core.training.pipeline.AutoTokenizer")
@patch("app.core.training.pipeline.get_peft_model")
@patch("app.core.training.pipeline.Trainer")
def test_run_lora_training(
    mock_trainer_cls,
    mock_get_peft_model,
    mock_tokenizer_cls,
    mock_model_cls,
    sample_config,
    sample_dataset,
    monkeypatch
):
    """LoRA 학습 실행 테스트"""
    # 환경 설정
    monkeypatch.setattr("app.core.config.settings.UPLOAD_DIR", sample_dataset.parent.parent)
    monkeypatch.setattr("app.core.config.settings.MODEL_STORAGE_PATH", str(sample_dataset.parent))
    
    # Mock 설정
    mock_model = MagicMock()
    mock_model_cls.from_pretrained.return_value = mock_model
    
    mock_tokenizer = MagicMock()
    mock_tokenizer.pad_token = None
    mock_tokenizer_cls.from_pretrained.return_value = mock_tokenizer
    
    mock_peft_model = MagicMock()
    mock_get_peft_model.return_value = mock_peft_model
    
    mock_trainer = MagicMock()
    mock_train_result = MagicMock()
    mock_train_result.training_loss = 0.5
    mock_train_result.metrics = {
        "train_runtime": 100.0,
        "train_samples_per_second": 10.0,
        "epoch": 1.0
    }
    mock_trainer.train.return_value = mock_train_result
    mock_trainer_cls.return_value = mock_trainer
    
    # 학습 실행
    result = run_training_pipeline(sample_config)
    
    # 검증
    assert result["status"] == "completed"
    assert "metrics" in result
    assert "model_path" in result
    assert result["metrics"]["train_loss"] == 0.5
    
    # Mock 호출 검증
    mock_model_cls.from_pretrained.assert_called_once()
    mock_tokenizer_cls.from_pretrained.assert_called_once()
    mock_get_peft_model.assert_called_once()
    mock_trainer.train.assert_called_once()
    mock_trainer.save_model.assert_called_once()


def test_unsupported_training_type(sample_config, sample_dataset, monkeypatch):
    """지원되지 않는 학습 타입 테스트"""
    monkeypatch.setattr("app.core.config.settings.UPLOAD_DIR", sample_dataset.parent.parent)
    monkeypatch.setattr("app.core.config.settings.MODEL_STORAGE_PATH", str(sample_dataset.parent))
    
    # 잘못된 학습 타입 설정
    sample_config.training_type = "invalid_type"
    
    with pytest.raises(ValueError, match="Unsupported training type"):
        run_training_pipeline(sample_config)


def test_dataset_not_found(sample_config, monkeypatch, tmp_path):
    """데이터셋을 찾을 수 없는 경우 테스트"""
    monkeypatch.setattr("app.core.config.settings.UPLOAD_DIR", str(tmp_path))
    
    with pytest.raises(ValueError, match="No data file found"):
        load_and_prepare_dataset(sample_config)