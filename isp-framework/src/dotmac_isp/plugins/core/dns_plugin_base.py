"""
DNS Plugin Base Classes for DotMac Platform

Provides a plugin-based architecture for DNS automation that can be extended
with different DNS providers without hardcoding specific implementations.
"""

import asyncio
from abc import abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum

from .base import BasePlugin, PluginCategory, PluginInfo, PluginContext
from pydantic import BaseModel


class DNSRecordType(Enum):
    """DNS record types supported by plugins."""
    A = "A"
    AAAA = "AAAA"
    CNAME = "CNAME"
    TXT = "TXT"
    MX = "MX"
    NS = "NS"
    SOA = "SOA"


@dataclass 
class DNSRecord:
    """DNS record data structure."""
    name: str
    record_type: DNSRecordType
    content: str
    ttl: int = 300
    priority: Optional[int] = None  # For MX records


class DNSVerificationResult(BaseModel):
    """DNS domain verification result."""
    success: bool
    message: str
    records_found: List[str] = []
    records_missing: List[str] = []


class TenantDNSSetup(BaseModel):
    """Tenant DNS setup configuration."""
    tenant_id: str
    base_domain: str
    load_balancer_ip: str
    custom_domain: Optional[str] = None
    subdomains: List[str] = ["", "api", "customer", "billing", "support", "status"]


class DNSPlugin(BasePlugin):
    """
    Base class for DNS automation plugins.
    
    This allows different DNS providers to be plugged in:
    - Local BIND9 server
    - Docker-based DNS (CoreDNS, PowerDNS)
    - Cloud providers (if needed in future)
    - Custom internal DNS solutions
    """
    
    @property
    def plugin_info(self) -> PluginInfo:
        """Plugin information - override in implementations."""
        return PluginInfo(
            id="dns-base",
            name="DNS Base Plugin",
            version="1.0.0",
            description="Base class for DNS automation plugins",
            author="DotMac Platform",
            category=PluginCategory.NETWORK_AUTOMATION,
            supports_multi_tenant=True,
            supports_hot_reload=False,
            permissions_required=["dns:manage", "system:configure"]
        )

    @abstractmethod
    async def create_tenant_records(
        self, 
        setup: TenantDNSSetup,
        context: PluginContext
    ) -> Dict[str, bool]:
        """
        Create DNS records for a tenant.
        
        Args:
            setup: Tenant DNS setup configuration
            context: Plugin execution context
            
        Returns:
            Dict mapping domain names to success status
        """
        pass

    @abstractmethod
    async def delete_tenant_records(
        self,
        tenant_id: str,
        base_domain: str,
        context: PluginContext
    ) -> Dict[str, bool]:
        """
        Delete DNS records for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            base_domain: Base domain name
            context: Plugin execution context
            
        Returns:
            Dict mapping domain names to success status
        """
        pass

    @abstractmethod
    async def verify_domain_ownership(
        self,
        domain: str,
        context: PluginContext
    ) -> DNSVerificationResult:
        """
        Verify domain ownership using DNS challenge.
        
        Args:
            domain: Domain to verify
            context: Plugin execution context
            
        Returns:
            Verification result with details
        """
        pass

    @abstractmethod
    async def get_required_records(
        self,
        custom_domain: str,
        tenant_id: str,
        base_domain: str,
        context: PluginContext
    ) -> List[DNSRecord]:
        """
        Generate list of DNS records customer needs to create.
        
        Args:
            custom_domain: Customer's domain
            tenant_id: Tenant identifier  
            base_domain: Platform base domain
            context: Plugin execution context
            
        Returns:
            List of required DNS records
        """
        pass

    @abstractmethod
    async def health_check_domains(
        self,
        domains: List[str],
        context: PluginContext
    ) -> Dict[str, bool]:
        """
        Check health/availability of domains.
        
        Args:
            domains: List of domains to check
            context: Plugin execution context
            
        Returns:
            Dict mapping domains to health status
        """
        pass

    async def get_tenant_domains(
        self,
        tenant_id: str,
        base_domain: str
    ) -> List[str]:
        """
        Get standard list of subdomains for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            base_domain: Base domain name
            
        Returns:
            List of fully qualified domain names
        """
        subdomains = ["", "api", "customer", "billing", "support", "status"]
        return [
            f"{tenant_id}.{base_domain}" if not subdomain 
            else f"{subdomain}.{tenant_id}.{base_domain}"
            for subdomain in subdomains
        ]

    def create_verification_record(self, domain: str) -> DNSRecord:
        """
        Create verification TXT record for domain ownership.
        
        Args:
            domain: Domain to create verification record for
            
        Returns:
            DNS TXT record for verification
        """
        return DNSRecord(
            name=f"_dotmac-verify.{domain}",
            record_type=DNSRecordType.TXT,
            content="dotmac-domain-verification",
            ttl=300
        )


class LocalDNSPlugin(DNSPlugin):
    """
    Strategic DNS plugin that leverages existing local infrastructure.
    
    Uses the system's existing DNS setup:
    1. Checks for local BIND9 installation
    2. Falls back to hosts file management
    3. Can integrate with existing network infrastructure
    """

    @property
    def plugin_info(self) -> PluginInfo:
        return PluginInfo(
            id="local-dns",
            name="Local DNS Manager",
            version="1.0.0", 
            description="Manages DNS using local system infrastructure",
            author="DotMac Platform",
            category=PluginCategory.NETWORK_AUTOMATION,
            supports_multi_tenant=True,
            supports_hot_reload=True,
            permissions_required=["dns:manage", "system:configure", "file:write"]
        )

    async def initialize(self) -> None:
        """Initialize local DNS management."""
        self.api.logger.info("Initializing Local DNS Plugin")
        
        # Detect available DNS management options
        self.dns_method = await self._detect_dns_method()
        self.api.logger.info(f"Using DNS method: {self.dns_method}")

    async def _detect_dns_method(self) -> str:
        """
        Detect the best DNS management method for current system.
        
        Returns:
            DNS method identifier
        """
        methods = []
        
        # Check for BIND9
        try:
            proc = await asyncio.create_subprocess_exec(
                'which', 'named',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            if proc.returncode == 0:
                methods.append("bind9")
        except:
            pass
            
        # Check for systemd-resolved
        try:
            proc = await asyncio.create_subprocess_exec(
                'systemctl', 'is-active', 'systemd-resolved',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            if b'active' in stdout:
                methods.append("systemd-resolved")
        except:
            pass
            
        # Check for dnsmasq
        try:
            proc = await asyncio.create_subprocess_exec(
                'which', 'dnsmasq',
                stdout=asyncio.subprocess.PIPE, 
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            if proc.returncode == 0:
                methods.append("dnsmasq")
        except:
            pass
            
        # Always available fallback
        methods.append("hosts_file")
        
        # Return best available method
        if "bind9" in methods:
            return "bind9"
        elif "dnsmasq" in methods: 
            return "dnsmasq"
        elif "systemd-resolved" in methods:
            return "systemd-resolved"
        else:
            return "hosts_file"

    async def activate(self) -> None:
        """Activate DNS plugin."""
        self.api.logger.info(f"Activating Local DNS Plugin with method: {self.dns_method}")

    async def deactivate(self) -> None:
        """Deactivate DNS plugin."""
        self.api.logger.info("Deactivating Local DNS Plugin")

    async def cleanup(self) -> None:
        """Cleanup DNS plugin resources."""
        self.api.logger.info("Cleaning up Local DNS Plugin")

    async def create_tenant_records(
        self,
        setup: TenantDNSSetup,
        context: PluginContext
    ) -> Dict[str, bool]:
        """Create tenant DNS records using detected method."""
        self.api.logger.info(f"Creating DNS records for tenant {setup.tenant_id} using {self.dns_method}")
        
        if self.dns_method == "bind9":
            return await self._create_bind9_records(setup, context)
        elif self.dns_method == "dnsmasq":
            return await self._create_dnsmasq_records(setup, context) 
        elif self.dns_method == "systemd-resolved":
            return await self._create_systemd_resolved_records(setup, context)
        else:
            return await self._create_hosts_file_records(setup, context)

    async def _create_bind9_records(
        self,
        setup: TenantDNSSetup,
        context: PluginContext
    ) -> Dict[str, bool]:
        """Create records using BIND9."""
        # Import the existing BIND9 provider logic here
        from ..dns_providers.bind9_provider import Bind9Provider
        
        provider = Bind9Provider()
        return provider.create_tenant_records(setup.tenant_id, setup.load_balancer_ip)

    async def _create_hosts_file_records(
        self,
        setup: TenantDNSSetup, 
        context: PluginContext
    ) -> Dict[str, bool]:
        """Create records using /etc/hosts file (local development)."""
        hosts_file = "/etc/hosts"
        results = {}
        
        try:
            domains = await self.get_tenant_domains(setup.tenant_id, setup.base_domain)
            
            # Read existing hosts file
            try:
                with open(hosts_file, 'r') as f:
                    content = f.read()
            except FileNotFoundError:
                content = ""
                
            # Add tenant section
            content += f"\n# DotMac Tenant: {setup.tenant_id}\n"
            for domain in domains:
                content += f"{setup.load_balancer_ip} {domain}\n"
                results[domain] = True
                
            # Write back (requires sudo/root)
            with open(hosts_file, 'w') as f:
                f.write(content)
                
            self.api.logger.info(f"Added {len(domains)} DNS entries to {hosts_file}")
            
        except PermissionError:
            self.api.logger.warning(f"Cannot write to {hosts_file} - insufficient permissions")
            # Fallback: create local hosts file for development
            local_hosts = f"/tmp/dotmac-hosts-{setup.tenant_id}"
            domains = await self.get_tenant_domains(setup.tenant_id, setup.base_domain)
            
            with open(local_hosts, 'w') as f:
                f.write(f"# DotMac Local DNS for tenant {setup.tenant_id}\n")
                for domain in domains:
                    f.write(f"{setup.load_balancer_ip} {domain}\n")
                    results[domain] = True
                    
            self.api.logger.info(f"Created local hosts file: {local_hosts}")
            
        except Exception as e:
            self.api.logger.error(f"Failed to create hosts file records: {e}")
            for domain in await self.get_tenant_domains(setup.tenant_id, setup.base_domain):
                results[domain] = False
                
        return results

    # Additional methods would be implemented for other DNS backends...
    # _create_dnsmasq_records, _create_systemd_resolved_records, etc.

    async def delete_tenant_records(
        self,
        tenant_id: str,
        base_domain: str,
        context: PluginContext
    ) -> Dict[str, bool]:
        """Delete tenant DNS records."""
        # Implementation would depend on the DNS method
        self.api.logger.info(f"Deleting DNS records for tenant {tenant_id}")
        return {}

    async def verify_domain_ownership(
        self,
        domain: str,
        context: PluginContext
    ) -> DNSVerificationResult:
        """Verify domain ownership using DNS lookup."""
        import dns.resolver
        
        verification_record = f"_dotmac-verify.{domain}"
        expected_value = "dotmac-domain-verification"
        
        try:
            resolver = dns.resolver.Resolver()
            resolver.timeout = 10
            
            answers = resolver.resolve(verification_record, 'TXT')
            found_records = []
            
            for rdata in answers:
                txt_content = str(rdata).strip('"')
                found_records.append(txt_content)
                
                if expected_value in txt_content:
                    return DNSVerificationResult(
                        success=True,
                        message=f"Domain ownership verified for {domain}",
                        records_found=found_records
                    )
                    
            return DNSVerificationResult(
                success=False,
                message=f"Verification record not found. Expected: {expected_value}",
                records_found=found_records,
                records_missing=[f"{verification_record} TXT {expected_value}"]
            )
            
        except Exception as e:
            return DNSVerificationResult(
                success=False,
                message=f"DNS verification failed: {str(e)}",
                records_missing=[f"{verification_record} TXT {expected_value}"]
            )

    async def get_required_records(
        self,
        custom_domain: str,
        tenant_id: str,
        base_domain: str,
        context: PluginContext
    ) -> List[DNSRecord]:
        """Generate required DNS records for customer setup."""
        target_domain = f"{tenant_id}.{base_domain}"
        
        return [
            self.create_verification_record(custom_domain),
            DNSRecord(
                name=custom_domain,
                record_type=DNSRecordType.CNAME,
                content=target_domain,
                ttl=300
            ),
            DNSRecord(
                name=f"api.{custom_domain}",
                record_type=DNSRecordType.CNAME,
                content=f"api.{target_domain}",
                ttl=300
            ),
            DNSRecord(
                name=f"billing.{custom_domain}",
                record_type=DNSRecordType.CNAME,
                content=f"billing.{target_domain}",
                ttl=300
            )
        ]

    async def health_check_domains(
        self,
        domains: List[str],
        context: PluginContext
    ) -> Dict[str, bool]:
        """Check domain health using DNS resolution."""
        import dns.resolver
        
        results = {}
        resolver = dns.resolver.Resolver()
        
        for domain in domains:
            try:
                answers = resolver.resolve(domain, 'A')
                results[domain] = len(answers) > 0
            except:
                results[domain] = False
                
        return results