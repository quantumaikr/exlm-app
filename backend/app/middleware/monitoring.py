"""
Monitoring middleware for tracking metrics
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import time
from typing import Callable

from app.core.monitoring import (
    http_requests_total,
    http_request_duration_seconds,
    error_count,
    active_users,
)
from app.core.logging import logger


class MonitoringMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Start timer
        start_time = time.time()
        
        # Extract route info
        route = request.url.path
        method = request.method
        
        try:
            # Process request
            response = await call_next(request)
            
            # Record metrics
            status = response.status_code
            http_requests_total.labels(
                method=method,
                endpoint=route,
                status=status
            ).inc()
            
            # Record errors
            if status >= 400:
                error_type = "client_error" if status < 500 else "server_error"
                error_count.labels(
                    error_type=error_type,
                    endpoint=route
                ).inc()
            
            return response
            
        except Exception as e:
            # Record error
            error_count.labels(
                error_type="unhandled_exception",
                endpoint=route
            ).inc()
            
            logger.error(f"Unhandled exception in {method} {route}: {str(e)}")
            raise
            
        finally:
            # Record duration
            duration = time.time() - start_time
            http_request_duration_seconds.labels(
                method=method,
                endpoint=route
            ).observe(duration)
            
            # Update active users (simplified - in real app, track by auth)
            if hasattr(request.state, "user") and request.state.user:
                active_users.set(1)  # This is simplified