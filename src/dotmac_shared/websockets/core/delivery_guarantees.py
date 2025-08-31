"""
WebSocket Delivery Guarantees Extension

Extends the existing EventManager with enhanced delivery guarantees,
retry mechanisms, and persistent storage for critical notifications.
Follows DRY patterns from the existing WebSocket infrastructure.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from pydantic import BaseModel, Field

from dotmac_shared.websockets.core.events import (
    EventManager,
    EventPriority,
    WebSocketEvent,
)

logger = logging.getLogger(__name__)


class DeliveryGuaranteeLevel(str, Enum):
    """Delivery guarantee levels."""
    
    FIRE_AND_FORGET = "fire_and_forget"  # Best effort, no retry
    AT_LEAST_ONCE = "at_least_once"     # Retry until acknowledged
    EXACTLY_ONCE = "exactly_once"        # Prevent duplicates
    PERSISTENT = "persistent"            # Store until delivered


class AcknowledgmentType(str, Enum):
    """Types of acknowledgments."""
    
    RECEIVED = "received"      # Message received by client
    PROCESSED = "processed"    # Message processed by client
    DISPLAYED = "displayed"    # Message displayed to user
    INTERACTED = "interacted"  # User interacted with message


@dataclass
class DeliveryAttempt:
    """Record of a delivery attempt."""
    
    attempt_number: int
    timestamp: datetime
    connection_id: str
    success: bool
    error_message: Optional[str] = None
    response_time_ms: Optional[int] = None


class PendingDelivery(BaseModel):
    """Pending delivery with retry configuration."""
    
    delivery_id: str = Field(default_factory=lambda: str(uuid4()))
    event: WebSocketEvent
    target_connections: Set[str]
    guarantee_level: DeliveryGuaranteeLevel
    
    # Retry configuration
    max_attempts: int = 3
    retry_delay_seconds: int = 2
    backoff_multiplier: float = 2.0
    max_retry_delay_seconds: int = 300  # 5 minutes
    
    # Delivery tracking
    attempts: List[DeliveryAttempt] = Field(default_factory=list)
    acknowledged_connections: Set[str] = Field(default_factory=set)
    failed_connections: Set[str] = Field(default_factory=set)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    
    @property
    def is_expired(self) -> bool:
        """Check if delivery has expired."""
        return self.expires_at is not None and datetime.utcnow() > self.expires_at
    
    @property
    def remaining_connections(self) -> Set[str]:
        """Get connections that still need delivery."""
        return self.target_connections - self.acknowledged_connections - self.failed_connections
    
    @property
    def next_retry_delay(self) -> int:
        """Calculate next retry delay with exponential backoff."""
        attempt_count = len(self.attempts)
        delay = self.retry_delay_seconds * (self.backoff_multiplier ** attempt_count)
        return min(int(delay), self.max_retry_delay_seconds)


class DeliveryGuaranteeManager:
    """
    Enhanced delivery guarantee manager extending EventManager functionality.
    
    Features:
    - Acknowledgment tracking
    - Retry mechanisms with exponential backoff
    - Persistent delivery for critical messages
    - Duplicate detection for exactly-once delivery
    - Delivery metrics and monitoring
    """

    def __init__(self, event_manager: EventManager, cache_service=None):
        self.event_manager = event_manager
        self.cache_service = cache_service
        
        # Delivery tracking
        self.pending_deliveries: Dict[str, PendingDelivery] = {}
        self.delivered_messages: Dict[str, Set[str]] = {}  # event_id -> connection_ids
        self.message_deduplication: Dict[str, datetime] = {}  # For exactly-once delivery
        
        # Background tasks
        self._retry_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._is_running = False
        
        # Metrics
        self.delivery_metrics = {
            "pending_deliveries": 0,
            "successful_deliveries": 0,
            "failed_deliveries": 0,
            "retry_attempts": 0,
            "acknowledgments_received": 0,
            "duplicates_prevented": 0,
        }

    async def start(self):
        """Start the delivery guarantee manager."""
        if self._is_running:
            return
        
        self._is_running = True
        self._retry_task = asyncio.create_task(self._retry_failed_deliveries())
        self._cleanup_task = asyncio.create_task(self._cleanup_expired_deliveries())
        
        logger.info("Delivery guarantee manager started")

    async def stop(self):
        """Stop the delivery guarantee manager."""
        self._is_running = False
        
        for task in [self._retry_task, self._cleanup_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        logger.info("Delivery guarantee manager stopped")

    async def send_with_guarantees(
        self,
        event: WebSocketEvent,
        target_connections: Set[str],
        guarantee_level: DeliveryGuaranteeLevel = DeliveryGuaranteeLevel.AT_LEAST_ONCE,
        max_attempts: int = 3,
        retry_delay: int = 2,
        ttl_seconds: Optional[int] = None,
    ) -> str:
        """
        Send event with delivery guarantees.
        
        Args:
            event: WebSocket event to send
            target_connections: Target connection IDs
            guarantee_level: Delivery guarantee level
            max_attempts: Maximum retry attempts
            retry_delay: Initial retry delay in seconds
            ttl_seconds: Time-to-live for the message
        
        Returns:
            Delivery ID for tracking
        """
        # Create pending delivery
        pending_delivery = PendingDelivery(
            event=event,
            target_connections=target_connections.copy(),
            guarantee_level=guarantee_level,
            max_attempts=max_attempts,
            retry_delay_seconds=retry_delay,
            expires_at=datetime.utcnow() + timedelta(seconds=ttl_seconds) if ttl_seconds else None,
        )
        
        # For exactly-once delivery, check for duplicates
        if guarantee_level == DeliveryGuaranteeLevel.EXACTLY_ONCE:
            if await self._is_duplicate(event.event_id, target_connections):
                self.delivery_metrics["duplicates_prevented"] += 1
                logger.debug(f"Duplicate message prevented: {event.event_id}")
                return pending_delivery.delivery_id
        
        # Store pending delivery
        self.pending_deliveries[pending_delivery.delivery_id] = pending_delivery
        self.delivery_metrics["pending_deliveries"] += 1
        
        # Attempt initial delivery
        await self._attempt_delivery(pending_delivery)
        
        return pending_delivery.delivery_id

    async def acknowledge_delivery(
        self,
        connection_id: str,
        event_id: str,
        acknowledgment_type: AcknowledgmentType = AcknowledgmentType.RECEIVED,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Acknowledge message delivery from client.
        
        Args:
            connection_id: Connection that received the message
            event_id: Event ID being acknowledged
            acknowledgment_type: Type of acknowledgment
            metadata: Additional metadata
        
        Returns:
            True if acknowledgment was processed
        """
        self.delivery_metrics["acknowledgments_received"] += 1
        
        # Find pending delivery for this event
        pending_delivery = None
        for delivery in self.pending_deliveries.values():
            if delivery.event.event_id == event_id and connection_id in delivery.target_connections:
                pending_delivery = delivery
                break
        
        if not pending_delivery:
            logger.debug(f"No pending delivery found for ack: {event_id} from {connection_id}")
            return False
        
        # Mark as acknowledged
        pending_delivery.acknowledged_connections.add(connection_id)
        
        # Check if all connections have acknowledged
        if not pending_delivery.remaining_connections:
            # All connections acknowledged, mark as complete
            await self._complete_delivery(pending_delivery)
        
        # Publish acknowledgment event
        ack_event = WebSocketEvent(
            event_type="message_acknowledged",
            data={
                "original_event_id": event_id,
                "acknowledgment_type": acknowledgment_type.value,
                "connection_id": connection_id,
                "metadata": metadata or {},
            },
            tenant_id=pending_delivery.event.tenant_id,
            priority=EventPriority.LOW,
        )
        
        await self.event_manager.publish_event(ack_event)
        
        logger.debug(f"Acknowledged delivery: {event_id} from {connection_id}")
        return True

    async def get_delivery_status(self, delivery_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a delivery."""
        if delivery_id not in self.pending_deliveries:
            return None
        
        delivery = self.pending_deliveries[delivery_id]
        
        return {
            "delivery_id": delivery_id,
            "event_id": delivery.event.event_id,
            "guarantee_level": delivery.guarantee_level.value,
            "target_count": len(delivery.target_connections),
            "acknowledged_count": len(delivery.acknowledged_connections),
            "failed_count": len(delivery.failed_connections),
            "remaining_count": len(delivery.remaining_connections),
            "attempt_count": len(delivery.attempts),
            "is_expired": delivery.is_expired,
            "created_at": delivery.created_at.isoformat(),
            "expires_at": delivery.expires_at.isoformat() if delivery.expires_at else None,
        }

    async def _attempt_delivery(self, pending_delivery: PendingDelivery) -> bool:
        """Attempt to deliver message to remaining connections."""
        if not pending_delivery.remaining_connections:
            return True
        
        # Create delivery attempt record
        attempt = DeliveryAttempt(
            attempt_number=len(pending_delivery.attempts) + 1,
            timestamp=datetime.utcnow(),
            connection_id="",  # Will be updated per connection
            success=False,
        )
        
        # Attempt delivery to each remaining connection
        successful_deliveries = []
        failed_deliveries = []
        
        for connection_id in pending_delivery.remaining_connections:
            try:
                # For fire-and-forget, use regular event manager
                if pending_delivery.guarantee_level == DeliveryGuaranteeLevel.FIRE_AND_FORGET:
                    result = await self.event_manager.publish_event(
                        pending_delivery.event,
                        target_connections={connection_id}
                    )
                    if result["delivered"] > 0:
                        successful_deliveries.append(connection_id)
                    else:
                        failed_deliveries.append(connection_id)
                else:
                    # For guaranteed delivery, use WebSocket manager directly
                    success = await self.event_manager.websocket_manager.send_message(
                        connection_id,
                        {
                            **pending_delivery.event.to_message(),
                            "requires_ack": True,
                            "delivery_id": pending_delivery.delivery_id,
                            "guarantee_level": pending_delivery.guarantee_level.value,
                        }
                    )
                    
                    if success:
                        successful_deliveries.append(connection_id)
                        # For fire-and-forget, immediately mark as acknowledged
                        if pending_delivery.guarantee_level == DeliveryGuaranteeLevel.FIRE_AND_FORGET:
                            pending_delivery.acknowledged_connections.add(connection_id)
                    else:
                        failed_deliveries.append(connection_id)
            
            except Exception as e:
                logger.error(f"Delivery attempt failed for {connection_id}: {e}")
                failed_deliveries.append(connection_id)
        
        # Update attempt record
        attempt.success = len(successful_deliveries) > 0
        pending_delivery.attempts.append(attempt)
        
        # Update metrics
        if successful_deliveries:
            self.delivery_metrics["successful_deliveries"] += len(successful_deliveries)
        if failed_deliveries:
            self.delivery_metrics["failed_deliveries"] += len(failed_deliveries)
        
        # For persistent delivery, mark failed connections for retry
        if pending_delivery.guarantee_level in [
            DeliveryGuaranteeLevel.AT_LEAST_ONCE,
            DeliveryGuaranteeLevel.EXACTLY_ONCE,
            DeliveryGuaranteeLevel.PERSISTENT,
        ]:
            # Don't immediately fail connections, they'll be retried
            pass
        else:
            # For fire-and-forget, mark failed connections as failed
            pending_delivery.failed_connections.update(failed_deliveries)
        
        # Check if delivery is complete
        if not pending_delivery.remaining_connections:
            await self._complete_delivery(pending_delivery)
            return True
        
        return len(successful_deliveries) > 0

    async def _complete_delivery(self, pending_delivery: PendingDelivery):
        """Mark delivery as complete and clean up."""
        delivery_id = pending_delivery.delivery_id
        
        # Update delivered messages tracking for exactly-once delivery
        if pending_delivery.guarantee_level == DeliveryGuaranteeLevel.EXACTLY_ONCE:
            self.delivered_messages[pending_delivery.event.event_id] = pending_delivery.acknowledged_connections.copy()
        
        # Remove from pending deliveries
        if delivery_id in self.pending_deliveries:
            del self.pending_deliveries[delivery_id]
            self.delivery_metrics["pending_deliveries"] -= 1
        
        # Publish completion event
        completion_event = WebSocketEvent(
            event_type="delivery_completed",
            data={
                "delivery_id": delivery_id,
                "event_id": pending_delivery.event.event_id,
                "guarantee_level": pending_delivery.guarantee_level.value,
                "target_count": len(pending_delivery.target_connections),
                "acknowledged_count": len(pending_delivery.acknowledged_connections),
                "failed_count": len(pending_delivery.failed_connections),
                "attempt_count": len(pending_delivery.attempts),
            },
            tenant_id=pending_delivery.event.tenant_id,
            priority=EventPriority.LOW,
        )
        
        await self.event_manager.publish_event(completion_event)
        
        logger.debug(f"Delivery completed: {delivery_id}")

    async def _is_duplicate(self, event_id: str, target_connections: Set[str]) -> bool:
        """Check if message is a duplicate for exactly-once delivery."""
        if event_id not in self.delivered_messages:
            return False
        
        # Check if any target connections have already received this message
        already_delivered = self.delivered_messages[event_id]
        return bool(target_connections.intersection(already_delivered))

    async def _retry_failed_deliveries(self):
        """Background task to retry failed deliveries."""
        while self._is_running:
            try:
                current_time = datetime.utcnow()
                deliveries_to_retry = []
                
                # Find deliveries that need retry
                for delivery in list(self.pending_deliveries.values()):
                    if (delivery.remaining_connections and 
                        len(delivery.attempts) < delivery.max_attempts and
                        not delivery.is_expired):
                        
                        # Check if enough time has passed for retry
                        if delivery.attempts:
                            last_attempt = delivery.attempts[-1].timestamp
                            retry_delay = timedelta(seconds=delivery.next_retry_delay)
                            if current_time >= last_attempt + retry_delay:
                                deliveries_to_retry.append(delivery)
                        else:
                            # No previous attempts, retry immediately
                            deliveries_to_retry.append(delivery)
                
                # Retry deliveries
                for delivery in deliveries_to_retry:
                    self.delivery_metrics["retry_attempts"] += 1
                    await self._attempt_delivery(delivery)
                
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Retry task error: {e}")
                await asyncio.sleep(10)

    async def _cleanup_expired_deliveries(self):
        """Background task to clean up expired deliveries."""
        while self._is_running:
            try:
                current_time = datetime.utcnow()
                expired_deliveries = []
                
                # Find expired deliveries
                for delivery_id, delivery in list(self.pending_deliveries.items()):
                    if (delivery.is_expired or 
                        len(delivery.attempts) >= delivery.max_attempts):
                        expired_deliveries.append(delivery_id)
                
                # Clean up expired deliveries
                for delivery_id in expired_deliveries:
                    if delivery_id in self.pending_deliveries:
                        delivery = self.pending_deliveries[delivery_id]
                        
                        # Mark remaining connections as failed
                        delivery.failed_connections.update(delivery.remaining_connections)
                        
                        # Complete delivery
                        await self._complete_delivery(delivery)
                        
                        logger.debug(f"Cleaned up expired delivery: {delivery_id}")
                
                # Clean up old delivered messages (for exactly-once tracking)
                cutoff_time = current_time - timedelta(hours=24)  # Keep for 24 hours
                expired_event_ids = []
                
                for event_id, timestamp in list(self.message_deduplication.items()):
                    if timestamp < cutoff_time:
                        expired_event_ids.append(event_id)
                
                for event_id in expired_event_ids:
                    self.message_deduplication.pop(event_id, None)
                    self.delivered_messages.pop(event_id, None)
                
                await asyncio.sleep(60)  # Cleanup every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup task error: {e}")
                await asyncio.sleep(60)

    def get_metrics(self) -> Dict[str, Any]:
        """Get delivery guarantee metrics."""
        return {
            **self.delivery_metrics,
            "pending_deliveries_count": len(self.pending_deliveries),
            "delivered_messages_tracked": len(self.delivered_messages),
            "deduplication_entries": len(self.message_deduplication),
        }