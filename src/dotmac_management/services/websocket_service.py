"""WebSocket Event Service for the Management Platform."""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from uuid import uuid4

from fastapi import WebSocket, WebSocketDisconnect

from dotmac_shared.exceptions import NotFoundError, ValidationError, PermissionError

from ..models.websocket_event import (
    DeliveryStatus,
    EventPriority,
    EventType,
    SubscriptionType,
    WebSocketConnection,
    WebSocketEvent,
)
from ..repositories.websocket_repository import WebSocketEventRepository

logger = logging.getLogger(__name__)


class WebSocketEventService:
    """Service for WebSocket event management and delivery."""

    def __init__(self, repository: WebSocketEventRepository):
        self.repository = repository
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_subscriptions: Dict[str, Set[str]] = {}
        self.user_connections: Dict[str, Set[str]] = {}
        self.tenant_connections: Dict[str, Set[str]] = {}

    # Connection Management

    async def register_connection(
        self,
        websocket: WebSocket,
        user_id: str,
        tenant_id: str,
        session_id: str = None,
        client_ip: str = None,
        user_agent: str = None
    ) -> str:
        """Register a new WebSocket connection."""
        try:
            await websocket.accept()
            
            connection_id = str(uuid4())
            
            # Store active connection
            self.active_connections[connection_id] = websocket
            self.connection_subscriptions[connection_id] = set()
            
            # Track by user
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(connection_id)
            
            # Track by tenant
            if tenant_id not in self.tenant_connections:
                self.tenant_connections[tenant_id] = set()
            self.tenant_connections[tenant_id].add(connection_id)
            
            # Create database record
            connection_data = {
                'connection_id': connection_id,
                'user_id': user_id,
                'session_id': session_id,
                'client_ip': client_ip,
                'user_agent': user_agent,
                'is_active': True,
                'active_subscriptions': []
            }
            
            await self.repository.create_connection(tenant_id, connection_data)
            
            # Send welcome message
            welcome_message = {
                'type': 'connection_established',
                'connection_id': connection_id,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            await websocket.send_text(json.dumps(welcome_message))
            
            logger.info(f"Registered WebSocket connection: {connection_id} for user: {user_id}")
            return connection_id
            
        except Exception as e:
            logger.error(f"Failed to register WebSocket connection: {e}")
            if connection_id in self.active_connections:
                del self.active_connections[connection_id]
            raise ValidationError(f"Failed to register connection: {str(e)}")

    async def unregister_connection(self, connection_id: str) -> bool:
        """Unregister a WebSocket connection."""
        try:
            # Remove from active connections
            websocket = self.active_connections.pop(connection_id, None)
            
            # Remove subscriptions
            self.connection_subscriptions.pop(connection_id, None)
            
            # Remove from user tracking
            for user_id, conn_set in self.user_connections.items():
                conn_set.discard(connection_id)
            
            # Remove from tenant tracking  
            for tenant_id, conn_set in self.tenant_connections.items():
                conn_set.discard(connection_id)
            
            # Update database record
            await self.repository.disconnect_connection(connection_id)
            
            logger.info(f"Unregistered WebSocket connection: {connection_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unregister connection: {e}")
            return False

    async def subscribe_to_events(
        self,
        connection_id: str,
        user_id: str,
        tenant_id: str,
        subscription_name: str,
        event_types: List[EventType] = None,
        entity_filter: Dict = None
    ) -> bool:
        """Subscribe connection to specific events."""
        try:
            if connection_id not in self.active_connections:
                raise ValidationError("Connection not found")
            
            # Add to connection subscriptions
            self.connection_subscriptions[connection_id].add(subscription_name)
            
            # Create database subscription record
            subscription_data = {
                'connection_id': connection_id,
                'subscription_name': subscription_name,
                'subscription_type': SubscriptionType.EVENT_TYPE,
                'user_id': user_id,
                'event_types': event_types,
                'entity_filter': entity_filter,
                'is_active': True
            }
            
            await self.repository.create_subscription(tenant_id, subscription_data, user_id)
            
            # Update connection's active subscriptions in database
            connection_subscriptions = list(self.connection_subscriptions[connection_id])
            await self.repository.update_connection_activity(
                connection_id,
                {'active_subscriptions': connection_subscriptions}
            )
            
            logger.info(f"Subscribed connection {connection_id} to {subscription_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create subscription: {e}")
            raise ValidationError(f"Failed to create subscription: {str(e)}")

    # Event Creation and Broadcasting

    async def create_event(
        self,
        tenant_id: str,
        event_type: EventType,
        title: str,
        event_data: Dict,
        user_id: str,
        target_user_id: str = None,
        target_user_ids: List[str] = None,
        priority: EventPriority = EventPriority.NORMAL,
        requires_acknowledgment: bool = False,
        expires_in_hours: int = None,
        broadcast_to_tenant: bool = False
    ) -> WebSocketEvent:
        """Create a new WebSocket event."""
        event_dict = {
            'event_type': event_type,
            'event_category': self._get_event_category(event_type),
            'title': title,
            'event_data': event_data,
            'priority': priority,
            'target_user_id': target_user_id,
            'target_user_ids': target_user_ids,
            'requires_acknowledgment': requires_acknowledgment,
            'broadcast_to_tenant': broadcast_to_tenant,
            'source_service': 'management_platform'
        }
        
        if expires_in_hours:
            event_dict['expires_at'] = datetime.utcnow() + timedelta(hours=expires_in_hours)
        
        event = await self.repository.create_event(tenant_id, event_dict, user_id)
        
        # Attempt immediate delivery
        await self._deliver_event(event)
        
        return event

    async def broadcast_to_tenant(
        self,
        tenant_id: str,
        event_type: EventType,
        title: str,
        event_data: Dict,
        user_id: str,
        priority: EventPriority = EventPriority.NORMAL
    ) -> WebSocketEvent:
        """Broadcast event to all users in a tenant."""
        return await self.create_event(
            tenant_id=tenant_id,
            event_type=event_type,
            title=title,
            event_data=event_data,
            user_id=user_id,
            priority=priority,
            broadcast_to_tenant=True
        )

    async def send_to_user(
        self,
        user_id: str,
        tenant_id: str,
        event_type: EventType,
        title: str,
        event_data: Dict,
        sender_user_id: str,
        priority: EventPriority = EventPriority.NORMAL,
        requires_acknowledgment: bool = False
    ) -> WebSocketEvent:
        """Send event to a specific user."""
        return await self.create_event(
            tenant_id=tenant_id,
            event_type=event_type,
            title=title,
            event_data=event_data,
            user_id=sender_user_id,
            target_user_id=user_id,
            priority=priority,
            requires_acknowledgment=requires_acknowledgment
        )

    # Event Delivery

    async def _deliver_event(self, event: WebSocketEvent) -> bool:
        """Deliver event to appropriate connections."""
        try:
            delivered_count = 0
            
            # Get target connections
            target_connections = []
            
            if event.broadcast_to_tenant:
                # Get all tenant connections
                tenant_conn_ids = self.tenant_connections.get(event.tenant_id, set())
                target_connections.extend(list(tenant_conn_ids))
            
            if event.target_user_id:
                # Get user connections
                user_conn_ids = self.user_connections.get(event.target_user_id, set())
                target_connections.extend(list(user_conn_ids))
            
            if event.target_user_ids:
                # Get connections for multiple users
                for user_id in event.target_user_ids:
                    user_conn_ids = self.user_connections.get(user_id, set())
                    target_connections.extend(list(user_conn_ids))
            
            # Remove duplicates
            target_connections = list(set(target_connections))
            
            # Prepare message
            message = {
                'event_id': event.event_id,
                'event_type': event.event_type,
                'title': event.title,
                'data': event.event_data,
                'priority': event.priority,
                'timestamp': event.created_at.isoformat(),
                'requires_acknowledgment': event.requires_acknowledgment
            }
            
            # Deliver to connections
            for connection_id in target_connections:
                websocket = self.active_connections.get(connection_id)
                if websocket:
                    try:
                        await websocket.send_text(json.dumps(message))
                        
                        # Create delivery record
                        delivery_data = {
                            'event_id': event.event_id,
                            'connection_id': connection_id,
                            'user_id': self._get_connection_user_id(connection_id),
                            'status': DeliveryStatus.DELIVERED,
                            'delivered_at': datetime.utcnow(),
                            'message_size_bytes': len(json.dumps(message))
                        }
                        
                        await self.repository.create_delivery(event.tenant_id, delivery_data)
                        delivered_count += 1
                        
                    except Exception as e:
                        logger.warning(f"Failed to deliver event to connection {connection_id}: {e}")
                        
                        # Create failed delivery record
                        delivery_data = {
                            'event_id': event.event_id,
                            'connection_id': connection_id,
                            'user_id': self._get_connection_user_id(connection_id),
                            'status': DeliveryStatus.FAILED,
                            'error_message': str(e)
                        }
                        
                        await self.repository.create_delivery(event.tenant_id, delivery_data)
            
            # Update event delivery status
            if delivered_count > 0:
                await self.repository.update_event_delivery_status(
                    event.event_id,
                    event.tenant_id,
                    DeliveryStatus.DELIVERED
                )
            else:
                await self.repository.update_event_delivery_status(
                    event.event_id,
                    event.tenant_id,
                    DeliveryStatus.FAILED,
                    "No active connections found"
                )
            
            logger.info(f"Delivered event {event.event_id} to {delivered_count} connections")
            return delivered_count > 0
            
        except Exception as e:
            logger.error(f"Failed to deliver event: {e}")
            await self.repository.update_event_delivery_status(
                event.event_id,
                event.tenant_id,
                DeliveryStatus.FAILED,
                str(e)
            )
            return False

    async def acknowledge_event(
        self,
        event_id: str,
        tenant_id: str,
        user_id: str
    ) -> bool:
        """Acknowledge an event."""
        try:
            await self.repository.acknowledge_event(event_id, tenant_id, user_id)
            logger.info(f"Event {event_id} acknowledged by user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to acknowledge event: {e}")
            raise ValidationError(f"Failed to acknowledge event: {str(e)}")

    # Event Retrieval

    async def get_user_events(
        self,
        user_id: str,
        tenant_id: str,
        event_types: List[EventType] = None,
        limit: int = 50,
        unacknowledged_only: bool = False
    ) -> List[WebSocketEvent]:
        """Get events for a user."""
        events = await self.repository.get_events_for_user(
            user_id=user_id,
            tenant_id=tenant_id,
            event_types=event_types,
            limit=limit
        )
        
        if unacknowledged_only:
            events = [
                event for event in events
                if event.requires_acknowledgment and (
                    not event.acknowledged_by or user_id not in event.acknowledged_by
                )
            ]
        
        return events

    async def get_tenant_event_stats(self, tenant_id: str, days: int = 7) -> Dict:
        """Get event statistics for a tenant."""
        return await self.repository.get_tenant_event_stats(tenant_id, days)

    # Utility Methods

    def _get_event_category(self, event_type: EventType) -> str:
        """Get event category from event type."""
        category_mapping = {
            EventType.SYSTEM_NOTIFICATION: "system",
            EventType.CONNECTION_STATUS: "system",
            EventType.HEARTBEAT: "system",
            
            EventType.USER_LOGIN: "auth",
            EventType.USER_LOGOUT: "auth",
            EventType.USER_SESSION_UPDATE: "auth",
            
            EventType.TENANT_CREATED: "tenant",
            EventType.TENANT_UPDATED: "tenant",
            EventType.TENANT_DEPLOYED: "tenant",
            EventType.TENANT_SUSPENDED: "tenant",
            
            EventType.PAYMENT_PROCESSED: "billing",
            EventType.INVOICE_GENERATED: "billing",
            EventType.BILLING_UPDATE: "billing",
            EventType.PAYMENT_FAILED: "billing",
            
            EventType.SERVICE_ACTIVATED: "service",
            EventType.SERVICE_SUSPENDED: "service",
            EventType.SERVICE_PROVISIONED: "service",
            EventType.SERVICE_ERROR: "service",
            
            EventType.NETWORK_ALERT: "network",
            EventType.DEVICE_STATUS_CHANGE: "network",
            EventType.BANDWIDTH_ALERT: "network",
            EventType.CONNECTION_EVENT: "network",
            
            EventType.TICKET_CREATED: "support",
            EventType.TICKET_UPDATED: "support",
            EventType.TICKET_ASSIGNED: "support",
            EventType.TICKET_RESOLVED: "support",
            
            EventType.FILE_UPLOADED: "file",
            EventType.FILE_DOWNLOADED: "file",
            EventType.FILE_DELETED: "file",
            EventType.FILE_SHARED: "file",
            
            EventType.DOMAIN_ADDED: "domain",
            EventType.DOMAIN_VERIFIED: "domain",
            EventType.DOMAIN_EXPIRED: "domain",
            EventType.DNS_UPDATED: "domain",
        }
        
        return category_mapping.get(event_type, "unknown")

    def _get_connection_user_id(self, connection_id: str) -> str:
        """Get user ID for a connection."""
        for user_id, conn_set in self.user_connections.items():
            if connection_id in conn_set:
                return user_id
        return "unknown"

    async def get_connection_stats(self) -> Dict:
        """Get current connection statistics."""
        return {
            'total_connections': len(self.active_connections),
            'connections_by_tenant': {
                tenant_id: len(conn_set) 
                for tenant_id, conn_set in self.tenant_connections.items()
            },
            'connections_by_user': {
                user_id: len(conn_set)
                for user_id, conn_set in self.user_connections.items()
            },
            'total_subscriptions': sum(
                len(subs) for subs in self.connection_subscriptions.values()
            )
        }

    # Background Processing

    async def process_pending_events(self, tenant_id: str = None) -> int:
        """Process pending events for delivery."""
        try:
            pending_events = await self.repository.get_pending_events(tenant_id)
            processed_count = 0
            
            for event in pending_events:
                try:
                    success = await self._deliver_event(event)
                    if success:
                        processed_count += 1
                except Exception as e:
                    logger.error(f"Failed to process event {event.event_id}: {e}")
            
            logger.info(f"Processed {processed_count} pending events")
            return processed_count
            
        except Exception as e:
            logger.error(f"Failed to process pending events: {e}")
            return 0

    async def cleanup_expired_events(self) -> int:
        """Clean up expired events."""
        return await self.repository.cleanup_expired_events()

    async def cleanup_stale_connections(self) -> int:
        """Clean up stale connections."""
        return await self.repository.cleanup_old_connections()

    # High-level Event Broadcasting Methods

    async def broadcast_tenant_update(
        self,
        tenant_id: str,
        update_type: str,
        update_data: Dict,
        user_id: str
    ) -> WebSocketEvent:
        """Broadcast tenant update event."""
        event_type_mapping = {
            'created': EventType.TENANT_CREATED,
            'updated': EventType.TENANT_UPDATED,
            'deployed': EventType.TENANT_DEPLOYED,
            'suspended': EventType.TENANT_SUSPENDED
        }
        
        event_type = event_type_mapping.get(update_type, EventType.TENANT_UPDATED)
        
        return await self.broadcast_to_tenant(
            tenant_id=tenant_id,
            event_type=event_type,
            title=f"Tenant {update_type.title()}",
            event_data=update_data,
            user_id=user_id,
            priority=EventPriority.HIGH
        )

    async def broadcast_billing_event(
        self,
        tenant_id: str,
        billing_event_type: str,
        billing_data: Dict,
        user_id: str,
        target_user_id: str = None
    ) -> WebSocketEvent:
        """Broadcast billing event."""
        event_type_mapping = {
            'payment_processed': EventType.PAYMENT_PROCESSED,
            'invoice_generated': EventType.INVOICE_GENERATED,
            'payment_failed': EventType.PAYMENT_FAILED,
            'billing_updated': EventType.BILLING_UPDATE
        }
        
        event_type = event_type_mapping.get(billing_event_type, EventType.BILLING_UPDATE)
        
        if target_user_id:
            return await self.send_to_user(
                user_id=target_user_id,
                tenant_id=tenant_id,
                event_type=event_type,
                title=f"Billing {billing_event_type.replace('_', ' ').title()}",
                event_data=billing_data,
                sender_user_id=user_id,
                priority=EventPriority.HIGH,
                requires_acknowledgment=billing_event_type == 'payment_failed'
            )
        else:
            return await self.broadcast_to_tenant(
                tenant_id=tenant_id,
                event_type=event_type,
                title=f"Billing {billing_event_type.replace('_', ' ').title()}",
                event_data=billing_data,
                user_id=user_id,
                priority=EventPriority.HIGH
            )

    async def broadcast_network_alert(
        self,
        tenant_id: str,
        alert_data: Dict,
        user_id: str,
        severity: str = "medium"
    ) -> WebSocketEvent:
        """Broadcast network alert."""
        priority_mapping = {
            'low': EventPriority.LOW,
            'medium': EventPriority.NORMAL,
            'high': EventPriority.HIGH,
            'critical': EventPriority.CRITICAL
        }
        
        priority = priority_mapping.get(severity, EventPriority.NORMAL)
        
        return await self.broadcast_to_tenant(
            tenant_id=tenant_id,
            event_type=EventType.NETWORK_ALERT,
            title=f"Network Alert - {severity.title()}",
            event_data={
                'severity': severity,
                'alert': alert_data
            },
            user_id=user_id,
            priority=priority
        )