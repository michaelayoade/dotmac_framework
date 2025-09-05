"""
CoreDNS Provider - Modern Kubernetes-Native DNS
File-based or etcd-backed DNS with simple management
"""

import logging
from pathlib import Path

import aiofiles

logger = logging.getLogger(__name__)


class CoreDNSProvider:
    """CoreDNS provider using hosts plugin or etcd backend"""

    def __init__(self):
        self.hosts_file = "/etc/coredns/hosts"
        self.base_domain = "dotmac.io"
        self.load_balancer_ip = "127.0.0.1"

    async def create_tenant_records(self, tenant_id: str) -> dict[str, bool]:
        """Add tenant records to CoreDNS hosts file"""
        try:
            records = [
                f"{self.load_balancer_ip} {tenant_id}.{self.base_domain}",
                f"{self.load_balancer_ip} customer.{tenant_id}.{self.base_domain}",
                f"{self.load_balancer_ip} api.{tenant_id}.{self.base_domain}",
                f"{self.load_balancer_ip} billing.{tenant_id}.{self.base_domain}",
                f"{self.load_balancer_ip} support.{tenant_id}.{self.base_domain}",
            ]

            # Read existing hosts file
            hosts_content = ""
            if Path(self.hosts_file).exists():
                async with aiofiles.open(self.hosts_file, "r") as f:
                    hosts_content = await f.read()

            # Add tenant section
            hosts_content += f"\n# Tenant records for {tenant_id}\n"
            for record in records:
                hosts_content += record + "\n"

            # Write updated hosts file
            async with aiofiles.open(self.hosts_file, "w") as f:
                await f.write(hosts_content)

            # Signal CoreDNS to reload (if using file plugin with auto-reload)
            logger.info(f"✅ Added CoreDNS records for tenant: {tenant_id}")
            return {f"{tenant_id}.{self.base_domain}": True}

        except Exception as e:
            logger.error(f"❌ Failed to add CoreDNS records for {tenant_id}: {e}")
            return {f"{tenant_id}.{self.base_domain}": False}

    def generate_corefile(self, tenants: list[str]) -> str:
        """Generate CoreDNS Corefile configuration"""
        corefile = f"""# CoreDNS Configuration for DotMac Platform

{self.base_domain}:53 {{
    # Enable hosts file for tenant records
    hosts {self.hosts_file} {{
        fallthrough
    }}

    # Forward to upstream DNS
    forward . 8.8.8.8 8.8.4.4

    # Enable logging
    log

    # Enable errors
    errors

    # Cache responses
    cache 30

    # Enable reload
    reload

    # Prometheus metrics
    prometheus :9153
}}

# Health check endpoint
.:9153 {{
    health
    prometheus
}}
"""
        return corefile
