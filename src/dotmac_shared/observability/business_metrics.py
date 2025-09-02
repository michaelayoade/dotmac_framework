"""
Business-specific metrics for DotMac Framework.
Provides domain-specific observability for partners, customers, and operations.
"""

import time
from typing import Optional, Dict, Any
from opentelemetry import trace

from .otel import get_meter
from .logging import get_logger

logger = get_logger("dotmac.business.metrics")


class DotMacBusinessMetrics:
    """
    Business metrics collector for DotMac operations.
    
    Provides high-level business metrics that complement technical metrics:
    - Partner performance and growth
    - Customer lifecycle events  
    - Commission calculations and payouts
    - Territory management
    - Revenue attribution
    """
    
    def __init__(self):
        self.meter = get_meter("dotmac-business")
        
        # Partner Metrics
        self.partner_signups = self.meter.create_counter(
            "dotmac.partners.signups.total",
            description="Total partner signups"
        )
        
        self.partner_activations = self.meter.create_counter(
            "dotmac.partners.activations.total", 
            description="Partner activations (first customer)"
        )
        
        self.partner_revenue_histogram = self.meter.create_histogram(
            "dotmac.partners.revenue.monthly",
            description="Monthly revenue per partner",
            unit="USD"
        )
        
        self.partner_customer_count = self.meter.create_histogram(
            "dotmac.partners.customers.count",
            description="Number of customers per partner"
        )
        
        # Customer Metrics
        self.customer_acquisitions = self.meter.create_counter(
            "dotmac.customers.acquisitions.total",
            description="Total customer acquisitions"
        )
        
        self.customer_churn = self.meter.create_counter(
            "dotmac.customers.churn.total",
            description="Customer churn events"
        )
        
        self.customer_lifetime_value = self.meter.create_histogram(
            "dotmac.customers.lifetime_value",
            description="Customer lifetime value",
            unit="USD"
        )
        
        self.customer_mrr = self.meter.create_histogram(
            "dotmac.customers.mrr",
            description="Monthly recurring revenue per customer",
            unit="USD"
        )
        
        # Commission Metrics
        self.commission_calculations = self.meter.create_counter(
            "dotmac.commissions.calculations.total",
            description="Commission calculations performed"
        )
        
        self.commission_payouts = self.meter.create_counter(
            "dotmac.commissions.payouts.total",
            description="Commission payouts processed"
        )
        
        self.commission_amounts = self.meter.create_histogram(
            "dotmac.commissions.amount",
            description="Commission amounts",
            unit="USD"
        )
        
        # Territory Metrics
        self.territory_assignments = self.meter.create_counter(
            "dotmac.territories.assignments.total",
            description="Territory assignments"
        )
        
        self.territory_coverage = self.meter.create_histogram(
            "dotmac.territories.coverage.percent",
            description="Territory coverage percentage",
            unit="percent"
        )
        
        # System Performance Business Impact
        self.sla_violations = self.meter.create_counter(
            "dotmac.sla.violations.total",
            description="SLA violations affecting business operations"
        )
        
        self.revenue_at_risk = self.meter.create_histogram(
            "dotmac.revenue.at_risk",
            description="Revenue at risk due to system issues",
            unit="USD"
        )

        # Additional Business Critical Metrics for Enhanced Monitoring
        self.partner_onboarding_attempts = self.meter.create_counter(
            "dotmac.partners.onboarding.attempts.total",
            description="Total partner onboarding attempts"
        )
        
        self.partner_onboarding_success = self.meter.create_counter(
            "dotmac.partners.onboarding.success.total",
            description="Successful partner onboarding completions"
        )
        
        self.revenue_processed = self.meter.create_counter(
            "dotmac.revenue.processed.total",
            description="Total revenue processed through platform",
            unit="USD"
        )
        
        self.support_tickets_created = self.meter.create_counter(
            "dotmac.support.tickets.total",
            description="Support tickets created by priority"
        )
        
        self.support_tickets_open = self.meter.create_gauge(
            "dotmac.support.tickets.open.total", 
            description="Currently open support tickets by priority"
        )
        
        self.payment_attempts = self.meter.create_counter(
            "dotmac.payments.total",
            description="Total payment processing attempts"
        )
        
        self.payment_failures = self.meter.create_counter(
            "dotmac.payments.failed.total",
            description="Failed payment processing attempts"
        )
        
        self.tenant_isolation_violations = self.meter.create_counter(
            "dotmac.tenant.isolation_violations.total",
            description="Tenant data isolation violations (CRITICAL SECURITY)"
        )

    def record_partner_signup(
        self, 
        partner_tier: str,
        territory: str,
        signup_source: str = "direct"
    ):
        """Record partner signup event."""
        labels = {
            "tier": partner_tier,
            "territory": territory,
            "source": signup_source
        }
        
        self.partner_signups.add(1, labels)
        
        # Add span event for trace correlation
        span = trace.get_current_span()
        if span.is_recording():
            span.add_event("partner_signup", {
                "partner.tier": partner_tier,
                "partner.territory": territory,
                "signup.source": signup_source
            })
        
        logger.info(
            "Partner signup recorded",
            tier=partner_tier,
            territory=territory,
            source=signup_source
        )

    def record_partner_activation(
        self,
        partner_id: str,
        days_to_activation: int,
        first_customer_mrr: float
    ):
        """Record partner activation (first customer)."""
        labels = {
            "partner_id": partner_id,
            "activation_speed": "fast" if days_to_activation <= 30 else "slow"
        }
        
        self.partner_activations.add(1, labels)
        
        span = trace.get_current_span()
        if span.is_recording():
            span.set_attribute("partner.id", partner_id)
            span.set_attribute("partner.days_to_activation", days_to_activation)
            span.set_attribute("partner.first_customer_mrr", first_customer_mrr)
        
        logger.info(
            "Partner activation recorded",
            partner_id=partner_id,
            days_to_activation=days_to_activation,
            first_customer_mrr=first_customer_mrr
        )

    def record_customer_acquisition(
        self,
        partner_id: str,
        customer_mrr: float,
        service_plan: str,
        acquisition_channel: str = "partner"
    ):
        """Record new customer acquisition."""
        labels = {
            "partner_id": partner_id,
            "service_plan": service_plan,
            "channel": acquisition_channel,
            "mrr_tier": self._get_mrr_tier(customer_mrr)
        }
        
        self.customer_acquisitions.add(1, labels)
        self.customer_mrr.record(customer_mrr, labels)
        
        span = trace.get_current_span()
        if span.is_recording():
            span.add_event("customer_acquisition", {
                "partner.id": partner_id,
                "customer.mrr": customer_mrr,
                "customer.service_plan": service_plan
            })
        
        logger.info(
            "Customer acquisition recorded",
            partner_id=partner_id,
            customer_mrr=customer_mrr,
            service_plan=service_plan
        )

    def record_customer_churn(
        self,
        partner_id: str,
        customer_mrr: float,
        churn_reason: str,
        customer_lifetime_months: int
    ):
        """Record customer churn event."""
        labels = {
            "partner_id": partner_id,
            "churn_reason": churn_reason,
            "mrr_tier": self._get_mrr_tier(customer_mrr),
            "lifetime_tier": self._get_lifetime_tier(customer_lifetime_months)
        }
        
        self.customer_churn.add(1, labels)
        
        # Calculate and record lifetime value
        lifetime_value = customer_mrr * customer_lifetime_months
        self.customer_lifetime_value.record(lifetime_value, labels)
        
        span = trace.get_current_span()
        if span.is_recording():
            span.add_event("customer_churn", {
                "partner.id": partner_id,
                "churn.reason": churn_reason,
                "customer.lifetime_value": lifetime_value
            })
        
        logger.warning(
            "Customer churn recorded",
            partner_id=partner_id,
            churn_reason=churn_reason,
            lifetime_value=lifetime_value
        )

    def record_commission_calculation(
        self,
        partner_id: str,
        commission_amount: float,
        base_amount: float,
        commission_rate: float,
        calculation_type: str = "monthly"
    ):
        """Record commission calculation."""
        labels = {
            "partner_id": partner_id,
            "calculation_type": calculation_type,
            "commission_tier": self._get_commission_tier(commission_amount)
        }
        
        self.commission_calculations.add(1, labels)
        self.commission_amounts.record(commission_amount, labels)
        
        span = trace.get_current_span()
        if span.is_recording():
            span.set_attribute("commission.partner_id", partner_id)
            span.set_attribute("commission.amount", commission_amount)
            span.set_attribute("commission.rate", commission_rate)
        
        logger.info(
            "Commission calculation recorded",
            partner_id=partner_id,
            commission_amount=commission_amount,
            base_amount=base_amount,
            rate=commission_rate
        )

    def record_commission_payout(
        self,
        partner_id: str,
        payout_amount: float,
        payout_method: str,
        processing_time_minutes: int
    ):
        """Record commission payout."""
        labels = {
            "partner_id": partner_id,
            "payout_method": payout_method,
            "processing_speed": "fast" if processing_time_minutes <= 60 else "slow"
        }
        
        self.commission_payouts.add(1, labels)
        
        span = trace.get_current_span()
        if span.is_recording():
            span.add_event("commission_payout", {
                "partner.id": partner_id,
                "payout.amount": payout_amount,
                "payout.method": payout_method
            })
        
        logger.info(
            "Commission payout recorded",
            partner_id=partner_id,
            payout_amount=payout_amount,
            payout_method=payout_method
        )

    def record_sla_violation(
        self,
        service_component: str,
        violation_type: str,
        affected_customers: int,
        revenue_impact: float,
        duration_minutes: int
    ):
        """Record SLA violation with business impact."""
        labels = {
            "component": service_component,
            "violation_type": violation_type,
            "severity": self._get_severity_by_impact(affected_customers, revenue_impact)
        }
        
        self.sla_violations.add(1, labels)
        self.revenue_at_risk.record(revenue_impact, labels)
        
        span = trace.get_current_span()
        if span.is_recording():
            span.add_event("sla_violation", {
                "sla.component": service_component,
                "sla.violation_type": violation_type,
                "sla.affected_customers": affected_customers,
                "sla.revenue_impact": revenue_impact
            })
        
        logger.error(
            "SLA violation recorded",
            component=service_component,
            violation_type=violation_type,
            affected_customers=affected_customers,
            revenue_impact=revenue_impact,
            duration_minutes=duration_minutes
        )

    def record_partner_performance_metrics(
        self,
        partner_id: str,
        monthly_revenue: float,
        customer_count: int,
        growth_rate: float
    ):
        """Record comprehensive partner performance metrics."""
        labels = {
            "partner_id": partner_id,
            "performance_tier": self._get_performance_tier(monthly_revenue, growth_rate)
        }
        
        self.partner_revenue_histogram.record(monthly_revenue, labels)
        self.partner_customer_count.record(customer_count, labels)
        
        span = trace.get_current_span()
        if span.is_recording():
            span.set_attribute("partner.id", partner_id)
            span.set_attribute("partner.monthly_revenue", monthly_revenue)
            span.set_attribute("partner.customer_count", customer_count)
            span.set_attribute("partner.growth_rate", growth_rate)

    def _get_mrr_tier(self, mrr: float) -> str:
        """Categorize MRR into tiers."""
        if mrr < 50:
            return "basic"
        elif mrr < 150:
            return "standard"
        elif mrr < 500:
            return "premium"
        else:
            return "enterprise"

    def _get_lifetime_tier(self, months: int) -> str:
        """Categorize customer lifetime into tiers."""
        if months < 6:
            return "short"
        elif months < 24:
            return "medium"
        else:
            return "long"

    def _get_commission_tier(self, amount: float) -> str:
        """Categorize commission amounts into tiers."""
        if amount < 100:
            return "low"
        elif amount < 500:
            return "medium"
        elif amount < 2000:
            return "high"
        else:
            return "premium"

    def _get_performance_tier(self, revenue: float, growth_rate: float) -> str:
        """Categorize partner performance."""
        if revenue > 10000 and growth_rate > 20:
            return "top_performer"
        elif revenue > 5000 and growth_rate > 10:
            return "high_performer"
        elif revenue > 1000:
            return "standard_performer"
        else:
            return "developing"

    def _get_severity_by_impact(self, customers: int, revenue: float) -> str:
        """Determine incident severity by business impact."""
        if customers > 100 or revenue > 10000:
            return "critical"
        elif customers > 50 or revenue > 5000:
            return "major"
        elif customers > 10 or revenue > 1000:
            return "minor"
        else:
            return "low"

    def record_partner_onboarding_attempt(
        self,
        partner_tier: str,
        referral_source: str = "direct"
    ):
        """Record partner onboarding attempt."""
        labels = {
            "tier": partner_tier,
            "referral_source": referral_source
        }
        
        self.partner_onboarding_attempts.add(1, labels)
        logger.info("Partner onboarding attempt", **labels)

    def record_partner_onboarding_success(
        self,
        partner_id: str,
        partner_tier: str,
        onboarding_duration_minutes: int
    ):
        """Record successful partner onboarding completion."""
        labels = {
            "partner_id": partner_id,
            "tier": partner_tier,
            "speed": "fast" if onboarding_duration_minutes <= 60 else "slow"
        }
        
        self.partner_onboarding_success.add(1, labels)
        logger.info("Partner onboarding success", **labels)

    def record_revenue_processed(
        self,
        amount_usd: float,
        revenue_type: str,
        partner_id: Optional[str] = None
    ):
        """Record revenue processing event."""
        labels = {
            "revenue_type": revenue_type,
            "amount_tier": self._get_revenue_tier(amount_usd)
        }
        if partner_id:
            labels["partner_id"] = partner_id
            
        self.revenue_processed.add(amount_usd, labels)
        logger.info("Revenue processed", amount=amount_usd, **labels)

    def record_support_ticket_created(
        self,
        priority: str,
        category: str,
        partner_id: Optional[str] = None
    ):
        """Record support ticket creation."""
        labels = {
            "priority": priority,
            "category": category
        }
        if partner_id:
            labels["partner_id"] = partner_id
            
        self.support_tickets_created.add(1, labels)
        self.support_tickets_open.add(1, labels)  # Also increment open counter
        logger.info("Support ticket created", **labels)

    def record_support_ticket_closed(
        self,
        priority: str,
        category: str,
        resolution_time_hours: float,
        partner_id: Optional[str] = None
    ):
        """Record support ticket closure."""
        labels = {
            "priority": priority,
            "category": category
        }
        if partner_id:
            labels["partner_id"] = partner_id
            
        self.support_tickets_open.add(-1, labels)  # Decrement open counter
        logger.info("Support ticket closed", 
                   resolution_time_hours=resolution_time_hours, **labels)

    def record_payment_attempt(
        self,
        amount_usd: float,
        payment_method: str,
        status: str,
        partner_id: Optional[str] = None
    ):
        """Record payment processing attempt."""
        labels = {
            "payment_method": payment_method,
            "status": status,
            "amount_tier": self._get_payment_tier(amount_usd)
        }
        if partner_id:
            labels["partner_id"] = partner_id
            
        self.payment_attempts.add(1, labels)
        
        if status == "failed":
            self.payment_failures.add(1, labels)
            logger.warning("Payment failed", amount=amount_usd, **labels)
        else:
            logger.info("Payment processed", amount=amount_usd, **labels)

    def record_tenant_isolation_violation(
        self,
        violation_type: str,
        tenant_id: str,
        severity: str = "critical"
    ):
        """Record tenant data isolation violation - CRITICAL SECURITY EVENT."""
        labels = {
            "violation_type": violation_type,
            "tenant_id": tenant_id,
            "severity": severity
        }
        
        self.tenant_isolation_violations.add(1, labels)
        
        # This is a critical security event - log with maximum priority
        logger.critical("SECURITY BREACH: Tenant isolation violation detected", 
                       **labels)
        
        # Also record as SLA violation with maximum impact
        self.record_sla_violation(
            service_component="tenant_isolation",
            violation_type="security_breach",
            affected_customers=1,  # Minimum affected
            revenue_impact=0,  # Not immediately measurable
            duration_minutes=0   # Instant violation
        )

    def _get_revenue_tier(self, amount: float) -> str:
        """Categorize revenue amounts into tiers."""
        if amount < 100:
            return "small"
        elif amount < 1000:
            return "medium"
        elif amount < 10000:
            return "large"
        else:
            return "enterprise"

    def _get_payment_tier(self, amount: float) -> str:
        """Categorize payment amounts into tiers."""
        if amount < 50:
            return "micro"
        elif amount < 200:
            return "small"
        elif amount < 1000:
            return "medium"
        else:
            return "large"


# Global business metrics instance
business_metrics = DotMacBusinessMetrics()

# Convenience functions for common operations
def record_partner_signup(partner_tier: str, territory: str, signup_source: str = "direct"):
    """Convenience function for partner signup."""
    return business_metrics.record_partner_signup(partner_tier, territory, signup_source)

def record_customer_acquisition(partner_id: str, customer_mrr: float, service_plan: str):
    """Convenience function for customer acquisition."""
    return business_metrics.record_customer_acquisition(partner_id, customer_mrr, service_plan)

def record_commission_calculation(partner_id: str, commission_amount: float, base_amount: float, rate: float):
    """Convenience function for commission calculation."""
    return business_metrics.record_commission_calculation(partner_id, commission_amount, base_amount, rate)