"""
Hugging Face Hub integration
"""

import os
from typing import List, Dict, Optional, Any
from huggingface_hub import HfApi, ModelCard, list_models, model_info
from huggingface_hub.utils import RepositoryNotFoundError
import aiohttp
from pydantic import BaseModel

from app.core.config import settings
from app.core.logging import logger


class HFModelInfo(BaseModel):
    """Hugging Face model information"""
    model_id: str
    author: str
    model_name: str
    pipeline_tag: Optional[str] = None
    task: Optional[str] = None
    library_name: Optional[str] = None
    license: Optional[str] = None
    tags: List[str] = []
    downloads: int = 0
    likes: int = 0
    created_at: Optional[str] = None
    last_modified: Optional[str] = None


class HuggingFaceHub:
    """Hugging Face Hub client"""
    
    def __init__(self, token: Optional[str] = None):
        self.token = token or settings.HF_TOKEN
        self.api = HfApi(token=self.token)
    
    async def search_models(
        self,
        query: str,
        task: Optional[str] = None,
        library: Optional[str] = None,
        limit: int = 20
    ) -> List[HFModelInfo]:
        """Search models on Hugging Face Hub"""
        try:
            # Build filter
            filter_params = []
            if task:
                filter_params.append(f"task:{task}")
            if library:
                filter_params.append(f"library:{library}")
            
            # Search models
            models = list(list_models(
                search=query,
                filter=filter_params,
                sort="downloads",
                direction=-1,
                limit=limit,
                token=self.token
            ))
            
            # Convert to our model format
            result = []
            for model in models:
                model_id = model.modelId
                parts = model_id.split("/")
                author = parts[0] if len(parts) > 1 else "unknown"
                model_name = parts[1] if len(parts) > 1 else model_id
                
                result.append(HFModelInfo(
                    model_id=model_id,
                    author=author,
                    model_name=model_name,
                    pipeline_tag=getattr(model, "pipeline_tag", None),
                    task=getattr(model, "task", None),
                    library_name=getattr(model, "library_name", None),
                    license=getattr(model, "license", None),
                    tags=getattr(model, "tags", []),
                    downloads=getattr(model, "downloads", 0),
                    likes=getattr(model, "likes", 0),
                    created_at=str(getattr(model, "created_at", None)),
                    last_modified=str(getattr(model, "last_modified", None))
                ))
            
            return result
            
        except Exception as e:
            logger.error(f"Error searching models: {e}")
            raise
    
    async def get_model_info(self, model_id: str) -> Dict[str, Any]:
        """Get detailed model information"""
        try:
            info = model_info(model_id, token=self.token)
            
            # Get model card if available
            card_data = None
            try:
                card = ModelCard.load(model_id, token=self.token)
                card_data = {
                    "content": card.content,
                    "data": card.data.to_dict() if card.data else None
                }
            except Exception:
                pass
            
            return {
                "model_id": info.modelId,
                "author": info.author,
                "sha": info.sha,
                "last_modified": str(info.lastModified),
                "private": info.private,
                "disabled": getattr(info, "disabled", False),
                "gated": getattr(info, "gated", False),
                "pipeline_tag": info.pipeline_tag,
                "tags": info.tags,
                "downloads": getattr(info, "downloads", 0),
                "likes": getattr(info, "likes", 0),
                "library_name": getattr(info, "library_name", None),
                "model_card": card_data,
                "siblings": [
                    {
                        "filename": s.rfilename,
                        "size": s.size,
                        "blob_id": s.blob_id,
                        "lfs": getattr(s, "lfs", None)
                    }
                    for s in info.siblings
                ] if hasattr(info, "siblings") else []
            }
            
        except RepositoryNotFoundError:
            raise ValueError(f"Model {model_id} not found")
        except Exception as e:
            logger.error(f"Error getting model info: {e}")
            raise
    
    async def download_model(
        self,
        model_id: str,
        revision: Optional[str] = None,
        cache_dir: Optional[str] = None
    ) -> str:
        """Download model from Hugging Face Hub"""
        try:
            from huggingface_hub import snapshot_download
            
            cache_dir = cache_dir or os.path.join(settings.MODEL_DIR, "huggingface")
            
            # Download model
            local_path = snapshot_download(
                repo_id=model_id,
                revision=revision,
                cache_dir=cache_dir,
                token=self.token,
                local_dir_use_symlinks=False
            )
            
            logger.info(f"Downloaded model {model_id} to {local_path}")
            return local_path
            
        except Exception as e:
            logger.error(f"Error downloading model: {e}")
            raise
    
    async def list_model_files(self, model_id: str) -> List[Dict[str, Any]]:
        """List files in a model repository"""
        try:
            info = model_info(model_id, files_metadata=True, token=self.token)
            
            files = []
            for sibling in info.siblings:
                files.append({
                    "filename": sibling.rfilename,
                    "size": sibling.size,
                    "blob_id": sibling.blob_id,
                    "lfs": getattr(sibling, "lfs", None)
                })
            
            return files
            
        except Exception as e:
            logger.error(f"Error listing model files: {e}")
            raise
    
    def get_model_download_url(self, model_id: str, filename: str) -> str:
        """Get direct download URL for a model file"""
        return f"https://huggingface.co/{model_id}/resolve/main/{filename}"


# Global instance
hf_hub = HuggingFaceHub()