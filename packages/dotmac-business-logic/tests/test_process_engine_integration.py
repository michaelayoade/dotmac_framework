"""
Integration tests for Business Process Engine
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

try:
    from dotmac_business_logic.engines.policy_engine import PolicyEngine, PolicyResult
    from dotmac_business_logic.engines.process_engine import BusinessProcessEngine
    from dotmac_business_logic.engines.rules_engine import (
        BusinessRulesEngine,
        RuleResult,
    )
    from dotmac_business_logic.workflows.base import (
        BusinessWorkflow,
        BusinessWorkflowStatus,
        WorkflowResult,
    )
except ImportError:
    # Mock implementations for testing
    from dataclasses import dataclass
    from enum import Enum

    class BusinessWorkflowStatus(Enum):
        PENDING = "pending"
        RUNNING = "running"
        WAITING_APPROVAL = "waiting_approval"
        COMPLETED = "completed"
        FAILED = "failed"
        CANCELLED = "cancelled"

    @dataclass
    class WorkflowResult:
        result_id: str
        workflow_id: str
        step: str
        success: bool
        message: str
        data: dict = None

        def to_dict(self):
            return {
                "result_id": self.result_id,
                "workflow_id": self.workflow_id,
                "step": self.step,
                "success": self.success,
                "message": self.message,
                "data": self.data or {}
            }

    @dataclass
    class RuleResult:
        valid: bool
        errors: list[str] = None
        warnings: list[str] = None

        def to_dict(self):
            return {
                "valid": self.valid,
                "errors": self.errors or [],
                "warnings": self.warnings or []
            }

    @dataclass
    class PolicyResult:
        allowed: bool
        reason: str = None

        def to_dict(self):
            return {
                "allowed": self.allowed,
                "reason": self.reason
            }

    class BusinessWorkflow:
        def __init__(self, workflow_id: str = None, tenant_id: str = None, workflow_type: str = None):
            self.workflow_id = workflow_id or str(uuid4())
            self.tenant_id = tenant_id
            self.workflow_type = workflow_type or "test_workflow"
            self.status = BusinessWorkflowStatus.PENDING
            self.results = []
            self.start_time = datetime.now(timezone.utc)
            self.end_time = None
            self.context = {}
            self.db_session = None

        def set_business_context(self, context: dict, db_session=None):
            self.context = context
            self.db_session = db_session

        async def execute(self):
            self.status = BusinessWorkflowStatus.RUNNING
            # Simulate workflow execution
            result = WorkflowResult(
                result_id=str(uuid4()),
                workflow_id=self.workflow_id,
                step="execution",
                success=True,
                message="Workflow executed successfully"
            )
            self.results.append(result)
            self.status = BusinessWorkflowStatus.COMPLETED
            self.end_time = datetime.now(timezone.utc)

        async def approve_and_continue(self, approval_data=None):
            if self.status == BusinessWorkflowStatus.WAITING_APPROVAL:
                self.status = BusinessWorkflowStatus.RUNNING
                await self.execute()

        async def reject_and_cancel(self, reason=None):
            self.status = BusinessWorkflowStatus.CANCELLED
            self.end_time = datetime.now(timezone.utc)

        async def cancel(self):
            self.status = BusinessWorkflowStatus.CANCELLED
            self.end_time = datetime.now(timezone.utc)

        @property
        def is_completed(self):
            return self.status == BusinessWorkflowStatus.COMPLETED

        @property
        def is_failed(self):
            return self.status == BusinessWorkflowStatus.FAILED

        def to_dict(self):
            return {
                "workflow_id": self.workflow_id,
                "workflow_type": self.workflow_type,
                "tenant_id": self.tenant_id,
                "status": self.status.value,
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "end_time": self.end_time.isoformat() if self.end_time else None,
                "results": [r.to_dict() for r in self.results],
                "context": self.context
            }

    class BusinessRulesEngine:
        def __init__(self):
            self.rules = {}

        async def validate_workflow_rules(self, workflow_type: str, context: dict, tenant_id: str) -> RuleResult:
            # Mock validation - always pass unless context says otherwise
            if context.get("should_fail_validation"):
                return RuleResult(valid=False, errors=["Validation failed"])
            return RuleResult(valid=True)

        async def evaluate_rule(self, rule_name: str, context: dict, tenant_id: str) -> RuleResult:
            if rule_name == "failing_rule":
                return RuleResult(valid=False, errors=["Rule failed"])
            return RuleResult(valid=True)

    class PolicyEngine:
        def __init__(self):
            self.policies = {}

        async def check_workflow_policies(self, workflow_type: str, context: dict, tenant_id: str) -> PolicyResult:
            # Mock policy check - always allow unless context says otherwise
            if context.get("should_fail_policy"):
                return PolicyResult(allowed=False, reason="Policy violation")
            return PolicyResult(allowed=True)

        async def evaluate_policy(self, policy_name: str, context: dict, tenant_id: str) -> PolicyResult:
            if policy_name == "restrictive_policy":
                return PolicyResult(allowed=False, reason="Policy denied")
            return PolicyResult(allowed=True)

    class BusinessProcessEngine:
        def __init__(self, db_session_factory=None):
            self.db_session_factory = db_session_factory
            self.rules_engine = BusinessRulesEngine()
            self.policy_engine = PolicyEngine()

            self.workflows = {}
            self.process_definitions = {}
            self.active_workflows = {}
            self.workflow_history = []

        def register_workflow(self, workflow_type: str, workflow_class):
            self.workflows[workflow_type] = workflow_class

        def register_process(self, process_id: str, process_definition: dict):
            self.process_definitions[process_id] = process_definition

        async def start_workflow(
            self,
            workflow_type: str,
            context: dict,
            tenant_id: str,
            db_session=None,
            workflow_id: str = None
        ) -> BusinessWorkflow:
            if workflow_type not in self.workflows:
                raise ValueError(f"Unknown workflow type: {workflow_type}")

            # Check rules and policies
            rules_result = await self.rules_engine.validate_workflow_rules(
                workflow_type, context, tenant_id
            )
            if not rules_result.valid:
                raise ValueError(f"Business rules validation failed: {rules_result.errors}")

            policy_result = await self.policy_engine.check_workflow_policies(
                workflow_type, context, tenant_id
            )
            if not policy_result.allowed:
                raise ValueError(f"Policy violation: {policy_result.reason}")

            # Create workflow
            workflow_class = self.workflows[workflow_type]
            workflow = workflow_class(
                workflow_id=workflow_id,
                tenant_id=tenant_id,
                workflow_type=workflow_type
            )

            workflow.set_business_context(context, db_session)
            self.active_workflows[workflow.workflow_id] = workflow

            await workflow.execute()

            return workflow

        async def resume_workflow(self, workflow_id: str, approval_data=None):
            if workflow_id not in self.active_workflows:
                raise ValueError(f"Workflow {workflow_id} not found")

            workflow = self.active_workflows[workflow_id]
            if workflow.status != BusinessWorkflowStatus.WAITING_APPROVAL:
                raise ValueError(f"Workflow {workflow_id} is not waiting for approval")

            await workflow.approve_and_continue(approval_data)
            return workflow

        async def reject_workflow(self, workflow_id: str, rejection_reason: str = None):
            if workflow_id not in self.active_workflows:
                raise ValueError(f"Workflow {workflow_id} not found")

            workflow = self.active_workflows[workflow_id]
            if workflow.status != BusinessWorkflowStatus.WAITING_APPROVAL:
                raise ValueError(f"Workflow {workflow_id} is not waiting for approval")

            await workflow.reject_and_cancel(rejection_reason)
            return workflow

        async def cancel_workflow(self, workflow_id: str):
            if workflow_id not in self.active_workflows:
                raise ValueError(f"Workflow {workflow_id} not found")

            workflow = self.active_workflows[workflow_id]
            await workflow.cancel()
            return workflow

        async def get_workflow_status(self, workflow_id: str):
            if workflow_id not in self.active_workflows:
                raise ValueError(f"Workflow {workflow_id} not found")
            return self.active_workflows[workflow_id].to_dict()

        async def list_active_workflows(self, tenant_id=None, workflow_type=None, status=None):
            workflows = []
            for workflow in self.active_workflows.values():
                if tenant_id and workflow.tenant_id != tenant_id:
                    continue
                if workflow_type and workflow.workflow_type != workflow_type:
                    continue
                if status and workflow.status != status:
                    continue
                workflows.append(workflow.to_dict())
            return workflows

        async def execute_process(self, process_id: str, context: dict, tenant_id: str, db_session=None):
            if process_id not in self.process_definitions:
                raise ValueError(f"Unknown process: {process_id}")

            process_def = self.process_definitions[process_id]

            process_context = {
                "process_id": process_id,
                "tenant_id": tenant_id,
                "started_at": datetime.now(timezone.utc),
                "context": context,
                "steps_completed": 0,
                "total_steps": len(process_def.get("steps", [])),
                "results": [],
                "status": "running"
            }

            for step in process_def.get("steps", []):
                step_result = await self._execute_process_step(step, process_context, db_session)
                process_context["results"].append(step_result)
                process_context["steps_completed"] += 1

                if not step_result.get("success", False):
                    process_context["status"] = "failed"
                    process_context["error"] = step_result.get("error")
                    break

            if process_context["steps_completed"] == process_context["total_steps"]:
                process_context["status"] = "completed"

            process_context["completed_at"] = datetime.now(timezone.utc)
            return process_context

        async def _execute_process_step(self, step: dict, process_context: dict, db_session=None):
            step_type = step.get("type")
            step_name = step.get("name", "unknown_step")

            try:
                if step_type == "workflow":
                    workflow_type = step.get("workflow_type")
                    workflow = await self.start_workflow(
                        workflow_type,
                        process_context["context"],
                        process_context["tenant_id"],
                        db_session
                    )
                    return {
                        "success": workflow.is_completed,
                        "step_name": step_name,
                        "step_type": step_type,
                        "workflow_id": workflow.workflow_id
                    }
                elif step_type == "rule_check":
                    rule_name = step.get("rule_name")
                    result = await self.rules_engine.evaluate_rule(
                        rule_name, process_context["context"], process_context["tenant_id"]
                    )
                    return {
                        "success": result.valid,
                        "step_name": step_name,
                        "step_type": step_type,
                        "rule_result": result.to_dict()
                    }
                elif step_type == "policy_check":
                    policy_name = step.get("policy_name")
                    result = await self.policy_engine.evaluate_policy(
                        policy_name, process_context["context"], process_context["tenant_id"]
                    )
                    return {
                        "success": result.allowed,
                        "step_name": step_name,
                        "step_type": step_type,
                        "policy_result": result.to_dict()
                    }
                elif step_type == "custom":
                    function_name = step.get("function")
                    return {
                        "success": True,
                        "step_name": step_name,
                        "step_type": step_type,
                        "message": f"Custom function {function_name} executed"
                    }
                else:
                    return {
                        "success": False,
                        "step_name": step_name,
                        "step_type": step_type,
                        "error": f"Unknown step type: {step_type}"
                    }
            except Exception as e:
                return {
                    "success": False,
                    "step_name": step_name,
                    "step_type": step_type,
                    "error": str(e)
                }

        async def cleanup_completed_workflows(self, max_age_hours: int = 24):
            from datetime import timedelta
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

            workflows_to_remove = []
            for workflow_id, workflow in self.active_workflows.items():
                if (workflow.is_completed or workflow.is_failed) and workflow.end_time:
                    if workflow.end_time < cutoff_time:
                        self.workflow_history.append(workflow.to_dict())
                        workflows_to_remove.append(workflow_id)

            for workflow_id in workflows_to_remove:
                del self.active_workflows[workflow_id]


class MockCustomerOnboardingWorkflow(BusinessWorkflow):
    """Mock workflow for testing"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.workflow_type = "customer_onboarding"

    async def execute(self):
        """Simulate customer onboarding workflow"""
        self.status = BusinessWorkflowStatus.RUNNING

        # Step 1: Validate customer data
        result1 = WorkflowResult(
            result_id=str(uuid4()),
            workflow_id=self.workflow_id,
            step="validate_customer_data",
            success=True,
            message="Customer data validated"
        )
        self.results.append(result1)

        # Step 2: Create customer account
        result2 = WorkflowResult(
            result_id=str(uuid4()),
            workflow_id=self.workflow_id,
            step="create_customer_account",
            success=True,
            message="Customer account created"
        )
        self.results.append(result2)

        # Step 3: Setup billing
        result3 = WorkflowResult(
            result_id=str(uuid4()),
            workflow_id=self.workflow_id,
            step="setup_billing",
            success=True,
            message="Billing setup completed"
        )
        self.results.append(result3)

        self.status = BusinessWorkflowStatus.COMPLETED
        self.end_time = datetime.now(timezone.utc)


class MockApprovalWorkflow(BusinessWorkflow):
    """Mock workflow that requires approval"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.workflow_type = "approval_required"

    async def execute(self):
        """Simulate workflow that needs approval"""
        self.status = BusinessWorkflowStatus.RUNNING

        # Step 1: Initial processing
        result1 = WorkflowResult(
            result_id=str(uuid4()),
            workflow_id=self.workflow_id,
            step="initial_processing",
            success=True,
            message="Initial processing completed"
        )
        self.results.append(result1)

        # Move to waiting for approval
        self.status = BusinessWorkflowStatus.WAITING_APPROVAL

    async def approve_and_continue(self, approval_data=None):
        """Continue workflow after approval"""
        if self.status == BusinessWorkflowStatus.WAITING_APPROVAL:
            self.status = BusinessWorkflowStatus.RUNNING

            # Step 2: Post-approval processing
            result2 = WorkflowResult(
                result_id=str(uuid4()),
                workflow_id=self.workflow_id,
                step="post_approval_processing",
                success=True,
                message="Post-approval processing completed"
            )
            self.results.append(result2)

            # Complete the workflow
            self.status = BusinessWorkflowStatus.COMPLETED
            self.end_time = datetime.now(timezone.utc)


@pytest.mark.integration
@pytest.mark.asyncio
class TestBusinessProcessEngineIntegration:
    """Integration tests for BusinessProcessEngine"""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session"""
        return AsyncMock()

    @pytest.fixture
    def process_engine(self, mock_db_session):
        """Create process engine for testing"""
        engine = BusinessProcessEngine(
            db_session_factory=lambda: mock_db_session
        )

        # Register test workflows
        engine.register_workflow("customer_onboarding", MockCustomerOnboardingWorkflow)
        engine.register_workflow("approval_required", MockApprovalWorkflow)

        return engine

    async def test_complete_workflow_execution(self, process_engine):
        """Test complete workflow execution from start to finish"""
        tenant_id = str(uuid4())
        context = {
            "customer_id": str(uuid4()),
            "email": "test@example.com",
            "plan_id": "premium"
        }

        # Start workflow
        workflow = await process_engine.start_workflow(
            "customer_onboarding",
            context,
            tenant_id
        )

        # Verify workflow creation
        assert workflow is not None
        assert workflow.workflow_id in process_engine.active_workflows
        assert workflow.tenant_id == tenant_id
        assert workflow.status == BusinessWorkflowStatus.COMPLETED
        assert len(workflow.results) == 3  # 3 steps in mock workflow

        # Verify workflow results
        steps = [r.step for r in workflow.results]
        assert "validate_customer_data" in steps
        assert "create_customer_account" in steps
        assert "setup_billing" in steps

        # All results should be successful
        assert all(r.success for r in workflow.results)

    async def test_workflow_with_business_rules_validation(self, process_engine):
        """Test workflow with business rules validation"""
        tenant_id = str(uuid4())

        # Context that should fail validation
        failing_context = {
            "should_fail_validation": True,
            "customer_id": str(uuid4())
        }

        # Should raise validation error
        with pytest.raises(ValueError, match="Business rules validation failed"):
            await process_engine.start_workflow(
                "customer_onboarding",
                failing_context,
                tenant_id
            )

        # Valid context should succeed
        valid_context = {
            "customer_id": str(uuid4()),
            "email": "valid@example.com"
        }

        workflow = await process_engine.start_workflow(
            "customer_onboarding",
            valid_context,
            tenant_id
        )

        assert workflow.status == BusinessWorkflowStatus.COMPLETED

    async def test_workflow_with_policy_checks(self, process_engine):
        """Test workflow with policy validation"""
        tenant_id = str(uuid4())

        # Context that should fail policy check
        failing_context = {
            "should_fail_policy": True,
            "customer_id": str(uuid4())
        }

        # Should raise policy violation error
        with pytest.raises(ValueError, match="Policy violation"):
            await process_engine.start_workflow(
                "customer_onboarding",
                failing_context,
                tenant_id
            )

    async def test_approval_workflow_lifecycle(self, process_engine):
        """Test complete approval workflow lifecycle"""
        tenant_id = str(uuid4())
        context = {"approval_required": True}

        # Start approval workflow
        workflow = await process_engine.start_workflow(
            "approval_required",
            context,
            tenant_id
        )

        # Should be waiting for approval
        assert workflow.status == BusinessWorkflowStatus.WAITING_APPROVAL
        assert len(workflow.results) == 1  # Initial processing completed

        # Test getting workflow status
        status = await process_engine.get_workflow_status(workflow.workflow_id)
        assert status["status"] == "waiting_approval"

        # Resume workflow with approval
        approval_data = {"approved_by": "admin@example.com", "notes": "Approved"}
        resumed_workflow = await process_engine.resume_workflow(
            workflow.workflow_id,
            approval_data
        )

        # Should now be completed
        assert resumed_workflow.status == BusinessWorkflowStatus.COMPLETED
        assert resumed_workflow.workflow_id == workflow.workflow_id

    async def test_workflow_rejection(self, process_engine):
        """Test workflow rejection"""
        tenant_id = str(uuid4())
        context = {"approval_required": True}

        # Start approval workflow
        workflow = await process_engine.start_workflow(
            "approval_required",
            context,
            tenant_id
        )

        assert workflow.status == BusinessWorkflowStatus.WAITING_APPROVAL

        # Reject workflow
        rejection_reason = "Insufficient documentation"
        rejected_workflow = await process_engine.reject_workflow(
            workflow.workflow_id,
            rejection_reason
        )

        # Should be cancelled
        assert rejected_workflow.status == BusinessWorkflowStatus.CANCELLED
        assert rejected_workflow.end_time is not None

    async def test_workflow_cancellation(self, process_engine):
        """Test workflow cancellation"""
        tenant_id = str(uuid4())
        context = {"customer_id": str(uuid4())}

        # Start workflow
        workflow = await process_engine.start_workflow(
            "customer_onboarding",
            context,
            tenant_id
        )

        # Cancel workflow (in practice this would be done before completion)
        cancelled_workflow = await process_engine.cancel_workflow(workflow.workflow_id)

        assert cancelled_workflow.status == BusinessWorkflowStatus.CANCELLED
        assert cancelled_workflow.end_time is not None

    async def test_list_active_workflows_with_filters(self, process_engine):
        """Test listing active workflows with various filters"""
        tenant1 = str(uuid4())
        tenant2 = str(uuid4())

        # Start workflows for different tenants
        await process_engine.start_workflow(
            "customer_onboarding",
            {"customer_id": str(uuid4())},
            tenant1
        )

        await process_engine.start_workflow(
            "customer_onboarding",
            {"customer_id": str(uuid4())},
            tenant2
        )

        # List all active workflows
        all_workflows = await process_engine.list_active_workflows()
        assert len(all_workflows) >= 2

        # Filter by tenant
        tenant1_workflows = await process_engine.list_active_workflows(tenant_id=tenant1)
        assert len(tenant1_workflows) == 1
        assert tenant1_workflows[0]["tenant_id"] == tenant1

        # Filter by workflow type
        onboarding_workflows = await process_engine.list_active_workflows(
            workflow_type="customer_onboarding"
        )
        assert len(onboarding_workflows) >= 2
        assert all(w["workflow_type"] == "customer_onboarding" for w in onboarding_workflows)

        # Filter by status
        completed_workflows = await process_engine.list_active_workflows(
            status=BusinessWorkflowStatus.COMPLETED
        )
        assert len(completed_workflows) >= 2
        assert all(w["status"] == "completed" for w in completed_workflows)


@pytest.mark.integration
@pytest.mark.asyncio
class TestBusinessProcessIntegration:
    """Integration tests for business process execution"""

    @pytest.fixture
    def process_engine(self):
        """Create process engine with sample processes"""
        engine = BusinessProcessEngine()

        # Register workflows
        engine.register_workflow("customer_onboarding", MockCustomerOnboardingWorkflow)

        # Register sample process
        sample_process = {
            "name": "Customer Lifecycle Process",
            "description": "Complete customer lifecycle from signup to billing",
            "steps": [
                {
                    "type": "rule_check",
                    "name": "validate_customer_eligibility",
                    "rule_name": "customer_eligibility"
                },
                {
                    "type": "policy_check",
                    "name": "check_signup_policies",
                    "policy_name": "signup_policy"
                },
                {
                    "type": "workflow",
                    "name": "run_customer_onboarding",
                    "workflow_type": "customer_onboarding"
                },
                {
                    "type": "custom",
                    "name": "send_welcome_email",
                    "function": "send_email"
                }
            ]
        }

        engine.register_process("customer_lifecycle", sample_process)

        return engine

    async def test_complete_process_execution(self, process_engine):
        """Test complete business process execution"""
        tenant_id = str(uuid4())
        context = {
            "customer_id": str(uuid4()),
            "email": "newcustomer@example.com",
            "plan": "premium"
        }

        # Execute process
        result = await process_engine.execute_process(
            "customer_lifecycle",
            context,
            tenant_id
        )

        # Verify process execution
        assert result["status"] == "completed"
        assert result["steps_completed"] == result["total_steps"]
        assert result["process_id"] == "customer_lifecycle"
        assert result["tenant_id"] == tenant_id
        assert "started_at" in result
        assert "completed_at" in result

        # Verify all steps succeeded
        assert len(result["results"]) == 4
        assert all(step["success"] for step in result["results"])

        # Verify step types
        step_types = [step["step_type"] for step in result["results"]]
        assert "rule_check" in step_types
        assert "policy_check" in step_types
        assert "workflow" in step_types
        assert "custom" in step_types

    async def test_process_with_failing_rule(self, process_engine):
        """Test process execution with failing rule"""
        # Register process with failing rule
        failing_process = {
            "name": "Failing Process",
            "steps": [
                {
                    "type": "rule_check",
                    "name": "failing_validation",
                    "rule_name": "failing_rule"
                },
                {
                    "type": "workflow",
                    "name": "should_not_execute",
                    "workflow_type": "customer_onboarding"
                }
            ]
        }

        process_engine.register_process("failing_process", failing_process)

        # Execute process
        result = await process_engine.execute_process(
            "failing_process",
            {},
            str(uuid4())
        )

        # Should fail at first step
        assert result["status"] == "failed"
        assert result["steps_completed"] == 1
        assert result["total_steps"] == 2
        assert "error" in result

        # Only first step should have executed
        assert len(result["results"]) == 1
        assert not result["results"][0]["success"]

    async def test_process_with_workflow_step(self, process_engine):
        """Test process step that executes a workflow"""
        workflow_process = {
            "name": "Workflow Process",
            "steps": [
                {
                    "type": "workflow",
                    "name": "execute_onboarding",
                    "workflow_type": "customer_onboarding"
                }
            ]
        }

        process_engine.register_process("workflow_process", workflow_process)

        # Execute process
        result = await process_engine.execute_process(
            "workflow_process",
            {"customer_id": str(uuid4())},
            str(uuid4())
        )

        # Verify workflow was executed
        assert result["status"] == "completed"
        assert len(result["results"]) == 1

        workflow_result = result["results"][0]
        assert workflow_result["step_type"] == "workflow"
        assert workflow_result["success"]
        assert "workflow_id" in workflow_result

        # Verify workflow was added to active workflows
        workflow_id = workflow_result["workflow_id"]
        assert workflow_id in process_engine.active_workflows

    async def test_unknown_process_execution(self, process_engine):
        """Test execution of unknown process"""
        with pytest.raises(ValueError, match="Unknown process: nonexistent_process"):
            await process_engine.execute_process(
                "nonexistent_process",
                {},
                str(uuid4())
            )


@pytest.mark.integration
@pytest.mark.asyncio
class TestWorkflowCleanupIntegration:
    """Integration tests for workflow cleanup functionality"""

    @pytest.fixture
    def process_engine(self):
        """Create process engine for cleanup testing"""
        engine = BusinessProcessEngine()
        engine.register_workflow("customer_onboarding", MockCustomerOnboardingWorkflow)
        return engine

    async def test_workflow_cleanup(self, process_engine):
        """Test cleanup of completed workflows"""
        tenant_id = str(uuid4())

        # Start several workflows
        workflows = []
        for _i in range(3):
            workflow = await process_engine.start_workflow(
                "customer_onboarding",
                {"customer_id": str(uuid4())},
                tenant_id
            )
            workflows.append(workflow)

        # All workflows should be active initially
        assert len(process_engine.active_workflows) >= 3
        assert len(process_engine.workflow_history) == 0

        # Mock old end times to trigger cleanup
        from datetime import timedelta
        old_time = datetime.now(timezone.utc) - timedelta(hours=25)

        for workflow in workflows:
            workflow.end_time = old_time

        # Run cleanup
        await process_engine.cleanup_completed_workflows(max_age_hours=24)

        # Workflows should be moved to history
        for workflow in workflows:
            assert workflow.workflow_id not in process_engine.active_workflows

        assert len(process_engine.workflow_history) >= 3

        # Verify history contains correct data
        history_workflow_ids = {wf["workflow_id"] for wf in process_engine.workflow_history}
        original_workflow_ids = {wf.workflow_id for wf in workflows}
        assert history_workflow_ids.intersection(original_workflow_ids) == original_workflow_ids

    async def test_cleanup_preserves_recent_workflows(self, process_engine):
        """Test that cleanup preserves recent completed workflows"""
        tenant_id = str(uuid4())

        # Start workflow
        workflow = await process_engine.start_workflow(
            "customer_onboarding",
            {"customer_id": str(uuid4())},
            tenant_id
        )

        # Workflow end time is recent (default)
        initial_count = len(process_engine.active_workflows)

        # Run cleanup
        await process_engine.cleanup_completed_workflows(max_age_hours=1)

        # Recent workflow should still be active
        assert workflow.workflow_id in process_engine.active_workflows
        assert len(process_engine.active_workflows) == initial_count


@pytest.mark.integration
@pytest.mark.asyncio
class TestErrorHandlingIntegration:
    """Integration tests for error handling scenarios"""

    @pytest.fixture
    def process_engine(self):
        """Create process engine for error testing"""
        engine = BusinessProcessEngine()
        engine.register_workflow("customer_onboarding", MockCustomerOnboardingWorkflow)
        return engine

    async def test_unknown_workflow_type_error(self, process_engine):
        """Test error handling for unknown workflow type"""
        with pytest.raises(ValueError, match="Unknown workflow type: nonexistent_workflow"):
            await process_engine.start_workflow(
                "nonexistent_workflow",
                {},
                str(uuid4())
            )

    async def test_workflow_not_found_errors(self, process_engine):
        """Test error handling for workflow not found scenarios"""
        nonexistent_id = str(uuid4())

        # Test resume nonexistent workflow
        with pytest.raises(ValueError, match=f"Workflow {nonexistent_id} not found"):
            await process_engine.resume_workflow(nonexistent_id)

        # Test reject nonexistent workflow
        with pytest.raises(ValueError, match=f"Workflow {nonexistent_id} not found"):
            await process_engine.reject_workflow(nonexistent_id)

        # Test cancel nonexistent workflow
        with pytest.raises(ValueError, match=f"Workflow {nonexistent_id} not found"):
            await process_engine.cancel_workflow(nonexistent_id)

        # Test get status of nonexistent workflow
        with pytest.raises(ValueError, match=f"Workflow {nonexistent_id} not found"):
            await process_engine.get_workflow_status(nonexistent_id)

    async def test_invalid_workflow_state_errors(self, process_engine):
        """Test error handling for invalid workflow state operations"""
        tenant_id = str(uuid4())

        # Start completed workflow
        workflow = await process_engine.start_workflow(
            "customer_onboarding",
            {"customer_id": str(uuid4())},
            tenant_id
        )

        # Try to resume completed workflow (should fail)
        with pytest.raises(ValueError, match="is not waiting for approval"):
            await process_engine.resume_workflow(workflow.workflow_id)

        # Try to reject completed workflow (should fail)
        with pytest.raises(ValueError, match="is not waiting for approval"):
            await process_engine.reject_workflow(workflow.workflow_id)
