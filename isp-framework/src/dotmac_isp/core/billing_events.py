"""Billing Events Integration for Real-time Frontend Updates."""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from decimal import Decimal

from ..core.websocket_manager import websocket_manager, WebSocketMessage, EventType
from ..api.websocket_router import broadcast_billing_event

logger = logging.getLogger(__name__)


class BillingEventManager:
    """
    Billing Event Manager for real-time frontend notifications.
    
    Integrates with the billing system to send real-time updates to the frontend
    when billing events occur (payments processed, invoices generated, etc.).
    """
    
    @staticmethod
    async def on_payment_processed(
        payment_data: Dict[str, Any],
        tenant_id: str,
        customer_id: str = None
    ):
        """
        Handle payment processed event.
        
        Args:
            payment_data: Payment data
            tenant_id: Tenant ID
            customer_id: Customer ID (optional)
        """
        try:
            # Extract key payment information
            event_data = {
                "payment_id": payment_data.get("id"),
                "amount": float(payment_data.get("amount", 0)),
                "currency": payment_data.get("currency", "USD"),
                "payment_method": payment_data.get("payment_method"),
                "status": payment_data.get("status"),
                "customer_id": customer_id or payment_data.get("customer_id"),
                "invoice_id": payment_data.get("invoice_id"),
                "transaction_id": payment_data.get("transaction_id"),
                "processed_at": payment_data.get("processed_at", datetime.utcnow().isoformat()),
                "gateway": payment_data.get("gateway"),
            }
            
            # Broadcast to billing updates subscribers
            await broadcast_billing_event(
                event_type="payment_processed",
                data=event_data,
                tenant_id=tenant_id,
                user_id=customer_id
            )
            
            logger.info(f"Payment processed event broadcasted: {payment_data.get('id')}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast payment processed event: {e}")
    
    @staticmethod
    async def on_invoice_generated(
        invoice_data: Dict[str, Any],
        tenant_id: str,
        customer_id: str = None
    ):
        """
        Handle invoice generated event.
        
        Args:
            invoice_data: Invoice data
            tenant_id: Tenant ID
            customer_id: Customer ID (optional)
        """
        try:
            # Extract key invoice information
            event_data = {
                "invoice_id": invoice_data.get("id"),
                "invoice_number": invoice_data.get("invoice_number"),
                "customer_id": customer_id or invoice_data.get("customer_id"),
                "total_amount": float(invoice_data.get("total_amount", 0)),
                "currency": invoice_data.get("currency", "USD"),
                "status": invoice_data.get("status"),
                "due_date": invoice_data.get("due_date"),
                "generated_at": invoice_data.get("created_at", datetime.utcnow().isoformat()),
                "billing_period": invoice_data.get("billing_period"),
                "items_count": len(invoice_data.get("items", [])),
                "pdf_url": invoice_data.get("pdf_url"),
            }
            
            # Broadcast to billing updates subscribers
            await broadcast_billing_event(
                event_type="invoice_generated",
                data=event_data,
                tenant_id=tenant_id,
                user_id=customer_id
            )
            
            logger.info(f"Invoice generated event broadcasted: {invoice_data.get('invoice_number')}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast invoice generated event: {e}")
    
    @staticmethod
    async def on_billing_updated(
        update_data: Dict[str, Any],
        tenant_id: str,
        customer_id: str = None
    ):
        """
        Handle general billing update event.
        
        Args:
            update_data: Update data
            tenant_id: Tenant ID
            customer_id: Customer ID (optional)
        """
        try:
            # Format update information
            event_data = {
                "update_type": update_data.get("type", "general"),
                "entity_id": update_data.get("entity_id"),
                "entity_type": update_data.get("entity_type", "billing"),
                "customer_id": customer_id or update_data.get("customer_id"),
                "changes": update_data.get("changes", {}),
                "updated_at": update_data.get("updated_at", datetime.utcnow().isoformat()),
                "message": update_data.get("message", "Billing information updated"),
            }
            
            # Broadcast to billing updates subscribers
            await broadcast_billing_event(
                event_type="billing_updated",
                data=event_data,
                tenant_id=tenant_id,
                user_id=customer_id
            )
            
            logger.info(f"Billing updated event broadcasted: {update_data.get('type')}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast billing updated event: {e}")
    
    @staticmethod
    async def on_payment_failed(
        payment_data: Dict[str, Any],
        tenant_id: str,
        customer_id: str = None
    ):
        """
        Handle payment failed event.
        
        Args:
            payment_data: Payment data
            tenant_id: Tenant ID
            customer_id: Customer ID (optional)
        """
        try:
            # Extract key payment failure information
            event_data = {
                "payment_id": payment_data.get("id"),
                "amount": float(payment_data.get("amount", 0)),
                "currency": payment_data.get("currency", "USD"),
                "payment_method": payment_data.get("payment_method"),
                "customer_id": customer_id or payment_data.get("customer_id"),
                "invoice_id": payment_data.get("invoice_id"),
                "failure_reason": payment_data.get("failure_reason"),
                "failure_code": payment_data.get("failure_code"),
                "failed_at": payment_data.get("failed_at", datetime.utcnow().isoformat()),
                "retry_possible": payment_data.get("retry_possible", True),
                "gateway": payment_data.get("gateway"),
            }
            
            # Create high-priority message for payment failures
            message = WebSocketMessage(
                event_type=EventType.BILLING_UPDATE,
                data={
                    "type": "payment_failed",
                    "severity": "high",
                    **event_data
                },
                tenant_id=tenant_id,
                user_id=customer_id
            )
            
            # Send to user and billing subscribers
            if customer_id:
                await websocket_manager.broadcast_to_user(customer_id, message)
            
            await websocket_manager.broadcast_to_subscription("billing_updates", message, tenant_id)
            
            logger.warning(f"Payment failed event broadcasted: {payment_data.get('id')}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast payment failed event: {e}")
    
    @staticmethod
    async def on_subscription_changed(
        subscription_data: Dict[str, Any],
        tenant_id: str,
        customer_id: str = None
    ):
        """
        Handle subscription changed event.
        
        Args:
            subscription_data: Subscription data
            tenant_id: Tenant ID
            customer_id: Customer ID (optional)
        """
        try:
            # Extract key subscription information
            event_data = {
                "subscription_id": subscription_data.get("id"),
                "customer_id": customer_id or subscription_data.get("customer_id"),
                "plan_id": subscription_data.get("plan_id"),
                "plan_name": subscription_data.get("plan_name"),
                "status": subscription_data.get("status"),
                "previous_status": subscription_data.get("previous_status"),
                "change_type": subscription_data.get("change_type", "status_change"),
                "effective_date": subscription_data.get("effective_date"),
                "next_billing_date": subscription_data.get("next_billing_date"),
                "monthly_amount": float(subscription_data.get("monthly_amount", 0)),
                "currency": subscription_data.get("currency", "USD"),
                "changed_at": subscription_data.get("changed_at", datetime.utcnow().isoformat()),
            }
            
            # Broadcast to billing updates subscribers
            await broadcast_billing_event(
                event_type="billing_updated",
                data={
                    "type": "subscription_changed",
                    **event_data
                },
                tenant_id=tenant_id,
                user_id=customer_id
            )
            
            logger.info(f"Subscription changed event broadcasted: {subscription_data.get('id')}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast subscription changed event: {e}")
    
    @staticmethod
    async def on_credit_balance_updated(
        balance_data: Dict[str, Any],
        tenant_id: str,
        customer_id: str = None
    ):
        """
        Handle credit balance updated event.
        
        Args:
            balance_data: Balance data
            tenant_id: Tenant ID
            customer_id: Customer ID (optional)
        """
        try:
            # Extract key balance information
            event_data = {
                "customer_id": customer_id or balance_data.get("customer_id"),
                "previous_balance": float(balance_data.get("previous_balance", 0)),
                "new_balance": float(balance_data.get("new_balance", 0)),
                "change_amount": float(balance_data.get("change_amount", 0)),
                "change_type": balance_data.get("change_type"),
                "currency": balance_data.get("currency", "USD"),
                "reference_id": balance_data.get("reference_id"),
                "description": balance_data.get("description"),
                "updated_at": balance_data.get("updated_at", datetime.utcnow().isoformat()),
            }
            
            # Broadcast to billing updates subscribers
            await broadcast_billing_event(
                event_type="billing_updated",
                data={
                    "type": "credit_balance_updated",
                    **event_data
                },
                tenant_id=tenant_id,
                user_id=customer_id
            )
            
            logger.info(f"Credit balance updated event broadcasted for customer: {customer_id}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast credit balance updated event: {e}")


# Integration functions for billing module

async def notify_payment_processed(payment_record, tenant_id: str):
    """Notify frontend of processed payment."""
    payment_data = {
        "id": str(payment_record.id),
        "amount": payment_record.amount,
        "currency": payment_record.currency,
        "payment_method": payment_record.payment_method.value if payment_record.payment_method else None,
        "status": payment_record.status.value if payment_record.status else None,
        "customer_id": str(payment_record.customer_id) if payment_record.customer_id else None,
        "invoice_id": str(payment_record.invoice_id) if payment_record.invoice_id else None,
        "transaction_id": payment_record.transaction_id,
        "processed_at": payment_record.processed_at.isoformat() if payment_record.processed_at else None,
        "gateway": payment_record.gateway,
    }
    
    await BillingEventManager.on_payment_processed(
        payment_data, 
        tenant_id, 
        str(payment_record.customer_id) if payment_record.customer_id else None
    )


async def notify_invoice_generated(invoice_record, tenant_id: str):
    """Notify frontend of generated invoice."""
    invoice_data = {
        "id": str(invoice_record.id),
        "invoice_number": invoice_record.invoice_number,
        "customer_id": str(invoice_record.customer_id) if invoice_record.customer_id else None,
        "total_amount": invoice_record.total_amount,
        "currency": invoice_record.currency,
        "status": invoice_record.status.value if invoice_record.status else None,
        "due_date": invoice_record.due_date.isoformat() if invoice_record.due_date else None,
        "created_at": invoice_record.created_at.isoformat() if invoice_record.created_at else None,
        "billing_period": f"{invoice_record.billing_period_start} - {invoice_record.billing_period_end}",
        "items": [],  # Would be populated from related invoice items
    }
    
    await BillingEventManager.on_invoice_generated(
        invoice_data,
        tenant_id,
        str(invoice_record.customer_id) if invoice_record.customer_id else None
    )


async def notify_payment_failed(payment_record, failure_reason: str, tenant_id: str):
    """Notify frontend of failed payment."""
    payment_data = {
        "id": str(payment_record.id),
        "amount": payment_record.amount,
        "currency": payment_record.currency,
        "payment_method": payment_record.payment_method.value if payment_record.payment_method else None,
        "customer_id": str(payment_record.customer_id) if payment_record.customer_id else None,
        "invoice_id": str(payment_record.invoice_id) if payment_record.invoice_id else None,
        "failure_reason": failure_reason,
        "failed_at": datetime.utcnow().isoformat(),
        "retry_possible": True,  # Could be determined based on failure type
        "gateway": payment_record.gateway,
    }
    
    await BillingEventManager.on_payment_failed(
        payment_data,
        tenant_id,
        str(payment_record.customer_id) if payment_record.customer_id else None
    )


# Event handler registration
async def register_billing_event_handlers():
    """Register billing event handlers with WebSocket manager."""
    try:
        # Register event handlers for billing events
        websocket_manager.register_event_handler(
            EventType.PAYMENT_PROCESSED,
            lambda msg: logger.info(f"Payment processed: {msg.data.get('payment_id')}")
        )
        
        websocket_manager.register_event_handler(
            EventType.INVOICE_GENERATED,
            lambda msg: logger.info(f"Invoice generated: {msg.data.get('invoice_number')}")
        )
        
        websocket_manager.register_event_handler(
            EventType.BILLING_UPDATE,
            lambda msg: logger.info(f"Billing updated: {msg.data.get('type')}")
        )
        
        logger.info("Billing event handlers registered successfully")
        
    except Exception as e:
        logger.error(f"Failed to register billing event handlers: {e}")


# Utility functions for common billing notifications

async def send_low_balance_alert(customer_id: str, current_balance: float, tenant_id: str):
    """Send low balance alert to customer."""
    message = WebSocketMessage(
        event_type=EventType.BILLING_UPDATE,
        data={
            "type": "low_balance_alert",
            "customer_id": customer_id,
            "current_balance": current_balance,
            "currency": "USD",  # Would come from customer settings
            "message": f"Your account balance is low: ${current_balance:.2f}",
            "action_required": True,
            "suggested_actions": ["Add funds", "Update payment method"]
        },
        tenant_id=tenant_id,
        user_id=customer_id
    )
    
    await websocket_manager.broadcast_to_user(customer_id, message)


async def send_payment_reminder(customer_id: str, invoice_data: Dict[str, Any], tenant_id: str):
    """Send payment reminder to customer."""
    message = WebSocketMessage(
        event_type=EventType.BILLING_UPDATE,
        data={
            "type": "payment_reminder",
            "customer_id": customer_id,
            "invoice_id": invoice_data.get("id"),
            "invoice_number": invoice_data.get("invoice_number"),
            "amount_due": invoice_data.get("amount_due"),
            "due_date": invoice_data.get("due_date"),
            "days_overdue": invoice_data.get("days_overdue", 0),
            "message": "Payment reminder for your outstanding invoice",
            "action_required": True
        },
        tenant_id=tenant_id,
        user_id=customer_id
    )
    
    await websocket_manager.broadcast_to_user(customer_id, message)