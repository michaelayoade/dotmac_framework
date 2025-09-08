"""
Test package imports and public API.
"""


def test_package_imports():
    """Test that all public API components can be imported."""
    from dotmac_workflows import (
        InMemoryStateStore,
        Workflow,
        WorkflowConfigurationError,
        WorkflowError,
        WorkflowExecutionError,
        WorkflowResult,
        WorkflowStatus,
        __version__,
    )

    # Test that classes are actually classes
    assert isinstance(Workflow, type)
    assert isinstance(WorkflowResult, type)
    assert isinstance(WorkflowStatus, type)
    assert isinstance(InMemoryStateStore, type)

    # Test that exceptions are exception classes
    assert issubclass(WorkflowError, Exception)
    assert issubclass(WorkflowExecutionError, WorkflowError)
    assert issubclass(WorkflowConfigurationError, WorkflowError)

    # Test version
    assert isinstance(__version__, str)
    assert __version__ == "1.0.0"


def test_all_exports():
    """Test __all__ exports match what's actually exported."""
    import dotmac_workflows

    expected_exports = {
        "Workflow",
        "WorkflowResult",
        "WorkflowStatus",
        "WorkflowError",
        "WorkflowExecutionError",
        "WorkflowConfigurationError",
        "WorkflowStateStore",
        "InMemoryStateStore",
        "WorkflowId",
        "StepName",
        "WorkflowCallback",
        "AsyncWorkflowCallback",
    }

    actual_exports = set(dotmac_workflows.__all__)
    assert actual_exports == expected_exports

    # Test that all exports are actually accessible
    for export_name in expected_exports:
        assert hasattr(dotmac_workflows, export_name)


def test_workflow_status_enum_values():
    """Test WorkflowStatus enum has expected values."""
    from dotmac_workflows import WorkflowStatus

    expected_statuses = {
        "PENDING",
        "RUNNING",
        "COMPLETED",
        "FAILED",
        "CANCELLED",
        "WAITING_APPROVAL",
        "PAUSED",
    }

    actual_statuses = {status.name for status in WorkflowStatus}
    assert actual_statuses == expected_statuses


def test_basic_workflow_functionality():
    """Test basic workflow can be created and configured."""
    from dotmac_workflows import Workflow, WorkflowResult

    class TestWorkflow(Workflow):
        async def execute_step(self, step: str) -> WorkflowResult:
            return WorkflowResult(success=True, step=step, data={"test": True})

    workflow = TestWorkflow(workflow_id="test", steps=["step1"], metadata={"test": "data"})

    assert workflow.workflow_id == "test"
    assert workflow.steps == ["step1"]
    assert workflow.metadata == {"test": "data"}

    # Test configuration
    workflow.configure(require_approval=True)
    assert workflow.require_approval is True


def test_memory_store_basic_functionality():
    """Test InMemoryStateStore basic functionality."""
    from dotmac_workflows import InMemoryStateStore

    store = InMemoryStateStore()
    assert hasattr(store, "save")
    assert hasattr(store, "load")
    assert hasattr(store, "delete")
    assert hasattr(store, "clear")


def test_type_aliases():
    """Test type aliases are properly defined."""
    from dotmac_workflows import StepName, WorkflowId

    # These should be string aliases
    test_id: WorkflowId = "test-workflow"
    test_step: StepName = "test-step"

    assert isinstance(test_id, str)
    assert isinstance(test_step, str)
