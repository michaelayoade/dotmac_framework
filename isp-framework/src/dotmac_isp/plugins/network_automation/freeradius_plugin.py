"""FreeRADIUS Integration Plugin for ISP Authentication and Accounting."""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
import aiohttp
import socket
import struct
from dataclasses import dataclass

# SECURITY ENHANCEMENT: Import enterprise secrets manager
from ...core.secrets.enterprise_secrets_manager import create_enterprise_secrets_manager, SecurityError

from ..core.base import (
    NetworkAutomationPlugin,
    PluginInfo,
    PluginCategory,
    PluginContext,
    PluginConfig,
    PluginAPI,
)
from datetime import datetime, timezone
from ..core.exceptions import PluginError, PluginConfigError


@dataclass
class RADIUSClient:
    """RADIUS client configuration."""

    name: str
    ip_address: str
    secret: str
    nas_type: str = "other"
    virtual_server: str = "default"


@dataclass
class RADIUSUser:
    """RADIUS user configuration."""

    username: str
    password: str = None
    password_type: str = "cleartext"  # cleartext, md5, sha1
    attributes: Dict[str, str] = None
    group: str = None
    expiry_date: Optional[datetime] = None
    enabled: bool = True


class FreeRADIUSPlugin(NetworkAutomationPlugin):
    """
    FreeRADIUS Integration Plugin.

    Provides integration with FreeRADIUS server for:
    - Customer authentication (PPPoE, WiFi, etc.)
    - Accounting and session tracking
    - Dynamic authorization
    - NAS client management
    - User management and provisioning
    """

    def __init__(self, config: PluginConfig, api: PluginAPI):
        """Initialize FreeRADIUS plugin with enterprise secrets management."""
        super().__init__(config, api)
        
        # SECURITY ENHANCEMENT: Initialize enterprise secrets manager
        vault_url = os.getenv("VAULT_URL")
        vault_token = os.getenv("VAULT_TOKEN")
        self.secrets_manager = create_enterprise_secrets_manager(vault_url, vault_token)
        
        # Basic configuration
        self.radius_host = os.getenv("FREERADIUS_HOST", "localhost")
        self.radius_port = int(os.getenv("FREERADIUS_PORT", "1812"))
        
        # SECURITY FIX: Use enterprise secrets manager for all secrets
        try:
            self.radius_secret = self.secrets_manager.get_secure_secret(
                secret_id="freeradius-secret",
                env_var="FREERADIUS_SECRET",
                default_error="FreeRADIUS secret not configured"
            )
        except (ValueError, SecurityError) as e:
            raise ValueError(f"CRITICAL SECURITY ERROR: {e}")
            
        self.admin_api_url = os.getenv("FREERADIUS_ADMIN_URL")
        
        try:
            self.admin_api_token = self.secrets_manager.get_secure_secret(
                secret_id="freeradius-admin-token",
                env_var="FREERADIUS_ADMIN_TOKEN", 
                default_error="FreeRADIUS admin token not configured"
            )
        except (ValueError, SecurityError) as e:
            # Admin token is optional for some deployments
            self.admin_api_token = None
            self._logger.warning(f"Admin API token not configured: {e}")
            
        self.mysql_config = None
        self.session = None
        self._logger = None

    @property
    def plugin_info(self) -> PluginInfo:
        """Return plugin information."""
        return PluginInfo(
            id="freeradius_integration",
            name="FreeRADIUS Integration",
            version="1.0.0",
            description="FreeRADIUS server integration for ISP authentication and accounting",
            author="DotMac ISP Framework",
            category=PluginCategory.NETWORK_AUTOMATION,
            dependencies=["mysql_connector", "radius_client"],
            supports_multi_tenant=True,
            supports_hot_reload=True,
            security_level="elevated",
            permissions_required=["network.radius.manage", "database.radius.access"],
        )

    # REMOVED: _get_secure_secret method replaced with enterprise_secrets_manager

    async def initialize(self) -> None:
        """Initialize FreeRADIUS plugin."""
        try:
            # Get configuration
            config_data = self.config.config_data or {}

            # SECURITY FIX: Override with secure values if environment/vault configured
            self.radius_host = os.getenv("FREERADIUS_HOST", config_data.get("radius_host", "localhost")
            self.radius_port = int(os.getenv("FREERADIUS_PORT", str(config_data.get("radius_port", 1812)
            
            # SECURITY: Re-validate secrets during initialization (in case they were rotated)
            # This ensures we always have fresh, valid secrets
            if not hasattr(self, 'radius_secret') or not self.radius_secret:
                try:
                    self.radius_secret = self.secrets_manager.get_secure_secret(
                        secret_id="freeradius-secret",
                        env_var="FREERADIUS_SECRET",
                        default_error="FreeRADIUS secret not configured"
                    )
                except (ValueError, SecurityError) as e:
                    raise ValueError(f"CRITICAL SECURITY ERROR during initialization: {e}")
            
            self.admin_api_url = os.getenv("FREERADIUS_ADMIN_URL", config_data.get("admin_api_url")
            
            # Admin token validation
            if not hasattr(self, 'admin_api_token'):
                try:
                    self.admin_api_token = self.secrets_manager.get_secure_secret(
                        secret_id="freeradius-admin-token",
                        env_var="FREERADIUS_ADMIN_TOKEN",
                        default_error="FreeRADIUS admin token not configured"
                    )
                except (ValueError, SecurityError):
                    # Admin token is optional
                    self.admin_api_token = None
            self.mysql_config = config_data.get("mysql_config", {})

            # Setup logging
            self._logger = logging.getLogger(f"{__name__}.{self.plugin_info.id}")

            # Initialize HTTP session for API calls
            self.session = aiohttp.ClientSession()

            # Test connectivity
            await self._test_connectivity()

            self._logger.info("FreeRADIUS plugin initialized successfully")

        except Exception as e:
            self._logger.error(f"Failed to initialize FreeRADIUS plugin: {e}")
            raise PluginError(f"FreeRADIUS plugin initialization failed: {e}")

    async def activate(self) -> None:
        """Activate FreeRADIUS plugin."""
        try:
            # Start background tasks
            self._start_background_tasks()

            self._logger.info("FreeRADIUS plugin activated")

        except Exception as e:
            self._logger.error(f"Failed to activate FreeRADIUS plugin: {e}")
            raise PluginError(f"FreeRADIUS plugin activation failed: {e}")

    async def deactivate(self) -> None:
        """Deactivate FreeRADIUS plugin."""
        try:
            # Stop background tasks
            await self._stop_background_tasks()

            self._logger.info("FreeRADIUS plugin deactivated")

        except Exception as e:
            self._logger.error(f"Failed to deactivate FreeRADIUS plugin: {e}")

    async def cleanup(self) -> None:
        """Clean up FreeRADIUS plugin resources."""
        try:
            if self.session:
                await self.session.close()

            self._logger.info("FreeRADIUS plugin cleaned up")

        except Exception as e:
            self._logger.error(f"Failed to cleanup FreeRADIUS plugin: {e}")

    # Network Automation Plugin Interface

    async def discover_devices(self, context: PluginContext) -> List[Dict[str, Any]]:
        """Discover RADIUS NAS clients."""
        try:
            clients = await self._get_nas_clients()

            devices = []
            for client in clients:
                devices.append(
                    {
                        "device_id": client.name,
                        "device_type": "radius_nas",
                        "ip_address": client.ip_address,
                        "nas_type": client.nas_type,
                        "virtual_server": client.virtual_server,
                        "status": "active",
                        "discovered_at": datetime.now(timezone.utc).isoformat(),
                    }
                )

            return devices

        except Exception as e:
            self._logger.error(f"Failed to discover RADIUS devices: {e}")
            raise PluginError(f"Device discovery failed: {e}")

    async def configure_device(
        self, device_id: str, config: Dict[str, Any], context: PluginContext
    ) -> bool:
        """Configure RADIUS NAS client."""
        try:
            client = RADIUSClient(
                name=device_id,
                ip_address=config["ip_address"],
                secret=config["secret"],
                nas_type=config.get("nas_type", "other"),
                virtual_server=config.get("virtual_server", "default"),
            )

            success = await self._add_nas_client(client)

            if success:
                self._logger.info(
                    f"Successfully configured RADIUS NAS client: {device_id}"
                )

            return success

        except Exception as e:
            self._logger.error(f"Failed to configure RADIUS device {device_id}: {e}")
            return False

    async def get_device_status(
        self, device_id: str, context: PluginContext
    ) -> Dict[str, Any]:
        """Get RADIUS NAS client status."""
        try:
            # Get client configuration
            client = await self._get_nas_client(device_id)
            if not client:
                return {"status": "not_found", "error": "NAS client not found"}

            # Test connectivity
            is_reachable = await self._test_nas_connectivity(client.ip_address)

            # Get active sessions
            active_sessions = await self._get_active_sessions(device_id)

            return {
                "status": "active" if is_reachable else "unreachable",
                "ip_address": client.ip_address,
                "nas_type": client.nas_type,
                "virtual_server": client.virtual_server,
                "reachable": is_reachable,
                "active_sessions": len(active_sessions),
                "last_checked": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            self._logger.error(
                f"Failed to get status for RADIUS device {device_id}: {e}"
            )
            return {"status": "error", "error": str(e)}

    # FreeRADIUS Specific Methods

    async def authenticate_user(
        self,
        username: str,
        password: str,
        nas_ip: str = None,
        context: PluginContext = None,
    ) -> Dict[str, Any]:
        """
        Authenticate user against RADIUS server.

        Args:
            username: Username to authenticate
            password: Password to verify
            nas_ip: NAS IP address (optional)
            context: Plugin context

        Returns:
            Authentication result dictionary
        """
        try:
            # Create RADIUS authentication packet
            auth_result = await self._radius_auth(username, password, nas_ip)

            result = {
                "username": username,
                "authenticated": auth_result.get("code") == "Access-Accept",
                "attributes": auth_result.get("attributes", {}),
                "message": auth_result.get("message", ""),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            return result

        except Exception as e:
            self._logger.error(f"Authentication failed for user {username}: {e}")
            return {
                "username": username,
                "authenticated": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    async def add_user(self, user: RADIUSUser, context: PluginContext = None) -> bool:
        """
        Add user to RADIUS database.

        Args:
            user: RADIUS user configuration
            context: Plugin context

        Returns:
            True if successful, False otherwise
        """
        try:
            # Add user to radcheck table
            success = await self._add_user_to_database(user)

            if success:
                self._logger.info(f"Successfully added RADIUS user: {user.username}")

            return success

        except Exception as e:
            self._logger.error(f"Failed to add RADIUS user {user.username}: {e}")
            return False

    async def update_user(
        self, username: str, updates: Dict[str, Any], context: PluginContext = None
    ) -> bool:
        """
        Update RADIUS user.

        Args:
            username: Username to update
            updates: User updates
            context: Plugin context

        Returns:
            True if successful, False otherwise
        """
        try:
            success = await self._update_user_in_database(username, updates)

            if success:
                self._logger.info(f"Successfully updated RADIUS user: {username}")

            return success

        except Exception as e:
            self._logger.error(f"Failed to update RADIUS user {username}: {e}")
            return False

    async def delete_user(self, username: str, context: PluginContext = None) -> bool:
        """
        Delete RADIUS user.

        Args:
            username: Username to delete
            context: Plugin context

        Returns:
            True if successful, False otherwise
        """
        try:
            success = await self._delete_user_from_database(username)

            if success:
                self._logger.info(f"Successfully deleted RADIUS user: {username}")

            return success

        except Exception as e:
            self._logger.error(f"Failed to delete RADIUS user {username}: {e}")
            return False

    async def get_user_sessions(
        self, username: str, context: PluginContext = None
    ) -> List[Dict[str, Any]]:
        """
        Get active sessions for a user.

        Args:
            username: Username to query
            context: Plugin context

        Returns:
            List of active sessions
        """
        try:
            sessions = await self._get_user_active_sessions(username)
            return sessions

        except Exception as e:
            self._logger.error(f"Failed to get sessions for user {username}: {e}")
            return []

    async def disconnect_user(
        self, username: str, context: PluginContext = None
    ) -> bool:
        """
        Disconnect user sessions.

        Args:
            username: Username to disconnect
            context: Plugin context

        Returns:
            True if successful, False otherwise
        """
        try:
            success = await self._send_disconnect_request(username)

            if success:
                self._logger.info(f"Successfully disconnected RADIUS user: {username}")

            return success

        except Exception as e:
            self._logger.error(f"Failed to disconnect RADIUS user {username}: {e}")
            return False

    async def get_accounting_data(
        self,
        start_time: datetime = None,
        end_time: datetime = None,
        context: PluginContext = None,
    ) -> List[Dict[str, Any]]:
        """
        Get RADIUS accounting data.

        Args:
            start_time: Start time for data query
            end_time: End time for data query
            context: Plugin context

        Returns:
            List of accounting records
        """
        try:
            records = await self._get_accounting_records(start_time, end_time)
            return records

        except Exception as e:
            self._logger.error(f"Failed to get accounting data: {e}")
            return []

    # Private Helper Methods

    async def _test_connectivity(self) -> None:
        """Test connectivity to RADIUS server."""
        try:
            # Test basic UDP connectivity
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5.0)

            try:
                sock.connect((self.radius_host, self.radius_port)
                self._logger.debug(
                    f"Successfully connected to RADIUS server {self.radius_host}:{self.radius_port}"
                )
            finally:
                sock.close()

        except Exception as e:
            raise PluginError(
                f"Cannot connect to RADIUS server {self.radius_host}:{self.radius_port}: {e}"
            )

    async def _radius_auth(
        self, username: str, password: str, nas_ip: str = None
    ) -> Dict[str, Any]:
        """Perform RADIUS authentication (placeholder implementation)."""
        # This is a placeholder implementation
        # In production, use a proper RADIUS client library like pyrad

        return {
            "code": "Access-Accept" if password == "test" else "Access-Reject",
            "attributes": (
                {"Framed-IP-Address": "192.168.1.100", "Session-Timeout": 3600}
                if password == "test"
                else {}
            ),
            "message": (
                "Authentication successful"
                if password == "test"
                else "Authentication failed"
            ),
        }

    async def _get_nas_clients(self) -> List[RADIUSClient]:
        """
        Get NAS clients from RADIUS configuration.
        
        SECURITY FIX: No longer returns hardcoded secrets.
        NAS client secrets should be configured via:
        1. Environment variables (NAS_CLIENT_<NAME>_SECRET)
        2. Vault/secrets management
        3. Database configuration
        """
        try:
            # SECURITY ENHANCEMENT: Get NAS secrets using enterprise secrets manager
            nas_secret = self.secrets_manager.get_secure_secret(
                secret_id="nas-client-test-secret",
                env_var="NAS_CLIENT_TEST_SECRET",
                default_error="NAS client test secret not configured"
            )
        except (ValueError, SecurityError):
            # If no secure secret configured, return empty list instead of insecure default
            self._logger.warning(
                "No secure NAS client secrets configured. "
                "Set NAS_CLIENT_TEST_SECRET environment variable or configure in vault."
            )
            return []
        
        return [
            RADIUSClient(
                name="test-nas-1",
                ip_address=os.getenv("NAS_CLIENT_TEST_IP", "192.168.1.1"),
                secret=nas_secret,
                nas_type=os.getenv("NAS_CLIENT_TEST_TYPE", "cisco"),
            )
        ]

    async def _get_nas_client(self, device_id: str) -> Optional[RADIUSClient]:
        """Get specific NAS client."""
        clients = await self._get_nas_clients()
        for client in clients:
            if client.name == device_id:
                return client
        return None

    async def _add_nas_client(self, client: RADIUSClient) -> bool:
        """Add NAS client to RADIUS configuration."""
        # Placeholder implementation
        self._logger.info(f"Adding NAS client: {client.name} ({client.ip_address})")
        return True

    async def _test_nas_connectivity(self, ip_address: str) -> bool:
        """Test connectivity to NAS device."""
        try:
            # Simple ping test (placeholder)
            proc = await asyncio.create_subprocess_exec(
                "ping",
                "-c",
                "1",
                "-W",
                "3",
                ip_address,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )

            await proc.wait()
            return proc.returncode == 0

        except Exception:
            return False

    async def _get_active_sessions(self, device_id: str = None) -> List[Dict[str, Any]]:
        """Get active RADIUS sessions."""
        # Placeholder implementation - would query radacct table
        return [
            {
                "session_id": "12345",
                "username": "user@domain.com",
                "nas_id": device_id,
                "start_time": datetime.now(timezone.utc).isoformat(),
                "bytes_in": 1024000,
                "bytes_out": 2048000,
            }
        ]

    async def _add_user_to_database(self, user: RADIUSUser) -> bool:
        """Add user to RADIUS database."""
        # Placeholder - would insert into radcheck/radreply tables
        self._logger.info(f"Adding user to RADIUS database: {user.username}")
        return True

    async def _update_user_in_database(
        self, username: str, updates: Dict[str, Any]
    ) -> bool:
        """Update user in RADIUS database."""
        # Placeholder - would update radcheck/radreply tables
        self._logger.info(f"Updating RADIUS user: {username}")
        return True

    async def _delete_user_from_database(self, username: str) -> bool:
        """Delete user from RADIUS database."""
        # Placeholder - would delete from radcheck/radreply tables
        self._logger.info(f"Deleting RADIUS user: {username}")
        return True

    async def _get_user_active_sessions(self, username: str) -> List[Dict[str, Any]]:
        """Get active sessions for user."""
        # Placeholder - would query radacct table
        return []

    async def _send_disconnect_request(self, username: str) -> bool:
        """Send RADIUS disconnect request."""
        # Placeholder - would send CoA/Disconnect message
        self._logger.info(f"Sending disconnect request for user: {username}")
        return True

    async def _get_accounting_records(
        self, start_time: datetime = None, end_time: datetime = None
    ) -> List[Dict[str, Any]]:
        """Get accounting records from RADIUS database."""
        # Placeholder - would query radacct table
        return []

    def _start_background_tasks(self) -> None:
        """Start background monitoring tasks."""
        # Placeholder for background tasks like session cleanup
        pass

    async def _stop_background_tasks(self) -> None:
        """Stop background tasks."""
        # Placeholder for stopping background tasks
        pass

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        health_data = await super().health_check()

        try:
            # Test RADIUS server connectivity
            await self._test_connectivity()

            # Get session counts
            active_sessions = await self._get_active_sessions()

            health_data.update(
                {
                    "radius_server_reachable": True,
                    "active_sessions": len(active_sessions),
                    "details": {
                        "radius_host": self.radius_host,
                        "radius_port": self.radius_port,
                    },
                }
            )

        except Exception as e:
            health_data.update(
                {"healthy": False, "radius_server_reachable": False, "error": str(e)}
            )

        return health_data

    async def get_metrics(self) -> Dict[str, Any]:
        """Get plugin metrics."""
        metrics = await super().get_metrics()

        try:
            # Get RADIUS-specific metrics
            active_sessions = await self._get_active_sessions()

            metrics.update(
                {
                    "radius_active_sessions": len(active_sessions),
                    "radius_server_host": self.radius_host,
                    "radius_server_port": self.radius_port,
                }
            )

        except Exception as e:
            metrics["metrics_error"] = str(e)

        return metrics
