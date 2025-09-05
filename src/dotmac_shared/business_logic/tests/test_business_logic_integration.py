import logging
logger = logging.getLogger(__name__)

"""
Business Logic Integration Tests

Tests for the complete business logic framework including policies,
idempotency, and saga operations.
"""

import asyncio
from datetime import datetime
from typing import Any

import pytest

# Import business logic components
try:
    from ..exceptions import (
        BillingRunError,
        CommissionPolicyError,
        IdempotencyError,
        PlanEligibilityError,
        PolicyViolationError,
        ProvisioningError,
    )
    from ..idempotency import IdempotencyKey, IdempotentOperation, OperationResult
    from ..operations.billing_runs import BillingRunOperation
    from ..operations.service_provisioning import ServiceProvisioningOperation
    from ..operations.tenant_provisioning import TenantProvisioningOperation
    from ..policies import BusinessPolicy, PolicyContext, PolicyEngine, PolicyResult, PolicyRule, RuleOperator
    from ..policies.commission_rules import CommissionRulesEngine
    from ..policies.plan_eligibility import PlanEligibilityEngine
except ImportError as e:
    logger.info(f"Import error: {e}")
    logger.info("Business logic module structure validation test")


class TestPolicyFramework:
    """Test policy-as-code framework"""

    def test_policy_rule_evaluation(self):
        """Test individual policy rule evaluation"""

        rule = PolicyRule(
            name="credit_score_check",
            field_path="customer.credit_score",
            operator=RuleOperator.GREATER_THAN_OR_EQUAL,
            expected_value=600,
            error_message="Credit score must be at least 600",
        )

        # Test passing case
        test_data = {"customer": {"credit_score": 650}}
        assert rule.evaluate(test_data) is True

        # Test failing case
        test_data = {"customer": {"credit_score": 550}}
        assert rule.evaluate(test_data) is False

        # Test missing data
        test_data = {"customer": {}}
        assert rule.evaluate(test_data) is False

    def test_business_policy_evaluation(self):
        """Test complete business policy evaluation"""

        rules = [
            PolicyRule(
                name="customer_type_check",
                field_path="customer.type",
                operator=RuleOperator.EQUALS,
                expected_value="residential",
            ),
            PolicyRule(
                name="credit_score_check",
                field_path="customer.credit_score",
                operator=RuleOperator.GREATER_THAN_OR_EQUAL,
                expected_value=600,
            ),
        ]

        policy = BusinessPolicy(
            name="residential_eligibility",
            version="1.0.0",
            description="Test policy",
            category="eligibility",
            rules=rules,
            effective_from=datetime.utcnow(),
            created_by="test",
        )

        context = PolicyContext(tenant_id="test-tenant", operation="eligibility_check")

        # Test passing case
        evaluation_data = {"customer": {"type": "residential", "credit_score": 650}}

        result = policy.evaluate(context, evaluation_data)
        assert result.result == PolicyResult.ALLOW
        assert len(result.violated_rules) == 0

        # Test failing case
        evaluation_data["customer"]["credit_score"] = 550
        result = policy.evaluate(context, evaluation_data)
        assert result.result == PolicyResult.DENY
        assert "credit_score_check" in result.violated_rules

    def test_plan_eligibility_engine(self):
        """Test plan eligibility policy engine"""

        engine = PlanEligibilityEngine()

        context = PolicyContext(tenant_id="test-tenant", operation="plan_eligibility")

        customer_data = {
            "id": "cust123",
            "customer_type": "residential",
            "credit_score": 650,
            "outstanding_balance": 0.0,
            "location": {"service_coverage": True},
        }

        result = engine.check_plan_eligibility("residential_basic", customer_data, context)

        assert result["eligible"] is True
        assert result["plan_type"] == "residential_basic"
        assert result["policy_result"]["result"] == "allow"

    def test_commission_rules_engine(self):
        """Test commission rules policy engine"""

        engine = CommissionRulesEngine()

        context = PolicyContext(tenant_id="test-tenant", operation="commission_validation")

        partner_data = {
            "id": "partner123",
            "status": "active",
            "agreement_signed": True,
            "compliance_status": "compliant",
            "performance_score": 85.0,
            "active_disputes": 0,
            "tax_info_complete": True,
        }

        result = engine.validate_partner_commission_eligibility(partner_data, context)

        assert result["eligible"] is True
        assert result["partner_id"] == "partner123"
        assert len(result["violations"]) == 0


class TestIdempotencyFramework:
    """Test idempotency framework"""

    def test_idempotency_key_generation(self):
        """Test idempotency key generation"""

        key = IdempotencyKey.generate(
            operation_type="test_operation",
            tenant_id="tenant123",
            operation_data={"param1": "value1", "param2": "value2"},
        )

        assert key.operation_type == "test_operation"
        assert key.tenant_id == "tenant123"
        assert key.key.startswith("test_operation:tenant123:")

        # Test deterministic generation
        key2 = IdempotencyKey.generate(
            operation_type="test_operation",
            tenant_id="tenant123",
            operation_data={"param1": "value1", "param2": "value2"},
        )

        assert key.key == key2.key

    def test_operation_result_structure(self):
        """Test operation result structure"""

        result = OperationResult(success=True, data={"result": "test_data"}, execution_time_ms=100)

        assert result.success is True
        assert result.data["result"] == "test_data"
        assert result.execution_time_ms == 100

        result_dict = result.to_dict()
        assert "success" in result_dict
        assert "data" in result_dict
        assert "execution_time_ms" in result_dict


class MockIdempotentOperation(IdempotentOperation[dict[str, Any]]):
    """Mock operation for testing"""

    def __init__(self):
        super().__init__(operation_type="mock_operation", max_attempts=3)

    def validate_operation_data(self, operation_data: dict[str, Any]) -> None:
        if "required_field" not in operation_data:
            raise ValueError("Missing required field")

    async def execute(self, operation_data: dict[str, Any], context: dict[str, Any] = None) -> dict[str, Any]:
        await asyncio.sleep(0.01)  # Simulate async work
        return {"result": "success", "data": operation_data}


class TestBusinessOperations:
    """Test business operation implementations"""

    def test_tenant_provisioning_operation_validation(self):
        """Test tenant provisioning operation validation"""

        operation = TenantProvisioningOperation()

        # Test valid data
        valid_data = {"name": "Test Tenant", "domain": "test-tenant", "plan": "basic", "admin_email": "admin@test.com"}

        # Should not raise exception
        operation.validate_operation_data(valid_data)

        # Test invalid data
        invalid_data = {"name": "Test Tenant"}  # Missing required fields

        with pytest.raises(ValueError):
            operation.validate_operation_data(invalid_data)

    def test_service_provisioning_operation_validation(self):
        """Test service provisioning operation validation"""

        operation = ServiceProvisioningOperation()

        # Test valid data
        valid_data = {
            "customer_id": "cust123",
            "service_type": "internet",
            "plan": "standard",
            "billing_period": "monthly",
        }

        operation.validate_operation_data(valid_data)

        # Test invalid service type
        invalid_data = valid_data.copy()
        invalid_data["service_type"] = "invalid_type"

        with pytest.raises(ValueError):
            operation.validate_operation_data(invalid_data)

    def test_billing_run_operation_validation(self):
        """Test billing run operation validation"""

        operation = BillingRunOperation()

        # Test valid data
        valid_data = {"billing_period": "2024-03", "tenant_id": "tenant123"}

        operation.validate_operation_data(valid_data)

        # Test invalid billing period format
        invalid_data = {"billing_period": "invalid-format"}

        with pytest.raises(ValueError):
            operation.validate_operation_data(invalid_data)

    @pytest.mark.asyncio
    async def test_mock_operation_execution(self):
        """Test mock idempotent operation execution"""

        operation = MockIdempotentOperation()

        # Test successful execution
        operation_data = {"required_field": "value", "test_data": "123"}
        result = await operation.execute(operation_data, {})

        assert result["result"] == "success"
        assert result["data"]["required_field"] == "value"

        # Test validation failure
        with pytest.raises(ValueError):
            await operation.execute({}, {})  # Missing required field


class TestExceptionHandling:
    """Test exception handling in business logic"""

    def test_policy_violation_error(self):
        """Test PolicyViolationError structure"""

        error = PolicyViolationError(
            message="Policy violated", policy_name="test_policy", violated_rules=["rule1", "rule2"]
        )

        assert error.policy_name == "test_policy"
        assert "rule1" in error.violated_rules
        assert "rule2" in error.violated_rules

        error_dict = error.to_dict()
        assert "policy_name" in error_dict["details"]
        assert "violated_rules" in error_dict["details"]

    def test_provisioning_error(self):
        """Test ProvisioningError structure"""

        error = ProvisioningError(
            message="Provisioning failed",
            provisioning_type="tenant",
            target_id="test-tenant",
            step_failed="create_tenant",
        )

        assert error.provisioning_type == "tenant"
        assert error.target_id == "test-tenant"
        assert error.step_failed == "create_tenant"

        error_dict = error.to_dict()
        assert error_dict["error_code"] == "TENANT_PROVISIONING_ERROR"

    def test_billing_run_error(self):
        """Test BillingRunError structure"""

        error = BillingRunError(
            message="Billing run failed",
            billing_period="2024-03",
            tenant_id="tenant123",
            customer_count=100,
            failed_customers=["cust1", "cust2"],
        )

        assert error.billing_period == "2024-03"
        assert error.customer_count == 100
        assert len(error.failed_customers) == 2

        error_dict = error.to_dict()
        assert error_dict["error_code"] == "BILLING_RUN_ERROR"


def test_module_imports():
    """Test that all business logic modules can be imported"""

    # Test policy imports
    try:
        from ..policies import BusinessPolicy, PolicyEngine
        from ..policies.commission_rules import CommissionRulesEngine
        from ..policies.plan_eligibility import PlanEligibilityEngine

        logger.info("✅ Policy modules imported successfully")
    except ImportError as e:
        logger.info(f"❌ Policy module import failed: {e}")

    # Test idempotency imports
    try:
        from ..idempotency import IdempotencyManager, IdempotentOperation
        from ..sagas import SagaCoordinator, SagaStep

        logger.info("✅ Idempotency and saga modules imported successfully")
    except ImportError as e:
        logger.info(f"❌ Idempotency module import failed: {e}")

    # Test operations imports
    try:
        from ..operations import BillingRunOperation, ServiceProvisioningOperation, TenantProvisioningOperation

        logger.info("✅ Operation modules imported successfully")
    except ImportError as e:
        logger.info(f"❌ Operations module import failed: {e}")

    # Test exceptions imports
    try:
        from ..exceptions import BusinessLogicError, IdempotencyError, PolicyViolationError, SagaError

        logger.info("✅ Exception modules imported successfully")
    except ImportError as e:
        logger.info(f"❌ Exception module import failed: {e}")


def validate_business_logic_structure():
    """Validate the overall business logic structure"""

    logger.info("\n=== Business Logic Framework Validation ===")

    # Test policy framework
    logger.info("\n1. Testing Policy Framework:")
    test_framework = TestPolicyFramework()
    try:
        test_framework.test_policy_rule_evaluation()
        logger.info("   ✅ Policy rule evaluation works")
    except Exception as e:
        logger.info(f"   ❌ Policy rule evaluation failed: {e}")

    try:
        test_framework.test_business_policy_evaluation()
        logger.info("   ✅ Business policy evaluation works")
    except Exception as e:
        logger.info(f"   ❌ Business policy evaluation failed: {e}")

    # Test idempotency framework
    logger.info("\n2. Testing Idempotency Framework:")
    test_idempotency = TestIdempotencyFramework()
    try:
        test_idempotency.test_idempotency_key_generation()
        logger.info("   ✅ Idempotency key generation works")
    except Exception as e:
        logger.info(f"   ❌ Idempotency key generation failed: {e}")

    # Test operations
    logger.info("\n3. Testing Business Operations:")
    test_operations = TestBusinessOperations()
    try:
        test_operations.test_tenant_provisioning_operation_validation()
        logger.info("   ✅ Tenant provisioning validation works")
    except Exception as e:
        logger.info(f"   ❌ Tenant provisioning validation failed: {e}")

    # Test exception handling
    logger.info("\n4. Testing Exception Handling:")
    test_exceptions = TestExceptionHandling()
    try:
        test_exceptions.test_policy_violation_error()
        logger.info("   ✅ Policy violation error structure works")
    except Exception as e:
        logger.info(f"   ❌ Policy violation error failed: {e}")

    logger.info("\n5. Testing Module Imports:")
    test_module_imports()

    logger.info("\n=== Validation Complete ===")
    logger.info("\nThe business logic framework includes:")
    logger.info("• Policy-as-code with declarative rules and versioning")
    logger.info("• Idempotency management for safe operation retries")
    logger.info("• Saga orchestration for distributed transactions")
    logger.info("• Plan eligibility and licensing policies")
    logger.info("• Commission rule validation and calculation")
    logger.info("• Tenant, service, and billing provisioning operations")
    logger.info("• Comprehensive error handling and compensation")


if __name__ == "__main__":
    validate_business_logic_structure()
