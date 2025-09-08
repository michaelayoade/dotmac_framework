"""
Plan Eligibility Policies

Defines business rules for service plan eligibility, licensing constraints,
and customer qualification requirements.
"""

from datetime import datetime
from typing import Any

from ..exceptions import ErrorContext, LicensingError, PlanEligibilityError
from ..policies import (
    BusinessPolicy,
    PolicyContext,
    PolicyEngine,
    PolicyRegistry,
    PolicyResult,
    PolicyRule,
    RuleOperator,
)


class PlanEligibilityEngine:
    """High-level engine to check plan eligibility using policies"""

    def __init__(self):
        self.registry = PolicyRegistry()
        self.policy_engine = PolicyEngine(self.registry)

        # Register default policies
        self.registry.register_policy(PlanEligibilityPolicies.create_residential_basic_eligibility())
        self.registry.register_policy(PlanEligibilityPolicies.create_business_pro_eligibility())
        self.registry.register_policy(PlanEligibilityPolicies.create_enterprise_eligibility())

    def check_plan_eligibility(self, plan_type: str, customer_data: dict[str, Any], context: PolicyContext) -> dict[str, Any]:
        policy_name_map = {
            "residential_basic": "residential_basic_eligibility",
            "business_pro": "business_pro_eligibility",
            "enterprise": "enterprise_eligibility",
        }

        policy_name = policy_name_map.get(plan_type)
        if not policy_name:
            return {"eligible": False, "error": f"Unknown plan type: {plan_type}"}

        result = self.policy_engine.evaluate_policy(policy_name, context, {"customer": customer_data, "plan": {}})
        return {
            "eligible": result.result == PolicyResult.ALLOW,
            "policy_result": result.to_dict(),
            "plan_type": plan_type,
        }


class PlanEligibilityPolicies:
    """Factory for creating plan eligibility business policies"""

    @staticmethod
    def create_residential_basic_eligibility() -> BusinessPolicy:
        """Create residential basic plan eligibility policy"""

        rules = [
            PolicyRule(
                name="customer_type_residential",
                description="Customer must be residential type",
                field_path="customer.customer_type",
                operator=RuleOperator.EQUALS,
                expected_value="residential",
                error_message="Basic plans are only available for residential customers",
            ),
            PolicyRule(
                name="credit_score_minimum",
                description="Minimum credit score requirement",
                field_path="customer.credit_score",
                operator=RuleOperator.GREATER_THAN_OR_EQUAL,
                expected_value=600,
                error_message="Credit score must be at least 600 for basic plans",
            ),
            PolicyRule(
                name="no_outstanding_debt",
                description="Customer cannot have outstanding debt",
                field_path="customer.outstanding_balance",
                operator=RuleOperator.LESS_THAN_OR_EQUAL,
                expected_value=0.00,
                error_message="Outstanding balance must be resolved before plan activation",
            ),
            PolicyRule(
                name="service_area_coverage",
                description="Customer location must be in service area",
                field_path="customer.location.service_coverage",
                operator=RuleOperator.EQUALS,
                expected_value=True,
                error_message="Service is not available in customer's location",
                weight=2.0,
            ),
        ]

        return BusinessPolicy(
            name="residential_basic_eligibility",
            version="1.0.0",
            description="Eligibility rules for residential basic internet plans",
            category="plan_eligibility",
            default_result=PolicyResult.DENY,
            require_all_rules=True,
            rules=rules,
            effective_from=datetime.utcnow(),
            is_active=True,
            created_by="system",
            tags=["residential", "basic", "internet"],
        )

    @staticmethod
    def create_business_pro_eligibility() -> BusinessPolicy:
        """Create business pro plan eligibility policy"""

        rules = [
            PolicyRule(
                name="customer_type_business",
                description="Customer must be business type",
                field_path="customer.customer_type",
                operator=RuleOperator.EQUALS,
                expected_value="business",
                error_message="Pro plans are only available for business customers",
            ),
            PolicyRule(
                name="business_registration_valid",
                description="Business registration must be valid",
                field_path="customer.business_details.registration_status",
                operator=RuleOperator.EQUALS,
                expected_value="active",
                error_message="Valid business registration is required",
            ),
            PolicyRule(
                name="minimum_contract_term",
                description="Minimum contract term acceptance",
                field_path="plan.contract_term_months",
                operator=RuleOperator.GREATER_THAN_OR_EQUAL,
                expected_value=12,
                error_message="Business pro plans require minimum 12-month commitment",
            ),
            PolicyRule(
                name="credit_limit_sufficient",
                description="Credit limit must be sufficient",
                field_path="customer.credit_limit",
                operator=RuleOperator.GREATER_THAN_OR_EQUAL,
                expected_value=1000.00,
                error_message="Minimum $1,000 credit limit required for business pro plans",
            ),
            PolicyRule(
                name="dedicated_support_required",
                description="Business customers require dedicated support",
                field_path="plan.support_tier",
                operator=RuleOperator.IN,
                expected_value=["premium", "enterprise"],
                error_message="Business pro plans require premium or enterprise support",
            ),
        ]

        return BusinessPolicy(
            name="business_pro_eligibility",
            version="1.0.0",
            description="Eligibility rules for business pro internet plans",
            category="plan_eligibility",
            default_result=PolicyResult.DENY,
            require_all_rules=True,
            rules=rules,
            effective_from=datetime.utcnow(),
            is_active=True,
            created_by="system",
            tags=["business", "pro", "internet"],
        )

    @staticmethod
    def create_enterprise_eligibility() -> BusinessPolicy:
        """Create enterprise plan eligibility policy"""

        rules = [
            PolicyRule(
                name="customer_type_enterprise",
                description="Customer must be enterprise type",
                field_path="customer.customer_type",
                operator=RuleOperator.EQUALS,
                expected_value="enterprise",
                error_message="Enterprise plans require enterprise customer classification",
            ),
            PolicyRule(
                name="minimum_employee_count",
                description="Minimum employee count requirement",
                field_path="customer.business_details.employee_count",
                operator=RuleOperator.GREATER_THAN_OR_EQUAL,
                expected_value=50,
                error_message="Enterprise plans require minimum 50 employees",
            ),
            PolicyRule(
                name="annual_revenue_minimum",
                description="Minimum annual revenue requirement",
                field_path="customer.business_details.annual_revenue",
                operator=RuleOperator.GREATER_THAN_OR_EQUAL,
                expected_value=1000000.00,
                error_message="Enterprise plans require minimum $1M annual revenue",
            ),
            PolicyRule(
                name="sla_agreement_required",
                description="SLA agreement must be signed",
                field_path="customer.agreements.sla_signed",
                operator=RuleOperator.EQUALS,
                expected_value=True,
                error_message="Service Level Agreement must be signed for enterprise plans",
            ),
            PolicyRule(
                name="dedicated_account_manager",
                description="Dedicated account manager assignment required",
                field_path="customer.account_manager_assigned",
                operator=RuleOperator.EQUALS,
                expected_value=True,
                error_message="Enterprise plans require dedicated account manager",
                weight=1.5,
            ),
            PolicyRule(
                name="multi_location_support",
                description="Multi-location deployment capability",
                field_path="customer.business_details.location_count",
                operator=RuleOperator.GREATER_THAN,
                expected_value=1,
                error_message="Enterprise plans are designed for multi-location businesses",
            ),
        ]

        return BusinessPolicy(
            name="enterprise_eligibility",
            version="1.0.0",
            description="Eligibility rules for enterprise-grade service plans",
            category="plan_eligibility",
            default_result=PolicyResult.REQUIRE_APPROVAL,  # Enterprise requires manual approval
            require_all_rules=True,
            rules=rules,
            effective_from=datetime.utcnow(),
            is_active=True,
            created_by="system",
            tags=["enterprise", "internet"],
        )
