from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "secure_video_platform",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.transcode_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.workers.transcode_tasks.*": {"queue": "video_processing"},
    },
    broker_connection_retry_on_startup=False,
    broker_connection_max_retries=1,
    broker_connection_timeout=1.0,
    broker_transport_options={
        "socket_timeout": 1,
        "socket_connect_timeout": 1,
    },
    task_publish_retry=False,
)
