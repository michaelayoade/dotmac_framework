"""
Audit SDK - Contract-first audit logging and compliance tracking.

Provides comprehensive audit logging, compliance reporting, and security event tracking
with multi-tenant isolation and configurable retention policies.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from dotmac_isp.sdks.contracts.audit import (
    AuditEvent,
    AuditEventType,
    AuditExportRequest,
    AuditExportResponse,
    AuditHealthCheck,
    AuditOutcome,
    AuditQuery,
    AuditQueryResponse,
    AuditRetentionPolicy,
    AuditSeverity,
    AuditStats,
)
from dotmac_isp.sdks.contracts.transport import RequestContext
from dotmac_isp.sdks.platform.utils.datetime_compat import UTC

logger = logging.getLogger(__name__)


class AuditSDKConfig:
    """Audit SDK configuration."""

    def __init__(  # noqa: PLR0913
        self,
        enable_async_processing: bool = True,
        batch_size: int = 100,
        batch_timeout_seconds: int = 5,
        max_queue_size: int = 10000,
        default_retention_days: int = 365,
        enable_compression: bool = True,
        enable_encryption: bool = True,
        storage_backend: str = "database",  # database, s3, elasticsearch
        export_max_events: int = 100000,
        enable_real_time_alerts: bool = True,
    ):
        self.enable_async_processing = enable_async_processing
        self.batch_size = batch_size
        self.batch_timeout_seconds = batch_timeout_seconds
        self.max_queue_size = max_queue_size
        self.default_retention_days = default_retention_days
        self.enable_compression = enable_compression
        self.enable_encryption = enable_encryption
        self.storage_backend = storage_backend
        self.export_max_events = export_max_events
        self.enable_real_time_alerts = enable_real_time_alerts


class AuditSDK:
    """
    Contract-first Audit SDK with comprehensive logging and compliance.

    Features:
    - Multi-tenant audit event logging
    - Configurable retention policies
    - Real-time and batch processing
    - Compliance reporting and exports
    - Security event monitoring
    - Performance metrics and health checks
    - Immutable audit trails
    """

    def __init__(
        self,
        config: AuditSDKConfig | None = None,
        database_sdk: Any | None = None,
        cache_sdk: Any | None = None,
        file_storage_sdk: Any | None = None,
    ):
        """Initialize Audit SDK."""
        self.config = config or AuditSDKConfig()
        self.database_sdk = database_sdk
        self.cache_sdk = cache_sdk
        self.file_storage_sdk = file_storage_sdk

        # In-memory storage for testing/development
        self._events: dict[str, list[AuditEvent]] = {}  # tenant_id -> events
        self._retention_policies: dict[str, AuditRetentionPolicy] = (
            {}
        )  # tenant_id -> policy
        self._exports: dict[str, dict[str, Any]] = {}  # export_id -> export_data

        # Processing queue for async events
        self._event_queue: asyncio.Queue = asyncio.Queue(
            maxsize=self.config.max_queue_size
        )
        self._processing_task: asyncio.Task | None = None
        self._stats_cache: dict[str, dict[str, Any]] = {}  # tenant_id -> cached_stats

        logger.info("AuditSDK initialized")

    async def log_event(  # noqa: C901
        self,
        event: AuditEvent,
        context: RequestContext | None = None,
    ) -> bool:
        """Log an audit event."""
        try:
            # Set event ID if not provided
            if not event.id:
                event.id = uuid4()

            # Set timestamp if not provided
            if not event.timestamp:
                event.timestamp = datetime.now(UTC)

            # Add context information if available
            if context:
                if not event.request_id:
                    event.request_id = context.headers.x_request_id
                if not event.correlation_id:
                    event.correlation_id = context.headers.x_correlation_id
                if not event.trace_id:
                    event.trace_id = context.headers.x_trace_id
                if not event.ip_address:
                    event.ip_address = getattr(context, "client_ip", None)
                if not event.user_agent:
                    event.user_agent = context.user_agent

            # Process event based on configuration
            if self.config.enable_async_processing:
                await self._queue_event(event)
            else:
                await self._store_event(event)

            # Real-time alerts for critical events
            if (
                self.config.enable_real_time_alerts
                and event.severity == AuditSeverity.CRITICAL
            ):
                await self._trigger_alert(event)

            return True

        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
            return False

    async def log_auth_event(
        self,
        tenant_id: UUID,
        event_type: AuditEventType,
        user_id: str | None = None,
        outcome: AuditOutcome = AuditOutcome.SUCCESS,
        details: dict[str, Any] | None = None,
        context: RequestContext | None = None,
    ) -> bool:
        """Log authentication/authorization event."""
        event = AuditEvent(
            tenant_id=tenant_id,
            event_type=event_type,
            timestamp=datetime.now(UTC),
            severity=(
                AuditSeverity.MEDIUM
                if outcome == AuditOutcome.SUCCESS
                else AuditSeverity.HIGH
            ),
            outcome=outcome,
            user_id=user_id,
            description=f"Authentication event: {event_type.value}",
            details=details or {},
        )

        return await self.log_event(event, context)

    async def log_data_event(  # noqa: PLR0913
        self,
        tenant_id: UUID,
        event_type: AuditEventType,
        resource_type: str,
        resource_id: str,
        resource_name: str | None = None,
        user_id: str | None = None,
        old_values: dict[str, Any] | None = None,
        new_values: dict[str, Any] | None = None,
        context: RequestContext | None = None,
    ) -> bool:
        """Log data access/modification event."""
        event = AuditEvent(
            tenant_id=tenant_id,
            event_type=event_type,
            timestamp=datetime.now(UTC),
            severity=(
                AuditSeverity.LOW
                if event_type == AuditEventType.DATA_READ
                else AuditSeverity.MEDIUM
            ),
            outcome=AuditOutcome.SUCCESS,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            description=f"Data {event_type.value} on {resource_type}",
            old_values=old_values,
            new_values=new_values,
        )

        return await self.log_event(event, context)

    async def log_security_event(
        self,
        tenant_id: UUID,
        event_type: AuditEventType,
        severity: AuditSeverity = AuditSeverity.HIGH,
        description: str = "",
        details: dict[str, Any] | None = None,
        context: RequestContext | None = None,
    ) -> bool:
        """Log security-related event."""
        event = AuditEvent(
            tenant_id=tenant_id,
            event_type=event_type,
            timestamp=datetime.now(UTC),
            severity=severity,
            outcome=AuditOutcome.FAILURE,
            description=description or f"Security event: {event_type.value}",
            details=details or {},
        )

        return await self.log_event(event, context)

    async def query_events(
        self,
        query: AuditQuery,
        context: RequestContext | None = None,
    ) -> AuditQueryResponse:
        """Query audit events with filtering and pagination."""
        try:
            tenant_events = self._events.get(str(query.tenant_id), [])

            # Apply filters
            filtered_events = self._apply_filters(tenant_events, query)

            # Apply sorting
            sorted_events = self._apply_sorting(
                filtered_events, query.sort_by, query.sort_order
            )

            # Apply pagination
            total_count = len(sorted_events)
            start_idx = (query.page - 1) * query.per_page
            end_idx = start_idx + query.per_page
            page_events = sorted_events[start_idx:end_idx]

            total_pages = (total_count + query.per_page - 1) // query.per_page

            return AuditQueryResponse(
                events=page_events,
                total_count=total_count,
                page=query.page,
                per_page=query.per_page,
                total_pages=total_pages,
            )

        except Exception as e:
            logger.error(f"Failed to query audit events: {e}")
            return AuditQueryResponse(
                events=[],
                total_count=0,
                page=query.page,
                per_page=query.per_page,
                total_pages=0,
            )

    async def get_stats(
        self,
        tenant_id: UUID,
        context: RequestContext | None = None,
    ) -> AuditStats:
        """Get audit statistics for tenant."""
        try:
            # Check cache first
            cache_key = f"audit_stats:{tenant_id}"
            if self.cache_sdk and cache_key in self._stats_cache:
                cached_stats = self._stats_cache[cache_key]
                if cached_stats["expires_at"] > datetime.now(UTC):
                    return AuditStats(**cached_stats["data"])

            tenant_events = self._events.get(str(tenant_id), [])

            # Calculate statistics
            stats = self._calculate_stats(tenant_id, tenant_events)

            # Cache results
            if self.cache_sdk:
                self._stats_cache[cache_key] = {
                    "data": stats.model_dump(),
                    "expires_at": datetime.now(UTC) + timedelta(minutes=15),
                }

            return stats

        except Exception as e:
            logger.error(f"Failed to get audit stats: {e}")
            return AuditStats(
                tenant_id=tenant_id,
                total_events=0,
                events_by_type={},
                events_by_severity={},
                events_by_outcome={},
                events_last_hour=0,
                events_last_day=0,
                events_last_week=0,
                events_last_month=0,
                top_users=[],
                top_resources=[],
                failed_logins=0,
                security_violations=0,
                retention_summary={},
            )

    async def export_events(
        self,
        request: AuditExportRequest,
        context: RequestContext | None = None,
    ) -> AuditExportResponse:
        """Export audit events for compliance."""
        try:
            export_id = uuid4()

            # Create export job
            export_data = {
                "id": export_id,
                "status": "processing",
                "request": request.model_dump(),
                "created_at": datetime.now(UTC),
                "total_events": 0,
                "file_size_bytes": None,
                "download_url": None,
                "expires_at": None,
            }

            self._exports[str(export_id)] = export_data

            # Start async export processing
            if self.config.enable_async_processing:
                asyncio.create_task(self._process_export(export_id, request))
            else:
                await self._process_export(export_id, request)

            return AuditExportResponse(
                export_id=export_id,
                status="processing",
                download_url=None,
                expires_at=None,
                total_events=0,
                file_size_bytes=None,
                created_at=datetime.now(UTC),
            )

        except Exception as e:
            logger.error(f"Failed to create export: {e}")
            raise

    async def set_retention_policy(
        self,
        policy: AuditRetentionPolicy,
        context: RequestContext | None = None,
    ) -> bool:
        """Set audit log retention policy for tenant."""
        try:
            if not policy.id:
                policy.id = uuid4()

            policy.updated_at = datetime.now(UTC)
            if not policy.created_at:
                policy.created_at = datetime.now(UTC)

            self._retention_policies[str(policy.tenant_id)] = policy

            # Log policy change
            await self.log_event(
                AuditEvent(
                    tenant_id=policy.tenant_id,
                    event_type=AuditEventType.CONFIG_CHANGE,
                    timestamp=datetime.now(UTC),
                    severity=AuditSeverity.MEDIUM,
                    outcome=AuditOutcome.SUCCESS,
                    description="Audit retention policy updated",
                    details={
                        "policy_id": str(policy.id),
                        "retention_days": policy.default_retention_days,
                    },
                ),
                context,
            )

            return True

        except Exception as e:
            logger.error(f"Failed to set retention policy: {e}")
            return False

    async def health_check(self) -> AuditHealthCheck:
        """Perform health check."""
        try:
            now = datetime.now(UTC)

            # Calculate metrics
            total_events = sum(len(events) for events in self._events.values())
            events_last_minute = sum(
                len([e for e in events if (now - e.timestamp).total_seconds() < 60])
                for events in self._events.values()
            )

            return AuditHealthCheck(
                status="healthy",
                timestamp=now,
                storage_available=True,
                storage_usage_percent=None,
                avg_write_latency_ms=1.5,
                avg_query_latency_ms=25.0,
                events_processed_last_minute=events_last_minute,
                processing_queue_size=(
                    self._event_queue.qsize() if self._event_queue else 0
                ),
                retention_job_last_run=None,
                retention_job_status="not_configured",
                details={
                    "total_events": total_events,
                    "tenants_count": len(self._events),
                    "exports_active": len(
                        [
                            e
                            for e in self._exports.values()
                            if e["status"] == "processing"
                        ]
                    ),
                },
            )

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return AuditHealthCheck(
                status="unhealthy",
                timestamp=datetime.now(UTC),
                storage_available=False,
                avg_write_latency_ms=None,
                avg_query_latency_ms=None,
                events_processed_last_minute=0,
                processing_queue_size=0,
                details={"error": str(e)},
            )

    # Private helper methods

    async def _queue_event(self, event: AuditEvent) -> None:
        """Queue event for async processing."""
        try:
            await self._event_queue.put(event)

            # Start processing task if not running
            if not self._processing_task or self._processing_task.done():
                self._processing_task = asyncio.create_task(self._process_event_queue())

        except asyncio.QueueFull:
            logger.error("Audit event queue is full, dropping event")
            # In production, you might want to use a persistent queue

    async def _process_event_queue(self) -> None:
        """Process events from the queue in batches."""
        batch = []

        while True:
            try:
                # Wait for events with timeout
                try:
                    event = await asyncio.wait_for(
                        self._event_queue.get(),
                        timeout=self.config.batch_timeout_seconds,
                    )
                    batch.append(event)
                except TimeoutError:
                    pass

                # Process batch when full or timeout reached
                if len(batch) >= self.config.batch_size or (
                    batch and self._event_queue.empty()
                ):
                    await self._store_events_batch(batch)
                    batch = []

                # Exit if queue is empty and no pending events
                if self._event_queue.empty() and not batch:
                    break

            except Exception as e:
                logger.error(f"Error processing event queue: {e}")
                await asyncio.sleep(1)

    async def _store_event(self, event: AuditEvent) -> None:
        """Store single audit event."""
        tenant_id = str(event.tenant_id)

        if tenant_id not in self._events:
            self._events[tenant_id] = []

        self._events[tenant_id].append(event)

        # Clear stats cache for tenant
        cache_key = f"audit_stats:{tenant_id}"
        if cache_key in self._stats_cache:
            del self._stats_cache[cache_key]

    async def _store_events_batch(self, events: list[AuditEvent]) -> None:
        """Store batch of audit events."""
        for event in events:
            await self._store_event(event)

    async def _trigger_alert(self, event: AuditEvent) -> None:
        """Trigger real-time alert for critical events."""
        logger.warning(
            f"CRITICAL AUDIT EVENT: {event.description} (Tenant: {event.tenant_id})"
        )
        # In production, integrate with alerting system

    def _apply_filters(
        self, events: list[AuditEvent], query: AuditQuery
    ) -> list[AuditEvent]:
        """Apply query filters to events."""
        filtered = events

        # Time range filter
        if query.start_time:
            filtered = [e for e in filtered if e.timestamp >= query.start_time]
        if query.end_time:
            filtered = [e for e in filtered if e.timestamp <= query.end_time]

        # Event type filter
        if query.event_types:
            filtered = [e for e in filtered if e.event_type in query.event_types]

        # Severity filter
        if query.severities:
            filtered = [e for e in filtered if e.severity in query.severities]

        # Outcome filter
        if query.outcomes:
            filtered = [e for e in filtered if e.outcome in query.outcomes]

        # User filter
        if query.user_ids:
            filtered = [e for e in filtered if e.user_id in query.user_ids]

        # Resource type filter
        if query.resource_types:
            filtered = [e for e in filtered if e.resource_type in query.resource_types]

        # Resource ID filter
        if query.resource_ids:
            filtered = [e for e in filtered if e.resource_id in query.resource_ids]

        # Text search
        if query.search_text:
            search_lower = query.search_text.lower()
            filtered = [
                e
                for e in filtered
                if search_lower in e.description.lower()
                or any(search_lower in str(v).lower() for v in e.details.values())
            ]

        return filtered

    def _apply_sorting(
        self, events: list[AuditEvent], sort_by: str, sort_order: str
    ) -> list[AuditEvent]:
        """Apply sorting to events."""
        reverse = sort_order == "desc"

        if sort_by == "timestamp":
            return sorted(events, key=lambda e: e.timestamp, reverse=reverse)
        elif sort_by == "severity":
            severity_order = {"low": 1, "medium": 2, "high": 3, "critical": 4}
            return sorted(
                events,
                key=lambda e: severity_order.get(e.severity.value, 0),
                reverse=reverse,
            )
        else:
            return events

    def _calculate_stats(self, tenant_id: UUID, events: list[AuditEvent]) -> AuditStats:
        """Calculate audit statistics."""
        now = datetime.now(UTC)

        # Event counts by type
        events_by_type = {}
        events_by_severity = {}
        events_by_outcome = {}

        for event in events:
            events_by_type[event.event_type.value] = (
                events_by_type.get(event.event_type.value, 0) + 1
            )
            events_by_severity[event.severity.value] = (
                events_by_severity.get(event.severity.value, 0) + 1
            )
            events_by_outcome[event.outcome.value] = (
                events_by_outcome.get(event.outcome.value, 0) + 1
            )

        # Time-based counts
        events_last_hour = len(
            [e for e in events if (now - e.timestamp).total_seconds() < 3600]
        )
        events_last_day = len(
            [e for e in events if (now - e.timestamp).total_seconds() < 86400]
        )
        events_last_week = len(
            [e for e in events if (now - e.timestamp).total_seconds() < 604800]
        )
        events_last_month = len(
            [e for e in events if (now - e.timestamp).total_seconds() < 2592000]
        )

        # Security metrics
        failed_logins = len(
            [e for e in events if e.event_type == AuditEventType.LOGIN_FAILED]
        )
        security_violations = len(
            [e for e in events if e.event_type == AuditEventType.SECURITY_VIOLATION]
        )

        # Calculate user activity ranking
        user_activity = {}
        resource_activity = {}
        retention_by_type = {}
        
        for event in events:
            # User ranking - count events per user
            if event.user_id:
                user_activity[event.user_id] = user_activity.get(event.user_id, 0) + 1
                
            # Resource ranking - count events per resource
            if hasattr(event, 'resource_id') and event.resource_id:
                resource_activity[event.resource_id] = resource_activity.get(event.resource_id, 0) + 1
                
            # Retention summary - calculate retention by event type
            event_type = event.event_type.value
            if event_type not in retention_by_type:
                retention_by_type[event_type] = {'total': 0, 'retained_days': 0}
            retention_by_type[event_type]['total'] += 1
            
            # Calculate how long ago this event occurred
            if hasattr(event, 'timestamp') and event.timestamp:
                days_ago = (now - event.timestamp).days
                retention_by_type[event_type]['retained_days'] = max(
                    retention_by_type[event_type]['retained_days'], 
                    days_ago
                )
        
        # Get top 10 most active users
        top_users = sorted(user_activity.items(), key=lambda x: x[1], reverse=True)[:10]
        top_users_list = [
            {"user_id": user_id, "event_count": count} 
            for user_id, count in top_users
        ]
        
        # Get top 10 most accessed resources
        top_resources = sorted(resource_activity.items(), key=lambda x: x[1], reverse=True)[:10]
        top_resources_list = [
            {"resource_id": resource_id, "access_count": count} 
            for resource_id, count in top_resources
        ]
        
        # Build retention summary
        retention_summary = {}
        for event_type, data in retention_by_type.items():
            avg_retention = data['retained_days'] / max(data['total'], 1)
            retention_summary[event_type] = {
                "total_events": data['total'],
                "max_retention_days": data['retained_days'],
                "avg_retention_days": round(avg_retention, 1)
            }

        return AuditStats(
            tenant_id=tenant_id,
            total_events=len(events),
            events_by_type=events_by_type,
            events_by_severity=events_by_severity,
            events_by_outcome=events_by_outcome,
            events_last_hour=events_last_hour,
            events_last_day=events_last_day,
            events_last_week=events_last_week,
            events_last_month=events_last_month,
            top_users=top_users_list,
            top_resources=top_resources_list,
            failed_logins=failed_logins,
            security_violations=security_violations,
            retention_summary=retention_summary,
        )

    async def _process_export(
        self, export_id: UUID, request: AuditExportRequest
    ) -> None:
        """Process audit export request."""
        try:
            export_data = self._exports[str(export_id)]

            # Query events
            query_response = await self.query_events(request.query)

            # Generate export file (simplified)
            export_content = self._generate_export_content(
                query_response.events, request.format
            )

            # Update export status
            export_data.update(
                {
                    "status": "completed",
                    "total_events": query_response.total_count,
                    "file_size_bytes": len(export_content.encode()),
                    "download_url": f"/api/v1/audit/exports/{export_id}/download",
                    "expires_at": datetime.now(UTC) + timedelta(hours=24),
                }
            )

        except Exception as e:
            logger.error(f"Export processing failed: {e}")
            self._exports[str(export_id)]["status"] = "failed"

    def _generate_export_content(self, events: list[AuditEvent], format: str) -> str:
        """Generate export content in specified format."""
        if format == "json":
            import json

            return json.dumps(
                [event.model_dump() for event in events], indent=2, default=str
            )
        elif format == "csv":
            # Simplified CSV generation
            import csv
            import io

            output = io.StringIO()
            if events:
                writer = csv.DictWriter(
                    output, fieldnames=events[0].model_dump().keys()
                )
                writer.writeheader()
                for event in events:
                    writer.writerow(event.model_dump())
            return output.getvalue()
        else:
            return str(events)  # Fallback
