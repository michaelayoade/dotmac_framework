"""Ansible client for playbook execution and management."""

import asyncio
import json
import os
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import subprocess
import yaml
import logging

from dotmac_isp.integrations.ansible.models import (
    AnsiblePlaybook,
    PlaybookExecution,
    DeviceInventory,
    ExecutionStatus,
    PlaybookType,
, timezone)


logger = logging.getLogger(__name__)


class AnsibleExecutionError(Exception):
    """Exception raised when Ansible execution fails."""

    def __init__(self, message: str, return_code: int = None, stderr: str = None):
        """  Init   operation."""
        super().__init__(message)
        self.return_code = return_code
        self.stderr = stderr


class AnsibleClient:
    """Client for executing Ansible playbooks and managing automation."""

    def __init__(
        self,
        ansible_config: Optional[Dict[str, Any]] = None,
        working_directory: Optional[str] = None,
        vault_password_file: Optional[str] = None,
    ):
        """Initialize Ansible client.

        Args:
            ansible_config: Ansible configuration options
            working_directory: Working directory for playbook execution
            vault_password_file: Path to Ansible vault password file
        """
        self.config = ansible_config or {}
        self.working_directory = working_directory or tempfile.gettempdir()
        self.vault_password_file = vault_password_file

        # Ensure working directory exists
        os.makedirs(self.working_directory, exist_ok=True)

        # Default Ansible configuration
        self.default_config = {
            "host_key_checking": False,
            "stdout_callback": "json",
            "callback_whitelist": "profile_tasks,timer",
            "gathering": "smart",
            "fact_caching": "memory",
            "pipelining": True,
            "ssh_args": "-o ControlMaster=auto -o ControlPersist=60s",
            "timeout": 30,
        }

    async def execute_playbook(
        self,
        playbook: AnsiblePlaybook,
        inventory_content: str,
        extra_vars: Optional[Dict[str, Any]] = None,
        limit_hosts: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        skip_tags: Optional[List[str]] = None,
        check_mode: bool = False,
        diff_mode: bool = False,
        verbose: int = 0,
    ) -> PlaybookExecution:
        """Execute an Ansible playbook.

        Args:
            playbook: Playbook to execute
            inventory_content: Inventory content as string
            extra_vars: Extra variables for playbook execution
            limit_hosts: Limit execution to specific hosts
            tags: Run only tasks with these tags
            skip_tags: Skip tasks with these tags
            check_mode: Run in check mode (dry run)
            diff_mode: Show diffs for changes
            verbose: Verbose level (0-4)

        Returns:
            PlaybookExecution: Execution result object
        """
        execution_id = str(uuid.uuid4()

        # Create execution record
        execution = PlaybookExecution(
            tenant_id=playbook.tenant_id,
            playbook_id=playbook.id,
            execution_id=execution_id,
            inventory_content=inventory_content,
            extra_variables=extra_vars,
            limit_hosts=limit_hosts,
            tags=tags,
            skip_tags=skip_tags,
            status=ExecutionStatus.PENDING,
            triggered_by="api",
        )

        try:
            # Create temporary files for playbook and inventory
            playbook_file = await self._create_playbook_file(playbook, execution_id)
            inventory_file = await self._create_inventory_file(
                inventory_content, execution_id
            )

            # Build ansible-playbook command
            cmd = await self._build_playbook_command(
                playbook_file=playbook_file,
                inventory_file=inventory_file,
                extra_vars=extra_vars,
                limit_hosts=limit_hosts,
                tags=tags,
                skip_tags=skip_tags,
                check_mode=check_mode,
                diff_mode=diff_mode,
                verbose=verbose,
            )

            # Update execution status
            execution.status = ExecutionStatus.RUNNING
            execution.started_at = datetime.now(timezone.utc)

            logger.info(f"Starting playbook execution: {execution_id}")

            # Execute the playbook
            result = await self._run_ansible_command(cmd, execution_id)

            # Parse execution results
            await self._parse_execution_results(execution, result)

            # Update playbook statistics
            await self._update_playbook_stats(playbook, execution)

            logger.info(
                f"Completed playbook execution: {execution_id} with status: {execution.status}"
            )

        except Exception as e:
            execution.status = ExecutionStatus.FAILED
            execution.stderr_log = str(e)
            logger.error(f"Playbook execution failed: {execution_id}, error: {e}")
            raise AnsibleExecutionError(f"Playbook execution failed: {e}")

        finally:
            execution.completed_at = datetime.now(timezone.utc)
            if execution.started_at:
                duration = execution.completed_at - execution.started_at
                execution.duration_seconds = int(duration.total_seconds()

            # Cleanup temporary files
            await self._cleanup_execution_files(execution_id)

        return execution

    async def validate_playbook(self, playbook_content: str) -> Tuple[bool, List[str]]:
        """Validate Ansible playbook syntax.

        Args:
            playbook_content: Playbook content to validate

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        try:
            # Parse YAML syntax
            yaml.safe_load(playbook_content)

            # Create temporary playbook file
            temp_file = os.path.join(
                self.working_directory, f"validate_{uuid.uuid4()}.yml"
            )

            with open(temp_file, "w") as f:
                f.write(playbook_content)

            # Run ansible-playbook syntax check
            cmd = ["ansible-playbook", "--syntax-check", temp_file]

            result = await self._run_command(cmd)

            if result.returncode != 0:
                errors.append(f"Syntax check failed: {result.stderr}")

            # Cleanup
            os.unlink(temp_file)

        except yaml.YAMLError as e:
            errors.append(f"YAML syntax error: {e}")
        except Exception as e:
            errors.append(f"Validation error: {e}")

        return len(errors) == 0, errors

    async def validate_inventory(
        self, inventory_content: str
    ) -> Tuple[bool, List[str]]:
        """Validate Ansible inventory.

        Args:
            inventory_content: Inventory content to validate

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        try:
            # Create temporary inventory file
            temp_file = os.path.join(
                self.working_directory, f"inventory_{uuid.uuid4()}.ini"
            )

            with open(temp_file, "w") as f:
                f.write(inventory_content)

            # Run ansible-inventory to validate
            cmd = ["ansible-inventory", "--inventory", temp_file, "--list", "--export"]

            result = await self._run_command(cmd)

            if result.returncode != 0:
                errors.append(f"Inventory validation failed: {result.stderr}")

            # Cleanup
            os.unlink(temp_file)

        except Exception as e:
            errors.append(f"Inventory validation error: {e}")

        return len(errors) == 0, errors

    async def get_inventory_hosts(self, inventory_content: str) -> List[Dict[str, Any]]:
        """Get hosts from inventory.

        Args:
            inventory_content: Inventory content

        Returns:
            List of hosts with their variables
        """
        hosts = []

        try:
            # Create temporary inventory file
            temp_file = os.path.join(
                self.working_directory, f"inventory_{uuid.uuid4()}.ini"
            )

            with open(temp_file, "w") as f:
                f.write(inventory_content)

            # Get inventory information
            cmd = ["ansible-inventory", "--inventory", temp_file, "--list"]

            result = await self._run_command(cmd)

            if result.returncode == 0:
                inventory_data = json.loads(result.stdout)

                # Extract hosts information
                for group_name, group_data in inventory_data.items():
                    if group_name == "_meta":
                        continue

                    if "hosts" in group_data:
                        for host in group_data["hosts"]:
                            host_vars = (
                                inventory_data.get("_meta", {})
                                .get("hostvars", {})
                                .get(host, {})
                            )
                            hosts.append(
                                {
                                    "hostname": host,
                                    "group": group_name,
                                    "variables": host_vars,
                                }
                            )

            # Cleanup
            os.unlink(temp_file)

        except Exception as e:
            logger.error(f"Failed to get inventory hosts: {e}")

        return hosts

    async def _create_playbook_file(
        self, playbook: AnsiblePlaybook, execution_id: str
    ) -> str:
        """Create temporary playbook file."""
        filename = f"playbook_{execution_id}.yml"
        filepath = os.path.join(self.working_directory, filename)

        with open(filepath, "w") as f:
            f.write(playbook.playbook_content)

        return filepath

    async def _create_inventory_file(
        self, inventory_content: str, execution_id: str
    ) -> str:
        """Create temporary inventory file."""
        filename = f"inventory_{execution_id}.ini"
        filepath = os.path.join(self.working_directory, filename)

        with open(filepath, "w") as f:
            f.write(inventory_content)

        return filepath

    async def _create_config_file(self, execution_id: str) -> str:
        """Create Ansible configuration file."""
        filename = f"ansible_{execution_id}.cfg"
        filepath = os.path.join(self.working_directory, filename)

        config = {**self.default_config, **self.config}

        config_content = "[defaults]\n"
        for key, value in config.items():
            config_content += f"{key} = {value}\n"

        with open(filepath, "w") as f:
            f.write(config_content)

        return filepath

    async def _build_playbook_command(
        self,
        playbook_file: str,
        inventory_file: str,
        extra_vars: Optional[Dict[str, Any]] = None,
        limit_hosts: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        skip_tags: Optional[List[str]] = None,
        check_mode: bool = False,
        diff_mode: bool = False,
        verbose: int = 0,
    ) -> List[str]:
        """Build ansible-playbook command."""
        cmd = ["ansible-playbook"]

        # Add inventory
        cmd.extend(["--inventory", inventory_file])

        # Add extra variables
        if extra_vars:
            cmd.extend(["--extra-vars", json.dumps(extra_vars)])

        # Add host limit
        if limit_hosts:
            cmd.extend(["--limit", ",".join(limit_hosts)])

        # Add tags
        if tags:
            cmd.extend(["--tags", ",".join(tags)])

        if skip_tags:
            cmd.extend(["--skip-tags", ",".join(skip_tags)])

        # Add execution modes
        if check_mode:
            cmd.append("--check")

        if diff_mode:
            cmd.append("--diff")

        # Add verbosity
        if verbose > 0:
            cmd.append("-" + "v" * min(verbose, 4)

        # Add vault password file if provided
        if self.vault_password_file:
            cmd.extend(["--vault-password-file", self.vault_password_file])

        # Add playbook file
        cmd.append(playbook_file)

        return cmd

    async def _run_ansible_command(
        self, cmd: List[str], execution_id: str
    ) -> subprocess.CompletedProcess:
        """Run Ansible command with proper environment."""
        env = os.environ.model_copy()

        # Set Ansible configuration
        config_file = await self._create_config_file(execution_id)
        env["ANSIBLE_CONFIG"] = config_file

        # Set other environment variables
        env["ANSIBLE_FORCE_COLOR"] = "false"
        env["ANSIBLE_HOST_KEY_CHECKING"] = "false"
        env["ANSIBLE_STDOUT_CALLBACK"] = "json"

        logger.debug(f"Executing command: {' '.join(cmd)}")

        try:
            result = await self._run_command(
                cmd, env=env, timeout=3600
            )  # 1 hour timeout
            return result
        finally:
            # Cleanup config file
            if os.path.exists(config_file):
                os.unlink(config_file)

    async def _run_command(
        self,
        cmd: List[str],
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> subprocess.CompletedProcess:
        """Run system command asynchronously."""
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            cwd=self.working_directory,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )

            return subprocess.CompletedProcess(
                args=cmd,
                returncode=process.returncode,
                stdout=stdout.decode(),
                stderr=stderr.decode(),
            )

        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise AnsibleExecutionError("Command execution timed out")

    async def _parse_execution_results(
        self, execution: PlaybookExecution, result: subprocess.CompletedProcess
    ) -> None:
        """Parse Ansible execution results."""
        execution.return_code = result.returncode
        execution.stdout_log = result.stdout
        execution.stderr_log = result.stderr

        if result.returncode == 0:
            execution.status = ExecutionStatus.SUCCESS
        else:
            execution.status = ExecutionStatus.FAILED

        # Try to parse JSON output for detailed statistics
        try:
            if result.stdout:
                # Look for Ansible JSON output
                lines = result.stdout.split("\n")
                for line in lines:
                    if line.strip().startswith("{") and '"stats"' in line:
                        stats_data = json.loads(line)
                        if "stats" in stats_data:
                            await self._parse_stats(execution, stats_data["stats"])
                        if "plays" in stats_data:
                            await self._parse_plays(execution, stats_data["plays"])
                        break
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse Ansible JSON output: {e}")

    async def _parse_stats(
        self, execution: PlaybookExecution, stats: Dict[str, Any]
    ) -> None:
        """Parse Ansible execution statistics."""
        total_hosts = len(stats)
        successful_hosts = 0
        failed_hosts = 0
        unreachable_hosts = 0

        host_results = {}
        changed_hosts = []

        for host, host_stats in stats.items():
            host_results[host] = host_stats

            if host_stats.get("unreachable", 0) > 0:
                unreachable_hosts += 1
            elif host_stats.get("failures", 0) > 0:
                failed_hosts += 1
            else:
                successful_hosts += 1

            if host_stats.get("changed", 0) > 0:
                changed_hosts.append(host)

        execution.total_hosts = total_hosts
        execution.successful_hosts = successful_hosts
        execution.failed_hosts = failed_hosts
        execution.unreachable_hosts = unreachable_hosts
        execution.host_results = host_results
        execution.changed_hosts = changed_hosts

    async def _parse_plays(
        self, execution: PlaybookExecution, plays: List[Dict[str, Any]]
    ) -> None:
        """Parse Ansible play results."""
        task_results = []

        for play in plays:
            for task in play.get("tasks", []):
                task_results.append(
                    {
                        "name": task.get("task", {}).get("name", "Unknown"),
                        "hosts": task.get("hosts", {}),
                        "action": task.get("task", {}).get("action", "Unknown"),
                    }
                )

        execution.task_results = task_results

    async def _update_playbook_stats(
        self, playbook: AnsiblePlaybook, execution: PlaybookExecution
    ) -> None:
        """Update playbook execution statistics."""
        playbook.execution_count += 1
        playbook.last_executed = datetime.now(timezone.utc)

        # Calculate success rate (simplified)
        if execution.status == ExecutionStatus.SUCCESS:
            success_count = (
                playbook.success_rate * (playbook.execution_count - 1) / 100
            ) + 1
            playbook.success_rate = int(
                (success_count / playbook.execution_count) * 100
            )
        else:
            success_count = playbook.success_rate * (playbook.execution_count - 1) / 100
            playbook.success_rate = int(
                (success_count / playbook.execution_count) * 100
            )

    async def _cleanup_execution_files(self, execution_id: str) -> None:
        """Clean up temporary files created for execution."""
        patterns = [
            f"playbook_{execution_id}.yml",
            f"inventory_{execution_id}.ini",
            f"ansible_{execution_id}.cfg",
        ]

        for pattern in patterns:
            filepath = os.path.join(self.working_directory, pattern)
            if os.path.exists(filepath):
                try:
                    os.unlink(filepath)
                except OSError as e:
                    logger.warning(f"Failed to cleanup file {filepath}: {e}")

    def get_supported_modules(self) -> List[str]:
        """Get list of available Ansible modules."""
        # This would typically query ansible-doc or use ansible-core APIs
        # For now, return a basic list of common network modules
        return [
            "cisco.ios.ios_command",
            "cisco.ios.ios_config",
            "cisco.ios.ios_facts",
            "cisco.ios.ios_interfaces",
            "cisco.ios.ios_vlans",
            "arista.eos.eos_command",
            "arista.eos.eos_config",
            "arista.eos.eos_facts",
            "juniper.device.netconf",
            "juniper.device.config",
            "ansible.netcommon.net_ping",
            "ansible.netcommon.cli_command",
            "ansible.netcommon.cli_config",
        ]
