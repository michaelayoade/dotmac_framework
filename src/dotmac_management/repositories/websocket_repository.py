"""WebSocket Event Repository for the Management Platform."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, joinedload

from dotmac_isp.shared.base_repository import BaseRepository
from dotmac_shared.exceptions import NotFoundError, ValidationError

from ..models.websocket_event import (
    DeliveryStatus,
    EventPriority,
    EventType,
    SubscriptionType,
    WebSocketConnection,
    WebSocketDelivery,
    WebSocketEvent,
    WebSocketMetrics,
    WebSocketSubscription,
)

logger = logging.getLogger(__name__)


class WebSocketEventRepository(BaseRepository):
    """Repository for WebSocket event management."""

    def __init__(self, session: Session):
        super().__init__(session)
        self.model = WebSocketEvent

    # Event Operations

    async def create_event(
        self,
        tenant_id: str,
        event_data: Dict,
        user_id: str
    ) -> WebSocketEvent:
        """Create a new WebSocket event."""
        try:
            event_id = str(uuid4())
            
            event = WebSocketEvent(
                event_id=event_id,
                tenant_id=tenant_id,
                created_by=user_id,
                **event_data
            )
            
            self.session.add(event)
            await self.session.commit()
            await self.session.refresh(event)
            
            logger.info(f"Created WebSocket event: {event_id}")
            return event
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to create WebSocket event: {e}")
            raise ValidationError(f"Failed to create WebSocket event: {str(e)}")

    async def get_event_by_id(self, event_id: str, tenant_id: str) -> Optional[WebSocketEvent]:
        """Get event by ID."""
        return await self.session.query(WebSocketEvent).filter(
            and_(
                WebSocketEvent.event_id == event_id,
                WebSocketEvent.tenant_id == tenant_id
            )
        ).first()

    async def get_pending_events(
        self,
        tenant_id: str = None,
        limit: int = 100
    ) -> List[WebSocketEvent]:
        """Get pending events ready for delivery."""
        query = self.session.query(WebSocketEvent).filter(
            and_(
                WebSocketEvent.delivery_status == DeliveryStatus.PENDING,
                or_(
                    WebSocketEvent.scheduled_for.is_(None),
                    WebSocketEvent.scheduled_for <= datetime.now(timezone.utc)
                ),
                or_(
                    WebSocketEvent.expires_at.is_(None),
                    WebSocketEvent.expires_at > datetime.now(timezone.utc)
                )
            )
        )
        
        if tenant_id:
            query = query.filter(WebSocketEvent.tenant_id == tenant_id)
        
        return await query.order_by(
            WebSocketEvent.priority.desc(),
            WebSocketEvent.created_at.asc()
        ).limit(limit).all()

    async def get_events_for_user(
        self,
        user_id: str,
        tenant_id: str,
        event_types: List[EventType] = None,
        limit: int = 50
    ) -> List[WebSocketEvent]:
        """Get events targeted for a specific user."""
        query = self.session.query(WebSocketEvent).filter(
            and_(
                WebSocketEvent.tenant_id == tenant_id,
                or_(
                    WebSocketEvent.target_user_id == user_id,
                    WebSocketEvent.target_user_ids.contains([user_id]),
                    WebSocketEvent.broadcast_to_tenant == True
                )
            )
        )
        
        if event_types:
            query = query.filter(WebSocketEvent.event_type.in_(event_types))
        
        return await query.order_by(
            WebSocketEvent.priority.desc(),
            WebSocketEvent.created_at.desc()
        ).limit(limit).all()

    async def update_event_delivery_status(
        self,
        event_id: str,
        tenant_id: str,
        status: DeliveryStatus,
        error_message: str = None
    ) -> WebSocketEvent:
        """Update event delivery status."""
        event = await self.get_event_by_id(event_id, tenant_id)
        if not event:
            raise NotFoundError(f"Event not found: {event_id}")
        
        try:
            event.delivery_status = status
            event.delivery_attempts += 1
            event.last_delivery_attempt = datetime.now(timezone.utc)
            
            if status == DeliveryStatus.DELIVERED:
                event.delivered_at = datetime.now(timezone.utc)
            elif status == DeliveryStatus.FAILED:
                event.error_message = error_message
                event.retry_count += 1
            
            await self.session.commit()
            await self.session.refresh(event)
            
            return event
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to update event delivery status: {e}")
            raise ValidationError(f"Failed to update event delivery status: {str(e)}")

    async def acknowledge_event(
        self,
        event_id: str,
        tenant_id: str,
        user_id: str
    ) -> WebSocketEvent:
        """Acknowledge an event."""
        event = await self.get_event_by_id(event_id, tenant_id)
        if not event:
            raise NotFoundError(f"Event not found: {event_id}")
        
        try:
            # Add user to acknowledged list
            acknowledged_by = event.acknowledged_by or []
            if user_id not in acknowledged_by:
                acknowledged_by.append(user_id)
                event.acknowledged_by = acknowledged_by
                
                # Set first acknowledgment timestamp
                if not event.acknowledged_at:
                    event.acknowledged_at = datetime.now(timezone.utc)
            
            await self.session.commit()
            await self.session.refresh(event)
            
            return event
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to acknowledge event: {e}")
            raise ValidationError(f"Failed to acknowledge event: {str(e)}")

    # Connection Operations

    async def create_connection(
        self,
        tenant_id: str,
        connection_data: Dict
    ) -> WebSocketConnection:
        """Create a new WebSocket connection record."""
        try:
            connection_id = str(uuid4())
            
            connection = WebSocketConnection(
                connection_id=connection_id,
                tenant_id=tenant_id,
                **connection_data
            )
            
            self.session.add(connection)
            await self.session.commit()
            await self.session.refresh(connection)
            
            logger.info(f"Created WebSocket connection: {connection_id}")
            return connection
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to create WebSocket connection: {e}")
            raise ValidationError(f"Failed to create WebSocket connection: {str(e)}")

    async def get_active_connections(
        self,
        tenant_id: str = None,
        user_id: str = None
    ) -> List[WebSocketConnection]:
        """Get active WebSocket connections."""
        query = self.session.query(WebSocketConnection).filter(
            WebSocketConnection.is_active == True
        )
        
        if tenant_id:
            query = query.filter(WebSocketConnection.tenant_id == tenant_id)
        
        if user_id:
            query = query.filter(WebSocketConnection.user_id == user_id)
        
        return await query.all()

    async def update_connection_activity(
        self,
        connection_id: str,
        activity_data: Dict
    ) -> WebSocketConnection:
        """Update connection activity metrics."""
        connection = await self.session.query(WebSocketConnection).filter(
            WebSocketConnection.connection_id == connection_id
        ).first()
        
        if not connection:
            raise NotFoundError(f"Connection not found: {connection_id}")
        
        try:
            connection.last_activity = datetime.now(timezone.utc)
            
            for key, value in activity_data.items():
                if hasattr(connection, key):
                    setattr(connection, key, value)
            
            await self.session.commit()
            await self.session.refresh(connection)
            
            return connection
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to update connection activity: {e}")
            raise ValidationError(f"Failed to update connection activity: {str(e)}")

    async def disconnect_connection(self, connection_id: str) -> bool:
        """Mark connection as disconnected."""
        connection = await self.session.query(WebSocketConnection).filter(
            WebSocketConnection.connection_id == connection_id
        ).first()
        
        if not connection:
            return False
        
        try:
            connection.is_active = False
            connection.disconnected_at = datetime.now(timezone.utc)
            
            await self.session.commit()
            logger.info(f"Disconnected WebSocket connection: {connection_id}")
            return True
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to disconnect connection: {e}")
            raise ValidationError(f"Failed to disconnect connection: {str(e)}")

    # Subscription Operations

    async def create_subscription(
        self,
        tenant_id: str,
        subscription_data: Dict,
        user_id: str
    ) -> WebSocketSubscription:
        """Create a new WebSocket subscription."""
        try:
            subscription = WebSocketSubscription(
                tenant_id=tenant_id,
                user_id=user_id,
                created_by=user_id,
                **subscription_data
            )
            
            self.session.add(subscription)
            await self.session.commit()
            await self.session.refresh(subscription)
            
            logger.info(f"Created WebSocket subscription: {subscription.subscription_name}")
            return subscription
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to create WebSocket subscription: {e}")
            raise ValidationError(f"Failed to create WebSocket subscription: {str(e)}")

    async def get_subscriptions_for_connection(
        self,
        connection_id: str
    ) -> List[WebSocketSubscription]:
        """Get active subscriptions for a connection."""
        return await self.session.query(WebSocketSubscription).filter(
            and_(
                WebSocketSubscription.connection_id == connection_id,
                WebSocketSubscription.is_active == True
            )
        ).all()

    async def get_matching_subscriptions(
        self,
        event: WebSocketEvent
    ) -> List[WebSocketSubscription]:
        """Get subscriptions that match an event."""
        query = self.session.query(WebSocketSubscription).filter(
            and_(
                WebSocketSubscription.tenant_id == event.tenant_id,
                WebSocketSubscription.is_active == True
            )
        )
        
        # Filter by event types if subscription has event type filter
        if event.event_type:
            query = query.filter(
                or_(
                    WebSocketSubscription.event_types.is_(None),
                    WebSocketSubscription.event_types.contains([event.event_type])
                )
            )
        
        # Get all potential matches and filter in Python for complex logic
        potential_matches = await query.all()
        
        matching_subscriptions = []
        for subscription in potential_matches:
            if subscription.matches_event(event):
                matching_subscriptions.append(subscription)
        
        return matching_subscriptions

    # Delivery Operations

    async def create_delivery(
        self,
        tenant_id: str,
        delivery_data: Dict
    ) -> WebSocketDelivery:
        """Create a delivery record."""
        try:
            delivery_id = str(uuid4())
            
            delivery = WebSocketDelivery(
                delivery_id=delivery_id,
                tenant_id=tenant_id,
                **delivery_data
            )
            
            self.session.add(delivery)
            await self.session.commit()
            await self.session.refresh(delivery)
            
            return delivery
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to create delivery: {e}")
            raise ValidationError(f"Failed to create delivery: {str(e)}")

    async def update_delivery_status(
        self,
        delivery_id: str,
        status: DeliveryStatus,
        delivery_data: Dict = None
    ) -> WebSocketDelivery:
        """Update delivery status."""
        delivery = await self.session.query(WebSocketDelivery).filter(
            WebSocketDelivery.delivery_id == delivery_id
        ).first()
        
        if not delivery:
            raise NotFoundError(f"Delivery not found: {delivery_id}")
        
        try:
            delivery.status = status
            
            if status == DeliveryStatus.DELIVERED:
                delivery.delivered_at = datetime.now(timezone.utc)
            elif status == DeliveryStatus.FAILED:
                delivery.retry_after = datetime.now(timezone.utc) + timedelta(minutes=5)  # 5 minute retry
            
            if delivery_data:
                for key, value in delivery_data.items():
                    if hasattr(delivery, key):
                        setattr(delivery, key, value)
            
            await self.session.commit()
            await self.session.refresh(delivery)
            
            return delivery
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to update delivery status: {e}")
            raise ValidationError(f"Failed to update delivery status: {str(e)}")

    # Metrics Operations

    async def record_metrics(
        self,
        tenant_id: str,
        metric_data: Dict
    ) -> WebSocketMetrics:
        """Record WebSocket metrics."""
        try:
            # Get current hour metrics or create new
            current_hour = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
            
            metrics = await self.session.query(WebSocketMetrics).filter(
                and_(
                    WebSocketMetrics.tenant_id == tenant_id,
                    WebSocketMetrics.metric_date == current_hour.date(),
                    WebSocketMetrics.metric_hour == current_hour.hour
                )
            ).first()
            
            if not metrics:
                metrics = WebSocketMetrics(
                    tenant_id=tenant_id,
                    metric_date=current_hour.date(),
                    metric_hour=current_hour.hour,
                    **metric_data
                )
                self.session.add(metrics)
            else:
                # Update existing metrics
                for key, value in metric_data.items():
                    if hasattr(metrics, key):
                        current_value = getattr(metrics, key) or 0
                        if key.startswith('total_') or key.startswith('peak_'):
                            setattr(metrics, key, max(current_value, value))
                        else:
                            setattr(metrics, key, value)
            
            await self.session.commit()
            await self.session.refresh(metrics)
            
            return metrics
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to record metrics: {e}")
            raise ValidationError(f"Failed to record metrics: {str(e)}")

    async def get_tenant_event_stats(
        self,
        tenant_id: str,
        days: int = 7
    ) -> Dict:
        """Get event statistics for a tenant."""
        try:
            since_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            # Total events
            total_events = await self.session.query(func.count(WebSocketEvent.id)).filter(
                and_(
                    WebSocketEvent.tenant_id == tenant_id,
                    WebSocketEvent.created_at >= since_date
                )
            ).scalar()
            
            # Events by type
            events_by_type = await self.session.query(
                WebSocketEvent.event_type,
                func.count(WebSocketEvent.id)
            ).filter(
                and_(
                    WebSocketEvent.tenant_id == tenant_id,
                    WebSocketEvent.created_at >= since_date
                )
            ).group_by(WebSocketEvent.event_type).all()
            
            # Events by priority
            events_by_priority = await self.session.query(
                WebSocketEvent.priority,
                func.count(WebSocketEvent.id)
            ).filter(
                and_(
                    WebSocketEvent.tenant_id == tenant_id,
                    WebSocketEvent.created_at >= since_date
                )
            ).group_by(WebSocketEvent.priority).all()
            
            # Delivery success rate
            total_deliveries = await self.session.query(func.count(WebSocketDelivery.id)).join(
                WebSocketEvent
            ).filter(
                and_(
                    WebSocketEvent.tenant_id == tenant_id,
                    WebSocketEvent.created_at >= since_date
                )
            ).scalar()
            
            successful_deliveries = await self.session.query(func.count(WebSocketDelivery.id)).join(
                WebSocketEvent
            ).filter(
                and_(
                    WebSocketEvent.tenant_id == tenant_id,
                    WebSocketEvent.created_at >= since_date,
                    WebSocketDelivery.status == DeliveryStatus.DELIVERED
                )
            ).scalar()
            
            success_rate = (successful_deliveries / total_deliveries * 100) if total_deliveries > 0 else 0
            
            # Active connections
            active_connections = await self.session.query(func.count(WebSocketConnection.id)).filter(
                and_(
                    WebSocketConnection.tenant_id == tenant_id,
                    WebSocketConnection.is_active == True
                )
            ).scalar()
            
            return {
                'total_events': total_events,
                'events_by_type': dict(events_by_type),
                'events_by_priority': dict(events_by_priority),
                'delivery_success_rate': round(success_rate, 2),
                'total_deliveries': total_deliveries,
                'successful_deliveries': successful_deliveries,
                'active_connections': active_connections,
                'period_days': days
            }
            
        except Exception as e:
            logger.error(f"Failed to get tenant event stats: {e}")
            raise ValidationError(f"Failed to get tenant event stats: {str(e)}")

    # Cleanup Operations

    async def cleanup_expired_events(self) -> int:
        """Clean up expired events."""
        try:
            expired_events = await self.session.query(WebSocketEvent).filter(
                and_(
                    WebSocketEvent.expires_at.isnot(None),
                    WebSocketEvent.expires_at < datetime.now(timezone.utc)
                )
            ).all()
            
            count = len(expired_events)
            
            for event in expired_events:
                event.delivery_status = DeliveryStatus.EXPIRED
            
            await self.session.commit()
            
            logger.info(f"Marked {count} events as expired")
            return count
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to cleanup expired events: {e}")
            raise ValidationError(f"Failed to cleanup expired events: {str(e)}")

    async def cleanup_old_connections(self, hours: int = 24) -> int:
        """Clean up old inactive connections."""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            old_connections = await self.session.query(WebSocketConnection).filter(
                or_(
                    and_(
                        WebSocketConnection.is_active == False,
                        WebSocketConnection.disconnected_at < cutoff_time
                    ),
                    and_(
                        WebSocketConnection.is_active == True,
                        WebSocketConnection.last_activity < cutoff_time
                    )
                )
            ).all()
            
            count = len(old_connections)
            
            for connection in old_connections:
                await self.session.delete(connection)
            
            await self.session.commit()
            
            logger.info(f"Cleaned up {count} old connections")
            return count
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to cleanup old connections: {e}")
            raise ValidationError(f"Failed to cleanup old connections: {str(e)}")

    async def cleanup_old_deliveries(self, days: int = 30) -> int:
        """Clean up old delivery records."""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
            
            old_deliveries = await self.session.query(WebSocketDelivery).filter(
                WebSocketDelivery.attempted_at < cutoff_time
            ).all()
            
            count = len(old_deliveries)
            
            for delivery in old_deliveries:
                await self.session.delete(delivery)
            
            await self.session.commit()
            
            logger.info(f"Cleaned up {count} old delivery records")
            return count
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to cleanup old deliveries: {e}")
            raise ValidationError(f"Failed to cleanup old deliveries: {str(e)}")