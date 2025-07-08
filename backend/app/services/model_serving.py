"""
vLLM 기반 모델 서빙 서비스
"""
import asyncio
import json
import os
import subprocess
import time
from typing import Dict, Any, List, Optional
from pathlib import Path
import aiohttp
from datetime import datetime

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.serving import (
    ServingConfig,
    ServingStatus,
    GenerationRequest,
    ModelServingInfo,
    ServingMetrics
)

logger = get_logger(__name__)


class ModelServingService:
    """모델 서빙 서비스"""
    
    def __init__(self):
        self.serving_models: Dict[str, Dict[str, Any]] = {}
        self.vllm_processes: Dict[str, subprocess.Popen] = {}
        self.base_port = 8001
        
    async def start_serving(
        self,
        model_id: str,
        model_path: str,
        config: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """모델 서빙 시작"""
        try:
            # 모델 경로 확인
            if not os.path.exists(model_path):
                raise ValueError(f"Model path does not exist: {model_path}")
            
            # 포트 할당
            port = await self._get_available_port()
            
            # vLLM 서버 시작
            process = await self._start_vllm_server(
                model_id=model_id,
                model_path=model_path,
                port=port,
                config=config
            )
            
            # 서빙 정보 저장
            serving_info = {
                "model_id": model_id,
                "status": ServingStatus.STARTING,
                "endpoint_url": f"http://localhost:{port}",
                "config": ServingConfig(**config),
                "started_at": datetime.utcnow(),
                "user_id": user_id,
                "port": port,
                "process": process
            }
            
            self.serving_models[model_id] = serving_info
            self.vllm_processes[model_id] = process
            
            # 서버 시작 대기
            await self._wait_for_server_ready(port)
            
            # 상태 업데이트
            serving_info["status"] = ServingStatus.RUNNING
            
            logger.info(f"Started serving model {model_id} on port {port}")
            return serving_info
            
        except Exception as e:
            logger.error(f"Failed to start serving model {model_id}: {str(e)}")
            await self.stop_serving(model_id)
            raise
    
    async def stop_serving(self, model_id: str) -> None:
        """모델 서빙 중지"""
        try:
            if model_id in self.vllm_processes:
                process = self.vllm_processes[model_id]
                process.terminate()
                process.wait(timeout=10)
                del self.vllm_processes[model_id]
            
            if model_id in self.serving_models:
                self.serving_models[model_id]["status"] = ServingStatus.STOPPED
                del self.serving_models[model_id]
            
            logger.info(f"Stopped serving model {model_id}")
            
        except Exception as e:
            logger.error(f"Failed to stop serving model {model_id}: {str(e)}")
    
    async def get_serving_status(self, model_id: str) -> Optional[Dict[str, Any]]:
        """서빙 상태 조회"""
        if model_id not in self.serving_models:
            return None
        
        serving_info = self.serving_models[model_id].copy()
        
        # 프로세스 상태 확인
        if model_id in self.vllm_processes:
            process = self.vllm_processes[model_id]
            if process.poll() is not None:
                serving_info["status"] = ServingStatus.ERROR
                serving_info["error_message"] = "Process terminated unexpectedly"
        
        return serving_info
    
    async def generate_text(
        self,
        model_id: str,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stop: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """텍스트 생성"""
        if model_id not in self.serving_models:
            raise ValueError(f"Model {model_id} is not serving")
        
        serving_info = self.serving_models[model_id]
        if serving_info["status"] != ServingStatus.RUNNING:
            raise ValueError(f"Model {model_id} is not running")
        
        endpoint_url = serving_info["endpoint_url"]
        
        # vLLM API 호출
        payload = {
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "stream": False
        }
        
        if stop:
            payload["stop"] = stop
        
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{endpoint_url}/v1/completions",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status != 200:
                        raise ValueError(f"API call failed: {response.status}")
                    
                    result = await response.json()
                    latency = time.time() - start_time
                    
                    return {
                        "text": result["choices"][0]["text"],
                        "tokens_used": result["usage"]["total_tokens"],
                        "finish_reason": result["choices"][0]["finish_reason"],
                        "latency": latency
                    }
                    
        except Exception as e:
            logger.error(f"Failed to generate text for model {model_id}: {str(e)}")
            raise
    
    async def batch_generate_text(
        self,
        model_id: str,
        requests: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """배치 텍스트 생성"""
        if model_id not in self.serving_models:
            raise ValueError(f"Model {model_id} is not serving")
        
        serving_info = self.serving_models[model_id]
        if serving_info["status"] != ServingStatus.RUNNING:
            raise ValueError(f"Model {model_id} is not running")
        
        endpoint_url = serving_info["endpoint_url"]
        
        # 배치 요청 준비
        prompts = [req["prompt"] for req in requests]
        max_tokens = requests[0].get("max_tokens", 512)
        temperature = requests[0].get("temperature", 0.7)
        top_p = requests[0].get("top_p", 0.9)
        
        payload = {
            "prompt": prompts,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "stream": False
        }
        
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{endpoint_url}/v1/completions",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    if response.status != 200:
                        raise ValueError(f"API call failed: {response.status}")
                    
                    result = await response.json()
                    latency = time.time() - start_time
                    
                    responses = []
                    for i, choice in enumerate(result["choices"]):
                        responses.append({
                            "text": choice["text"],
                            "tokens_used": result["usage"]["total_tokens"] // len(prompts),
                            "finish_reason": choice["finish_reason"],
                            "latency": latency
                        })
                    
                    return responses
                    
        except Exception as e:
            logger.error(f"Failed to batch generate text for model {model_id}: {str(e)}")
            raise
    
    async def list_serving_models(self, project_ids: List[str] = None) -> List[Dict[str, Any]]:
        """서빙 중인 모델 목록 조회"""
        models = []
        for model_id, serving_info in self.serving_models.items():
            if project_ids is None or serving_info.get("project_id") in project_ids:
                models.append(serving_info)
        return models
    
    async def get_model_metrics(self, model_id: str) -> Dict[str, Any]:
        """모델별 메트릭 조회"""
        if model_id not in self.serving_models:
            raise ValueError(f"Model {model_id} is not serving")
        
        # 실제 구현에서는 vLLM의 메트릭 엔드포인트 사용
        return {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_latency": 0.0,
            "tokens_per_second": 0.0,
            "gpu_memory_used": 0.0,
            "gpu_utilization": 0.0
        }
    
    async def get_overall_metrics(self) -> Dict[str, Any]:
        """전체 메트릭 조회"""
        total_models = len(self.serving_models)
        running_models = sum(
            1 for info in self.serving_models.values()
            if info["status"] == ServingStatus.RUNNING
        )
        
        return {
            "total_serving_models": total_models,
            "running_models": running_models,
            "stopped_models": total_models - running_models
        }
    
    async def _get_available_port(self) -> int:
        """사용 가능한 포트 찾기"""
        used_ports = {info["port"] for info in self.serving_models.values()}
        
        for port in range(self.base_port, self.base_port + 100):
            if port not in used_ports:
                return port
        
        raise RuntimeError("No available ports")
    
    async def _start_vllm_server(
        self,
        model_id: str,
        model_path: str,
        port: int,
        config: Dict[str, Any]
    ) -> subprocess.Popen:
        """vLLM 서버 시작"""
        cmd = [
            "python", "-m", "vllm.entrypoints.openai.api_server",
            "--model", model_path,
            "--port", str(port),
            "--max-model-len", str(config.get("max_model_len", 2048)),
            "--gpu-memory-utilization", str(config.get("gpu_memory_utilization", 0.9)),
            "--max-num-batched-tokens", str(config.get("max_num_batched_tokens", 4096)),
            "--max-num-seqs", str(config.get("max_num_seqs", 256)),
            "--tensor-parallel-size", str(config.get("tensor_parallel_size", 1)),
            "--trust-remote-code" if config.get("trust_remote_code", False) else "",
            "--dtype", config.get("dtype", "auto")
        ]
        
        # None 값 제거
        cmd = [arg for arg in cmd if arg]
        
        # 환경 변수 설정
        env = os.environ.copy()
        env["CUDA_VISIBLE_DEVICES"] = "0"  # GPU 설정
        
        process = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        return process
    
    async def _wait_for_server_ready(self, port: int, timeout: int = 60) -> None:
        """서버 준비 대기"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"http://localhost:{port}/v1/models",
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        if response.status == 200:
                            return
            except:
                pass
            
            await asyncio.sleep(1)
        
        raise TimeoutError(f"Server not ready within {timeout} seconds")


# 싱글톤 인스턴스
model_serving_service = ModelServingService() 