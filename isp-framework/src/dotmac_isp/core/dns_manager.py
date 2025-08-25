"""
DNS Management Service for Tenant Domain Automation

Plugin-based DNS automation system that can leverage:
- Local BIND9 installations
- System DNS infrastructure (dnsmasq, systemd-resolved)
- Development hosts file management
- Future extensibility for cloud providers via plugins
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from uuid import uuid4

from pydantic import BaseModel
from dotmac_isp.core.settings import get_settings
from dotmac_isp.plugins.core.dns_plugin_base import (
    DNSPlugin, 
    LocalDNSPlugin,
    TenantDNSSetup, 
    DNSVerificationResult,
    DNSRecord
)
from dotmac_isp.plugins.core.base import PluginContext, PluginAPI
from dotmac_isp.plugins.core.manager import PluginManager

logger = logging.getLogger(__name__)
settings = get_settings()


# DNS models are now imported from the plugin base
# This maintains backward compatibility while using the new plugin system


class DNSManager:
    """
    Strategic DNS Management service using plugin architecture.
    
    Automatically detects and uses the best available DNS infrastructure:
    1. Local BIND9 server (production)
    2. System DNS services (dnsmasq, systemd-resolved)
    3. Hosts file management (development)
    4. Extensible for future cloud providers via plugins
    """
    
    def __init__(self):
        self.base_domain = getattr(settings, 'BASE_DOMAIN', 'dotmac.io')
        self.load_balancer_ip = getattr(settings, 'LOAD_BALANCER_IP', '127.0.0.1')
        
        # Initialize plugin system
        self.plugin_manager = None
        self.dns_plugin: Optional[DNSPlugin] = None
        
        # Setup plugin API with framework services
        self.api = PluginAPI({
            'logger': logger,
            'config': settings,
            'database': None,  # Would be injected in production
            'redis': None,     # Would be injected in production
            'event_bus': None  # Would be injected in production
        })
    
    async def initialize(self):
        """Initialize DNS management with plugin system."""
        try:
            # For now, use the local DNS plugin directly
            # In future, this could load plugins dynamically from config
            dns_plugin_config = {
                'enabled': True,
                'config_data': {
                    'base_domain': self.base_domain,
                    'load_balancer_ip': self.load_balancer_ip
                }
            }
            
            from dotmac_isp.plugins.core.models import PluginConfig
            config = PluginConfig(**dns_plugin_config)
            
            # Initialize the local DNS plugin
            self.dns_plugin = LocalDNSPlugin(config, self.api)
            await self.dns_plugin.initialize()
            await self.dns_plugin.activate()
            
            logger.info(f"✅ DNS Management initialized with plugin: {self.dns_plugin.plugin_info.name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize DNS management: {e}")
            return False
    
    async def create_tenant_subdomains(self, tenant_id: str, custom_domain: Optional[str] = None) -> Dict[str, bool]:
        """
        Create all required subdomains for a tenant using the active DNS plugin.
        
        Args:
            tenant_id: Unique tenant identifier
            custom_domain: Optional custom domain for the tenant
            
        Returns:
            Dictionary with subdomain creation results
        """
        if not self.dns_plugin:
            await self.initialize()
            if not self.dns_plugin:
                logger.error("No DNS plugin available")
                return {"error": "DNS service not available"}
        
        try:
            # Create tenant DNS setup configuration
            setup = TenantDNSSetup(
                tenant_id=tenant_id,
                base_domain=self.base_domain,
                load_balancer_ip=self.load_balancer_ip,
                custom_domain=custom_domain
            )
            
            # Create plugin context
            context = PluginContext(
                request_id=str(uuid4()),
                tenant_id=tenant_id
            )
            
            # Use plugin to create DNS records
            return await self.dns_plugin.create_tenant_records(setup, context)
                
        except Exception as e:
            logger.error(f"Error creating DNS records for {tenant_id}: {e}")
            return {"error": str(e)}
    
    async def delete_tenant_subdomains(self, tenant_id: str) -> Dict[str, bool]:
        """
        Delete all subdomains for a tenant using the active DNS plugin.
        
        Args:
            tenant_id: Unique tenant identifier
            
        Returns:
            Dictionary with subdomain deletion results
        """
        if not self.dns_plugin:
            await self.initialize()
            if not self.dns_plugin:
                logger.error("No DNS plugin available")
                return {"error": "DNS service not available"}
        
        try:
            context = PluginContext(
                request_id=str(uuid4()),
                tenant_id=tenant_id
            )
            
            return await self.dns_plugin.delete_tenant_records(
                tenant_id, 
                self.base_domain, 
                context
            )
                
        except Exception as e:
            logger.error(f"Error deleting DNS records for {tenant_id}: {e}")
            return {"error": str(e)}
    
    async def setup_custom_domain(self, custom_domain: str, tenant_id: str) -> Dict[str, Any]:
        """
        Setup custom domain for a tenant by providing required DNS records.
        
        Args:
            custom_domain: Customer's custom domain (e.g., portal.acmeisp.com)
            tenant_id: Tenant identifier
            
        Returns:
            Setup information including required DNS records
        """
        if not self.dns_plugin:
            await self.initialize()
            if not self.dns_plugin:
                return {"error": "DNS service not available"}
        
        try:
            context = PluginContext(
                request_id=str(uuid4()),
                tenant_id=tenant_id
            )
            
            # Get required DNS records for customer to create
            required_records = await self.dns_plugin.get_required_records(
                custom_domain,
                tenant_id, 
                self.base_domain,
                context
            )
            
            return {
                "success": True,
                "custom_domain": custom_domain,
                "target_domain": f"{tenant_id}.{self.base_domain}",
                "required_records": [
                    {
                        "name": record.name,
                        "type": record.record_type.value,
                        "content": record.content,
                        "ttl": record.ttl
                    } for record in required_records
                ],
                "instructions": f"Add these DNS records to {custom_domain} at your DNS provider"
            }
            
        except Exception as e:
            logger.error(f"Error setting up custom domain {custom_domain}: {e}")
            return {"error": str(e)}
    
    async def get_plugin_status(self) -> Dict[str, Any]:
        """
        Get status information about the active DNS plugin.
        
        Returns:
            Plugin status and health information
        """
        if not self.dns_plugin:
            return {
                "plugin_loaded": False,
                "error": "No DNS plugin loaded"
            }
        
        try:
            health = await self.dns_plugin.health_check()
            return {
                "plugin_loaded": True,
                "plugin_name": self.dns_plugin.plugin_info.name,
                "plugin_version": self.dns_plugin.plugin_info.version,
                "status": health.get("status"),
                "healthy": health.get("healthy"),
                "base_domain": self.base_domain,
                "load_balancer_ip": self.load_balancer_ip
            }
        except Exception as e:
            return {
                "plugin_loaded": True,
                "plugin_name": self.dns_plugin.plugin_info.name,
                "error": str(e)
            }
    
    async def verify_custom_domain_ownership(self, domain: str) -> DNSVerificationResult:
        """
        Verify domain ownership using DNS TXT record challenge via plugin.
        
        Args:
            domain: Domain to verify
            
        Returns:
            Verification result with details
        """
        if not self.dns_plugin:
            await self.initialize()
            if not self.dns_plugin:
                return DNSVerificationResult(
                    success=False,
                    message="DNS service not available"
                )
        
        try:
            context = PluginContext(
                request_id=str(uuid4())
            )
            
            return await self.dns_plugin.verify_domain_ownership(domain, context)
            
        except Exception as e:
            logger.error(f"DNS verification error for {domain}: {e}")
            return DNSVerificationResult(
                success=False,
                message=f"DNS verification failed: {str(e)}"
            )
    
    async def get_required_dns_records(self, custom_domain: str, tenant_id: str) -> List[Dict[str, Any]]:
        """
        Generate list of DNS records customer needs to create via plugin.
        
        Args:
            custom_domain: Customer's domain
            tenant_id: Tenant identifier
            
        Returns:
            List of required DNS records as dictionaries
        """
        if not self.dns_plugin:
            await self.initialize()
            if not self.dns_plugin:
                return []
        
        try:
            context = PluginContext(
                request_id=str(uuid4()),
                tenant_id=tenant_id
            )
            
            records = await self.dns_plugin.get_required_records(
                custom_domain,
                tenant_id,
                self.base_domain,
                context
            )
            
            # Convert to dictionary format for API responses
            return [
                {
                    "name": record.name,
                    "type": record.record_type.value,
                    "content": record.content,
                    "ttl": record.ttl
                } for record in records
            ]
            
        except Exception as e:
            logger.error(f"Error getting required DNS records: {e}")
            return []
    
    async def check_subdomain_health(self, tenant_id: str) -> Dict[str, bool]:
        """
        Check health of all tenant subdomains via plugin.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Health status for each subdomain
        """
        if not self.dns_plugin:
            await self.initialize()
            if not self.dns_plugin:
                return {}
        
        try:
            context = PluginContext(
                request_id=str(uuid4()),
                tenant_id=tenant_id
            )
            
            # Get tenant domains and check their health
            domains = await self.dns_plugin.get_tenant_domains(tenant_id, self.base_domain)
            return await self.dns_plugin.health_check_domains(domains, context)
            
        except Exception as e:
            logger.error(f"Error checking subdomain health for {tenant_id}: {e}")
            return {}


# Global DNS manager instance - lazy initialized
_dns_manager_instance = None

async def get_dns_manager() -> DNSManager:
    """Get global DNS manager instance with lazy initialization."""
    global _dns_manager_instance
    if _dns_manager_instance is None:
        _dns_manager_instance = DNSManager()
        await _dns_manager_instance.initialize()
    return _dns_manager_instance


async def create_tenant_dns(tenant_id: str, custom_domain: str = None) -> Dict:
    """
    Convenience function for tenant DNS setup using plugin system.
    
    Args:
        tenant_id: Unique tenant identifier
        custom_domain: Optional custom domain
        
    Returns:
        Setup results
    """
    dns_manager = await get_dns_manager()
    
    results = {
        "tenant_id": tenant_id,
        "subdomains_created": {},
        "custom_domain_setup": None,
        "verification_required": [],
        "plugin_info": {}
    }
    
    try:
        # Get plugin status for debugging
        plugin_status = await dns_manager.get_plugin_status()
        results["plugin_info"] = plugin_status
        
        # Create tenant subdomains
        subdomain_results = await dns_manager.create_tenant_subdomains(tenant_id, custom_domain)
        results["subdomains_created"] = subdomain_results
        
        # Handle custom domain if provided
        if custom_domain:
            custom_result = await dns_manager.setup_custom_domain(custom_domain, tenant_id)
            results["custom_domain_setup"] = custom_result
            
            # Get required DNS records for customer
            required_records = await dns_manager.get_required_dns_records(custom_domain, tenant_id)
            results["verification_required"] = required_records
        
        return results
        
    except Exception as e:
        logger.error(f"Error in create_tenant_dns: {e}")
        results["error"] = str(e)
        return results