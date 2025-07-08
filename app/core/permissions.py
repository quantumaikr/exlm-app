"""
Permission system for role-based access control
"""

from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.user import User
from app.models.role import Role, Permission
from app.models.project import Project


class PermissionChecker:
    """Check if a user has specific permissions"""
    
    def __init__(self, resource: str, action: str):
        self.resource = resource
        self.action = action
        self.permission_name = f"{resource}:{action}"
    
    async def __call__(self, current_user: User, db: AsyncSession) -> bool:
        """Check if the user has the required permission"""
        # Superusers have all permissions
        if current_user.is_superuser:
            return True
        
        # Check user's roles and permissions
        query = select(Permission).join(
            Permission.roles
        ).join(
            Role.users
        ).where(
            and_(
                Role.users.any(id=current_user.id),
                Permission.resource == self.resource,
                Permission.action == self.action
            )
        )
        
        result = await db.execute(query)
        permission = result.scalar_one_or_none()
        
        if not permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {self.permission_name}"
            )
        
        return True


class ResourceOwnerChecker:
    """Check if a user owns a specific resource"""
    
    def __init__(self, resource_type: str):
        self.resource_type = resource_type
    
    async def check_ownership(
        self, 
        user: User, 
        resource_id: str, 
        db: AsyncSession
    ) -> bool:
        """Check if the user owns the resource"""
        if user.is_superuser:
            return True
        
        if self.resource_type == "project":
            query = select(Project).where(
                and_(
                    Project.id == resource_id,
                    Project.owner_id == user.id
                )
            )
            result = await db.execute(query)
            project = result.scalar_one_or_none()
            
            if not project:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Project not found or access denied"
                )
            
            return True
        
        # Add more resource types as needed
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown resource type: {self.resource_type}"
        )


# Predefined permission checkers
class Permissions:
    # Project permissions
    create_project = PermissionChecker("project", "create")
    read_project = PermissionChecker("project", "read")
    update_project = PermissionChecker("project", "update")
    delete_project = PermissionChecker("project", "delete")
    
    # Model permissions
    create_model = PermissionChecker("model", "create")
    read_model = PermissionChecker("model", "read")
    update_model = PermissionChecker("model", "update")
    delete_model = PermissionChecker("model", "delete")
    execute_model = PermissionChecker("model", "execute")
    
    # Dataset permissions
    create_dataset = PermissionChecker("dataset", "create")
    read_dataset = PermissionChecker("dataset", "read")
    update_dataset = PermissionChecker("dataset", "update")
    delete_dataset = PermissionChecker("dataset", "delete")
    
    # User management permissions
    create_user = PermissionChecker("user", "create")
    read_user = PermissionChecker("user", "read")
    update_user = PermissionChecker("user", "update")
    delete_user = PermissionChecker("user", "delete")
    
    # Role management permissions
    create_role = PermissionChecker("role", "create")
    read_role = PermissionChecker("role", "read")
    update_role = PermissionChecker("role", "update")
    delete_role = PermissionChecker("role", "delete")


# Default roles and their permissions
DEFAULT_ROLES = {
    "admin": {
        "description": "Administrator with full access",
        "permissions": [
            "project:create", "project:read", "project:update", "project:delete",
            "model:create", "model:read", "model:update", "model:delete", "model:execute",
            "dataset:create", "dataset:read", "dataset:update", "dataset:delete",
            "user:create", "user:read", "user:update", "user:delete",
            "role:create", "role:read", "role:update", "role:delete",
        ]
    },
    "developer": {
        "description": "Developer with project and model access",
        "permissions": [
            "project:create", "project:read", "project:update",
            "model:create", "model:read", "model:update", "model:execute",
            "dataset:create", "dataset:read", "dataset:update",
        ]
    },
    "viewer": {
        "description": "Read-only access to resources",
        "permissions": [
            "project:read",
            "model:read",
            "dataset:read",
        ]
    }
}