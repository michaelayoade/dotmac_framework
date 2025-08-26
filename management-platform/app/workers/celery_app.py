"""
Celery application configuration.
"""

import os

from celery import Celery

from config import settings

# Create Celery instance
celery_app = Celery(
    "dotmac_management_platform",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.workers.tasks.billing_tasks",
        "app.workers.tasks.deployment_tasks", 
        "app.workers.tasks.plugin_tasks",
        "app.workers.tasks.monitoring_tasks",
        "app.workers.tasks.notification_tasks"
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    result_expires=3600,
    timezone="UTC",
    enable_utc=True,
    
    # Worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
    
    # Routing
    task_routes={
        "app.workers.tasks.billing_tasks.*": {"queue": "billing"},
        "app.workers.tasks.deployment_tasks.*": {"queue": "deployment"},
        "app.workers.tasks.plugin_tasks.*": {"queue": "plugins"},
        "app.workers.tasks.monitoring_tasks.*": {"queue": "monitoring"},
        "app.workers.tasks.notification_tasks.*": {"queue": "notifications"},
    },
    
    # Default queue
    task_default_queue="default",
    task_default_exchange="default",
    task_default_routing_key="default",
    
    # Retry settings
    task_default_retry_delay=60,
    task_max_retries=3,
    
    # Beat schedule for periodic tasks
    beat_schedule={
        "process-subscription-renewals": {
            "task": "app.workers.tasks.billing_tasks.process_subscription_renewals",
            "schedule": 3600.0,  # Every hour
        },
        "check-infrastructure-health": {
            "task": "app.workers.tasks.deployment_tasks.check_infrastructure_health",
            "schedule": 300.0,  # Every 5 minutes
        },
        "process-plugin-updates": {
            "task": "app.workers.tasks.plugin_tasks.process_plugin_updates",
            "schedule": 1800.0,  # Every 30 minutes
        },
        "cleanup-old-metrics": {
            "task": "app.workers.tasks.monitoring_tasks.cleanup_old_metrics",
            "schedule": 86400.0,  # Daily
        },
        "retry-failed-notifications": {
            "task": "app.workers.tasks.notification_tasks.retry_failed_notifications",
            "schedule": 600.0,  # Every 10 minutes
        },
    },
)

# Optional: Set broker transport options for Redis
if settings.redis_url.startswith("redis://"):
    celery_app.conf.broker_transport_options = {
        "visibility_timeout": 3600,
        "fanout_prefix": True,
        "fanout_patterns": True
    }