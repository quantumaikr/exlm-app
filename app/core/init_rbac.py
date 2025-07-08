"""
Initialize default roles and permissions
"""

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import async_session
from app.models.role import Role, Permission
from app.models.user import User
from app.core.permissions import DEFAULT_ROLES


async def create_default_permissions(db: AsyncSession):
    """Create all default permissions"""
    resources = ["project", "model", "dataset", "pipeline", "deployment", "user", "role"]
    actions = ["create", "read", "update", "delete", "execute"]
    
    for resource in resources:
        for action in actions:
            # Skip execute for non-executable resources
            if action == "execute" and resource not in ["model", "pipeline"]:
                continue
            
            name = f"{resource}:{action}"
            
            # Check if permission already exists
            result = await db.execute(
                select(Permission).where(Permission.name == name)
            )
            if result.scalar_one_or_none():
                continue
            
            permission = Permission(
                name=name,
                resource=resource,
                action=action,
                description=f"{action.capitalize()} {resource}s"
            )
            db.add(permission)
    
    await db.commit()
    print("Default permissions created")


async def create_default_roles(db: AsyncSession):
    """Create default roles with their permissions"""
    for role_name, role_data in DEFAULT_ROLES.items():
        # Check if role already exists
        result = await db.execute(
            select(Role).where(Role.name == role_name)
        )
        if result.scalar_one_or_none():
            print(f"Role '{role_name}' already exists")
            continue
        
        # Create role
        role = Role(
            name=role_name,
            description=role_data["description"],
            is_system=True
        )
        
        # Add permissions
        for perm_name in role_data["permissions"]:
            perm_result = await db.execute(
                select(Permission).where(Permission.name == perm_name)
            )
            permission = perm_result.scalar_one_or_none()
            if permission:
                role.permissions.append(permission)
        
        db.add(role)
        print(f"Created role: {role_name}")
    
    await db.commit()


async def assign_admin_role_to_superusers(db: AsyncSession):
    """Assign admin role to all superusers"""
    # Get admin role
    admin_role_result = await db.execute(
        select(Role).where(Role.name == "admin")
    )
    admin_role = admin_role_result.scalar_one_or_none()
    
    if not admin_role:
        print("Admin role not found")
        return
    
    # Get all superusers
    superusers_result = await db.execute(
        select(User).where(User.is_superuser == True)
    )
    superusers = superusers_result.scalars().all()
    
    for user in superusers:
        await db.refresh(user, ["roles"])
        if admin_role not in user.roles:
            user.roles.append(admin_role)
            print(f"Assigned admin role to user: {user.email}")
    
    await db.commit()


async def init_rbac():
    """Initialize RBAC system with default roles and permissions"""
    async with async_session() as db:
        print("Initializing RBAC system...")
        
        # Create permissions
        await create_default_permissions(db)
        
        # Create roles
        await create_default_roles(db)
        
        # Assign admin role to superusers
        await assign_admin_role_to_superusers(db)
        
        print("RBAC initialization completed")


if __name__ == "__main__":
    asyncio.run(init_rbac())