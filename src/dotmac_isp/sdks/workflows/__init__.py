"""
Core SDKs for operations plane functionality.

This module provides SDKs for:
- Workflow orchestration and management
- Task execution and coordination
- Automation rules and engines
- Plugin lifecycle workflows
- Project workflow management
- Support automation workflows
"""

from dotmac_workflows import (
    Workflow as BaseWorkflow,
)
from dotmac_workflows import (
    WorkflowResult,
    WorkflowStatus,
)
from dotmac_workflows.base import (
    WorkflowConfigurationError,
    WorkflowError,
)
from dotmac_workflows.base import (
    WorkflowExecutionError as WorkflowValidationError,
)

# Create aliases for backward compatibility
TaskWorkflow = BaseWorkflow
SequentialTaskWorkflow = BaseWorkflow
AutomationWorkflow = BaseWorkflow
AutomationRule = dict  # Simple fallback
TriggerType = str  # Simple fallback

# Create simple factory functions
def create_task_workflow(workflow_id, steps):
    return BaseWorkflow(workflow_id, steps)

def create_sequential_workflow(workflow_id, steps):
    return BaseWorkflow(workflow_id, steps)

def create_automation_workflow(workflow_id, steps):
    return BaseWorkflow(workflow_id, steps)

def create_simple_rule(name, condition):
    return {"name": name, "condition": condition}

# Import workflow contracts
from ..contracts.workflow import WorkflowContract, WorkflowStep

# Import from actual implementations (optional)
try:
    from dotmac_management.workflows.plugin_workflows import (
        PluginInstallationStep,
        PluginInstallationWorkflow,
        PluginUninstallWorkflow,
        PluginUpdateWorkflow,
    )

    _PLUGIN_WORKFLOWS_AVAILABLE = True
except ImportError:
    _PLUGIN_WORKFLOWS_AVAILABLE = False

try:
    from dotmac_shared.project_management.workflows.project_workflows import (
        ProjectWorkflowManager,
        WorkflowAction,
        WorkflowRule,
        WorkflowTrigger,
    )

    _PROJECT_WORKFLOWS_AVAILABLE = True
except ImportError:
    _PROJECT_WORKFLOWS_AVAILABLE = False

try:
    from dotmac_management.workflows.support_automation import (
        assign_to_team,
        auto_respond_to_ticket,
        categorize_ticket,
        escalate_ticket,
    )

    _SUPPORT_AUTOMATION_AVAILABLE = True
except ImportError:
    _SUPPORT_AUTOMATION_AVAILABLE = False

# Re-export with consistent naming
if _PROJECT_WORKFLOWS_AVAILABLE:
    WorkflowSDK = ProjectWorkflowManager
else:
    WorkflowSDK = BaseWorkflow  # Fallback to base workflow

if _PLUGIN_WORKFLOWS_AVAILABLE:
    PluginWorkflowSDK = PluginInstallationWorkflow
else:
    PluginWorkflowSDK = None

if _SUPPORT_AUTOMATION_AVAILABLE:
    SupportAutomationSDK = categorize_ticket
else:
    SupportAutomationSDK = None

# Define what's always available for export
__all__ = [
    # Contracts
    "WorkflowContract",
    "WorkflowStep",
    # Core workflow classes (always available)
    "BaseWorkflow",
    "WorkflowResult",
    "WorkflowStatus",
    "TaskWorkflow",
    "SequentialTaskWorkflow",
    "AutomationWorkflow",
    "AutomationRule",
    "TriggerType",
    "WorkflowSDK",
    # Factory functions
    "create_task_workflow",
    "create_sequential_workflow",
    "create_automation_workflow",
    "create_simple_rule",
    # Exceptions
    "WorkflowError",
    "WorkflowValidationError",
]

# Add available workflow implementations
if _PROJECT_WORKFLOWS_AVAILABLE:
    __all__.extend(
        [
            "ProjectWorkflowManager",
            "WorkflowRule",
            "WorkflowTrigger",
            "WorkflowAction",
        ]
    )

if _PLUGIN_WORKFLOWS_AVAILABLE:
    __all__.extend(
        [
            "PluginWorkflowSDK",
            "PluginInstallationWorkflow",
            "PluginUpdateWorkflow",
            "PluginUninstallWorkflow",
            "PluginInstallationStep",
        ]
    )

if _SUPPORT_AUTOMATION_AVAILABLE:
    __all__.extend(
        [
            "SupportAutomationSDK",
            "categorize_ticket",
            "auto_respond_to_ticket",
            "assign_to_team",
            "escalate_ticket",
        ]
    )
