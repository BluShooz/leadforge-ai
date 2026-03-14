"""
LeadForge AI - Celery Worker Configuration
Handles background tasks for scraping, enrichment, and email sending
"""
from celery import Celery
from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "leadforge",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    task_soft_time_limit=3000,  # 50 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)

# Scheduled tasks (Celery Beat)
celery_app.conf.beat_schedule = {
    'daily-scrape-google-maps': {
        'task': 'app.workers.tasks.scheduled_scrape_task',
        'schedule': 86400,  # Daily
        'args': ('google_maps', 'restaurant', 'New York, NY')
    },
    'enrich-new-leads': {
        'task': 'app.workers.tasks.enrich_pending_leads',
        'schedule': 3600,  # Every hour
    },
    'send-pending-emails': {
        'task': 'app.workers.tasks.send_pending_outreach',
        'schedule': 300,  # Every 5 minutes
    },
}
