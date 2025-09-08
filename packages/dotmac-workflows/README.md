# dotmac-workflows

Base workflow engine for business processes with steps, approvals, rollback, callbacks, and resumability hooks.

## Purpose

Provides core workflow types for building business processes with support for:
- Sequential step execution
- Approval workflows
- Rollback on failure
- Resumable execution
- Pluggable persistence

## Features

- **Pure stdlib**: No external dependencies
- **Async-first**: Built for async/await patterns
- **Type-safe**: Full type hints and mypy support
- **Extensible**: Pluggable persistence and callbacks
- **Production-ready**: Comprehensive error handling and logging

## Quick Start

### Basic Workflow

```python
from dotmac_workflows import Workflow, WorkflowResult

class MyWorkflow(Workflow):
    async def execute_step(self, step: str) -> WorkflowResult:
        if step == "validate_data":
            # Your validation logic here
            return WorkflowResult(success=True, step=step, data={"validated": True})
        elif step == "process_data":
            # Your processing logic here
            return WorkflowResult(success=True, step=step, data={"processed": True})
        else:
            return WorkflowResult(
                success=False, 
                step=step, 
                error="unknown_step", 
                message=f"Unknown step: {step}"
            )

# Usage
workflow = MyWorkflow(
    workflow_id="my-workflow-123",
    steps=["validate_data", "process_data"]
)

results = await workflow.execute()
for result in results:
    print(f"Step {result.step}: {'✓' if result.success else '✗'}")
```

### Approval Workflow

```python
class ApprovalWorkflow(MyWorkflow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.configure(require_approval=True)

    async def execute_step(self, step: str) -> WorkflowResult:
        result = await super().execute_step(step)
        if step == "process_data":
            result.requires_approval = True
        return result

# Workflow will pause for approval
workflow = ApprovalWorkflow(steps=["validate_data", "process_data"])
results = await workflow.execute()  # Stops at approval step

# Later, after approval
results = await workflow.approve_and_continue({"approved_by": "user123"})
```

## API Reference

### WorkflowStatus

```python
class WorkflowStatus(Enum):
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    WAITING_APPROVAL = "waiting_approval"
    PAUSED = "paused"
```

### WorkflowResult

```python
@dataclass
class WorkflowResult:
    success: bool
    step: str
    data: dict
    error: str | None = None
    message: str | None = None
    execution_time: float | None = None
    requires_approval: bool = False
```

### Workflow

```python
class Workflow:
    def __init__(
        self,
        workflow_id: str | None = None,
        steps: list[str] | None = None,
        metadata: dict | None = None
    ):
        ...

    def configure(
        self,
        rollback_on_failure: bool = True,
        continue_on_step_failure: bool = False,
        require_approval: bool = False
    ):
        ...

    async def execute(self) -> list[WorkflowResult]:
        """Execute all workflow steps"""

    async def execute_step(self, step: str) -> WorkflowResult:
        """Override this method to implement step logic"""

    async def approve_and_continue(
        self, 
        approval_data: dict | None = None
    ) -> list[WorkflowResult]:
        """Continue execution after approval"""

    async def reject_and_cancel(
        self, 
        reason: str | None = None
    ) -> list[WorkflowResult]:
        """Cancel workflow due to rejection"""
```

### Callbacks

```python
# Set callbacks for workflow events
workflow.on_step_started = lambda step: print(f"Starting {step}")
workflow.on_step_completed = lambda result: print(f"Completed {result.step}")
workflow.on_workflow_completed = lambda results: print("Workflow done!")
workflow.on_approval_required = lambda step: print(f"Approval needed for {step}")
```

## Installation

```bash
pip install dotmac-workflows
```

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Type checking
mypy src/

# Linting
ruff check src/
```

## License

MIT