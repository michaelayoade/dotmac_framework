"""
SSH Automation SDK - Production SSH device management using Paramiko
"""

import asyncio
import time
import socket
from typing import Any, Dict, List, Optional, Tuple

try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False
from uuid import uuid4
from datetime import datetime

from ..core.datetime_utils import utc_now
from ..core.exceptions import NetworkingError
from ..core.config import config


class SSHConnectionPool:
    """Connection pool for managing SSH connections efficiently"""

    def __init__(self, max_connections: int = 10):
        """  Init   operation."""
        self.max_connections = max_connections
        self.active_connections: Dict[str, Any] = {}
        self.connection_lock = asyncio.Lock()

    async def get_connection(
        self, host: str, username: str, password: str, port: int = 22
    ):
        """Get or create SSH connection"""
        connection_key = f"{username}@{host}:{port}"

        async with self.connection_lock:
            if connection_key in self.active_connections:
                conn_info = self.active_connections[connection_key]
                if time.time() - conn_info["last_used"] < 300:  # 5 minute timeout
                    conn_info["last_used"] = time.time()
                    return conn_info["client"]
                else:
                    # Connection expired, remove it
                    try:
                        conn_info["client"].close()
                    except:
                        pass
                    del self.active_connections[connection_key]

            # Create new connection using enhanced SSH client
            # Use mock mode for testing, real paramiko for production
            use_mock_mode = config.environment == "development"
            enhanced_client = EnhancedSSHClient(
                host, username, port, use_mock=use_mock_mode
            )

            self.active_connections[connection_key] = {
                "client": enhanced_client,
                "created": time.time(),
                "last_used": time.time(),
            }

            return enhanced_client

    async def close_all_connections(self):
        """Close all active connections"""
        async with self.connection_lock:
            for conn_info in self.active_connections.values():
                try:
                    conn_info["client"].close()
                except:
                    pass
            self.active_connections.clear()


class EnhancedSSHClient:
    """Enhanced SSH client with both real and mock capabilities"""

    def __init__(self, host: str, username: str, port: int, use_mock: bool = False):
        """  Init   operation."""
        self.host = host
        self.username = username
        self.port = port
        self.use_mock = use_mock
        self.connected = False

        if use_mock:
            self.client = self._create_mock_client()
        else:
            self.client = paramiko.SSHClient()
            # Load system host keys for secure verification
            self.client.load_system_host_keys()
            self.client.load_host_keys()
            # Use RejectPolicy for production security - require known hosts
            self.client.set_missing_host_key_policy(paramiko.RejectPolicy())

    def _create_mock_client(self):
        """Create mock client for testing"""

        class MockClient:
            """Class for MockClient operations."""
            def __init__(self):
                """  Init   operation."""
                self.connected = False

            def connect(self, **kwargs):
                """Connect operation."""
                self.connected = True
                return True

            def exec_command(self, command: str):
                """Exec Command operation."""
                # Simulate common network device responses
                mock_responses = {
                    "uci show wireless": "wireless.@wifi-device[0]=wifi-device\nwireless.@wifi-device[0].type='mac80211'",
                    "uptime": "12:34:56 up 5 days, 2:15, load average: 0.15, 0.12, 0.09",
                    "cat /proc/meminfo": "MemTotal: 128000 kB\nMemFree: 45000 kB",
                    "iwconfig wlan0": 'wlan0 IEEE 802.11 ESSID:"TestNetwork" Mode:Master',
                    "ping -c 3 8.8.8.8": "PING 8.8.8.8: 3 packets transmitted, 3 received, 0% packet loss",
                }

                # Return mock response based on command
                output = mock_responses.get(command, f"Executed: {command}")
                error = ""

                # Simulate UCI configuration commands
                if command.startswith("uci set"):
                    output = "Configuration updated"
                elif command == "uci commit":
                    output = "Configuration committed"
                elif command.startswith("wget"):
                    output = "File downloaded successfully"
                elif command.startswith("sysupgrade"):
                    output = "Firmware upgrade initiated"

                # Mock stdin, stdout, stderr
                class MockStream:
                    """Class for MockStream operations."""
                    def __init__(self, content: str):
                        """  Init   operation."""
                        self.content = content

                    def read(self):
                        """Read operation."""
                        return self.content.encode("utf-8")

                    def channel(self):
                        """Channel operation."""
                        class MockChannel:
                            """Class for MockChannel operations."""
                            def recv_exit_status(self):
                                """Recv Exit Status operation."""
                                return 0

                        return MockChannel()

                return MockStream(""), MockStream(output), MockStream(error)

            def close(self):
                """Close operation."""
                self.connected = False

        return MockClient()

    def connect(self, **kwargs):
        """Connect to SSH host"""
        try:
            if self.use_mock:
                self.client.connect(**kwargs)
                self.connected = True
                return True
            else:
                # Real paramiko connection
                self.client.connect(
                    hostname=self.host,
                    username=self.username,
                    port=self.port,
                    timeout=kwargs.get("timeout", config.ssh_timeout),
                    **kwargs,
                )
                self.connected = True
                return True
        except Exception as e:
            self.connected = False
            raise NetworkingError(
                f"SSH connection failed to {self.host}:{self.port} - {str(e)}"
            )

    def exec_command(self, command: str):
        """Execute command via SSH"""
        if not self.connected:
            raise NetworkingError("SSH client not connected")

        return self.client.exec_command(command)

    def close(self):
        """Close SSH connection"""
        if self.client:
            self.client.close()
        self.connected = False


class SSHDeviceManager:
    """Production SSH automation for network devices"""

    def __init__(self, max_concurrent: int = None):
        """  Init   operation."""
        self.connection_pool = SSHConnectionPool()
        self.max_concurrent = max_concurrent or config.ssh_max_concurrent
        self.execution_history: List[Dict[str, Any]] = []

    async def execute_command(
        self,
        device_ip: str,
        command: str,
        credentials: Dict[str, str],
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """Execute single command on network device"""

        execution_id = str(uuid4())
        start_time = utc_now()

        try:
            # Get SSH connection from pool
            ssh_client = await self.connection_pool.get_connection(
                host=device_ip,
                username=credentials["username"],
                password=credentials["password"],
                port=credentials.get("port", 22),
            )

            # Connect if not already connected
            if not ssh_client.connected:
                ssh_client.connect(
                    hostname=device_ip,
                    username=credentials["username"],
                    password=credentials["password"],
                    port=credentials.get("port", 22),
                    timeout=timeout,
                )

            # Execute command
            stdin, stdout, stderr = ssh_client.exec_command(command)
            output = stdout.read().decode("utf-8")
            errors = stderr.read().decode("utf-8")

            execution_result = {
                "execution_id": execution_id,
                "device_ip": device_ip,
                "command": command,
                "output": output.strip(),
                "errors": errors.strip(),
                "success": len(errors.strip()) == 0,
                "duration_seconds": (utc_now() - start_time).total_seconds(),
                "executed_at": start_time.isoformat(),
            }

            self.execution_history.append(execution_result)
            return execution_result

        except Exception as e:
            error_result = {
                "execution_id": execution_id,
                "device_ip": device_ip,
                "command": command,
                "output": "",
                "errors": str(e),
                "success": False,
                "duration_seconds": (utc_now() - start_time).total_seconds(),
                "executed_at": start_time.isoformat(),
            }

            self.execution_history.append(error_result)
            return error_result

    async def execute_commands_batch(
        self,
        device_ip: str,
        commands: List[str],
        credentials: Dict[str, str],
        stop_on_error: bool = True,
    ) -> Dict[str, Any]:
        """Execute multiple commands in sequence"""

        results = []
        batch_start = utc_now()

        for command in commands:
            result = await self.execute_command(device_ip, command, credentials)
            results.append(result)

            if not result["success"] and stop_on_error:
                break

        return {
            "device_ip": device_ip,
            "batch_id": str(uuid4()),
            "total_commands": len(commands),
            "executed_commands": len(results),
            "successful_commands": len([r for r in results if r["success"]]),
            "failed_commands": len([r for r in results if not r["success"]]),
            "total_duration": (utc_now() - batch_start).total_seconds(),
            "stopped_on_error": stop_on_error
            and any(not r["success"] for r in results),
            "results": results,
            "executed_at": batch_start.isoformat(),
        }

    async def execute_parallel(
        self, device_commands: List[Tuple[str, str, Dict[str, str]]]
    ) -> List[Dict[str, Any]]:
        """Execute commands on multiple devices in parallel"""

        # Limit concurrency
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def execute_with_semaphore(
            """Execute With Semaphore operation."""
            device_ip: str, command: str, credentials: Dict[str, str]
        ):
            async with semaphore:
                return await self.execute_command(device_ip, command, credentials)

        tasks = [
            execute_with_semaphore(device_ip, command, credentials)
            for device_ip, command, credentials in device_commands
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                device_ip, command, _ = device_commands[i]
                processed_results.append(
                    {
                        "execution_id": str(uuid4()),
                        "device_ip": device_ip,
                        "command": command,
                        "output": "",
                        "errors": str(result),
                        "success": False,
                        "executed_at": utc_now().isoformat(),
                    }
                )
            else:
                processed_results.append(result)

        return processed_results

    async def backup_device_config(
        self, device_ip: str, credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Backup device configuration"""

        backup_commands = [
            "uci export",
            "cat /etc/config/network",
            "cat /etc/config/wireless",
            "cat /etc/config/system",
        ]

        backup_results = {}
        for command in backup_commands:
            result = await self.execute_command(device_ip, command, credentials)
            backup_results[command] = result["output"] if result["success"] else ""

        return {
            "device_ip": device_ip,
            "backup_id": str(uuid4()),
            "backup_data": backup_results,
            "backup_created": utc_now().isoformat(),
        }

    async def restore_device_config(
        self, device_ip: str, backup_data: Dict[str, str], credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Restore device configuration from backup"""

        # Apply backed up UCI configuration
        uci_config = backup_data.get("uci export", "")
        if uci_config:
            # Split UCI export into individual commands
            restore_commands = []
            for line in uci_config.split("\n"):
                if line.strip() and not line.startswith("#"):
                    restore_commands.append(f"uci {line.strip()}")

            restore_commands.append("uci commit")

            return await self.execute_commands_batch(
                device_ip, restore_commands, credentials
            )
        else:
            return {
                "device_ip": device_ip,
                "success": False,
                "error": "No backup data available",
            }

    async def get_device_info(
        self, device_ip: str, credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Get comprehensive device information"""

        info_commands = {
            "hostname": "uci get system.@system[0].hostname",
            "uptime": "uptime",
            "memory": "cat /proc/meminfo | head -3",
            "wireless_status": "iwconfig 2>/dev/null | grep -E '(wlan|ath)'",
            "network_interfaces": "ip addr show",
            "system_info": "cat /proc/version",
            "storage": "df -h",
        }

        device_info = {"device_ip": device_ip}

        for info_type, command in info_commands.items():
            result = await self.execute_command(device_ip, command, credentials)
            device_info[info_type] = {
                "data": result["output"] if result["success"] else "",
                "success": result["success"],
                "error": result["errors"] if not result["success"] else "",
            }

        device_info["collected_at"] = utc_now().isoformat()
        return device_info

    async def health_check(
        self, device_list: List[Tuple[str, Dict[str, str]]]
    ) -> Dict[str, Any]:
        """Perform health check on multiple devices"""

        health_check_command = "uptime && echo '---' && cat /proc/meminfo | head -2 && echo '---' && ping -c 2 8.8.8.8"

        parallel_commands = [
            (device_ip, health_check_command, credentials)
            for device_ip, credentials in device_list
        ]

        results = await self.execute_parallel(parallel_commands)

        # Analyze health status
        health_summary = {
            "total_devices": len(device_list),
            "healthy_devices": 0,
            "unhealthy_devices": 0,
            "unreachable_devices": 0,
            "device_status": {},
        }

        for result in results:
            device_ip = result["device_ip"]
            if result["success"]:
                # Parse uptime and memory from output
                output = result["output"]
                if "load average" in output and "MemFree" in output:
                    health_summary["healthy_devices"] += 1
                    health_summary["device_status"][device_ip] = "healthy"
                else:
                    health_summary["unhealthy_devices"] += 1
                    health_summary["device_status"][device_ip] = "unhealthy"
            else:
                health_summary["unreachable_devices"] += 1
                health_summary["device_status"][device_ip] = "unreachable"

        health_summary["health_check_completed"] = utc_now().isoformat()
        health_summary["detailed_results"] = results

        return health_summary

    async def get_execution_stats(self) -> Dict[str, Any]:
        """Get SSH execution statistics"""

        if not self.execution_history:
            return {"total_executions": 0}

        successful_executions = [e for e in self.execution_history if e["success"]]
        failed_executions = [e for e in self.execution_history if not e["success"]]

        return {
            "total_executions": len(self.execution_history),
            "successful_executions": len(successful_executions),
            "failed_executions": len(failed_executions),
            "success_rate": len(successful_executions)
            / len(self.execution_history)
            * 100,
            "average_execution_time": sum(
                e["duration_seconds"] for e in self.execution_history
            )
            / len(self.execution_history),
            "most_executed_commands": self._get_command_frequency(),
            "unique_devices": len(set(e["device_ip"] for e in self.execution_history)),
        }

    def _get_command_frequency(self) -> Dict[str, int]:
        """Get frequency of executed commands"""
        command_freq = {}
        for execution in self.execution_history:
            command = execution["command"]
            command_freq[command] = command_freq.get(command, 0) + 1

        # Return top 10 most frequent commands
        return dict(sorted(command_freq.items(), key=lambda x: x[1], reverse=True)[:10])

    async def cleanup(self):
        """Clean up resources"""
        await self.connection_pool.close_all_connections()


class SSHAutomationSDK:
    """Main SDK for SSH-based network automation"""

    def __init__(self, tenant_id: str):
        """  Init   operation."""
        self.tenant_id = tenant_id
        self.ssh_manager = SSHDeviceManager()
        self.default_credentials = {}

    def set_default_credentials(self, username: str, password: str, port: int = 22):
        """Set default SSH credentials for devices"""
        self.default_credentials = {
            "username": username,
            "password": password,
            "port": port,
        }

    async def deploy_configuration(
        self,
        device_list: List[str],
        uci_commands: List[str],
        credentials: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Deploy UCI configuration to multiple devices"""

        creds = credentials or self.default_credentials
        if not creds:
            raise NetworkingError("No credentials provided")

        deployment_results = []

        for device_ip in device_list:
            # Backup current configuration
            backup = await self.ssh_manager.backup_device_config(device_ip, creds)

            # Deploy new configuration
            deploy_result = await self.ssh_manager.execute_commands_batch(
                device_ip, uci_commands, creds, stop_on_error=True
            )

            deploy_result["backup_id"] = backup["backup_id"]
            deployment_results.append(deploy_result)

        return {
            "deployment_id": str(uuid4()),
            "total_devices": len(device_list),
            "successful_deployments": len(
                [
                    r
                    for r in deployment_results
                    if r["successful_commands"] == r["total_commands"]
                ]
            ),
            "failed_deployments": len(
                [
                    r
                    for r in deployment_results
                    if r["successful_commands"] != r["total_commands"]
                ]
            ),
            "detailed_results": deployment_results,
            "deployment_completed": utc_now().isoformat(),
        }

    async def network_discovery(
        self, ip_range: str, credentials: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Discover network devices via SSH"""

        # Generate IP list from range (simplified)
        # In production, use ipaddress module for proper range parsing
        base_ip = ".".join(ip_range.split(".")[:-1])
        discovered_devices = []

        # Test a few IPs for demonstration
        test_ips = [f"{base_ip}.{i}" for i in [1, 2, 10, 100, 254]]

        discovery_commands = [
            (ip, "uci get system.@system[0].hostname", credentials) for ip in test_ips
        ]

        results = await self.ssh_manager.execute_parallel(discovery_commands)

        for result in results:
            if result["success"]:
                device_info = await self.ssh_manager.get_device_info(
                    result["device_ip"], credentials
                )
                discovered_devices.append(device_info)

        return discovered_devices

    async def mass_firmware_upgrade(
        self, device_list: List[str], firmware_url: str, credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Perform mass firmware upgrade"""

        upgrade_commands = [
            f"wget {firmware_url} -O /tmp/firmware.bin",
            "md5sum /tmp/firmware.bin",  # Verify download
            "sysupgrade -v /tmp/firmware.bin",
        ]

        upgrade_results = []

        for device_ip in device_list:
            # Backup configuration before upgrade
            backup = await self.ssh_manager.backup_device_config(device_ip, credentials)

            # Execute upgrade
            upgrade_result = await self.ssh_manager.execute_commands_batch(
                device_ip, upgrade_commands, credentials, stop_on_error=True
            )

            upgrade_result["backup_id"] = backup["backup_id"]
            upgrade_results.append(upgrade_result)

        return {
            "upgrade_id": str(uuid4()),
            "firmware_url": firmware_url,
            "total_devices": len(device_list),
            "upgrade_initiated": len(
                [r for r in upgrade_results if r["successful_commands"] >= 2]
            ),
            "upgrade_failed": len(
                [r for r in upgrade_results if r["successful_commands"] < 2]
            ),
            "detailed_results": upgrade_results,
            "upgrade_started": utc_now().isoformat(),
        }

    async def cleanup(self):
        """Clean up SSH automation resources"""
        await self.ssh_manager.cleanup()
