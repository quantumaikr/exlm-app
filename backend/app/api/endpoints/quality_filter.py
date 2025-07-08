"""
Quality filtering API endpoints
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from uuid import UUID

from app.core.auth import get_current_user
from app.core.quality_filter import quality_filter
from app.tasks.data_generation import filter_dataset_quality
from app.models.user import User
from app.models.dataset import Dataset
from app.core.database import async_session_maker
from sqlalchemy import select
from app.core.logging import logger

router = APIRouter()


class QualityFilterConfig(BaseModel):
    """Quality filter configuration"""
    duplicate_threshold: float = Field(default=0.95, ge=0.0, le=1.0)
    min_length: int = Field(default=10, ge=1)
    max_length: int = Field(default=2048, ge=1)
    check_language: bool = Field(default=True)
    target_language: str = Field(default="en")
    quality_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    filter_toxic: bool = Field(default=True)
    toxicity_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    domain_keywords: Optional[list] = Field(default=None)
    domain_threshold: float = Field(default=0.3, ge=0.0, le=1.0)


class FilterDatasetRequest(BaseModel):
    """Request to filter dataset quality"""
    dataset_id: UUID
    config: QualityFilterConfig


@router.post("/filter-dataset")
async def filter_dataset(
    request: FilterDatasetRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Apply quality filtering to a dataset
    """
    try:
        # Check if dataset exists and belongs to user
        async with async_session_maker() as session:
            stmt = select(Dataset).where(
                Dataset.id == request.dataset_id,
                Dataset.user_id == current_user.id
            )
            result = await session.execute(stmt)
            dataset = result.scalar_one_or_none()
            
            if not dataset:
                raise HTTPException(
                    status_code=404,
                    detail="Dataset not found or access denied"
                )
            
            if not dataset.file_path:
                raise HTTPException(
                    status_code=400,
                    detail="Dataset has no data file"
                )
        
        # Start background task
        task = filter_dataset_quality.delay(
            str(request.dataset_id),
            request.config.dict()
        )
        
        return {
            "message": "Quality filtering started",
            "task_id": task.id,
            "dataset_id": request.dataset_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting quality filtering: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to start quality filtering"
        )


@router.get("/filter-config/defaults")
async def get_default_filter_config():
    """
    Get default quality filter configuration
    """
    return {
        "duplicate_threshold": 0.95,
        "min_length": 10,
        "max_length": 2048,
        "check_language": True,
        "target_language": "en",
        "quality_threshold": 0.6,
        "filter_toxic": True,
        "toxicity_threshold": 0.8,
        "domain_keywords": [],
        "domain_threshold": 0.3
    }


@router.post("/analyze-quality")
async def analyze_dataset_quality(
    request: FilterDatasetRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Analyze dataset quality without filtering (preview)
    """
    try:
        # Check if dataset exists and belongs to user
        async with async_session_maker() as session:
            stmt = select(Dataset).where(
                Dataset.id == request.dataset_id,
                Dataset.user_id == current_user.id
            )
            result = await session.execute(stmt)
            dataset = result.scalar_one_or_none()
            
            if not dataset:
                raise HTTPException(
                    status_code=404,
                    detail="Dataset not found or access denied"
                )
            
            if not dataset.file_path:
                raise HTTPException(
                    status_code=400,
                    detail="Dataset has no data file"
                )
        
        # Load and analyze data
        import json
        with open(dataset.file_path, "r", encoding="utf-8") as f:
            if dataset.file_path.endswith(".jsonl"):
                data = [json.loads(line) for line in f]
            else:
                data = json.load(f)
        
        # Analyze quality (without filtering)
        analyzed_data = quality_filter._calculate_quality_scores(data)
        
        # Calculate statistics
        quality_scores = [s.get("quality_score", 0) for s in analyzed_data]
        
        stats = {
            "total_samples": len(data),
            "quality_scores": {
                "mean": sum(quality_scores) / len(quality_scores) if quality_scores else 0,
                "min": min(quality_scores) if quality_scores else 0,
                "max": max(quality_scores) if quality_scores else 0,
                "distribution": {
                    "excellent": sum(1 for s in quality_scores if s >= 0.8),
                    "good": sum(1 for s in quality_scores if 0.6 <= s < 0.8),
                    "fair": sum(1 for s in quality_scores if 0.4 <= s < 0.6),
                    "poor": sum(1 for s in quality_scores if s < 0.4)
                }
            }
        }
        
        # Preview filtering results
        config_dict = request.config.dict()
        filtered_data, filter_stats = quality_filter.filter_samples(data, config_dict)
        
        return {
            "analysis": stats,
            "filter_preview": {
                "original_count": len(data),
                "filtered_count": len(filtered_data),
                "filter_rate": 1 - (len(filtered_data) / max(len(data), 1)),
                "statistics": filter_stats
            },
            "sample_scores": [
                {
                    "index": i,
                    "quality_score": s.get("quality_score", 0),
                    "quality_scores": s.get("quality_scores", {}),
                    "preview": (
                        s.get("instruction", "")[:100] + "..." if len(s.get("instruction", "")) > 100
                        else s.get("response", "")[:100] + "..." if len(s.get("response", "")) > 100
                        else str(s)[:100] + "..."
                    )
                }
                for i, s in enumerate(analyzed_data[:20])  # Show first 20 samples
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing dataset quality: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to analyze dataset quality"
        )


@router.get("/supported-languages")
async def get_supported_languages():
    """
    Get list of supported languages for quality filtering
    """
    return {
        "languages": [
            {"code": "en", "name": "English"},
            {"code": "es", "name": "Spanish"},
            {"code": "fr", "name": "French"},
            {"code": "de", "name": "German"},
            {"code": "it", "name": "Italian"},
            {"code": "pt", "name": "Portuguese"},
            {"code": "ru", "name": "Russian"},
            {"code": "ja", "name": "Japanese"},
            {"code": "ko", "name": "Korean"},
            {"code": "zh", "name": "Chinese"}
        ]
    }