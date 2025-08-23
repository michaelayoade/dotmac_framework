"""
Stripe payment integration service for the DotMac Management Platform.
Handles subscriptions, payments, invoices, and webhook processing.
"""

import logging
import stripe
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..models.billing import (
    Subscription, Invoice, Payment, PricingPlan,
    SubscriptionStatus, InvoiceStatus, PaymentStatus
)
from ..repositories.billing_additional import (
    SubscriptionRepository, InvoiceRepository, PaymentRepository
)
from ..schemas.billing import (
    SubscriptionCreate, InvoiceCreate, PaymentCreate,
    StripeWebhookEvent, StripeCustomerCreate, StripeSubscriptionCreate
)

logger = logging.getLogger(__name__)

# Configure Stripe
stripe.api_key = settings.stripe_secret_key


class StripeService:
    """Comprehensive Stripe payment integration service."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.subscription_repo = SubscriptionRepository(db)
        self.invoice_repo = InvoiceRepository(db)
        self.payment_repo = PaymentRepository(db)
    
    async def create_customer(
        self, 
        tenant_id: UUID,
        email: str,
        name: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Create a Stripe customer for a tenant."""
        try:
            customer_metadata = {
                "tenant_id": str(tenant_id),
                **(metadata or {})
            }
            
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata=customer_metadata,
                description=f"DotMac tenant: {name}"
            )
            
            logger.info(f"Created Stripe customer {customer.id} for tenant {tenant_id}")
            return {
                "stripe_customer_id": customer.id,
                "email": customer.email,
                "name": customer.name,
                "created": customer.created
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe customer creation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create Stripe customer: {str(e)}"
            )
    
    async def create_product_and_prices(
        self, 
        pricing_plan: PricingPlan
    ) -> Dict[str, Any]:
        """Create Stripe product and pricing for a pricing plan."""
        try:
            # Create product
            product = stripe.Product.create(
                name=pricing_plan.name,
                description=pricing_plan.description,
                metadata={
                    "pricing_plan_id": str(pricing_plan.id),
                    "features": str(pricing_plan.features)
                }
            )
            
            # Create prices for different billing cycles
            prices = {}
            
            if pricing_plan.monthly_price_cents:
                monthly_price = stripe.Price.create(
                    product=product.id,
                    unit_amount=pricing_plan.monthly_price_cents,
                    currency="usd",
                    recurring={"interval": "month"},
                    metadata={"billing_cycle": "monthly"}
                )
                prices["monthly"] = monthly_price.id
            
            if pricing_plan.annual_price_cents:
                annual_price = stripe.Price.create(
                    product=product.id,
                    unit_amount=pricing_plan.annual_price_cents,
                    currency="usd", 
                    recurring={"interval": "year"},
                    metadata={"billing_cycle": "annual"}
                )
                prices["annual"] = annual_price.id
            
            logger.info(f"Created Stripe product {product.id} for pricing plan {pricing_plan.id}")
            return {
                "stripe_product_id": product.id,
                "stripe_prices": prices
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe product creation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create Stripe product: {str(e)}"
            )
    
    async def create_subscription(
        self,
        stripe_customer_id: str,
        stripe_price_id: str,
        tenant_id: UUID,
        trial_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a Stripe subscription."""
        try:
            subscription_params = {
                "customer": stripe_customer_id,
                "items": [{"price": stripe_price_id}],
                "metadata": {
                    "tenant_id": str(tenant_id)
                },
                "expand": ["latest_invoice.payment_intent"]
            }
            
            if trial_days:
                subscription_params["trial_period_days"] = trial_days
            
            stripe_subscription = stripe.Subscription.create(**subscription_params)
            
            # Update local subscription record
            local_subscription = await self.subscription_repo.get_by_tenant_id(tenant_id)
            if local_subscription:
                await self.subscription_repo.update(
                    local_subscription.id,
                    {
                        "stripe_subscription_id": stripe_subscription.id,
                        "stripe_customer_id": stripe_customer_id,
                        "status": self._map_stripe_status(stripe_subscription.status),
                        "current_period_start": datetime.fromtimestamp(stripe_subscription.current_period_start),
                        "current_period_end": datetime.fromtimestamp(stripe_subscription.current_period_end)
                    },
                    "stripe_service"
                )
            
            logger.info(f"Created Stripe subscription {stripe_subscription.id} for tenant {tenant_id}")
            return {
                "stripe_subscription_id": stripe_subscription.id,
                "status": stripe_subscription.status,
                "current_period_start": stripe_subscription.current_period_start,
                "current_period_end": stripe_subscription.current_period_end,
                "client_secret": stripe_subscription.latest_invoice.payment_intent.client_secret if stripe_subscription.latest_invoice.payment_intent else None
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe subscription creation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create Stripe subscription: {str(e)}"
            )
    
    async def cancel_subscription(
        self,
        stripe_subscription_id: str,
        immediately: bool = False
    ) -> Dict[str, Any]:
        """Cancel a Stripe subscription."""
        try:
            if immediately:
                # Cancel immediately
                subscription = stripe.Subscription.delete(stripe_subscription_id)
            else:
                # Cancel at period end
                subscription = stripe.Subscription.modify(
                    stripe_subscription_id,
                    cancel_at_period_end=True
                )
            
            # Update local record
            local_subscription = await self.subscription_repo.get_by_stripe_id(stripe_subscription_id)
            if local_subscription:
                update_data = {
                    "status": SubscriptionStatus.CANCELLED if immediately else SubscriptionStatus.PENDING_CANCELLATION,
                }
                if immediately:
                    update_data["cancelled_at"] = datetime.utcnow()
                    
                await self.subscription_repo.update(
                    local_subscription.id,
                    update_data,
                    "stripe_service"
                )
            
            logger.info(f"Cancelled Stripe subscription {stripe_subscription_id}")
            return {
                "status": subscription.status,
                "cancel_at_period_end": subscription.cancel_at_period_end,
                "canceled_at": subscription.canceled_at
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe subscription cancellation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to cancel Stripe subscription: {str(e)}"
            )
    
    async def create_payment_intent(
        self,
        amount_cents: int,
        customer_id: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Create a Stripe payment intent for one-time payments."""
        try:
            payment_intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency="usd",
                customer=customer_id,
                metadata=metadata or {},
                automatic_payment_methods={"enabled": True}
            )
            
            logger.info(f"Created payment intent {payment_intent.id} for ${amount_cents/100:.2f}")
            return {
                "payment_intent_id": payment_intent.id,
                "client_secret": payment_intent.client_secret,
                "status": payment_intent.status,
                "amount": payment_intent.amount
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Payment intent creation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create payment intent: {str(e)}"
            )
    
    async def process_webhook(self, payload: bytes, signature: str) -> Dict[str, Any]:
        """Process Stripe webhook events."""
        try:
            # Verify webhook signature
            event = stripe.Webhook.construct_event(
                payload, signature, settings.stripe_webhook_secret
            )
            
            logger.info(f"Processing Stripe webhook: {event['type']}")
            
            # Route to appropriate handler
            if event["type"] == "invoice.payment_succeeded":
                return await self._handle_payment_succeeded(event["data"]["object"])
            elif event["type"] == "invoice.payment_failed":
                return await self._handle_payment_failed(event["data"]["object"])
            elif event["type"] == "customer.subscription.updated":
                return await self._handle_subscription_updated(event["data"]["object"])
            elif event["type"] == "customer.subscription.deleted":
                return await self._handle_subscription_deleted(event["data"]["object"])
            elif event["type"] == "invoice.created":
                return await self._handle_invoice_created(event["data"]["object"])
            else:
                logger.info(f"Unhandled webhook event type: {event['type']}")
                return {"status": "ignored", "event_type": event["type"]}
                
        except stripe.error.SignatureVerificationError:
            logger.error("Invalid Stripe webhook signature")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid webhook signature"
            )
        except Exception as e:
            logger.error(f"Webhook processing failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Webhook processing failed"
            )
    
    async def _handle_payment_succeeded(self, stripe_invoice: Dict[str, Any]) -> Dict[str, Any]:
        """Handle successful payment webhook."""
        try:
            # Find local invoice
            local_invoice = await self.invoice_repo.get_by_stripe_id(stripe_invoice["id"])
            
            if local_invoice:
                # Update invoice status
                await self.invoice_repo.update(
                    local_invoice.id,
                    {
                        "status": InvoiceStatus.PAID,
                        "paid_at": datetime.fromtimestamp(stripe_invoice["status_transitions"]["paid_at"]),
                        "amount_paid_cents": stripe_invoice["amount_paid"]
                    },
                    "stripe_webhook"
                )
                
                # Create payment record
                payment_data = PaymentCreate(
                    invoice_id=local_invoice.id,
                    amount_cents=stripe_invoice["amount_paid"],
                    payment_method="stripe",
                    payment_processor="stripe",
                    processor_payment_id=stripe_invoice["payment_intent"],
                    status=PaymentStatus.COMPLETED
                )
                await self.payment_repo.create(payment_data.dict(), "stripe_webhook")
                
                # Update subscription status if needed
                if stripe_invoice.get("subscription"):
                    subscription = await self.subscription_repo.get_by_stripe_id(
                        stripe_invoice["subscription"]
                    )
                    if subscription:
                        await self.subscription_repo.update(
                            subscription.id,
                            {"status": SubscriptionStatus.ACTIVE},
                            "stripe_webhook"
                        )
                
                logger.info(f"Processed successful payment for invoice {local_invoice.id}")
                return {"status": "processed", "invoice_id": str(local_invoice.id)}
            else:
                logger.warning(f"Local invoice not found for Stripe invoice {stripe_invoice['id']}")
                return {"status": "ignored", "reason": "invoice_not_found"}
                
        except Exception as e:
            logger.error(f"Failed to handle payment succeeded: {e}")
            raise
    
    async def _handle_payment_failed(self, stripe_invoice: Dict[str, Any]) -> Dict[str, Any]:
        """Handle failed payment webhook."""
        try:
            local_invoice = await self.invoice_repo.get_by_stripe_id(stripe_invoice["id"])
            
            if local_invoice:
                # Update invoice status
                await self.invoice_repo.update(
                    local_invoice.id,
                    {"status": InvoiceStatus.PAYMENT_FAILED},
                    "stripe_webhook"
                )
                
                # Update subscription status if multiple failures
                if stripe_invoice.get("subscription"):
                    subscription = await self.subscription_repo.get_by_stripe_id(
                        stripe_invoice["subscription"]
                    )
                    if subscription:
                        # Check if this is multiple failures
                        failed_payments = await self.payment_repo.count_failed_for_subscription(
                            subscription.id
                        )
                        if failed_payments >= 3:  # 3 strikes rule
                            await self.subscription_repo.update(
                                subscription.id,
                                {
                                    "status": SubscriptionStatus.SUSPENDED,
                                    "suspended_at": datetime.utcnow()
                                },
                                "stripe_webhook"
                            )
                
                logger.info(f"Processed failed payment for invoice {local_invoice.id}")
                return {"status": "processed", "invoice_id": str(local_invoice.id)}
            else:
                return {"status": "ignored", "reason": "invoice_not_found"}
                
        except Exception as e:
            logger.error(f"Failed to handle payment failed: {e}")
            raise
    
    async def _handle_subscription_updated(self, stripe_subscription: Dict[str, Any]) -> Dict[str, Any]:
        """Handle subscription updated webhook."""
        try:
            local_subscription = await self.subscription_repo.get_by_stripe_id(
                stripe_subscription["id"]
            )
            
            if local_subscription:
                update_data = {
                    "status": self._map_stripe_status(stripe_subscription["status"]),
                    "current_period_start": datetime.fromtimestamp(
                        stripe_subscription["current_period_start"]
                    ),
                    "current_period_end": datetime.fromtimestamp(
                        stripe_subscription["current_period_end"]
                    )
                }
                
                if stripe_subscription.get("canceled_at"):
                    update_data["cancelled_at"] = datetime.fromtimestamp(
                        stripe_subscription["canceled_at"]
                    )
                
                await self.subscription_repo.update(
                    local_subscription.id,
                    update_data,
                    "stripe_webhook"
                )
                
                logger.info(f"Updated subscription {local_subscription.id} from webhook")
                return {"status": "processed", "subscription_id": str(local_subscription.id)}
            else:
                return {"status": "ignored", "reason": "subscription_not_found"}
                
        except Exception as e:
            logger.error(f"Failed to handle subscription updated: {e}")
            raise
    
    async def _handle_subscription_deleted(self, stripe_subscription: Dict[str, Any]) -> Dict[str, Any]:
        """Handle subscription deleted webhook."""
        try:
            local_subscription = await self.subscription_repo.get_by_stripe_id(
                stripe_subscription["id"]
            )
            
            if local_subscription:
                await self.subscription_repo.update(
                    local_subscription.id,
                    {
                        "status": SubscriptionStatus.CANCELLED,
                        "cancelled_at": datetime.utcnow()
                    },
                    "stripe_webhook"
                )
                
                logger.info(f"Cancelled subscription {local_subscription.id} from webhook")
                return {"status": "processed", "subscription_id": str(local_subscription.id)}
            else:
                return {"status": "ignored", "reason": "subscription_not_found"}
                
        except Exception as e:
            logger.error(f"Failed to handle subscription deleted: {e}")
            raise
    
    async def _handle_invoice_created(self, stripe_invoice: Dict[str, Any]) -> Dict[str, Any]:
        """Handle invoice created webhook."""
        try:
            # Check if we already have this invoice
            existing_invoice = await self.invoice_repo.get_by_stripe_id(stripe_invoice["id"])
            if existing_invoice:
                return {"status": "ignored", "reason": "invoice_already_exists"}
            
            # Find the subscription
            if stripe_invoice.get("subscription"):
                subscription = await self.subscription_repo.get_by_stripe_id(
                    stripe_invoice["subscription"]
                )
                
                if subscription:
                    # Create local invoice record
                    invoice_data = InvoiceCreate(
                        subscription_id=subscription.id,
                        stripe_invoice_id=stripe_invoice["id"],
                        amount_cents=stripe_invoice["total"],
                        description=f"Subscription invoice for period {stripe_invoice['period_start']} to {stripe_invoice['period_end']}",
                        due_date=datetime.fromtimestamp(stripe_invoice["due_date"]) if stripe_invoice.get("due_date") else None,
                        status=InvoiceStatus.PENDING
                    )
                    
                    local_invoice = await self.invoice_repo.create(invoice_data.dict(), "stripe_webhook")
                    
                    logger.info(f"Created local invoice {local_invoice.id} from Stripe webhook")
                    return {"status": "processed", "invoice_id": str(local_invoice.id)}
            
            return {"status": "ignored", "reason": "no_matching_subscription"}
            
        except Exception as e:
            logger.error(f"Failed to handle invoice created: {e}")
            raise
    
    def _map_stripe_status(self, stripe_status: str) -> SubscriptionStatus:
        """Map Stripe subscription status to local status."""
        status_mapping = {
            "active": SubscriptionStatus.ACTIVE,
            "trialing": SubscriptionStatus.TRIALING,
            "past_due": SubscriptionStatus.PAST_DUE,
            "canceled": SubscriptionStatus.CANCELLED,
            "unpaid": SubscriptionStatus.SUSPENDED,
            "incomplete": SubscriptionStatus.PENDING,
            "incomplete_expired": SubscriptionStatus.CANCELLED
        }
        return status_mapping.get(stripe_status, SubscriptionStatus.PENDING)
    
    async def get_usage_records(
        self, 
        stripe_subscription_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get usage records from Stripe for metered billing."""
        try:
            # Get subscription items
            subscription = stripe.Subscription.retrieve(stripe_subscription_id)
            usage_records = []
            
            for item in subscription["items"]["data"]:
                if item["price"]["billing_scheme"] == "per_unit":
                    # Get usage records for this subscription item
                    usage = stripe.UsageRecord.list(
                        subscription_item=item["id"],
                        limit=100
                    )
                    usage_records.extend(usage["data"])
            
            return usage_records
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to get usage records: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to get usage records: {str(e)}"
            )
    
    async def create_usage_record(
        self,
        subscription_item_id: str,
        quantity: int,
        timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Create a usage record in Stripe for metered billing."""
        try:
            usage_record = stripe.UsageRecord.create(
                subscription_item=subscription_item_id,
                quantity=quantity,
                timestamp=int(timestamp.timestamp()) if timestamp else None
            )
            
            logger.info(f"Created usage record {usage_record.id} for {quantity} units")
            return {
                "usage_record_id": usage_record.id,
                "quantity": usage_record.quantity,
                "timestamp": usage_record.timestamp
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Usage record creation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create usage record: {str(e)}"
            )