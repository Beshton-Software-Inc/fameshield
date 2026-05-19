"""
Celery application configuration.
"""
from celery import Celery
from celery.schedules import crontab

from app.config import settings


# Create Celery app
celery_app = Celery(
    "fameshield",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.workers.monitor_worker",
        "app.workers.classify_worker",
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes
    task_soft_time_limit=540,  # 9 minutes
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
)

# Periodic task schedule
celery_app.conf.beat_schedule = {
    # Monitor active athletes every 15 minutes
    "monitor-active-athletes": {
        "task": "app.workers.monitor_worker.monitor_all_active_athletes",
        "schedule": crontab(minute="*/15"),  # Every 15 minutes
    },
    # Process pending classifications every 5 minutes
    "process-pending-classifications": {
        "task": "app.workers.classify_worker.process_pending_content",
        "schedule": crontab(minute="*/5"),  # Every 5 minutes
    },
    # Cleanup old tasks daily at 2 AM
    "cleanup-old-data": {
        "task": "app.workers.monitor_worker.cleanup_old_data",
        "schedule": crontab(hour=2, minute=0),  # Daily at 2 AM
    },
}

# Task routing
celery_app.conf.task_routes = {
    "app.workers.monitor_worker.*": {"queue": "monitoring"},
    "app.workers.classify_worker.*": {"queue": "classification"},
}


if __name__ == "__main__":
    celery_app.start()
