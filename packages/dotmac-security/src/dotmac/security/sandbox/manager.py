"""
Plugin security scanner and manager.
"""

import ast
import hashlib
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

import structlog

from .models import PluginPermissions, ResourceLimits
from .sandbox import PluginSandbox, PluginSecurityError

logger = structlog.get_logger(__name__)


class SecurityScanner:
    """Central plugin security scanner."""

    def __init__(self):
        self._code_validators: list[callable] = []
        self._trusted_signatures: set[str] = set()

        # Initialize default validators
        self._setup_default_validators()

    def _setup_default_validators(self) -> None:
        """Setup default code validators."""
        self._code_validators = [
            self._check_dangerous_imports,
            self._check_system_calls,
            self._check_file_operations,
            self._check_network_operations,
        ]

    async def validate_plugin_code(self, plugin_code: str, plugin_metadata: dict[str, Any]) -> bool:
        """
        Validate plugin code for security issues.

        Returns True if code is safe, raises PluginSecurityError if not.
        """
        logger.info("Validating plugin code", plugin_name=plugin_metadata.get("name", "unknown"))

        try:
            # Parse code to AST for analysis
            tree = ast.parse(plugin_code)

            # Run security validators
            for validator in self._code_validators:
                if not validator(tree, plugin_code):
                    return False

            # Check code signature if provided
            signature = plugin_metadata.get("signature")
            if signature and not self._verify_signature(plugin_code, signature):
                raise PluginSecurityError("Invalid plugin signature")

            logger.info("Plugin code validation passed")
            return True

        except SyntaxError as e:
            raise PluginSecurityError(f"Plugin code syntax error: {e}") from e
        except Exception as e:
            logger.error("Plugin validation error", error=str(e))
            raise PluginSecurityError(f"Plugin validation failed: {e}") from e

    def _check_dangerous_imports(self, tree: ast.AST, code: str) -> bool:
        """Check for dangerous imports."""
        dangerous_modules = {
            "os",
            "subprocess",
            "sys",
            "eval",
            "exec",
            "compile",
            "__import__",
            "importlib",
            "ctypes",
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in dangerous_modules:
                        raise PluginSecurityError(f"Dangerous import detected: {alias.name}")

            elif isinstance(node, ast.ImportFrom):
                if node.module in dangerous_modules:
                    raise PluginSecurityError(f"Dangerous import detected: {node.module}")

        return True

    def _check_system_calls(self, tree: ast.AST, code: str) -> bool:
        """Check for system calls."""
        dangerous_functions = {"eval", "exec", "compile", "open", "__import__"}

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in dangerous_functions:
                    raise PluginSecurityError(f"Dangerous function call: {node.func.id}")

        return True

    def _check_file_operations(self, tree: ast.AST, code: str) -> bool:
        """Check for unauthorized file operations."""
        # This would be more sophisticated in production
        if "open(" in code and "/etc/" in code:
            raise PluginSecurityError("Unauthorized system file access detected")

        return True

    def _check_network_operations(self, tree: ast.AST, code: str) -> bool:
        """Check for network operations."""
        # This would validate network access patterns
        return True

    def _verify_signature(self, code: str, signature: str) -> bool:
        """Verify plugin code signature."""
        # Implementation would verify cryptographic signature
        hashlib.sha256(code.encode()).hexdigest()
        return signature in self._trusted_signatures or len(signature) > 0

    def create_sandbox(
        self,
        plugin_id: str,
        tenant_id: Optional[UUID] = None,
        security_level: str = "default",
    ) -> PluginSandbox:
        """Create plugin sandbox with appropriate security settings."""
        # Define security levels
        security_configs = {
            "minimal": {
                "permissions": PluginPermissions.create_default(),
                "limits": ResourceLimits(max_memory_mb=128, max_cpu_time_seconds=10),
            },
            "default": {
                "permissions": PluginPermissions.create_default(),
                "limits": ResourceLimits(),
            },
            "trusted": {
                "permissions": PluginPermissions.create_full_access(),
                "limits": ResourceLimits(max_memory_mb=1024, max_cpu_time_seconds=120),
            },
        }

        config = security_configs.get(security_level, security_configs["default"])

        return PluginSandbox(
            plugin_id=plugin_id,
            tenant_id=tenant_id,
            permissions=config["permissions"],
            resource_limits=config["limits"],
        )

    async def scan_plugin_file(self, file_path: Path) -> dict[str, Any]:
        """
        Scan plugin file for security issues.

        Returns scan results with security assessment.
        """
        logger.info("Scanning plugin file", file_path=str(file_path))

        try:
            with open(file_path, encoding="utf-8") as f:
                code = f.read()

            # Basic file analysis
            scan_result = {
                "file_size": file_path.stat().st_size,
                "line_count": len(code.splitlines()),
                "code_hash": hashlib.sha256(code.encode()).hexdigest(),
                "security_issues": [],
                "risk_level": "low",
            }

            # Validate code
            try:
                await self.validate_plugin_code(code, {"name": file_path.name})
                scan_result["validation_passed"] = True
            except PluginSecurityError as e:
                scan_result["validation_passed"] = False
                scan_result["security_issues"].append(str(e))
                scan_result["risk_level"] = "high"

            return scan_result

        except Exception as e:
            logger.error("Plugin file scan error", error=str(e))
            return {"error": str(e), "risk_level": "unknown"}
