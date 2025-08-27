"""
Plugin-based billing service for subscription and payment management.
"""

import logging
from datetime import datetime, timezone, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from database import database_transaction
from repositories.billing import (
    BillingPlanRepository, SubscriptionRepository, InvoiceRepository,
    PaymentRepository, UsageRecordRepository
)
from repositories.customer import CustomerRepository
from models.billing import (
    PricingPlan, Subscription, Invoice, Payment, UsageRecord,
    SubscriptionStatus, InvoiceStatus, PaymentStatus
)
from models.customer import Customer
from core.exceptions import (
    SubscriptionNotFoundError, ActiveSubscriptionExistsError,
    PaymentProcessingError, BusinessLogicError, DatabaseError,
    ExternalServiceError, ResourceNotFoundError
)
from core.plugins.service_integration import service_integration
from core.plugins.interfaces import PaymentProviderPlugin, BillingCalculatorPlugin
from core.plugins.base import PluginType
from config import settings

logger = logging.getLogger(__name__)


class PluginBillingService:
    """Plugin-based billing service for subscription and payment management."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.plan_repo = BillingPlanRepository(db)
        self.subscription_repo = SubscriptionRepository(db)
        self.invoice_repo = InvoiceRepository(db)
        self.payment_repo = PaymentRepository(db)
        self.usage_repo = UsageRecordRepository(db)
        self.customer_repo = CustomerRepository(db)
        self.service_integration = service_integration
    
    async def create_subscription(
        self,
        tenant_id: UUID,
        plan_id: UUID,
        customer_id: UUID,
        payment_method: Optional[Dict[str, Any]] = None,
        trial_days: Optional[int] = None,
        created_by: str = None
    ) -> Subscription:
        """Create a new subscription using plugin-based payment provider."""
        try:
            async with database_transaction(self.db) as tx:
                # Check if plan exists
                plan = await self.plan_repo.get_by_id(plan_id)
                if not plan:
                    raise ResourceNotFoundError("Billing Plan", plan_id)
                
                # Check for existing active subscription
                existing = await self.subscription_repo.get_active_subscription(tenant_id)
                if existing:
                    raise ActiveSubscriptionExistsError(f"Tenant {tenant_id} already has an active subscription")
                
                # Get customer details
                customer = await self.customer_repo.get_by_id(customer_id)
                if not customer:
                    raise ResourceNotFoundError("Customer", customer_id)
                
                # Calculate dates
                start_date = datetime.now(timezone.utc)
                trial_end_date = None
                current_period_end = start_date
                
                if trial_days and trial_days > 0:
                    trial_end_date = start_date + timedelta(days=trial_days)
                    current_period_end = trial_end_date
                else:
                    # Calculate period end based on billing interval
                    if plan.billing_interval == "monthly":
                        current_period_end = start_date + timedelta(days=30)
                    elif plan.billing_interval == "annual":
                        current_period_end = start_date + timedelta(days=365)
                    else:
                        current_period_end = start_date + timedelta(days=30)
                
                # Create subscription
                subscription_data = {
                    "tenant_id": tenant_id,
                    "pricing_plan_id": plan_id,
                    "status": SubscriptionStatus.TRIAL if trial_end_date else SubscriptionStatus.ACTIVE,
                    "current_period_start": start_date,
                    "current_period_end": current_period_end,
                    "trial_start": start_date if trial_end_date else None,
                    "trial_end": trial_end_date,
                    "billing_cycle_day": start_date.day,
                    "current_usage": {},
                    "default_payment_method_id": None
                }
                
                # Create subscription via plugin if payment provider specified
                payment_provider = getattr(settings, 'DEFAULT_PAYMENT_PROVIDER', 'stripe')
                if payment_method and payment_provider:
                    try:
                        # Use plugin to create subscription with payment provider
                        subscription_result = await self.service_integration.create_subscription_via_plugin(
                            payment_provider,
                            {
                                "plan_config": {
                                    "id": str(plan_id),
                                    "name": plan.name,
                                    "amount": int(plan.base_price_cents),
                                    "currency": "usd",
                                    "interval": plan.billing_interval
                                },
                                "customer_data": {
                                    "id": str(customer_id),
                                    "email": customer.email,
                                    "name": customer.full_name
                                },
                                "payment_method": payment_method
                            }
                        )
                        
                        # Store external subscription ID
                        subscription_data["stripe_subscription_id"] = subscription_result.get("subscription_id")
                        subscription_data["stripe_customer_id"] = subscription_result.get("customer_id")
                        
                    except Exception as e:
                        logger.error(f"Failed to create subscription with payment provider: {e}")
                        # Continue without payment provider integration
                        pass
                
                subscription = await self.subscription_repo.create(subscription_data, created_by)
                
                # Generate first invoice if not in trial
                if not trial_end_date:
                    await self._generate_subscription_invoice(subscription.id, created_by)
                
                logger.info(f"Subscription created: {subscription.id} for tenant {tenant_id}")
                return subscription
                
        except (ResourceNotFoundError, ActiveSubscriptionExistsError):
            raise
        except Exception as e:
            logger.error(f"Failed to create subscription: {e}", exc_info=True)
            raise DatabaseError(
                message="Failed to create subscription",
                details={"error": str(e), "tenant_id": str(tenant_id), "plan_id": str(plan_id)}
            )
    
    async def process_payment(
        self,
        invoice_id: UUID,
        payment_method: Dict[str, Any],
        payment_provider: str = "stripe",
        created_by: Optional[str] = None
    ) -> Payment:
        """Process payment using plugin-based payment provider."""
        try:
            # Get invoice
            invoice = await self.invoice_repo.get_by_id(invoice_id)
            if not invoice:
                raise ResourceNotFoundError("Invoice", invoice_id)
            
            if invoice.status == InvoiceStatus.PAID:
                raise BusinessLogicError("Invoice is already paid")
            
            # Process payment via plugin
            payment_result = await self.service_integration.process_payment_via_plugin(
                payment_provider,
                invoice.total_cents / 100,  # Convert to decimal
                payment_method,
                {
                    "invoice_id": str(invoice_id),
                    "tenant_id": str(invoice.subscription.tenant_id) if invoice.subscription else None,
                    "subscription_id": str(invoice.subscription_id) if invoice.subscription_id else None
                }
            )
            
            # Create payment record
            payment_data = {
                "invoice_id": invoice_id,
                "amount_cents": int(payment_result.get("amount", 0) * 100),
                "currency": payment_result.get("currency", "USD"),
                "status": PaymentStatus.SUCCEEDED if payment_result.get("success") else PaymentStatus.FAILED,
                "payment_method_type": payment_method.get("type", "card"),
                "payment_method_details": {
                    "last4": payment_method.get("last4"),
                    "brand": payment_method.get("brand")
                },
                "processed_at": datetime.now(timezone.utc),
                "stripe_payment_intent_id": payment_result.get("payment_intent_id"),
                "stripe_charge_id": payment_result.get("charge_id"),
                "processor_fee_cents": int(payment_result.get("fees", 0) * 100)
            }
            
            if not payment_result.get("success"):
                payment_data.update({
                    "failed_at": datetime.now(timezone.utc),
                    "failure_reason": payment_result.get("error_message", "Payment failed")
                })
            
            payment = await self.payment_repo.create(payment_data, created_by)
            
            # Update invoice status if payment successful
            if payment.status == PaymentStatus.SUCCEEDED:
                await self.invoice_repo.update(invoice_id, {
                    "status": InvoiceStatus.PAID,
                    "paid_at": payment.processed_at,
                    "amount_paid_cents": payment.amount_cents
                }, created_by)
                
                # Update subscription status if needed
                if invoice.subscription_id:
                    subscription = await self.subscription_repo.get_by_id(invoice.subscription_id)
                    if subscription and subscription.status in [SubscriptionStatus.PAST_DUE, SubscriptionStatus.UNPAID]:
                        await self.subscription_repo.update(subscription.id, {
                            "status": SubscriptionStatus.ACTIVE
                        }, created_by)
            
            logger.info(f"Payment processed: {payment.amount_cents/100} for invoice {invoice.invoice_number}")
            return payment
            
        except (ResourceNotFoundError, BusinessLogicError):
            raise
        except Exception as e:
            logger.error(f"Failed to process payment: {e}", exc_info=True)
            raise PaymentProcessingError(
                message="Failed to process payment",
                details={"error": str(e), "invoice_id": str(invoice_id)}
            )
    
    async def calculate_usage_billing(
        self,
        tenant_id: UUID,
        usage_data: List[Dict[str, Any]],
        calculator_name: str = "standard",
        billing_period_start: Optional[datetime] = None,
        billing_period_end: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Calculate usage-based billing using plugin-based calculator."""
        try:
            # Get active subscription
            subscription = await self.subscription_repo.get_active_subscription(tenant_id)
            if not subscription:
                raise SubscriptionNotFoundError(f"No active subscription for tenant {tenant_id}")
            
            # Get pricing plan
            plan = await self.plan_repo.get_by_id(subscription.pricing_plan_id)
            if not plan:
                raise ResourceNotFoundError("Pricing Plan", subscription.pricing_plan_id)
            
            # Set billing period
            if not billing_period_start:
                billing_period_start = subscription.current_period_start
            if not billing_period_end:
                billing_period_end = subscription.current_period_end
            
            # Prepare billing plan data for plugin
            billing_plan = {
                "id": str(plan.id),
                "name": plan.name,
                "type": plan.plan_type.value if hasattr(plan.plan_type, 'value') else str(plan.plan_type),
                "base_price": float(plan.base_price_cents / 100),
                "usage_limits": plan.usage_limits,
                "pricing_tiers": plan.pricing_tiers,
                "features": plan.features,
                "billing_interval": plan.billing_interval
            }
            
            # Calculate usage cost via plugin
            usage_cost = await self.service_integration.calculate_billing_via_plugin(
                calculator_name,
                usage_data,
                billing_plan
            )
            
            # Create usage records
            total_cost_cents = int(float(usage_cost) * 100)
            
            for usage_item in usage_data:
                usage_record_data = {
                    "subscription_id": subscription.id,
                    "tenant_id": tenant_id,
                    "metric_name": usage_item.get("metric_name", "unknown"),
                    "quantity": Decimal(str(usage_item.get("quantity", 0))),
                    "unit_price_cents": int(usage_item.get("unit_price", 0) * 100),
                    "total_cost_cents": int(usage_item.get("cost", 0) * 100),
                    "usage_date": datetime.now(timezone.utc),
                    "period_start": billing_period_start,
                    "period_end": billing_period_end,
                    "description": usage_item.get("description"),
                    "metadata_json": usage_item.get("metadata", {})
                }
                
                await self.usage_repo.create(usage_record_data)
            
            return {
                "total_usage_cost": float(usage_cost),
                "base_cost": float(plan.base_price_cents / 100),
                "total_cost": float(plan.base_price_cents / 100) + float(usage_cost),
                "usage_items": len(usage_data),
                "billing_period_start": billing_period_start,
                "billing_period_end": billing_period_end,
                "calculator_used": calculator_name
            }
            
        except (SubscriptionNotFoundError, ResourceNotFoundError):
            raise
        except Exception as e:
            logger.error(f"Failed to calculate usage billing: {e}", exc_info=True)
            raise BusinessLogicError(
                message="Failed to calculate usage billing",
                details={"error": str(e), "tenant_id": str(tenant_id)}
            )
    
    async def cancel_subscription(
        self,
        subscription_id: UUID,
        reason: Optional[str] = None,
        immediate: bool = False,
        process_refund: bool = True,
        updated_by: Optional[str] = None
    ) -> Subscription:
        """Cancel subscription with optional refund processing."""
        try:
            subscription = await self.subscription_repo.get_by_id(subscription_id)
            if not subscription:
                raise SubscriptionNotFoundError(f"Subscription {subscription_id} not found")
            
            if subscription.status == SubscriptionStatus.CANCELLED:
                raise BusinessLogicError("Subscription is already cancelled")
            
            cancellation_date = datetime.now(timezone.utc)
            
            # Cancel with payment provider if external subscription exists
            if subscription.stripe_subscription_id:
                try:
                    payment_provider = getattr(settings, 'DEFAULT_PAYMENT_PROVIDER', 'stripe')
                    await self.service_integration.cancel_subscription_via_plugin(
                        payment_provider,
                        subscription.stripe_subscription_id,
                        reason or "Customer requested cancellation"
                    )
                except Exception as e:
                    logger.error(f"Failed to cancel subscription with payment provider: {e}")
            
            # Update subscription
            update_data = {
                "status": SubscriptionStatus.CANCELLED,
                "cancelled_at": cancellation_date,
                "cancel_reason": reason
            }
            
            if immediate:
                update_data["current_period_end"] = cancellation_date
            else:
                update_data["cancel_at_period_end"] = True
            
            subscription = await self.subscription_repo.update(subscription_id, update_data, updated_by)
            
            # Process refund if requested and subscription was cancelled immediately
            if process_refund and immediate:
                await self._process_cancellation_refund(subscription, reason or "Cancellation refund")
            
            logger.info(f"Subscription cancelled: {subscription_id}, reason: {reason}")
            return subscription
            
        except (SubscriptionNotFoundError, BusinessLogicError):
            raise
        except Exception as e:
            logger.error(f"Failed to cancel subscription: {e}", exc_info=True)
            raise DatabaseError(
                message="Failed to cancel subscription",
                details={"error": str(e), "subscription_id": str(subscription_id)}
            )
    
    async def _generate_subscription_invoice(
        self,
        subscription_id: UUID,
        created_by: Optional[str] = None
    ) -> Invoice:
        """Generate an invoice for a subscription."""
        subscription = await self.subscription_repo.get_by_id(subscription_id)
        if not subscription:
            raise SubscriptionNotFoundError(f"Subscription {subscription_id} not found")
        
        plan = await self.plan_repo.get_by_id(subscription.pricing_plan_id)
        if not plan:
            raise ResourceNotFoundError("Pricing Plan", subscription.pricing_plan_id)
        
        # Generate invoice number
        today = datetime.now(timezone.utc)
        invoice_count = await self.invoice_repo.count({})
        invoice_number = f"INV-{today.strftime('%Y%m')}-{invoice_count + 1:04d}"
        
        # Calculate amounts
        base_amount_cents = plan.base_price_cents
        tax_rate = Decimal("0.08")  # 8% tax rate - should be configurable
        subtotal_cents = base_amount_cents
        tax_cents = int(subtotal_cents * tax_rate)
        total_cents = subtotal_cents + tax_cents
        
        # Calculate due date
        due_date = today + timedelta(days=30)
        
        invoice_data = {
            "subscription_id": subscription_id,
            "invoice_number": invoice_number,
            "status": InvoiceStatus.DRAFT,
            "period_start": subscription.current_period_start,
            "period_end": subscription.current_period_end,
            "subtotal_cents": subtotal_cents,
            "tax_cents": tax_cents,
            "total_cents": total_cents,
            "amount_due_cents": total_cents,
            "invoice_date": today,
            "due_date": due_date,
            "currency": "USD",
            "description": f"Subscription to {plan.name}",
            "line_items": [
                {
                    "description": f"{plan.name} subscription",
                    "quantity": 1,
                    "unit_price_cents": base_amount_cents,
                    "total_cents": base_amount_cents
                }
            ]
        }
        
        return await self.invoice_repo.create(invoice_data, created_by)
    
    async def _process_cancellation_refund(
        self,
        subscription: Subscription,
        reason: str
    ):
        """Process refund for cancelled subscription."""
        try:
            # Calculate prorated refund amount
            today = datetime.now(timezone.utc)
            period_start = subscription.current_period_start
            period_end = subscription.current_period_end
            
            if today < period_end:
                total_period_days = (period_end - period_start).days
                remaining_days = (period_end - today).days
                
                if total_period_days > 0 and remaining_days > 0:
                    # Get last payment amount
                    latest_payment = await self.payment_repo.get_latest_payment(subscription.id)
                    if latest_payment and latest_payment.status == PaymentStatus.SUCCEEDED:
                        refund_ratio = remaining_days / total_period_days
                        refund_amount = float(latest_payment.amount_cents / 100) * refund_ratio
                        
                        if refund_amount > 0:
                            # Process refund via payment provider plugin
                            if subscription.stripe_subscription_id and latest_payment.stripe_charge_id:
                                try:
                                    payment_provider = getattr(settings, 'DEFAULT_PAYMENT_PROVIDER', 'stripe')
                                    refund_result = await self.service_integration.refund_payment_via_plugin(
                                        payment_provider,
                                        latest_payment.stripe_charge_id,
                                        Decimal(str(refund_amount)),
                                        reason
                                    )
                                    
                                    logger.info(f"Processed refund: ${refund_amount:.2f} for subscription {subscription.id}")
                                    
                                except Exception as e:
                                    logger.error(f"Failed to process refund via payment provider: {e}")
            
        except Exception as e:
            logger.error(f"Failed to process cancellation refund: {e}")
    
    async def get_available_payment_providers(self) -> List[Dict[str, Any]]:
        """Get list of available payment providers from plugins."""
        providers = []
        
        try:
            payment_plugins = self.service_integration.registry.get_plugins_by_type(PluginType.PAYMENT_PROVIDER)
            
            for plugin in payment_plugins:
                if isinstance(plugin, PaymentProviderPlugin):
                    providers.append({
                        "name": plugin.meta.name,
                        "description": plugin.meta.description,
                        "supported_currencies": plugin.get_supported_currencies(),
                        "supported_payment_methods": plugin.get_supported_payment_methods(),
                        "status": plugin.status.value if hasattr(plugin.status, 'value') else str(plugin.status)
                    })
            
        except Exception as e:
            logger.error(f"Failed to get payment providers: {e}")
        
        return providers
    
    async def get_available_billing_calculators(self) -> List[Dict[str, Any]]:
        """Get list of available billing calculators from plugins."""
        calculators = []
        
        try:
            billing_plugins = self.service_integration.registry.get_plugins_by_type(PluginType.BILLING_CALCULATOR)
            
            for plugin in billing_plugins:
                if isinstance(plugin, BillingCalculatorPlugin):
                    calculators.append({
                        "name": plugin.meta.name,
                        "description": plugin.meta.description,
                        "supported_billing_models": plugin.get_supported_billing_models(),
                        "status": plugin.status.value if hasattr(plugin.status, 'value') else str(plugin.status)
                    })
            
        except Exception as e:
            logger.error(f"Failed to get billing calculators: {e}")
        
        return calculators
    
    async def get_tenant_billing_overview(
        self,
        tenant_id: UUID
    ) -> Dict[str, Any]:
        """Get comprehensive billing overview for a tenant."""
        try:
            # Get active subscription
            subscription = await self.subscription_repo.get_active_subscription(tenant_id)
            
            # Get recent invoices
            recent_invoices = await self.invoice_repo.get_tenant_invoices(tenant_id, limit=5)
            
            # Get recent payments
            recent_payments = await self.payment_repo.get_tenant_payments(tenant_id, limit=5)
            
            # Calculate outstanding balance
            outstanding_balance = await self._calculate_outstanding_balance(tenant_id)
            
            # Get usage summary
            usage_summary = {}
            if subscription:
                usage_records = await self.usage_repo.get_subscription_usage(
                    subscription.id,
                    subscription.current_period_start,
                    subscription.current_period_end
                )
                
                total_usage_cost = sum(float(record.total_cost_cents / 100) for record in usage_records)
                usage_summary = {
                    "current_period_usage_cost": total_usage_cost,
                    "usage_records_count": len(usage_records),
                    "period_start": subscription.current_period_start,
                    "period_end": subscription.current_period_end
                }
            
            return {
                "tenant_id": str(tenant_id),
                "subscription": {
                    "id": str(subscription.id) if subscription else None,
                    "status": subscription.status.value if subscription and hasattr(subscription.status, 'value') else str(subscription.status) if subscription else None,
                    "plan_name": subscription.pricing_plan.name if subscription and subscription.pricing_plan else None,
                    "current_period_start": subscription.current_period_start if subscription else None,
                    "current_period_end": subscription.current_period_end if subscription else None,
                    "cancel_at_period_end": subscription.cancel_at_period_end if subscription else None
                },
                "outstanding_balance": float(outstanding_balance),
                "usage_summary": usage_summary,
                "recent_invoices": [
                    {
                        "id": str(invoice.id),
                        "invoice_number": invoice.invoice_number,
                        "status": invoice.status.value if hasattr(invoice.status, 'value') else str(invoice.status),
                        "total_amount": float(invoice.total_cents / 100),
                        "due_date": invoice.due_date,
                        "paid_at": invoice.paid_at
                    }
                    for invoice in recent_invoices
                ],
                "recent_payments": [
                    {
                        "id": str(payment.id),
                        "amount": float(payment.amount_cents / 100),
                        "status": payment.status.value if hasattr(payment.status, 'value') else str(payment.status),
                        "processed_at": payment.processed_at,
                        "payment_method_type": payment.payment_method_type
                    }
                    for payment in recent_payments
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to get billing overview: {e}")
            raise DatabaseError(
                message="Failed to get billing overview",
                details={"error": str(e), "tenant_id": str(tenant_id)}
            )
    
    async def _calculate_outstanding_balance(self, tenant_id: UUID) -> Decimal:
        """Calculate total outstanding balance for a tenant."""
        unpaid_invoices = await self.invoice_repo.get_unpaid_invoices(tenant_id)
        return Decimal(sum(invoice.total_cents for invoice in unpaid_invoices)) / 100