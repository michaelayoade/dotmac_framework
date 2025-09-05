"""
DNS Provider Interface
Abstract interface for DNS validation and management providers
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class DNSRecord:
    """DNS record representation"""

    domain: str
    record_type: str  # A, AAAA, CNAME, MX, TXT, etc.
    value: str
    ttl: int = 300
    priority: Optional[int] = None  # For MX records


@dataclass
class DNSValidationResult:
    """Result of DNS validation"""

    domain: str
    available: bool
    dns_exists: bool = False
    http_responding: bool = False
    https_responding: bool = False
    ssl_valid: bool = False
    details: dict[str, Any] = None
    error: Optional[str] = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


@dataclass
class SSLCertificateInfo:
    """SSL certificate information"""

    domain: str
    valid: bool
    issuer: str = ""
    subject: str = ""
    expires_at: Optional[str] = None
    days_until_expiry: Optional[int] = None
    error: Optional[str] = None


class IDNSProvider(ABC):
    """
    Abstract interface for DNS providers.
    Provides DNS validation, resolution, and management capabilities.
    """

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the DNS provider"""
        pass

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Check provider health"""
        pass

    @abstractmethod
    async def validate_subdomain_available(
        self, subdomain: str, base_domain: Optional[str] = None
    ) -> DNSValidationResult:
        """Check if subdomain is available for provisioning"""
        pass

    @abstractmethod
    async def validate_ssl_certificate(self, domain: str) -> SSLCertificateInfo:
        """Validate SSL certificate for domain"""
        pass

    @abstractmethod
    async def resolve_domain(self, domain: str, record_type: str = "A") -> dict[str, Any]:
        """Resolve DNS domain"""
        pass

    @abstractmethod
    async def check_dns_propagation(self, domain: str, expected_value: Optional[str] = None) -> dict[str, Any]:
        """Check DNS propagation status"""
        pass

    @abstractmethod
    def get_supported_record_types(self) -> list[str]:
        """Get supported DNS record types"""
        pass

    # Optional methods for DNS management (not all providers support these)

    async def create_record(self, record: DNSRecord) -> dict[str, Any]:
        """Create DNS record (optional - not all providers support this)"""
        return {
            "success": False,
            "error": "DNS record creation not supported by this provider",
            "provider": self.__class__.__name__,
        }

    async def update_record(self, record_id: str, record: DNSRecord) -> dict[str, Any]:
        """Update DNS record (optional)"""
        return {"success": False, "error": "DNS record update not supported by this provider"}

    async def delete_record(self, record_id: str) -> bool:
        """Delete DNS record (optional)"""
        return False

    @abstractmethod
    async def cleanup(self) -> bool:
        """Cleanup provider resources"""
        pass
