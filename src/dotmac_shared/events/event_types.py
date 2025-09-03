"""
Event type definitions for the DotMac Framework
"""
from enum import Enum


class EventType(Enum):
    """Enumeration of all event types in the system"""
    
    # Customer Events
    CUSTOMER_CREATED = "customer.created"
    CUSTOMER_UPDATED = "customer.updated"
    CUSTOMER_DELETED = "customer.deleted"
    CUSTOMER_VERIFIED = "customer.verified"
    
    # Billing Events
    BILLING_ACCOUNT_CREATED = "billing_account.created"
    BILLING_ACCOUNT_UPDATED = "billing_account.updated"
    PAYMENT_PROCESSING_REQUESTED = "payment.processing_requested"
    PAYMENT_PROCESSED = "payment.processed"
    PAYMENT_FAILED = "payment.failed"
    INVOICE_GENERATED = "invoice.generated"
    INVOICE_SENT = "invoice.sent"
    INVOICE_PAID = "invoice.paid"
    
    # Service Events
    SERVICE_PLAN_CREATED = "service_plan.created"
    SERVICE_PLAN_UPDATED = "service_plan.updated"
    SERVICE_PLAN_UPGRADED = "service_plan.upgraded"
    SERVICE_PROVISIONING_STARTED = "service.provisioning_started"
    SERVICE_PROVISIONING_COMPLETED = "service.provisioning_completed"
    SERVICE_PROVISIONING_FAILED = "service.provisioning_failed"
    SERVICE_ACTIVATED = "service.activated"
    SERVICE_SUSPENDED = "service.suspended"
    SERVICE_RESTORED = "service.restored"
    SERVICE_TERMINATED = "service.terminated"
    
    # Notification Events
    NOTIFICATION_QUEUED = "notification.queued"
    NOTIFICATION_SENT = "notification.sent"
    NOTIFICATION_DELIVERED = "notification.delivered"
    NOTIFICATION_FAILED = "notification.failed"
    
    # Infrastructure Events
    NETWORK_CONFIGURED = "network.configured"
    EQUIPMENT_ASSIGNED = "equipment.assigned"
    EQUIPMENT_PROVISIONED = "equipment.provisioned"
    
    # Audit Events
    AUDIT_LOG_CREATED = "audit.log_created"
    SECURITY_EVENT = "security.event"
    ACCESS_GRANTED = "access.granted"
    ACCESS_DENIED = "access.denied"