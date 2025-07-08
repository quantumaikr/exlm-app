"""
Monitoring and metrics configuration
"""

from prometheus_client import Counter, Histogram, Gauge, Info
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi import FastAPI
import time
from typing import Callable
from functools import wraps
import psutil
import asyncio

# Request metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)

# Model training metrics
model_training_total = Counter(
    'model_training_total',
    'Total number of model training tasks',
    ['project_id', 'status']
)

model_training_duration_seconds = Histogram(
    'model_training_duration_seconds',
    'Model training duration',
    ['project_id', 'model_type']
)

# Dataset processing metrics
dataset_processing_total = Counter(
    'dataset_processing_total',
    'Total number of dataset processing tasks',
    ['dataset_type', 'status']
)

dataset_size_bytes = Histogram(
    'dataset_size_bytes',
    'Size of processed datasets in bytes',
    ['dataset_type']
)

# System metrics
active_users = Gauge(
    'active_users',
    'Number of active users'
)

active_websocket_connections = Gauge(
    'active_websocket_connections',
    'Number of active WebSocket connections'
)

celery_tasks_pending = Gauge(
    'celery_tasks_pending',
    'Number of pending Celery tasks',
    ['queue']
)

celery_tasks_active = Gauge(
    'celery_tasks_active',
    'Number of active Celery tasks',
    ['queue']
)

# System resource metrics
cpu_usage_percent = Gauge(
    'cpu_usage_percent',
    'CPU usage percentage'
)

memory_usage_percent = Gauge(
    'memory_usage_percent',
    'Memory usage percentage'
)

disk_usage_percent = Gauge(
    'disk_usage_percent',
    'Disk usage percentage'
)

# Application info
app_info = Info(
    'app_info',
    'Application information'
)

# Error metrics
error_count = Counter(
    'error_count',
    'Total number of errors',
    ['error_type', 'endpoint']
)

# Database metrics
db_connection_pool_size = Gauge(
    'db_connection_pool_size',
    'Database connection pool size'
)

db_query_duration_seconds = Histogram(
    'db_query_duration_seconds',
    'Database query duration',
    ['query_type']
)

# Cache metrics
cache_hits = Counter(
    'cache_hits',
    'Number of cache hits',
    ['cache_type']
)

cache_misses = Counter(
    'cache_misses',
    'Number of cache misses',
    ['cache_type']
)


def setup_metrics(app: FastAPI):
    """Setup Prometheus metrics"""
    # Basic FastAPI instrumentator
    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_respect_env_var=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/metrics", "/health"],
        env_var_name="ENABLE_METRICS",
        inprogress_name="http_requests_inprogress",
        inprogress_labels=True,
    )
    
    instrumentator.instrument(app).expose(app, endpoint="/metrics")
    
    # Set application info
    from app.core.config import settings
    app_info.info({
        'version': settings.VERSION,
        'environment': settings.ENVIRONMENT,
        'project_name': settings.PROJECT_NAME
    })
    
    # Start system metrics collector
    asyncio.create_task(collect_system_metrics())


async def collect_system_metrics():
    """Collect system metrics periodically"""
    while True:
        try:
            # CPU usage
            cpu_usage_percent.set(psutil.cpu_percent(interval=1))
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_usage_percent.set(memory.percent)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_usage_percent.set(disk.percent)
            
        except Exception as e:
            print(f"Error collecting system metrics: {e}")
        
        await asyncio.sleep(30)  # Collect every 30 seconds


def track_time(metric: Histogram, labels: dict = None):
    """Decorator to track execution time"""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                if labels:
                    metric.labels(**labels).observe(duration)
                else:
                    metric.observe(duration)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                if labels:
                    metric.labels(**labels).observe(duration)
                else:
                    metric.observe(duration)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator


def increment_counter(counter: Counter, labels: dict = None):
    """Increment a counter metric"""
    if labels:
        counter.labels(**labels).inc()
    else:
        counter.inc()


def set_gauge(gauge: Gauge, value: float, labels: dict = None):
    """Set a gauge metric value"""
    if labels:
        gauge.labels(**labels).set(value)
    else:
        gauge.set(value)