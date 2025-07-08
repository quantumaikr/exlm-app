"""
Health check endpoints
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as redis
import psutil
from datetime import datetime
from typing import Dict, Any

from app.db.session import get_db
from app.core.config import settings
from app.core.redis import get_redis

router = APIRouter()


@router.get("/", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, Any]:
    """Basic health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "service": "exlm-backend"
    }


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check(
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
) -> Dict[str, Any]:
    """
    Readiness check - verifies all dependencies are ready
    """
    checks = {
        "database": False,
        "redis": False,
        "disk_space": False,
        "memory": False
    }
    
    errors = []
    
    # Check database
    try:
        result = await db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception as e:
        errors.append(f"Database error: {str(e)}")
    
    # Check Redis
    try:
        await redis_client.ping()
        checks["redis"] = True
    except Exception as e:
        errors.append(f"Redis error: {str(e)}")
    
    # Check disk space (require at least 10% free)
    try:
        disk_usage = psutil.disk_usage('/')
        if disk_usage.percent < 90:
            checks["disk_space"] = True
        else:
            errors.append(f"Disk space low: {disk_usage.percent}% used")
    except Exception as e:
        errors.append(f"Disk check error: {str(e)}")
    
    # Check memory (require at least 10% free)
    try:
        memory = psutil.virtual_memory()
        if memory.percent < 90:
            checks["memory"] = True
        else:
            errors.append(f"Memory usage high: {memory.percent}%")
    except Exception as e:
        errors.append(f"Memory check error: {str(e)}")
    
    # Determine overall status
    all_healthy = all(checks.values())
    
    response = {
        "status": "ready" if all_healthy else "not_ready",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks
    }
    
    if errors:
        response["errors"] = errors
    
    if not all_healthy:
        # Return 503 for not ready state
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=response
        )
    
    return response


@router.get("/live", status_code=status.HTTP_200_OK)
async def liveness_check() -> Dict[str, Any]:
    """
    Liveness check - verifies the application is running
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.VERSION
    }


@router.get("/metrics", status_code=status.HTTP_200_OK)
async def system_metrics() -> Dict[str, Any]:
    """
    Get current system metrics
    """
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Get network I/O
        net_io = psutil.net_io_counters()
        
        # Get process info
        process = psutil.Process()
        process_info = {
            "cpu_percent": process.cpu_percent(),
            "memory_mb": process.memory_info().rss / 1024 / 1024,
            "num_threads": process.num_threads(),
            "num_fds": process.num_fds() if hasattr(process, "num_fds") else None
        }
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "system": {
                "cpu": {
                    "percent": cpu_percent,
                    "count": psutil.cpu_count()
                },
                "memory": {
                    "total_mb": memory.total / 1024 / 1024,
                    "available_mb": memory.available / 1024 / 1024,
                    "percent": memory.percent
                },
                "disk": {
                    "total_gb": disk.total / 1024 / 1024 / 1024,
                    "free_gb": disk.free / 1024 / 1024 / 1024,
                    "percent": disk.percent
                },
                "network": {
                    "bytes_sent": net_io.bytes_sent,
                    "bytes_recv": net_io.bytes_recv,
                    "packets_sent": net_io.packets_sent,
                    "packets_recv": net_io.packets_recv
                }
            },
            "process": process_info
        }
    except Exception as e:
        return {
            "error": f"Failed to collect metrics: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }