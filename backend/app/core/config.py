from typing import List, Union, Optional
from pydantic import AnyHttpUrl, field_validator, validator
from pydantic_settings import BaseSettings
import os
from datetime import datetime
import torch


class Settings(BaseSettings):
    # Project
    PROJECT_NAME: str = "exlm - Domain-Specific LLM Automation Platform"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    STARTUP_TIME: datetime = datetime.utcnow()
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Database
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "localhost")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "exlm_db")
    DATABASE_URL: str = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER}/{POSTGRES_DB}"
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = [
        "http://localhost:3000",
        "http://localhost:8000",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # ML/AI API Keys
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    
    # Hugging Face
    HF_TOKEN: str = os.getenv("HF_TOKEN", "")
    
    # Monitoring
    WANDB_API_KEY: str = os.getenv("WANDB_API_KEY", "")
    MLFLOW_TRACKING_URI: str = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    
    # Storage
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    MODEL_DIR: str = os.getenv("MODEL_DIR", "./models")
    
    # Celery
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
    
    # GPU
    USE_GPU: bool = False
    CUDA_VISIBLE_DEVICES: Optional[str] = None
    
    @validator("USE_GPU", pre=True, always=True)
    def set_gpu_settings(cls, v, values):
        """GPU 사용 가능 여부를 자동으로 감지하고 설정"""
        build_env = values.get("ENVIRONMENT", "development")
        
        # GPU 환경에서 빌드된 경우
        if build_env == "gpu":
            # CUDA 사용 가능 여부 확인
            if torch.cuda.is_available():
                return True
            else:
                print("Warning: GPU build but CUDA not available, falling back to CPU")
                return False
        else:
            # 개발 환경에서는 CPU 사용
            return False
    
    @validator("CUDA_VISIBLE_DEVICES", pre=True, always=True)
    def set_cuda_devices(cls, v, values):
        """CUDA 디바이스 설정"""
        use_gpu = values.get("USE_GPU", False)
        if use_gpu and torch.cuda.is_available():
            # 모든 GPU 사용 (필요시 특정 GPU 지정 가능)
            return "0,1,2,3" if torch.cuda.device_count() > 1 else "0"
        return None
    
    @property
    def is_gpu_available(self) -> bool:
        """GPU 사용 가능 여부 반환"""
        return self.USE_GPU and torch.cuda.is_available()
    
    @property
    def device(self) -> str:
        """사용할 디바이스 반환"""
        return "cuda" if self.is_gpu_available else "cpu"
    
    @property
    def torch_dtype(self):
        """PyTorch 데이터 타입 반환"""
        if self.is_gpu_available:
            return torch.float16  # GPU에서는 float16 사용
        else:
            return torch.float32  # CPU에서는 float32 사용
    
    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()

# GPU 정보 출력
if settings.is_gpu_available:
    print(f"🚀 GPU 환경 감지됨:")
    print(f"   - 사용 가능한 GPU: {torch.cuda.device_count()}개")
    print(f"   - 현재 디바이스: {settings.device}")
    print(f"   - CUDA 버전: {torch.version.cuda}")
    for i in range(torch.cuda.device_count()):
        gpu_name = torch.cuda.get_device_name(i)
        gpu_memory = torch.cuda.get_device_properties(i).total_memory / 1024**3
        print(f"   - GPU {i}: {gpu_name} ({gpu_memory:.1f}GB)")
else:
    print(f"💻 CPU 환경으로 실행 중")
    print(f"   - 디바이스: {settings.device}")
    print(f"   - PyTorch 버전: {torch.__version__}")