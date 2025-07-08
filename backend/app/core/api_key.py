"""
API Key management utilities
"""

import secrets
import hashlib
import json
from typing import Optional, Tuple, List
from datetime import datetime, timedelta
from fastapi import HTTPException, status, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.api_key import APIKey
from app.models.user import User
from app.core.config import settings


# API Key header scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def generate_api_key() -> Tuple[str, str, str]:
    """
    Generate a new API key
    Returns: (full_key, key_hash, key_prefix)
    """
    # Generate a secure random key
    key = secrets.token_urlsafe(32)
    full_key = f"exlm_{key}"
    
    # Hash the key for storage
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    
    # Get prefix for identification (first 8 chars after prefix)
    key_prefix = full_key[:12]  # "exlm_" + first 7 chars
    
    return full_key, key_hash, key_prefix


def hash_api_key(api_key: str) -> str:
    """Hash an API key for comparison"""
    return hashlib.sha256(api_key.encode()).hexdigest()


async def get_api_key_user(
    api_key: Optional[str] = Security(api_key_header),
    db: AsyncSession = None
) -> Optional[User]:
    """
    Validate API key and return associated user
    """
    if not api_key:
        return None
    
    # Hash the provided key
    key_hash = hash_api_key(api_key)
    
    # Look up the key
    query = select(APIKey).where(
        APIKey.key_hash == key_hash,
        APIKey.is_active == True
    )
    result = await db.execute(query)
    api_key_obj = result.scalar_one_or_none()
    
    if not api_key_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    # Check if expired
    if api_key_obj.is_expired():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has expired"
        )
    
    # Update last used timestamp
    api_key_obj.update_last_used()
    await db.commit()
    
    # Get the associated user
    await db.refresh(api_key_obj, ["user"])
    
    if not api_key_obj.user or not api_key_obj.user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive"
        )
    
    return api_key_obj.user


async def create_api_key(
    db: AsyncSession,
    user: User,
    name: str,
    description: Optional[str] = None,
    expires_in_days: Optional[int] = None,
    scopes: Optional[List[str]] = None
) -> Tuple[str, APIKey]:
    """
    Create a new API key for a user
    Returns the full key (only shown once) and the key object
    """
    # Generate the key
    full_key, key_hash, key_prefix = generate_api_key()
    
    # Calculate expiration
    expires_at = None
    if expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
    
    # Create the key object
    api_key = APIKey(
        name=name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        description=description,
        user_id=user.id,
        expires_at=expires_at,
        scopes=json.dumps(scopes or [])
    )
    
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    
    return full_key, api_key


async def revoke_api_key(
    db: AsyncSession,
    user: User,
    key_id: str
) -> bool:
    """Revoke an API key"""
    query = select(APIKey).where(
        APIKey.id == key_id,
        APIKey.user_id == user.id
    )
    result = await db.execute(query)
    api_key = result.scalar_one_or_none()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    api_key.is_active = False
    await db.commit()
    
    return True