"""
IPAM Configuration Examples and Production Setup Guide.
"""

from datetime import timedelta
from typing import Any, Dict

# Production IPAM Configuration Example
PRODUCTION_IPAM_CONFIG = {
    # Network configuration
    "network": {
        "allow_overlapping_networks": False,  # Strict network isolation
        "default_dhcp_enabled": False,
        "supernet": "10.0.0.0/8",  # Default supernet for planning
        "reserved_ranges": ["10.0.0.0/24", "10.255.255.0/24"],  # Management  # Reserved
    },
    # Allocation settings
    "allocation": {
        "default_lease_time": 86400,  # 24 hours
        "max_lease_time": 2592000,  # 30 days
        "auto_release_expired": True,
        "conflict_detection": True,
        "max_bulk_allocation": 100,
    },
    # Reservation settings
    "reservation": {
        "default_reservation_time": 3600,  # 1 hour
        "max_reservation_time": 86400,  # 24 hours
        "cleanup_interval": 1800,  # 30 minutes
    },
    # Performance optimization
    "performance": {
        "enable_batch_scanning": True,
        "batch_size": 1000,
        "enable_caching": True,
        "cache_ttl": 300,  # 5 minutes
        "large_network_threshold": 1024,
    },
    # Rate limiting
    "rate_limiting": {
        "enabled": True,
        "redis_url": "redis://localhost:6379/0",
        "default_limits": {
            "allocate_ip": {"requests": 100, "window": 3600, "burst": 10},
            "create_network": {"requests": 10, "window": 3600, "burst": 2},
            "bulk_allocation": {"requests": 5, "window": 3600, "burst": 1},
        },
    },
    # Audit and logging
    "audit": {
        "enable_logging": True,
        "log_level": "INFO",
        "retention_days": 90,
        "sensitive_fields": ["mac_address", "hostname"],
    },
    # MAC address handling
    "mac_validation": {
        "enabled": True,
        "strict_validation": True,
        "normalize_format": True,
    },
    # Network planning
    "planning": {
        "enable_auto_planning": True,
        "default_growth_factor": 1.5,
        "subnet_purposes": {
            "customer": {"default_size": 24, "growth_factor": 1.8},
            "infrastructure": {"default_size": 26, "growth_factor": 1.2},
            "management": {"default_size": 27, "growth_factor": 1.1},
        },
    },
    # Analytics and monitoring
    "analytics": {
        "enabled": True,
        "default_growth_rate": 10.0,  # 10% monthly
        "utilization_thresholds": {
            "warning": 75.0,
            "critical": 85.0,
            "emergency": 95.0,
        },
        "report_schedule": "daily",
    },
    # Database settings
    "database": {
        "pool_size": 20,
        "max_overflow": 30,
        "pool_timeout": 30,
        "pool_recycle": 3600,
        "echo": False,  # Set to True for SQL debugging
    },
    # Security settings
    "security": {
        "require_authentication": True,
        "tenant_isolation": True,
        "encrypt_sensitive_data": True,
        "audit_all_operations": True,
    },
}


# Development IPAM Configuration
DEVELOPMENT_IPAM_CONFIG = {
    "network": {
        "allow_overlapping_networks": True,  # More permissive for testing
        "default_dhcp_enabled": True,
    },
    "allocation": {
        "default_lease_time": 3600,  # 1 hour for faster testing
        "max_lease_time": 86400,
        "auto_release_expired": True,
        "conflict_detection": True,
    },
    "performance": {
        "enable_batch_scanning": False,  # Simpler debugging
        "enable_caching": False,
    },
    "rate_limiting": {"enabled": False},  # Disabled for development
    "audit": {"enable_logging": True, "log_level": "DEBUG"},
    "mac_validation": {
        "enabled": True,
        "strict_validation": False,  # More lenient for testing
    },
    "database": {"echo": True},  # Enable SQL logging for debugging
}


# Celery task configuration for IPAM
CELERY_IPAM_CONFIG = {
    # Task routing
    "task_routes": {
        "dotmac_shared.ipam.tasks.cleanup_tasks.*": {"queue": "ipam_maintenance"},
        "dotmac_shared.ipam.tasks.analytics.*": {"queue": "ipam_analytics"},
    },
    # Beat schedule for periodic tasks
    "beat_schedule": {
        "ipam-cleanup-expired-allocations": {
            "task": "dotmac_shared.ipam.tasks.cleanup_tasks.cleanup_expired_allocations",
            "schedule": 14400.0,  # Every 4 hours
            "options": {"queue": "ipam_maintenance"},
        },
        "ipam-cleanup-expired-reservations": {
            "task": "dotmac_shared.ipam.tasks.cleanup_tasks.cleanup_expired_reservations",
            "schedule": 7200.0,  # Every 2 hours
            "options": {"queue": "ipam_maintenance"},
        },
        "ipam-generate-utilization-report": {
            "task": "dotmac_shared.ipam.tasks.cleanup_tasks.generate_utilization_report",
            "schedule": 86400.0,  # Daily
            "options": {"queue": "ipam_analytics"},
        },
        "ipam-audit-conflicts": {
            "task": "dotmac_shared.ipam.tasks.cleanup_tasks.audit_ip_conflicts",
            "schedule": 86400.0,  # Daily
            "options": {"queue": "ipam_audit"},
        },
    },
    # Task configuration
    "task_serializer": "json",
    "accept_content": ["json"],
    "result_serializer": "json",
    "timezone": "UTC",
    "enable_utc": True,
    # Result backend
    "result_backend": "redis://localhost:6379/1",
    "result_expires": 3600,
    # Worker configuration
    "worker_prefetch_multiplier": 1,
    "task_acks_late": True,
    "worker_disable_rate_limits": False,
}


# Network planning templates
NETWORK_PLANNING_TEMPLATES = {
    "small_isp": {
        "supernet": "10.0.0.0/16",
        "requirements": [
            {
                "purpose": "customer",
                "min_hosts": 1000,
                "growth_factor": 2.0,
                "priority": 1,
                "location": "primary",
            },
            {
                "purpose": "infrastructure",
                "min_hosts": 50,
                "growth_factor": 1.3,
                "priority": 2,
            },
            {
                "purpose": "management",
                "min_hosts": 20,
                "growth_factor": 1.2,
                "priority": 3,
            },
        ],
    },
    "enterprise": {
        "supernet": "172.16.0.0/12",
        "requirements": [
            {
                "purpose": "customer",
                "min_hosts": 5000,
                "growth_factor": 1.5,
                "priority": 1,
            },
            {"purpose": "dmz", "min_hosts": 100, "growth_factor": 1.4, "priority": 2},
            {"purpose": "voice", "min_hosts": 500, "growth_factor": 1.6, "priority": 2},
            {"purpose": "guest", "min_hosts": 200, "growth_factor": 2.0, "priority": 3},
        ],
    },
}


# Usage examples
def get_ipam_config(environment: str = "production") -> Dict[str, Any]:
    """Get IPAM configuration for specific environment."""
    configs = {
        "production": PRODUCTION_IPAM_CONFIG,
        "development": DEVELOPMENT_IPAM_CONFIG,
        "testing": DEVELOPMENT_IPAM_CONFIG,
    }

    return configs.get(environment, PRODUCTION_IPAM_CONFIG)


def setup_enhanced_ipam_service(
    database_session, environment: str = "production", redis_url: Optional[str] = None
):
    """Setup enhanced IPAM service with full configuration."""
    from .enhanced_service import EnhancedIPAMService
    from .middleware.rate_limiting import (
        create_memory_rate_limiter,
        create_redis_rate_limiter,
    )

    # Get configuration
    config = get_ipam_config(environment)

    # Setup rate limiter
    rate_limiter = None
    if config.get("rate_limiting", {}).get("enabled", False):
        if redis_url or config.get("rate_limiting", {}).get("redis_url"):
            rate_limiter = create_redis_rate_limiter(
                redis_url or config["rate_limiting"]["redis_url"],
                default_limits=config["rate_limiting"]["default_limits"],
            )
        else:
            rate_limiter = create_memory_rate_limiter(
                default_limits=config["rate_limiting"]["default_limits"]
            )

    # Create service
    service = EnhancedIPAMService(
        database_session=database_session, config=config, rate_limiter=rate_limiter
    )

    return service


# Integration examples
FASTAPI_INTEGRATION_EXAMPLE = """
# FastAPI Integration Example

from fastapi import FastAPI, Depends, HTTPException
from .enhanced_service import EnhancedIPAMService
from .middleware.rate_limiting import IPAMRateLimitMiddleware

app = FastAPI()

# Setup IPAM service
async def get_ipam_service():
    # Your database session setup here
    db_session = get_db_session()
    return setup_enhanced_ipam_service(db_session, "production")

# Add rate limiting middleware
ipam_service = get_ipam_service()
if ipam_service.rate_limiter:
    app.add_middleware(
        IPAMRateLimitMiddleware,
        rate_limiter=ipam_service.rate_limiter
    )

@app.post("/api/ipam/allocations")
async def allocate_ip(
    allocation_request: dict,
    tenant_id: str,
    ipam: EnhancedIPAMService = Depends(get_ipam_service)
):
    try:
        result = await ipam.allocate_ip(tenant_id, **allocation_request)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
"""

DJANGO_INTEGRATION_EXAMPLE = """
# Django Integration Example

# settings.py
IPAM_CONFIG = get_ipam_config("production")

CELERY_BEAT_SCHEDULE = CELERY_IPAM_CONFIG["beat_schedule"]

# services.py
from django.conf import settings
from .enhanced_service import EnhancedIPAMService

class IPAMServiceManager:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = setup_enhanced_ipam_service(
                database_session=None,  # Use Django ORM adapter
                environment="production"
            )
        return cls._instance

# views.py
from rest_framework import views, status
from rest_framework.response import Response

class IPAllocationView(views.APIView):
    def post(self, request, tenant_id):
        ipam = IPAMServiceManager.get_instance()
        try:
            result = await ipam.allocate_ip(tenant_id, **request.data)
            return Response(result, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
"""
