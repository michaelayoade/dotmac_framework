"""Domain Management Service for the Management Platform."""

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from dotmac_shared.exceptions import NotFoundError, PermissionError, ValidationError

from ..models.domain_management import (
    DNSRecordType,
    DomainProvider,
    DomainStatus,
    SSLStatus,
    VerificationStatus,
)
from ..repositories.domain_repository import DomainRepository

logger = logging.getLogger(__name__)


class DomainService:
    """Service for domain management operations."""

    def __init__(self, domain_repository: DomainRepository):
        self.domain_repository = domain_repository
        self.base_domain = "dotmac.io"
        self.default_nameservers = ["ns1.dotmac.io", "ns2.dotmac.io"]

    # Domain Creation and Management

    async def create_domain(
        self,
        tenant_id: str,
        user_id: str,
        domain_name: str,
        subdomain: Optional[str] = None,
        dns_provider: DomainProvider = DomainProvider.COREDNS,
        is_primary: bool = False,
        auto_ssl: bool = True,
    ) -> dict:
        """Create a new domain for a tenant."""
        try:
            # Validate domain name
            if not self._is_valid_domain_name(domain_name):
                raise ValidationError("Invalid domain name format")

            # Construct full domain
            if subdomain:
                full_domain = f"{subdomain}.{domain_name}"
            else:
                full_domain = domain_name

            # Check if domain already exists
            existing_domain = await self.domain_repository.get_domain_by_name(
                full_domain, tenant_id
            )
            if existing_domain:
                raise ValidationError(f"Domain already exists: {full_domain}")

            # Create domain record
            domain_data = {
                "domain_name": domain_name,
                "subdomain": subdomain,
                "full_domain": full_domain,
                "domain_status": DomainStatus.PENDING,
                "is_primary": is_primary,
                "dns_provider": dns_provider,
                "nameservers": self.default_nameservers,
                "owner_user_id": user_id,
                "managed_by_system": True,
                "verification_status": VerificationStatus.PENDING,
                "ssl_status": SSLStatus.NONE,
            }

            domain = await self.domain_repository.create_domain(
                tenant_id=tenant_id, domain_data=domain_data, user_id=user_id
            )

            # Create default DNS records
            await self._create_default_dns_records(domain, user_id)

            # Initiate domain verification
            verification = await self._initiate_domain_verification(domain, user_id)

            # Log domain creation
            await self.domain_repository.log_domain_action(
                domain_id=domain.domain_id,
                tenant_id=tenant_id,
                action="created",
                user_id=user_id,
                description=f"Domain {full_domain} created",
                success=True,
            )

            result = {
                "domain": domain,
                "verification": verification,
                "dns_records_created": True,
                "ssl_requested": auto_ssl,
            }

            # Request SSL certificate if enabled
            if auto_ssl:
                ssl_certificate = await self._request_ssl_certificate(domain, user_id)
                result["ssl_certificate"] = ssl_certificate

            return result

        except Exception as e:
            logger.error(f"Failed to create domain: {e}")
            raise ValidationError(f"Failed to create domain: {str(e)}") from e

    async def get_domain(self, domain_id: str, tenant_id: str, user_id: str) -> dict:
        """Get domain with related records."""
        domain = await self.domain_repository.get_domain_by_id(domain_id, tenant_id)
        if not domain:
            raise NotFoundError(f"Domain not found: {domain_id}")

        # Check permissions (domain owner or admin)
        await self._check_domain_permission(domain, user_id)

        # Get DNS records
        dns_records = await self.domain_repository.get_domain_dns_records(
            domain_id, tenant_id
        )

        # Get SSL certificates
        ssl_certificates = await self.domain_repository.get_domain_ssl_certificates(
            domain_id, tenant_id
        )

        # Get recent logs
        domain_logs = await self.domain_repository.get_domain_logs(
            domain_id, tenant_id, limit=20
        )

        return {
            "domain": domain,
            "dns_records": dns_records,
            "ssl_certificates": ssl_certificates,
            "recent_logs": domain_logs,
        }

    async def update_domain(
        self, domain_id: str, tenant_id: str, user_id: str, updates: dict
    ) -> dict:
        """Update domain configuration."""
        domain = await self.domain_repository.get_domain_by_id(domain_id, tenant_id)
        if not domain:
            raise NotFoundError(f"Domain not found: {domain_id}")

        # Check permissions
        await self._check_domain_permission(domain, user_id)

        # Validate updates
        validated_updates = await self._validate_domain_updates(updates)

        updated_domain = await self.domain_repository.update_domain(
            domain_id=domain_id,
            tenant_id=tenant_id,
            updates=validated_updates,
            user_id=user_id,
        )

        return {"domain": updated_domain}

    async def delete_domain(
        self, domain_id: str, tenant_id: str, user_id: str, force: bool = False
    ) -> bool:
        """Delete domain and associated records."""
        domain = await self.domain_repository.get_domain_by_id(domain_id, tenant_id)
        if not domain:
            raise NotFoundError(f"Domain not found: {domain_id}")

        # Check permissions
        await self._check_domain_permission(domain, user_id)

        # Check if domain is primary (requires force)
        if domain.is_primary and not force:
            raise ValidationError("Cannot delete primary domain without force flag")

        return await self.domain_repository.delete_domain(domain_id, tenant_id, user_id)

    # DNS Record Management

    async def create_dns_record(
        self,
        domain_id: str,
        tenant_id: str,
        user_id: str,
        name: str,
        record_type: DNSRecordType,
        value: str,
        ttl: int = 3600,
        priority: Optional[int] = None,
    ) -> dict:
        """Create a new DNS record."""
        # Validate domain exists
        domain = await self.domain_repository.get_domain_by_id(domain_id, tenant_id)
        if not domain:
            raise NotFoundError(f"Domain not found: {domain_id}")

        # Check permissions
        await self._check_domain_permission(domain, user_id)

        # Validate DNS record data
        await self._validate_dns_record(name, record_type, value, priority)

        record_data = {
            "domain_id": domain_id,
            "name": name,
            "record_type": record_type,
            "value": value,
            "ttl": ttl,
            "priority": priority,
            "is_system_managed": False,
            "sync_status": "pending",
        }

        dns_record = await self.domain_repository.create_dns_record(
            tenant_id=tenant_id, record_data=record_data, user_id=user_id
        )

        # Log DNS record creation
        await self.domain_repository.log_domain_action(
            domain_id=domain_id,
            tenant_id=tenant_id,
            action="dns_record_created",
            user_id=user_id,
            description=f"Created {record_type} record: {name} -> {value}",
            success=True,
        )

        return {"dns_record": dns_record}

    async def update_dns_record(
        self, record_id: str, tenant_id: str, user_id: str, updates: dict
    ) -> dict:
        """Update DNS record."""
        dns_record = await self.domain_repository.get_dns_record_by_id(
            record_id, tenant_id
        )
        if not dns_record:
            raise NotFoundError(f"DNS record not found: {record_id}")

        # Get domain for permission check
        domain = await self.domain_repository.get_domain_by_id(
            dns_record.domain_id, tenant_id
        )
        await self._check_domain_permission(domain, user_id)

        # Check if record is editable
        if not dns_record.is_editable:
            raise PermissionError("DNS record is not editable")

        # Validate updates
        if "name" in updates or "record_type" in updates or "value" in updates:
            await self._validate_dns_record(
                updates.get("name", dns_record.name),
                updates.get("record_type", dns_record.record_type),
                updates.get("value", dns_record.value),
                updates.get("priority", dns_record.priority),
            )

        updated_record = await self.domain_repository.update_dns_record(
            record_id=record_id, tenant_id=tenant_id, updates=updates, user_id=user_id
        )

        # Log DNS record update
        await self.domain_repository.log_domain_action(
            domain_id=dns_record.domain_id,
            tenant_id=tenant_id,
            action="dns_record_updated",
            user_id=user_id,
            description=f"Updated {dns_record.record_type} record: {dns_record.name}",
            success=True,
        )

        return {"dns_record": updated_record}

    async def delete_dns_record(
        self, record_id: str, tenant_id: str, user_id: str
    ) -> bool:
        """Delete DNS record."""
        dns_record = await self.domain_repository.get_dns_record_by_id(
            record_id, tenant_id
        )
        if not dns_record:
            raise NotFoundError(f"DNS record not found: {record_id}")

        # Get domain for permission check
        domain = await self.domain_repository.get_domain_by_id(
            dns_record.domain_id, tenant_id
        )
        await self._check_domain_permission(domain, user_id)

        # Check if record is editable
        if not dns_record.is_editable:
            raise PermissionError("DNS record is not editable")

        success = await self.domain_repository.delete_dns_record(
            record_id, tenant_id, user_id
        )

        if success:
            # Log DNS record deletion
            await self.domain_repository.log_domain_action(
                domain_id=dns_record.domain_id,
                tenant_id=tenant_id,
                action="dns_record_deleted",
                user_id=user_id,
                description=f"Deleted {dns_record.record_type} record: {dns_record.name}",
                success=True,
            )

        return success

    # Domain Verification

    async def verify_domain(
        self,
        domain_id: str,
        tenant_id: str,
        user_id: str,
        verification_method: str = "DNS",
    ) -> dict:
        """Initiate domain verification process."""
        domain = await self.domain_repository.get_domain_by_id(domain_id, tenant_id)
        if not domain:
            raise NotFoundError(f"Domain not found: {domain_id}")

        # Check permissions
        await self._check_domain_permission(domain, user_id)

        verification = await self._initiate_domain_verification(
            domain, user_id, verification_method
        )

        return {
            "verification": verification,
            "instructions": self._get_verification_instructions(verification),
        }

    async def check_domain_verification(
        self, domain_id: str, tenant_id: str, user_id: str
    ) -> dict:
        """Check domain verification status."""
        domain = await self.domain_repository.get_domain_by_id(domain_id, tenant_id)
        if not domain:
            raise NotFoundError(f"Domain not found: {domain_id}")

        # Check permissions
        await self._check_domain_permission(domain, user_id)

        # Get pending verifications
        pending_verifications = await self.domain_repository.get_pending_verifications(
            tenant_id
        )
        domain_verifications = [
            v for v in pending_verifications if v.domain_id == domain_id
        ]

        if not domain_verifications:
            return {
                "verified": domain.verification_status == VerificationStatus.VERIFIED
            }

        # Check each pending verification
        verification_results = []
        for verification in domain_verifications:
            result = await self._check_verification(verification)
            verification_results.append(result)

        return {
            "verifications": verification_results,
            "verified": domain.verification_status == VerificationStatus.VERIFIED,
        }

    # SSL Certificate Management

    async def request_ssl_certificate(
        self,
        domain_id: str,
        tenant_id: str,
        user_id: str,
        certificate_authority: str = "letsencrypt",
    ) -> dict:
        """Request SSL certificate for domain."""
        domain = await self.domain_repository.get_domain_by_id(domain_id, tenant_id)
        if not domain:
            raise NotFoundError(f"Domain not found: {domain_id}")

        # Check permissions
        await self._check_domain_permission(domain, user_id)

        # Check if domain is verified
        if domain.verification_status != VerificationStatus.VERIFIED:
            raise ValidationError(
                "Domain must be verified before requesting SSL certificate"
            )

        ssl_certificate = await self._request_ssl_certificate(
            domain, user_id, certificate_authority
        )

        return {"ssl_certificate": ssl_certificate}

    async def renew_ssl_certificate(
        self, certificate_id: str, tenant_id: str, user_id: str
    ) -> dict:
        """Renew SSL certificate."""
        # Implementation would depend on certificate authority
        # For now, return a placeholder
        return {"status": "renewal_initiated", "certificate_id": certificate_id}

    # Statistics and Analytics

    async def get_tenant_domain_stats(self, tenant_id: str) -> dict:
        """Get domain statistics for a tenant."""
        return await self.domain_repository.get_tenant_domain_stats(tenant_id)

    async def get_expiring_domains(self, tenant_id: str, days_ahead: int = 30) -> list:
        """Get domains expiring within specified days."""
        return await self.domain_repository.get_expiring_domains(tenant_id, days_ahead)

    async def get_expiring_ssl_certificates(
        self, tenant_id: str, days_ahead: int = 30
    ) -> list:
        """Get SSL certificates expiring within specified days."""
        return await self.domain_repository.get_expiring_ssl_certificates(
            tenant_id, days_ahead
        )

    # Background Processing

    async def process_pending_verifications(
        self, tenant_id: Optional[str] = None
    ) -> int:
        """Process pending domain verifications."""
        pending_verifications = await self.domain_repository.get_pending_verifications(
            tenant_id
        )
        processed_count = 0

        for verification in pending_verifications:
            try:
                await self._check_verification(verification)
                processed_count += 1
            except Exception as e:
                logger.error(
                    f"Failed to check verification {verification.verification_id}: {e}"
                )

        return processed_count

    async def sync_dns_records(self, tenant_id: Optional[str] = None) -> int:
        """Synchronize DNS records with providers."""
        records_needing_sync = await self.domain_repository.get_records_needing_sync(
            tenant_id
        )
        synced_count = 0

        for record in records_needing_sync:
            try:
                # Implementation would depend on DNS provider
                # For now, mark as synced
                await self.domain_repository.update_dns_record(
                    record_id=record.record_id,
                    tenant_id=record.tenant_id,
                    updates={
                        "sync_status": "synced",
                        "last_sync_attempt": datetime.now(timezone.utc),
                    },
                    user_id="system",
                )
                synced_count += 1
            except Exception as e:
                logger.error(f"Failed to sync DNS record {record.record_id}: {e}")
                # Mark as failed
                await self.domain_repository.update_dns_record(
                    record_id=record.record_id,
                    tenant_id=record.tenant_id,
                    updates={
                        "sync_status": "failed",
                        "sync_error_message": str(e),
                        "last_sync_attempt": datetime.now(timezone.utc),
                    },
                    user_id="system",
                )

        return synced_count

    # Helper Methods

    def _is_valid_domain_name(self, domain_name: str) -> bool:
        """Validate domain name format."""
        if not domain_name or len(domain_name) > 253:
            return False

        # Basic domain name regex
        pattern = r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$"
        return bool(re.match(pattern, domain_name))

    async def _validate_dns_record(
        self,
        name: str,
        record_type: DNSRecordType,
        value: str,
        priority: Optional[int] = None,
    ) -> bool:
        """Validate DNS record data."""
        # Basic validation - expand based on record type
        if not name or not value:
            raise ValidationError("DNS record name and value are required")

        # Validate based on record type
        if record_type == DNSRecordType.A:
            # Validate IPv4 address
            if not self._is_valid_ipv4(value):
                raise ValidationError("Invalid IPv4 address for A record")

        elif record_type == DNSRecordType.AAAA:
            # Validate IPv6 address
            if not self._is_valid_ipv6(value):
                raise ValidationError("Invalid IPv6 address for AAAA record")

        elif record_type == DNSRecordType.MX:
            # Validate MX record format and priority
            if not priority:
                raise ValidationError("Priority is required for MX records")
            if not self._is_valid_domain_name(value):
                raise ValidationError("Invalid domain name for MX record")

        elif record_type == DNSRecordType.CNAME:
            # Validate CNAME target
            if not self._is_valid_domain_name(value):
                raise ValidationError("Invalid domain name for CNAME record")

        return True

    def _is_valid_ipv4(self, ip: str) -> bool:
        """Validate IPv4 address."""
        try:
            parts = ip.split(".")
            return len(parts) == 4 and all(0 <= int(part) <= 255 for part in parts)
        except (ValueError, AttributeError):
            return False

    def _is_valid_ipv6(self, ip: str) -> bool:
        """Validate IPv6 address."""
        try:
            import ipaddress

            ipaddress.IPv6Address(ip)
            return True
        except (ValueError, AttributeError):
            return False

    async def _check_domain_permission(self, domain, user_id: str) -> bool:
        """Check if user has permission to manage domain."""
        # Domain owner has full permissions
        if domain.owner_user_id == user_id:
            return True

        # Additional permission checks could be implemented here
        # For now, only owner can manage
        raise PermissionError(f"No permission to manage domain: {domain.domain_id}")

    async def _create_default_dns_records(self, domain, user_id: str) -> list:
        """Create default DNS records for a new domain."""
        default_records = [
            {
                "name": "@",
                "record_type": DNSRecordType.A,
                "value": "127.0.0.1",  # Default IP - should be configured
                "ttl": 3600,
                "is_system_managed": True,
                "is_editable": True,
            },
            {
                "name": "www",
                "record_type": DNSRecordType.CNAME,
                "value": domain.full_domain,
                "ttl": 3600,
                "is_system_managed": True,
                "is_editable": True,
            },
        ]

        created_records = []
        for record_data in default_records:
            record_data["domain_id"] = domain.domain_id
            try:
                dns_record = await self.domain_repository.create_dns_record(
                    tenant_id=domain.tenant_id, record_data=record_data, user_id=user_id
                )
                created_records.append(dns_record)
            except Exception as e:
                logger.error(f"Failed to create default DNS record: {e}")

        return created_records

    async def _initiate_domain_verification(
        self, domain, user_id: str, method: str = "DNS"
    ):
        """Initiate domain verification process."""
        verification_token = str(uuid4())

        verification_data = {
            "domain_id": domain.domain_id,
            "verification_method": method,
            "verification_token": verification_token,
            "verification_value": f"dotmac-verification={verification_token}",
            "status": VerificationStatus.PENDING,
            "expires_at": datetime.now(timezone.utc)
            + timedelta(days=7),  # 7 day expiry
            "next_check": datetime.now(timezone.utc)
            + timedelta(minutes=5),  # Check in 5 minutes
        }

        return await self.domain_repository.create_domain_verification(
            tenant_id=domain.tenant_id,
            verification_data=verification_data,
            user_id=user_id,
        )

    async def _check_verification(self, verification) -> dict:
        """Check if domain verification is complete."""
        # Implementation would depend on verification method
        # For DNS: check for TXT record
        # For HTTP: check for file at /.well-known/
        # For now, simulate verification

        # Simulate verification check
        verified = False  # Placeholder

        if verified:
            status = VerificationStatus.VERIFIED
            # Update domain verification status
            await self.domain_repository.update_domain(
                domain_id=verification.domain_id,
                tenant_id=verification.tenant_id,
                updates={
                    "verification_status": VerificationStatus.VERIFIED,
                    "verified_at": datetime.now(timezone.utc),
                },
                user_id="system",
            )
        else:
            status = VerificationStatus.PENDING

        # Update verification record
        await self.domain_repository.update_verification_status(
            verification_id=verification.verification_id,
            tenant_id=verification.tenant_id,
            status=status,
        )

        return {
            "verification_id": verification.verification_id,
            "status": status,
            "checked_at": datetime.now(timezone.utc),
        }

    async def _request_ssl_certificate(
        self, domain, user_id: str, certificate_authority: str = "letsencrypt"
    ):
        """Request SSL certificate for domain."""
        certificate_data = {
            "domain_id": domain.domain_id,
            "certificate_name": f"SSL Certificate for {domain.full_domain}",
            "common_name": domain.full_domain,
            "issuer": certificate_authority,
            "certificate_authority": certificate_authority,
            "issued_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc)
            + timedelta(days=90),  # 90 day cert
            "ssl_status": SSLStatus.PENDING,
            "auto_renew": True,
        }

        return await self.domain_repository.create_ssl_certificate(
            tenant_id=domain.tenant_id,
            certificate_data=certificate_data,
            user_id=user_id,
        )

    def _get_verification_instructions(self, verification) -> dict:
        """Get verification instructions based on method."""
        if verification.verification_method == "DNS":
            return {
                "method": "DNS",
                "instructions": f"Add a TXT record with name '_dotmac-verification' and value '{verification.verification_token}'",
                "record_name": "_dotmac-verification",
                "record_type": "TXT",
                "record_value": verification.verification_token,
            }
        elif verification.verification_method == "HTTP":
            return {
                "method": "HTTP",
                "instructions": f"Place verification file at http://{verification.domain.full_domain}/.well-known/dotmac-verification.txt",
                "file_path": ".well-known/dotmac-verification.txt",
                "file_content": verification.verification_token,
            }
        else:
            return {
                "method": verification.verification_method,
                "instructions": "Follow provider-specific verification instructions",
            }

    async def _validate_domain_updates(self, updates: dict) -> dict:
        """Validate domain update data."""
        validated_updates = {}

        # Validate each field
        for key, value in updates.items():
            if key == "domain_name" and value:
                if not self._is_valid_domain_name(value):
                    raise ValidationError("Invalid domain name format")
                validated_updates[key] = value
            elif key == "auto_renew" and isinstance(value, bool):
                validated_updates[key] = value
            elif key == "tags" and isinstance(value, list):
                validated_updates[key] = value
            elif key == "notes" and isinstance(value, str):
                validated_updates[key] = value
            # Add more validation rules as needed

        return validated_updates
