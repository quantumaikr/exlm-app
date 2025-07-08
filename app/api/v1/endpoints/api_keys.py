"""
API Key management endpoints
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, UUID4

from app.db.session import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.api_key import APIKey
from app.core.api_key import create_api_key, revoke_api_key


router = APIRouter()


class APIKeyCreate(BaseModel):
    name: str
    description: Optional[str] = None
    expires_in_days: Optional[int] = None
    scopes: Optional[List[str]] = None


class APIKeyResponse(BaseModel):
    id: UUID4
    name: str
    key_prefix: str
    description: Optional[str]
    is_active: bool
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class APIKeyCreateResponse(BaseModel):
    api_key: APIKeyResponse
    full_key: str  # Only shown once during creation


@router.get("/", response_model=List[APIKeyResponse])
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all API keys for the current user"""
    result = await db.execute(
        select(APIKey).where(
            APIKey.user_id == current_user.id
        ).order_by(APIKey.created_at.desc())
    )
    api_keys = result.scalars().all()
    
    return [
        APIKeyResponse(
            id=key.id,
            name=key.name,
            key_prefix=key.key_prefix,
            description=key.description,
            is_active=key.is_active,
            expires_at=key.expires_at,
            last_used_at=key.last_used_at,
            created_at=key.created_at
        )
        for key in api_keys
    ]


@router.post("/", response_model=APIKeyCreateResponse)
async def create_new_api_key(
    key_data: APIKeyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new API key"""
    try:
        full_key, api_key = await create_api_key(
            db=db,
            user=current_user,
            name=key_data.name,
            description=key_data.description,
            expires_in_days=key_data.expires_in_days,
            scopes=key_data.scopes
        )
        
        return APIKeyCreateResponse(
            api_key=APIKeyResponse(
                id=api_key.id,
                name=api_key.name,
                key_prefix=api_key.key_prefix,
                description=api_key.description,
                is_active=api_key.is_active,
                expires_at=api_key.expires_at,
                last_used_at=api_key.last_used_at,
                created_at=api_key.created_at
            ),
            full_key=full_key
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{key_id}")
async def delete_api_key(
    key_id: UUID4,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Revoke an API key"""
    try:
        await revoke_api_key(
            db=db,
            user=current_user,
            key_id=str(key_id)
        )
        return {"message": "API key revoked successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{key_id}", response_model=APIKeyResponse)
async def get_api_key(
    key_id: UUID4,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get details of a specific API key"""
    result = await db.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.user_id == current_user.id
        )
    )
    api_key = result.scalar_one_or_none()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    return APIKeyResponse(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        description=api_key.description,
        is_active=api_key.is_active,
        expires_at=api_key.expires_at,
        last_used_at=api_key.last_used_at,
        created_at=api_key.created_at
    )