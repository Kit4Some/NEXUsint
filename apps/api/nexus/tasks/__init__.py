"""Celery application initialization."""

from celery import Celery

from nexus.config import settings

app = Celery(
    "nexus",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_routes={
        "nexus.tasks.collection_tasks.*": {"queue": "collection"},
        "nexus.tasks.indexing_tasks.*": {"queue": "indexing"},
        "nexus.tasks.monitoring_tasks.*": {"queue": "collection"},
        "nexus.tasks.live_feed_tasks.*": {"queue": "live_feed"},
    },
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    beat_schedule={
        "check-watch-targets": {
            "task": "nexus.tasks.monitoring_tasks.check_watch_targets",
            "schedule": 300.0,  # Every 5 minutes
        },
        "sigint-area-scan": {
            "task": "nexus.tasks.monitoring_tasks.sigint_area_scan",
            "schedule": 60.0,  # Every 60 seconds
        },
        "live-feed-fast": {
            "task": "nexus.tasks.live_feed_tasks.live_feed_fast",
            "schedule": 60.0,  # Every 60 seconds
        },
        "live-feed-slow": {
            "task": "nexus.tasks.live_feed_tasks.live_feed_slow",
            "schedule": 300.0,  # Every 5 minutes
        },
    },
)

# Auto-discover tasks
app.autodiscover_tasks([
    "nexus.tasks.collection_tasks",
    "nexus.tasks.indexing_tasks",
    "nexus.tasks.monitoring_tasks",
    "nexus.tasks.live_feed_tasks",
])
