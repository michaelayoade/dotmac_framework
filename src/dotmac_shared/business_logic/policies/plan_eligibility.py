"""
Plan Eligibility Policies

Defines business rules for service plan eligibility, licensing constraints,
and customer qualification requirements.
"""

from datetime import datetime
from typing import Any

from dotmac_shared.core.exceptions import ErrorContext

from ..exceptions import LicensingError, PlanEligibilityError
from ..policies import (
    BusinessPolicy,
    PolicyContext,
    PolicyEngine,
    PolicyRegistry,
    PolicyResult,
    PolicyRule,
    RuleOperator,
)


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
            tags=["enterprise", "sla", "multi-location"],
        )


class LicensingPolicies:
    """Factory for creating software licensing constraint policies"""

    @staticmethod
    def create_tenant_license_limits() -> BusinessPolicy:
        """Create tenant licensing limit policy"""

        rules = [
            PolicyRule(
                name="user_count_within_limit",
                description="User count must be within license limit",
                field_path="tenant.current_user_count",
                operator=RuleOperator.LESS_THAN_OR_EQUAL,
                expected_value="license.max_users",  # Dynamic reference
                error_message="User count exceeds license limit",
            ),
            PolicyRule(
                name="bandwidth_within_limit",
                description="Bandwidth usage within licensed capacity",
                field_path="tenant.current_bandwidth_usage",
                operator=RuleOperator.LESS_THAN_OR_EQUAL,
                expected_value="license.max_bandwidth_mbps",
                error_message="Bandwidth usage exceeds licensed capacity",
            ),
            PolicyRule(
                name="storage_within_limit",
                description="Storage usage within licensed capacity",
                field_path="tenant.current_storage_gb",
                operator=RuleOperator.LESS_THAN_OR_EQUAL,
                expected_value="license.max_storage_gb",
                error_message="Storage usage exceeds licensed capacity",
            ),
            PolicyRule(
                name="feature_access_allowed",
                description="Requested features are included in license",
                field_path="requested_features",
                operator=RuleOperator.CONTAINS,  # Custom logic needed
                expected_value="license.included_features",
                error_message="Requested features not included in current license",
            ),
            PolicyRule(
                name="license_not_expired",
                description="License must be active and not expired",
                field_path="license.expires_at",
                operator=RuleOperator.GREATER_THAN,
                expected_value="current_date",
                error_message="License has expired and must be renewed",
            ),
            PolicyRule(
                name="compliance_requirements_met",
                description="Compliance requirements must be satisfied",
                field_path="tenant.compliance_status",
                operator=RuleOperator.EQUALS,
                expected_value="compliant",
                error_message="Compliance requirements must be met for continued service",
            ),
        ]

        return BusinessPolicy(
            name="tenant_license_limits",
            version="1.0.0",
            description="Software licensing limits and compliance rules",
            category="licensing",
            default_result=PolicyResult.DENY,
            require_all_rules=True,
            rules=rules,
            effective_from=datetime.utcnow(),
            is_active=True,
            created_by="system",
            tags=["licensing", "limits", "compliance"],
        )

    @staticmethod
    def create_feature_access_policy() -> BusinessPolicy:
        """Create feature access licensing policy"""

        rules = [
            PolicyRule(
                name="basic_features_always_allowed",
                description="Basic features are always available",
                field_path="requested_feature",
                operator=RuleOperator.IN,
                expected_value=["dashboard", "basic_reports", "user_management"],
                error_message="Basic features should always be available",
            ),
            PolicyRule(
                name="premium_features_license_required",
                description="Premium features require appropriate license",
                field_path="license.tier",
                operator=RuleOperator.IN,
                expected_value=["premium", "enterprise"],
                error_message="Premium license required for advanced features",
                weight=2.0,
            ),
            PolicyRule(
                name="api_rate_limits_enforced",
                description="API usage within licensed rate limits",
                field_path="tenant.api_calls_per_hour",
                operator=RuleOperator.LESS_THAN_OR_EQUAL,
                expected_value="license.max_api_calls_per_hour",
                error_message="API rate limit exceeded for current license tier",
            ),
            PolicyRule(
                name="integration_count_within_limit",
                description="Third-party integrations within limit",
                field_path="tenant.active_integrations",
                operator=RuleOperator.LESS_THAN_OR_EQUAL,
                expected_value="license.max_integrations",
                error_message="Number of active integrations exceeds license limit",
            ),
        ]

        return BusinessPolicy(
            name="feature_access_licensing",
            version="1.0.0",
            description="Feature access control based on licensing tiers",
            category="licensing",
            default_result=PolicyResult.DENY,
            require_all_rules=False,  # OR logic - at least one rule must pass
            rules=rules,
            effective_from=datetime.utcnow(),
            is_active=True,
            created_by="system",
            tags=["features", "licensing", "access_control"],
        )


class PlanEligibilityEngine:
    """Specialized engine for plan eligibility evaluation"""

    def __init__(self):
        self.registry = PolicyRegistry()
        self.engine = PolicyEngine(self.registry)
        self._register_default_policies()

    def _register_default_policies(self):
        """Register default eligibility policies"""
        # Plan eligibility policies
        self.registry.register_policy(PlanEligibilityPolicies.create_residential_basic_eligibility())
        self.registry.register_policy(PlanEligibilityPolicies.create_business_pro_eligibility())
        self.registry.register_policy(PlanEligibilityPolicies.create_enterprise_eligibility())

        # Licensing policies
        self.registry.register_policy(LicensingPolicies.create_tenant_license_limits())
        self.registry.register_policy(LicensingPolicies.create_feature_access_policy())

    def check_plan_eligibility(
        self, plan_type: str, customer_data: dict[str, Any], context: PolicyContext
    ) -> dict[str, Any]:
        """Check if customer is eligible for specific plan"""

        # Map plan type to policy name
        policy_map = {
            "residential_basic": "residential_basic_eligibility",
            "business_pro": "business_pro_eligibility",
            "enterprise": "enterprise_eligibility",
        }

        policy_name = policy_map.get(plan_type)
        if not policy_name:
            raise ValueError(f"Unknown plan type: {plan_type}")

        try:
            result = self.engine.evaluate_policy(
                policy_name=policy_name, context=context, evaluation_data={"customer": customer_data}
            )

            return {
                "eligible": result.result == PolicyResult.ALLOW,
                "requires_approval": result.result == PolicyResult.REQUIRE_APPROVAL,
                "policy_result": result.to_dict(),
                "plan_type": plan_type,
            }

        except Exception as e:
            raise PlanEligibilityError(
                message=f"Plan eligibility check failed: {str(e)}",
                plan_name=plan_type,
                customer_id=customer_data.get("id", "unknown"),
                failed_requirements=[str(e)],
                context=ErrorContext(
                    operation="plan_eligibility_check",
                    resource_type="plan",
                    resource_id=plan_type,
                    tenant_id=context.tenant_id,
                    user_id=context.user_id,
                    correlation_id=context.correlation_id,
                ),
            ) from e

    def check_license_compliance(
        self, tenant_data: dict[str, Any], license_data: dict[str, Any], context: PolicyContext
    ) -> dict[str, Any]:
        """Check tenant licensing compliance"""

        evaluation_data = {
            "tenant": tenant_data,
            "license": license_data,
            "current_date": datetime.utcnow().isoformat(),
        }

        try:
            result = self.engine.evaluate_policy(
                policy_name="tenant_license_limits", context=context, evaluation_data=evaluation_data
            )

            return {
                "compliant": result.result == PolicyResult.ALLOW,
                "violations": result.violated_rules,
                "policy_result": result.to_dict(),
                "license_status": "active" if result.result == PolicyResult.ALLOW else "violation",
            }

        except Exception as e:
            raise LicensingError(
                message=f"License compliance check failed: {str(e)}",
                license_type=license_data.get("tier", "unknown"),
                tenant_id=context.tenant_id,
                usage_limit=license_data.get("max_users", 0),
                current_usage=tenant_data.get("current_user_count", 0),
                context=ErrorContext(
                    operation="license_compliance_check",
                    resource_type="license",
                    resource_id=license_data.get("id", "unknown"),
                    tenant_id=context.tenant_id,
                    user_id=context.user_id,
                    correlation_id=context.correlation_id,
                ),
            ) from e

    def check_feature_access(
        self,
        requested_features: list[str],
        license_data: dict[str, Any],
        tenant_data: dict[str, Any],
        context: PolicyContext,
    ) -> dict[str, Any]:
        """Check if tenant can access requested features"""

        evaluation_data = {"requested_features": requested_features, "license": license_data, "tenant": tenant_data}

        try:
            result = self.engine.evaluate_policy(
                policy_name="feature_access_licensing", context=context, evaluation_data=evaluation_data
            )

            # Determine which features are allowed
            allowed_features = []
            denied_features = []

            for feature in requested_features:
                # This would need more sophisticated logic in practice
                feature_evaluation_data = {**evaluation_data, "requested_feature": feature}

                try:
                    feature_result = self.engine.evaluate_policy(
                        policy_name="feature_access_licensing", context=context, evaluation_data=feature_evaluation_data
                    )

                    if feature_result.result == PolicyResult.ALLOW:
                        allowed_features.append(feature)
                    else:
                        denied_features.append(feature)

                except Exception:
                    denied_features.append(feature)

            return {
                "access_granted": result.result == PolicyResult.ALLOW,
                "allowed_features": allowed_features,
                "denied_features": denied_features,
                "policy_result": result.to_dict(),
            }

        except Exception as e:
            raise LicensingError(
                message=f"Feature access check failed: {str(e)}",
                license_type=license_data.get("tier", "unknown"),
                tenant_id=context.tenant_id,
                usage_limit=0,
                current_usage=len(requested_features),
                context=ErrorContext(
                    operation="feature_access_check",
                    resource_type="feature_access",
                    resource_id=",".join(requested_features),
                    tenant_id=context.tenant_id,
                    user_id=context.user_id,
                    correlation_id=context.correlation_id,
                ),
            ) from e
