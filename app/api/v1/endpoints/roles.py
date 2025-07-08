"""
Role management endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from pydantic import BaseModel, UUID4

from app.db.session import get_db
from app.api.deps import get_current_active_user
from app.schemas.user import UserResponse
from app.models.role import Role, Permission
from app.models.user import User
from app.core.permissions import Permissions, DEFAULT_ROLES


router = APIRouter()


class RoleCreate(BaseModel):
    name: str
    description: str
    permissions: List[str]


class RoleUpdate(BaseModel):
    description: Optional[str] = None
    permissions: Optional[List[str]] = None


class RoleResponse(BaseModel):
    id: UUID4
    name: str
    description: str
    is_system: bool
    permissions: List[str]
    
    class Config:
        from_attributes = True


class PermissionResponse(BaseModel):
    id: UUID4
    name: str
    resource: str
    action: str
    description: Optional[str]
    
    class Config:
        from_attributes = True


@router.get("/permissions", response_model=List[PermissionResponse])
async def list_permissions(
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
    _: bool = Depends(Permissions.read_role)
):
    """List all available permissions"""
    result = await db.execute(select(Permission))
    permissions = result.scalars().all()
    
    permission_responses = []
    for permission in permissions:
        permission_responses.append(
            PermissionResponse(
                id=permission.id,
                name=permission.name,
                resource=permission.resource,
                action=permission.action,
                description=permission.description
            )
        )
    
    return permission_responses


@router.get("/", response_model=List[RoleResponse])
async def list_roles(
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
    _: bool = Depends(Permissions.read_role)
):
    """List all roles"""
    result = await db.execute(select(Role))
    roles = result.scalars().all()
    
    role_responses = []
    for role in roles:
        # Get permissions for each role
        await db.refresh(role, ["permissions"])
        role_responses.append(
            RoleResponse(
                id=role.id,
                name=role.name,
                description=role.description,
                is_system=role.is_system,
                permissions=[f"{p.resource}:{p.action}" for p in role.permissions]
            )
        )
    
    return role_responses


@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: UUID4,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
    _: bool = Depends(Permissions.read_role)
):
    """Get a specific role"""
    result = await db.execute(
        select(Role).where(Role.id == role_id)
    )
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    await db.refresh(role, ["permissions"])
    
    return RoleResponse(
        id=role.id,
        name=role.name,
        description=role.description,
        is_system=role.is_system,
        permissions=[f"{p.resource}:{p.action}" for p in role.permissions]
    )


@router.post("/", response_model=RoleResponse)
async def create_role(
    role_data: RoleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
    _: bool = Depends(Permissions.create_role)
):
    """Create a new role"""
    # Check if role name already exists
    existing = await db.execute(
        select(Role).where(Role.name == role_data.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role name already exists"
        )
    
    # Create the role
    role = Role(
        name=role_data.name,
        description=role_data.description,
        is_system=False
    )
    
    # Add permissions
    for perm_str in role_data.permissions:
        resource, action = perm_str.split(":")
        perm_result = await db.execute(
            select(Permission).where(
                Permission.resource == resource,
                Permission.action == action
            )
        )
        permission = perm_result.scalar_one_or_none()
        
        if permission:
            role.permissions.append(permission)
    
    db.add(role)
    await db.commit()
    await db.refresh(role, ["permissions"])
    
    return RoleResponse(
        id=role.id,
        name=role.name,
        description=role.description,
        is_system=role.is_system,
        permissions=[f"{p.resource}:{p.action}" for p in role.permissions]
    )


@router.put("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: UUID4,
    role_data: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
    _: bool = Depends(Permissions.update_role)
):
    """Update a role"""
    result = await db.execute(
        select(Role).where(Role.id == role_id)
    )
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify system roles"
        )
    
    # Update basic fields
    if role_data.description is not None:
        role.description = role_data.description
    
    # Update permissions if provided
    if role_data.permissions is not None:
        # Clear existing permissions
        role.permissions.clear()
        
        # Add new permissions
        for perm_str in role_data.permissions:
            resource, action = perm_str.split(":")
            perm_result = await db.execute(
                select(Permission).where(
                    Permission.resource == resource,
                    Permission.action == action
                )
            )
            permission = perm_result.scalar_one_or_none()
            
            if permission:
                role.permissions.append(permission)
    
    await db.commit()
    await db.refresh(role, ["permissions"])
    
    return RoleResponse(
        id=role.id,
        name=role.name,
        description=role.description,
        is_system=role.is_system,
        permissions=[f"{p.resource}:{p.action}" for p in role.permissions]
    )


@router.delete("/{role_id}")
async def delete_role(
    role_id: UUID4,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
    _: bool = Depends(Permissions.delete_role)
):
    """Delete a role"""
    result = await db.execute(
        select(Role).where(Role.id == role_id)
    )
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete system roles"
        )
    
    await db.delete(role)
    await db.commit()
    
    return {"message": "Role deleted successfully"}


@router.post("/{role_id}/users/{user_id}")
async def assign_role_to_user(
    role_id: UUID4,
    user_id: UUID4,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
    _: bool = Depends(Permissions.update_role)
):
    """Assign a role to a user"""
    # Get role
    role_result = await db.execute(
        select(Role).where(Role.id == role_id)
    )
    role = role_result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    # Get user
    user_result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Assign role
    await db.refresh(user, ["roles"])
    if role not in user.roles:
        user.roles.append(role)
        await db.commit()
    
    return {"message": "Role assigned successfully"}


@router.delete("/{role_id}/users/{user_id}")
async def remove_role_from_user(
    role_id: UUID4,
    user_id: UUID4,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
    _: bool = Depends(Permissions.update_role)
):
    """Remove a role from a user"""
    # Get role
    role_result = await db.execute(
        select(Role).where(Role.id == role_id)
    )
    role = role_result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    # Get user
    user_result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Remove role
    await db.refresh(user, ["roles"])
    if role in user.roles:
        user.roles.remove(role)
        await db.commit()
    
    return {"message": "Role removed successfully"}