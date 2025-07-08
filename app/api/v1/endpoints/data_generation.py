from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from pydantic import BaseModel, Field

from app.api import deps
from app.core.database import get_db
from app.schemas.user import UserResponse
from app.models.project import Project
from app.models.dataset import Dataset
from app.services.llm_clients import data_generation_service
from app.core.logging import get_logger
import json
import aiofiles
from datetime import datetime

logger = get_logger(__name__)

router = APIRouter()


class PromptTemplate(BaseModel):
    name: str
    content: str
    variables: List[str]
    description: Optional[str] = None


class DataGenerationRequest(BaseModel):
    project_id: UUID
    dataset_name: str
    api_provider: str = Field(..., regex="^(openai|anthropic|google)$")
    api_key: Optional[str] = None
    model_name: Optional[str] = None
    template: PromptTemplate
    template_variables: Dict[str, str]
    num_samples: int = Field(100, ge=1, le=10000)
    batch_size: int = Field(10, ge=1, le=100)
    generation_config: Dict[str, Any] = Field(default_factory=dict)
    quality_filter: Dict[str, Any] = Field(default_factory=lambda: {
        "enabled": True,
        "min_length": 50,
        "max_length": 2000,
        "min_quality_score": 7,
        "remove_duplicates": True,
    })


class DataGenerationResponse(BaseModel):
    task_id: str
    dataset_id: UUID
    message: str


class GenerationStatus(BaseModel):
    task_id: str
    status: str
    progress: int
    total_samples: int
    generated_samples: int
    filtered_samples: int
    error: Optional[str] = None


@router.post("/generate", response_model=DataGenerationResponse)
async def generate_data(
    request: DataGenerationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(deps.get_current_active_user)
):
    """Start synthetic data generation task"""
    
    # Verify project access
    result = await db.execute(
        select(Project).where(
            Project.id == request.project_id,
            Project.user_id == current_user.id
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Create dataset entry
    dataset = Dataset(
        name=request.dataset_name,
        project_id=request.project_id,
        source="generated",
        status="generating",
        metadata={
            "provider": request.api_provider,
            "template": request.template.dict(),
            "num_samples": request.num_samples,
            "generation_started_at": datetime.utcnow().isoformat(),
        }
    )
    
    db.add(dataset)
    await db.commit()
    await db.refresh(dataset)
    
    # Generate unique task ID
    task_id = f"gen_{dataset.id}_{datetime.utcnow().timestamp()}"
    
    # Start background generation
    background_tasks.add_task(
        generate_data_task,
        task_id=task_id,
        dataset_id=str(dataset.id),
        request=request.dict()
    )
    
    return DataGenerationResponse(
        task_id=task_id,
        dataset_id=dataset.id,
        message=f"Data generation started. Generating {request.num_samples} samples."
    )


@router.get("/status/{task_id}", response_model=GenerationStatus)
async def get_generation_status(
    task_id: str,
    current_user: UserResponse = Depends(deps.get_current_active_user)
):
    """Get data generation task status"""
    
    # In production, this would check a task queue (e.g., Celery, Redis)
    # For now, return mock status
    return GenerationStatus(
        task_id=task_id,
        status="in_progress",
        progress=45,
        total_samples=100,
        generated_samples=45,
        filtered_samples=3,
    )


@router.post("/templates", response_model=PromptTemplate)
async def create_template(
    template: PromptTemplate,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(deps.get_current_active_user)
):
    """Create a reusable prompt template"""
    
    # In production, save to database
    # For now, just return the template
    return template


@router.get("/templates", response_model=List[PromptTemplate])
async def list_templates(
    current_user: UserResponse = Depends(deps.get_current_active_user)
):
    """List available prompt templates"""
    
    # Default templates
    templates = [
        PromptTemplate(
            name="instruction_response",
            content="""Generate a high-quality instruction-response pair for {domain} domain.

Instruction: Create a {difficulty} level question about {topic}.
Response: Provide a detailed, accurate answer.

Requirements:
- The instruction should be clear and specific
- The response should be comprehensive and accurate
- Use proper formatting and structure

Format as JSON:
{{
  "instruction": "...",
  "response": "..."
}}""",
            variables=["domain", "difficulty", "topic"],
            description="Generate instruction-response pairs for fine-tuning"
        ),
        PromptTemplate(
            name="qa_pairs",
            content="""Generate a question-answer pair related to {subject}.

Context: {context}

Create a thoughtful question and provide a detailed answer.

Format as JSON:
{{
  "question": "...",
  "answer": "...",
  "category": "{category}"
}}""",
            variables=["subject", "context", "category"],
            description="Generate Q&A pairs for training"
        ),
        PromptTemplate(
            name="dialog_turns",
            content="""Generate a realistic dialogue between a user and an AI assistant about {topic}.

The conversation should:
- Be natural and engaging
- Cover {num_turns} turns
- Demonstrate {skill_focus}

Format as JSON:
{{
  "conversation": [
    {{"role": "user", "content": "..."}},
    {{"role": "assistant", "content": "..."}}
  ]
}}""",
            variables=["topic", "num_turns", "skill_focus"],
            description="Generate multi-turn dialogues"
        ),
    ]
    
    return templates


async def generate_data_task(task_id: str, dataset_id: str, request: dict):
    """Background task for data generation"""
    try:
        logger.info(f"Starting data generation task {task_id}")
        
        # Initialize generation service
        template = request["template"]
        results = []
        
        # Generate in batches
        batch_size = request["batch_size"]
        total_samples = request["num_samples"]
        
        for i in range(0, total_samples, batch_size):
            current_batch_size = min(batch_size, total_samples - i)
            
            # Generate batch
            batch_results = await data_generation_service.generate_instruction_response_pairs(
                provider=request["api_provider"],
                template=template["content"],
                variables=request["template_variables"],
                num_samples=current_batch_size,
                api_key=request.get("api_key"),
                **request.get("generation_config", {})
            )
            
            # Apply quality filters if enabled
            if request["quality_filter"]["enabled"]:
                # Evaluate quality
                batch_results = await data_generation_service.evaluate_quality(
                    batch_results,
                    provider=request["api_provider"],
                    api_key=request.get("api_key")
                )
                
                # Filter by quality score
                min_score = request["quality_filter"]["min_quality_score"]
                batch_results = [
                    item for item in batch_results
                    if item.get("quality_score", 0) >= min_score
                ]
                
                # Filter by length
                min_len = request["quality_filter"]["min_length"]
                max_len = request["quality_filter"]["max_length"]
                batch_results = [
                    item for item in batch_results
                    if min_len <= len(item.get("response", "")) <= max_len
                ]
            
            results.extend(batch_results)
            
            # Update progress (would update in task queue in production)
            progress = len(results) / total_samples * 100
            logger.info(f"Task {task_id}: {progress:.1f}% complete")
        
        # Remove duplicates if enabled
        if request["quality_filter"]["remove_duplicates"]:
            seen = set()
            unique_results = []
            for item in results:
                key = (item.get("instruction", ""), item.get("response", ""))
                if key not in seen:
                    seen.add(key)
                    unique_results.append(item)
            results = unique_results
        
        # Save results to file
        output_path = f"data/generated/{dataset_id}.jsonl"
        async with aiofiles.open(output_path, 'w') as f:
            for item in results:
                await f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        # Update dataset status in database
        async with AsyncSession(get_db.engine) as db:
            result = await db.execute(
                select(Dataset).where(Dataset.id == dataset_id)
            )
            dataset = result.scalar_one_or_none()
            if dataset:
                dataset.status = "ready"
                dataset.file_path = output_path
                dataset.metadata["generation_completed_at"] = datetime.utcnow().isoformat()
                dataset.metadata["total_samples"] = len(results)
                await db.commit()
        
        logger.info(f"Task {task_id} completed. Generated {len(results)} samples.")
        
    except Exception as e:
        logger.error(f"Data generation task {task_id} failed: {e}")
        
        # Update dataset status to failed
        async with AsyncSession(get_db.engine) as db:
            result = await db.execute(
                select(Dataset).where(Dataset.id == dataset_id)
            )
            dataset = result.scalar_one_or_none()
            if dataset:
                dataset.status = "failed"
                dataset.metadata["error"] = str(e)
                await db.commit()