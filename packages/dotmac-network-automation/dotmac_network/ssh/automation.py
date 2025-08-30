"""
SSH automation for network device management.
"""

import asyncio
import logging
import socket
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import paramiko

from .types import (
    CommandType,
    ConnectionStatus,
    DeviceCredentials,
    DeviceType,
    SSHAuthenticationError,
    SSHCommand,
    SSHCommandError,
    SSHConnection,
    SSHConnectionConfig,
    SSHConnectionError,
    SSHException,
    SSHResponse,
    SSHTimeoutError,
)

logger = logging.getLogger(__name__)


class SSHAutomation:
    """
    SSH automation engine for network device management.

    Provides high-level SSH operations including:
    - Secure connection management
    - Command execution with error handling
    - Multi-device operations
    - Session persistence and reuse
    """

    def __init__(self):
        self._connections: Dict[str, paramiko.SSHClient] = {}
        self._connection_info: Dict[str, SSHConnection] = {}

        # Configure paramiko logging
        paramiko.util.log_to_file("/dev/null", level=logging.ERROR)

    async def connect(
        self,
        host: str,
        credentials: DeviceCredentials,
        config: Optional[SSHConnectionConfig] = None,
        device_type: DeviceType = DeviceType.UNKNOWN,
    ) -> SSHConnection:
        """
        Establish SSH connection to device.

        Args:
            host: Target hostname or IP address
            credentials: Authentication credentials
            config: Connection configuration
            device_type: Type of network device

        Returns:
            SSHConnection object with connection details

        Raises:
            SSHConnectionError: Connection failed
            SSHAuthenticationError: Authentication failed
        """
        if not config:
            config = SSHConnectionConfig(host=host)

        connection_id = f"{host}:{config.port}:{credentials.username}"

        # Check if already connected
        if connection_id in self._connections:
            conn_info = self._connection_info[connection_id]
            if conn_info.status == ConnectionStatus.CONNECTED:
                conn_info.update_last_used()
                return conn_info

        # Create connection info
        conn_info = SSHConnection(
            connection_id=connection_id,
            host=host,
            port=config.port,
            username=credentials.username,
            device_type=device_type,
            status=ConnectionStatus.CONNECTING,
        )

        try:
            # Create SSH client
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # Configure connection parameters
            connect_kwargs = {
                "hostname": host,
                "port": config.port,
                "username": credentials.username,
                "timeout": config.timeout,
                "banner_timeout": config.banner_timeout,
                "auth_timeout": config.auth_timeout,
                "compress": config.compression,
            }

            # Add authentication method
            if credentials.has_key_auth():
                if credentials.private_key:
                    # Use private key string
                    from io import StringIO

                    key_file = StringIO(credentials.private_key)
                    private_key = paramiko.RSAKey.from_private_key(
                        key_file, password=credentials.passphrase
                    )
                    connect_kwargs["pkey"] = private_key
                elif credentials.private_key_path:
                    # Use private key file
                    connect_kwargs["key_filename"] = credentials.private_key_path
                    if credentials.passphrase:
                        connect_kwargs["passphrase"] = credentials.passphrase

            if credentials.has_password_auth():
                connect_kwargs["password"] = credentials.password

            # Establish connection
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: ssh_client.connect(**connect_kwargs)
            )

            # Test connection
            await self._test_connection(ssh_client)

            # Store connection
            self._connections[connection_id] = ssh_client
            conn_info.status = ConnectionStatus.CONNECTED
            conn_info.update_last_used()
            self._connection_info[connection_id] = conn_info

            logger.info(f"SSH connection established to {host}:{config.port}")
            return conn_info

        except paramiko.AuthenticationException as e:
            conn_info.record_error(f"Authentication failed: {e}")
            raise SSHAuthenticationError(host, credentials.username, str(e))

        except (paramiko.SSHException, socket.error, OSError) as e:
            conn_info.record_error(f"Connection failed: {e}")
            raise SSHConnectionError(host, config.port, str(e))

        except Exception as e:
            conn_info.record_error(f"Unexpected error: {e}")
            raise SSHConnectionError(host, config.port, f"Unexpected error: {e}")

    async def disconnect(self, connection_id: str) -> bool:
        """
        Disconnect SSH session.

        Args:
            connection_id: Connection identifier

        Returns:
            True if disconnection successful
        """
        if connection_id not in self._connections:
            return False

        try:
            ssh_client = self._connections[connection_id]
            await asyncio.get_event_loop().run_in_executor(None, ssh_client.close)

            # Update connection info
            if connection_id in self._connection_info:
                self._connection_info[connection_id].status = (
                    ConnectionStatus.DISCONNECTED
                )

            # Remove from active connections
            del self._connections[connection_id]

            logger.info(f"SSH connection {connection_id} disconnected")
            return True

        except Exception as e:
            logger.error(f"Error disconnecting {connection_id}: {e}")
            return False

    async def execute_command(
        self, connection_id: str, command: Union[str, SSHCommand], **kwargs
    ) -> SSHResponse:
        """
        Execute command on SSH connection.

        Args:
            connection_id: Connection identifier
            command: Command to execute
            **kwargs: Additional command parameters

        Returns:
            SSHResponse with command results

        Raises:
            SSHCommandError: Command execution failed
            SSHTimeoutError: Command timed out
        """
        if connection_id not in self._connections:
            raise SSHConnectionError("", 0, f"Connection {connection_id} not found")

        # Convert string to SSHCommand if needed
        if isinstance(command, str):
            command = SSHCommand(command=command, **kwargs)

        ssh_client = self._connections[connection_id]
        start_time = time.time()

        try:
            # Execute command based on type
            if command.command_type == CommandType.INTERACTIVE:
                return await self._execute_interactive_command(ssh_client, command)
            else:
                return await self._execute_simple_command(ssh_client, command)

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Command execution failed: {e}")

            return SSHResponse(
                command=command.command,
                output="",
                success=False,
                error_message=str(e),
                execution_time=execution_time,
            )

    async def _execute_simple_command(
        self, ssh_client: paramiko.SSHClient, command: SSHCommand
    ) -> SSHResponse:
        """Execute simple command."""
        start_time = time.time()

        try:
            # Execute command
            stdin, stdout, stderr = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: ssh_client.exec_command(
                    command.command, timeout=command.timeout
                ),
            )

            # Read output
            output_task = asyncio.get_event_loop().run_in_executor(None, stdout.read)
            error_task = asyncio.get_event_loop().run_in_executor(None, stderr.read)

            try:
                output_bytes, error_bytes = await asyncio.wait_for(
                    asyncio.gather(output_task, error_task), timeout=command.timeout
                )
            except asyncio.TimeoutError:
                raise SSHTimeoutError("command execution", command.timeout)

            # Decode output
            output = output_bytes.decode("utf-8", errors="ignore")
            error_output = error_bytes.decode("utf-8", errors="ignore")

            # Get exit code
            exit_code = stdout.channel.recv_exit_status()

            # Process output
            if command.strip_command and output.startswith(command.command):
                lines = output.split("\n")
                if lines and lines[0].strip() == command.command.strip():
                    output = "\n".join(lines[1:])

            if command.normalize:
                output = output.strip()

            execution_time = time.time() - start_time
            success = exit_code == 0 and not error_output

            response = SSHResponse(
                command=command.command,
                output=output,
                success=success,
                error_message=error_output if error_output else None,
                execution_time=execution_time,
                exit_code=exit_code,
            )

            # Apply TextFSM parsing if requested
            if command.use_textfsm and command.textfsm_template:
                response.structured_output = await self._parse_with_textfsm(
                    output, command.textfsm_template
                )

            return response

        except Exception as e:
            execution_time = time.time() - start_time
            raise SSHCommandError(command.command, str(e), "")

    async def _execute_interactive_command(
        self, ssh_client: paramiko.SSHClient, command: SSHCommand
    ) -> SSHResponse:
        """Execute interactive command with shell."""
        start_time = time.time()

        try:
            # Create interactive shell
            shell = ssh_client.invoke_shell()
            shell.settimeout(command.timeout)

            # Wait for initial prompt
            await asyncio.sleep(0.5)
            initial_output = shell.recv(4096).decode("utf-8", errors="ignore")

            # Send command
            shell.send(command.command + "\n")

            # Collect output
            output_parts = []
            loops = 0
            while loops < command.max_loops:
                try:
                    data = shell.recv(4096)
                    if not data:
                        break

                    output_parts.append(data.decode("utf-8", errors="ignore"))

                    # Check for expected prompt
                    if command.expect_prompt:
                        current_output = "".join(output_parts)
                        if command.expect_prompt in current_output:
                            break

                    await asyncio.sleep(command.delay_factor * 0.1)
                    loops += 1

                except socket.timeout:
                    break

            shell.close()

            output = "".join(output_parts)

            # Process output
            if command.strip_command and command.command in output:
                lines = output.split("\n")
                # Remove command line
                output_lines = []
                command_found = False
                for line in lines:
                    if not command_found and command.command.strip() in line:
                        command_found = True
                        continue
                    if command_found:
                        output_lines.append(line)
                output = "\n".join(output_lines)

            if command.strip_prompt and command.expect_prompt:
                output = output.replace(command.expect_prompt, "")

            if command.normalize:
                output = output.strip()

            execution_time = time.time() - start_time

            return SSHResponse(
                command=command.command,
                output=output,
                success=True,
                execution_time=execution_time,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            raise SSHCommandError(command.command, str(e), "")

    async def _parse_with_textfsm(
        self, output: str, template_path: str
    ) -> Optional[List[Dict[str, Any]]]:
        """Parse output using TextFSM template."""
        try:
            import textfsm

            from dotmac_shared.api.exception_handlers import standard_exception_handler

            with open(template_path, "r") as template_file:
                template = textfsm.TextFSM(template_file)
                parsed_result = template.ParseText(output)

                # Convert to list of dictionaries
                headers = template.header
                structured_data = []
                for row in parsed_result:
                    structured_data.append(dict(zip(headers, row)))

                return structured_data

        except ImportError:
            logger.warning("TextFSM not available for structured parsing")
            return None
        except Exception as e:
            logger.error(f"TextFSM parsing failed: {e}")
            return None

    async def _test_connection(self, ssh_client: paramiko.SSHClient):
        """Test SSH connection with simple command."""
        try:
            stdin, stdout, stderr = ssh_client.exec_command('echo "test"', timeout=5)
            output = stdout.read().decode("utf-8")
            if "test" not in output:
                raise SSHConnectionError("", 0, "Connection test failed")
        except Exception as e:
            raise SSHConnectionError("", 0, f"Connection test failed: {e}")

    async def execute_commands(
        self, connection_id: str, commands: List[Union[str, SSHCommand]]
    ) -> List[SSHResponse]:
        """
        Execute multiple commands sequentially.

        Args:
            connection_id: Connection identifier
            commands: List of commands to execute

        Returns:
            List of SSHResponse objects
        """
        responses = []
        for command in commands:
            response = await self.execute_command(connection_id, command)
            responses.append(response)

            # Stop on first failure if command is required
            if not response.success and isinstance(command, SSHCommand):
                # Could add logic for required vs optional commands
                pass

        return responses

    def get_connection_info(self, connection_id: str) -> Optional[SSHConnection]:
        """Get connection information."""
        return self._connection_info.get(connection_id)

    def list_connections(self) -> List[SSHConnection]:
        """List all active connections."""
        return list(self._connection_info.values())

    async def disconnect_all(self):
        """Disconnect all SSH connections."""
        connection_ids = list(self._connections.keys())
        for connection_id in connection_ids:
            await self.disconnect(connection_id)

    @asynccontextmanager
    async def connection_context(
        self,
        host: str,
        credentials: DeviceCredentials,
        config: Optional[SSHConnectionConfig] = None,
        device_type: DeviceType = DeviceType.UNKNOWN,
    ):
        """Context manager for SSH connection lifecycle."""
        connection = None
        try:
            connection = await self.connect(host, credentials, config, device_type)
            yield connection
        finally:
            if connection:
                await self.disconnect(connection.connection_id)
