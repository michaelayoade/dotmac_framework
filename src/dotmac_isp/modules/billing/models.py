"""
Billing module data models.

Uses DRY patterns from dotmac_shared package to leverage existing billing infrastructure.
These models extend the shared billing models with ISP-specific functionality.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as SQLAuuid
from sqlalchemy.orm import relationship

from dotmac_business_logic.billing.core.models import BillingPlan as SharedBillingPlan
from dotmac_business_logic.billing.core.models import Customer as SharedCustomer
from dotmac_business_logic.billing.core.models import Invoice as SharedInvoice
from dotmac_business_logic.billing.core.models import (
    InvoiceLineItem as SharedInvoiceLineItem,
)
from dotmac_business_logic.billing.core.models import Payment as SharedPayment
from dotmac_business_logic.billing.core.models import Subscription as SharedSubscription
from dotmac_business_logic.billing.core.models import UsageRecord as SharedUsageRecord
from dotmac_isp.shared.database.base import BaseModel


class BillingCustomer(SharedCustomer, BaseModel):
    """
    ISP-specific billing customer model.

    Extends shared billing customer with ISP tenant isolation.
    """

    __tablename__ = "billing_customers"

    # ISP-specific fields
    isp_customer_id = Column(String(100), nullable=True, index=True)
    account_manager_id = Column(SQLAuuid(as_uuid=True), nullable=True)
    service_address = Column(Text, nullable=True)
    installation_date = Column(DateTime, nullable=True)
    connection_type = Column(String(50), nullable=True)  # fiber, cable, dsl, etc.
    bandwidth_package = Column(String(100), nullable=True)

    # Override relationship to use ISP-specific models
    subscriptions = relationship("Subscription", back_populates="customer", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="customer", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="customer", cascade="all, delete-orphan")


class BillingPlan(SharedBillingPlan, BaseModel):
    """
    ISP-specific billing plan model.

    Extends shared billing plan with ISP service configurations.
    """

    __tablename__ = "billing_plans"

    # ISP-specific fields
    service_type = Column(String(50), nullable=True)  # internet, phone, tv, bundle
    bandwidth_up = Column(Numeric(10, 2), nullable=True)  # Upload speed in Mbps
    bandwidth_down = Column(Numeric(10, 2), nullable=True)  # Download speed in Mbps
    data_allowance = Column(Numeric(12, 2), nullable=True)  # Data cap in GB
    installation_fee = Column(Numeric(10, 2), default=0)
    equipment_rental = Column(Numeric(10, 2), default=0)
    contract_length_months = Column(Integer, nullable=True)
    early_termination_fee = Column(Numeric(10, 2), default=0)

    # Service features
    static_ip_included = Column(Boolean, default=False)
    email_accounts_included = Column(Integer, default=0)
    tech_support_level = Column(String(20), default="basic")  # basic, premium, enterprise

    # Override relationship
    subscriptions = relationship("Subscription", back_populates="billing_plan")


class Subscription(SharedSubscription, BaseModel):
    """
    ISP customer subscription model.

    Extends shared subscription with ISP-specific service tracking.
    """

    __tablename__ = "billing_subscriptions"

    # ISP-specific fields
    service_address = Column(Text, nullable=True)
    installation_scheduled = Column(DateTime, nullable=True)
    activation_date = Column(DateTime, nullable=True)
    last_service_date = Column(DateTime, nullable=True)
    equipment_serial_numbers = Column(JSONB, default=dict)
    static_ip_addresses = Column(JSONB, default=list)
    port_assignments = Column(JSONB, default=dict)

    # Service quality tracking
    uptime_sla = Column(Numeric(5, 4), default=0.9999)  # 99.99%
    actual_uptime = Column(Numeric(5, 4), nullable=True)
    last_outage_date = Column(DateTime, nullable=True)
    support_incidents = Column(Integer, default=0)

    # Relationships
    customer_id = Column(SQLAuuid(as_uuid=True), ForeignKey("billing_customers.id"), nullable=False)
    billing_plan_id = Column(SQLAuuid(as_uuid=True), ForeignKey("billing_plans.id"), nullable=False)

    customer = relationship("BillingCustomer", back_populates="subscriptions")
    billing_plan = relationship("BillingPlan", back_populates="subscriptions")
    usage_records = relationship("UsageRecord", back_populates="subscription", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="subscription")


class Invoice(SharedInvoice, BaseModel):
    """
    ISP invoice model with service billing details.

    Extends shared invoice with ISP-specific billing cycles and service charges.
    """

    __tablename__ = "billing_invoices"

    # ISP-specific fields
    service_period_description = Column(String(200), nullable=True)
    late_fee_applied = Column(Numeric(10, 2), default=0)
    service_credits = Column(Numeric(10, 2), default=0)
    equipment_charges = Column(Numeric(10, 2), default=0)
    installation_charges = Column(Numeric(10, 2), default=0)
    overage_charges = Column(Numeric(10, 2), default=0)
    regulatory_fees = Column(Numeric(10, 2), default=0)

    # Billing cycle info
    billing_cycle_start = Column(DateTime, nullable=True)
    billing_cycle_end = Column(DateTime, nullable=True)
    meter_reading_date = Column(DateTime, nullable=True)

    # Payment tracking
    autopay_enabled = Column(Boolean, default=False)
    payment_failed_attempts = Column(Integer, default=0)
    collection_status = Column(String(20), default="current")  # current, past_due, collections

    # Relationships
    customer_id = Column(SQLAuuid(as_uuid=True), ForeignKey("billing_customers.id"), nullable=False)
    subscription_id = Column(SQLAuuid(as_uuid=True), ForeignKey("billing_subscriptions.id"), nullable=True)

    customer = relationship("BillingCustomer", back_populates="invoices")
    subscription = relationship("Subscription", back_populates="invoices")
    line_items = relationship("InvoiceLineItem", back_populates="invoice", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="invoice")


class InvoiceLineItem(SharedInvoiceLineItem, BaseModel):
    """
    ISP invoice line item with service-specific details.

    Extends shared line item with ISP service breakdown and usage details.
    """

    __tablename__ = "billing_invoice_line_items"

    # ISP-specific fields
    service_type = Column(String(50), nullable=True)  # monthly_service, usage, equipment, fees
    service_identifier = Column(String(100), nullable=True)  # account number, service ID
    usage_period_start = Column(DateTime, nullable=True)
    usage_period_end = Column(DateTime, nullable=True)
    usage_quantity = Column(Numeric(12, 4), nullable=True)
    usage_unit = Column(String(20), nullable=True)  # GB, minutes, calls
    rate_per_unit = Column(Numeric(10, 6), nullable=True)

    # Proration handling
    prorated = Column(Boolean, default=False)
    proration_days = Column(Integer, nullable=True)
    proration_factor = Column(Numeric(5, 4), nullable=True)

    # Relationship
    invoice_id = Column(SQLAuuid(as_uuid=True), ForeignKey("billing_invoices.id"), nullable=False)
    invoice = relationship("Invoice", back_populates="line_items")


class Payment(SharedPayment, BaseModel):
    """
    ISP payment model with processing details.

    Extends shared payment with ISP-specific payment processing and reconciliation.
    """

    __tablename__ = "billing_payments"

    # ISP-specific fields
    payment_processor = Column(String(50), nullable=True)  # stripe, square, ach, check
    bank_routing_number = Column(String(9), nullable=True)
    bank_account_last4 = Column(String(4), nullable=True)
    check_number = Column(String(20), nullable=True)
    batch_id = Column(String(50), nullable=True)
    reconciliation_date = Column(DateTime, nullable=True)

    # Processing details
    processing_fee = Column(Numeric(10, 4), default=0)
    net_amount = Column(Numeric(10, 2), nullable=True)  # Amount after fees
    settlement_date = Column(DateTime, nullable=True)
    refund_amount = Column(Numeric(10, 2), default=0)
    refund_date = Column(DateTime, nullable=True)

    # ACH/Bank transfer details
    ach_return_code = Column(String(10), nullable=True)
    ach_return_reason = Column(String(200), nullable=True)

    # Relationships
    customer_id = Column(SQLAuuid(as_uuid=True), ForeignKey("billing_customers.id"), nullable=False)
    invoice_id = Column(SQLAuuid(as_uuid=True), ForeignKey("billing_invoices.id"), nullable=True)

    customer = relationship("BillingCustomer", back_populates="payments")
    invoice = relationship("Invoice", back_populates="payments")


class UsageRecord(SharedUsageRecord, BaseModel):
    """
    ISP usage tracking model.

    Extends shared usage record with ISP-specific metering and bandwidth tracking.
    """

    __tablename__ = "billing_usage_records"

    # ISP-specific fields
    service_identifier = Column(String(100), nullable=True)
    meter_type = Column(String(30), nullable=True)  # bandwidth, data, time, calls
    peak_usage = Column(Numeric(15, 6), nullable=True)
    average_usage = Column(Numeric(15, 6), nullable=True)
    overage_threshold = Column(Numeric(15, 6), nullable=True)
    overage_quantity = Column(Numeric(15, 6), default=0)

    # Network performance
    uptime_percentage = Column(Numeric(5, 4), nullable=True)
    avg_latency_ms = Column(Numeric(8, 2), nullable=True)
    packet_loss_percentage = Column(Numeric(5, 4), nullable=True)

    # Data collection
    collection_method = Column(String(30), nullable=True)  # snmp, radius, manual
    raw_data = Column(JSONB, default=dict)
    quality_score = Column(Numeric(3, 2), nullable=True)  # Data quality 0-1

    # Relationship
    subscription_id = Column(SQLAuuid(as_uuid=True), ForeignKey("billing_subscriptions.id"), nullable=False)
    subscription = relationship("Subscription", back_populates="usage_records")


class CreditNote(BaseModel):
    """
    ISP credit note model for service adjustments and refunds.
    """

    __tablename__ = "billing_credit_notes"

    id = Column(SQLAuuid(as_uuid=True), primary_key=True, default=uuid4)
    credit_note_number = Column(String(50), nullable=False, unique=True, index=True)

    # Relationships
    customer_id = Column(SQLAuuid(as_uuid=True), ForeignKey("billing_customers.id"), nullable=False)
    invoice_id = Column(SQLAuuid(as_uuid=True), ForeignKey("billing_invoices.id"), nullable=True)

    # Credit details
    reason = Column(String(500), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    credit_type = Column(String(30), nullable=False)  # service_credit, refund, adjustment
    status = Column(String(20), nullable=False, default="pending")  # pending, applied, voided

    # Service-specific
    service_period_start = Column(DateTime, nullable=True)
    service_period_end = Column(DateTime, nullable=True)
    outage_duration_hours = Column(Numeric(8, 2), nullable=True)
    sla_breach = Column(Boolean, default=False)

    # Processing
    applied_date = Column(DateTime, nullable=True)
    applied_to_invoice_id = Column(SQLAuuid(as_uuid=True), nullable=True)
    authorization_code = Column(String(50), nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    custom_metadata = Column(JSONB, default=dict)


class TaxRate(BaseModel):
    """
    ISP tax rate configuration for different jurisdictions.
    """

    __tablename__ = "billing_tax_rates"

    id = Column(SQLAuuid(as_uuid=True), primary_key=True, default=uuid4)

    # Tax configuration
    name = Column(String(100), nullable=False)
    rate = Column(Numeric(8, 6), nullable=False)  # Tax rate as decimal
    tax_type = Column(String(30), nullable=False)  # sales, vat, gst, utility, regulatory
    jurisdiction = Column(String(100), nullable=False)  # state, county, city

    # Geographic scope
    country_code = Column(String(2), nullable=True)
    state_code = Column(String(10), nullable=True)
    zip_codes = Column(JSONB, default=list)  # List of applicable ZIP codes

    # Service applicability
    applies_to_services = Column(JSONB, default=list)  # Service types this tax applies to
    applies_to_equipment = Column(Boolean, default=True)
    applies_to_installation = Column(Boolean, default=True)

    # Date ranges
    effective_date = Column(DateTime, nullable=False)
    expiry_date = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Export all models for easy importing
__all__ = [
    "BillingCustomer",
    "BillingPlan",
    "Subscription",
    "Invoice",
    "InvoiceLineItem",
    "Payment",
    "UsageRecord",
    "CreditNote",
    "TaxRate",
]
