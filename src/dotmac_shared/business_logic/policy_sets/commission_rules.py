"""
Commission Rules Policies

Defines business rules for partner commission calculations, eligibility,
and compliance requirements using policy-as-code patterns.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any

from ..exceptions import CommissionPolicyError, ErrorContext
from ..policies import (
    BusinessPolicy,
    PolicyContext,
    PolicyEngine,
    PolicyRegistry,
    PolicyResult,
    PolicyRule,
    RuleOperator,
)


class CommissionRulesEngine:
    """High-level engine to validate commission scenarios using policies"""

    def __init__(self):
        self.registry = PolicyRegistry()
        self.policy_engine = PolicyEngine(self.registry)

        # Register default policies
        self.registry.register_policy(CommissionRulesPolicies.create_partner_eligibility_policy())
        self.registry.register_policy(CommissionRulesPolicies.create_commission_calculation_policy())
        self.registry.register_policy(CommissionRulesPolicies.create_tier_advancement_policy())

    def validate_partner_commission_eligibility(self, partner_data: dict[str, Any], context: PolicyContext) -> dict[str, Any]:
        policy_name = "partner_commission_eligibility"
        result = self.policy_engine.evaluate_policy(policy_name, context, {"partner": partner_data})
        result_dict = result.to_dict()
        return {
            "eligible": result.result == PolicyResult.ALLOW,
            "policy_result": result_dict,
            "partner_id": partner_data.get("id"),
            "violations": result_dict.get("violated_rules", []),
        }

    def validate_commission_calculation(self, commission: dict[str, Any], customer: dict[str, Any], service: dict[str, Any], context: PolicyContext) -> dict[str, Any]:
        policy_name = "commission_calculation_validation"
        result = self.policy_engine.evaluate_policy(
            policy_name,
            context,
            {"commission": commission, "customer": customer, "service": service},
        )
        return {
            "valid": result.result == PolicyResult.ALLOW,
            "policy_result": result.to_dict(),
        }

    def validate_tier_advancement(self, partner: dict[str, Any], tier: dict[str, Any], context: PolicyContext) -> dict[str, Any]:
        policy_name = "partner_tier_advancement"
        result = self.policy_engine.evaluate_policy(
            policy_name,
            context,
            {"partner": partner, "tier": tier},
        )
        return {
            "eligible": result.result in (PolicyResult.ALLOW, PolicyResult.REQUIRE_APPROVAL),
            "requires_approval": result.result == PolicyResult.REQUIRE_APPROVAL,
            "policy_result": result.to_dict(),
        }


class CommissionRulesPolicies:
    """Factory for creating commission-related business policies"""

    @staticmethod
    def create_partner_eligibility_policy() -> BusinessPolicy:
        """Create partner commission eligibility policy"""

        rules = [
            PolicyRule(
                name="partner_status_active",
                description="Partner must have active status",
                field_path="partner.status",
                operator=RuleOperator.EQUALS,
                expected_value="active",
                error_message="Partner must have active status to receive commissions",
            ),
            PolicyRule(
                name="agreement_signed",
                description="Partner agreement must be signed",
                field_path="partner.agreement_signed",
                operator=RuleOperator.EQUALS,
                expected_value=True,
                error_message="Signed partner agreement required for commission eligibility",
            ),
            PolicyRule(
                name="compliance_current",
                description="Partner must be compliant with requirements",
                field_path="partner.compliance_status",
                operator=RuleOperator.EQUALS,
                expected_value="compliant",
                error_message="Partner must maintain compliance status for commissions",
            ),
            PolicyRule(
                name="minimum_performance_threshold",
                description="Partner must meet minimum performance threshold",
                field_path="partner.performance_score",
                operator=RuleOperator.GREATER_THAN_OR_EQUAL,
                expected_value=70.0,
                error_message="Partner performance score must be at least 70% for commission eligibility",
            ),
            PolicyRule(
                name="no_payment_disputes",
                description="Partner cannot have active payment disputes",
                field_path="partner.active_disputes",
                operator=RuleOperator.EQUALS,
                expected_value=0,
                error_message="Active payment disputes must be resolved before commission payments",
            ),
            PolicyRule(
                name="tax_information_complete",
                description="Partner tax information must be complete",
                field_path="partner.tax_info_complete",
                operator=RuleOperator.EQUALS,
                expected_value=True,
                error_message="Complete tax information required for commission payments",
            ),
        ]

        return BusinessPolicy(
            name="partner_commission_eligibility",
            version="1.0.0",
            description="Eligibility rules for partner commission payments",
            category="commission_rules",
            default_result=PolicyResult.DENY,
            require_all_rules=True,
            rules=rules,
            effective_from=datetime.utcnow(),
            is_active=True,
            created_by="system",
            tags=["partner", "commission", "eligibility"],
        )

    @staticmethod
    def create_commission_calculation_policy() -> BusinessPolicy:
        """Create commission calculation validation policy"""

        rules = [
            PolicyRule(
                name="commission_rate_within_limits",
                description="Commission rate must be within allowed limits",
                field_path="commission.rate_percentage",
                operator=RuleOperator.BETWEEN,
                expected_value=[0.0, 50.0],  # 0% to 50%
                error_message="Commission rate must be between 0% and 50%",
            ),
            PolicyRule(
                name="minimum_payout_threshold",
                description="Commission amount must meet minimum payout threshold",
                field_path="commission.calculated_amount",
                operator=RuleOperator.GREATER_THAN_OR_EQUAL,
                expected_value=50.00,
                error_message="Commission amount must be at least $50.00 for payout",
            ),
            PolicyRule(
                name="maximum_single_commission",
                description="Single commission cannot exceed maximum limit",
                field_path="commission.calculated_amount",
                operator=RuleOperator.LESS_THAN_OR_EQUAL,
                expected_value=10000.00,
                error_message="Single commission amount cannot exceed $10,000",
            ),
            PolicyRule(
                name="customer_revenue_positive",
                description="Customer revenue must be positive",
                field_path="customer.monthly_revenue",
                operator=RuleOperator.GREATER_THAN,
                expected_value=0.00,
                error_message="Commission requires positive customer revenue",
            ),
            PolicyRule(
                name="service_active_duration",
                description="Service must be active for minimum period",
                field_path="service.active_days",
                operator=RuleOperator.GREATER_THAN_OR_EQUAL,
                expected_value=30,
                error_message="Service must be active for at least 30 days before commission eligibility",
            ),
            PolicyRule(
                name="no_customer_refund_pending",
                description="Customer cannot have pending refunds",
                field_path="customer.pending_refunds",
                operator=RuleOperator.EQUALS,
                expected_value=0.00,
                error_message="Commission held until pending customer refunds are resolved",
            ),
        ]

        return BusinessPolicy(
            name="commission_calculation_validation",
            version="1.0.0",
            description="Validation rules for commission calculations",
            category="commission_rules",
            default_result=PolicyResult.DENY,
            require_all_rules=True,
            rules=rules,
            effective_from=datetime.utcnow(),
            is_active=True,
            created_by="system",
            tags=["commission", "calculation", "validation"],
        )

    @staticmethod
    def create_tier_advancement_policy() -> BusinessPolicy:
        """Create partner tier advancement policy"""

        rules = [
            PolicyRule(
                name="minimum_revenue_threshold",
                description="Partner must meet revenue threshold for tier",
                field_path="partner.quarterly_revenue",
                operator=RuleOperator.GREATER_THAN_OR_EQUAL,
                expected_value="tier.min_quarterly_revenue",  # Dynamic based on target tier
                error_message="Quarterly revenue threshold not met for tier advancement",
            ),
            PolicyRule(
                name="customer_count_requirement",
                description="Partner must maintain minimum customer count",
                field_path="partner.active_customers",
                operator=RuleOperator.GREATER_THAN_OR_EQUAL,
                expected_value="tier.min_customers",
                error_message="Minimum customer count not met for tier advancement",
            ),
            PolicyRule(
                name="performance_score_requirement",
                description="Partner performance score must meet tier requirement",
                field_path="partner.performance_score",
                operator=RuleOperator.GREATER_THAN_OR_EQUAL,
                expected_value="tier.min_performance_score",
                error_message="Performance score requirement not met for tier advancement",
            ),
            PolicyRule(
                name="training_certifications_current",
                description="Required training certifications must be current",
                field_path="partner.certifications_current",
                operator=RuleOperator.EQUALS,
                expected_value=True,
                error_message="Current training certifications required for tier advancement",
            ),
            PolicyRule(
                name="no_recent_violations",
                description="No compliance violations in past 6 months",
                field_path="partner.violations_last_6_months",
                operator=RuleOperator.EQUALS,
                expected_value=0,
                error_message="No compliance violations allowed in past 6 months for tier advancement",
            ),
            PolicyRule(
                name="geographic_diversity_bonus",
                description="Bonus for geographic diversity in customer base",
                field_path="partner.geographic_diversity_score",
                operator=RuleOperator.GREATER_THAN_OR_EQUAL,
                expected_value=0.3,  # 30% diversity
                error_message="Geographic diversity in customer base improves tier eligibility",
                weight=0.5,  # Bonus rule, lower weight
            ),
        ]

        return BusinessPolicy(
            name="partner_tier_advancement",
            version="1.0.0",
            description="Rules for partner tier advancement and maintenance",
            category="commission_rules",
            default_result=PolicyResult.REQUIRE_APPROVAL,
            require_all_rules=False,
            rules=rules,
            effective_from=datetime.utcnow(),
            is_active=True,
            created_by="system",
            tags=["partner", "tier", "advancement"],
        )
