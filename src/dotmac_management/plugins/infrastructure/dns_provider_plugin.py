"""
DNS Provider Plugin
Provides DNS validation and management using the plugin system
"""

import asyncio
import socket
import ssl
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

import httpx
import dns.resolver
import dns.exception

from dotmac_shared.core.logging import get_logger
from dotmac_shared.api.exception_handlers import standard_exception_handler

from ...core.plugins.base import PluginMeta, PluginType, PluginStatus, PluginError
from ...core.plugins.interfaces import DNSProviderPlugin

logger = get_logger(__name__)


class StandardDNSProviderPlugin(DNSProviderPlugin):
    """
    Standard DNS provider plugin using system DNS resolution.
    Provides DNS validation and basic management capabilities.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.base_domain: Optional[str] = None
        self.timeout: int = 10
        self.resolver: Optional[dns.resolver.Resolver] = None
    
    @property
    def meta(self) -> PluginMeta:
        return PluginMeta(
            name="StandardDNSProviderPlugin",
            version="1.0.0",
            plugin_type=PluginType.DNS_PROVIDER,
            description="Standard DNS validation and management using system DNS",
            author="DotMac",
            dependencies=[],
            configuration_schema={
                "type": "object",
                "properties": {
                    "base_domain": {"type": "string", "description": "Base domain for subdomain validation"},
                    "timeout": {"type": "integer", "description": "DNS query timeout in seconds", "default": 10},
                    "dns_servers": {"type": "array", "items": {"type": "string"}, "description": "Custom DNS servers"}
                },
                "required": ["base_domain"]
            },
            supported_features=["subdomain_validation", "ssl_validation", "dns_propagation_check"]
        )
    
    @standard_exception_handler
    async def initialize(self) -> bool:
        """Initialize the DNS plugin."""
        try:
            self.base_domain = self.config.get("base_domain") or os.getenv('BASE_DOMAIN')
            if not self.base_domain:
                raise PluginError("Base domain is required (base_domain in config or BASE_DOMAIN env var)")
            
            self.timeout = self.config.get("timeout", 10)
            
            # Initialize DNS resolver
            self.resolver = dns.resolver.Resolver()
            
            # Configure custom DNS servers if provided
            dns_servers = self.config.get("dns_servers")
            if dns_servers:
                self.resolver.nameservers = dns_servers
                self._logger.info(f"Using custom DNS servers: {dns_servers}")
            
            # Test DNS resolution
            health_result = await self.health_check()
            if not health_result.get("healthy", False):
                raise PluginError(f"DNS health check failed: {health_result.get('error')}")
            
            self.status = PluginStatus.ACTIVE
            self._logger.info(f"✅ DNS provider plugin initialized for domain: {self.base_domain}")
            return True
            
        except Exception as e:
            self.status = PluginStatus.ERROR
            self.last_error = e
            self._logger.error(f"Failed to initialize DNS plugin: {e}")
            return False
    
    @standard_exception_handler
    async def shutdown(self) -> bool:
        """Shutdown the plugin."""
        try:
            self.resolver = None
            self.status = PluginStatus.INACTIVE
            self._logger.info("✅ DNS provider plugin shutdown complete")
            return True
            
        except Exception as e:
            self._logger.error(f"Error during plugin shutdown: {e}")
            return False
    
    @standard_exception_handler
    async def health_check(self) -> Dict[str, Any]:
        """Check DNS provider health."""
        try:
            # Test DNS resolution of base domain
            start_time = datetime.now(timezone.utc)
            
            # Try to resolve the base domain
            result = await self._resolve_domain(self.base_domain, 'A')
            
            response_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            if result.get("success", False):
                return {
                    "healthy": True,
                    "status": "operational",
                    "response_time_ms": response_time,
                    "base_domain": self.base_domain,
                    "dns_servers": self.resolver.nameservers if self.resolver else []
                }
            else:
                return {
                    "healthy": False,
                    "error": result.get("error", "DNS resolution failed"),
                    "status": "error"
                }
                
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "status": "error"
            }
    
    # Implementation of DNSProviderPlugin interface methods
    
    @standard_exception_handler
    async def validate_subdomain_available(self, subdomain: str, base_domain: str = None) -> Dict[str, Any]:
        """Check if a subdomain is available for tenant provisioning."""
        try:
            domain_to_check = base_domain or self.base_domain
            full_domain = f"{subdomain}.{domain_to_check}"
            
            self._logger.info(f"Validating subdomain availability: {full_domain}")
            
            # Check DNS resolution
            dns_result = await self._check_dns_exists(full_domain)
            
            # Check HTTP availability
            http_result = await self._check_http_exists(full_domain)
            
            # Determine availability
            is_available = not (dns_result["exists"] or http_result["exists"])
            
            result = {
                "subdomain": subdomain,
                "full_domain": full_domain,
                "available": is_available,
                "dns_exists": dns_result["exists"],
                "http_exists": http_result["exists"],
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "details": {
                    "dns_check": dns_result,
                    "http_check": http_result
                }
            }
            
            if is_available:
                self._logger.info(f"✅ Subdomain available: {full_domain}")
            else:
                self._logger.info(f"❌ Subdomain unavailable: {full_domain}")
            
            return result
            
        except Exception as e:
            self._logger.error(f"Subdomain validation failed: {e}")
            return {
                "subdomain": subdomain,
                "available": False,
                "error": str(e),
                "checked_at": datetime.now(timezone.utc).isoformat()
            }
    
    @standard_exception_handler
    async def validate_ssl_certificate(self, domain: str) -> Dict[str, Any]:
        """Validate SSL certificate for domain."""
        try:
            self._logger.info(f"Validating SSL certificate for: {domain}")
            
            # Check if domain resolves
            dns_result = await self._resolve_domain(domain, 'A')
            if not dns_result.get("success", False):
                return {
                    "valid": False,
                    "error": "Domain does not resolve",
                    "domain": domain,
                    "checked_at": datetime.now(timezone.utc).isoformat()
                }
            
            # Check SSL certificate
            ssl_info = await self._get_ssl_certificate_info(domain)
            
            if ssl_info.get("error"):
                return {
                    "valid": False,
                    "error": ssl_info["error"],
                    "domain": domain,
                    "checked_at": datetime.now(timezone.utc).isoformat()
                }
            
            # Check if certificate is valid and not expired
            expires_at = ssl_info.get("expires_at")
            is_valid = ssl_info.get("valid", False)
            
            if expires_at:
                expires_datetime = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                days_until_expiry = (expires_datetime - datetime.now(timezone.utc)).days
                is_expiring_soon = days_until_expiry < 30
            else:
                days_until_expiry = None
                is_expiring_soon = False
            
            return {
                "valid": is_valid,
                "domain": domain,
                "certificate_info": ssl_info,
                "days_until_expiry": days_until_expiry,
                "expiring_soon": is_expiring_soon,
                "checked_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self._logger.error(f"SSL validation failed for {domain}: {e}")
            return {
                "valid": False,
                "error": str(e),
                "domain": domain,
                "checked_at": datetime.now(timezone.utc).isoformat()
            }
    
    @standard_exception_handler
    async def create_dns_record(self, domain: str, record_type: str, value: str, ttl: int = 300) -> Dict[str, Any]:
        """Create DNS record (not supported in standard DNS provider)."""
        # Standard DNS provider can't create records - this is read-only
        return {
            "success": False,
            "error": "DNS record creation not supported in standard DNS provider",
            "domain": domain,
            "record_type": record_type,
            "message": "Use a DNS management provider plugin (e.g., Cloudflare) for record creation"
        }
    
    @standard_exception_handler
    async def delete_dns_record(self, domain: str, record_id: str) -> bool:
        """Delete DNS record (not supported in standard DNS provider)."""
        return False
    
    @standard_exception_handler
    async def check_dns_propagation(self, domain: str, expected_value: str) -> Dict[str, Any]:
        """Check DNS propagation status."""
        try:
            self._logger.info(f"Checking DNS propagation for: {domain}")
            
            # Check A record propagation
            a_result = await self._resolve_domain(domain, 'A')
            
            if not a_result.get("success", False):
                return {
                    "propagated": False,
                    "domain": domain,
                    "expected_value": expected_value,
                    "error": a_result.get("error"),
                    "checked_at": datetime.now(timezone.utc).isoformat()
                }
            
            # Check if the resolved value matches expected
            resolved_ips = a_result.get("addresses", [])
            propagated = expected_value in resolved_ips if expected_value else len(resolved_ips) > 0
            
            return {
                "propagated": propagated,
                "domain": domain,
                "expected_value": expected_value,
                "resolved_values": resolved_ips,
                "match": expected_value in resolved_ips if expected_value else None,
                "checked_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {
                "propagated": False,
                "error": str(e),
                "domain": domain,
                "checked_at": datetime.now(timezone.utc).isoformat()
            }
    
    @standard_exception_handler
    async def get_ssl_certificate_info(self, domain: str) -> Dict[str, Any]:
        """Get SSL certificate information."""
        return await self._get_ssl_certificate_info(domain)
    
    def get_supported_record_types(self) -> List[str]:
        """Return supported DNS record types for validation."""
        return ["A", "AAAA", "CNAME", "MX", "TXT", "NS"]
    
    # Helper methods
    
    async def _check_dns_exists(self, domain: str) -> Dict[str, Any]:
        """Check if domain has DNS records."""
        try:
            # Check A record
            a_result = await self._resolve_domain(domain, 'A')
            if a_result.get("success", False):
                return {
                    "exists": True,
                    "record_type": "A",
                    "addresses": a_result.get("addresses", [])
                }
            
            # Check CNAME record
            cname_result = await self._resolve_domain(domain, 'CNAME')
            if cname_result.get("success", False):
                return {
                    "exists": True,
                    "record_type": "CNAME",
                    "target": cname_result.get("target")
                }
            
            return {"exists": False, "error": "No DNS records found"}
            
        except Exception as e:
            return {"exists": False, "error": str(e)}
    
    async def _check_http_exists(self, domain: str) -> Dict[str, Any]:
        """Check if domain responds to HTTP requests."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                try:
                    # Try HTTPS first
                    response = await client.get(f"https://{domain}")
                    return {
                        "exists": True,
                        "protocol": "https",
                        "status_code": response.status_code
                    }
                except:
                    # Try HTTP
                    try:
                        response = await client.get(f"http://{domain}")
                        return {
                            "exists": True,
                            "protocol": "http",
                            "status_code": response.status_code
                        }
                    except:
                        return {"exists": False}
                        
        except Exception:
            return {"exists": False}
    
    async def _resolve_domain(self, domain: str, record_type: str) -> Dict[str, Any]:
        """Resolve DNS domain."""
        try:
            if not self.resolver:
                return {"success": False, "error": "DNS resolver not initialized"}
            
            # Run DNS resolution in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._sync_resolve_domain, domain, record_type)
            
            return result
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _sync_resolve_domain(self, domain: str, record_type: str) -> Dict[str, Any]:
        """Synchronous DNS resolution."""
        try:
            self.resolver.timeout = self.timeout
            self.resolver.lifetime = self.timeout
            
            if record_type == 'A':
                answers = self.resolver.resolve(domain, 'A')
                addresses = [str(answer) for answer in answers]
                return {"success": True, "addresses": addresses}
            
            elif record_type == 'CNAME':
                answers = self.resolver.resolve(domain, 'CNAME')
                target = str(answers[0]) if answers else None
                return {"success": True, "target": target}
            
            elif record_type == 'MX':
                answers = self.resolver.resolve(domain, 'MX')
                mx_records = [{"priority": answer.preference, "host": str(answer.exchange)} for answer in answers]
                return {"success": True, "mx_records": mx_records}
            
            elif record_type == 'TXT':
                answers = self.resolver.resolve(domain, 'TXT')
                txt_records = [str(answer) for answer in answers]
                return {"success": True, "txt_records": txt_records}
            
            else:
                return {"success": False, "error": f"Unsupported record type: {record_type}"}
                
        except dns.resolver.NXDOMAIN:
            return {"success": False, "error": "Domain does not exist"}
        except dns.resolver.NoAnswer:
            return {"success": False, "error": f"No {record_type} record found"}
        except dns.resolver.Timeout:
            return {"success": False, "error": "DNS query timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _get_ssl_certificate_info(self, domain: str) -> Dict[str, Any]:
        """Get SSL certificate information."""
        try:
            # Run SSL check in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._sync_get_ssl_info, domain)
            
            return result
            
        except Exception as e:
            return {"error": str(e), "valid": False}
    
    def _sync_get_ssl_info(self, domain: str) -> Dict[str, Any]:
        """Synchronous SSL certificate check."""
        try:
            # Connect to domain on port 443
            context = ssl.create_default_context()
            
            with socket.create_connection((domain, 443), timeout=self.timeout) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert = ssock.getpeercert()
                    
                    if not cert:
                        return {"error": "No certificate found", "valid": False}
                    
                    # Parse certificate info
                    subject = dict(x[0] for x in cert.get('subject', []))
                    issuer = dict(x[0] for x in cert.get('issuer', []))
                    
                    # Parse dates
                    not_before = datetime.strptime(cert.get('notBefore'), '%b %d %H:%M:%S %Y %Z')
                    not_after = datetime.strptime(cert.get('notAfter'), '%b %d %H:%M:%S %Y %Z')
                    
                    # Check if certificate is currently valid
                    now = datetime.now(timezone.utc)
                    is_valid = not_before <= now <= not_after
                    
                    return {
                        "valid": is_valid,
                        "subject": subject.get('commonName', domain),
                        "issuer": issuer.get('organizationName', 'Unknown'),
                        "issued_at": not_before.isoformat() + 'Z',
                        "expires_at": not_after.isoformat() + 'Z',
                        "days_remaining": (not_after - now).days,
                        "serial_number": cert.get('serialNumber'),
                        "version": cert.get('version'),
                        "subject_alt_names": [x[1] for x in cert.get('subjectAltName', [])]
                    }
                    
        except socket.timeout:
            return {"error": "Connection timeout", "valid": False}
        except socket.gaierror:
            return {"error": "Domain resolution failed", "valid": False}
        except ssl.SSLError as e:
            return {"error": f"SSL error: {e}", "valid": False}
        except Exception as e:
            return {"error": str(e), "valid": False}