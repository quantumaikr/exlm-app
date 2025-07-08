import asyncio
import httpx
from typing import Dict, Any
from app.core.config import settings
from app.core.logging import logger


async def send_websocket_update(user_id: str, event_type: str, data: Dict[str, Any]):
    """Send update via internal API to WebSocket connections"""
    try:
        # Internal API endpoint to trigger WebSocket messages
        url = f"http://localhost:8000{settings.API_V1_STR}/internal/websocket/notify"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json={
                    "user_id": user_id,
                    "type": event_type,
                    "data": data
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to send WebSocket update: {response.status_code}")
    
    except Exception as e:
        logger.error(f"Error sending WebSocket update: {e}")


def notify_user(user_id: str, event_type: str, data: Dict[str, Any]):
    """Synchronous wrapper for sending WebSocket updates from Celery tasks"""
    asyncio.run(send_websocket_update(user_id, event_type, data))