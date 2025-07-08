"""
모델 서빙 관련 스키마
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class ServingStatus(str, Enum):
    """서빙 상태"""
    PENDING = "pending"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class ServingConfig(BaseModel):
    """서빙 설정"""
    max_model_len: int = Field(2048, description="최대 모델 길이")
    gpu_memory_utilization: float = Field(0.9, description="GPU 메모리 사용률")
    max_num_batched_tokens: int = Field(4096, description="최대 배치 토큰 수")
    max_num_seqs: int = Field(256, description="최대 시퀀스 수")
    quantization: Optional[str] = Field(None, description="양자화 방법")
    tensor_parallel_size: int = Field(1, description="텐서 병렬 크기")
    trust_remote_code: bool = Field(False, description="원격 코드 신뢰")
    dtype: str = Field("auto", description="데이터 타입")


class GenerationRequest(BaseModel):
    """텍스트 생성 요청"""
    prompt: str = Field(..., description="입력 프롬프트")
    max_tokens: int = Field(512, description="최대 토큰 수")
    temperature: float = Field(0.7, description="온도")
    top_p: float = Field(0.9, description="Top-p 샘플링")
    stop: Optional[List[str]] = Field(None, description="중지 토큰")
    stream: bool = Field(False, description="스트리밍 여부")


class GenerationResponse(BaseModel):
    """텍스트 생성 응답"""
    text: str = Field(..., description="생성된 텍스트")
    tokens_used: int = Field(..., description="사용된 토큰 수")
    finish_reason: str = Field(..., description="완료 이유")
    latency: float = Field(..., description="지연 시간 (초)")


class ModelServingInfo(BaseModel):
    """모델 서빙 정보"""
    model_id: str = Field(..., description="모델 ID")
    status: ServingStatus = Field(..., description="서빙 상태")
    endpoint_url: Optional[str] = Field(None, description="엔드포인트 URL")
    config: ServingConfig = Field(..., description="서빙 설정")
    started_at: Optional[datetime] = Field(None, description="시작 시간")
    metrics: Optional[Dict[str, Any]] = Field(None, description="메트릭")
    error_message: Optional[str] = Field(None, description="에러 메시지")


class ServingMetrics(BaseModel):
    """서빙 메트릭"""
    total_requests: int = Field(0, description="총 요청 수")
    successful_requests: int = Field(0, description="성공한 요청 수")
    failed_requests: int = Field(0, description="실패한 요청 수")
    average_latency: float = Field(0.0, description="평균 지연 시간")
    tokens_per_second: float = Field(0.0, description="초당 토큰 수")
    gpu_memory_used: float = Field(0.0, description="GPU 메모리 사용량")
    gpu_utilization: float = Field(0.0, description="GPU 사용률") 