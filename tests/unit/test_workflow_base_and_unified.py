import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

from dotmac_shared.workflows.base import BaseWorkflow, WorkflowResult
from dotmac_shared.workflows.exceptions import (
    WorkflowError,
    WorkflowTransientError,
    WorkflowValidationError,
)
from dotmac_shared.workflows.unified_workflow_service import (
    ActionType,
    TriggerType,
    UnifiedWorkflowRule,
    UnifiedWorkflowService,
    WorkflowContext,
    WorkflowType,
)


class SleepWorkflow(BaseWorkflow):
    def __init__(self, sleep_seconds: float, timeout_seconds: float | None = None):
        metadata: dict[str, Any] = {}
        if timeout_seconds:
            metadata["timeouts"] = {"sleep": timeout_seconds}
        super().__init__(workflow_id="wf1", workflow_type="test", steps=["sleep"], metadata=metadata)
        self._sleep = sleep_seconds

    async def execute_step(self, step_name: str) -> WorkflowResult:
        if step_name == "sleep":
            await asyncio.sleep(self._sleep)
            return WorkflowResult(success=True, step_name=step_name, message="slept")
        raise WorkflowError("unknown step")


@pytest.mark.asyncio
async def test_base_workflow_timeout_maps_to_code_timeout() -> None:
    wf = SleepWorkflow(sleep_seconds=0.05, timeout_seconds=0.01)
    results = await wf.execute()
    assert len(results) == 1
    assert results[0].success is False
    assert results[0].code == "timeout"


class ValidationWorkflow(BaseWorkflow):
    def __init__(self):
        super().__init__(workflow_id="wf2", workflow_type="test", steps=["validate"])

    async def execute_step(self, step_name: str) -> WorkflowResult:
        raise WorkflowValidationError("bad input")


@pytest.mark.asyncio
async def test_base_workflow_validation_error_mapped() -> None:
    wf = ValidationWorkflow()
    results = await wf.execute()
    assert results[0].success is False
    assert results[0].code == "validation_error"


@pytest.mark.asyncio
async def test_unified_workflow_execute_workflow_rule_level_classification(monkeypatch) -> None:
    svc = UnifiedWorkflowService()
    await svc.initialize()
    ctx = WorkflowContext(workflow_id="x", tenant_id="t", user_id="u")

    rule = UnifiedWorkflowRule(
        rule_id="r1",
        name="r1",
        workflow_type=WorkflowType.AUTOMATION,
        trigger_type=svc.TriggerType.EVENT if hasattr(svc, "TriggerType") else WorkflowType.AUTOMATION,  # safe
        conditions=[],
        actions=[],
    )

    # Monkeypatch _execute_rule to raise different errors and verify code mapping
    async def raise_val(rule, context):  # noqa: ANN001
        raise WorkflowValidationError("nope")

    async def raise_transient(rule, context):  # noqa: ANN001
        raise WorkflowTransientError("flaky")

    async def raise_workflow(rule, context):  # noqa: ANN001
        raise WorkflowError("boom")

    async def raise_unexpected(rule, context):  # noqa: ANN001
        raise RuntimeError("weird")

    # Validation
    monkeypatch.setattr(svc, "_execute_rule", raise_val, raising=True)
    out = await svc.execute_workflow(WorkflowType.AUTOMATION, ctx, [rule])
    assert out and out[0].code == "validation_error"

    # Transient
    monkeypatch.setattr(svc, "_execute_rule", raise_transient, raising=True)
    out = await svc.execute_workflow(WorkflowType.AUTOMATION, ctx, [rule])
    assert out and out[0].code == "transient_error"

    # Workflow
    monkeypatch.setattr(svc, "_execute_rule", raise_workflow, raising=True)
    out = await svc.execute_workflow(WorkflowType.AUTOMATION, ctx, [rule])
    assert out and out[0].code == "workflow_error"

    # Unexpected
    monkeypatch.setattr(svc, "_execute_rule", raise_unexpected, raising=True)
    out = await svc.execute_workflow(WorkflowType.AUTOMATION, ctx, [rule])
    assert out and out[0].code == "unexpected_error"


@pytest.mark.asyncio
async def test_unified_workflow_execute_rule_action_classification() -> None:
    svc = UnifiedWorkflowService()
    await svc.initialize()
    ctx = WorkflowContext(workflow_id="x", tenant_id="t", user_id="u")

    async def h_ok(action, context):  # noqa: ANN001
        return {"ok": True}

    async def h_val(action, context):  # noqa: ANN001
        raise ValueError("bad")

    async def h_transient(action, context):  # noqa: ANN001
        raise TimeoutError("t")

    async def h_wf(action, context):  # noqa: ANN001
        raise WorkflowError("wf")

    async def h_unexpected(action, context):  # noqa: ANN001
        raise RuntimeError("x")

    svc.register_action_handler(ActionType.CUSTOM, h_ok)
    svc.register_action_handler(ActionType.NOTIFICATION, h_val)
    svc.register_action_handler(ActionType.API_CALL, h_transient)
    svc.register_action_handler(ActionType.DATABASE_UPDATE, h_wf)
    svc.register_action_handler(ActionType.EMAIL, h_unexpected)

    rule = UnifiedWorkflowRule(
        rule_id="r2",
        name="r2",
        workflow_type=WorkflowType.AUTOMATION,
        trigger_type=TriggerType.EVENT,
        actions=[
            {"type": "custom"},
            {"type": "notification"},
            {"type": "api_call"},
            {"type": "database_update"},
            {"type": "email"},
        ],
    )

    res = await svc._execute_rule(rule, ctx)
    assert res.success is False
    assert res.data["error_count"] == 4
    errors = res.error or ""
    assert "validation failed" in errors or "validation" in errors
    assert "transient" in errors
    assert "workflow" in errors
    assert "failed" in errors


class DummyLicenseRepo:
    def __init__(self):
        self.updates: list[tuple] = []

    async def update(self, license_id, payload):  # noqa: ANN001
        self.updates.append((license_id, payload))


class DummyTenantManager:
    def __init__(self, should_raise: bool = False):
        self.shutdown_calls = 0
        self.should_raise = should_raise

    async def initialize(self):  # noqa: D401
        return True

    async def shutdown(self):  # noqa: D401
        self.shutdown_calls += 1
        if self.should_raise:
            raise RuntimeError("shutdown error")


@pytest.mark.asyncio
async def test_plugin_installation_workflow_rollback_on_failure(monkeypatch):
    # Prepare fake modules required by plugin_workflows import
    import sys
    import types
    fake_dotmac = types.ModuleType("dotmac")
    fake_security = types.ModuleType("dotmac.security")
    fake_sandbox = types.ModuleType("dotmac.security.sandbox")
    class SecurityScanner:  # noqa: N801
        pass
    fake_sandbox.SecurityScanner = SecurityScanner
    fake_plugins = types.ModuleType("dotmac_plugins")
    fake_isolation = types.ModuleType("dotmac_plugins.isolation")
    fake_tpm = types.ModuleType("dotmac_plugins.isolation.tenant_plugin_manager")
    def get_tenant_plugin_manager(**kwargs):  # noqa: ANN001
        return SimpleNamespace(initialize=lambda: None)
    fake_tpm.get_tenant_plugin_manager = get_tenant_plugin_manager
    # Stub dotmac_management models/service modules to avoid heavy ORM imports
    fake_dm_models = types.ModuleType("dotmac_management.models")
    fake_dm_models_plugin = types.ModuleType("dotmac_management.models.plugin")
    class _LicenseStatus:
        CANCELLED = "cancelled"
        TRIAL = "trial"
    fake_dm_models_plugin.LicenseStatus = _LicenseStatus
    class Plugin:  # noqa: N801
        pass
    class PluginLicense:  # noqa: N801
        pass
    fake_dm_models_plugin.Plugin = Plugin
    fake_dm_models_plugin.PluginLicense = PluginLicense
    fake_dm_core_notifications = types.ModuleType("dotmac_management.core.notifications")
    class NotificationService:  # noqa: N801
        pass
    fake_dm_core_notifications.NotificationService = NotificationService
    fake_dm_services_plugin_service = types.ModuleType("dotmac_management.services.plugin_service")
    class PluginService:  # noqa: N801
        pass
    fake_dm_services_plugin_service.PluginService = PluginService

    fake_dm_schemas = types.ModuleType("dotmac_management.schemas")
    fake_dm_schemas_plugin = types.ModuleType("dotmac_management.schemas.plugin")
    class PluginInstallationRequest:  # noqa: N801
        pass
    fake_dm_schemas_plugin.PluginInstallationRequest = PluginInstallationRequest

    sys.modules.update({
        "dotmac": fake_dotmac,
        "dotmac.security": fake_security,
        "dotmac.security.sandbox": fake_sandbox,
        "dotmac_plugins": fake_plugins,
        "dotmac_plugins.isolation": fake_isolation,
        "dotmac_plugins.isolation.tenant_plugin_manager": fake_tpm,
        "dotmac_management.models": fake_dm_models,
        "dotmac_management.models.plugin": fake_dm_models_plugin,
        "dotmac_management.core.notifications": fake_dm_core_notifications,
        "dotmac_management.services.plugin_service": fake_dm_services_plugin_service,
        "dotmac_management.schemas": fake_dm_schemas,
        "dotmac_management.schemas.plugin": fake_dm_schemas_plugin,
    })

    from dotmac_management.workflows.plugin_workflows import PluginInstallationWorkflow

    # Build minimal workflow with faked services
    request = SimpleNamespace(plugin_id="pid", license_tier=SimpleNamespace(value="basic"), configuration={})
    plugin_service = SimpleNamespace(license_repo=DummyLicenseRepo())
    notification_service = SimpleNamespace(
        send_admin_notification=lambda *a, **k: None,
        send_user_notification=lambda *a, **k: None,
    )

    wf = PluginInstallationWorkflow(
        request=request,
        tenant_id="tid",
        user_id="uid",
        plugin_service=plugin_service,
        notification_service=notification_service,
    )

    # Stub steps: make earlier steps succeed and then fail on LOAD_PLUGIN
    async def ok_step():
        return {}

    async def create_license_ok():
        wf.plugin_license = SimpleNamespace(id="lic1", license_tier=request.license_tier, status="trial", trial_ends_at=None)
        return {"license_id": "lic1"}

    tm = DummyTenantManager()

    async def setup_env_ok():
        wf.tenant_manager = tm
        return {"tenant_environment_ready": True}

    async def fail_load():
        raise WorkflowError("load failed")

    # Patch handlers on instance
    monkeypatch.setattr(wf, "_validate_request", ok_step)
    monkeypatch.setattr(wf, "_check_dependencies", ok_step)
    monkeypatch.setattr(wf, "_validate_security", ok_step)
    monkeypatch.setattr(wf, "_create_license", create_license_ok)
    monkeypatch.setattr(wf, "_setup_tenant_environment", setup_env_ok)
    monkeypatch.setattr(wf, "_load_plugin", fail_load)

    results = await wf.execute()

    # Ensure last step failed and rollback ran for previous successes (tenant shutdown + license cancel)
    assert results[-1].success is False
    # tenant manager shutdown invoked
    assert tm.shutdown_calls == 1
    # license cancelled in rollback
    assert plugin_service.license_repo.updates
    assert plugin_service.license_repo.updates[-1][1].get("status") in ("cancelled", getattr(plugin_service.license_repo.updates[-1][1].get("status"), "value", None))


@pytest.mark.asyncio
async def test_plugin_installation_workflow_rollback_continues_on_rollback_error(monkeypatch):
    # Prepare fake imports as above
    import sys
    import types
    fake_dotmac = types.ModuleType("dotmac")
    fake_security = types.ModuleType("dotmac.security")
    fake_sandbox = types.ModuleType("dotmac.security.sandbox")
    class SecurityScanner:  # noqa: N801
        pass
    fake_sandbox.SecurityScanner = SecurityScanner
    fake_plugins = types.ModuleType("dotmac_plugins")
    fake_isolation = types.ModuleType("dotmac_plugins.isolation")
    fake_tpm = types.ModuleType("dotmac_plugins.isolation.tenant_plugin_manager")
    def get_tenant_plugin_manager(**kwargs):  # noqa: ANN001
        return SimpleNamespace(initialize=lambda: None)
    fake_tpm.get_tenant_plugin_manager = get_tenant_plugin_manager
    fake_dm_models = types.ModuleType("dotmac_management.models")
    fake_dm_models_plugin = types.ModuleType("dotmac_management.models.plugin")
    class _LicenseStatus:
        CANCELLED = "cancelled"
        TRIAL = "trial"
    fake_dm_models_plugin.LicenseStatus = _LicenseStatus
    class Plugin:  # noqa: N801
        pass
    class PluginLicense:  # noqa: N801
        pass
    fake_dm_models_plugin.Plugin = Plugin
    fake_dm_models_plugin.PluginLicense = PluginLicense
    fake_dm_core_notifications = types.ModuleType("dotmac_management.core.notifications")
    class NotificationService:  # noqa: N801
        pass
    fake_dm_core_notifications.NotificationService = NotificationService
    fake_dm_services_plugin_service = types.ModuleType("dotmac_management.services.plugin_service")
    class PluginService:  # noqa: N801
        pass
    fake_dm_services_plugin_service.PluginService = PluginService

    fake_dm_schemas = types.ModuleType("dotmac_management.schemas")
    fake_dm_schemas_plugin = types.ModuleType("dotmac_management.schemas.plugin")
    class PluginInstallationRequest:  # noqa: N801
        pass
    fake_dm_schemas_plugin.PluginInstallationRequest = PluginInstallationRequest

    sys.modules.update({
        "dotmac": fake_dotmac,
        "dotmac.security": fake_security,
        "dotmac.security.sandbox": fake_sandbox,
        "dotmac_plugins": fake_plugins,
        "dotmac_plugins.isolation": fake_isolation,
        "dotmac_plugins.isolation.tenant_plugin_manager": fake_tpm,
        "dotmac_management.models": fake_dm_models,
        "dotmac_management.models.plugin": fake_dm_models_plugin,
        "dotmac_management.core.notifications": fake_dm_core_notifications,
        "dotmac_management.services.plugin_service": fake_dm_services_plugin_service,
        "dotmac_management.schemas": fake_dm_schemas,
        "dotmac_management.schemas.plugin": fake_dm_schemas_plugin,
    })

    from dotmac_management.workflows.plugin_workflows import PluginInstallationWorkflow
    request = SimpleNamespace(plugin_id="pid", license_tier=SimpleNamespace(value="basic"), configuration={})
    plugin_service = SimpleNamespace(license_repo=DummyLicenseRepo())
    notification_service = SimpleNamespace(
        send_admin_notification=lambda *a, **k: None,
        send_user_notification=lambda *a, **k: None,
    )

    wf = PluginInstallationWorkflow(
        request=request,
        tenant_id="tid",
        user_id="uid",
        plugin_service=plugin_service,
        notification_service=notification_service,
    )

    async def ok_step():
        return {}

    async def create_license_ok():
        wf.plugin_license = SimpleNamespace(id="lic2", license_tier=request.license_tier, status="trial", trial_ends_at=None)
        return {"license_id": "lic2"}

    tm = DummyTenantManager(should_raise=True)

    async def setup_env_ok():
        wf.tenant_manager = tm
        return {"tenant_environment_ready": True}

    async def fail_configure():
        raise WorkflowError("configure failed")

    monkeypatch.setattr(wf, "_validate_request", ok_step)
    monkeypatch.setattr(wf, "_check_dependencies", ok_step)
    monkeypatch.setattr(wf, "_validate_security", ok_step)
    monkeypatch.setattr(wf, "_create_license", create_license_ok)
    monkeypatch.setattr(wf, "_setup_tenant_environment", setup_env_ok)
    monkeypatch.setattr(wf, "_load_plugin", ok_step)
    monkeypatch.setattr(wf, "_configure_plugin", fail_configure)

    results = await wf.execute()

    # Despite rollback error from tenant shutdown, license rollback still executed
    assert results[-1].success is False
    assert plugin_service.license_repo.updates
    assert plugin_service.license_repo.updates[-1][1].get("status") in ("cancelled", getattr(plugin_service.license_repo.updates[-1][1].get("status"), "value", None))
