"""
Hugging Face models endpoints
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.api.deps import get_current_active_user
from app.models.user import User
from app.core.huggingface import hf_hub, HFModelInfo
from app.core.permissions import Permissions


router = APIRouter()


class HFModelSearchResponse(BaseModel):
    items: List[HFModelInfo]
    total: int


@router.get("/search", response_model=HFModelSearchResponse)
async def search_hf_models(
    query: str = Query(..., description="Search query"),
    task: Optional[str] = Query(None, description="Filter by task"),
    library: Optional[str] = Query(None, description="Filter by library"),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    _: bool = Depends(Permissions.read_model)
):
    """Search models on Hugging Face Hub"""
    try:
        models = await hf_hub.search_models(
            query=query,
            task=task,
            library=library,
            limit=limit
        )
        
        return HFModelSearchResponse(
            items=models,
            total=len(models)
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to search models: {str(e)}"
        )


@router.get("/{model_id:path}/info")
async def get_hf_model_info(
    model_id: str,
    current_user: User = Depends(get_current_active_user),
    _: bool = Depends(Permissions.read_model)
) -> Dict[str, Any]:
    """Get detailed information about a Hugging Face model"""
    try:
        info = await hf_hub.get_model_info(model_id)
        return info
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to get model info: {str(e)}"
        )


@router.get("/{model_id:path}/files")
async def list_hf_model_files(
    model_id: str,
    current_user: User = Depends(get_current_active_user),
    _: bool = Depends(Permissions.read_model)
) -> List[Dict[str, Any]]:
    """List files in a Hugging Face model repository"""
    try:
        files = await hf_hub.list_model_files(model_id)
        return files
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to list model files: {str(e)}"
        )


@router.post("/{model_id:path}/import")
async def import_hf_model(
    model_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    _: bool = Depends(Permissions.create_model)
):
    """Import a model from Hugging Face Hub to local project"""
    try:
        # Get model info first
        info = await hf_hub.get_model_info(model_id)
        
        # Download model
        local_path = await hf_hub.download_model(model_id)
        
        # TODO: Create model record in database
        # For now, just return the download info
        return {
            "message": "Model imported successfully",
            "model_id": model_id,
            "local_path": local_path,
            "info": info
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to import model: {str(e)}"
        )