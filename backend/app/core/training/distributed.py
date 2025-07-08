"""
분산 학습 지원 모듈
"""
import os
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

import torch
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP
from accelerate import Accelerator, DistributedDataParallelKwargs
from transformers import TrainingArguments
from loguru import logger


class DistributedBackend(str, Enum):
    """분산 학습 백엔드"""
    NCCL = "nccl"  # NVIDIA GPU
    GLOO = "gloo"  # CPU
    MPI = "mpi"    # MPI


class DistributedStrategy(str, Enum):
    """분산 학습 전략"""
    DDP = "ddp"                    # Data Parallel
    FSDP = "fsdp"                  # Fully Sharded Data Parallel
    DEEPSPEED = "deepspeed"        # DeepSpeed
    FAIRSCALE = "fairscale"        # FairScale


@dataclass
class DistributedConfig:
    """분산 학습 설정"""
    enabled: bool = False
    backend: DistributedBackend = DistributedBackend.NCCL
    strategy: DistributedStrategy = DistributedStrategy.DDP
    world_size: int = 1
    local_rank: int = -1
    master_addr: str = "localhost"
    master_port: str = "29500"
    
    # DDP 설정
    gradient_as_bucket_view: bool = True
    find_unused_parameters: bool = False
    
    # FSDP 설정
    fsdp_transformer_layer_cls_to_wrap: Optional[List[str]] = None
    fsdp_min_num_params: int = 0
    fsdp_backward_prefetch: str = "backward_pre"
    fsdp_forward_prefetch: bool = False
    fsdp_use_orig_params: bool = True
    
    # DeepSpeed 설정
    deepspeed_config_file: Optional[str] = None
    zero_stage: int = 2
    offload_optimizer: bool = False
    offload_param: bool = False
    
    # 통신 최적화
    gradient_accumulation_steps: int = 1
    gradient_checkpointing: bool = True
    mixed_precision: str = "fp16"  # no, fp16, bf16
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        config = {
            "enabled": self.enabled,
            "backend": self.backend.value,
            "strategy": self.strategy.value,
            "world_size": self.world_size,
            "local_rank": self.local_rank,
            "master_addr": self.master_addr,
            "master_port": self.master_port,
            "gradient_as_bucket_view": self.gradient_as_bucket_view,
            "find_unused_parameters": self.find_unused_parameters,
            "gradient_accumulation_steps": self.gradient_accumulation_steps,
            "gradient_checkpointing": self.gradient_checkpointing,
            "mixed_precision": self.mixed_precision
        }
        
        if self.strategy == DistributedStrategy.FSDP:
            config.update({
                "fsdp_transformer_layer_cls_to_wrap": self.fsdp_transformer_layer_cls_to_wrap,
                "fsdp_min_num_params": self.fsdp_min_num_params,
                "fsdp_backward_prefetch": self.fsdp_backward_prefetch,
                "fsdp_forward_prefetch": self.fsdp_forward_prefetch,
                "fsdp_use_orig_params": self.fsdp_use_orig_params
            })
        elif self.strategy == DistributedStrategy.DEEPSPEED:
            config.update({
                "deepspeed_config_file": self.deepspeed_config_file,
                "zero_stage": self.zero_stage,
                "offload_optimizer": self.offload_optimizer,
                "offload_param": self.offload_param
            })
        
        return config


class DistributedTrainer:
    """분산 학습 트레이너"""
    
    def __init__(self, config: DistributedConfig):
        self.config = config
        self.accelerator = None
        self.is_initialized = False
    
    def initialize(self) -> None:
        """분산 학습 환경 초기화"""
        if self.is_initialized:
            return
        
        if not self.config.enabled:
            logger.info("Distributed training is disabled")
            return
        
        # 환경 변수 설정
        os.environ["MASTER_ADDR"] = self.config.master_addr
        os.environ["MASTER_PORT"] = self.config.master_port
        
        if self.config.local_rank >= 0:
            os.environ["LOCAL_RANK"] = str(self.config.local_rank)
        
        # Accelerate 설정
        kwargs = {}
        
        if self.config.strategy == DistributedStrategy.DDP:
            ddp_kwargs = DistributedDataParallelKwargs(
                gradient_as_bucket_view=self.config.gradient_as_bucket_view,
                find_unused_parameters=self.config.find_unused_parameters
            )
            kwargs["ddp_kwargs"] = ddp_kwargs
        
        elif self.config.strategy == DistributedStrategy.FSDP:
            kwargs["fsdp_plugin"] = self._create_fsdp_plugin()
        
        elif self.config.strategy == DistributedStrategy.DEEPSPEED:
            kwargs["deepspeed_plugin"] = self._create_deepspeed_plugin()
        
        # Accelerator 초기화
        self.accelerator = Accelerator(
            mixed_precision=self.config.mixed_precision,
            gradient_accumulation_steps=self.config.gradient_accumulation_steps,
            **kwargs
        )
        
        self.is_initialized = True
        logger.info(f"Distributed training initialized with {self.config.strategy.value}")
    
    def _create_fsdp_plugin(self) -> Dict[str, Any]:
        """FSDP 플러그인 생성"""
        from accelerate import FullyShardedDataParallelPlugin
        from torch.distributed.fsdp import FullStateDictConfig, StateDictType
        
        return FullyShardedDataParallelPlugin(
            sharding_strategy="FULL_SHARD",
            backward_prefetch=self.config.fsdp_backward_prefetch,
            forward_prefetch=self.config.fsdp_forward_prefetch,
            use_orig_params=self.config.fsdp_use_orig_params,
            sync_module_states=True,
            state_dict_config=FullStateDictConfig(
                offload_to_cpu=True,
                rank0_only=True
            )
        )
    
    def _create_deepspeed_plugin(self) -> Dict[str, Any]:
        """DeepSpeed 플러그인 생성"""
        from accelerate import DeepSpeedPlugin
        
        # DeepSpeed 설정 파일이 있으면 사용
        if self.config.deepspeed_config_file and os.path.exists(self.config.deepspeed_config_file):
            with open(self.config.deepspeed_config_file, 'r') as f:
                ds_config = json.load(f)
        else:
            # 기본 DeepSpeed 설정 생성
            ds_config = self._create_default_deepspeed_config()
        
        return DeepSpeedPlugin(
            gradient_accumulation_steps=self.config.gradient_accumulation_steps,
            gradient_clipping=1.0,
            zero_stage=self.config.zero_stage,
            offload_optimizer_device="cpu" if self.config.offload_optimizer else None,
            offload_param_device="cpu" if self.config.offload_param else None,
            zero3_init_flag=self.config.zero_stage == 3,
            zero3_save_16bit_model=self.config.zero_stage == 3
        )
    
    def _create_default_deepspeed_config(self) -> Dict[str, Any]:
        """기본 DeepSpeed 설정 생성"""
        config = {
            "train_batch_size": "auto",
            "train_micro_batch_size_per_gpu": "auto",
            "gradient_accumulation_steps": self.config.gradient_accumulation_steps,
            "gradient_clipping": 1.0,
            "zero_optimization": {
                "stage": self.config.zero_stage,
                "offload_optimizer": {
                    "device": "cpu" if self.config.offload_optimizer else "none",
                    "pin_memory": True
                },
                "offload_param": {
                    "device": "cpu" if self.config.offload_param else "none",
                    "pin_memory": True
                },
                "overlap_comm": True,
                "contiguous_gradients": True,
                "sub_group_size": 1e9,
                "reduce_bucket_size": "auto",
                "stage3_prefetch_bucket_size": "auto",
                "stage3_param_persistence_threshold": "auto",
                "stage3_max_live_parameters": 1e9,
                "stage3_max_reuse_distance": 1e9,
                "stage3_gather_16bit_weights_on_model_save": True
            }
        }
        
        # Mixed precision 설정
        if self.config.mixed_precision == "fp16":
            config["fp16"] = {
                "enabled": True,
                "auto_cast": False,
                "loss_scale": 0,
                "initial_scale_power": 32,
                "loss_scale_window": 1000,
                "hysteresis": 2,
                "min_loss_scale": 1
            }
        elif self.config.mixed_precision == "bf16":
            config["bf16"] = {
                "enabled": True
            }
        
        return config
    
    def prepare_model_and_optimizer(
        self,
        model: torch.nn.Module,
        optimizer: torch.optim.Optimizer,
        scheduler: Optional[Any] = None
    ) -> tuple:
        """모델과 옵티마이저 준비"""
        if not self.is_initialized:
            self.initialize()
        
        if not self.config.enabled:
            return model, optimizer, scheduler
        
        # Gradient checkpointing 설정
        if self.config.gradient_checkpointing and hasattr(model, "gradient_checkpointing_enable"):
            model.gradient_checkpointing_enable()
        
        # Accelerator로 준비
        if scheduler:
            model, optimizer, scheduler = self.accelerator.prepare(model, optimizer, scheduler)
        else:
            model, optimizer = self.accelerator.prepare(model, optimizer)
            scheduler = None
        
        return model, optimizer, scheduler
    
    def prepare_dataloader(self, dataloader):
        """데이터로더 준비"""
        if not self.config.enabled:
            return dataloader
        
        return self.accelerator.prepare(dataloader)
    
    def backward(self, loss):
        """역전파"""
        if self.config.enabled and self.accelerator:
            self.accelerator.backward(loss)
        else:
            loss.backward()
    
    def optimizer_step(self, optimizer):
        """옵티마이저 스텝"""
        if self.config.enabled and self.accelerator:
            optimizer.step()
            optimizer.zero_grad()
        else:
            optimizer.step()
            optimizer.zero_grad()
    
    def save_checkpoint(self, output_dir: str, model: torch.nn.Module):
        """체크포인트 저장"""
        if self.config.enabled and self.accelerator:
            self.accelerator.wait_for_everyone()
            unwrapped_model = self.accelerator.unwrap_model(model)
            self.accelerator.save_model(unwrapped_model, output_dir)
        else:
            model.save_pretrained(output_dir)
    
    def load_checkpoint(self, checkpoint_path: str, model: torch.nn.Module):
        """체크포인트 로드"""
        if self.config.enabled and self.accelerator:
            self.accelerator.wait_for_everyone()
            unwrapped_model = self.accelerator.unwrap_model(model)
            unwrapped_model.load_state_dict(
                torch.load(checkpoint_path, map_location=self.accelerator.device)
            )
        else:
            model.load_state_dict(torch.load(checkpoint_path))
    
    def get_world_size(self) -> int:
        """전체 프로세스 수 반환"""
        if self.config.enabled and dist.is_initialized():
            return dist.get_world_size()
        return 1
    
    def get_rank(self) -> int:
        """현재 프로세스 랭크 반환"""
        if self.config.enabled and dist.is_initialized():
            return dist.get_rank()
        return 0
    
    def is_main_process(self) -> bool:
        """메인 프로세스 여부 확인"""
        if self.config.enabled and self.accelerator:
            return self.accelerator.is_main_process
        return True
    
    def wait_for_everyone(self):
        """모든 프로세스 동기화"""
        if self.config.enabled and self.accelerator:
            self.accelerator.wait_for_everyone()
    
    def print(self, *args, **kwargs):
        """메인 프로세스에서만 출력"""
        if self.is_main_process():
            print(*args, **kwargs)
    
    def log(self, message: str, level: str = "info"):
        """메인 프로세스에서만 로깅"""
        if self.is_main_process():
            getattr(logger, level)(message)
    
    def cleanup(self):
        """분산 학습 환경 정리"""
        if self.config.enabled and dist.is_initialized():
            dist.destroy_process_group()
        self.is_initialized = False


def create_distributed_training_args(
    base_args: TrainingArguments,
    distributed_config: DistributedConfig
) -> TrainingArguments:
    """분산 학습을 위한 TrainingArguments 생성"""
    if not distributed_config.enabled:
        return base_args
    
    # 분산 학습 관련 인자 업데이트
    base_args.local_rank = distributed_config.local_rank
    base_args.ddp_backend = distributed_config.backend.value
    base_args.ddp_find_unused_parameters = distributed_config.find_unused_parameters
    
    # Mixed precision 설정
    if distributed_config.mixed_precision == "fp16":
        base_args.fp16 = True
        base_args.bf16 = False
    elif distributed_config.mixed_precision == "bf16":
        base_args.fp16 = False
        base_args.bf16 = True
    else:
        base_args.fp16 = False
        base_args.bf16 = False
    
    # FSDP 설정
    if distributed_config.strategy == DistributedStrategy.FSDP:
        base_args.fsdp = "full_shard"
        base_args.fsdp_transformer_layer_cls_to_wrap = distributed_config.fsdp_transformer_layer_cls_to_wrap
        base_args.fsdp_min_num_params = distributed_config.fsdp_min_num_params
    
    # DeepSpeed 설정
    elif distributed_config.strategy == DistributedStrategy.DEEPSPEED:
        if distributed_config.deepspeed_config_file:
            base_args.deepspeed = distributed_config.deepspeed_config_file
        else:
            # 인라인 DeepSpeed 설정
            trainer = DistributedTrainer(distributed_config)
            base_args.deepspeed = trainer._create_default_deepspeed_config()
    
    # Gradient accumulation
    base_args.gradient_accumulation_steps = distributed_config.gradient_accumulation_steps
    base_args.gradient_checkpointing = distributed_config.gradient_checkpointing
    
    return base_args