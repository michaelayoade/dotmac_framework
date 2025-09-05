"""Domain Management Repository for the Management Platform."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from dotmac_isp.shared.base_repository import BaseRepository
from dotmac_shared.exceptions import NotFoundError, ValidationError

from ..models.domain_management import (
    DNSRecord,
    DNSRecordType,
    DNSZone,
    Domain,
    DomainLog,
    DomainStatus,
    DomainVerification,
    SSLCertificate,
    SSLStatus,
    VerificationStatus,
)

logger = logging.getLogger(__name__)


class DomainRepository(BaseRepository):
    """Repository for domain management operations."""

    def __init__(self, session: Session):
        super().__init__(session)
        self.model = Domain

    # Domain Operations

    async def create_domain(
        self, tenant_id: str, domain_data: dict, user_id: str
    ) -> Domain:
        """Create a new domain."""
        try:
            domain_id = str(uuid4())

            domain = Domain(
                domain_id=domain_id,
                tenant_id=tenant_id,
                owner_user_id=user_id,
                created_by=user_id,
                **domain_data,
            )

            self.session.add(domain)
            await self.session.commit()
            await self.session.refresh(domain)

            logger.info(f"Created domain: {domain_id} ({domain.full_domain})")
            return domain

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to create domain: {e}")
            raise ValidationError(f"Failed to create domain: {str(e)}") from e

    async def get_domain_by_id(
        self, domain_id: str, tenant_id: str
    ) -> Optional[Domain]:
        """Get domain by ID."""
        return (
            await self.session.query(Domain)
            .filter(and_(Domain.domain_id == domain_id, Domain.tenant_id == tenant_id))
            .first()
        )

    async def get_domain_by_name(
        self, full_domain: str, tenant_id: str
    ) -> Optional[Domain]:
        """Get domain by full domain name."""
        return (
            await self.session.query(Domain)
            .filter(
                and_(Domain.full_domain == full_domain, Domain.tenant_id == tenant_id)
            )
            .first()
        )

    async def get_tenant_domains(
        self,
        tenant_id: str,
        status: DomainStatus = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Domain], int]:
        """Get domains for a tenant with pagination."""
        query = self.session.query(Domain).filter(Domain.tenant_id == tenant_id)

        if status:
            query = query.filter(Domain.domain_status == status)

        query = query.order_by(Domain.created_at.desc())

        total = await query.count()
        domains = await query.offset(skip).limit(limit).all()

        return domains, total

    async def get_expiring_domains(
        self, tenant_id: Optional[str] = None, days_ahead: int = 30
    ) -> list[Domain]:
        """Get domains expiring within specified days."""
        cutoff_date = datetime.now(timezone.utc) + timedelta(days=days_ahead)

        query = self.session.query(Domain).filter(
            and_(
                Domain.expiration_date.isnot(None),
                Domain.expiration_date <= cutoff_date,
                Domain.expiration_date > datetime.now(timezone.utc),
                Domain.domain_status == DomainStatus.ACTIVE,
            )
        )

        if tenant_id:
            query = query.filter(Domain.tenant_id == tenant_id)

        return await query.order_by(Domain.expiration_date.asc()).all()

    async def update_domain(
        self, domain_id: str, tenant_id: str, updates: dict, user_id: str
    ) -> Domain:
        """Update domain information."""
        domain = await self.get_domain_by_id(domain_id, tenant_id)
        if not domain:
            raise NotFoundError(f"Domain not found: {domain_id}")

        try:
            # Store previous state for logging
            previous_state = {
                "domain_status": domain.domain_status,
                "verification_status": domain.verification_status,
                "ssl_status": domain.ssl_status,
            }

            # Apply updates
            for key, value in updates.items():
                if hasattr(domain, key):
                    setattr(domain, key, value)

            domain.updated_by = user_id
            domain.updated_at = datetime.now(timezone.utc)

            await self.session.commit()
            await self.session.refresh(domain)

            # Log the update
            await self.log_domain_action(
                domain_id=domain_id,
                tenant_id=tenant_id,
                action="updated",
                user_id=user_id,
                description=f"Domain updated with fields: {list(updates.keys())}",
                before_state=previous_state,
                after_state={key: getattr(domain, key) for key in updates.keys()},
                success=True,
            )

            logger.info(f"Updated domain: {domain_id}")
            return domain

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to update domain: {e}")
            raise ValidationError(f"Failed to update domain: {str(e)}") from e

    async def delete_domain(self, domain_id: str, tenant_id: str, user_id: str) -> bool:
        """Delete domain (soft delete)."""
        domain = await self.get_domain_by_id(domain_id, tenant_id)
        if not domain:
            raise NotFoundError(f"Domain not found: {domain_id}")

        try:
            # Soft delete by updating status
            domain.domain_status = DomainStatus.SUSPENDED
            domain.updated_by = user_id
            domain.updated_at = datetime.now(timezone.utc)

            await self.session.commit()

            # Log deletion
            await self.log_domain_action(
                domain_id=domain_id,
                tenant_id=tenant_id,
                action="deleted",
                user_id=user_id,
                description=f"Domain {domain.full_domain} deleted",
                success=True,
            )

            logger.info(f"Deleted domain: {domain_id}")
            return True

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to delete domain: {e}")
            raise ValidationError(f"Failed to delete domain: {str(e)}") from e

    # DNS Record Operations

    async def create_dns_record(
        self, tenant_id: str, record_data: dict, user_id: str
    ) -> DNSRecord:
        """Create a new DNS record."""
        try:
            record_id = str(uuid4())

            dns_record = DNSRecord(
                record_id=record_id,
                tenant_id=tenant_id,
                created_by=user_id,
                **record_data,
            )

            self.session.add(dns_record)
            await self.session.commit()
            await self.session.refresh(dns_record)

            logger.info(f"Created DNS record: {record_id}")
            return dns_record

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to create DNS record: {e}")
            raise ValidationError(f"Failed to create DNS record: {str(e)}") from e

    async def get_domain_dns_records(
        self, domain_id: str, tenant_id: str, record_type: DNSRecordType = None
    ) -> list[DNSRecord]:
        """Get DNS records for a domain."""
        query = self.session.query(DNSRecord).filter(
            and_(DNSRecord.domain_id == domain_id, DNSRecord.tenant_id == tenant_id)
        )

        if record_type:
            query = query.filter(DNSRecord.record_type == record_type)

        return await query.order_by(DNSRecord.record_type, DNSRecord.name).all()

    async def get_dns_record_by_id(
        self, record_id: str, tenant_id: str
    ) -> Optional[DNSRecord]:
        """Get DNS record by ID."""
        return (
            await self.session.query(DNSRecord)
            .filter(
                and_(DNSRecord.record_id == record_id, DNSRecord.tenant_id == tenant_id)
            )
            .first()
        )

    async def update_dns_record(
        self, record_id: str, tenant_id: str, updates: dict, user_id: str
    ) -> DNSRecord:
        """Update DNS record."""
        dns_record = await self.get_dns_record_by_id(record_id, tenant_id)
        if not dns_record:
            raise NotFoundError(f"DNS record not found: {record_id}")

        try:
            for key, value in updates.items():
                if hasattr(dns_record, key):
                    setattr(dns_record, key, value)

            dns_record.updated_by = user_id
            dns_record.updated_at = datetime.now(timezone.utc)
            dns_record.sync_status = "pending"  # Mark for re-sync

            await self.session.commit()
            await self.session.refresh(dns_record)

            logger.info(f"Updated DNS record: {record_id}")
            return dns_record

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to update DNS record: {e}")
            raise ValidationError(f"Failed to update DNS record: {str(e)}") from e

    async def delete_dns_record(
        self, record_id: str, tenant_id: str, user_id: str
    ) -> bool:
        """Delete DNS record."""
        dns_record = await self.get_dns_record_by_id(record_id, tenant_id)
        if not dns_record:
            raise NotFoundError(f"DNS record not found: {record_id}")

        try:
            await self.session.delete(dns_record)
            await self.session.commit()

            logger.info(f"Deleted DNS record: {record_id}")
            return True

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to delete DNS record: {e}")
            raise ValidationError(f"Failed to delete DNS record: {str(e)}") from e

    # SSL Certificate Operations

    async def create_ssl_certificate(
        self, tenant_id: str, certificate_data: dict, user_id: str
    ) -> SSLCertificate:
        """Create a new SSL certificate."""
        try:
            certificate_id = str(uuid4())

            ssl_certificate = SSLCertificate(
                certificate_id=certificate_id,
                tenant_id=tenant_id,
                created_by=user_id,
                **certificate_data,
            )

            self.session.add(ssl_certificate)
            await self.session.commit()
            await self.session.refresh(ssl_certificate)

            logger.info(f"Created SSL certificate: {certificate_id}")
            return ssl_certificate

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to create SSL certificate: {e}")
            raise ValidationError(f"Failed to create SSL certificate: {str(e)}") from e

    async def get_domain_ssl_certificates(
        self, domain_id: str, tenant_id: str
    ) -> list[SSLCertificate]:
        """Get SSL certificates for a domain."""
        return (
            await self.session.query(SSLCertificate)
            .filter(
                and_(
                    SSLCertificate.domain_id == domain_id,
                    SSLCertificate.tenant_id == tenant_id,
                )
            )
            .order_by(SSLCertificate.created_at.desc())
            .all()
        )

    async def get_expiring_ssl_certificates(
        self, tenant_id: Optional[str] = None, days_ahead: int = 30
    ) -> list[SSLCertificate]:
        """Get SSL certificates expiring within specified days."""
        cutoff_date = datetime.now(timezone.utc) + timedelta(days=days_ahead)

        query = self.session.query(SSLCertificate).filter(
            and_(
                SSLCertificate.expires_at <= cutoff_date,
                SSLCertificate.expires_at > datetime.now(timezone.utc),
                SSLCertificate.ssl_status == SSLStatus.ISSUED,
            )
        )

        if tenant_id:
            query = query.filter(SSLCertificate.tenant_id == tenant_id)

        return await query.order_by(SSLCertificate.expires_at.asc()).all()

    # Domain Verification Operations

    async def create_domain_verification(
        self, tenant_id: str, verification_data: dict, user_id: str
    ) -> DomainVerification:
        """Create a new domain verification."""
        try:
            verification_id = str(uuid4())

            verification = DomainVerification(
                verification_id=verification_id,
                tenant_id=tenant_id,
                created_by=user_id,
                **verification_data,
            )

            self.session.add(verification)
            await self.session.commit()
            await self.session.refresh(verification)

            logger.info(f"Created domain verification: {verification_id}")
            return verification

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to create domain verification: {e}")
            raise ValidationError(
                f"Failed to create domain verification: {str(e)}"
            ) from e

    async def get_pending_verifications(
        self, tenant_id: Optional[str] = None
    ) -> list[DomainVerification]:
        """Get pending domain verifications."""
        query = self.session.query(DomainVerification).filter(
            and_(
                DomainVerification.status == VerificationStatus.PENDING,
                or_(
                    DomainVerification.next_check.is_(None),
                    DomainVerification.next_check <= datetime.now(timezone.utc),
                ),
            )
        )

        if tenant_id:
            query = query.filter(DomainVerification.tenant_id == tenant_id)

        return await query.order_by(DomainVerification.initiated_at.asc()).all()

    async def update_verification_status(
        self,
        verification_id: str,
        tenant_id: str,
        status: VerificationStatus,
        verification_response: Optional[dict] = None,
        error_details: Optional[dict] = None,
    ) -> DomainVerification:
        """Update domain verification status."""
        verification = (
            await self.session.query(DomainVerification)
            .filter(
                and_(
                    DomainVerification.verification_id == verification_id,
                    DomainVerification.tenant_id == tenant_id,
                )
            )
            .first()
        )

        if not verification:
            raise NotFoundError(f"Domain verification not found: {verification_id}")

        try:
            verification.status = status
            verification.attempts += 1
            verification.last_check = datetime.now(timezone.utc)

            if status == VerificationStatus.VERIFIED:
                verification.verified_at = datetime.now(timezone.utc)
            elif status == VerificationStatus.FAILED:
                verification.error_details = error_details
                # Schedule next attempt (exponential backoff)
                delay_minutes = min(5 * (2**verification.attempts), 60)  # Max 1 hour
                verification.next_check = datetime.now(timezone.utc) + timedelta(
                    minutes=delay_minutes
                )

            if verification_response:
                verification.verification_response = verification_response

            await self.session.commit()
            await self.session.refresh(verification)

            return verification

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to update verification status: {e}")
            raise ValidationError(
                f"Failed to update verification status: {str(e)}"
            ) from e

    # Domain Logging

    async def log_domain_action(
        self,
        domain_id: str,
        tenant_id: str,
        action: str,
        user_id: str,
        description: str,
        before_state: Optional[dict] = None,
        after_state: Optional[dict] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        operation_id: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ) -> DomainLog:
        """Log domain action for audit trail."""
        try:
            log_entry = DomainLog(
                domain_id=domain_id,
                tenant_id=tenant_id,
                action=action,
                user_id=user_id,
                description=description,
                before_state=before_state,
                after_state=after_state,
                success=success,
                error_message=error_message,
                operation_id=operation_id,
                duration_ms=duration_ms,
            )

            self.session.add(log_entry)
            await self.session.commit()
            await self.session.refresh(log_entry)

            return log_entry

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to log domain action: {e}")
            raise ValidationError(f"Failed to log domain action: {str(e)}") from e

    async def get_domain_logs(
        self, domain_id: str, tenant_id: str, limit: int = 100
    ) -> list[DomainLog]:
        """Get domain action logs."""
        return (
            await self.session.query(DomainLog)
            .filter(
                and_(DomainLog.domain_id == domain_id, DomainLog.tenant_id == tenant_id)
            )
            .order_by(DomainLog.log_timestamp.desc())
            .limit(limit)
            .all()
        )

    # DNS Zone Operations

    async def create_dns_zone(
        self, tenant_id: str, zone_data: dict, user_id: str
    ) -> DNSZone:
        """Create a new DNS zone."""
        try:
            zone_id = str(uuid4())

            dns_zone = DNSZone(
                zone_id=zone_id, tenant_id=tenant_id, created_by=user_id, **zone_data
            )

            self.session.add(dns_zone)
            await self.session.commit()
            await self.session.refresh(dns_zone)

            logger.info(f"Created DNS zone: {zone_id}")
            return dns_zone

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to create DNS zone: {e}")
            raise ValidationError(f"Failed to create DNS zone: {str(e)}") from e

    async def get_zones_needing_sync(
        self, tenant_id: Optional[str] = None
    ) -> list[DNSZone]:
        """Get DNS zones that need synchronization."""
        query = self.session.query(DNSZone).filter(
            DNSZone.sync_status.in_(["pending", "failed"])
        )

        if tenant_id:
            query = query.filter(DNSZone.tenant_id == tenant_id)

        return await query.order_by(DNSZone.last_sync.asc().nullsfirst()).all()

    # Statistics and Analytics

    async def get_tenant_domain_stats(self, tenant_id: str) -> dict:
        """Get domain statistics for a tenant."""
        try:
            # Total domains
            total_domains = (
                await self.session.query(func.count(Domain.id))
                .filter(Domain.tenant_id == tenant_id)
                .scalar()
            )

            # Domains by status
            status_stats = (
                await self.session.query(Domain.domain_status, func.count(Domain.id))
                .filter(Domain.tenant_id == tenant_id)
                .group_by(Domain.domain_status)
                .all()
            )

            # SSL certificates by status
            ssl_stats = (
                await self.session.query(
                    SSLCertificate.ssl_status, func.count(SSLCertificate.id)
                )
                .join(Domain)
                .filter(Domain.tenant_id == tenant_id)
                .group_by(SSLCertificate.ssl_status)
                .all()
            )

            # Expiring domains (next 30 days)
            month_from_now = datetime.now(timezone.utc) + timedelta(days=30)
            expiring_domains = (
                await self.session.query(Domain)
                .filter(
                    and_(
                        Domain.tenant_id == tenant_id,
                        Domain.expiration_date.isnot(None),
                        Domain.expiration_date <= month_from_now,
                        Domain.expiration_date > datetime.now(timezone.utc),
                    )
                )
                .order_by(Domain.expiration_date.asc())
                .limit(10)
                .all()
            )

            # Expiring SSL certificates (next 30 days)
            expiring_ssl = (
                await self.session.query(SSLCertificate)
                .join(Domain)
                .filter(
                    and_(
                        Domain.tenant_id == tenant_id,
                        SSLCertificate.expires_at <= month_from_now,
                        SSLCertificate.expires_at > datetime.now(timezone.utc),
                        SSLCertificate.ssl_status == SSLStatus.ISSUED,
                    )
                )
                .order_by(SSLCertificate.expires_at.asc())
                .limit(10)
                .all()
            )

            # DNS providers usage
            provider_stats = (
                await self.session.query(Domain.dns_provider, func.count(Domain.id))
                .filter(Domain.tenant_id == tenant_id)
                .group_by(Domain.dns_provider)
                .all()
            )

            return {
                "total_domains": total_domains,
                "domains_by_status": dict(status_stats),
                "ssl_by_status": dict(ssl_stats),
                "expiring_domains": expiring_domains,
                "expiring_ssl_certificates": expiring_ssl,
                "providers_usage": dict(provider_stats),
            }

        except Exception as e:
            logger.error(f"Failed to get tenant domain stats: {e}")
            raise ValidationError(f"Failed to get tenant domain stats: {str(e)}") from e

    # Cleanup Operations

    async def cleanup_expired_verifications(self) -> int:
        """Clean up expired domain verifications."""
        try:
            expired_verifications = (
                await self.session.query(DomainVerification)
                .filter(
                    and_(
                        DomainVerification.expires_at.isnot(None),
                        DomainVerification.expires_at < datetime.now(timezone.utc),
                        DomainVerification.status == VerificationStatus.PENDING,
                    )
                )
                .all()
            )

            count = len(expired_verifications)

            for verification in expired_verifications:
                verification.status = VerificationStatus.EXPIRED

            await self.session.commit()

            logger.info(f"Marked {count} verifications as expired")
            return count

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to cleanup expired verifications: {e}")
            raise ValidationError(
                f"Failed to cleanup expired verifications: {str(e)}"
            ) from e

    async def get_records_needing_sync(
        self, tenant_id: Optional[str] = None
    ) -> list[DNSRecord]:
        """Get DNS records that need synchronization."""
        query = self.session.query(DNSRecord).filter(
            DNSRecord.sync_status.in_(["pending", "failed"])
        )

        if tenant_id:
            query = query.filter(DNSRecord.tenant_id == tenant_id)

        return await query.order_by(
            DNSRecord.last_sync_attempt.asc().nullsfirst()
        ).all()
