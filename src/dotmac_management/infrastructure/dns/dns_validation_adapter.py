"""
DNS Validation Adapter
Implementation of IDNSProvider for DNS validation and SSL checking
"""

import asyncio
import os
import socket
import ssl
from datetime import datetime
from typing import Any, Optional

import dns.exception
import dns.resolver
import httpx
from dotmac_shared.core.logging import get_logger

from dotmac.application import standard_exception_handler

from ..interfaces.dns_provider import (
    DNSValidationResult,
    IDNSProvider,
    SSLCertificateInfo,
)

logger = get_logger(__name__)


class DNSValidationAdapter(IDNSProvider):
    """
    DNS validation provider implementation.
    Provides DNS validation, SSL checking, and domain availability checking.
    """

    def __init__(self, config: Optional[dict[str, Any]] = None):
        self.config = config or {}
        self.base_domain: Optional[str] = None
        self.timeout: int = 10
        self.resolver: Optional[dns.resolver.Resolver] = None
        self._initialized = False

    @standard_exception_handler
    async def initialize(self) -> bool:
        """Initialize the DNS adapter"""
        try:
            if self._initialized:
                return True

            self.base_domain = self.config.get("base_domain") or os.getenv(
                "BASE_DOMAIN"
            )
            if not self.base_domain:
                logger.warning(
                    "Base domain not configured - subdomain validation may not work"
                )

            self.timeout = self.config.get("timeout", 10)

            # Initialize DNS resolver
            self.resolver = dns.resolver.Resolver()

            # Configure custom DNS servers if provided
            dns_servers = self.config.get("dns_servers")
            if dns_servers:
                self.resolver.nameservers = dns_servers
                logger.info(f"Using custom DNS servers: {dns_servers}")

            # Test DNS resolution
            if self.base_domain:
                health_result = await self.health_check()
                if not health_result.get("healthy", False):
                    logger.warning(
                        f"DNS health check failed: {health_result.get('error')}"
                    )

            self._initialized = True
            logger.info("✅ DNS validation adapter initialized")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize DNS adapter: {e}")
            return False

    @standard_exception_handler
    async def health_check(self) -> dict[str, Any]:
        """Check DNS provider health"""
        try:
            if not self.base_domain:
                return {
                    "healthy": True,
                    "status": "operational",
                    "message": "No base domain configured, DNS resolution available",
                }

            # Test DNS resolution of base domain
            start_time = datetime.utcnow()
            result = await self._resolve_domain_internal(self.base_domain, "A")
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            if result.get("success", False):
                return {
                    "healthy": True,
                    "status": "operational",
                    "response_time_ms": response_time,
                    "base_domain": self.base_domain,
                    "dns_servers": self.resolver.nameservers if self.resolver else [],
                }
            else:
                return {
                    "healthy": False,
                    "error": result.get("error", "DNS resolution failed"),
                    "status": "error",
                }

        except Exception as e:
            return {"healthy": False, "error": str(e), "status": "error"}

    @standard_exception_handler
    async def validate_subdomain_available(
        self, subdomain: str, base_domain: Optional[str] = None
    ) -> DNSValidationResult:
        """Check if subdomain is available for provisioning"""
        try:
            domain_to_check = base_domain or self.base_domain
            if not domain_to_check:
                return DNSValidationResult(
                    domain=subdomain, available=False, error="No base domain configured"
                )

            full_domain = f"{subdomain}.{domain_to_check}"
            logger.info(f"Validating subdomain availability: {full_domain}")

            # Check DNS resolution
            dns_result = await self._check_dns_exists(full_domain)

            # Check HTTP availability
            http_result = await self._check_http_exists(full_domain)

            # Determine availability
            is_available = not (dns_result["exists"] or http_result["exists"])

            result = DNSValidationResult(
                domain=full_domain,
                available=is_available,
                dns_exists=dns_result["exists"],
                http_responding=http_result.get("http_responding", False),
                https_responding=http_result.get("https_responding", False),
                details={
                    "dns_check": dns_result,
                    "http_check": http_result,
                    "subdomain": subdomain,
                    "base_domain": domain_to_check,
                },
            )

            if is_available:
                logger.info(f"✅ Subdomain available: {full_domain}")
            else:
                logger.info(f"❌ Subdomain unavailable: {full_domain}")

            return result

        except Exception as e:
            logger.error(f"Subdomain validation failed: {e}")
            return DNSValidationResult(
                domain=f"{subdomain}.{base_domain or 'unknown'}",
                available=False,
                error=str(e),
            )

    @standard_exception_handler
    async def validate_ssl_certificate(self, domain: str) -> SSLCertificateInfo:
        """Validate SSL certificate for domain"""
        try:
            logger.info(f"Validating SSL certificate for: {domain}")

            # Check if domain resolves first
            dns_result = await self._resolve_domain_internal(domain, "A")
            if not dns_result.get("success", False):
                return SSLCertificateInfo(
                    domain=domain, valid=False, error="Domain does not resolve"
                )

            # Get SSL certificate info
            ssl_info = await self._get_ssl_certificate_info(domain)

            if ssl_info.get("error"):
                return SSLCertificateInfo(
                    domain=domain, valid=False, error=ssl_info["error"]
                )

            # Parse certificate info
            expires_at = ssl_info.get("expires_at")
            is_valid = ssl_info.get("valid", False)

            days_until_expiry = None
            if expires_at:
                try:
                    expires_datetime = datetime.fromisoformat(
                        expires_at.replace("Z", "+00:00")
                    )
                    days_until_expiry = (expires_datetime - datetime.utcnow()).days
                except Exception:
                    pass

            return SSLCertificateInfo(
                domain=domain,
                valid=is_valid,
                issuer=ssl_info.get("issuer", ""),
                subject=ssl_info.get("subject", ""),
                expires_at=expires_at,
                days_until_expiry=days_until_expiry,
            )

        except Exception as e:
            logger.error(f"SSL validation failed for {domain}: {e}")
            return SSLCertificateInfo(domain=domain, valid=False, error=str(e))

    @standard_exception_handler
    async def resolve_domain(
        self, domain: str, record_type: str = "A"
    ) -> dict[str, Any]:
        """Resolve DNS domain"""
        return await self._resolve_domain_internal(domain, record_type)

    @standard_exception_handler
    async def check_dns_propagation(
        self, domain: str, expected_value: Optional[str] = None
    ) -> dict[str, Any]:
        """Check DNS propagation status"""
        try:
            logger.info(f"Checking DNS propagation for: {domain}")

            # Check A record propagation
            a_result = await self._resolve_domain_internal(domain, "A")

            if not a_result.get("success", False):
                return {
                    "propagated": False,
                    "domain": domain,
                    "expected_value": expected_value,
                    "error": a_result.get("error"),
                    "checked_at": datetime.utcnow().isoformat(),
                }

            # Check if the resolved value matches expected
            resolved_ips = a_result.get("addresses", [])
            propagated = (
                expected_value in resolved_ips
                if expected_value
                else len(resolved_ips) > 0
            )

            return {
                "propagated": propagated,
                "domain": domain,
                "expected_value": expected_value,
                "resolved_values": resolved_ips,
                "match": expected_value in resolved_ips if expected_value else None,
                "checked_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            return {
                "propagated": False,
                "error": str(e),
                "domain": domain,
                "checked_at": datetime.utcnow().isoformat(),
            }

    def get_supported_record_types(self) -> list[str]:
        """Get supported DNS record types"""
        return ["A", "AAAA", "CNAME", "MX", "TXT", "NS"]

    async def cleanup(self) -> bool:
        """Cleanup adapter resources"""
        try:
            self.resolver = None
            self._initialized = False
            logger.info("✅ DNS validation adapter cleanup complete")
            return True

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return False

    # Helper methods

    async def _check_dns_exists(self, domain: str) -> dict[str, Any]:
        """Check if domain has DNS records"""
        try:
            # Check A record
            a_result = await self._resolve_domain_internal(domain, "A")
            if a_result.get("success", False):
                return {
                    "exists": True,
                    "record_type": "A",
                    "addresses": a_result.get("addresses", []),
                }

            # Check CNAME record
            cname_result = await self._resolve_domain_internal(domain, "CNAME")
            if cname_result.get("success", False):
                return {
                    "exists": True,
                    "record_type": "CNAME",
                    "target": cname_result.get("target"),
                }

            return {"exists": False, "message": "No DNS records found"}

        except Exception as e:
            return {"exists": False, "error": str(e)}

    async def _check_http_exists(self, domain: str) -> dict[str, Any]:
        """Check if domain responds to HTTP requests"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                result = {
                    "http_responding": False,
                    "https_responding": False,
                    "http_status": None,
                    "https_status": None,
                    "exists": False,
                }

                # Try HTTPS first
                try:
                    response = await client.get(f"https://{domain}")
                    result["https_responding"] = True
                    result["https_status"] = response.status_code
                    result["exists"] = True
                except Exception:
                    pass

                # Try HTTP
                try:
                    response = await client.get(f"http://{domain}")
                    result["http_responding"] = True
                    result["http_status"] = response.status_code
                    result["exists"] = True
                except Exception:
                    pass

                return result

        except Exception:
            return {"exists": False}

    async def _resolve_domain_internal(
        self, domain: str, record_type: str
    ) -> dict[str, Any]:
        """Internal DNS resolution method"""
        try:
            if not self.resolver:
                return {"success": False, "error": "DNS resolver not initialized"}

            # Run DNS resolution in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, self._sync_resolve_domain, domain, record_type
            )

            return result

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _sync_resolve_domain(self, domain: str, record_type: str) -> dict[str, Any]:
        """Synchronous DNS resolution"""
        try:
            self.resolver.timeout = self.timeout
            self.resolver.lifetime = self.timeout

            if record_type == "A":
                answers = self.resolver.resolve(domain, "A")
                addresses = [str(answer) for answer in answers]
                return {"success": True, "addresses": addresses}

            elif record_type == "CNAME":
                answers = self.resolver.resolve(domain, "CNAME")
                target = str(answers[0]) if answers else None
                return {"success": True, "target": target}

            elif record_type == "MX":
                answers = self.resolver.resolve(domain, "MX")
                mx_records = [
                    {"priority": answer.preference, "host": str(answer.exchange)}
                    for answer in answers
                ]
                return {"success": True, "mx_records": mx_records}

            elif record_type == "TXT":
                answers = self.resolver.resolve(domain, "TXT")
                txt_records = [str(answer) for answer in answers]
                return {"success": True, "txt_records": txt_records}

            else:
                return {
                    "success": False,
                    "error": f"Unsupported record type: {record_type}",
                }

        except dns.resolver.NXDOMAIN:
            return {"success": False, "error": "Domain does not exist"}
        except dns.resolver.NoAnswer:
            return {"success": False, "error": f"No {record_type} record found"}
        except dns.resolver.Timeout:
            return {"success": False, "error": "DNS query timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _get_ssl_certificate_info(self, domain: str) -> dict[str, Any]:
        """Get SSL certificate information"""
        try:
            # Run SSL check in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._sync_get_ssl_info, domain)

            return result

        except Exception as e:
            return {"error": str(e), "valid": False}

    def _sync_get_ssl_info(self, domain: str) -> dict[str, Any]:
        """Synchronous SSL certificate check"""
        try:
            # Connect to domain on port 443
            context = ssl.create_default_context()

            with socket.create_connection((domain, 443), timeout=self.timeout) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert = ssock.getpeercert()

                    if not cert:
                        return {"error": "No certificate found", "valid": False}

                    # Parse certificate info
                    subject = dict(x[0] for x in cert.get("subject", []))
                    issuer = dict(x[0] for x in cert.get("issuer", []))

                    # Parse dates
                    not_before = datetime.strptime(
                        cert.get("notBefore"), "%b %d %H:%M:%S %Y %Z"
                    )
                    not_after = datetime.strptime(
                        cert.get("notAfter"), "%b %d %H:%M:%S %Y %Z"
                    )

                    # Check if certificate is currently valid
                    now = datetime.utcnow()
                    is_valid = not_before <= now <= not_after

                    return {
                        "valid": is_valid,
                        "subject": subject.get("commonName", domain),
                        "issuer": issuer.get("organizationName", "Unknown"),
                        "issued_at": not_before.isoformat() + "Z",
                        "expires_at": not_after.isoformat() + "Z",
                        "days_remaining": (not_after - now).days,
                        "serial_number": cert.get("serialNumber"),
                        "version": cert.get("version"),
                        "subject_alt_names": [
                            x[1] for x in cert.get("subjectAltName", [])
                        ],
                    }

        except socket.timeout:
            return {"error": "Connection timeout", "valid": False}
        except socket.gaierror:
            return {"error": "Domain resolution failed", "valid": False}
        except ssl.SSLError as e:
            return {"error": f"SSL error: {e}", "valid": False}
        except Exception as e:
            return {"error": str(e), "valid": False}
