from celery import Celery

from config import settings

# Create Celery instance
celery_app = Celery(
    "tasks",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["celery_tasks", "tasks.tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,
)

# Optional: Configure periodic tasks (Celery Beat)
celery_app.conf.beat_schedule = {
    # Daily data fetch task
    'daily-website-fetch': {
        'task': 'celery_tasks.daily_website_fetch',
        'schedule': 86400.0,  # Run every 86400 seconds (24 hours / everyday)
        'args': [None]  # Use default URLs
    },
    # Example periodic task (commented out)
    'periodic-task': {
        'task': 'celery_tasks.example_task',
        'schedule': 30.0,  # Run every 30 seconds
        'args': ['periodic_user']  # Provide the required 'name' argument
    },
}

if __name__ == "__main__":
    celery_app.start()
