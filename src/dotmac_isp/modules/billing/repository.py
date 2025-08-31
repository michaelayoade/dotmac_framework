"""
Billing module repositories.

Uses DRY patterns from base repository to provide consistent data access
for billing entities with tenant isolation and standard CRUD operations.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, desc, extract, func, or_
from sqlalchemy.orm import Session, joinedload

from dotmac_isp.shared.base_repository import BaseTenantRepository
from dotmac_isp.shared.exceptions import EntityNotFoundError, ValidationError

from .models import (
    BillingCustomer,
    BillingPlan,
    CreditNote,
    Invoice,
    InvoiceLineItem,
    Payment,
    Subscription,
    TaxRate,
    UsageRecord,
)


class BillingCustomerRepository(BaseTenantRepository[BillingCustomer]):
    """Repository for billing customer operations."""
    
    def __init__(self, db: Session, tenant_id: str):
        super().__init__(db, BillingCustomer, tenant_id)
    
    def find_by_email(self, email: str) -> Optional[BillingCustomer]:
        """Find customer by email address."""
        return (
            self._build_base_query()
            .filter(BillingCustomer.email == email.lower())
            .first()
        )
    
    def find_by_customer_code(self, customer_code: str) -> Optional[BillingCustomer]:
        """Find customer by customer code."""
        return (
            self._build_base_query()
            .filter(BillingCustomer.customer_code == customer_code)
            .first()
        )
    
    def find_by_isp_customer_id(self, isp_customer_id: str) -> Optional[BillingCustomer]:
        """Find customer by ISP customer ID."""
        return (
            self._build_base_query()
            .filter(BillingCustomer.isp_customer_id == isp_customer_id)
            .first()
        )
    
    def get_customers_with_overdue_invoices(self, days_overdue: int = 30) -> List[BillingCustomer]:
        """Get customers with overdue invoices."""
        cutoff_date = datetime.utcnow() - timedelta(days=days_overdue)
        
        return (
            self._build_base_query()
            .join(Invoice)
            .filter(
                and_(
                    Invoice.status.in_(["sent", "pending"]),
                    Invoice.due_date < cutoff_date,
                    Invoice.amount_due > 0
                )
            )
            .distinct()
            .all()
        )
    
    def get_customers_by_connection_type(self, connection_type: str) -> List[BillingCustomer]:
        """Get customers by connection type."""
        return (
            self._build_base_query()
            .filter(BillingCustomer.connection_type == connection_type)
            .all()
        )


class BillingPlanRepository(BaseTenantRepository[BillingPlan]):
    """Repository for billing plan operations."""
    
    def __init__(self, db: Session, tenant_id: str):
        super().__init__(db, BillingPlan, tenant_id)
    
    def find_by_plan_code(self, plan_code: str) -> Optional[BillingPlan]:
        """Find billing plan by plan code."""
        return (
            self._build_base_query()
            .filter(BillingPlan.plan_code == plan_code)
            .first()
        )
    
    def get_active_plans(self) -> List[BillingPlan]:
        """Get all active billing plans."""
        return (
            self._build_base_query()
            .filter(BillingPlan.is_active == True)
            .order_by(BillingPlan.base_price)
            .all()
        )
    
    def get_public_plans(self) -> List[BillingPlan]:
        """Get public billing plans."""
        return (
            self._build_base_query()
            .filter(
                and_(
                    BillingPlan.is_active == True,
                    BillingPlan.is_public == True
                )
            )
            .order_by(BillingPlan.base_price)
            .all()
        )
    
    def get_plans_by_service_type(self, service_type: str) -> List[BillingPlan]:
        """Get plans by service type."""
        return (
            self._build_base_query()
            .filter(
                and_(
                    BillingPlan.is_active == True,
                    BillingPlan.service_type == service_type
                )
            )
            .order_by(BillingPlan.base_price)
            .all()
        )
    
    def get_plans_by_bandwidth_range(
        self, 
        min_download: Optional[Decimal] = None,
        max_download: Optional[Decimal] = None
    ) -> List[BillingPlan]:
        """Get plans within bandwidth range."""
        query = self._build_base_query().filter(BillingPlan.is_active == True)
        
        if min_download is not None:
            query = query.filter(BillingPlan.bandwidth_down >= min_download)
        if max_download is not None:
            query = query.filter(BillingPlan.bandwidth_down <= max_download)
            
        return query.order_by(BillingPlan.bandwidth_down).all()


class SubscriptionRepository(BaseTenantRepository[Subscription]):
    """Repository for subscription operations."""
    
    def __init__(self, db: Session, tenant_id: str):
        super().__init__(db, Subscription, tenant_id)
    
    def get_customer_subscriptions(self, customer_id: UUID) -> List[Subscription]:
        """Get all subscriptions for a customer."""
        return (
            self._build_base_query()
            .filter(Subscription.customer_id == customer_id)
            .options(joinedload(Subscription.billing_plan))
            .order_by(desc(Subscription.created_at))
            .all()
        )
    
    def get_active_subscriptions(self) -> List[Subscription]:
        """Get all active subscriptions."""
        return (
            self._build_base_query()
            .filter(Subscription.status == "active")
            .options(
                joinedload(Subscription.customer),
                joinedload(Subscription.billing_plan)
            )
            .all()
        )
    
    def get_subscriptions_for_billing(self, billing_date: datetime) -> List[Subscription]:
        """Get subscriptions that need billing on a specific date."""
        return (
            self._build_base_query()
            .filter(
                and_(
                    Subscription.status == "active",
                    Subscription.next_billing_date <= billing_date
                )
            )
            .options(
                joinedload(Subscription.customer),
                joinedload(Subscription.billing_plan)
            )
            .all()
        )
    
    def get_expiring_subscriptions(self, days_ahead: int = 30) -> List[Subscription]:
        """Get subscriptions expiring within specified days."""
        expiry_date = datetime.utcnow() + timedelta(days=days_ahead)
        
        return (
            self._build_base_query()
            .filter(
                and_(
                    Subscription.status == "active",
                    Subscription.end_date.isnot(None),
                    Subscription.end_date <= expiry_date
                )
            )
            .options(joinedload(Subscription.customer))
            .all()
        )
    
    def get_subscriptions_by_service_address(self, service_address: str) -> List[Subscription]:
        """Get subscriptions by service address."""
        return (
            self._build_base_query()
            .filter(Subscription.service_address.ilike(f"%{service_address}%"))
            .options(
                joinedload(Subscription.customer),
                joinedload(Subscription.billing_plan)
            )
            .all()
        )


class InvoiceRepository(BaseTenantRepository[Invoice]):
    """Repository for invoice operations."""
    
    def __init__(self, db: Session, tenant_id: str):
        super().__init__(db, Invoice, tenant_id)
    
    def find_by_invoice_number(self, invoice_number: str) -> Optional[Invoice]:
        """Find invoice by invoice number."""
        return (
            self._build_base_query()
            .filter(Invoice.invoice_number == invoice_number)
            .options(
                joinedload(Invoice.customer),
                joinedload(Invoice.line_items)
            )
            .first()
        )
    
    def get_customer_invoices(self, customer_id: UUID) -> List[Invoice]:
        """Get all invoices for a customer."""
        return (
            self._build_base_query()
            .filter(Invoice.customer_id == customer_id)
            .options(joinedload(Invoice.line_items))
            .order_by(desc(Invoice.created_at))
            .all()
        )
    
    def get_overdue_invoices(self, days_overdue: int = 0) -> List[Invoice]:
        """Get overdue invoices."""
        cutoff_date = datetime.utcnow() - timedelta(days=days_overdue)
        
        return (
            self._build_base_query()
            .filter(
                and_(
                    Invoice.status.in_(["sent", "pending"]),
                    Invoice.due_date < cutoff_date,
                    Invoice.amount_due > 0
                )
            )
            .options(joinedload(Invoice.customer))
            .order_by(Invoice.due_date)
            .all()
        )
    
    def get_unpaid_invoices(self) -> List[Invoice]:
        """Get all unpaid invoices."""
        return (
            self._build_base_query()
            .filter(
                and_(
                    Invoice.status.in_(["sent", "pending", "overdue"]),
                    Invoice.amount_due > 0
                )
            )
            .options(joinedload(Invoice.customer))
            .order_by(Invoice.due_date)
            .all()
        )
    
    def get_revenue_by_period(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> Tuple[Decimal, int]:
        """Get total revenue and invoice count for a period."""
        result = (
            self._build_base_query()
            .filter(
                and_(
                    Invoice.invoice_date >= start_date,
                    Invoice.invoice_date <= end_date,
                    Invoice.status.in_(["paid", "partially_paid"])
                )
            )
            .with_entities(
                func.sum(Invoice.amount_paid).label("total_revenue"),
                func.count(Invoice.id).label("invoice_count")
            )
            .first()
        )
        
        return (
            result.total_revenue or Decimal("0"),
            result.invoice_count or 0
        )
    
    def get_monthly_revenue_trend(self, months: int = 12) -> List[Dict[str, Any]]:
        """Get monthly revenue trend."""
        start_date = datetime.utcnow() - timedelta(days=months * 31)
        
        results = (
            self._build_base_query()
            .filter(
                and_(
                    Invoice.invoice_date >= start_date,
                    Invoice.status.in_(["paid", "partially_paid"])
                )
            )
            .with_entities(
                extract("year", Invoice.invoice_date).label("year"),
                extract("month", Invoice.invoice_date).label("month"),
                func.sum(Invoice.amount_paid).label("revenue"),
                func.count(Invoice.id).label("invoice_count")
            )
            .group_by(
                extract("year", Invoice.invoice_date),
                extract("month", Invoice.invoice_date)
            )
            .order_by(
                extract("year", Invoice.invoice_date),
                extract("month", Invoice.invoice_date)
            )
            .all()
        )
        
        return [
            {
                "year": int(r.year),
                "month": int(r.month),
                "revenue": r.revenue or Decimal("0"),
                "invoice_count": r.invoice_count or 0
            }
            for r in results
        ]


class PaymentRepository(BaseTenantRepository[Payment]):
    """Repository for payment operations."""
    
    def __init__(self, db: Session, tenant_id: str):
        super().__init__(db, Payment, tenant_id)
    
    def find_by_payment_number(self, payment_number: str) -> Optional[Payment]:
        """Find payment by payment number."""
        return (
            self._build_base_query()
            .filter(Payment.payment_number == payment_number)
            .first()
        )
    
    def find_by_transaction_id(self, transaction_id: str) -> Optional[Payment]:
        """Find payment by gateway transaction ID."""
        return (
            self._build_base_query()
            .filter(Payment.gateway_transaction_id == transaction_id)
            .first()
        )
    
    def get_customer_payments(self, customer_id: UUID) -> List[Payment]:
        """Get all payments for a customer."""
        return (
            self._build_base_query()
            .filter(Payment.customer_id == customer_id)
            .order_by(desc(Payment.payment_date))
            .all()
        )
    
    def get_invoice_payments(self, invoice_id: UUID) -> List[Payment]:
        """Get all payments for an invoice."""
        return (
            self._build_base_query()
            .filter(Payment.invoice_id == invoice_id)
            .order_by(Payment.payment_date)
            .all()
        )
    
    def get_failed_payments(self, days_back: int = 30) -> List[Payment]:
        """Get failed payments within specified days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        
        return (
            self._build_base_query()
            .filter(
                and_(
                    Payment.status == "failed",
                    Payment.created_at >= cutoff_date
                )
            )
            .options(joinedload(Payment.customer))
            .order_by(desc(Payment.created_at))
            .all()
        )
    
    def get_pending_settlements(self) -> List[Payment]:
        """Get payments pending settlement."""
        return (
            self._build_base_query()
            .filter(
                and_(
                    Payment.status == "completed",
                    Payment.settlement_date.is_(None)
                )
            )
            .all()
        )


class UsageRecordRepository(BaseTenantRepository[UsageRecord]):
    """Repository for usage record operations."""
    
    def __init__(self, db: Session, tenant_id: str):
        super().__init__(db, UsageRecord, tenant_id)
    
    def get_subscription_usage(
        self, 
        subscription_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[UsageRecord]:
        """Get usage records for a subscription."""
        query = (
            self._build_base_query()
            .filter(UsageRecord.subscription_id == subscription_id)
        )
        
        if start_date:
            query = query.filter(UsageRecord.usage_date >= start_date)
        if end_date:
            query = query.filter(UsageRecord.usage_date <= end_date)
            
        return query.order_by(UsageRecord.usage_date).all()
    
    def get_unprocessed_usage(self) -> List[UsageRecord]:
        """Get usage records that haven't been processed for billing."""
        return (
            self._build_base_query()
            .filter(UsageRecord.processed == False)
            .order_by(UsageRecord.usage_date)
            .all()
        )
    
    def get_usage_summary_by_subscription(
        self, 
        subscription_id: UUID,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Decimal]:
        """Get usage summary for a subscription in a period."""
        result = (
            self._build_base_query()
            .filter(
                and_(
                    UsageRecord.subscription_id == subscription_id,
                    UsageRecord.usage_date >= start_date,
                    UsageRecord.usage_date <= end_date
                )
            )
            .with_entities(
                func.sum(UsageRecord.quantity).label("total_quantity"),
                func.sum(UsageRecord.overage_quantity).label("total_overage"),
                func.avg(UsageRecord.uptime_percentage).label("avg_uptime"),
                func.count(UsageRecord.id).label("record_count")
            )
            .first()
        )
        
        return {
            "total_quantity": result.total_quantity or Decimal("0"),
            "total_overage": result.total_overage or Decimal("0"),
            "average_uptime": result.avg_uptime or Decimal("0"),
            "record_count": result.record_count or 0
        }


class CreditNoteRepository(BaseTenantRepository[CreditNote]):
    """Repository for credit note operations."""
    
    def __init__(self, db: Session, tenant_id: str):
        super().__init__(db, CreditNote, tenant_id)
    
    def find_by_credit_note_number(self, credit_note_number: str) -> Optional[CreditNote]:
        """Find credit note by number."""
        return (
            self._build_base_query()
            .filter(CreditNote.credit_note_number == credit_note_number)
            .first()
        )
    
    def get_customer_credits(self, customer_id: UUID) -> List[CreditNote]:
        """Get all credit notes for a customer."""
        return (
            self._build_base_query()
            .filter(CreditNote.customer_id == customer_id)
            .order_by(desc(CreditNote.created_at))
            .all()
        )
    
    def get_pending_credits(self) -> List[CreditNote]:
        """Get credit notes pending application."""
        return (
            self._build_base_query()
            .filter(CreditNote.status == "pending")
            .order_by(CreditNote.created_at)
            .all()
        )


class TaxRateRepository(BaseTenantRepository[TaxRate]):
    """Repository for tax rate operations."""
    
    def __init__(self, db: Session, tenant_id: str):
        super().__init__(db, TaxRate, tenant_id)
    
    def get_active_tax_rates(self) -> List[TaxRate]:
        """Get all active tax rates."""
        current_date = datetime.utcnow()
        return (
            self._build_base_query()
            .filter(
                and_(
                    TaxRate.is_active == True,
                    TaxRate.effective_date <= current_date,
                    or_(
                        TaxRate.expiry_date.is_(None),
                        TaxRate.expiry_date > current_date
                    )
                )
            )
            .all()
        )
    
    def get_tax_rates_for_location(
        self, 
        country_code: str,
        state_code: Optional[str] = None,
        zip_code: Optional[str] = None
    ) -> List[TaxRate]:
        """Get applicable tax rates for a location."""
        query = self.get_active_tax_rates()
        
        # Filter by location criteria
        applicable_rates = []
        for rate in query:
            if rate.country_code and rate.country_code != country_code:
                continue
            if rate.state_code and state_code and rate.state_code != state_code:
                continue
            if rate.zip_codes and zip_code and zip_code not in rate.zip_codes:
                continue
            applicable_rates.append(rate)
        
        return applicable_rates


# Export all repositories
__all__ = [
    "BillingCustomerRepository",
    "BillingPlanRepository", 
    "SubscriptionRepository",
    "InvoiceRepository",
    "PaymentRepository",
    "UsageRecordRepository",
    "CreditNoteRepository",
    "TaxRateRepository",
]