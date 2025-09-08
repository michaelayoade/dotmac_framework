"""
Domain Verification Service

Provides DNS TXT and HTTP-based domain ownership verification for partner branding.
Includes idempotent verification workers and comprehensive error handling.
"""

import asyncio
import logging
import secrets
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

import dns.resolver
import httpx
from pydantic import BaseModel

from dotmac.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


class VerificationMethod(str, Enum):
    """Domain verification methods."""
    DNS_TXT = "dns_txt"
    HTTP_FILE = "http_file"


class VerificationStatus(str, Enum):
    """Domain verification status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    VERIFIED = "verified"
    FAILED = "failed"
    EXPIRED = "expired"


class DomainVerificationChallenge(BaseModel):
    """Domain verification challenge data."""
    domain: str
    method: VerificationMethod
    challenge_token: str
    expected_value: str
    expires_at: datetime
    attempts: int = 0
    last_error: Optional[str] = None


class DomainVerificationService:
    """Service for verifying domain ownership."""
    
    def __init__(
        self,
        challenge_ttl_seconds: int = 86400,  # 24 hours
        max_attempts: int = 3,
        http_timeout_seconds: int = 10,
    ):
        self.challenge_ttl_seconds = challenge_ttl_seconds
        self.max_attempts = max_attempts
        self.http_timeout_seconds = http_timeout_seconds
        self._dns_resolver = dns.resolver.Resolver()
        self._dns_resolver.timeout = 10
        self._dns_resolver.lifetime = 30

    def create_verification_challenge(
        self, 
        domain: str, 
        method: VerificationMethod = VerificationMethod.DNS_TXT
    ) -> DomainVerificationChallenge:
        """
        Create a new domain verification challenge.
        
        Args:
            domain: Domain name to verify
            method: Verification method to use
            
        Returns:
            Domain verification challenge data
        """
        # Validate domain format
        if not self._is_valid_domain(domain):
            raise ValidationError(f"Invalid domain format: {domain}")
        
        # Generate unique challenge token
        challenge_token = secrets.token_urlsafe(32)
        
        # Create expected value based on method
        if method == VerificationMethod.DNS_TXT:
            expected_value = f"dotmac-domain-verification={challenge_token}"
        else:  # HTTP_FILE
            expected_value = challenge_token
        
        # Set expiration
        expires_at = datetime.now(timezone.utc).timestamp() + self.challenge_ttl_seconds
        expires_at = datetime.fromtimestamp(expires_at, tz=timezone.utc)
        
        challenge = DomainVerificationChallenge(
            domain=domain,
            method=method,
            challenge_token=challenge_token,
            expected_value=expected_value,
            expires_at=expires_at,
        )
        
        logger.info(f"Created {method.value} verification challenge for domain: {domain}")
        return challenge

    async def verify_domain_challenge(
        self, 
        challenge: DomainVerificationChallenge
    ) -> tuple[bool, Optional[str]]:
        """
        Verify a domain ownership challenge.
        
        Args:
            challenge: Domain verification challenge to verify
            
        Returns:
            Tuple of (success, error_message)
        """
        # Check if challenge is expired
        if datetime.now(timezone.utc) > challenge.expires_at:
            return False, "Verification challenge has expired"
        
        # Check if max attempts exceeded
        if challenge.attempts >= self.max_attempts:
            return False, f"Maximum verification attempts ({self.max_attempts}) exceeded"
        
        try:
            if challenge.method == VerificationMethod.DNS_TXT:
                return await self._verify_dns_txt_challenge(challenge)
            else:  # HTTP_FILE
                return await self._verify_http_file_challenge(challenge)
                
        except Exception as e:
            error_msg = f"Verification error: {str(e)}"
            logger.warning(f"Domain verification failed for {challenge.domain}: {error_msg}")
            return False, error_msg

    async def _verify_dns_txt_challenge(
        self, 
        challenge: DomainVerificationChallenge
    ) -> tuple[bool, Optional[str]]:
        """Verify DNS TXT record challenge."""
        domain = challenge.domain
        expected_value = challenge.expected_value
        
        try:
            # Query TXT records for the domain
            txt_records = self._dns_resolver.resolve(domain, 'TXT')
            
            # Check each TXT record
            for record in txt_records:
                record_value = str(record).strip('"')
                if record_value == expected_value:
                    logger.info(f"DNS TXT verification successful for domain: {domain}")
                    return True, None
            
            # Also check _dotmac-challenge subdomain (alternative approach)
            try:
                challenge_subdomain = f"_dotmac-challenge.{domain}"
                challenge_records = self._dns_resolver.resolve(challenge_subdomain, 'TXT')
                
                for record in challenge_records:
                    record_value = str(record).strip('"')
                    if record_value == challenge.challenge_token:
                        logger.info(f"DNS TXT verification successful for domain: {domain} (subdomain method)")
                        return True, None
                        
            except dns.resolver.NXDOMAIN:
                pass  # Subdomain doesn't exist, that's fine
            
            return False, f"DNS TXT record not found or doesn't match expected value"
            
        except dns.resolver.NXDOMAIN:
            return False, f"Domain {domain} does not exist"
        except dns.resolver.NoAnswer:
            return False, f"No TXT records found for domain {domain}"
        except dns.resolver.Timeout:
            return False, f"DNS query timeout for domain {domain}"
        except Exception as e:
            return False, f"DNS verification error: {str(e)}"

    async def _verify_http_file_challenge(
        self, 
        challenge: DomainVerificationChallenge
    ) -> tuple[bool, Optional[str]]:
        """Verify HTTP file challenge."""
        domain = challenge.domain
        expected_content = challenge.challenge_token
        
        # Try multiple URL patterns
        url_patterns = [
            f"http://{domain}/.well-known/dotmac-domain-verification.txt",
            f"https://{domain}/.well-known/dotmac-domain-verification.txt",
            f"http://{domain}/dotmac-domain-verification.txt",
            f"https://{domain}/dotmac-domain-verification.txt",
        ]
        
        async with httpx.AsyncClient(timeout=self.http_timeout_seconds) as client:
            for url in url_patterns:
                try:
                    logger.debug(f"Attempting HTTP verification: {url}")
                    response = await client.get(url, follow_redirects=True)
                    
                    if response.status_code == 200:
                        content = response.text.strip()
                        if content == expected_content:
                            logger.info(f"HTTP file verification successful for domain: {domain}")
                            return True, None
                        else:
                            logger.debug(f"HTTP file content mismatch: expected '{expected_content}', got '{content}'")
                            
                except httpx.RequestError as e:
                    logger.debug(f"HTTP request failed for {url}: {e}")
                    continue
                except Exception as e:
                    logger.debug(f"HTTP verification error for {url}: {e}")
                    continue
        
        return False, "HTTP verification file not found or content doesn't match"

    def _is_valid_domain(self, domain: str) -> bool:
        """Validate domain name format."""
        if not domain or len(domain) > 253:
            return False
        
        # Basic domain validation
        import re
        domain_pattern = re.compile(
            r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$'
        )
        
        return bool(domain_pattern.match(domain))

    def get_verification_instructions(
        self, 
        challenge: DomainVerificationChallenge
    ) -> dict[str, str]:
        """Get human-readable verification instructions."""
        domain = challenge.domain
        
        if challenge.method == VerificationMethod.DNS_TXT:
            return {
                "method": "DNS TXT Record",
                "instructions": f"""
To verify ownership of {domain}, add one of these TXT records to your DNS:

Option 1 (Recommended):
Host: _dotmac-challenge.{domain}
Type: TXT
Value: {challenge.challenge_token}

Option 2:
Host: {domain}
Type: TXT  
Value: {challenge.expected_value}

DNS changes may take up to 24 hours to propagate.
""".strip(),
                "verification_url": f"/api/partners/verify-domain/{domain}",
                "expires_at": challenge.expires_at.isoformat(),
            }
        else:  # HTTP_FILE
            return {
                "method": "HTTP File Upload",
                "instructions": f"""
To verify ownership of {domain}, upload a file with this content:

File path: /.well-known/dotmac-domain-verification.txt
OR: /dotmac-domain-verification.txt

Content: {challenge.challenge_token}

Make sure the file is accessible via HTTP or HTTPS.
""".strip(),
                "verification_url": f"/api/partners/verify-domain/{domain}",
                "expires_at": challenge.expires_at.isoformat(),
            }


# Global service instance
domain_verification_service = DomainVerificationService()