"""
Celery 앱 설정 및 태스크 관리
"""
from celery import Celery
from app.core.config import settings

# Celery 앱 생성
celery_app = Celery(
    "exlm",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.training",
        "app.tasks.data_generation",
        "app.tasks.evaluation",
    ]
)

# Celery 설정
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # 태스크 실행 시간 제한 (6시간)
    task_time_limit=21600,
    # 태스크 소프트 시간 제한 (5시간 50분)
    task_soft_time_limit=21000,
    # 결과 만료 시간 (7일)
    result_expires=604800,
    # 워커 프리페치 설정
    worker_prefetch_multiplier=1,
    # 태스크 추적
    task_track_started=True,
    # 태스크 재시도 설정
    task_default_retry_delay=60,
    task_max_retries=3,
)

# 라우팅 설정 - 태스크별 큐 분리
celery_app.conf.task_routes = {
    "app.tasks.training.*": {"queue": "training"},
    "app.tasks.data_generation.*": {"queue": "data_generation"},
    "app.tasks.evaluation.*": {"queue": "evaluation"},
}