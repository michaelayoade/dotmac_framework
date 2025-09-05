"""
DNS and TLS validation utilities for tenant provisioning.
Validates domain availability and TLS certificate automation.
"""

import os
import socket
import ssl
from datetime import datetime, timezone
from typing import Any

import dns.exception
import dns.resolver
import httpx
from dotmac_shared.core.logging import get_logger

logger = get_logger(__name__)


class DNSValidator:
    """
    Validates DNS configuration and domain availability for tenant provisioning.
    """

    def __init__(self):
        self.base_domain = os.getenv("BASE_DOMAIN")
        if not self.base_domain:
            raise ValueError("BASE_DOMAIN environment variable is required")

        self.timeout = 10  # seconds

    async def validate_subdomain_available(self, subdomain: str) -> dict[str, Any]:
        """
        Check if a subdomain is available for tenant provisioning.

        Args:
            subdomain: The subdomain to check (e.g., 'demo' for 'demo.yourdomain.com')

        Returns:
            Dictionary with availability status and details
        """

        full_domain = f"{subdomain}.{self.base_domain}"

        try:
            logger.info(f"Validating subdomain availability: {full_domain}")

            # Check DNS resolution
            dns_exists = await self._check_dns_exists(full_domain)

            # Check HTTP/HTTPS response
            http_status = await self._check_http_response(full_domain)

            # Check SSL certificate (if HTTPS is responding)
            ssl_status = await self._check_ssl_certificate(full_domain) if http_status.get("https_responding") else None

            is_available = (
                not dns_exists["exists"]
                and not http_status.get("http_responding")
                and not http_status.get("https_responding")
            )

            return {
                "subdomain": subdomain,
                "full_domain": full_domain,
                "available": is_available,
                "dns_status": dns_exists,
                "http_status": http_status,
                "ssl_status": ssl_status,
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "message": "Domain is available" if is_available else "Domain is already in use",
            }

        except Exception as e:
            logger.error(f"Domain validation failed for {full_domain}: {e}")
            return {
                "subdomain": subdomain,
                "full_domain": full_domain,
                "available": False,
                "error": str(e),
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "message": "Validation failed - assuming domain unavailable for safety",
            }

    async def _check_dns_exists(self, domain: str) -> dict[str, Any]:
        """Check if DNS records exist for the domain"""

        try:
            resolver = dns.resolver.Resolver()
            resolver.timeout = self.timeout

            # Check A record
            try:
                answers = resolver.resolve(domain, "A")
                a_records = [str(answer) for answer in answers]
                logger.debug(f"Found A records for {domain}: {a_records}")
                return {"exists": True, "record_type": "A", "records": a_records}
            except dns.resolver.NXDOMAIN:
                pass
            except dns.resolver.NoAnswer:
                pass

            # Check CNAME record
            try:
                answers = resolver.resolve(domain, "CNAME")
                cname_records = [str(answer) for answer in answers]
                logger.debug(f"Found CNAME records for {domain}: {cname_records}")
                return {"exists": True, "record_type": "CNAME", "records": cname_records}
            except dns.resolver.NXDOMAIN:
                pass
            except dns.resolver.NoAnswer:
                pass

            # No records found
            logger.debug(f"No DNS records found for {domain}")
            return {"exists": False, "message": "No DNS records found"}

        except Exception as e:
            logger.error(f"DNS check failed for {domain}: {e}")
            return {"exists": False, "error": str(e), "message": "DNS check failed"}

    async def _check_http_response(self, domain: str) -> dict[str, Any]:
        """Check HTTP/HTTPS response from the domain"""

        result = {"http_responding": False, "https_responding": False, "http_status": None, "https_status": None}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Check HTTP
            try:
                response = await client.get(f"http://{domain}", follow_redirects=True)
                result["http_responding"] = True
                result["http_status"] = response.status_code
                logger.debug(f"HTTP response for {domain}: {response.status_code}")
            except Exception as e:
                logger.debug(f"HTTP check failed for {domain}: {e}")

            # Check HTTPS
            try:
                response = await client.get(f"https://{domain}", follow_redirects=True)
                result["https_responding"] = True
                result["https_status"] = response.status_code
                logger.debug(f"HTTPS response for {domain}: {response.status_code}")
            except Exception as e:
                logger.debug(f"HTTPS check failed for {domain}: {e}")

        return result

    async def _check_ssl_certificate(self, domain: str) -> dict[str, Any]:
        """Check SSL certificate status"""

        try:
            # Create SSL context
            context = ssl.create_default_context()

            # Connect and get certificate
            with socket.create_connection((domain, 443), timeout=self.timeout) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert = ssock.getpeercert()

                    # Parse certificate info
                    not_after = datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
                    not_before = datetime.strptime(cert["notBefore"], "%b %d %H:%M:%S %Y %Z")
                    now = datetime.now(timezone.utc)

                    days_until_expiry = (not_after - now).days

                    return {
                        "valid": True,
                        "issuer": dict(x[0] for x in cert["issuer"]),
                        "subject": dict(x[0] for x in cert["subject"]),
                        "not_before": not_before.isoformat(),
                        "not_after": not_after.isoformat(),
                        "days_until_expiry": days_until_expiry,
                        "expired": now > not_after,
                        "san": cert.get("subjectAltName", []),
                    }

        except Exception as e:
            logger.debug(f"SSL check failed for {domain}: {e}")
            return {"valid": False, "error": str(e), "message": "SSL certificate check failed"}

    async def validate_base_domain_config(self) -> dict[str, Any]:
        """
        Validate that the base domain is properly configured for tenant provisioning.
        """

        try:
            logger.info(f"Validating base domain configuration: {self.base_domain}")

            # Check if base domain resolves
            base_dns = await self._check_dns_exists(self.base_domain)

            # Check wildcard subdomain support (if possible)
            f"test-{int(datetime.now(timezone.utc).timestamp())}.{self.base_domain}"
            wildcard_dns = await self._check_dns_exists(f"*.{self.base_domain}")

            return {
                "base_domain": self.base_domain,
                "base_domain_dns": base_dns,
                "wildcard_dns_configured": wildcard_dns.get("exists", False),
                "ready_for_tenants": base_dns.get("exists", False),
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "recommendations": self._get_dns_recommendations(base_dns, wildcard_dns),
            }

        except Exception as e:
            logger.error(f"Base domain validation failed: {e}")
            return {
                "base_domain": self.base_domain,
                "error": str(e),
                "ready_for_tenants": False,
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "message": "Base domain validation failed",
            }

    def _get_dns_recommendations(self, base_dns: dict, wildcard_dns: dict) -> list[str]:
        """Get DNS configuration recommendations"""

        recommendations = []

        if not base_dns.get("exists"):
            recommendations.append(f"Configure DNS A record for {self.base_domain}")

        if not wildcard_dns.get("exists"):
            recommendations.append(f"Configure wildcard DNS (*.{self.base_domain}) for automatic tenant subdomains")

        recommendations.extend(
            [
                "Ensure Let's Encrypt or similar is configured for automatic SSL certificates",
                "Configure Coolify domain automation for tenant provisioning",
                "Test tenant provisioning in staging environment before production use",
            ]
        )

        return recommendations


class CoolifyDNSValidator:
    """
    Validates Coolify DNS and TLS automation configuration.
    """

    def __init__(self):
        self.coolify_url = os.getenv("COOLIFY_API_URL")
        self.coolify_token = os.getenv("COOLIFY_API_TOKEN")

        if not self.coolify_url or not self.coolify_token:
            raise ValueError("Coolify API configuration is required for DNS validation")

    async def validate_coolify_dns_config(self) -> dict[str, Any]:
        """
        Validate that Coolify is properly configured for automatic DNS/TLS.
        """

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # Check Coolify API connectivity
                response = await client.get(
                    f"{self.coolify_url}/api/v1/servers", headers={"Authorization": f"Bearer {self.coolify_token}"}
                )

                if response.status_code != 200:
                    raise Exception(f"Coolify API returned {response.status_code}")

                servers = response.json()

                # Check if any servers support automatic DNS
                dns_automation_available = any(
                    server.get("settings", {}).get("automatic_domain_creation", False) for server in servers
                )

                # Check SSL certificate automation
                ssl_automation_available = any(
                    server.get("settings", {}).get("lets_encrypt_enabled", False) for server in servers
                )

                return {
                    "coolify_accessible": True,
                    "server_count": len(servers),
                    "dns_automation": dns_automation_available,
                    "ssl_automation": ssl_automation_available,
                    "ready_for_tenants": dns_automation_available and ssl_automation_available,
                    "checked_at": datetime.now(timezone.utc).isoformat(),
                    "recommendations": self._get_coolify_recommendations(
                        dns_automation_available, ssl_automation_available
                    ),
                }

        except Exception as e:
            logger.error(f"Coolify DNS validation failed: {e}")
            return {
                "coolify_accessible": False,
                "error": str(e),
                "ready_for_tenants": False,
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "message": "Coolify DNS/TLS automation check failed",
            }

    def _get_coolify_recommendations(self, dns_auto: bool, ssl_auto: bool) -> list[str]:
        """Get Coolify configuration recommendations"""

        recommendations = []

        if not dns_auto:
            recommendations.append("Enable automatic domain creation in Coolify server settings")

        if not ssl_auto:
            recommendations.append("Enable Let's Encrypt SSL automation in Coolify server settings")

        recommendations.extend(
            [
                "Configure Coolify webhook endpoints for deployment notifications",
                "Set up monitoring for automatic certificate renewals",
                "Test tenant domain creation in staging environment",
            ]
        )

        return recommendations


# Export classes
__all__ = ["DNSValidator", "CoolifyDNSValidator"]
