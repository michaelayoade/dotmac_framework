"""
Commission Rules Policies

Defines business rules for partner commission calculations, eligibility,
and compliance requirements using policy-as-code patterns.
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional

from ..policies import (
    BusinessPolicy, PolicyRule, RuleOperator, PolicyResult,
    PolicyContext, PolicyEngine, PolicyRegistry
)
from ..exceptions import CommissionPolicyError, ErrorContext


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
                error_message="Partner must have active status to receive commissions"
            ),
            PolicyRule(
                name="agreement_signed",
                description="Partner agreement must be signed",
                field_path="partner.agreement_signed",
                operator=RuleOperator.EQUALS,
                expected_value=True,
                error_message="Signed partner agreement required for commission eligibility"
            ),
            PolicyRule(
                name="compliance_current",
                description="Partner must be compliant with requirements",
                field_path="partner.compliance_status",
                operator=RuleOperator.EQUALS,
                expected_value="compliant",
                error_message="Partner must maintain compliance status for commissions"
            ),
            PolicyRule(
                name="minimum_performance_threshold",
                description="Partner must meet minimum performance threshold",
                field_path="partner.performance_score",
                operator=RuleOperator.GREATER_THAN_OR_EQUAL,
                expected_value=70.0,
                error_message="Partner performance score must be at least 70% for commission eligibility"
            ),
            PolicyRule(
                name="no_payment_disputes",
                description="Partner cannot have active payment disputes",
                field_path="partner.active_disputes",
                operator=RuleOperator.EQUALS,
                expected_value=0,
                error_message="Active payment disputes must be resolved before commission payments"
            ),
            PolicyRule(
                name="tax_information_complete",
                description="Partner tax information must be complete",
                field_path="partner.tax_info_complete",
                operator=RuleOperator.EQUALS,
                expected_value=True,
                error_message="Complete tax information required for commission payments"
            )
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
            tags=["partner", "commission", "eligibility"]
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
                error_message="Commission rate must be between 0% and 50%"
            ),
            PolicyRule(
                name="minimum_payout_threshold",
                description="Commission amount must meet minimum payout threshold",
                field_path="commission.calculated_amount",
                operator=RuleOperator.GREATER_THAN_OR_EQUAL,
                expected_value=50.00,
                error_message="Commission amount must be at least $50.00 for payout"
            ),
            PolicyRule(
                name="maximum_single_commission",
                description="Single commission cannot exceed maximum limit",
                field_path="commission.calculated_amount",
                operator=RuleOperator.LESS_THAN_OR_EQUAL,
                expected_value=10000.00,
                error_message="Single commission amount cannot exceed $10,000"
            ),
            PolicyRule(
                name="customer_revenue_positive",
                description="Customer revenue must be positive",
                field_path="customer.monthly_revenue",
                operator=RuleOperator.GREATER_THAN,
                expected_value=0.00,
                error_message="Commission requires positive customer revenue"
            ),
            PolicyRule(
                name="service_active_duration",
                description="Service must be active for minimum period",
                field_path="service.active_days",
                operator=RuleOperator.GREATER_THAN_OR_EQUAL,
                expected_value=30,
                error_message="Service must be active for at least 30 days before commission eligibility"
            ),
            PolicyRule(
                name="no_customer_refund_pending",
                description="Customer cannot have pending refunds",
                field_path="customer.pending_refunds",
                operator=RuleOperator.EQUALS,
                expected_value=0.00,
                error_message="Commission held until pending customer refunds are resolved"
            )
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
            tags=["commission", "calculation", "validation"]
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
                error_message="Quarterly revenue threshold not met for tier advancement"
            ),
            PolicyRule(
                name="customer_count_requirement",
                description="Partner must maintain minimum customer count",
                field_path="partner.active_customers",
                operator=RuleOperator.GREATER_THAN_OR_EQUAL,
                expected_value="tier.min_customers",
                error_message="Minimum customer count not met for tier advancement"
            ),
            PolicyRule(
                name="performance_score_requirement",
                description="Partner performance score must meet tier requirement",
                field_path="partner.performance_score",
                operator=RuleOperator.GREATER_THAN_OR_EQUAL,
                expected_value="tier.min_performance_score",
                error_message="Performance score requirement not met for tier advancement"
            ),
            PolicyRule(
                name="training_certifications_current",
                description="Required training certifications must be current",
                field_path="partner.certifications_current",
                operator=RuleOperator.EQUALS,
                expected_value=True,
                error_message="Current training certifications required for tier advancement"
            ),
            PolicyRule(
                name="no_recent_violations",
                description="No compliance violations in past 6 months",
                field_path="partner.violations_last_6_months",
                operator=RuleOperator.EQUALS,
                expected_value=0,
                error_message="No compliance violations allowed in past 6 months for tier advancement"
            ),
            PolicyRule(
                name="geographic_diversity_bonus",
                description="Bonus for geographic diversity in customer base",
                field_path="partner.geographic_diversity_score",
                operator=RuleOperator.GREATER_THAN_OR_EQUAL,
                expected_value=0.3,  # 30% diversity
                error_message="Geographic diversity in customer base improves tier eligibility",
                weight=0.5  # Bonus rule, lower weight
            )
        ]
        
        return BusinessPolicy(
            name="partner_tier_advancement",
            version="1.0.0",
            description="Rules for partner tier advancement and maintenance",
            category="commission_rules",
            default_result=PolicyResult.REQUIRE_APPROVAL,
            require_all_rules=False,  # Most rules required, but some are bonuses
            rules=rules,
            effective_from=datetime.utcnow(),
            is_active=True,
            created_by="system",
            tags=["partner", "tier", "advancement"]
        )
    
    @staticmethod
    def create_commission_clawback_policy() -> BusinessPolicy:
        """Create commission clawback policy"""
        
        rules = [
            PolicyRule(
                name="customer_cancellation_within_grace",
                description="Customer cancelled within clawback grace period",
                field_path="customer.cancellation_within_days",
                operator=RuleOperator.LESS_THAN_OR_EQUAL,
                expected_value=90,
                error_message="Commission subject to clawback for cancellations within 90 days"
            ),
            PolicyRule(
                name="service_quality_issues",
                description="Service quality issues triggering clawback",
                field_path="service.quality_score",
                operator=RuleOperator.LESS_THAN,
                expected_value=60.0,
                error_message="Commission clawback triggered by service quality issues"
            ),
            PolicyRule(
                name="customer_chargeback_received",
                description="Customer initiated chargeback",
                field_path="customer.chargeback_amount",
                operator=RuleOperator.GREATER_THAN,
                expected_value=0.00,
                error_message="Commission clawback required for customer chargebacks"
            ),
            PolicyRule(
                name="fraudulent_signup_detected",
                description="Fraudulent customer signup detected",
                field_path="customer.fraud_score",
                operator=RuleOperator.GREATER_THAN,
                expected_value=75.0,
                error_message="Commission clawback required for fraudulent signups"
            ),
            PolicyRule(
                name="partner_policy_violation",
                description="Partner violated terms and conditions",
                field_path="partner.policy_violations",
                operator=RuleOperator.GREATER_THAN,
                expected_value=0,
                error_message="Commission clawback triggered by partner policy violations"
            )
        ]
        
        return BusinessPolicy(
            name="commission_clawback_rules",
            version="1.0.0",
            description="Rules determining when commissions should be clawed back",
            category="commission_rules",
            default_result=PolicyResult.DENY,  # Default to no clawback
            require_all_rules=False,  # Any rule can trigger clawback
            rules=rules,
            effective_from=datetime.utcnow(),
            is_active=True,
            created_by="system",
            tags=["commission", "clawback", "compliance"]
        )
    
    @staticmethod
    def create_bonus_commission_policy() -> BusinessPolicy:
        """Create bonus commission eligibility policy"""
        
        rules = [
            PolicyRule(
                name="exceeds_quarterly_target",
                description="Partner exceeded quarterly sales target",
                field_path="partner.quarterly_performance_vs_target",
                operator=RuleOperator.GREATER_THAN,
                expected_value=1.1,  # 110% of target
                error_message="Quarterly performance must exceed 110% of target for bonus"
            ),
            PolicyRule(
                name="customer_satisfaction_high",
                description="High customer satisfaction scores",
                field_path="partner.average_customer_satisfaction",
                operator=RuleOperator.GREATER_THAN_OR_EQUAL,
                expected_value=4.5,  # Out of 5
                error_message="Customer satisfaction must be 4.5+ for bonus eligibility"
            ),
            PolicyRule(
                name="new_customer_acquisition",
                description="Strong new customer acquisition",
                field_path="partner.new_customers_this_quarter",
                operator=RuleOperator.GREATER_THAN_OR_EQUAL,
                expected_value=10,
                error_message="Minimum 10 new customers required for bonus commission"
            ),
            PolicyRule(
                name="high_value_customers",
                description="Acquired high-value customers",
                field_path="partner.high_value_customer_percentage",
                operator=RuleOperator.GREATER_THAN_OR_EQUAL,
                expected_value=0.25,  # 25%
                error_message="At least 25% of customers must be high-value for bonus",
                weight=1.5
            ),
            PolicyRule(
                name="territory_expansion",
                description="Successfully expanded into new territories",
                field_path="partner.new_territories_this_quarter",
                operator=RuleOperator.GREATER_THAN,
                expected_value=0,
                error_message="Territory expansion qualifies for bonus commission",
                weight=0.8
            ),
            PolicyRule(
                name="referral_program_participation",
                description="Active participation in referral programs",
                field_path="partner.referral_commissions_earned",
                operator=RuleOperator.GREATER_THAN,
                expected_value=0.00,
                error_message="Referral program participation earns bonus eligibility",
                weight=0.6
            )
        ]
        
        return BusinessPolicy(
            name="bonus_commission_eligibility",
            version="1.0.0",
            description="Rules for bonus commission eligibility and calculation",
            category="commission_rules",
            default_result=PolicyResult.DENY,
            require_all_rules=False,  # Weighted scoring system
            rules=rules,
            effective_from=datetime.utcnow(),
            is_active=True,
            created_by="system",
            tags=["commission", "bonus", "performance"]
        )


class CommissionRulesEngine:
    """Specialized engine for commission rule evaluation"""
    
    def __init__(self):
        self.registry = PolicyRegistry()
        self.engine = PolicyEngine(self.registry)
        self._register_default_policies()
    
    def _register_default_policies(self):
        """Register default commission policies"""
        self.registry.register_policy(
            CommissionRulesPolicies.create_partner_eligibility_policy()
        )
        self.registry.register_policy(
            CommissionRulesPolicies.create_commission_calculation_policy()
        )
        self.registry.register_policy(
            CommissionRulesPolicies.create_tier_advancement_policy()
        )
        self.registry.register_policy(
            CommissionRulesPolicies.create_commission_clawback_policy()
        )
        self.registry.register_policy(
            CommissionRulesPolicies.create_bonus_commission_policy()
        )
    
    def validate_partner_commission_eligibility(
        self,
        partner_data: Dict[str, Any],
        context: PolicyContext
    ) -> Dict[str, Any]:
        """Validate partner eligibility for commission payments"""
        
        try:
            result = self.engine.evaluate_policy(
                policy_name="partner_commission_eligibility",
                context=context,
                evaluation_data={"partner": partner_data}
            )
            
            return {
                "eligible": result.result == PolicyResult.ALLOW,
                "violations": result.violated_rules,
                "policy_result": result.to_dict(),
                "partner_id": partner_data.get("id", "unknown")
            }
            
        except Exception as e:
            raise CommissionPolicyError(
                message=f"Partner commission eligibility check failed: {str(e)}",
                commission_config_id="eligibility_check",
                partner_id=partner_data.get("id", "unknown"),
                violated_constraints=[str(e)],
                context=ErrorContext(
                    operation="commission_eligibility_check",
                    resource_type="partner",
                    resource_id=partner_data.get("id", "unknown"),
                    tenant_id=context.tenant_id,
                    user_id=context.user_id,
                    correlation_id=context.correlation_id
                )
            )
    
    def validate_commission_calculation(
        self,
        commission_data: Dict[str, Any],
        customer_data: Dict[str, Any],
        service_data: Dict[str, Any],
        context: PolicyContext
    ) -> Dict[str, Any]:
        """Validate commission calculation against business rules"""
        
        evaluation_data = {
            "commission": commission_data,
            "customer": customer_data,
            "service": service_data
        }
        
        try:
            result = self.engine.evaluate_policy(
                policy_name="commission_calculation_validation",
                context=context,
                evaluation_data=evaluation_data
            )
            
            return {
                "valid": result.result == PolicyResult.ALLOW,
                "violations": result.violated_rules,
                "policy_result": result.to_dict(),
                "commission_amount": commission_data.get("calculated_amount", 0.0)
            }
            
        except Exception as e:
            raise CommissionPolicyError(
                message=f"Commission calculation validation failed: {str(e)}",
                commission_config_id=commission_data.get("config_id", "unknown"),
                partner_id=commission_data.get("partner_id", "unknown"),
                violated_constraints=[str(e)],
                context=ErrorContext(
                    operation="commission_calculation_validation",
                    resource_type="commission",
                    resource_id=commission_data.get("id", "unknown"),
                    tenant_id=context.tenant_id,
                    user_id=context.user_id,
                    correlation_id=context.correlation_id
                )
            )
    
    def check_tier_advancement_eligibility(
        self,
        partner_data: Dict[str, Any],
        target_tier_data: Dict[str, Any],
        context: PolicyContext
    ) -> Dict[str, Any]:
        """Check if partner is eligible for tier advancement"""
        
        evaluation_data = {
            "partner": partner_data,
            "tier": target_tier_data
        }
        
        try:
            result = self.engine.evaluate_policy(
                policy_name="partner_tier_advancement",
                context=context,
                evaluation_data=evaluation_data
            )
            
            return {
                "eligible": result.result in [PolicyResult.ALLOW, PolicyResult.REQUIRE_APPROVAL],
                "requires_approval": result.result == PolicyResult.REQUIRE_APPROVAL,
                "success_rate": result.success_rate,
                "failed_requirements": result.violated_rules,
                "policy_result": result.to_dict(),
                "target_tier": target_tier_data.get("name", "unknown")
            }
            
        except Exception as e:
            raise CommissionPolicyError(
                message=f"Tier advancement eligibility check failed: {str(e)}",
                commission_config_id=target_tier_data.get("id", "unknown"),
                partner_id=partner_data.get("id", "unknown"),
                violated_constraints=[str(e)],
                context=ErrorContext(
                    operation="tier_advancement_check",
                    resource_type="partner_tier",
                    resource_id=target_tier_data.get("name", "unknown"),
                    tenant_id=context.tenant_id,
                    user_id=context.user_id,
                    correlation_id=context.correlation_id
                )
            )
    
    def evaluate_clawback_conditions(
        self,
        commission_data: Dict[str, Any],
        customer_data: Dict[str, Any],
        service_data: Dict[str, Any],
        partner_data: Dict[str, Any],
        context: PolicyContext
    ) -> Dict[str, Any]:
        """Evaluate conditions that would trigger commission clawback"""
        
        evaluation_data = {
            "commission": commission_data,
            "customer": customer_data,
            "service": service_data,
            "partner": partner_data
        }
        
        try:
            result = self.engine.evaluate_policy(
                policy_name="commission_clawback_rules",
                context=context,
                evaluation_data=evaluation_data
            )
            
            # For clawback, we interpret results differently
            # ALLOW = no clawback needed, DENY = clawback required
            clawback_required = result.result != PolicyResult.ALLOW or len(result.violated_rules) > 0
            
            return {
                "clawback_required": clawback_required,
                "clawback_triggers": result.violated_rules if clawback_required else [],
                "policy_result": result.to_dict(),
                "commission_amount": commission_data.get("amount", 0.0),
                "clawback_amount": commission_data.get("amount", 0.0) if clawback_required else 0.0
            }
            
        except Exception as e:
            raise CommissionPolicyError(
                message=f"Clawback evaluation failed: {str(e)}",
                commission_config_id=commission_data.get("config_id", "unknown"),
                partner_id=partner_data.get("id", "unknown"),
                violated_constraints=[str(e)],
                context=ErrorContext(
                    operation="commission_clawback_evaluation",
                    resource_type="commission",
                    resource_id=commission_data.get("id", "unknown"),
                    tenant_id=context.tenant_id,
                    user_id=context.user_id,
                    correlation_id=context.correlation_id
                )
            )
    
    def calculate_bonus_commission(
        self,
        partner_data: Dict[str, Any],
        base_commission: Decimal,
        context: PolicyContext
    ) -> Dict[str, Any]:
        """Calculate bonus commission based on performance metrics"""
        
        try:
            result = self.engine.evaluate_policy(
                policy_name="bonus_commission_eligibility",
                context=context,
                evaluation_data={"partner": partner_data}
            )
            
            # Calculate bonus based on success rate and performance
            bonus_multiplier = result.success_rate  # 0.0 to 1.0
            max_bonus_percentage = 0.25  # Maximum 25% bonus
            
            bonus_percentage = bonus_multiplier * max_bonus_percentage
            bonus_amount = base_commission * Decimal(str(bonus_percentage))
            
            return {
                "eligible_for_bonus": result.success_rate > 0.7,  # 70% threshold
                "bonus_percentage": bonus_percentage,
                "bonus_amount": float(bonus_amount),
                "total_commission": float(base_commission + bonus_amount),
                "performance_metrics": {
                    "success_rate": result.success_rate,
                    "passed_rules": result.passed_rules,
                    "total_weight": result.total_weight,
                    "passed_weight": result.passed_weight
                },
                "policy_result": result.to_dict()
            }
            
        except Exception as e:
            # Return base commission if bonus calculation fails
            return {
                "eligible_for_bonus": False,
                "bonus_percentage": 0.0,
                "bonus_amount": 0.0,
                "total_commission": float(base_commission),
                "error": str(e),
                "policy_result": None
            }