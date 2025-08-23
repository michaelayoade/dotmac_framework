"""Celery application for background tasks in DotMac ISP Framework."""

import logging
from dotmac_isp.core.settings import get_settings

# Try to import Celery - if not available, provide a mock
try:
    from celery import Celery
    from kombu import Queue
    from celery.signals import task_prerun, task_postrun, task_failure, worker_ready

    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False

    # Mock classes for when Celery is not available
    class MockCelery:
        def __init__(self, *args, **kwargs):
            self.conf = self
            self.control = self
            self.broker_url = "redis://localhost:6379/1"

        def task(self, *args, **kwargs):
            def decorator(func):
                func.delay = lambda *args, **kwargs: None
                return func

            return decorator

        def send_task(self, *args, **kwargs):
            logging.warning("Celery not available - task not sent")
            return None

        def inspect(self):
            return MockInspect()

        def update(self, **kwargs):
            pass

    class MockInspect:
        def stats(self):
            return None

        def active(self):
            return None

        def scheduled(self):
            return None

    class MockQueue:
        def __init__(self, *args, **kwargs):
            pass

    Celery = MockCelery
    Queue = MockQueue

    # Mock signal decorators
    class MockSignal:
        def connect(self, func):
            return func

    task_prerun = MockSignal()
    task_postrun = MockSignal()
    task_failure = MockSignal()
    worker_ready = MockSignal()

logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Create Celery application
celery_app = Celery(
    "dotmac_isp",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "dotmac_isp.core.tasks",
        "dotmac_isp.modules.billing.tasks",
        "dotmac_isp.modules.notifications.tasks",
        "dotmac_isp.modules.services.tasks",
        "dotmac_isp.modules.analytics.tasks",
        "dotmac_isp.modules.omnichannel.tasks",
    ],
)

# Celery configuration
celery_app.conf.update(
    # Task serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Task routing
    task_routes={
        "dotmac_isp.modules.billing.*": {"queue": "billing"},
        "dotmac_isp.modules.notifications.*": {"queue": "notifications"},
        "dotmac_isp.modules.services.*": {"queue": "services"},
        "dotmac_isp.modules.analytics.*": {"queue": "analytics"},
        "dotmac_isp.modules.omnichannel.*": {"queue": "omnichannel"},
        "dotmac_isp.core.*": {"queue": "default"},
    },
    # Define queues
    task_default_queue="default",
    task_queues=(
        Queue("default", routing_key="default"),
        Queue("billing", routing_key="billing"),
        Queue("notifications", routing_key="notifications"),
        Queue("services", routing_key="services"),
        Queue("analytics", routing_key="analytics"),
        Queue("priority", routing_key="priority"),
    ),
    # Task execution
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    # Result backend settings
    result_expires=3600,  # 1 hour
    result_backend_max_retries=10,
    result_backend_retry_delay=0.2,
    # Beat (scheduler) configuration
    beat_schedule=(
        {}
        if not CELERY_AVAILABLE
        else {
            "health-check": {
                "task": "dotmac_isp.core.tasks.health_check",
                "schedule": 300.0,  # Every 5 minutes
                "options": {"queue": "default"},
            },
            "cleanup-sessions": {
                "task": "dotmac_isp.core.tasks.cleanup_expired_sessions",
                "schedule": 3600.0,  # Every hour
                "options": {"queue": "default"},
            },
            "generate-analytics": {
                "task": "dotmac_isp.modules.analytics.tasks.generate_daily_reports",
                "schedule": 86400.0,  # Daily
                "options": {"queue": "analytics"},
            },
            "renew-ssl-certificates": {
                "task": "dotmac_isp.core.tasks.renew_ssl_certificates",
                "schedule": 86400.0,  # Daily
                "options": {"queue": "default"},
            },
        }
    ),
    # Worker configuration
    worker_max_tasks_per_child=1000,
    worker_disable_rate_limits=False,
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
    # Error handling
    task_annotations={
        "*": {
            "rate_limit": "100/m",  # 100 tasks per minute max
            "time_limit": 300,  # 5 minutes hard timeout
            "soft_time_limit": 240,  # 4 minutes soft timeout
        },
        "dotmac_isp.modules.billing.*": {
            "rate_limit": "10/m",  # Billing tasks are slower
            "time_limit": 600,  # 10 minutes for billing
            "soft_time_limit": 540,
        },
        "dotmac_isp.modules.analytics.*": {
            "rate_limit": "5/m",  # Analytics can be resource intensive
            "time_limit": 1800,  # 30 minutes for analytics
            "soft_time_limit": 1620,
        },
    },
)


@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery setup."""
    print(f"Request: {self.request!r}")
    return {"status": "success", "worker_id": self.request.id}


# Task decorator shortcuts
def task(**kwargs):
    """Decorator shortcut for creating Celery tasks."""
    return celery_app.task(**kwargs)


def periodic_task(**kwargs):
    """Decorator shortcut for creating periodic Celery tasks."""
    return celery_app.task(bind=True, **kwargs)


# Celery signals for monitoring
from celery.signals import task_prerun, task_postrun, task_failure, worker_ready


@task_prerun.connect
def task_prerun_handler(
    sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds
):
    """Log task start."""
    logger.info(f"Task {task.name} [{task_id}] started")


@task_postrun.connect
def task_postrun_handler(
    sender=None,
    task_id=None,
    task=None,
    args=None,
    kwargs=None,
    retval=None,
    state=None,
    **kwds,
):
    """Log task completion."""
    logger.info(f"Task {task.name} [{task_id}] completed with state: {state}")


@task_failure.connect
def task_failure_handler(
    sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwds
):
    """Log task failure."""
    logger.error(f"Task {sender.name} [{task_id}] failed: {exception}")


@worker_ready.connect
def worker_ready_handler(sender=None, **kwds):
    """Log worker ready."""
    logger.info(f"Celery worker {sender.hostname} ready")


if __name__ == "__main__":
    celery_app.start()
