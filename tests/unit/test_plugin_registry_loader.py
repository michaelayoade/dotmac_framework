import pytest

from dotmac_management.core.plugins.base import (
    BasePlugin,
    PluginMeta,
    PluginType,
)
from dotmac_management.core.plugins.loader import PluginLoader
from dotmac_management.core.plugins.registry import PluginRegistry


class GoodPlugin(BasePlugin):
    @property
    def meta(self) -> PluginMeta:
        return PluginMeta(
            name="good",
            version="1.0.0",
            plugin_type=PluginType.ANALYTICS_PROVIDER,
            description="",
            author="test",
        )

    async def initialize(self) -> bool:  # noqa: D401
        return True

    async def validate_configuration(self, config: dict) -> bool:  # noqa: ANN001
        return True

    async def health_check(self) -> dict:  # noqa: ANN001
        return {"status": "ok"}


class BadInitPlugin(GoodPlugin):
    async def initialize(self) -> bool:  # noqa: D401
        raise TypeError("boom")


class BadConfigPlugin(GoodPlugin):
    async def validate_configuration(self, config: dict) -> bool:  # noqa: ANN001
        return False


@pytest.mark.asyncio
async def test_plugin_registry_register_and_reload():
    reg = PluginRegistry()

    ok = await reg.register_plugin(GoodPlugin({}))
    assert ok is True

    # reload
    assert await reg.reload_plugin("good") is True

    # health check works
    health = await reg.health_check_all()
    assert "good" in health and health["good"].get("status") == "ok"


@pytest.mark.asyncio
async def test_plugin_registry_register_failures():
    reg = PluginRegistry()

    # Bad init should fail but not raise
    ok = await reg.register_plugin(BadInitPlugin({}))
    assert ok is False

    # Bad config should fail validation
    ok = await reg.register_plugin(BadConfigPlugin({}))
    assert ok is False


@pytest.mark.asyncio
async def test_loader_reload_module_unknown():
    loader = PluginLoader()
    assert await loader.reload_module("does_not_exist") is False
