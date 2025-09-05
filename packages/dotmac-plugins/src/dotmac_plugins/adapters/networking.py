"""
Networking domain adapter for the plugin system.

Provides specialized interfaces for networking plugins like HTTP clients, DNS, and monitoring.
"""

import logging
from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from ..core.exceptions import PluginError
from ..core.plugin_base import BasePlugin


class NetworkProtocol(Enum):
    """Network protocols."""

    HTTP = "http"
    HTTPS = "https"
    TCP = "tcp"
    UDP = "udp"
    DNS = "dns"


@dataclass
class NetworkRequest:
    """Network request."""

    url: str
    method: str = "GET"
    headers: dict[str, str] = None
    data: Any = None
    timeout: float = 30.0

    def __post_init__(self):
        if self.headers is None:
            self.headers = {}


@dataclass
class NetworkResponse:
    """Network response."""

    status_code: int
    content: bytes
    headers: dict[str, str] = None
    error_message: Optional[str] = None

    def __post_init__(self):
        if self.headers is None:
            self.headers = {}


class NetworkingPlugin(BasePlugin):
    """Base class for networking plugins."""

    @abstractmethod
    async def make_request(self, request: NetworkRequest) -> NetworkResponse:
        """Make a network request."""
        pass

    def get_supported_protocols(self) -> list[NetworkProtocol]:
        """Get supported network protocols."""
        return [NetworkProtocol.HTTP]


class NetworkingAdapter:
    """Domain adapter for networking plugins."""

    def __init__(self):
        self._plugins: dict[str, NetworkingPlugin] = {}
        self._logger = logging.getLogger("plugins.networking_adapter")

    def register_plugin(self, plugin_name: str, plugin: NetworkingPlugin) -> None:
        """Register a networking plugin."""
        if not isinstance(plugin, NetworkingPlugin):
            raise PluginError(f"Plugin {plugin_name} is not a NetworkingPlugin")

        self._plugins[plugin_name] = plugin
        self._logger.info(f"Registered networking plugin: {plugin_name}")

    async def make_request(self, request: NetworkRequest, provider: Optional[str] = None) -> NetworkResponse:
        """Make network request using specified or default provider."""
        if provider:
            if provider not in self._plugins:
                raise PluginError(f"Networking provider {provider} not found")
            plugin = self._plugins[provider]
        else:
            if not self._plugins:
                raise PluginError("No networking providers available")
            plugin = list(self._plugins.values())[0]  # Use first available

        return await plugin.make_request(request)
