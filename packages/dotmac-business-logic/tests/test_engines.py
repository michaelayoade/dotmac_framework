"""
Tests for business logic engines.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from dotmac_business_logic.engines import (
    BusinessProcessEngine,
    BusinessRulesEngine,
    PolicyEngine,
)
from dotmac_business_logic.engines.policy_engine import (
    Policy,
    PolicyAction,
    PolicyCondition,
    PolicyScope,
)
from dotmac_business_logic.engines.rules_engine import (
    BusinessRule,
    RuleCondition,
    RuleOperator,
    RuleSeverity,
)


class TestBusinessRulesEngine:
    """Test business rules engine."""

    def setup_method(self):
        """Setup test environment."""
        self.rules_engine = BusinessRulesEngine()

    def test_register_rule(self):
        """Test rule registration."""
        rule = BusinessRule(
            name="max_amount_rule",
            description="Maximum transaction amount",
            conditions=[
                RuleCondition(
                    field="amount",
                    operator=RuleOperator.LESS_EQUAL,
                    value=10000,
                    description="Amount must be <= 10000",
                )
            ],
            severity=RuleSeverity.ERROR,
        )

        self.rules_engine.register_rule(rule)

        assert "max_amount_rule" in self.rules_engine.rules
        assert self.rules_engine.rules["max_amount_rule"] == rule

    @pytest.mark.asyncio
    async def test_evaluate_rule_success(self):
        """Test successful rule evaluation."""
        rule = BusinessRule(
            name="valid_email_rule",
            description="Email must be provided",
            conditions=[
                RuleCondition(
                    field="customer.email",
                    operator=RuleOperator.CONTAINS,
                    value="@",
                    description="Email must contain @ symbol",
                )
            ],
        )

        self.rules_engine.register_rule(rule)

        context = {
            "customer": {
                "email": "test@example.com",
                "name": "Test User",
            }
        }

        result = await self.rules_engine.evaluate_rule(
            "valid_email_rule", context, "test-tenant"
        )

        assert result.valid is True
        assert len(result.violations) == 0
        assert result.evaluated_rules == 1

    @pytest.mark.asyncio
    async def test_evaluate_rule_failure(self):
        """Test rule evaluation failure."""
        rule = BusinessRule(
            name="min_age_rule",
            description="Customer must be at least 18",
            conditions=[
                RuleCondition(
                    field="customer.age",
                    operator=RuleOperator.GREATER_EQUAL,
                    value=18,
                    description="Age must be >= 18",
                )
            ],
            severity=RuleSeverity.ERROR,
        )

        self.rules_engine.register_rule(rule)

        context = {
            "customer": {
                "age": 16,
                "name": "Young User",
            }
        }

        result = await self.rules_engine.evaluate_rule(
            "min_age_rule", context, "test-tenant"
        )

        assert result.valid is False
        assert len(result.violations) == 1
        assert result.violations[0].rule_name == "min_age_rule"
        assert result.violations[0].actual_value == 16

    @pytest.mark.asyncio
    async def test_evaluate_rule_group(self):
        """Test evaluating a group of rules."""
        # Create rules with same group
        rule1 = BusinessRule(
            name="billing_amount_rule",
            description="Billing amount limit",
            conditions=[
                RuleCondition(
                    field="amount",
                    operator=RuleOperator.LESS_EQUAL,
                    value=5000,
                )
            ],
            rule_group="billing_rules",
        )

        rule2 = BusinessRule(
            name="billing_customer_rule",
            description="Customer must exist",
            conditions=[
                RuleCondition(
                    field="customer_id",
                    operator=RuleOperator.NOT_EQUALS,
                    value=None,
                )
            ],
            rule_group="billing_rules",
        )

        self.rules_engine.register_rule(rule1)
        self.rules_engine.register_rule(rule2)

        context = {
            "amount": 3000,
            "customer_id": "cust-123",
        }

        result = await self.rules_engine.evaluate_rule_group(
            "billing_rules", context, "test-tenant"
        )

        assert result.valid is True
        assert result.evaluated_rules == 2

    def test_get_rules_summary(self):
        """Test rules summary generation."""
        # Add some test rules
        rule1 = BusinessRule(
            name="rule1",
            description="Test rule 1",
            conditions=[],
            severity=RuleSeverity.ERROR,
            rule_group="group1",
        )

        rule2 = BusinessRule(
            name="rule2",
            description="Test rule 2",
            conditions=[],
            severity=RuleSeverity.WARNING,
            rule_group="group2",
            active=False,
        )

        self.rules_engine.register_rule(rule1)
        self.rules_engine.register_rule(rule2)

        summary = self.rules_engine.get_rules_summary()

        assert summary["total_rules"] == 2
        assert summary["active_rules"] == 1
        assert summary["inactive_rules"] == 1
        assert summary["rules_by_severity"]["error"] == 1
        assert summary["rules_by_severity"]["warning"] == 1


class TestPolicyEngine:
    """Test policy engine."""

    def setup_method(self):
        """Setup test environment."""
        self.policy_engine = PolicyEngine()

    def test_register_policy(self):
        """Test policy registration."""
        policy = Policy(
            name="max_transaction_policy",
            description="Maximum transaction amount policy",
            scope=PolicyScope.TENANT,
            action=PolicyAction.REQUIRE_APPROVAL,
            conditions=[
                PolicyCondition(
                    field="amount",
                    operator="greater_than",
                    value=50000,
                )
            ],
            requires_approval_from=["manager", "finance"],
        )

        self.policy_engine.register_policy(policy)

        assert "max_transaction_policy" in self.policy_engine.policies

    @pytest.mark.asyncio
    async def test_policy_allow(self):
        """Test policy allowing action."""
        policy = Policy(
            name="small_transaction_policy",
            description="Allow small transactions",
            scope=PolicyScope.GLOBAL,
            action=PolicyAction.ALLOW,
            conditions=[
                PolicyCondition(
                    field="amount",
                    operator="less_than",
                    value=1000,
                )
            ],
        )

        self.policy_engine.register_policy(policy)

        context = {"amount": 500}

        result = await self.policy_engine.evaluate_policy(
            "small_transaction_policy", context, "test-tenant"
        )

        assert result.allowed is True
        assert result.action == PolicyAction.ALLOW

    @pytest.mark.asyncio
    async def test_policy_require_approval(self):
        """Test policy requiring approval."""
        policy = Policy(
            name="large_transaction_policy",
            description="Large transactions need approval",
            scope=PolicyScope.GLOBAL,
            action=PolicyAction.REQUIRE_APPROVAL,
            conditions=[
                PolicyCondition(
                    field="amount",
                    operator="greater_than",
                    value=10000,
                )
            ],
            requires_approval_from=["manager"],
        )

        self.policy_engine.register_policy(policy)

        context = {"amount": 15000}

        result = await self.policy_engine.evaluate_policy(
            "large_transaction_policy", context, "test-tenant"
        )

        assert result.allowed is False
        assert result.action == PolicyAction.REQUIRE_APPROVAL
        assert result.requires_approval is True
        assert "manager" in result.approval_roles

    @pytest.mark.asyncio
    async def test_check_user_permissions(self):
        """Test user permission checking."""
        policy = Policy(
            name="admin_only_policy",
            description="Admin only actions",
            scope=PolicyScope.USER,
            action=PolicyAction.DENY,
            conditions=[
                PolicyCondition(
                    field="user_roles",
                    operator="not_contains",
                    value="admin",
                )
            ],
            metadata={"targets": ["admin_action"]},
        )

        self.policy_engine.register_policy(policy)

        context = {"user_roles": ["user", "customer"]}

        result = await self.policy_engine.check_user_permissions(
            "user-123", "admin_action", "system", context, "test-tenant"
        )

        # Should be allowed because the deny condition is met (not admin),
        # so it defaults to allow
        assert result.allowed is True

    def test_get_policies_summary(self):
        """Test policies summary generation."""
        policy1 = Policy(
            name="policy1",
            description="Test policy 1",
            scope=PolicyScope.GLOBAL,
            action=PolicyAction.ALLOW,
        )

        policy2 = Policy(
            name="policy2",
            description="Test policy 2",
            scope=PolicyScope.TENANT,
            action=PolicyAction.DENY,
            active=False,
        )

        self.policy_engine.register_policy(policy1)
        self.policy_engine.register_policy(policy2)

        summary = self.policy_engine.get_policies_summary()

        assert summary["total_policies"] == 2
        assert summary["active_policies"] == 1
        assert summary["inactive_policies"] == 1
        assert summary["policies_by_action"]["allow"] == 1
        assert summary["policies_by_action"]["deny"] == 1
        assert summary["policies_by_scope"]["global"] == 1
        assert summary["policies_by_scope"]["tenant"] == 1


class TestBusinessProcessEngine:
    """Test business process engine."""

    def setup_method(self):
        """Setup test environment."""
        self.engine = BusinessProcessEngine()

    @pytest.mark.asyncio
    async def test_register_workflow(self):
        """Test workflow registration."""

        class TestWorkflow:
            def __init__(self, workflow_id=None, tenant_id=None):
                self.workflow_id = workflow_id
                self.tenant_id = tenant_id

        self.engine.register_workflow("test_workflow", TestWorkflow)

        assert "test_workflow" in self.engine.workflows
        assert self.engine.workflows["test_workflow"] == TestWorkflow

    def test_register_process(self):
        """Test process definition registration."""
        process_def = {
            "name": "test_process",
            "steps": [
                {
                    "type": "rule_check",
                    "name": "validate_input",
                    "rule_name": "input_rule",
                },
                {
                    "type": "workflow",
                    "name": "execute_workflow",
                    "workflow_type": "test_workflow",
                },
                {
                    "type": "policy_check",
                    "name": "check_policy",
                    "policy_name": "approval_policy",
                },
            ],
        }

        self.engine.register_process("test_process", process_def)

        assert "test_process" in self.engine.process_definitions
        assert self.engine.process_definitions["test_process"] == process_def

    @pytest.mark.asyncio
    async def test_execute_process_rule_check(self):
        """Test process execution with rule check step."""
        # Mock the rules engine
        mock_rule_result = MagicMock()
        mock_rule_result.valid = True
        mock_rule_result.to_dict = lambda: {"valid": True}

        self.engine.rules_engine.evaluate_rule = AsyncMock(
            return_value=mock_rule_result
        )

        step = {
            "type": "rule_check",
            "name": "test_rule_step",
            "rule_name": "test_rule",
        }

        process_context = {
            "process_id": "test_process",
            "tenant_id": "test-tenant",
            "context": {"test": "data"},
        }

        result = await self.engine._execute_process_step(step, process_context, None)

        assert result["success"] is True
        assert result["step_name"] == "test_rule_step"
        assert result["step_type"] == "rule_check"

    @pytest.mark.asyncio
    async def test_execute_process_policy_check(self):
        """Test process execution with policy check step."""
        # Mock the policy engine
        mock_policy_result = MagicMock()
        mock_policy_result.allowed = True
        mock_policy_result.to_dict = lambda: {"allowed": True}

        self.engine.policy_engine.evaluate_policy = AsyncMock(
            return_value=mock_policy_result
        )

        step = {
            "type": "policy_check",
            "name": "test_policy_step",
            "policy_name": "test_policy",
        }

        process_context = {
            "process_id": "test_process",
            "tenant_id": "test-tenant",
            "context": {"test": "data"},
        }

        result = await self.engine._execute_process_step(step, process_context, None)

        assert result["success"] is True
        assert result["step_name"] == "test_policy_step"
        assert result["step_type"] == "policy_check"

    @pytest.mark.asyncio
    async def test_list_active_workflows(self):
        """Test listing active workflows."""
        # Create mock workflow
        mock_workflow = MagicMock()
        mock_workflow.workflow_id = "workflow-123"
        mock_workflow.tenant_id = "test-tenant"
        mock_workflow.workflow_type = "test_workflow"
        mock_workflow.to_dict = lambda: {
            "workflow_id": "workflow-123",
            "tenant_id": "test-tenant",
            "workflow_type": "test_workflow",
        }

        self.engine.active_workflows["workflow-123"] = mock_workflow

        # List all workflows
        workflows = await self.engine.list_active_workflows()
        assert len(workflows) == 1
        assert workflows[0]["workflow_id"] == "workflow-123"

        # List with tenant filter
        workflows = await self.engine.list_active_workflows(tenant_id="test-tenant")
        assert len(workflows) == 1

        workflows = await self.engine.list_active_workflows(tenant_id="other-tenant")
        assert len(workflows) == 0

        # List with workflow type filter
        workflows = await self.engine.list_active_workflows(
            workflow_type="test_workflow"
        )
        assert len(workflows) == 1

        workflows = await self.engine.list_active_workflows(
            workflow_type="other_workflow"
        )
        assert len(workflows) == 0
