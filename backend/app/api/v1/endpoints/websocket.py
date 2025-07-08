from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from typing import Optional
from app.core.websocket import manager
from app.api import deps
from app.models.user import User
from app.core.logging import logger
from jose import jwt, JWTError
from app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db

router = APIRouter()


async def get_current_user_from_websocket(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Get current user from WebSocket connection"""
    if not token:
        await websocket.close(code=1008, reason="Missing authentication token")
        return None
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        
        if not user_id:
            await websocket.close(code=1008, reason="Invalid token")
            return None
        
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.is_active:
            await websocket.close(code=1008, reason="User not found or inactive")
            return None
        
        return user
    
    except JWTError:
        await websocket.close(code=1008, reason="Invalid token")
        return None


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    db: AsyncSession = Depends(get_db)
):
    """WebSocket endpoint for real-time updates"""
    # Authenticate user
    user = await get_current_user_from_websocket(websocket, db=db)
    if not user:
        return
    
    # Connect
    await manager.connect(websocket, str(user.id))
    
    try:
        # Send initial connection message
        await manager.send_json({
            "type": "connection",
            "message": "Connected to WebSocket",
            "user_id": str(user.id)
        }, str(user.id))
        
        # Keep connection alive and handle incoming messages
        while True:
            data = await websocket.receive_text()
            logger.info(f"Received WebSocket message from user {user.id}: {data}")
            
            # Echo message back (you can add custom message handling here)
            await manager.send_json({
                "type": "echo",
                "message": data,
                "user_id": str(user.id)
            }, str(user.id))
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info(f"WebSocket disconnected for user {user.id}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user.id}: {e}")
        manager.disconnect(websocket)