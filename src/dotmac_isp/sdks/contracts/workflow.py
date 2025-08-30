"""Workflow contract definitions."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base import BaseContract


@dataclass
class WorkflowStep:
    """Individual workflow step."""

    name: str
    action: str
    params: Dict[str, Any] = field(default_factory=dict)
    conditions: Optional[Dict[str, Any]] = None


@dataclass
class WorkflowContract(BaseContract):
    """Workflow execution contract."""

    name: str = ""
    description: str = ""
    steps: List[WorkflowStep] = field(default_factory=list)

    def add_step(self, step: WorkflowStep):
        """Add step to workflow."""
        self.steps.append(step)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        base_dict = super().to_dict()
        base_dict.update(
            {
                "name": self.name,
                "description": self.description,
                "steps": [
                    {
                        "name": step.name,
                        "action": step.action,
                        "params": step.params,
                        "conditions": step.conditions,
                    }
                    for step in self.steps
                ],
            }
        )
        return base_dict
