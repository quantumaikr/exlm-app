from celery import Task
from typing import Dict, Any, List, Optional
import asyncio
from uuid import UUID
import logging
import json
import os
from pathlib import Path
from datetime import datetime

from app.core.celery_app import celery_app
from app.core.database import async_session_maker
from app.core.config import settings
from app.models.dataset import Dataset, DatasetStatus
from app.core.llm_clients import get_llm_client, LLMProvider
from app.core.prompt_template import template_engine
from app.core.websocket import manager
from app.core.quality_filter import quality_filter
from sqlalchemy import select

logger = logging.getLogger(__name__)


class DataGenerationTask(Task):
    """Task for generating synthetic data"""
    
    def on_success(self, retval, task_id, args, kwargs):
        """Success callback"""
        dataset_id = kwargs.get("dataset_id")
        if dataset_id:
            asyncio.run(update_dataset_status(dataset_id, DatasetStatus.READY, retval))
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Failure callback"""
        dataset_id = kwargs.get("dataset_id")
        if dataset_id:
            asyncio.run(update_dataset_status(
                dataset_id, 
                DatasetStatus.FAILED, 
                {"error": str(exc)}
            ))


async def update_dataset_status(dataset_id: str, status: DatasetStatus, result: Dict[str, Any] = None):
    """Update dataset status in database"""
    async with async_session_maker() as session:
        stmt = select(Dataset).where(Dataset.id == UUID(dataset_id))
        result_db = await session.execute(stmt)
        dataset = result_db.scalar_one_or_none()
        
        if dataset:
            dataset.status = status
            if result and status == DatasetStatus.READY:
                dataset.size = result.get("num_samples", 0)
                dataset.file_path = result.get("file_path")
                dataset.statistics = result.get("statistics", {})
            
            await session.commit()
            
            # Send WebSocket notification
            await manager.broadcast({
                "type": f"dataset_{status.value}",
                "data": {
                    "dataset_id": dataset_id,
                    "status": status,
                    "result": result
                }
            })


@celery_app.task(base=DataGenerationTask, bind=True, name="generate_dataset")
def generate_dataset(self, dataset_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate synthetic dataset using LLM APIs
    
    Args:
        dataset_id: UUID of the dataset
        config: Generation configuration
    
    Returns:
        Dictionary with generation results
    """
    try:
        logger.info(f"Starting data generation for dataset {dataset_id}")
        
        # Update status to processing
        asyncio.run(update_dataset_status(dataset_id, DatasetStatus.PROCESSING))
        
        # Extract configuration
        provider = config.get("provider", "openai")
        model = config.get("model", "gpt-3.5-turbo")
        template_id = config.get("template_id", "instruction_following")
        template_vars = config.get("template_vars", {})
        num_samples = config.get("num_samples", 100)
        temperature = config.get("temperature", 0.7)
        max_tokens = config.get("max_tokens", 512)
        diversity_penalty = config.get("diversity_penalty", 0.0)
        
        # Initialize LLM client
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            llm_client = get_llm_client(provider)
        except Exception as e:
            logger.error(f"Failed to initialize LLM client: {e}")
            raise
        
        generated_samples = []
        failed_samples = 0
        total_tokens = 0
        
        # Get prompt template
        template = template_engine.get_template(template_id)
        if not template:
            # Use custom template if provided
            custom_template = config.get("custom_template")
            if not custom_template:
                raise ValueError(f"Template {template_id} not found and no custom template provided")
            template_str = custom_template
        else:
            template_str = template.template
        
        # Generate samples
        for i in range(num_samples):
            self.update_state(
                state="PROGRESS",
                meta={
                    "current": i + 1,
                    "total": num_samples,
                    "status": f"Generating sample {i + 1}/{num_samples}",
                    "failed": failed_samples
                }
            )
            
            try:
                # Prepare prompt
                current_vars = template_vars.copy()
                current_vars["sample_index"] = i + 1
                
                # If using instruction following, generate diverse instructions
                if template_id == "instruction_following" and "instruction" not in current_vars:
                    # Generate instruction using a meta-prompt
                    meta_prompt = f"Generate a unique and specific instruction for an AI assistant. Make it different from previous ones. Instruction #{i+1}:"
                    
                    instruction_response = loop.run_until_complete(
                        llm_client.generate(
                            prompt=meta_prompt,
                            model=model,
                            max_tokens=100,
                            temperature=temperature + diversity_penalty
                        )
                    )
                    
                    current_vars["instruction"] = instruction_response.text.strip()
                    total_tokens += instruction_response.usage["total_tokens"]
                
                # Render prompt
                prompt = template_engine.render_string(template_str, current_vars)
                
                # Generate response
                response = loop.run_until_complete(
                    llm_client.generate(
                        prompt=prompt,
                        model=model,
                        max_tokens=max_tokens,
                        temperature=temperature
                    )
                )
                
                total_tokens += response.usage["total_tokens"]
                
                # Parse and structure the sample
                sample = {
                    "index": i + 1,
                    "generated_at": datetime.utcnow().isoformat(),
                    "provider": provider,
                    "model": model,
                    "temperature": temperature,
                    "prompt_template": template_id,
                    "variables": current_vars,
                    "response": response.text.strip(),
                    "tokens_used": response.usage["total_tokens"]
                }
                
                # For instruction following, structure the data
                if template_id == "instruction_following":
                    sample["instruction"] = current_vars.get("instruction", "")
                    sample["output"] = response.text.strip()
                
                generated_samples.append(sample)
                
            except Exception as e:
                logger.error(f"Failed to generate sample {i + 1}: {e}")
                failed_samples += 1
                continue
        
        # Apply quality filtering if enabled
        filtering_enabled = config.get("enable_quality_filtering", True)
        if filtering_enabled and generated_samples:
            filter_config = config.get("quality_filter_config", {})
            
            self.update_state(
                state="PROGRESS",
                meta={
                    "current": num_samples,
                    "total": num_samples,
                    "status": "Applying quality filtering",
                    "failed": failed_samples
                }
            )
            
            try:
                filtered_samples, filter_stats = quality_filter.filter_samples(
                    generated_samples,
                    filter_config
                )
                
                logger.info(f"Quality filtering: {len(generated_samples)} -> {len(filtered_samples)} samples")
                
                # Use filtered samples for final output
                final_samples = filtered_samples
                
                # Add filtering statistics to overall stats
                filter_statistics = filter_stats
                
            except Exception as e:
                logger.error(f"Quality filtering failed: {e}")
                # Use original samples if filtering fails
                final_samples = generated_samples
                filter_statistics = {"error": str(e)}
        else:
            final_samples = generated_samples
            filter_statistics = {"enabled": False}
        
        # Save generated data to file
        output_dir = Path(settings.UPLOAD_DIR) / "datasets" / dataset_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save in multiple formats
        # JSON format (filtered)
        json_file = output_dir / "generated_data.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(final_samples, f, ensure_ascii=False, indent=2)
        
        # JSONL format (for training)
        jsonl_file = output_dir / "generated_data.jsonl"
        with open(jsonl_file, "w", encoding="utf-8") as f:
            for sample in final_samples:
                f.write(json.dumps(sample, ensure_ascii=False) + "\n")
        
        # Save raw unfiltered data for reference
        if filtering_enabled and len(final_samples) < len(generated_samples):
            raw_json_file = output_dir / "raw_generated_data.json"
            with open(raw_json_file, "w", encoding="utf-8") as f:
                json.dump(generated_samples, f, ensure_ascii=False, indent=2)
        
        # Calculate statistics
        statistics = {
            "num_samples": len(generated_samples),
            "filtered_samples": len(final_samples),
            "failed_samples": failed_samples,
            "success_rate": len(generated_samples) / num_samples if num_samples > 0 else 0,
            "filter_rate": 1 - (len(final_samples) / len(generated_samples)) if generated_samples else 0,
            "total_tokens": total_tokens,
            "avg_tokens_per_sample": total_tokens / len(generated_samples) if generated_samples else 0,
            "provider": provider,
            "model": model,
            "template_id": template_id,
            "generation_time": datetime.utcnow().isoformat(),
            "quality_filtering": filter_statistics
        }
        
        # Calculate content statistics
        if final_samples:
            if template_id == "instruction_following":
                statistics["avg_instruction_length"] = sum(
                    len(s.get("instruction", "")) for s in final_samples
                ) / len(final_samples)
                statistics["avg_output_length"] = sum(
                    len(s.get("output", "")) for s in final_samples
                ) / len(final_samples)
            else:
                statistics["avg_response_length"] = sum(
                    len(s.get("response", "")) for s in final_samples
                ) / len(final_samples)
        
        result = {
            "num_samples": len(final_samples),
            "original_samples": len(generated_samples),
            "file_path": str(json_file),
            "files": {
                "json": str(json_file),
                "jsonl": str(jsonl_file)
            },
            "statistics": statistics
        }
        
        # Add raw data file if filtering was applied
        if filtering_enabled and len(final_samples) < len(generated_samples):
            result["files"]["raw_json"] = str(raw_json_file)
        
        logger.info(f"Data generation completed for dataset {dataset_id}")
        return result
        
    except Exception as e:
        logger.error(f"Data generation failed for dataset {dataset_id}: {str(e)}")
        raise
    finally:
        if 'loop' in locals():
            loop.close()


@celery_app.task(name="augment_dataset")
def augment_dataset(dataset_id: str, augmentation_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Augment existing dataset with variations
    
    Args:
        dataset_id: UUID of the dataset
        augmentation_config: Augmentation configuration
    
    Returns:
        Dictionary with augmentation results
    """
    logger.info(f"Augmenting dataset {dataset_id}")
    
    try:
        # Load existing dataset
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Get dataset info
        dataset = loop.run_until_complete(get_dataset_info(dataset_id))
        if not dataset or not dataset.file_path:
            raise ValueError(f"Dataset {dataset_id} not found or has no file")
        
        # Load data
        with open(dataset.file_path, "r", encoding="utf-8") as f:
            if dataset.file_path.endswith(".jsonl"):
                original_data = [json.loads(line) for line in f]
            else:
                original_data = json.load(f)
        
        # Augmentation configuration
        methods = augmentation_config.get("methods", ["paraphrase"])
        augmentation_factor = augmentation_config.get("factor", 2)
        provider = augmentation_config.get("provider", "openai")
        model = augmentation_config.get("model", "gpt-3.5-turbo")
        
        llm_client = get_llm_client(provider)
        augmented_samples = []
        
        for idx, sample in enumerate(original_data):
            # Generate augmentations for each sample
            for aug_idx in range(augmentation_factor - 1):
                if "paraphrase" in methods:
                    # Paraphrase the instruction/text
                    if "instruction" in sample:
                        paraphrase_prompt = f"Paraphrase the following instruction while keeping the same meaning:\n\n{sample['instruction']}"
                        
                        response = loop.run_until_complete(
                            llm_client.generate(
                                prompt=paraphrase_prompt,
                                model=model,
                                max_tokens=150,
                                temperature=0.7
                            )
                        )
                        
                        augmented_sample = sample.copy()
                        augmented_sample["instruction"] = response.text.strip()
                        augmented_sample["augmentation_method"] = "paraphrase"
                        augmented_sample["original_index"] = idx
                        augmented_samples.append(augmented_sample)
        
        # Combine original and augmented data
        all_samples = original_data + augmented_samples
        
        # Save augmented dataset
        output_dir = Path(settings.UPLOAD_DIR) / "datasets" / dataset_id
        augmented_file = output_dir / "augmented_data.json"
        
        with open(augmented_file, "w", encoding="utf-8") as f:
            json.dump(all_samples, f, ensure_ascii=False, indent=2)
        
        result = {
            "original_samples": len(original_data),
            "augmented_samples": len(augmented_samples),
            "total_samples": len(all_samples),
            "augmentation_methods": methods,
            "augmentation_factor": augmentation_factor,
            "file_path": str(augmented_file)
        }
        
        logger.info(f"Dataset augmentation completed for {dataset_id}")
        return result
        
    except Exception as e:
        logger.error(f"Dataset augmentation failed for {dataset_id}: {str(e)}")
        raise
    finally:
        if 'loop' in locals():
            loop.close()


@celery_app.task(name="filter_dataset_quality")
def filter_dataset_quality(dataset_id: str, filter_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply quality filtering to an existing dataset
    
    Args:
        dataset_id: UUID of the dataset
        filter_config: Quality filtering configuration
    
    Returns:
        Dictionary with filtering results
    """
    try:
        logger.info(f"Starting quality filtering for dataset {dataset_id}")
        
        # Load existing dataset
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            dataset = loop.run_until_complete(get_dataset_info(dataset_id))
            if not dataset or not dataset.file_path:
                raise ValueError(f"Dataset {dataset_id} not found or has no file")
            
            # Load data
            with open(dataset.file_path, "r", encoding="utf-8") as f:
                if dataset.file_path.endswith(".jsonl"):
                    original_data = [json.loads(line) for line in f]
                else:
                    original_data = json.load(f)
            
            # Apply quality filtering
            filtered_data, filter_stats = quality_filter.filter_samples(
                original_data,
                filter_config
            )
            
            # Save filtered dataset
            output_dir = Path(settings.UPLOAD_DIR) / "datasets" / dataset_id
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Save filtered data
            filtered_file = output_dir / "filtered_data.json"
            with open(filtered_file, "w", encoding="utf-8") as f:
                json.dump(filtered_data, f, ensure_ascii=False, indent=2)
            
            # Save JSONL format
            filtered_jsonl_file = output_dir / "filtered_data.jsonl"
            with open(filtered_jsonl_file, "w", encoding="utf-8") as f:
                for sample in filtered_data:
                    f.write(json.dumps(sample, ensure_ascii=False) + "\n")
            
            # Update dataset in database
            loop.run_until_complete(update_dataset_status(
                dataset_id,
                DatasetStatus.READY,
                {
                    "num_samples": len(filtered_data),
                    "file_path": str(filtered_file),
                    "statistics": filter_stats
                }
            ))
            
            result = {
                "original_samples": len(original_data),
                "filtered_samples": len(filtered_data),
                "filter_rate": 1 - (len(filtered_data) / max(len(original_data), 1)),
                "file_path": str(filtered_file),
                "files": {
                    "json": str(filtered_file),
                    "jsonl": str(filtered_jsonl_file)
                },
                "statistics": filter_stats
            }
            
            logger.info(f"Quality filtering completed for dataset {dataset_id}")
            return result
            
        except Exception as e:
            logger.error(f"Quality filtering failed for dataset {dataset_id}: {str(e)}")
            raise
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Quality filtering task failed for dataset {dataset_id}: {str(e)}")
        raise


async def get_dataset_info(dataset_id: str) -> Optional[Dataset]:
    """Get dataset information from database"""
    async with async_session_maker() as session:
        stmt = select(Dataset).where(Dataset.id == UUID(dataset_id))
        result = await session.execute(stmt)
        return result.scalar_one_or_none()