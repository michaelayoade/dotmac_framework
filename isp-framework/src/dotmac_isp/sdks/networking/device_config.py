"""
Device Config SDK - intent → template, diff, drift, approvals, maintenance windows
"""

import difflib
from datetime import datetime
from dotmac_isp.sdks.core.datetime_utils import utc_now, utc_now_iso
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..core.exceptions import ConfigDriftDetectedError, ConfigError
from .netjson_support import NetJSONConfigMixin


class DeviceConfigService:
    """In-memory service for device configuration operations."""

    def __init__(self):
        self._configs: Dict[str, Dict[str, Any]] = {}
        self._templates: Dict[str, Dict[str, Any]] = {}
        self._intents: Dict[str, Dict[str, Any]] = {}
        self._approvals: Dict[str, Dict[str, Any]] = {}
        self._maintenance_windows: Dict[str, Dict[str, Any]] = {}
        self._config_history: Dict[str, List[Dict[str, Any]]] = {}

    async def create_config_template(self, **kwargs) -> Dict[str, Any]:
        """Create configuration template."""
        template_id = kwargs.get("template_id") or str(uuid4())

        template = {
            "template_id": template_id,
            "template_name": kwargs["template_name"],
            "device_type": kwargs.get("device_type", "generic"),
            "vendor": kwargs.get("vendor", ""),
            "template_content": kwargs["template_content"],
            "variables": kwargs.get("variables", []),
            "description": kwargs.get("description", ""),
            "version": kwargs.get("version", "1.0"),
            "status": kwargs.get("status", "active"),
            "created_at": utc_now().isoformat(),
            "updated_at": utc_now().isoformat(),
        }

        self._templates[template_id] = template
        return template

    async def create_config_intent(self, **kwargs) -> Dict[str, Any]:
        """Create configuration intent."""
        intent_id = kwargs.get("intent_id") or str(uuid4())

        intent = {
            "intent_id": intent_id,
            "device_id": kwargs["device_id"],
            "template_id": kwargs.get("template_id"),
            "intent_type": kwargs.get("intent_type", "configuration"),
            "parameters": kwargs.get("parameters", {}),
            "priority": kwargs.get("priority", "normal"),
            "requires_approval": kwargs.get("requires_approval", False),
            "maintenance_window_id": kwargs.get("maintenance_window_id"),
            "status": "pending",
            "created_at": utc_now().isoformat(),
            "created_by": kwargs.get("created_by", "system"),
        }

        self._intents[intent_id] = intent
        return intent

    async def render_config(self, intent_id: str) -> Dict[str, Any]:
        """Render configuration from intent and template."""
        if intent_id not in self._intents:
            raise ConfigError(f"Intent not found: {intent_id}")

        intent = self._intents[intent_id]
        template_id = intent.get("template_id")

        if not template_id or template_id not in self._templates:
            raise ConfigError(f"Template not found: {template_id}")

        template = self._templates[template_id]
        template_content = template["template_content"]
        parameters = intent["parameters"]

        # Simple template rendering (replace variables)
        rendered_config = template_content
        for var_name, var_value in parameters.items():
            placeholder = f"{{{{{var_name}}}}}"
            rendered_config = rendered_config.replace(placeholder, str(var_value))

        config_id = str(uuid4())
        config = {
            "config_id": config_id,
            "intent_id": intent_id,
            "device_id": intent["device_id"],
            "template_id": template_id,
            "rendered_config": rendered_config,
            "parameters": parameters,
            "status": "rendered",
            "rendered_at": utc_now().isoformat(),
        }

        self._configs[config_id] = config
        intent["config_id"] = config_id
        intent["status"] = "rendered"

        return config

    async def calculate_diff(self, device_id: str, new_config: str) -> Dict[str, Any]:
        """Calculate configuration diff."""
        # Get current config for device
        current_configs = [
            config
            for config in self._configs.values()
            if config["device_id"] == device_id and config["status"] == "applied"
        ]

        current_config = ""
        if current_configs:
            # Get the most recent applied config
            latest_config = max(current_configs, key=lambda c: c["rendered_at"])
            current_config = latest_config["rendered_config"]

        # Calculate diff
        current_lines = current_config.splitlines(keepends=True)
        new_lines = new_config.splitlines(keepends=True)

        diff = list(
            difflib.unified_diff(
                current_lines,
                new_lines,
                fromfile="current_config",
                tofile="new_config",
                lineterm="",
            )
        )

        return {
            "device_id": device_id,
            "has_changes": len(diff) > 0,
            "diff": "\n".join(diff),
            "added_lines": len(
                [
                    line
                    for line in diff
                    if line.startswith("+") and not line.startswith("+++")
                ]
            ),
            "removed_lines": len(
                [
                    line
                    for line in diff
                    if line.startswith("-") and not line.startswith("---")
                ]
            ),
            "calculated_at": utc_now().isoformat(),
        }

    async def detect_drift(self, device_id: str, running_config: str) -> Dict[str, Any]:
        """Detect configuration drift."""
        # Get expected config for device
        expected_configs = [
            config
            for config in self._configs.values()
            if config["device_id"] == device_id and config["status"] == "applied"
        ]

        if not expected_configs:
            return {
                "device_id": device_id,
                "drift_detected": False,
                "reason": "No expected configuration found",
            }

        # Get the most recent applied config
        expected_config = max(expected_configs, key=lambda c: c["rendered_at"])
        expected_content = expected_config["rendered_config"]

        # Simple drift detection (exact match)
        drift_detected = expected_content.strip() != running_config.strip()

        if drift_detected:
            diff_result = await self.calculate_diff(device_id, running_config)

            return {
                "device_id": device_id,
                "drift_detected": True,
                "expected_config_id": expected_config["config_id"],
                "diff": diff_result["diff"],
                "detected_at": utc_now().isoformat(),
            }

        return {
            "device_id": device_id,
            "drift_detected": False,
            "last_check": utc_now().isoformat(),
        }

    async def create_maintenance_window(self, **kwargs) -> Dict[str, Any]:
        """Create maintenance window."""
        window_id = kwargs.get("window_id") or str(uuid4())

        window = {
            "window_id": window_id,
            "window_name": kwargs["window_name"],
            "description": kwargs.get("description", ""),
            "start_time": kwargs["start_time"],
            "end_time": kwargs["end_time"],
            "timezone": kwargs.get("timezone", "UTC"),
            "recurrence": kwargs.get(
                "recurrence", "none"
            ),  # none, daily, weekly, monthly
            "device_ids": kwargs.get("device_ids", []),
            "max_concurrent_changes": kwargs.get("max_concurrent_changes", 5),
            "status": kwargs.get("status", "scheduled"),
            "created_at": utc_now().isoformat(),
            "created_by": kwargs.get("created_by", "system"),
        }

        self._maintenance_windows[window_id] = window
        return window


class DeviceConfigSDK(NetJSONConfigMixin):
    """Minimal, reusable SDK for device configuration management with NetJSON support."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._service = DeviceConfigService()
        # Initialize NetJSON support
        super().__init__()

    async def create_config_template(
        self,
        template_name: str,
        template_content: str,
        device_type: str = "generic",
        vendor: Optional[str] = None,
        variables: Optional[List[str]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create configuration template."""
        template = await self._service.create_config_template(
            template_name=template_name,
            template_content=template_content,
            device_type=device_type,
            vendor=vendor,
            variables=variables or [],
            tenant_id=self.tenant_id,
            **kwargs,
        )

        return {
            "template_id": template["template_id"],
            "template_name": template["template_name"],
            "device_type": template["device_type"],
            "vendor": template["vendor"],
            "variables": template["variables"],
            "description": template["description"],
            "version": template["version"],
            "status": template["status"],
            "created_at": template["created_at"],
        }

    async def create_config_intent(
        self,
        device_id: str,
        template_id: str,
        parameters: Dict[str, Any],
        requires_approval: bool = False,
        maintenance_window_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create configuration intent."""
        intent = await self._service.create_config_intent(
            device_id=device_id,
            template_id=template_id,
            parameters=parameters,
            requires_approval=requires_approval,
            maintenance_window_id=maintenance_window_id,
            **kwargs,
        )

        return {
            "intent_id": intent["intent_id"],
            "device_id": intent["device_id"],
            "template_id": intent["template_id"],
            "intent_type": intent["intent_type"],
            "parameters": intent["parameters"],
            "priority": intent["priority"],
            "requires_approval": intent["requires_approval"],
            "maintenance_window_id": intent["maintenance_window_id"],
            "status": intent["status"],
            "created_at": intent["created_at"],
            "created_by": intent["created_by"],
        }

    async def render_configuration(self, intent_id: str) -> Dict[str, Any]:
        """Render configuration from intent."""
        config = await self._service.render_config(intent_id)

        return {
            "config_id": config["config_id"],
            "intent_id": config["intent_id"],
            "device_id": config["device_id"],
            "template_id": config["template_id"],
            "rendered_config": config["rendered_config"],
            "parameters": config["parameters"],
            "status": config["status"],
            "rendered_at": config["rendered_at"],
        }

    async def calculate_config_diff(
        self, device_id: str, new_config: str
    ) -> Dict[str, Any]:
        """Calculate configuration diff."""
        diff_result = await self._service.calculate_diff(device_id, new_config)

        return {
            "device_id": diff_result["device_id"],
            "has_changes": diff_result["has_changes"],
            "diff": diff_result["diff"],
            "added_lines": diff_result["added_lines"],
            "removed_lines": diff_result["removed_lines"],
            "calculated_at": diff_result["calculated_at"],
        }

    async def detect_config_drift(
        self, device_id: str, running_config: str
    ) -> Dict[str, Any]:
        """Detect configuration drift."""
        drift_result = await self._service.detect_drift(device_id, running_config)

        if drift_result["drift_detected"]:
            # Raise exception for drift detection
            raise ConfigDriftDetectedError(
                device_id,
                {
                    "expected_config_id": drift_result.get("expected_config_id"),
                    "diff": drift_result.get("diff"),
                },
            )

        return {
            "device_id": drift_result["device_id"],
            "drift_detected": drift_result["drift_detected"],
            "last_check": drift_result.get("last_check"),
            "reason": drift_result.get("reason"),
        }

    async def create_maintenance_window(
        self,
        window_name: str,
        start_time: str,
        end_time: str,
        device_ids: Optional[List[str]] = None,
        description: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create maintenance window."""
        window = await self._service.create_maintenance_window(
            window_name=window_name,
            start_time=start_time,
            end_time=end_time,
            device_ids=device_ids or [],
            description=description,
            **kwargs,
        )

        return {
            "window_id": window["window_id"],
            "window_name": window["window_name"],
            "description": window["description"],
            "start_time": window["start_time"],
            "end_time": window["end_time"],
            "timezone": window["timezone"],
            "recurrence": window["recurrence"],
            "device_ids": window["device_ids"],
            "max_concurrent_changes": window["max_concurrent_changes"],
            "status": window["status"],
            "created_at": window["created_at"],
            "created_by": window["created_by"],
        }

    async def approve_config_intent(
        self, intent_id: str, approver: str, comments: Optional[str] = None
    ) -> Dict[str, Any]:
        """Approve configuration intent."""
        if intent_id not in self._service._intents:
            raise ConfigError(f"Intent not found: {intent_id}")

        intent = self._service._intents[intent_id]

        approval_id = str(uuid4())
        approval = {
            "approval_id": approval_id,
            "intent_id": intent_id,
            "approver": approver,
            "action": "approved",
            "comments": comments,
            "approved_at": utc_now().isoformat(),
        }

        self._service._approvals[approval_id] = approval
        intent["status"] = "approved"
        intent["approved_by"] = approver
        intent["approved_at"] = utc_now().isoformat()

        return {
            "approval_id": approval_id,
            "intent_id": intent_id,
            "approver": approver,
            "action": "approved",
            "comments": comments,
            "approved_at": approval["approved_at"],
        }

    async def get_pending_approvals(self) -> List[Dict[str, Any]]:
        """Get pending configuration approvals."""
        pending_intents = [
            intent
            for intent in self._service._intents.values()
            if intent["requires_approval"] and intent["status"] == "pending"
        ]

        return [
            {
                "intent_id": intent["intent_id"],
                "device_id": intent["device_id"],
                "intent_type": intent["intent_type"],
                "priority": intent["priority"],
                "created_at": intent["created_at"],
                "created_by": intent["created_by"],
            }
            for intent in pending_intents
        ]

    async def get_maintenance_windows(
        self, active_only: bool = False
    ) -> List[Dict[str, Any]]:
        """Get maintenance windows."""
        windows = list(self._service._maintenance_windows.values())

        if active_only:
            now = utc_now().isoformat()
            windows = [
                window
                for window in windows
                if window["start_time"] <= now <= window["end_time"]
                and window["status"] == "active"
            ]

        return [
            {
                "window_id": window["window_id"],
                "window_name": window["window_name"],
                "start_time": window["start_time"],
                "end_time": window["end_time"],
                "device_ids": window["device_ids"],
                "status": window["status"],
                "created_by": window["created_by"],
            }
            for window in windows
        ]
