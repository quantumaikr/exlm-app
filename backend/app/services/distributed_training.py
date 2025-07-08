"""
분산 학습 관리 서비스
"""
import os
import json
import asyncio
import subprocess
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path

from loguru import logger
import torch

from app.core.config import settings
from app.core.training.distributed import (
    DistributedConfig, DistributedStrategy, DistributedBackend,
    DistributedTrainer
)
from app.models.training import TrainingJob
from app.core.redis import get_redis


class DistributedTrainingService:
    """분산 학습 관리 서비스"""
    
    def __init__(self):
        self.active_jobs: Dict[str, Dict[str, Any]] = {}
        self.node_registry: Dict[str, Dict[str, Any]] = {}
    
    async def get_available_nodes(self) -> List[Dict[str, Any]]:
        """사용 가능한 노드 목록 조회"""
        redis = await get_redis()
        nodes = []
        
        # Redis에서 등록된 노드 정보 조회
        node_keys = await redis.keys("distributed_node:*")
        
        for key in node_keys:
            node_info = await redis.get(key)
            if node_info:
                node_data = json.loads(node_info)
                # 노드 상태 확인
                if await self._check_node_health(node_data["address"]):
                    nodes.append(node_data)
        
        return nodes
    
    async def register_node(
        self,
        node_id: str,
        address: str,
        gpu_count: int,
        gpu_memory: int,
        cpu_count: int,
        memory: int,
        capabilities: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """분산 학습 노드 등록"""
        node_info = {
            "node_id": node_id,
            "address": address,
            "gpu_count": gpu_count,
            "gpu_memory": gpu_memory,
            "cpu_count": cpu_count,
            "memory": memory,
            "capabilities": capabilities or {},
            "status": "active",
            "registered_at": datetime.utcnow().isoformat(),
            "last_heartbeat": datetime.utcnow().isoformat()
        }
        
        # Redis에 노드 정보 저장
        redis = await get_redis()
        await redis.setex(
            f"distributed_node:{node_id}",
            3600,  # 1시간 TTL
            json.dumps(node_info)
        )
        
        self.node_registry[node_id] = node_info
        logger.info(f"Registered distributed node: {node_id}")
        
        return node_info
    
    async def unregister_node(self, node_id: str) -> None:
        """노드 등록 해제"""
        redis = await get_redis()
        await redis.delete(f"distributed_node:{node_id}")
        
        if node_id in self.node_registry:
            del self.node_registry[node_id]
        
        logger.info(f"Unregistered distributed node: {node_id}")
    
    async def update_node_heartbeat(self, node_id: str) -> None:
        """노드 하트비트 업데이트"""
        redis = await get_redis()
        node_key = f"distributed_node:{node_id}"
        
        node_info = await redis.get(node_key)
        if node_info:
            node_data = json.loads(node_info)
            node_data["last_heartbeat"] = datetime.utcnow().isoformat()
            
            await redis.setex(
                node_key,
                3600,  # 1시간 TTL 갱신
                json.dumps(node_data)
            )
    
    async def _check_node_health(self, address: str) -> bool:
        """노드 상태 확인"""
        try:
            # 간단한 ping 테스트
            host = address.split(":")[0]
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "1", host],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Failed to check node health: {e}")
            return False
    
    def create_distributed_config(
        self,
        strategy: str,
        world_size: int,
        nodes: List[Dict[str, Any]],
        **kwargs
    ) -> DistributedConfig:
        """분산 학습 설정 생성"""
        # 기본 설정
        config = DistributedConfig(
            enabled=True,
            strategy=DistributedStrategy(strategy),
            world_size=world_size,
            backend=DistributedBackend.NCCL if torch.cuda.is_available() else DistributedBackend.GLOO
        )
        
        # 마스터 노드 설정
        if nodes:
            master_node = nodes[0]
            config.master_addr = master_node["address"].split(":")[0]
            config.master_port = master_node["address"].split(":")[1] if ":" in master_node["address"] else "29500"
        
        # 추가 설정 적용
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        return config
    
    async def launch_distributed_job(
        self,
        job_id: str,
        script_path: str,
        config: DistributedConfig,
        nodes: List[Dict[str, Any]],
        args: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """분산 학습 작업 실행"""
        launch_info = {
            "job_id": job_id,
            "script_path": script_path,
            "config": config.to_dict(),
            "nodes": nodes,
            "processes": [],
            "started_at": datetime.utcnow().isoformat()
        }
        
        # torchrun 명령어 구성
        base_cmd = [
            "torchrun",
            "--nproc_per_node", str(config.world_size // len(nodes)),
            "--nnodes", str(len(nodes)),
            "--master_addr", config.master_addr,
            "--master_port", config.master_port,
        ]
        
        # 각 노드에서 프로세스 실행
        for i, node in enumerate(nodes):
            node_cmd = base_cmd + [
                "--node_rank", str(i),
                script_path
            ]
            
            if args:
                node_cmd.extend(args)
            
            # 원격 노드인 경우 SSH로 실행
            if node["address"] != "localhost":
                ssh_cmd = ["ssh", node["address"]] + node_cmd
                process = subprocess.Popen(
                    ssh_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            else:
                # 로컬 실행
                process = subprocess.Popen(
                    node_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env={**os.environ, "CUDA_VISIBLE_DEVICES": ",".join(map(str, range(node["gpu_count"])))}
                )
            
            launch_info["processes"].append({
                "node_id": node["node_id"],
                "pid": process.pid,
                "command": " ".join(node_cmd)
            })
        
        # 활성 작업 목록에 추가
        self.active_jobs[job_id] = launch_info
        
        # Redis에 작업 정보 저장
        redis = await get_redis()
        await redis.setex(
            f"distributed_job:{job_id}",
            86400,  # 24시간 TTL
            json.dumps(launch_info)
        )
        
        logger.info(f"Launched distributed job: {job_id}")
        return launch_info
    
    async def monitor_distributed_job(
        self,
        job_id: str
    ) -> Dict[str, Any]:
        """분산 학습 작업 모니터링"""
        if job_id not in self.active_jobs:
            # Redis에서 조회
            redis = await get_redis()
            job_info = await redis.get(f"distributed_job:{job_id}")
            if job_info:
                self.active_jobs[job_id] = json.loads(job_info)
            else:
                raise ValueError(f"Job {job_id} not found")
        
        job_info = self.active_jobs[job_id]
        status = {
            "job_id": job_id,
            "started_at": job_info["started_at"],
            "nodes": job_info["nodes"],
            "processes": []
        }
        
        # 각 프로세스 상태 확인
        for proc_info in job_info["processes"]:
            try:
                # 프로세스 상태 확인 (psutil 사용 권장)
                pid = proc_info["pid"]
                # 여기서는 간단히 구현
                try:
                    os.kill(pid, 0)  # 프로세스 존재 확인
                    proc_status = "running"
                except ProcessLookupError:
                    proc_status = "completed"
                
                status["processes"].append({
                    "node_id": proc_info["node_id"],
                    "pid": pid,
                    "status": proc_status
                })
            except Exception as e:
                logger.error(f"Failed to check process status: {e}")
        
        # 전체 작업 상태 판단
        running_count = sum(1 for p in status["processes"] if p["status"] == "running")
        if running_count == 0:
            status["status"] = "completed"
        elif running_count < len(status["processes"]):
            status["status"] = "partial_failure"
        else:
            status["status"] = "running"
        
        return status
    
    async def terminate_distributed_job(
        self,
        job_id: str
    ) -> None:
        """분산 학습 작업 종료"""
        if job_id not in self.active_jobs:
            return
        
        job_info = self.active_jobs[job_id]
        
        # 각 프로세스 종료
        for proc_info in job_info["processes"]:
            try:
                pid = proc_info["pid"]
                os.kill(pid, 15)  # SIGTERM
                logger.info(f"Terminated process {pid} for job {job_id}")
            except Exception as e:
                logger.error(f"Failed to terminate process: {e}")
        
        # 정리
        del self.active_jobs[job_id]
        
        # Redis에서 제거
        redis = await get_redis()
        await redis.delete(f"distributed_job:{job_id}")
    
    async def get_distributed_metrics(
        self,
        job_id: str
    ) -> Dict[str, Any]:
        """분산 학습 메트릭 조회"""
        redis = await get_redis()
        
        # 각 노드의 메트릭 수집
        metrics = {
            "job_id": job_id,
            "nodes": {}
        }
        
        # 작업 정보 조회
        job_info = await redis.get(f"distributed_job:{job_id}")
        if not job_info:
            return metrics
        
        job_data = json.loads(job_info)
        
        # 각 노드별 메트릭 조회
        for node in job_data["nodes"]:
            node_id = node["node_id"]
            node_metrics_key = f"distributed_metrics:{job_id}:{node_id}"
            
            node_metrics = await redis.lrange(node_metrics_key, 0, -1)
            if node_metrics:
                metrics["nodes"][node_id] = [
                    json.loads(m) for m in node_metrics
                ]
        
        # 집계된 메트릭 계산
        if metrics["nodes"]:
            all_metrics = []
            for node_metrics in metrics["nodes"].values():
                all_metrics.extend(node_metrics)
            
            if all_metrics:
                # 최신 메트릭 기준으로 평균 계산
                latest_metrics = {}
                for m in all_metrics:
                    for key, value in m.get("metrics", {}).items():
                        if isinstance(value, (int, float)):
                            if key not in latest_metrics:
                                latest_metrics[key] = []
                            latest_metrics[key].append(value)
                
                # 평균 계산
                aggregated = {}
                for key, values in latest_metrics.items():
                    aggregated[key] = sum(values) / len(values)
                
                metrics["aggregated"] = aggregated
        
        return metrics
    
    def estimate_distributed_speedup(
        self,
        model_size: int,
        dataset_size: int,
        world_size: int,
        strategy: DistributedStrategy
    ) -> Dict[str, float]:
        """분산 학습 속도 향상 추정"""
        # 이론적 속도 향상 계산
        communication_overhead = 0.1  # 10% 통신 오버헤드 가정
        
        if strategy == DistributedStrategy.DDP:
            # DDP: 거의 선형 확장
            speedup = world_size * (1 - communication_overhead)
            memory_per_gpu = model_size
        
        elif strategy == DistributedStrategy.FSDP:
            # FSDP: 모델 샤딩으로 메모리 절약
            speedup = world_size * (1 - communication_overhead * 1.5)
            memory_per_gpu = model_size / world_size + (model_size * 0.1)  # 10% 오버헤드
        
        elif strategy == DistributedStrategy.DEEPSPEED:
            # DeepSpeed: ZeRO 최적화
            speedup = world_size * (1 - communication_overhead * 0.5)
            memory_per_gpu = model_size / (world_size * 2)  # ZeRO-2 가정
        
        else:
            speedup = world_size * 0.8
            memory_per_gpu = model_size
        
        return {
            "estimated_speedup": speedup,
            "memory_per_gpu_mb": memory_per_gpu / (1024 * 1024),
            "efficiency": speedup / world_size,
            "recommended_batch_size": int(32 * world_size * 0.8)
        }
    
    async def create_distributed_launch_script(
        self,
        job_id: str,
        training_script: str,
        config: DistributedConfig,
        output_dir: str
    ) -> str:
        """분산 학습 실행 스크립트 생성"""
        script_content = f"""#!/bin/bash
# Distributed training launch script for job {job_id}
# Generated at {datetime.utcnow().isoformat()}

# Environment setup
export MASTER_ADDR={config.master_addr}
export MASTER_PORT={config.master_port}
export WORLD_SIZE={config.world_size}

# NCCL settings for better performance
export NCCL_DEBUG=INFO
export NCCL_SOCKET_IFNAME=eth0
export NCCL_IB_DISABLE=1

# Launch command
torchrun \\
    --nproc_per_node={config.world_size} \\
    --nnodes=1 \\
    --node_rank=0 \\
    --master_addr=$MASTER_ADDR \\
    --master_port=$MASTER_PORT \\
    {training_script} \\
    --output_dir={output_dir} \\
    --distributed_strategy={config.strategy.value} \\
    --mixed_precision={config.mixed_precision}
"""
        
        # 스크립트 파일 저장
        script_path = Path(output_dir) / f"launch_distributed_{job_id}.sh"
        script_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(script_path, "w") as f:
            f.write(script_content)
        
        # 실행 권한 부여
        os.chmod(script_path, 0o755)
        
        logger.info(f"Created distributed launch script: {script_path}")
        return str(script_path)


# 싱글톤 인스턴스
distributed_training_service = DistributedTrainingService()