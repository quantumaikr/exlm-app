import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
import torch
from vllm import LLM, SamplingParams
from vllm.utils import random_uuid

from app.core.config import settings

logger = logging.getLogger(__name__)

class VLLMService:
    """vLLM 기반 모델 서빙 서비스"""
    
    def __init__(self):
        self.models: Dict[str, LLM] = {}
        self.model_configs: Dict[str, Dict] = {}
        
    async def load_model(self, model_path: str, model_config: Dict[str, Any]) -> bool:
        """모델 로드"""
        try:
            if model_path in self.models:
                logger.info(f"Model {model_path} already loaded")
                return True
                
            logger.info(f"Loading model: {model_path}")
            
            # GPU 설정 자동 감지
            if not settings.is_gpu_available:
                logger.warning("GPU not available, vLLM requires GPU for optimal performance")
                return False
            
            # vLLM 모델 로드
            llm = LLM(
                model=model_path,
                trust_remote_code=True,
                dtype="half" if settings.torch_dtype == torch.float16 else "float",
                gpu_memory_utilization=model_config.get("gpu_memory_utilization", 0.9),
                max_model_len=model_config.get("max_model_len", 4096),
                quantization=model_config.get("quantization", None),
                enforce_eager=model_config.get("enforce_eager", False),
            )
            
            self.models[model_path] = llm
            self.model_configs[model_path] = model_config
            
            logger.info(f"Model {model_path} loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load model {model_path}: {e}")
            return False
    
    async def unload_model(self, model_path: str) -> bool:
        """모델 언로드"""
        try:
            if model_path in self.models:
                del self.models[model_path]
                del self.model_configs[model_path]
                logger.info(f"Model {model_path} unloaded")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to unload model {model_path}: {e}")
            return False
    
    async def generate(
        self,
        model_path: str,
        prompts: List[str],
        sampling_params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """텍스트 생성"""
        try:
            if model_path not in self.models:
                raise ValueError(f"Model {model_path} not loaded")
            
            llm = self.models[model_path]
            
            # 기본 샘플링 파라미터
            default_params = {
                "temperature": 0.7,
                "top_p": 0.9,
                "max_tokens": 512,
                "stop": None,
            }
            
            if sampling_params:
                default_params.update(sampling_params)
            
            # SamplingParams 객체 생성
            params = SamplingParams(**default_params)
            
            # 생성 실행
            outputs = llm.generate(prompts, params)
            
            # 결과 포맷팅
            results = []
            for output in outputs:
                result = {
                    "request_id": output.request_id,
                    "prompt": output.prompt,
                    "generated_text": output.outputs[0].text,
                    "finish_reason": output.outputs[0].finish_reason,
                    "usage": {
                        "prompt_tokens": output.outputs[0].token_ids[0],
                        "completion_tokens": len(output.outputs[0].token_ids),
                        "total_tokens": len(output.outputs[0].token_ids) + len(output.outputs[0].token_ids[0])
                    }
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise
    
    async def get_model_info(self, model_path: str) -> Optional[Dict[str, Any]]:
        """모델 정보 조회"""
        try:
            if model_path not in self.models:
                return None
            
            llm = self.models[model_path]
            config = self.model_configs[model_path]
            
            info = {
                "model_path": model_path,
                "model_config": config,
                "device": settings.device,
                "dtype": str(settings.torch_dtype),
                "max_model_len": llm.llm_engine.model_config.max_model_len,
                "block_size": llm.llm_engine.model_config.block_size,
                "gpu_memory_utilization": config.get("gpu_memory_utilization", 0.9),
            }
            
            if settings.is_gpu_available:
                info.update({
                    "gpu_count": torch.cuda.device_count(),
                    "gpu_memory": {
                        f"gpu_{i}": torch.cuda.get_device_properties(i).total_memory / 1024**3
                        for i in range(torch.cuda.device_count())
                    }
                })
            
            return info
            
        except Exception as e:
            logger.error(f"Failed to get model info: {e}")
            return None
    
    async def list_loaded_models(self) -> List[str]:
        """로드된 모델 목록 반환"""
        return list(self.models.keys())
    
    async def health_check(self) -> Dict[str, Any]:
        """헬스 체크"""
        return {
            "status": "healthy",
            "loaded_models": len(self.models),
            "gpu_available": settings.is_gpu_available,
            "device": settings.device,
            "models": list(self.models.keys())
        }

# 전역 서비스 인스턴스
vllm_service = VLLMService() 