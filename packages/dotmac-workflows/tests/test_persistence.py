"""
Tests for workflow persistence implementations.
"""

import pytest

from dotmac_workflows.base import Workflow
from dotmac_workflows.persistence import InMemoryStateStore
from dotmac_workflows.result import WorkflowResult


class SimpleWorkflow(Workflow):
    """Simple workflow for testing."""

    async def execute_step(self, step: str) -> WorkflowResult:
        """Execute step - just return success."""
        return WorkflowResult(success=True, step=step, data={"step": step})


class TestInMemoryStateStore:
    """Test in-memory state store."""

    @pytest.fixture
    def store(self):
        """Create clean store for each test."""
        return InMemoryStateStore()

    @pytest.fixture
    def workflow(self):
        """Create test workflow."""
        return SimpleWorkflow(
            workflow_id="test-workflow", steps=["step1", "step2"], metadata={"test": "data"}
        )

    async def test_save_and_load(self, store, workflow):
        """Test saving and loading workflow."""
        # Save workflow
        await store.save(workflow)

        # Load workflow
        loaded = await store.load("test-workflow")

        assert loaded is not None
        assert loaded.workflow_id == workflow.workflow_id
        assert loaded.steps == workflow.steps
        assert loaded.metadata == workflow.metadata
        assert loaded.status == workflow.status

    async def test_load_nonexistent(self, store):
        """Test loading non-existent workflow returns None."""
        result = await store.load("nonexistent")
        assert result is None

    async def test_save_without_id_raises_error(self, store):
        """Test saving workflow without ID raises error."""
        workflow = SimpleWorkflow(workflow_id="")
        # Manually set empty ID to test the save validation
        workflow.workflow_id = ""

        with pytest.raises(ValueError, match="Workflow must have an ID"):
            await store.save(workflow)

    async def test_delete_existing(self, store, workflow):
        """Test deleting existing workflow."""
        # Save workflow first
        await store.save(workflow)

        # Delete it
        result = await store.delete("test-workflow")
        assert result is True

        # Verify it's gone
        loaded = await store.load("test-workflow")
        assert loaded is None

    async def test_delete_nonexistent(self, store):
        """Test deleting non-existent workflow returns False."""
        result = await store.delete("nonexistent")
        assert result is False

    async def test_clear(self, store, workflow):
        """Test clearing all workflows."""
        # Save some workflows
        await store.save(workflow)

        workflow2 = SimpleWorkflow(workflow_id="test-2")
        await store.save(workflow2)

        # Clear store
        store.clear()

        # Verify both are gone
        assert await store.load("test-workflow") is None
        assert await store.load("test-2") is None

    async def test_overwrite_existing(self, store, workflow):
        """Test overwriting existing workflow."""
        # Save initial workflow
        await store.save(workflow)

        # Modify and save again
        workflow.metadata["updated"] = True
        await store.save(workflow)

        # Load and verify update
        loaded = await store.load("test-workflow")
        assert loaded is not None
        assert loaded.metadata["updated"] is True
