from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID

from app.api import deps
from app.core.database import get_db
from app.schemas.user import UserResponse
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse, ProjectListResponse

router = APIRouter()


@router.get("/", response_model=ProjectListResponse)
async def get_projects(
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(deps.get_current_active_user),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
) -> Any:
    """Get list of projects for current user"""
    query = select(Project).where(Project.user_id == current_user.id)
    
    if search:
        query = query.where(Project.name.ilike(f"%{search}%"))
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()
    
    # Apply pagination
    query = query.offset((page - 1) * limit).limit(limit)
    query = query.order_by(Project.created_at.desc())
    
    result = await db.execute(query)
    projects = result.scalars().all()
    
    return ProjectListResponse(
        items=projects,
        total=total,
        page=page,
        pages=(total + limit - 1) // limit,
    )


@router.post("/", response_model=ProjectResponse)
async def create_project(
    *,
    db: AsyncSession = Depends(get_db),
    project_in: ProjectCreate,
    current_user: UserResponse = Depends(deps.get_current_active_user),
) -> Any:
    """Create new project"""
    project = Project(
        **project_in.dict(),
        user_id=current_user.id,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
    current_user: UserResponse = Depends(deps.get_current_active_user),
) -> Any:
    """Get project by ID"""
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == current_user.id
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return project


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
    project_in: ProjectUpdate,
    current_user: UserResponse = Depends(deps.get_current_active_user),
) -> Any:
    """Update project"""
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == current_user.id
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    update_data = project_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)
    
    await db.commit()
    await db.refresh(project)
    return project


@router.delete("/{project_id}")
async def delete_project(
    *,
    db: AsyncSession = Depends(get_db),
    project_id: UUID,
    current_user: UserResponse = Depends(deps.get_current_active_user),
) -> Any:
    """Delete project"""
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == current_user.id
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    await db.delete(project)
    await db.commit()
    
    return {"message": "Project deleted successfully"}