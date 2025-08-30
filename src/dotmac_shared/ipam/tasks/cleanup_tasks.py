"""
IPAM Cleanup Tasks - Automated background jobs for IPAM maintenance.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

try:
    from celery import shared_task
    from celery.exceptions import Retry

    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False

    # Mock decorator for when Celery is not available
    def shared_task(bind=False, **kwargs):
        def decorator(func):
            return func

        return decorator


try:
    from sqlalchemy import and_, func, or_
    from sqlalchemy.orm import Session

    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    Session = None

try:
    from ..core.exceptions import IPAMError
    from ..core.models import (
        AllocationStatus,
        IPAllocation,
        IPNetwork,
        IPReservation,
        ReservationStatus,
    )
    from ..repositories.ipam_repository import IPAMRepository

    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False
    IPNetwork = IPAllocation = IPReservation = None
    AllocationStatus = ReservationStatus = None
    IPAMError = Exception
    IPAMRepository = None

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def cleanup_expired_allocations(
    self, tenant_id: Optional[str] = None, batch_size: int = 100
):
    """
    Cleanup expired IP allocations.

    Args:
        tenant_id: Optional tenant filter, if None cleans all tenants
        batch_size: Number of records to process per batch

    Returns:
        Dict with cleanup statistics
    """
    if not (SQLALCHEMY_AVAILABLE and MODELS_AVAILABLE):
        logger.error("Required dependencies not available for cleanup task")
        return {"error": "Dependencies not available"}

    try:
        from dotmac_shared.database.session import get_database_session

        with get_database_session() as db:
            repository = IPAMRepository(db)

            # Build query for expired allocations
            query = db.query(IPAllocation).filter(
                IPAllocation.allocation_status == AllocationStatus.ALLOCATED,
                IPAllocation.expires_at <= datetime.utcnow(),
            )

            if tenant_id:
                query = query.filter(IPAllocation.tenant_id == tenant_id)

            # Process in batches
            total_cleaned = 0
            batch_num = 0

            while True:
                batch = query.limit(batch_size).offset(batch_num * batch_size).all()
                if not batch:
                    break

                batch_cleaned = 0
                for allocation in batch:
                    try:
                        allocation.allocation_status = AllocationStatus.EXPIRED
                        allocation.updated_at = datetime.utcnow()
                        allocation.updated_by = "system:cleanup_task"
                        batch_cleaned += 1
                    except Exception as e:
                        logger.error(
                            f"Error updating allocation {allocation.allocation_id}: {e}"
                        )

                db.commit()
                total_cleaned += batch_cleaned
                batch_num += 1

                logger.info(
                    f"Cleaned {batch_cleaned} expired allocations in batch {batch_num}"
                )

                # Break if batch was not full (last batch)
                if len(batch) < batch_size:
                    break

            logger.info(
                f"Cleanup completed: {total_cleaned} expired allocations processed"
            )

            return {
                "task": "cleanup_expired_allocations",
                "success": True,
                "tenant_id": tenant_id,
                "total_cleaned": total_cleaned,
                "batches_processed": batch_num,
                "timestamp": datetime.utcnow().isoformat(),
            }

    except Exception as exc:
        logger.error(f"Cleanup task failed: {exc}")
        # Retry on database errors
        if "database" in str(exc).lower() or "connection" in str(exc).lower():
            raise self.retry(exc=exc)

        return {
            "task": "cleanup_expired_allocations",
            "success": False,
            "error": str(exc),
            "timestamp": datetime.utcnow().isoformat(),
        }


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def cleanup_expired_reservations(
    self, tenant_id: Optional[str] = None, batch_size: int = 100
):
    """
    Cleanup expired IP reservations.

    Args:
        tenant_id: Optional tenant filter, if None cleans all tenants
        batch_size: Number of records to process per batch

    Returns:
        Dict with cleanup statistics
    """
    if not (SQLALCHEMY_AVAILABLE and MODELS_AVAILABLE):
        logger.error("Required dependencies not available for cleanup task")
        return {"error": "Dependencies not available"}

    try:
        from dotmac_shared.database.session import get_database_session

        with get_database_session() as db:
            repository = IPAMRepository(db)

            # Build query for expired reservations
            query = db.query(IPReservation).filter(
                IPReservation.reservation_status == ReservationStatus.RESERVED,
                IPReservation.expires_at <= datetime.utcnow(),
            )

            if tenant_id:
                query = query.filter(IPReservation.tenant_id == tenant_id)

            # Process in batches
            total_cleaned = 0
            batch_num = 0

            while True:
                batch = query.limit(batch_size).offset(batch_num * batch_size).all()
                if not batch:
                    break

                batch_cleaned = 0
                for reservation in batch:
                    try:
                        reservation.reservation_status = ReservationStatus.EXPIRED
                        reservation.updated_at = datetime.utcnow()
                        reservation.updated_by = "system:cleanup_task"
                        batch_cleaned += 1
                    except Exception as e:
                        logger.error(
                            f"Error updating reservation {reservation.reservation_id}: {e}"
                        )

                db.commit()
                total_cleaned += batch_cleaned
                batch_num += 1

                logger.info(
                    f"Cleaned {batch_cleaned} expired reservations in batch {batch_num}"
                )

                # Break if batch was not full (last batch)
                if len(batch) < batch_size:
                    break

            logger.info(
                f"Cleanup completed: {total_cleaned} expired reservations processed"
            )

            return {
                "task": "cleanup_expired_reservations",
                "success": True,
                "tenant_id": tenant_id,
                "total_cleaned": total_cleaned,
                "batches_processed": batch_num,
                "timestamp": datetime.utcnow().isoformat(),
            }

    except Exception as exc:
        logger.error(f"Cleanup task failed: {exc}")
        # Retry on database errors
        if "database" in str(exc).lower() or "connection" in str(exc).lower():
            raise self.retry(exc=exc)

        return {
            "task": "cleanup_expired_reservations",
            "success": False,
            "error": str(exc),
            "timestamp": datetime.utcnow().isoformat(),
        }


@shared_task(bind=True, max_retries=2, default_retry_delay=300)
def generate_utilization_report(self, tenant_id: Optional[str] = None):
    """
    Generate network utilization reports.

    Args:
        tenant_id: Optional tenant filter, if None reports on all tenants

    Returns:
        Dict with utilization statistics
    """
    if not (SQLALCHEMY_AVAILABLE and MODELS_AVAILABLE):
        logger.error("Required dependencies not available for report task")
        return {"error": "Dependencies not available"}

    try:
        from dotmac_shared.database.session import get_database_session

        with get_database_session() as db:
            repository = IPAMRepository(db)

            # Get networks to analyze
            if tenant_id:
                networks = repository.get_networks_by_tenant(tenant_id)
                tenants = [tenant_id]
            else:
                # Get all active tenants
                tenants = db.query(IPNetwork.tenant_id).distinct().all()
                tenants = [t[0] for t in tenants]
                networks = []
                for tid in tenants:
                    networks.extend(repository.get_networks_by_tenant(tid))

            report_data = {
                "task": "generate_utilization_report",
                "success": True,
                "timestamp": datetime.utcnow().isoformat(),
                "tenant_count": len(tenants),
                "network_count": len(networks),
                "tenants": {},
                "summary": {
                    "total_addresses": 0,
                    "total_allocated": 0,
                    "total_reserved": 0,
                    "average_utilization": 0,
                },
            }

            # Analyze each tenant
            for tid in tenants:
                tenant_summary = repository.get_tenant_summary(tid)
                tenant_networks = repository.get_networks_by_tenant(tid)

                tenant_data = {"summary": tenant_summary, "networks": {}}

                # Get detailed stats for each network
                for network in tenant_networks:
                    network_stats = repository.get_network_utilization_stats(
                        tid, network.network_id
                    )
                    tenant_data["networks"][str(network.network_id)] = network_stats

                    # Add to global summary
                    report_data["summary"]["total_addresses"] += network_stats[
                        "total_addresses"
                    ]
                    report_data["summary"]["total_allocated"] += network_stats[
                        "allocated_count"
                    ]
                    report_data["summary"]["total_reserved"] += network_stats[
                        "reserved_count"
                    ]

                report_data["tenants"][tid] = tenant_data

            # Calculate average utilization
            if report_data["summary"]["total_addresses"] > 0:
                total_used = (
                    report_data["summary"]["total_allocated"]
                    + report_data["summary"]["total_reserved"]
                )
                report_data["summary"]["average_utilization"] = round(
                    (total_used / report_data["summary"]["total_addresses"]) * 100, 2
                )

            logger.info(
                f"Utilization report generated for {len(tenants)} tenants, {len(networks)} networks"
            )

            return report_data

    except Exception as exc:
        logger.error(f"Report generation failed: {exc}")
        return {
            "task": "generate_utilization_report",
            "success": False,
            "error": str(exc),
            "timestamp": datetime.utcnow().isoformat(),
        }


@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def audit_ip_conflicts(self, tenant_id: Optional[str] = None):
    """
    Audit for IP address conflicts and inconsistencies.

    Args:
        tenant_id: Optional tenant filter, if None audits all tenants

    Returns:
        Dict with audit results
    """
    if not (SQLALCHEMY_AVAILABLE and MODELS_AVAILABLE):
        logger.error("Required dependencies not available for audit task")
        return {"error": "Dependencies not available"}

    try:
        from dotmac_shared.database.session import get_database_session

        with get_database_session() as db:
            conflicts = []
            inconsistencies = []

            # Query for potential conflicts
            base_query = db.query(IPAllocation.ip_address, IPAllocation.tenant_id)
            if tenant_id:
                base_query = base_query.filter(IPAllocation.tenant_id == tenant_id)

            # Find duplicate allocations
            duplicate_allocations = (
                base_query.filter(
                    IPAllocation.allocation_status == AllocationStatus.ALLOCATED
                )
                .group_by(IPAllocation.ip_address, IPAllocation.tenant_id)
                .having(func.count(IPAllocation.id) > 1)
                .all()
            )

            for ip, tid in duplicate_allocations:
                conflicts.append(
                    {
                        "type": "duplicate_allocation",
                        "ip_address": str(ip),
                        "tenant_id": tid,
                        "severity": "high",
                    }
                )

            # Find allocations in inactive networks
            inactive_network_allocations = (
                db.query(IPAllocation)
                .join(IPNetwork)
                .filter(
                    IPAllocation.allocation_status == AllocationStatus.ALLOCATED,
                    IPNetwork.is_active == False,
                )
            )
            if tenant_id:
                inactive_network_allocations = inactive_network_allocations.filter(
                    IPAllocation.tenant_id == tenant_id
                )

            for allocation in inactive_network_allocations.all():
                inconsistencies.append(
                    {
                        "type": "allocation_in_inactive_network",
                        "allocation_id": str(allocation.allocation_id),
                        "ip_address": str(allocation.ip_address),
                        "tenant_id": allocation.tenant_id,
                        "severity": "medium",
                    }
                )

            # Find long-running reservations (>24 hours)
            old_reservations = db.query(IPReservation).filter(
                IPReservation.reservation_status == ReservationStatus.RESERVED,
                IPReservation.reserved_at < datetime.utcnow() - timedelta(hours=24),
            )
            if tenant_id:
                old_reservations = old_reservations.filter(
                    IPReservation.tenant_id == tenant_id
                )

            for reservation in old_reservations.all():
                inconsistencies.append(
                    {
                        "type": "long_running_reservation",
                        "reservation_id": str(reservation.reservation_id),
                        "ip_address": str(reservation.ip_address),
                        "tenant_id": reservation.tenant_id,
                        "reserved_hours": int(
                            (
                                datetime.utcnow() - reservation.reserved_at
                            ).total_seconds()
                            / 3600
                        ),
                        "severity": "low",
                    }
                )

            return {
                "task": "audit_ip_conflicts",
                "success": True,
                "tenant_id": tenant_id,
                "timestamp": datetime.utcnow().isoformat(),
                "conflicts": conflicts,
                "inconsistencies": inconsistencies,
                "summary": {
                    "total_conflicts": len(conflicts),
                    "total_inconsistencies": len(inconsistencies),
                    "high_severity": len(
                        [
                            c
                            for c in conflicts + inconsistencies
                            if c["severity"] == "high"
                        ]
                    ),
                    "medium_severity": len(
                        [
                            c
                            for c in conflicts + inconsistencies
                            if c["severity"] == "medium"
                        ]
                    ),
                    "low_severity": len(
                        [
                            c
                            for c in conflicts + inconsistencies
                            if c["severity"] == "low"
                        ]
                    ),
                },
            }

    except Exception as exc:
        logger.error(f"Audit task failed: {exc}")
        return {
            "task": "audit_ip_conflicts",
            "success": False,
            "error": str(exc),
            "timestamp": datetime.utcnow().isoformat(),
        }


# Periodic task scheduling (if Celery Beat is available)
if CELERY_AVAILABLE:
    try:
        from celery.schedules import crontab

        # Example schedule configuration
        IPAM_CELERY_BEAT_SCHEDULE = {
            "ipam-cleanup-expired-allocations": {
                "task": "dotmac_shared.ipam.tasks.cleanup_tasks.cleanup_expired_allocations",
                "schedule": crontab(minute=0, hour="*/4"),  # Every 4 hours
                "options": {"queue": "ipam_maintenance"},
            },
            "ipam-cleanup-expired-reservations": {
                "task": "dotmac_shared.ipam.tasks.cleanup_tasks.cleanup_expired_reservations",
                "schedule": crontab(
                    minute=15, hour="*/2"
                ),  # Every 2 hours, offset by 15min
                "options": {"queue": "ipam_maintenance"},
            },
            "ipam-utilization-report": {
                "task": "dotmac_shared.ipam.tasks.cleanup_tasks.generate_utilization_report",
                "schedule": crontab(minute=0, hour=6),  # Daily at 6 AM
                "options": {"queue": "ipam_reports"},
            },
            "ipam-audit-conflicts": {
                "task": "dotmac_shared.ipam.tasks.cleanup_tasks.audit_ip_conflicts",
                "schedule": crontab(minute=30, hour=2),  # Daily at 2:30 AM
                "options": {"queue": "ipam_audit"},
            },
        }

    except ImportError:
        IPAM_CELERY_BEAT_SCHEDULE = {}
else:
    IPAM_CELERY_BEAT_SCHEDULE = {}
