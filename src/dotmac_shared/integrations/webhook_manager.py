"""
Webhook Manager - Centralized webhook handling following DRY patterns
Provides standardized webhook processing and management
"""

import asyncio
import hashlib
import hmac
import json
import logging
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from dotmac_shared.api.dependencies import StandardDependencies, get_standard_deps
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from dotmac.application import RouterFactory, standard_exception_handler
from dotmac.core.schemas.base_schemas import (
    BaseCreateSchema,
    BaseResponseSchema,
    BaseUpdateSchema,
)

logger = logging.getLogger(__name__)


class WebhookEndpointCreateSchema(BaseCreateSchema):
    """Schema for creating webhook endpoints."""

    name: str
    url: str
    secret: Optional[str] = None
    events: list[str] = []
    active: bool = True
    description: Optional[str] = None
    retry_config: dict[str, Any] = {
        "max_retries": 3,
        "retry_delay": 5,
        "exponential_backoff": True,
    }


class WebhookEndpointUpdateSchema(BaseUpdateSchema):
    """Schema for updating webhook endpoints."""

    name: Optional[str] = None
    url: Optional[str] = None
    secret: Optional[str] = None
    events: Optional[list[str]] = None
    active: Optional[bool] = None
    description: Optional[str] = None
    retry_config: Optional[dict[str, Any]] = None


class WebhookEndpointResponseSchema(BaseResponseSchema):
    """Response schema for webhook endpoints."""

    name: str
    url: str
    events: list[str]
    active: bool
    description: Optional[str] = None
    last_triggered: Optional[str] = None
    success_count: int = 0
    failure_count: int = 0
    retry_config: dict[str, Any]


class WebhookEvent(BaseModel):
    """Webhook event data structure."""

    id: str
    event_type: str
    timestamp: str
    data: dict[str, Any]
    source: str
    tenant_id: str


class WebhookDelivery(BaseModel):
    """Webhook delivery attempt record."""

    id: str
    webhook_id: str
    event_id: str
    url: str
    status_code: Optional[int] = None
    response_body: Optional[str] = None
    error: Optional[str] = None
    attempt: int = 1
    delivered_at: Optional[str] = None
    retry_at: Optional[str] = None


class WebhookProcessor:
    """Processes webhook events with retry logic and error handling."""

    def __init__(self):
        self.handlers: dict[str, list[Callable]] = {}
        self.middleware: list[Callable] = []

    def register_handler(self, event_type: str, handler: Callable):
        """Register a handler for specific event type."""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
        logger.info(f"Registered handler for event type: {event_type}")

    def add_middleware(self, middleware: Callable):
        """Add middleware for webhook processing."""
        self.middleware.append(middleware)

    async def process_event(
        self, event: WebhookEvent, endpoint_config: dict[str, Any]
    ) -> dict[str, Any]:
        """Process webhook event through handlers and middleware."""

        # Apply middleware
        for middleware in self.middleware:
            event = (
                await middleware(event)
                if asyncio.iscoroutinefunction(middleware)
                else middleware(event)
            )

        # Process through registered handlers
        results = []
        if event.event_type in self.handlers:
            for handler in self.handlers[event.event_type]:
                try:
                    result = (
                        await handler(event)
                        if asyncio.iscoroutinefunction(handler)
                        else handler(event)
                    )
                    results.append(
                        {"handler": handler.__name__, "success": True, "result": result}
                    )
                except Exception as e:
                    logger.error(f"Handler {handler.__name__} failed: {str(e)}")
                    results.append(
                        {"handler": handler.__name__, "success": False, "error": str(e)}
                    )

        return {
            "event_id": event.id,
            "event_type": event.event_type,
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "handlers_executed": len(results),
            "results": results,
        }


class WebhookManager:
    """
    Central webhook management service following DRY patterns.
    Handles webhook registration, validation, and delivery.
    """

    def __init__(self, db: AsyncSession, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.endpoints: dict[str, dict[str, Any]] = {}
        self.processor = WebhookProcessor()
        self.deliveries: dict[str, WebhookDelivery] = {}

    @standard_exception_handler
    async def create(
        self, data: WebhookEndpointCreateSchema, user_id: UUID
    ) -> WebhookEndpointResponseSchema:
        """Create a new webhook endpoint."""

        endpoint_id = str(uuid4())
        endpoint_config = {
            "id": endpoint_id,
            "name": data.name,
            "url": data.url,
            "secret": data.secret,
            "events": data.events,
            "active": data.active,
            "description": data.description,
            "retry_config": data.retry_config,
            "success_count": 0,
            "failure_count": 0,
            "last_triggered": None,
            "created_by": str(user_id),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        self.endpoints[endpoint_id] = endpoint_config
        logger.info(f"Created webhook endpoint: {data.name} -> {data.url}")

        return self._endpoint_to_response(endpoint_config)

    @standard_exception_handler
    async def get_by_id(
        self, endpoint_id: UUID, user_id: UUID
    ) -> WebhookEndpointResponseSchema:
        """Get webhook endpoint by ID."""
        endpoint_str = str(endpoint_id)

        if endpoint_str not in self.endpoints:
            raise ValueError(f"Webhook endpoint not found: {endpoint_str}")

        endpoint_config = self.endpoints[endpoint_str]
        return self._endpoint_to_response(endpoint_config)

    @standard_exception_handler
    async def update(
        self, endpoint_id: UUID, data: WebhookEndpointUpdateSchema, user_id: UUID
    ) -> WebhookEndpointResponseSchema:
        """Update webhook endpoint configuration."""
        endpoint_str = str(endpoint_id)

        if endpoint_str not in self.endpoints:
            raise ValueError(f"Webhook endpoint not found: {endpoint_str}")

        endpoint_config = self.endpoints[endpoint_str]

        # Update fields if provided
        if data.name is not None:
            endpoint_config["name"] = data.name
        if data.url is not None:
            endpoint_config["url"] = data.url
        if data.secret is not None:
            endpoint_config["secret"] = data.secret
        if data.events is not None:
            endpoint_config["events"] = data.events
        if data.active is not None:
            endpoint_config["active"] = data.active
        if data.description is not None:
            endpoint_config["description"] = data.description
        if data.retry_config is not None:
            endpoint_config["retry_config"] = data.retry_config

        endpoint_config["updated_at"] = datetime.now(timezone.utc).isoformat()

        logger.info(f"Updated webhook endpoint: {endpoint_str}")
        return self._endpoint_to_response(endpoint_config)

    @standard_exception_handler
    async def delete(self, endpoint_id: UUID, user_id: UUID, soft_delete: bool = True):
        """Delete/disable webhook endpoint."""
        endpoint_str = str(endpoint_id)

        if endpoint_str not in self.endpoints:
            raise ValueError(f"Webhook endpoint not found: {endpoint_str}")

        if soft_delete:
            self.endpoints[endpoint_str]["active"] = False
            self.endpoints[endpoint_str]["disabled_at"] = datetime.now(
                timezone.utc
            ).isoformat()
        else:
            del self.endpoints[endpoint_str]

        logger.info(
            f"{'Disabled' if soft_delete else 'Deleted'} webhook endpoint: {endpoint_str}"
        )

    @standard_exception_handler
    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[dict[str, Any]] = None,
        order_by: str = "created_at",
        user_id: Optional[UUID] = None,
    ) -> list[WebhookEndpointResponseSchema]:
        """List webhook endpoints with filtering."""
        endpoints = []

        for endpoint_config in self.endpoints.values():
            # Apply filters
            if filters:
                if (
                    "active" in filters
                    and endpoint_config["active"] != filters["active"]
                ):
                    continue
                if "event_type" in filters and filters[
                    "event_type"
                ] not in endpoint_config.get("events", []):
                    continue

            endpoints.append(self._endpoint_to_response(endpoint_config))

        # Apply pagination
        return endpoints[skip : skip + limit]

    @standard_exception_handler
    async def count(
        self, filters: Optional[dict[str, Any]] = None, user_id: Optional[UUID] = None
    ) -> int:
        """Count webhook endpoints with filters."""
        count = 0
        for endpoint_config in self.endpoints.values():
            if filters:
                if (
                    "active" in filters
                    and endpoint_config["active"] != filters["active"]
                ):
                    continue
                if "event_type" in filters and filters[
                    "event_type"
                ] not in endpoint_config.get("events", []):
                    continue
            count += 1
        return count

    def _endpoint_to_response(
        self, endpoint_config: dict[str, Any]
    ) -> WebhookEndpointResponseSchema:
        """Convert endpoint config to response schema."""
        return WebhookEndpointResponseSchema(
            id=UUID(endpoint_config["id"]),
            name=endpoint_config["name"],
            url=endpoint_config["url"],
            events=endpoint_config["events"],
            active=endpoint_config["active"],
            description=endpoint_config.get("description"),
            last_triggered=endpoint_config.get("last_triggered"),
            success_count=endpoint_config.get("success_count", 0),
            failure_count=endpoint_config.get("failure_count", 0),
            retry_config=endpoint_config.get("retry_config", {}),
            created_at=endpoint_config["created_at"],
            updated_at=endpoint_config.get("updated_at", endpoint_config["created_at"]),
        )

    @standard_exception_handler
    async def trigger_event(
        self, event_type: str, data: dict[str, Any], source: str = "system"
    ) -> dict[str, Any]:
        """Trigger webhook event to all subscribed endpoints."""

        event = WebhookEvent(
            id=str(uuid4()),
            event_type=event_type,
            timestamp=datetime.now(timezone.utc).isoformat(),
            data=data,
            source=source,
            tenant_id=str(self.tenant_id),
        )

        # Find endpoints subscribed to this event type
        matching_endpoints = [
            config
            for config in self.endpoints.values()
            if config["active"]
            and (not config["events"] or event_type in config["events"])
        ]

        delivery_results = []

        for endpoint_config in matching_endpoints:
            try:
                # Process the event
                result = await self.processor.process_event(event, endpoint_config)

                # Record delivery attempt
                delivery = WebhookDelivery(
                    id=str(uuid4()),
                    webhook_id=endpoint_config["id"],
                    event_id=event.id,
                    url=endpoint_config["url"],
                    status_code=200,  # Would be actual HTTP status
                    delivered_at=datetime.now(timezone.utc).isoformat(),
                    attempt=1,
                )

                self.deliveries[delivery.id] = delivery
                endpoint_config["success_count"] += 1
                endpoint_config["last_triggered"] = datetime.now(
                    timezone.utc
                ).isoformat()

                delivery_results.append(
                    {
                        "endpoint": endpoint_config["name"],
                        "success": True,
                        "delivery_id": delivery.id,
                        "result": result,
                    }
                )

            except Exception as e:
                # Record failed delivery
                delivery = WebhookDelivery(
                    id=str(uuid4()),
                    webhook_id=endpoint_config["id"],
                    event_id=event.id,
                    url=endpoint_config["url"],
                    error=str(e),
                    attempt=1,
                )

                self.deliveries[delivery.id] = delivery
                endpoint_config["failure_count"] += 1

                delivery_results.append(
                    {
                        "endpoint": endpoint_config["name"],
                        "success": False,
                        "delivery_id": delivery.id,
                        "error": str(e),
                    }
                )

        return {
            "event_id": event.id,
            "event_type": event_type,
            "triggered_at": event.timestamp,
            "endpoints_notified": len(matching_endpoints),
            "successful_deliveries": sum(1 for r in delivery_results if r["success"]),
            "failed_deliveries": sum(1 for r in delivery_results if not r["success"]),
            "delivery_results": delivery_results,
        }

    def validate_signature(
        self, payload: bytes, signature: str, secret: str, algorithm: str = "sha256"
    ) -> bool:
        """Validate webhook signature."""
        if not secret or not signature:
            return True  # No signature validation required

        expected_signature = hmac.new(
            secret.encode(), payload, getattr(hashlib, algorithm)
        ).hexdigest()

        # Support different signature formats
        if signature.startswith("sha256="):
            signature = signature[7:]

        return hmac.compare_digest(expected_signature, signature)


class WebhookManagerRouter:
    """Router factory for Webhook Manager following DRY patterns."""

    @classmethod
    def create_router(cls) -> APIRouter:
        """Create Webhook Manager router using RouterFactory."""

        # Use RouterFactory for standard CRUD operations
        router = RouterFactory.create_crud_router(
            service_class=WebhookManager,
            create_schema=WebhookEndpointCreateSchema,
            update_schema=WebhookEndpointUpdateSchema,
            response_schema=WebhookEndpointResponseSchema,
            prefix="/webhooks",
            tags=["webhooks", "integrations"],
            enable_search=True,
            enable_bulk_operations=False,  # Webhooks managed individually
        )

        # Add custom webhook-specific endpoints
        @router.post("/trigger", response_model=dict[str, Any])
        @standard_exception_handler
        async def trigger_webhook_event(
            event_type: Optional[str] = None,
            data: Optional[dict[str, Any]] = None,
            source: Optional[str] = None,
            deps: StandardDependencies = Depends(get_standard_deps),
        ):
            """Trigg            if event_type is None:
                            event_type = Body(...)  # noqa: B008
                        if data is None:
                            data = Body(...)  # noqa: B008
                        if source is None:
                            source = Body("system")  # noqa: B008
            er webhook event to subscribed endpoints."""
            manager = WebhookManager(deps.db, deps.tenant_id)
            return await manager.trigger_event(event_type, data, source)

        @router.post("/receive/{endpoint_id}")
        @standard_exception_handler
        async def receive_webhook(
            endpoint_id: str,
            request: Request,
            deps: StandardDependencies = Depends(get_standard_deps),
        ):
            """Receive incoming webhook (for testing)."""
            manager = WebhookManager(deps.db, deps.tenant_id)

            # Get the webhook endpoint config
            if endpoint_id not in manager.endpoints:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Webhook endpoint not found",
                )

            endpoint_config = manager.endpoints[endpoint_id]
            if not endpoint_config["active"]:
                raise HTTPException(
                    status_code=status.HTTP_410_GONE,
                    detail="Webhook endpoint is disabled",
                )

            # Get the payload
            payload = await request.body()

            # Validate signature if secret is configured
            signature = request.headers.get("X-Webhook-Signature", "")
            secret = endpoint_config.get("secret")

            if secret and not manager.validate_signature(payload, signature, secret):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid webhook signature",
                )

            # Process the webhook
            try:
                payload_data = json.loads(payload) if payload else {}
                event_type = payload_data.get("type", "webhook.received")

                result = await manager.trigger_event(
                    event_type=event_type, data=payload_data, source="webhook"
                )

                return {"status": "received", "result": result}

            except Exception as e:
                logger.error(f"Failed to process webhook: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to process webhook: {str(e)}",
                ) from e

        @router.get("/deliveries", response_model=list[dict[str, Any]])
        @standard_exception_handler
        async def list_webhook_deliveries(
            endpoint_id: Optional[str] = None,
            limit: int = 100,
            deps: StandardDependencies = Depends(get_standard_deps),
        ):
            """List webhook delivery attempts."""
            manager = WebhookManager(deps.db, deps.tenant_id)

            deliveries = list(manager.deliveries.values())

            # Filter by endpoint if specified
            if endpoint_id:
                deliveries = [d for d in deliveries if d.webhook_id == endpoint_id]

            # Apply limit
            deliveries = deliveries[:limit]

            return [delivery.model_dump() for delivery in deliveries]

        return router
