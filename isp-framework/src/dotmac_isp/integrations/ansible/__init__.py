"""Ansible Integration for Network Device Automation.

This module provides comprehensive Ansible integration for network device
management, configuration deployment, and automation workflows.
"""

from .client import AnsibleClient
from .playbook_manager import PlaybookManager
from .inventory_manager import InventoryManager
from .configuration_templates import ConfigurationTemplateManager
from .execution_engine import ExecutionEngine
from .models import (
    AnsiblePlaybook,
    PlaybookExecution,
    DeviceInventory,
    ConfigurationTemplate,
    AutomationTask,
)
from .schemas import (
    PlaybookCreate,
    PlaybookResponse,
    ExecutionCreate,
    ExecutionResponse,
    InventoryCreate,
    InventoryResponse,
    TemplateCreate,
    TemplateResponse,
)

__all__ = [
    # Core components
    "AnsibleClient",
    "PlaybookManager",
    "InventoryManager",
    "ConfigurationTemplateManager",
    "ExecutionEngine",
    # Models
    "AnsiblePlaybook",
    "PlaybookExecution",
    "DeviceInventory",
    "ConfigurationTemplate",
    "AutomationTask",
    # Schemas
    "PlaybookCreate",
    "PlaybookResponse",
    "ExecutionCreate",
    "ExecutionResponse",
    "InventoryCreate",
    "InventoryResponse",
    "TemplateCreate",
    "TemplateResponse",
]
