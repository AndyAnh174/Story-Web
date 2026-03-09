"""
Celery App — Background task queue cho Story AI Platform.
"""
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "story_platform",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Ho_Chi_Minh",
    enable_utc=True,
    # Retry config
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Prevent task buildup
    task_soft_time_limit=120,
    task_time_limit=180,
)
