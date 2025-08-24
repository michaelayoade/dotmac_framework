"""
Background tasks for billing operations.
"""

import logging
import asyncio
import aiohttp
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, Any, Optional
from uuid import UUID

from celery import current_task
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from ...core.config import settings
from ...services.billing_service import BillingService
from ...workers.celery_app import celery_app

logger = logging.getLogger(__name__)

# Payment provider configuration
STRIPE_API_URL = "https://api.stripe.com/v1"
STRIPE_API_KEY = settings.get("STRIPE_SECRET_KEY", "sk_test_...")

async def sync_payment_with_provider(payment) -> str:
    """Sync payment status with external payment provider."""
    try:
        if not payment.external_payment_id:
            return "unknown"
            
        # Stripe API integration
        headers = {
            "Authorization": f"Bearer {STRIPE_API_KEY}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        async with aiohttp.ClientSession() as session:
            # Get payment intent status from Stripe
            url = f"{STRIPE_API_URL}/payment_intents/{payment.external_payment_id}"
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    stripe_status = data.get("status", "unknown")
                    
                    # Map Stripe statuses to our internal statuses
                    status_mapping = {
                        "succeeded": "completed",
                        "processing": "pending", 
                        "requires_payment_method": "failed",
                        "requires_confirmation": "pending",
                        "requires_action": "pending",
                        "canceled": "failed",
                        "requires_capture": "pending"
                    }
                    
                    return status_mapping.get(stripe_status, "unknown")
                else:
                    logger.error(f"Failed to sync payment {payment.id} with Stripe: {response.status}")
                    return "unknown"
                    
    except Exception as e:
        logger.error(f"Error syncing payment {payment.id} with provider: {e}")
        return "unknown"

async def send_tenant_notification(
    tenant_id: UUID, 
    notification_type: str, 
    subject: str, 
    message: str, 
    metadata: Optional[Dict[str, Any]] = None
):
    """Send notification to tenant via multiple channels."""
    try:
        notification_data = {
            "tenant_id": str(tenant_id),
            "type": notification_type,
            "subject": subject,
            "message": message,
            "metadata": metadata or {},
            "channels": ["email", "dashboard"],  # Multi-channel notification
            "priority": "high" if "overdue" in notification_type else "normal",
            "created_at": date.today().isoformat()
        }
        
        # In a real implementation, this would integrate with:
        # 1. Email service (SendGrid, AWS SES, etc.)
        # 2. Dashboard notification system
        # 3. SMS service for critical notifications
        # 4. Slack/Teams integration for admin notifications
        
        # For now, we'll use the notification service
        from ...services.notification_service import NotificationService
        
        async with async_session() as session:
            notification_service = NotificationService(session)
            await notification_service.create_notification(notification_data)
        
        logger.info(f"Notification sent to tenant {tenant_id}: {notification_type}")
        
    except Exception as e:
        logger.error(f"Failed to send notification to tenant {tenant_id}: {e}")

# Create async database session for workers
engine = create_async_engine(settings.database_url)
async_session = async_sessionmaker(engine, expire_on_commit=False)


@celery_app.task(bind=True, max_retries=3)
def process_subscription_renewals(self):
    """Process subscription renewals that are due."""
    import asyncio
    
    async def _process_renewals():
        async with async_session() as db:
            try:
                service = BillingService(db)
                
                # Get subscriptions that need renewal (ending in next 7 days)
                cutoff_date = date.today() + timedelta(days=7)
                subscriptions = await service.subscription_repo.get_expiring_subscriptions(cutoff_date)
                
                processed = 0
                failed = 0
                
                for subscription in subscriptions:
                    try:
                        # Generate renewal invoice
                        await service._generate_subscription_invoice(subscription.id, "system")
                        processed += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to process renewal for subscription {subscription.id}: {e}")
                        failed += 1
                
                logger.info(f"Subscription renewals processed: {processed} successful, {failed} failed")
                return {"processed": processed, "failed": failed}
                
            except Exception as e:
                logger.error(f"Error processing subscription renewals: {e}")
                raise self.retry(countdown=60, exc=e)
    
    return asyncio.run(_process_renewals())


@celery_app.task(bind=True, max_retries=3)
def process_overdue_invoices(self):
    """Process overdue invoices and suspend services if needed."""
    import asyncio
    
    async def _process_overdue():
        async with async_session() as db:
            try:
                service = BillingService(db)
                
                # Get invoices overdue by more than 30 days
                cutoff_date = date.today() - timedelta(days=30)
                overdue_invoices = await service.invoice_repo.get_overdue_invoices(cutoff_date)
                
                suspended = 0
                notified = 0
                
                for invoice in overdue_invoices:
                    try:
                        # Update subscription status to suspended
                        if invoice.subscription:
                            await service.subscription_repo.update_status(
                                invoice.subscription.id, "suspended", "system"
                            )
                            suspended += 1
                        
                        # Send notification to tenant
                        await send_tenant_notification(
                            tenant_id=invoice.tenant_id,
                            notification_type="overdue_payment",
                            subject="Payment Overdue - Action Required",
                            message=f"Your invoice #{invoice.id} for ${invoice.amount} is overdue. "
                                   f"Please update your payment method to avoid service interruption.",
                            metadata={
                                "invoice_id": str(invoice.id),
                                "amount": str(invoice.amount),
                                "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
                                "days_overdue": days_overdue
                            }
                        )
                        notified += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to process overdue invoice {invoice.id}: {e}")
                
                logger.info(f"Overdue invoices processed: {suspended} suspended, {notified} notified")
                return {"suspended": suspended, "notified": notified}
                
            except Exception as e:
                logger.error(f"Error processing overdue invoices: {e}")
                raise self.retry(countdown=60, exc=e)
    
    return asyncio.run(_process_overdue())


@celery_app.task(bind=True, max_retries=3)
def generate_monthly_usage_invoices(self, tenant_id: str = None):
    """Generate usage-based invoices for tenants with usage billing."""
    import asyncio
    
    async def _generate_usage_invoices():
        async with async_session() as db:
            try:
                service = BillingService(db)
                
                # Get subscriptions with usage-based billing
                subscriptions = await service.subscription_repo.get_usage_based_subscriptions(
                    tenant_id=UUID(tenant_id) if tenant_id else None
                )
                
                generated = 0
                failed = 0
                
                for subscription in subscriptions:
                    try:
                        # Calculate usage for the month
                        start_date = date.today().replace(day=1) - timedelta(days=1)  # Last month
                        start_date = start_date.replace(day=1)
                        end_date = date.today().replace(day=1) - timedelta(days=1)
                        
                        # Get usage records
                        usage_records = await service.usage_repo.get_period_usage_detailed(
                            subscription.id, start_date, end_date
                        )
                        
                        if usage_records:
                            # Generate usage invoice
                            await service._generate_usage_invoice(subscription.id, usage_records, "system")
                            generated += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to generate usage invoice for subscription {subscription.id}: {e}")
                        failed += 1
                
                logger.info(f"Usage invoices generated: {generated} successful, {failed} failed")
                return {"generated": generated, "failed": failed}
                
            except Exception as e:
                logger.error(f"Error generating usage invoices: {e}")
                raise self.retry(countdown=60, exc=e)
    
    return asyncio.run(_generate_usage_invoices())


@celery_app.task(bind=True, max_retries=3)
def process_payment(self, payment_data: Dict[str, Any]):
    """Process a payment asynchronously."""
    import asyncio
    
    async def _process_payment():
        async with async_session() as db:
            try:
                service = BillingService(db)
                
                # Process the payment
                from ...schemas.billing import PaymentCreate
                payment_create = PaymentCreate(**payment_data)
                
                payment = await service.process_payment(payment_create, "system")
                
                logger.info(f"Payment processed successfully: {payment.id}")
                return {"payment_id": str(payment.id), "status": "success"}
                
            except Exception as e:
                logger.error(f"Error processing payment: {e}")
                raise self.retry(countdown=60, exc=e)
    
    return asyncio.run(_process_payment())


@celery_app.task(bind=True, max_retries=3)
def calculate_billing_analytics(self, start_date: str, end_date: str, tenant_id: str = None):
    """Calculate billing analytics for a period."""
    import asyncio
    from datetime import datetime
    
    async def _calculate_analytics():
        async with async_session() as db:
            try:
                service = BillingService(db)
                
                start = datetime.fromisoformat(start_date).date()
                end = datetime.fromisoformat(end_date).date()
                tenant_uuid = UUID(tenant_id) if tenant_id else None
                
                analytics = await service.generate_billing_analytics(start, end, tenant_uuid)
                
                logger.info(f"Billing analytics calculated for period {start} to {end}")
                return analytics
                
            except Exception as e:
                logger.error(f"Error calculating billing analytics: {e}")
                raise self.retry(countdown=60, exc=e)
    
    return asyncio.run(_calculate_analytics())


@celery_app.task(bind=True, max_retries=3)
def sync_payment_provider(self, provider: str):
    """Sync payments with external payment provider."""
    import asyncio
    
    async def _sync_payments():
        async with async_session() as db:
            try:
                service = BillingService(db)
                
                # Get pending payments
                pending_payments = await service.payment_repo.get_pending_payments(provider)
                
                synced = 0
                failed = 0
                
                for payment in pending_payments:
                    try:
                        # Integrate with payment provider API
                        external_status = await sync_payment_with_provider(payment)
                        
                        if external_status == "completed":
                            await service.payment_repo.update_status(
                                payment.id, "completed", "system"
                            )
                            synced += 1
                        elif external_status == "failed":
                            await service.payment_repo.update_status(
                                payment.id, "failed", "system"
                            )
                            failed += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to sync payment {payment.id}: {e}")
                        failed += 1
                
                logger.info(f"Payment provider sync completed: {synced} synced, {failed} failed")
                return {"synced": synced, "failed": failed}
                
            except Exception as e:
                logger.error(f"Error syncing with payment provider: {e}")
                raise self.retry(countdown=60, exc=e)
    
    return asyncio.run(_sync_payments())


@celery_app.task(bind=True, max_retries=3)
def export_billing_report(self, tenant_id: str, report_type: str, start_date: str, end_date: str):
    """Export billing report for a tenant."""
    import asyncio
    from datetime import datetime
    
    async def _export_report():
        async with async_session() as db:
            try:
                service = BillingService(db)
                
                start = datetime.fromisoformat(start_date).date()
                end = datetime.fromisoformat(end_date).date()
                tenant_uuid = UUID(tenant_id)
                
                if report_type == "invoices":
                    data = await service.invoice_repo.get_tenant_invoices_for_period(
                        tenant_uuid, start, end
                    )
                elif report_type == "payments":
                    data = await service.payment_repo.get_tenant_payments_for_period(
                        tenant_uuid, start, end
                    )
                elif report_type == "usage":
                    data = await service.usage_repo.get_tenant_usage_for_period(
                        tenant_uuid, start, end
                    )
                else:
                    raise ValueError(f"Unknown report type: {report_type}")
                
                # TODO: Generate actual report file (CSV, PDF, etc.)
                # For now, return summary
                report_summary = {
                    "tenant_id": tenant_id,
                    "report_type": report_type,
                    "period": f"{start} to {end}",
                    "record_count": len(data),
                    "generated_at": datetime.utcnow().isoformat()
                }
                
                logger.info(f"Billing report exported: {report_type} for tenant {tenant_id}")
                return report_summary
                
            except Exception as e:
                logger.error(f"Error exporting billing report: {e}")
                raise self.retry(countdown=60, exc=e)
    
    return asyncio.run(_export_report())