"""
Webhooks SDK - Contract-first webhook management.

Provides webhook registration, delivery, retry logic, and monitoring
with multi-tenant isolation and comprehensive event handling.
"""

import asyncio
import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import httpx

from dotmac_isp.sdks.contracts.transport import RequestContext
from dotmac_isp.sdks.contracts.webhooks import (
    Webhook,
    WebhookDelivery,
    WebhookDeliveryQuery,
    WebhookDeliveryStatus,
    WebhookEvent,
    WebhookHealthCheck,
    WebhookPayload,
    WebhookQuery,
    WebhookSecurityType,
    WebhookStats,
    WebhookStatus,
)
from dotmac_isp.sdks.platform.utils.datetime_compat import UTC

logger = logging.getLogger(__name__)


class WebhooksSDKConfig:
    """Webhooks SDK configuration."""

    def __init__(self, # noqa: PLR0913
        max_webhooks_per_tenant: int = 100,
        max_delivery_attempts: int = 10,
        default_timeout_seconds: int = 30,
        delivery_queue_size: int = 10000,
        retry_queue_size: int = 5000,
        batch_delivery_size: int = 50,
        delivery_worker_count: int = 5,
        enable_signature_verification: bool = True,
        max_payload_size_bytes: int = 1024 * 1024,  # 1MB
        delivery_history_retention_days: int = 30,
    ):
        self.max_webhooks_per_tenant = max_webhooks_per_tenant
        self.max_delivery_attempts = max_delivery_attempts
        self.default_timeout_seconds = default_timeout_seconds
        self.delivery_queue_size = delivery_queue_size
        self.retry_queue_size = retry_queue_size
        self.batch_delivery_size = batch_delivery_size
        self.delivery_worker_count = delivery_worker_count
        self.enable_signature_verification = enable_signature_verification
        self.max_payload_size_bytes = max_payload_size_bytes
        self.delivery_history_retention_days = delivery_history_retention_days


class WebhooksSDK:
    """
    Contract-first Webhooks SDK with reliable delivery.

    Features:
    - Multi-tenant webhook management
    - Reliable delivery with retry logic
    - Multiple security mechanisms (HMAC, Bearer, Basic Auth, API Key)
    - Event filtering and routing
    - Delivery monitoring and statistics
    - Async batch processing
    - Comprehensive audit logging
    - Health monitoring and alerting
    """

    def __init__(
        self,
        config: WebhooksSDKConfig | None = None,
        audit_sdk: Any | None = None,
    ):
        """Initialize Webhooks SDK."""
        self.config = config or WebhooksSDKConfig()
        self.audit_sdk = audit_sdk

        # In-memory storage for testing/development
        self._webhooks: dict[str, dict[str, Webhook]] = (
            {}
        )  # tenant_id -> webhook_id -> webhook
        self._deliveries: dict[str, list[WebhookDelivery]] = (
            {}
        )  # tenant_id -> deliveries
        self._delivery_queue: asyncio.Queue = asyncio.Queue(
            maxsize=self.config.delivery_queue_size
        )
        self._retry_queue: asyncio.Queue = asyncio.Queue(
            maxsize=self.config.retry_queue_size
        )

        # Statistics tracking
        self._stats: dict[str, dict[str, Any]] = {}  # tenant_id -> stats

        # Background tasks
        self._delivery_workers: list[asyncio.Task] = []
        self._retry_worker: asyncio.Task | None = None
        self._cleanup_worker: asyncio.Task | None = None

        # HTTP client for webhook deliveries
        self._http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.config.default_timeout_seconds),
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        )

        logger.info("WebhooksSDK initialized")

    async def start_workers(self):
        """Start background workers."""
        # Start delivery workers
        for i in range(self.config.delivery_worker_count):
            worker = asyncio.create_task(self._delivery_worker(f"delivery-{i}"))
            self._delivery_workers.append(worker)

        # Start retry worker
        self._retry_worker = asyncio.create_task(self._retry_worker_task())

        # Start cleanup worker
        self._cleanup_worker = asyncio.create_task(self._cleanup_worker_task())

        logger.info(
            f"Started {len(self._delivery_workers)} delivery workers and support workers"
        )

    async def stop_workers(self):
        """Stop background workers."""
        # Cancel all workers
        for worker in self._delivery_workers:
            worker.cancel()

        if self._retry_worker:
            self._retry_worker.cancel()

        if self._cleanup_worker:
            self._cleanup_worker.cancel()

        # Wait for workers to finish
        await asyncio.gather(*self._delivery_workers, return_exceptions=True)
        if self._retry_worker:
            await asyncio.gather(self._retry_worker, return_exceptions=True)
        if self._cleanup_worker:
            await asyncio.gather(self._cleanup_worker, return_exceptions=True)

        # Close HTTP client
        await self._http_client.aclose()

        logger.info("Stopped all webhook workers")

    async def create_webhook(
        self,
        webhook: Webhook,
        context: RequestContext | None = None,
    ) -> Webhook:
        """Create a new webhook."""
        try:
            tenant_id_str = str(webhook.tenant_id)

            # Check tenant webhook limits
            tenant_webhooks = self._webhooks.get(tenant_id_str, {})
            if len(tenant_webhooks) >= self.config.max_webhooks_per_tenant:
                raise ValueError(
                    f"Maximum webhooks per tenant ({self.config.max_webhooks_per_tenant}) exceeded"
                )

            # Set metadata
            if not webhook.id:
                webhook.id = uuid4()
            webhook.created_at = datetime.now(UTC)
            webhook.updated_at = datetime.now(UTC)
            webhook.created_by = context.headers.x_user_id if context else None

            # Store webhook
            if tenant_id_str not in self._webhooks:
                self._webhooks[tenant_id_str] = {}
            self._webhooks[tenant_id_str][str(webhook.id)] = webhook

            # Initialize statistics
            await self._init_webhook_stats(webhook)

            # Audit log
            if self.audit_sdk:
                await self.audit_sdk.log_system_event(
                    tenant_id=webhook.tenant_id,
                    event_type="WEBHOOK_CREATED",
                    resource_type="webhook",
                    resource_id=str(webhook.id),
                    resource_name=webhook.name,
                    context=context,
                )

            return webhook

        except Exception as e:
            logger.error(f"Failed to create webhook {webhook.name}: {e}")
            raise

    async def trigger_webhook(
        self,
        tenant_id: UUID,
        event: WebhookEvent,
        event_data: dict[str, Any],
        event_metadata: dict[str, Any] | None = None,
        context: RequestContext | None = None,
    ) -> list[UUID]:
        """Trigger webhooks for an event."""
        try:
            tenant_id_str = str(tenant_id)
            triggered_webhooks = []

            # Get active webhooks for tenant
            tenant_webhooks = self._webhooks.get(tenant_id_str, {})

            for webhook in tenant_webhooks.values():
                if webhook.status == WebhookStatus.ACTIVE and event in webhook.events:
                    # Check event filters
                    if self._matches_event_filters(event_data, webhook.event_filters):
                        # Create payload
                        payload = WebhookPayload(
                            id=uuid4(),
                            webhook_id=webhook.id,
                            tenant_id=tenant_id,
                            event=event,
                            event_id=uuid4(),
                            event_timestamp=datetime.now(UTC),
                            data=event_data,
                            metadata=event_metadata or {},
                            created_at=datetime.now(UTC),
                        )

                        # Queue for delivery
                        try:
                            await self._delivery_queue.put(payload)
                            triggered_webhooks.append(webhook.id)
                        except asyncio.QueueFull:
                            logger.warning(
                                f"Delivery queue full, dropping webhook {webhook.id}"
                            )

            return triggered_webhooks

        except Exception as e:
            logger.error(f"Failed to trigger webhooks for event {event}: {e}")
            return []

    async def get_webhook(
        self,
        tenant_id: UUID,
        webhook_id: UUID,
        context: RequestContext | None = None,
    ) -> Webhook | None:
        """Get webhook by ID."""
        tenant_webhooks = self._webhooks.get(str(tenant_id), {})
        return tenant_webhooks.get(str(webhook_id)

    async def list_webhooks(
        self,
        query: WebhookQuery,
        context: RequestContext | None = None,
    ) -> list[Webhook]:
        """List webhooks with filtering."""
        try:
            tenant_webhooks = self._webhooks.get(str(query.tenant_id), {})
            webhooks = list(tenant_webhooks.values()

            # Apply filters
            if query.webhook_ids:
                webhook_id_strs = [str(wid) for wid in query.webhook_ids]
                webhooks = [w for w in webhooks if str(w.id) in webhook_id_strs]

            if query.events:
                webhooks = [
                    w
                    for w in webhooks
                    if any(event in w.events for event in query.events)
                ]

            if query.status:
                webhooks = [w for w in webhooks if w.status == query.status]

            if query.tags:
                webhooks = [
                    w for w in webhooks if any(tag in w.tags for tag in query.tags)
                ]

            if query.created_after:
                webhooks = [
                    w
                    for w in webhooks
                    if w.created_at and w.created_at >= query.created_after
                ]

            if query.created_before:
                webhooks = [
                    w
                    for w in webhooks
                    if w.created_at and w.created_at <= query.created_before
                ]

            # Sort
            if query.sort_by == "created_at":
                webhooks.sort(
                    key=lambda w: w.created_at or datetime.min,
                    reverse=query.sort_order == "desc",
                )
            elif query.sort_by == "name":
                webhooks.sort(key=lambda w: w.name, reverse=query.sort_order == "desc")

            # Paginate
            start = query.offset
            end = start + query.limit
            return webhooks[start:end]

        except Exception as e:
            logger.error(f"Failed to list webhooks: {e}")
            return []

    async def update_webhook(
        self,
        webhook: Webhook,
        context: RequestContext | None = None,
    ) -> Webhook:
        """Update webhook."""
        try:
            tenant_id_str = str(webhook.tenant_id)
            webhook_id_str = str(webhook.id)

            # Check if webhook exists
            tenant_webhooks = self._webhooks.get(tenant_id_str, {})
            if webhook_id_str not in tenant_webhooks:
                raise ValueError(f"Webhook {webhook.id} not found")

            # Update timestamp
            webhook.updated_at = datetime.now(UTC)

            # Store updated webhook
            tenant_webhooks[webhook_id_str] = webhook

            return webhook

        except Exception as e:
            logger.error(f"Failed to update webhook {webhook.id}: {e}")
            raise

    async def delete_webhook(
        self,
        tenant_id: UUID,
        webhook_id: UUID,
        context: RequestContext | None = None,
    ) -> bool:
        """Delete webhook."""
        try:
            tenant_id_str = str(tenant_id)
            webhook_id_str = str(webhook_id)

            tenant_webhooks = self._webhooks.get(tenant_id_str, {})
            if webhook_id_str in tenant_webhooks:
                del tenant_webhooks[webhook_id_str]
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to delete webhook {webhook_id}: {e}")
            return False

    async def get_delivery_history(
        self,
        query: WebhookDeliveryQuery,
        context: RequestContext | None = None,
    ) -> list[WebhookDelivery]:
        """Get webhook delivery history."""
        try:
            tenant_deliveries = self._deliveries.get(str(query.tenant_id), [])
            deliveries = tenant_deliveries.model_copy()

            # Apply filters
            if query.webhook_id:
                deliveries = [d for d in deliveries if d.webhook_id == query.webhook_id]

            if query.status:
                deliveries = [d for d in deliveries if d.status == query.status]

            if query.created_after:
                deliveries = [
                    d for d in deliveries if d.created_at >= query.created_after
                ]

            if query.created_before:
                deliveries = [
                    d for d in deliveries if d.created_at <= query.created_before
                ]

            # Sort
            if query.sort_by == "created_at":
                deliveries.sort(
                    key=lambda d: d.created_at, reverse=query.sort_order == "desc"
                )

            # Paginate
            start = query.offset
            end = start + query.limit
            return deliveries[start:end]

        except Exception as e:
            logger.error(f"Failed to get delivery history: {e}")
            return []

    async def get_webhook_stats(
        self,
        tenant_id: UUID,
        webhook_id: UUID | None = None,
        context: RequestContext | None = None,
    ) -> WebhookStats:
        """Get webhook statistics."""
        try:
            tenant_id_str = str(tenant_id)

            # Get webhooks
            tenant_webhooks = self._webhooks.get(tenant_id_str, {})

            if webhook_id:
                # Single webhook stats
                webhook = tenant_webhooks.get(str(webhook_id)
                if not webhook:
                    raise ValueError(f"Webhook {webhook_id} not found")

                # Calculate real statistics from delivery history
                tenant_id_str = str(tenant_id)
                deliveries = self._deliveries.get(tenant_id_str, [])
                webhook_deliveries = [d for d in deliveries if d.webhook_id == webhook_id]
                
                # Calculate pending deliveries from queue
                pending_count = 0
                try:
                    # Estimate pending deliveries by queue size (approximation)
                    pending_count = min(self._delivery_queue.qsize(), 10)  # Cap at reasonable number
                except Exception:
                    pending_count = 0
                
                # Calculate average response time from recent deliveries
                recent_deliveries = [d for d in webhook_deliveries if d.response_time_ms is not None]
                avg_response_time = (
                    sum(d.response_time_ms for d in recent_deliveries) / len(recent_deliveries)
                    if recent_deliveries else 150.0
                )
                
                # Calculate events by type from delivery history
                events_by_type = {}
                for event in webhook.events:
                    event_count = len([d for d in webhook_deliveries if d.event_type == event.value])
                    events_by_type[event.value] = event_count
                
                # Calculate deliveries by status
                deliveries_by_status = {}
                for delivery in webhook_deliveries:
                    status = delivery.status.value if hasattr(delivery.status, 'value') else str(delivery.status)
                    deliveries_by_status[status] = deliveries_by_status.get(status, 0) + 1
                
                # Calculate time-based delivery counts
                now = datetime.now(UTC)
                deliveries_last_24h = len([
                    d for d in webhook_deliveries 
                    if d.created_at and (now - d.created_at).days < 1
                ])
                deliveries_last_7d = len([
                    d for d in webhook_deliveries 
                    if d.created_at and (now - d.created_at).days < 7
                ])
                deliveries_last_30d = len([
                    d for d in webhook_deliveries 
                    if d.created_at and (now - d.created_at).days < 30
                ])

                return WebhookStats(
                    tenant_id=tenant_id,
                    webhook_id=webhook_id,
                    total_webhooks=1,
                    active_webhooks=1 if webhook.status == WebhookStatus.ACTIVE else 0,
                    inactive_webhooks=(
                        1 if webhook.status == WebhookStatus.INACTIVE else 0
                    ),
                    failed_webhooks=1 if webhook.status == WebhookStatus.FAILED else 0,
                    total_deliveries=webhook.total_deliveries,
                    successful_deliveries=webhook.successful_deliveries,
                    failed_deliveries=webhook.failed_deliveries,
                    pending_deliveries=pending_count,
                    avg_response_time_ms=avg_response_time,
                    success_rate_percent=(
                        webhook.successful_deliveries / max(webhook.total_deliveries, 1)
                    )
                    * 100,
                    events_by_type=events_by_type,
                    deliveries_by_status=deliveries_by_status,
                    deliveries_last_24h=deliveries_last_24h,
                    deliveries_last_7d=deliveries_last_7d,
                    deliveries_last_30d=deliveries_last_30d,
                    last_updated=datetime.now(UTC),
                )
            else:
                # Tenant-wide stats
                total_webhooks = len(tenant_webhooks)
                active_webhooks = sum(
                    1
                    for w in tenant_webhooks.values()
                    if w.status == WebhookStatus.ACTIVE
                )
                inactive_webhooks = sum(
                    1
                    for w in tenant_webhooks.values()
                    if w.status == WebhookStatus.INACTIVE
                )
                failed_webhooks = sum(
                    1
                    for w in tenant_webhooks.values()
                    if w.status == WebhookStatus.FAILED
                )

                total_deliveries = sum(
                    w.total_deliveries for w in tenant_webhooks.values()
                )
                successful_deliveries = sum(
                    w.successful_deliveries for w in tenant_webhooks.values()
                )
                failed_deliveries = sum(
                    w.failed_deliveries for w in tenant_webhooks.values()
                )

                # Calculate tenant-wide statistics
                tenant_deliveries = self._deliveries.get(str(tenant_id), [])
                
                # Calculate average response time across all webhooks
                all_response_times = [
                    d.response_time_ms for d in tenant_deliveries 
                    if d.response_time_ms is not None
                ]
                avg_response_time = (
                    sum(all_response_times) / len(all_response_times)
                    if all_response_times else 150.0
                )
                
                # Calculate events by type across all webhooks
                events_by_type = {}
                for delivery in tenant_deliveries:
                    event_type = delivery.event_type
                    events_by_type[event_type] = events_by_type.get(event_type, 0) + 1
                
                # Calculate deliveries by status across all webhooks
                deliveries_by_status = {}
                for delivery in tenant_deliveries:
                    status = delivery.status.value if hasattr(delivery.status, 'value') else str(delivery.status)
                    deliveries_by_status[status] = deliveries_by_status.get(status, 0) + 1
                
                # Calculate time-based delivery counts
                now = datetime.now(UTC)
                deliveries_last_24h = len([
                    d for d in tenant_deliveries 
                    if d.created_at and (now - d.created_at).days < 1
                ])
                deliveries_last_7d = len([
                    d for d in tenant_deliveries 
                    if d.created_at and (now - d.created_at).days < 7
                ])
                deliveries_last_30d = len([
                    d for d in tenant_deliveries 
                    if d.created_at and (now - d.created_at).days < 30
                ])

                return WebhookStats(
                    tenant_id=tenant_id,
                    webhook_id=None,
                    total_webhooks=total_webhooks,
                    active_webhooks=active_webhooks,
                    inactive_webhooks=inactive_webhooks,
                    failed_webhooks=failed_webhooks,
                    total_deliveries=total_deliveries,
                    successful_deliveries=successful_deliveries,
                    failed_deliveries=failed_deliveries,
                    pending_deliveries=self._delivery_queue.qsize(),
                    avg_response_time_ms=avg_response_time,
                    success_rate_percent=(
                        successful_deliveries / max(total_deliveries, 1)
                    )
                    * 100,
                    events_by_type=events_by_type,
                    deliveries_by_status=deliveries_by_status,
                    deliveries_last_24h=deliveries_last_24h,
                    deliveries_last_7d=deliveries_last_7d,
                    deliveries_last_30d=deliveries_last_30d,
                    last_updated=datetime.now(UTC),
                )

        except Exception as e:
            logger.error(f"Failed to get webhook stats: {e}")
            raise

    async def health_check(self) -> WebhookHealthCheck:
        """Perform health check."""
        try:
            total_webhooks = sum(len(webhooks) for webhooks in self._webhooks.values()
            active_webhooks = sum(
                sum(1 for w in webhooks.values() if w.status == WebhookStatus.ACTIVE)
                for webhooks in self._webhooks.values()
            )
            failed_webhooks = sum(
                sum(1 for w in webhooks.values() if w.status == WebhookStatus.FAILED)
                for webhooks in self._webhooks.values()
            )

            # Calculate delivery metrics from actual data
            all_deliveries = []
            for deliveries in self._deliveries.values():
                all_deliveries.extend(deliveries)
            
            now = datetime.now(UTC)
            one_hour_ago = now - timedelta(hours=1)
            
            # Calculate failed deliveries in last hour
            failed_deliveries_last_hour = len([
                d for d in all_deliveries 
                if d.created_at and d.created_at > one_hour_ago and 
                hasattr(d.status, 'value') and 'failed' in d.status.value.lower()
            ])
            
            # Calculate average delivery time from recent deliveries
            recent_deliveries_with_time = [
                d for d in all_deliveries 
                if d.response_time_ms is not None and d.created_at and d.created_at > one_hour_ago
            ]
            avg_delivery_time = (
                sum(d.response_time_ms for d in recent_deliveries_with_time) / len(recent_deliveries_with_time)
                if recent_deliveries_with_time else 150.0
            )
            
            # Calculate delivery success rate
            recent_deliveries = [
                d for d in all_deliveries 
                if d.created_at and d.created_at > one_hour_ago
            ]
            successful_recent = len([
                d for d in recent_deliveries 
                if hasattr(d.status, 'value') and 'success' in d.status.value.lower()
            ])
            delivery_success_rate = (
                (successful_recent / len(recent_deliveries) * 100
                if recent_deliveries else 95.0
            )
            
            # Calculate error rates
            webhook_error_rate = (
                (failed_webhooks / max(total_webhooks, 1) * 100
            )
            delivery_error_rate = (
                (failed_deliveries_last_hour / max(len(recent_deliveries), 1) * 100
            )

            return WebhookHealthCheck(
                status="healthy",
                timestamp=datetime.now(UTC),
                total_webhooks=total_webhooks,
                active_webhooks=active_webhooks,
                failed_webhooks=failed_webhooks,
                pending_deliveries=self._delivery_queue.qsize(),
                failed_deliveries_last_hour=failed_deliveries_last_hour,
                avg_delivery_time_ms=avg_delivery_time,
                delivery_success_rate=delivery_success_rate,
                delivery_queue_size=self._delivery_queue.qsize(),
                retry_queue_size=self._retry_queue.qsize(),
                webhook_error_rate=webhook_error_rate,
                delivery_error_rate=delivery_error_rate,
                details={
                    "tenants_count": len(self._webhooks),
                    "delivery_workers": len(self._delivery_workers),
                    "workers_running": sum(
                        1 for w in self._delivery_workers if not w.done()
                    ),
                },
            )

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return WebhookHealthCheck(
                status="unhealthy",
                timestamp=datetime.now(UTC),
                total_webhooks=0,
                active_webhooks=0,
                failed_webhooks=0,
                pending_deliveries=0,
                failed_deliveries_last_hour=0,
                avg_delivery_time_ms=None,
                delivery_success_rate=0.0,
                delivery_queue_size=0,
                retry_queue_size=0,
                webhook_error_rate=100.0,
                delivery_error_rate=100.0,
                details={"error": str(e)},
            )

    # Private helper methods

    def _matches_event_filters(
        self, event_data: dict[str, Any], filters: dict[str, Any]
    ) -> bool:
        """Check if event data matches webhook filters."""
        for filter_key, filter_value in filters.items():
            if filter_key not in event_data or event_data[filter_key] != filter_value:
                return False
        return True

    async def _init_webhook_stats(self, webhook: Webhook):
        """Initialize webhook statistics."""
        tenant_id_str = str(webhook.tenant_id)
        if tenant_id_str not in self._stats:
            self._stats[tenant_id_str] = {}

    async def _delivery_worker(self, worker_name: str):
        """Background worker for webhook deliveries."""
        logger.info(f"Delivery worker {worker_name} started")

        while True:
            try:
                # Get payload from queue
                payload = await self._delivery_queue.get()

                # Get webhook
                webhook = await self._get_webhook_for_delivery(payload)
                if not webhook:
                    logger.warning(
                        f"Webhook {payload.webhook_id} not found for delivery"
                    )
                    continue

                # Attempt delivery
                delivery = await self._attempt_delivery(payload, webhook)

                # Store delivery record
                await self._store_delivery_record(delivery)

                # Update webhook statistics
                await self._update_webhook_stats(webhook, delivery)

                # Handle retry if needed
                if (
                    delivery.status == WebhookDeliveryStatus.FAILED
                    and not delivery.max_retries_reached
                ):
                    await self._schedule_retry(payload, delivery)

                # Mark task as done
                self._delivery_queue.task_done()

            except asyncio.CancelledError:
                logger.info(f"Delivery worker {worker_name} cancelled")
                break
            except Exception as e:
                logger.error(f"Delivery worker {worker_name} error: {e}")
                await asyncio.sleep(1)  # Brief pause before continuing

    async def _retry_worker_task(self):
        """Background worker for handling retries."""
        logger.info("Retry worker started")

        while True:
            try:
                # Get payload from retry queue
                payload = await self._retry_queue.get()

                # Re-queue for delivery
                await self._delivery_queue.put(payload)

                # Mark retry task as done
                self._retry_queue.task_done()

            except asyncio.CancelledError:
                logger.info("Retry worker cancelled")
                break
            except Exception as e:
                logger.error(f"Retry worker error: {e}")
                await asyncio.sleep(1)

    async def _cleanup_worker_task(self):
        """Background worker for cleanup tasks."""
        logger.info("Cleanup worker started")

        while True:
            try:
                # Clean up old delivery records
                await self._cleanup_old_deliveries()

                # Sleep for an hour before next cleanup
                await asyncio.sleep(3600)

            except asyncio.CancelledError:
                logger.info("Cleanup worker cancelled")
                break
            except Exception as e:
                logger.error(f"Cleanup worker error: {e}")
                await asyncio.sleep(60)  # Retry in a minute

    async def _get_webhook_for_delivery(
        self, payload: WebhookPayload
    ) -> Webhook | None:
        """Get webhook for delivery."""
        tenant_webhooks = self._webhooks.get(str(payload.tenant_id), {})
        return tenant_webhooks.get(str(payload.webhook_id)

    async def _attempt_delivery(
        self, payload: WebhookPayload, webhook: Webhook
    ) -> WebhookDelivery:
        """Attempt webhook delivery."""
        delivery_id = uuid4()
        start_time = time.time()

        try:
            # Prepare request
            headers = webhook.headers.model_copy()
            headers["Content-Type"] = "application/json"
            headers["User-Agent"] = "dotmac-webhooks/1.0"
            headers["X-Webhook-Event"] = payload.event.value
            headers["X-Webhook-Delivery"] = str(delivery_id)

            # Add security headers
            request_body = json.dumps(payload.model_dump(mode="json")
            if webhook.security:
                await self._add_security_headers(
                    headers, request_body, webhook.security
                )

            # Make HTTP request
            response = await self._http_client.request(
                method=webhook.method.value,
                url=webhook.url,
                headers=headers,
                content=request_body,
                timeout=webhook.retry_config.timeout_seconds,
            )

            response_time_ms = (time.time() - start_time) * 1000

            # Determine success
            is_success = 200 <= response.status_code < 300
            status = (
                WebhookDeliveryStatus.DELIVERED
                if is_success
                else WebhookDeliveryStatus.FAILED
            )

            return WebhookDelivery(
                id=delivery_id,
                webhook_id=payload.webhook_id,
                payload_id=payload.id,
                tenant_id=payload.tenant_id,
                attempt=payload.attempt,
                status=status,
                request_url=webhook.url,
                request_method=webhook.method.value,
                request_headers=headers,
                request_body=request_body,
                response_status_code=response.status_code,
                response_headers=dict(response.headers),
                response_body=response.text[:1000],  # Limit response body size
                response_time_ms=response_time_ms,
                max_retries_reached=payload.attempt
                >= webhook.retry_config.max_attempts,
                created_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
            )

        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000

            return WebhookDelivery(
                id=delivery_id,
                webhook_id=payload.webhook_id,
                payload_id=payload.id,
                tenant_id=payload.tenant_id,
                attempt=payload.attempt,
                status=WebhookDeliveryStatus.FAILED,
                request_url=webhook.url,
                request_method=webhook.method.value,
                request_headers=headers if "headers" in locals() else {},
                request_body=request_body if "request_body" in locals() else "",
                response_time_ms=response_time_ms,
                error_message=str(e),
                error_code=type(e).__name__,
                max_retries_reached=payload.attempt
                >= webhook.retry_config.max_attempts,
                created_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
            )

    async def _add_security_headers(self, headers: dict[str, str], body: str, security):
        """Add security headers to request."""
        if security.type == WebhookSecurityType.HMAC_SHA256 and security.secret:
            signature = hmac.new(
                security.secret.encode(), body.encode(), hashlib.sha256
            ).hexdigest()
            headers["X-Webhook-Signature"] = f"sha256={signature}"

        elif security.type == WebhookSecurityType.BEARER_TOKEN and security.secret:
            headers["Authorization"] = f"Bearer {security.secret}"

        elif (
            security.type == WebhookSecurityType.BASIC_AUTH
            and security.username
            and security.password
        ):
            import base64

            credentials = base64.b64encode(
                f"{security.username}:{security.password}".encode()
            ).decode()
            headers["Authorization"] = f"Basic {credentials}"

        elif (
            security.type == WebhookSecurityType.API_KEY
            and security.api_key_header
            and security.api_key_value
        ):
            headers[security.api_key_header] = security.api_key_value

    async def _store_delivery_record(self, delivery: WebhookDelivery):
        """Store delivery record."""
        tenant_id_str = str(delivery.tenant_id)
        if tenant_id_str not in self._deliveries:
            self._deliveries[tenant_id_str] = []

        self._deliveries[tenant_id_str].append(delivery)

    async def _update_webhook_stats(self, webhook: Webhook, delivery: WebhookDelivery):
        """Update webhook statistics."""
        webhook.total_deliveries += 1
        webhook.last_delivery_at = delivery.completed_at

        if delivery.status == WebhookDeliveryStatus.DELIVERED:
            webhook.successful_deliveries += 1
            webhook.last_success_at = delivery.completed_at
        else:
            webhook.failed_deliveries += 1

    async def _schedule_retry(self, payload: WebhookPayload, delivery: WebhookDelivery):
        """Schedule retry for failed delivery."""
        if payload.attempt >= self.config.max_delivery_attempts:
            return

        # Calculate retry delay
        webhook = await self._get_webhook_for_delivery(payload)
        if not webhook:
            return

        delay = min(
            webhook.retry_config.initial_delay_seconds
            * (webhook.retry_config.backoff_multiplier ** (payload.attempt - 1),
            webhook.retry_config.max_delay_seconds,
        )

        # Update payload for retry
        payload.attempt += 1
        payload.delivery_id = None

        # Schedule retry (simplified - in production, use a proper scheduler)
        asyncio.create_task(self._delayed_retry(payload, delay)

    async def _delayed_retry(self, payload: WebhookPayload, delay: float):
        """Delayed retry task."""
        await asyncio.sleep(delay)
        try:
            await self._retry_queue.put(payload)
        except asyncio.QueueFull:
            logger.warning(
                f"Retry queue full, dropping retry for webhook {payload.webhook_id}"
            )

    async def _cleanup_old_deliveries(self):
        """Clean up old delivery records."""
        cutoff_date = datetime.now(UTC) - timedelta(
            days=self.config.delivery_history_retention_days
        )

        for tenant_id, deliveries in self._deliveries.items():
            # Keep only recent deliveries
            self._deliveries[tenant_id] = [
                d for d in deliveries if d.created_at >= cutoff_date
            ]
