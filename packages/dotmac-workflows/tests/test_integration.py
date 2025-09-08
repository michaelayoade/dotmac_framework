"""
Integration tests for workflow package.
"""

from dotmac_workflows import InMemoryStateStore, Workflow, WorkflowResult, WorkflowStatus


class IntegrationTestWorkflow(Workflow):
    """Integration test workflow with realistic business logic."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.processed_data = {}
        self.validation_errors = []

    async def execute_step(self, step: str) -> WorkflowResult:
        """Execute business workflow steps."""

        if step == "validate_input":
            return await self._validate_input()
        elif step == "process_data":
            return await self._process_data()
        elif step == "send_notifications":
            return await self._send_notifications()
        elif step == "finalize":
            return await self._finalize()
        elif step.startswith("rollback_"):
            return await self._rollback_step(step)
        else:
            return WorkflowResult(
                success=False,
                step=step,
                data={},
                error="unknown_step",
                message=f"Unknown step: {step}",
            )

    async def _validate_input(self) -> WorkflowResult:
        """Validate input data."""
        input_data = self.metadata.get("input_data", {})

        if not input_data.get("user_id"):
            return WorkflowResult(
                success=False,
                step="validate_input",
                data={},
                error="missing_user_id",
                message="User ID is required",
            )

        if not input_data.get("amount") or input_data["amount"] <= 0:
            return WorkflowResult(
                success=False,
                step="validate_input",
                data={},
                error="invalid_amount",
                message="Amount must be positive",
            )

        return WorkflowResult(
            success=True, step="validate_input", data={"validated": True, "input": input_data}
        )

    async def _process_data(self) -> WorkflowResult:
        """Process the validated data."""
        input_data = self.metadata.get("input_data", {})

        # Simulate data processing
        processed = {
            "user_id": input_data["user_id"],
            "amount": input_data["amount"],
            "processed_at": "2024-01-01T12:00:00Z",
            "transaction_id": f"txn_{self.workflow_id[:8]}",
        }

        self.processed_data = processed

        # Check if approval needed for large amounts
        requires_approval = input_data["amount"] > 1000

        return WorkflowResult(
            success=True,
            step="process_data",
            data={"processed": processed},
            requires_approval=requires_approval,
        )

    async def _send_notifications(self) -> WorkflowResult:
        """Send notifications about processing."""
        if not self.processed_data:
            return WorkflowResult(
                success=False,
                step="send_notifications",
                data={},
                error="no_processed_data",
                message="No processed data to notify about",
            )

        notifications_sent = [
            f"email_to_{self.processed_data['user_id']}",
            f"sms_to_{self.processed_data['user_id']}",
        ]

        return WorkflowResult(
            success=True, step="send_notifications", data={"notifications": notifications_sent}
        )

    async def _finalize(self) -> WorkflowResult:
        """Finalize the workflow."""
        return WorkflowResult(
            success=True,
            step="finalize",
            data={
                "finalized": True,
                "transaction_id": self.processed_data.get("transaction_id"),
                "approval_data": self.approval_data,
            },
        )

    async def _rollback_step(self, step: str) -> WorkflowResult:
        """Rollback a specific step."""
        original_step = step.replace("rollback_", "")

        if original_step == "process_data":
            self.processed_data = {}
        elif original_step == "send_notifications":
            # Simulate canceling notifications
            pass

        return WorkflowResult(success=True, step=step, data={"rolled_back": original_step})


class TestWorkflowIntegration:
    """Integration tests for complete workflow scenarios."""

    async def test_successful_workflow_execution(self):
        """Test complete successful workflow execution."""
        workflow = IntegrationTestWorkflow(
            workflow_id="integration-test-1",
            steps=["validate_input", "process_data", "send_notifications", "finalize"],
            metadata={"input_data": {"user_id": "user123", "amount": 500}},
        )

        results = await workflow.execute()

        assert len(results) == 4
        assert all(r.success for r in results)
        assert workflow.status == WorkflowStatus.COMPLETED
        assert workflow.processed_data["user_id"] == "user123"
        assert workflow.processed_data["amount"] == 500

        # Check each step result
        validate_result = results[0]
        assert validate_result.step == "validate_input"
        assert validate_result.data["validated"] is True

        process_result = results[1]
        assert process_result.step == "process_data"
        assert "processed" in process_result.data
        assert not process_result.requires_approval  # Amount <= 1000

        notify_result = results[2]
        assert notify_result.step == "send_notifications"
        assert len(notify_result.data["notifications"]) == 2

        finalize_result = results[3]
        assert finalize_result.step == "finalize"
        assert finalize_result.data["finalized"] is True

    async def test_workflow_with_validation_failure(self):
        """Test workflow that fails validation."""
        workflow = IntegrationTestWorkflow(
            workflow_id="integration-test-2",
            steps=["validate_input", "process_data"],
            metadata={
                "input_data": {
                    "user_id": "",  # Invalid
                    "amount": -100,  # Invalid
                }
            },
        )

        results = await workflow.execute()

        assert len(results) == 1
        assert not results[0].success
        assert results[0].error == "missing_user_id"
        assert workflow.status == WorkflowStatus.FAILED

    async def test_approval_workflow_with_large_amount(self):
        """Test workflow requiring approval for large amounts."""
        workflow = IntegrationTestWorkflow(
            workflow_id="integration-test-3",
            steps=["validate_input", "process_data", "send_notifications", "finalize"],
            metadata={
                "input_data": {
                    "user_id": "user123",
                    "amount": 5000,  # Requires approval
                }
            },
        )
        workflow.configure(require_approval=True)

        # First execution should stop at approval
        results = await workflow.execute()

        assert len(results) == 2
        assert results[0].success is True  # validate_input
        assert results[1].success is True  # process_data
        assert results[1].requires_approval is True
        assert workflow.status == WorkflowStatus.WAITING_APPROVAL

        # Approve and continue
        approval_data = {"approved_by": "manager123", "notes": "Approved for large amount"}
        continued_results = await workflow.approve_and_continue(approval_data)

        assert len(continued_results) == 4  # All steps completed
        assert workflow.status == WorkflowStatus.COMPLETED
        assert workflow.approval_data == approval_data

        # Check finalize step got approval data
        finalize_result = continued_results[3]
        assert finalize_result.data["approval_data"] == approval_data

    async def test_workflow_with_rollback(self):
        """Test workflow with failure and rollback."""
        workflow = IntegrationTestWorkflow(
            workflow_id="integration-test-4",
            steps=["validate_input", "process_data", "send_notifications"],
            metadata={"input_data": {"user_id": "user123", "amount": 500}},
        )
        workflow.configure(rollback_on_failure=True)

        # Modify workflow to fail on notifications
        original_method = workflow._send_notifications

        async def failing_notifications():
            return WorkflowResult(
                success=False,
                step="send_notifications",
                data={},
                error="notification_service_down",
                message="Notification service is unavailable",
            )

        workflow._send_notifications = failing_notifications

        results = await workflow.execute()

        # Should have validation, processing, failed notifications, and rollbacks
        assert len(results) >= 3
        assert results[0].success is True  # validate_input
        assert results[1].success is True  # process_data
        assert results[2].success is False  # send_notifications (failed)
        assert workflow.status == WorkflowStatus.FAILED

        # Check that rollback was attempted
        rollback_steps = [r for r in results if r.step.startswith("rollback_")]
        assert len(rollback_steps) >= 1

    async def test_workflow_persistence(self):
        """Test workflow with persistence."""
        store = InMemoryStateStore()

        # Create and partially execute workflow
        workflow = IntegrationTestWorkflow(
            workflow_id="persistent-test",
            steps=["validate_input", "process_data", "send_notifications"],
            metadata={
                "input_data": {
                    "user_id": "user123",
                    "amount": 2000,  # Requires approval
                }
            },
        )
        workflow.configure(require_approval=True)

        # Execute until approval needed
        await workflow.execute()
        assert workflow.status == WorkflowStatus.WAITING_APPROVAL

        # Save workflow state
        await store.save(workflow)

        # Load workflow from storage
        loaded_workflow = await store.load("persistent-test")
        assert loaded_workflow is not None
        assert loaded_workflow.workflow_id == "persistent-test"
        assert loaded_workflow.status == WorkflowStatus.WAITING_APPROVAL
        assert loaded_workflow.current_step_index == 1  # Index at step that's waiting
        assert len(loaded_workflow.results) == 2

        # Continue execution from loaded state
        # Note: This would require the loaded workflow to be properly initialized
        # with the business logic, which is a limitation of the base persistence


class TestWorkflowErrorHandling:
    """Test error handling scenarios."""

    async def test_step_execution_exception(self):
        """Test handling of exceptions during step execution."""

        class FailingWorkflow(Workflow):
            async def execute_step(self, step: str) -> WorkflowResult:
                if step == "failing_step":
                    raise ValueError("Something went wrong")
                return WorkflowResult(success=True, step=step, data={})

        workflow = FailingWorkflow(workflow_id="test", steps=["good_step", "failing_step"])
        workflow.configure(rollback_on_failure=False)

        results = await workflow.execute()

        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is False
        assert results[1].error == "step_execution_error"
        assert "Something went wrong" in results[1].message
        assert workflow.status == WorkflowStatus.FAILED

    async def test_abstract_method_not_implemented(self):
        """Test that base workflow raises NotImplementedError."""
        workflow = Workflow(workflow_id="test", steps=["step1"])

        # Should raise NotImplementedError during step execution
        results = await workflow.execute()

        # The workflow should fail because execute_step is not implemented
        assert len(results) == 1
        assert not results[0].success
        assert results[0].error == "step_execution_error"
        assert "implement execute_step method" in results[0].message

    async def test_workflow_callbacks_with_exceptions(self):
        """Test workflow continues even if callbacks raise exceptions."""
        workflow = IntegrationTestWorkflow(
            workflow_id="callback-test",
            steps=["validate_input"],
            metadata={"input_data": {"user_id": "user123", "amount": 100}},
        )

        def failing_callback(step_or_result):
            raise RuntimeError("Callback failed")

        workflow.on_step_started = failing_callback
        workflow.on_step_completed = failing_callback

        # Workflow should still complete despite callback failures
        results = await workflow.execute()

        assert len(results) == 1
        assert results[0].success is True
        assert workflow.status == WorkflowStatus.COMPLETED
