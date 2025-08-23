"""
Network Automation SDK - adapters: Ansible/AWX, NETCONF/RESTCONF/SSH
"""

from datetime import datetime
from dotmac_isp.sdks.core.datetime_utils import utc_now, utc_now_iso
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..core.exceptions import AutomationError


class NetworkAutomationService:
    """In-memory service for network automation operations."""

    def __init__(self):
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._playbooks: Dict[str, Dict[str, Any]] = {}
        self._inventories: Dict[str, Dict[str, Any]] = {}
        self._adapters: Dict[str, Dict[str, Any]] = {}

    async def register_adapter(self, **kwargs) -> Dict[str, Any]:
        """Register automation adapter."""
        adapter_id = kwargs.get("adapter_id") or str(uuid4())

        adapter = {
            "adapter_id": adapter_id,
            "adapter_name": kwargs["adapter_name"],
            "adapter_type": kwargs["adapter_type"],  # ansible, netconf, ssh, restconf
            "connection_params": kwargs.get("connection_params", {}),
            "capabilities": kwargs.get("capabilities", []),
            "status": kwargs.get("status", "active"),
            "created_at": utc_now().isoformat(),
        }

        self._adapters[adapter_id] = adapter
        return adapter

    async def create_playbook(self, **kwargs) -> Dict[str, Any]:
        """Create Ansible playbook."""
        playbook_id = kwargs.get("playbook_id") or str(uuid4())

        playbook = {
            "playbook_id": playbook_id,
            "playbook_name": kwargs["playbook_name"],
            "playbook_content": kwargs["playbook_content"],
            "variables": kwargs.get("variables", {}),
            "tags": kwargs.get("tags", []),
            "description": kwargs.get("description", ""),
            "version": kwargs.get("version", "1.0"),
            "status": kwargs.get("status", "active"),
            "created_at": utc_now().isoformat(),
            "updated_at": utc_now().isoformat(),
        }

        self._playbooks[playbook_id] = playbook
        return playbook

    async def create_inventory(self, **kwargs) -> Dict[str, Any]:
        """Create automation inventory."""
        inventory_id = kwargs.get("inventory_id") or str(uuid4())

        inventory = {
            "inventory_id": inventory_id,
            "inventory_name": kwargs["inventory_name"],
            "hosts": kwargs.get("hosts", {}),
            "groups": kwargs.get("groups", {}),
            "variables": kwargs.get("variables", {}),
            "description": kwargs.get("description", ""),
            "status": kwargs.get("status", "active"),
            "created_at": utc_now().isoformat(),
            "updated_at": utc_now().isoformat(),
        }

        self._inventories[inventory_id] = inventory
        return inventory

    async def execute_ansible_job(self, **kwargs) -> Dict[str, Any]:
        """Execute Ansible job."""
        job_id = kwargs.get("job_id") or str(uuid4())

        job = {
            "job_id": job_id,
            "job_name": kwargs.get("job_name", f"Job-{job_id[:8]}"),
            "job_type": "ansible",
            "playbook_id": kwargs.get("playbook_id"),
            "inventory_id": kwargs.get("inventory_id"),
            "extra_vars": kwargs.get("extra_vars", {}),
            "limit": kwargs.get("limit", ""),
            "tags": kwargs.get("tags", []),
            "skip_tags": kwargs.get("skip_tags", []),
            "timeout": kwargs.get("timeout", 3600),
            "status": "running",
            "started_at": utc_now().isoformat(),
            "output": [],
            "result": {},
        }

        self._jobs[job_id] = job

        # Simulate job execution
        try:
            # In real implementation, this would execute actual Ansible
            job["status"] = "successful"
            job["finished_at"] = utc_now().isoformat()
            job["result"] = {
                "changed": True,
                "failed": False,
                "ok": 1,
                "skipped": 0,
                "unreachable": 0,
            }
        except Exception as e:
            job["status"] = "failed"
            job["finished_at"] = utc_now().isoformat()
            job["error"] = str(e)

        return job

    async def execute_netconf_operation(self, **kwargs) -> Dict[str, Any]:
        """Execute NETCONF operation."""
        job_id = kwargs.get("job_id") or str(uuid4())

        job = {
            "job_id": job_id,
            "job_name": kwargs.get("job_name", f"NETCONF-{job_id[:8]}"),
            "job_type": "netconf",
            "device_id": kwargs["device_id"],
            "operation": kwargs["operation"],  # get-config, edit-config, rpc
            "config_data": kwargs.get("config_data", ""),
            "datastore": kwargs.get("datastore", "running"),
            "timeout": kwargs.get("timeout", 30),
            "status": "running",
            "started_at": utc_now().isoformat(),
            "output": "",
            "result": {},
        }

        self._jobs[job_id] = job

        # Simulate NETCONF operation
        try:
            job["status"] = "successful"
            job["finished_at"] = utc_now().isoformat()
            job["output"] = f"NETCONF {job['operation']} completed successfully"
            job["result"] = {"success": True}
        except Exception as e:
            job["status"] = "failed"
            job["finished_at"] = utc_now().isoformat()
            job["error"] = str(e)

        return job

    async def execute_ssh_command(self, **kwargs) -> Dict[str, Any]:
        """Execute SSH command."""
        job_id = kwargs.get("job_id") or str(uuid4())

        job = {
            "job_id": job_id,
            "job_name": kwargs.get("job_name", f"SSH-{job_id[:8]}"),
            "job_type": "ssh",
            "device_id": kwargs["device_id"],
            "commands": kwargs["commands"],
            "timeout": kwargs.get("timeout", 30),
            "status": "running",
            "started_at": utc_now().isoformat(),
            "output": [],
            "result": {},
        }

        self._jobs[job_id] = job

        # Simulate SSH execution
        try:
            for cmd in job["commands"]:
                job["output"].append(f"Executing: {cmd}")
                job["output"].append("Command completed successfully")

            job["status"] = "successful"
            job["finished_at"] = utc_now().isoformat()
            job["result"] = {"commands_executed": len(job["commands"])}
        except Exception as e:
            job["status"] = "failed"
            job["finished_at"] = utc_now().isoformat()
            job["error"] = str(e)

        return job


class NetworkAutomationSDK:
    """Minimal, reusable SDK for network automation."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._service = NetworkAutomationService()

    async def register_ansible_adapter(
        self,
        adapter_name: str,
        awx_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Register Ansible/AWX adapter."""
        connection_params = {
            "awx_url": awx_url,
            "username": username,
            "password": password,
        }

        adapter = await self._service.register_adapter(
            adapter_name=adapter_name,
            adapter_type="ansible",
            connection_params=connection_params,
            capabilities=["playbook_execution", "inventory_management"],
            **kwargs,
        )

        return {
            "adapter_id": adapter["adapter_id"],
            "adapter_name": adapter["adapter_name"],
            "adapter_type": adapter["adapter_type"],
            "capabilities": adapter["capabilities"],
            "status": adapter["status"],
            "created_at": adapter["created_at"],
        }

    async def register_netconf_adapter(
        self, adapter_name: str, default_port: int = 830, **kwargs
    ) -> Dict[str, Any]:
        """Register NETCONF adapter."""
        connection_params = {
            "default_port": default_port,
            "protocol": "netconf",
        }

        adapter = await self._service.register_adapter(
            adapter_name=adapter_name,
            adapter_type="netconf",
            connection_params=connection_params,
            capabilities=["get-config", "edit-config", "rpc"],
            **kwargs,
        )

        return {
            "adapter_id": adapter["adapter_id"],
            "adapter_name": adapter["adapter_name"],
            "adapter_type": adapter["adapter_type"],
            "capabilities": adapter["capabilities"],
            "status": adapter["status"],
            "created_at": adapter["created_at"],
        }

    async def create_ansible_playbook(
        self,
        playbook_name: str,
        playbook_content: str,
        variables: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create Ansible playbook."""
        playbook = await self._service.create_playbook(
            playbook_name=playbook_name,
            playbook_content=playbook_content,
            variables=variables or {},
            tags=tags or [],
            **kwargs,
        )

        return {
            "playbook_id": playbook["playbook_id"],
            "playbook_name": playbook["playbook_name"],
            "variables": playbook["variables"],
            "tags": playbook["tags"],
            "description": playbook["description"],
            "version": playbook["version"],
            "status": playbook["status"],
            "created_at": playbook["created_at"],
        }

    async def create_inventory(
        self,
        inventory_name: str,
        hosts: Dict[str, Any],
        groups: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create automation inventory."""
        inventory = await self._service.create_inventory(
            inventory_name=inventory_name, hosts=hosts, groups=groups or {}, **kwargs
        )

        return {
            "inventory_id": inventory["inventory_id"],
            "inventory_name": inventory["inventory_name"],
            "hosts": inventory["hosts"],
            "groups": inventory["groups"],
            "variables": inventory["variables"],
            "status": inventory["status"],
            "created_at": inventory["created_at"],
        }

    async def run_ansible_playbook(
        self,
        playbook_id: str,
        inventory_id: str,
        extra_vars: Optional[Dict[str, Any]] = None,
        limit: Optional[str] = None,
        tags: Optional[List[str]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Run Ansible playbook."""
        job = await self._service.execute_ansible_job(
            playbook_id=playbook_id,
            inventory_id=inventory_id,
            extra_vars=extra_vars or {},
            limit=limit,
            tags=tags or [],
            **kwargs,
        )

        return {
            "job_id": job["job_id"],
            "job_name": job["job_name"],
            "job_type": job["job_type"],
            "playbook_id": job["playbook_id"],
            "inventory_id": job["inventory_id"],
            "status": job["status"],
            "started_at": job["started_at"],
            "finished_at": job.get("finished_at"),
            "result": job["result"],
        }

    async def execute_netconf_get_config(
        self,
        device_id: str,
        datastore: str = "running",
        filter_xml: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Execute NETCONF get-config operation."""
        job = await self._service.execute_netconf_operation(
            device_id=device_id,
            operation="get-config",
            datastore=datastore,
            config_data=filter_xml or "",
            **kwargs,
        )

        return {
            "job_id": job["job_id"],
            "job_type": job["job_type"],
            "device_id": job["device_id"],
            "operation": job["operation"],
            "datastore": job["datastore"],
            "status": job["status"],
            "output": job["output"],
            "result": job["result"],
            "started_at": job["started_at"],
            "finished_at": job.get("finished_at"),
        }

    async def execute_netconf_edit_config(
        self,
        device_id: str,
        config_xml: str,
        datastore: str = "running",
        default_operation: str = "merge",
        **kwargs,
    ) -> Dict[str, Any]:
        """Execute NETCONF edit-config operation."""
        job = await self._service.execute_netconf_operation(
            device_id=device_id,
            operation="edit-config",
            config_data=config_xml,
            datastore=datastore,
            default_operation=default_operation,
            **kwargs,
        )

        return {
            "job_id": job["job_id"],
            "job_type": job["job_type"],
            "device_id": job["device_id"],
            "operation": job["operation"],
            "datastore": job["datastore"],
            "status": job["status"],
            "output": job["output"],
            "result": job["result"],
            "started_at": job["started_at"],
            "finished_at": job.get("finished_at"),
        }

    async def execute_ssh_commands(
        self, device_id: str, commands: List[str], timeout: int = 30, **kwargs
    ) -> Dict[str, Any]:
        """Execute SSH commands on device."""
        job = await self._service.execute_ssh_command(
            device_id=device_id, commands=commands, timeout=timeout, **kwargs
        )

        return {
            "job_id": job["job_id"],
            "job_type": job["job_type"],
            "device_id": job["device_id"],
            "commands": job["commands"],
            "status": job["status"],
            "output": job["output"],
            "result": job["result"],
            "started_at": job["started_at"],
            "finished_at": job.get("finished_at"),
        }

    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get automation job status."""
        job = self._service._jobs.get(job_id)
        if not job:
            raise AutomationError(f"Job not found: {job_id}")

        return {
            "job_id": job["job_id"],
            "job_name": job["job_name"],
            "job_type": job["job_type"],
            "status": job["status"],
            "started_at": job["started_at"],
            "finished_at": job.get("finished_at"),
            "result": job["result"],
            "error": job.get("error"),
        }

    async def cancel_job(self, job_id: str) -> Dict[str, Any]:
        """Cancel running automation job."""
        job = self._service._jobs.get(job_id)
        if not job:
            raise AutomationError(f"Job not found: {job_id}")

        if job["status"] not in ["running", "pending"]:
            raise AutomationError(f"Cannot cancel job in status: {job['status']}")

        job["status"] = "cancelled"
        job["finished_at"] = utc_now().isoformat()
        job["result"] = {"cancelled": True}

        return {
            "job_id": job_id,
            "status": "cancelled",
            "cancelled_at": job["finished_at"],
        }

    async def list_jobs(
        self, device_id: Optional[str] = None, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List automation jobs."""
        jobs = list(self._service._jobs.values())

        if device_id:
            jobs = [job for job in jobs if job.get("device_id") == device_id]

        if status:
            jobs = [job for job in jobs if job["status"] == status]

        return [
            {
                "job_id": job["job_id"],
                "job_name": job["job_name"],
                "job_type": job["job_type"],
                "device_id": job.get("device_id"),
                "status": job["status"],
                "started_at": job["started_at"],
                "finished_at": job.get("finished_at"),
            }
            for job in sorted(jobs, key=lambda j: j["started_at"], reverse=True)
        ]
