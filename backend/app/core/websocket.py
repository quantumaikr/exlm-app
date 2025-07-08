from typing import Dict, Set
from fastapi import WebSocket
from app.core.logging import logger
import json


class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        # Store active connections by user ID
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Store connection to user mapping
        self.connection_users: Dict[WebSocket, str] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept and store a new connection"""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        self.active_connections[user_id].add(websocket)
        self.connection_users[websocket] = user_id
        
        logger.info(f"WebSocket connected for user: {user_id}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove a connection"""
        user_id = self.connection_users.get(websocket)
        
        if user_id:
            self.active_connections[user_id].discard(websocket)
            
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
            
            del self.connection_users[websocket]
            
            logger.info(f"WebSocket disconnected for user: {user_id}")
    
    async def send_personal_message(self, message: str, user_id: str):
        """Send a message to all connections of a specific user"""
        if user_id in self.active_connections:
            disconnected = []
            
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    logger.error(f"Error sending message to user {user_id}: {e}")
                    disconnected.append(connection)
            
            # Remove disconnected connections
            for conn in disconnected:
                self.disconnect(conn)
    
    async def send_json(self, data: dict, user_id: str):
        """Send JSON data to a specific user"""
        message = json.dumps(data)
        await self.send_personal_message(message, user_id)
    
    async def broadcast(self, message: str):
        """Broadcast a message to all connected users"""
        all_connections = []
        for connections in self.active_connections.values():
            all_connections.extend(connections)
        
        disconnected = []
        for connection in all_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")
                disconnected.append(connection)
        
        # Remove disconnected connections
        for conn in disconnected:
            self.disconnect(conn)
    
    async def broadcast_json(self, data: dict):
        """Broadcast JSON data to all users"""
        message = json.dumps(data)
        await self.broadcast(message)


# Global connection manager instance
manager = ConnectionManager()