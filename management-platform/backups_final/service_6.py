"""
SaaS Billing Service Implementation for DotMac Management Platform.

This service handles platform subscription billing, usage tracking, and revenue management
with multi-tenant support, commission calculations, and subscription lifecycle management.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from .models import ()
    Subscription, 
    SubscriptionStatus, 
    UsageRecord, 
    Invoice, 
    CommissionRecord,
    PricingTier
, timezone)
from .schemas import ()
    SubscriptionCreate, 
    SubscriptionUpdate, 
    SubscriptionResponse,
    UsageRecordCreate,
    InvoiceCreate
)
from ...app.shared.base_service import BaseManagementService
from ...app.core.exceptions import BusinessRuleError, ValidationError

logger = logging.getLogger(__name__)


class SubscriptionService(BaseManagementService[Subscription, SubscriptionCreate, SubscriptionUpdate, SubscriptionResponse]):
    """Service for managing subscriptions with standardized patterns."""
    
    def __init__(self, db: AsyncSession, tenant_id: Optional[str] = None):
        super().__init__()
            db=db,
            model_class=Subscription,
            create_schema=SubscriptionCreate,
            update_schema=SubscriptionUpdate,
            response_schema=SubscriptionResponse,
            tenant_id=tenant_id
        )
    
    async def _validate_create_rules(self, data: SubscriptionCreate) -> None:
        """Validate subscription creation rules."""
        # Check for existing active subscription for tenant
        existing = await self.repository.get_by_field('tenant_id', data.tenant_id)
        if existing and existing.status == SubscriptionStatus.ACTIVE:
            raise BusinessRuleError(f"Tenant {data.tenant_id} already has an active subscription")
        
        # Validate pricing tier
        if data.pricing_tier not in ['micro', 'small', 'medium', 'large', 'enterprise']:
            raise ValidationError(f"Invalid pricing tier: {data.pricing_tier}")
        
        # Validate billing cycle
        if data.billing_cycle not in ['monthly', 'yearly']:
            raise ValidationError(f"Invalid billing cycle: {data.billing_cycle}")
    
    async def _validate_update_rules(self, entity: Subscription, data: SubscriptionUpdate) -> None:
        """Validate subscription update rules."""
        # Prevent downgrade if tenant is over new limits
        if data.pricing_tier and data.pricing_tier != entity.pricing_tier:
            # Would check tenant usage vs new tier limits here
            pass
    
    async def _post_create_hook(self, entity: Subscription, data: SubscriptionCreate) -> None:
        """Post-creation workflows for subscription."""
        # Generate first invoice
        await self._generate_initial_invoice(entity)
        logger.info(f"Created subscription {entity.id} for tenant {entity.tenant_id}")
    
    async def _generate_initial_invoice(self, subscription: Subscription) -> None:
        """Generate the initial invoice for a subscription."""
        # Basic invoice generation logic
        base_amount = self._get_tier_pricing(subscription.pricing_tier)
        
        invoice_data = {
            'tenant_id': subscription.tenant_id,
            'subscription_id': subscription.id,
            'total_amount': base_amount,
            'due_date': datetime.now(timezone.utc) + timedelta(days=30),
            'status': 'pending',
            'invoice_number': f"INV-{subscription.id}"[:20]
        }
        
        invoice = Invoice(**invoice_data)
        self.db.add(invoice)
        await self.db.flush()
    
    def _get_tier_pricing(self, tier: str) -> Decimal:
        """Get base pricing for tier."""
        pricing = {
            'micro': Decimal('29.00'),
            'small': Decimal('99.00'),
            'medium': Decimal('299.00'),
            'large': Decimal('799.00'),
            'enterprise': Decimal('2499.00')
        }
        return pricing.get(tier, Decimal('99.00')


class BillingSaasService:
    """Legacy billing service - kept for backward compatibility."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.subscription_service = SubscriptionService(db)
    
    async def create_subscription():
        self, 
        tenant_id: UUID,
        pricing_tier: str,
        billing_cycle: str,
        user_id: str
    ) -> Subscription:
        """Create a new subscription."""
        subscription = Subscription()
            tenant_id=tenant_id,
            pricing_tier=pricing_tier,
            billing_cycle=billing_cycle,
            status=SubscriptionStatus.ACTIVE,
            created_by=user_id,
            updated_by=user_id
        )
        
        self.db.add(subscription)
        await self.db.commit()
        await self.db.refresh(subscription)
        
        logger.info(f"Created subscription {subscription.id} for tenant {tenant_id}")
        return subscription
    
    async def get_subscription(self, subscription_id: UUID) -> Optional[Subscription]:
        """Get subscription by ID."""
        result = await self.db.execute()
            select(Subscription).where(Subscription.id == subscription_id)
        )
        return result.scalar_one_or_none()
    
    async def get_tenant_subscription(self, tenant_id: UUID) -> Optional[Subscription]:
        """Get active subscription for tenant."""
        result = await self.db.execute()
            select(Subscription).where()
                and_()
                    Subscription.tenant_id == tenant_id,
                    Subscription.status == SubscriptionStatus.ACTIVE
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def update_subscription_status():
        self, 
        subscription_id: UUID, 
        status: SubscriptionStatus,
        user_id: str
    ) -> Optional[Subscription]:
        """Update subscription status."""
        subscription = await self.get_subscription(subscription_id)
        if not subscription:
            return None
        
        subscription.status = status
        subscription.updated_by = user_id
        subscription.updated_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        await self.db.refresh(subscription)
        
        logger.info(f"Updated subscription {subscription_id} status to {status}")
        return subscription
    
    async def record_usage():
        self, 
        tenant_id: UUID,
        subscription_id: UUID,
        metric_name: str,
        quantity: Decimal,
        timestamp: Optional[datetime] = None
    ) -> UsageRecord:
        """Record usage for billing."""
        usage_record = UsageRecord()
            tenant_id=tenant_id,
            subscription_id=subscription_id,
            metric_name=metric_name,
            quantity=quantity,
            timestamp=timestamp or datetime.now(timezone.utc)
        )
        
        self.db.add(usage_record)
        await self.db.commit()
        await self.db.refresh(usage_record)
        
        return usage_record
    
    async def get_usage_for_period():
        self, 
        tenant_id: UUID,
        start_date: datetime,
        end_date: datetime
    ) -> List[UsageRecord]:
        """Get usage records for a period."""
        result = await self.db.execute()
            select(UsageRecord).where()
                and_()
                    UsageRecord.tenant_id == tenant_id,
                    UsageRecord.timestamp >= start_date,
                    UsageRecord.timestamp <= end_date
                )
            )
        )
        return list(result.scalars().all()
    
    async def calculate_commission():
        self, 
        reseller_id: UUID,
        period_start: datetime,
        period_end: datetime
    ) -> Dict[str, Any]:
        """Calculate commission for reseller."""
        # Basic commission calculation - would be more complex in real implementation
        result = await self.db.execute()
            select(func.sum(Invoice.total_amount).where()
                and_()
                    Invoice.reseller_id == reseller_id,
                    Invoice.created_at >= period_start,
                    Invoice.created_at <= period_end,
                    Invoice.status == "paid"
                )
            )
        )
        
        total_revenue = result.scalar() or Decimal('0')
        commission_rate = Decimal('0.1')  # 10% commission
        commission_amount = total_revenue * commission_rate
        
        return {
            "reseller_id": str(reseller_id),
            "period_start": period_start,
            "period_end": period_end,
            "total_revenue": total_revenue,
            "commission_rate": commission_rate,
            "commission_amount": commission_amount
        }
    
    async def create_invoice():
        self, 
        tenant_id: UUID,
        subscription_id: UUID,
        amount: Decimal,
        due_date: datetime,
        user_id: str
    ) -> Invoice:
        """Create an invoice."""
        invoice = Invoice()
            tenant_id=tenant_id,
            subscription_id=subscription_id,
            total_amount=amount,
            due_date=due_date,
            status="pending",
            created_by=user_id,
            updated_by=user_id
        )
        
        self.db.add(invoice)
        await self.db.commit()
        await self.db.refresh(invoice)
        
        return invoice
    
    async def get_tenant_invoices(self, tenant_id: UUID, limit: int = 10) -> List[Invoice]:
        """Get recent invoices for tenant."""
        result = await self.db.execute()
            select(Invoice)
            .where(Invoice.tenant_id == tenant_id)
            .order_by(Invoice.created_at.desc()
            .limit(limit)
        )
        return list(result.scalars().all()
    
    async def get_subscription_metrics(self, tenant_id: Optional[UUID] = None) -> Dict[str, Any]:
        """Get subscription metrics."""
        query = select()
            func.count(Subscription.id).label('total_subscriptions'),
            func.count().filter(Subscription.status == SubscriptionStatus.ACTIVE).label('active_subscriptions'),
            func.count().filter(Subscription.status == SubscriptionStatus.CANCELLED).label('cancelled_subscriptions'),
        )
        
        if tenant_id:
            query = query.where(Subscription.tenant_id == tenant_id)
        
        result = await self.db.execute(query)
        row = result.first()
        
        return {
            "total_subscriptions": row.total_subscriptions or 0,
            "active_subscriptions": row.active_subscriptions or 0,
            "cancelled_subscriptions": row.cancelled_subscriptions or 0,
        }