from dotmac_shared.api.dependencies import (\n    PaginatedDependencies,\n    get_paginated_deps\n)\nfrom dotmac_shared.schemas.base_schemas import PaginatedResponseSchema\n"""Domain Management API Router for the Management Platform."""

import logging
from typing import List, Optional

from fastapi import Depends, Query

from dotmac_shared.api.exception_handlers import standard_exception_handler
from dotmac_shared.api.rate_limiting_decorators import rate_limit, rate_limit_strict
from dotmac_shared.api.router_factory import RouterFactory

from ...dependencies import get_current_user, get_domain_service
from ...models.domain_management import DNSRecordType, DomainProvider, DomainStatus
from ...schemas.domain_schemas import (
    BulkDomainOperationRequest,
    BulkDomainOperationResponse,
    DNSRecordCreate,
    DNSRecordResponse,
    DNSRecordUpdate,
    DomainCreate,
    DomainListResponse,
    DomainResponse,
    DomainSearchRequest,
    DomainStatsResponse,
    DomainUpdate,
    DomainVerificationInstructions,
    DomainVerificationResponse,
    SSLCertificateResponse,
)
from ...services.domain_service import DomainService
from datetime import timezone

logger = logging.getLogger(__name__)

# Create router using RouterFactory
router = RouterFactory.create_router(
    prefix="/domains",
    tags=["Domain Management"],
    dependencies=[Depends(get_current_user)]
)


# Domain Management Endpoints

@router.post("/", response_model=DomainResponse)
@rate_limit_strict(max_requests=10, time_window_seconds=60)
@standard_exception_handler
async def create_domain(
    domain_data: DomainCreate,
    current_user: dict = Depends(get_current_user),
    domain_service: DomainService = Depends(get_domain_service)
):
    """Create a new domain."""
    result = await domain_service.create_domain(
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        domain_name=domain_data.domain_name,
        subdomain=domain_data.subdomain,
        dns_provider=domain_data.dns_provider,
        is_primary=domain_data.is_primary,
        auto_ssl=domain_data.auto_ssl
    )
    
    domain = result['domain']
    
    return DomainResponse(
        id=domain.id,
        domain_id=domain.domain_id,
        tenant_id=domain.tenant_id,
        domain_name=domain.domain_name,
        subdomain=domain.subdomain,
        full_domain=domain.full_domain,
        domain_status=domain.domain_status,
        is_primary=domain.is_primary,
        dns_provider=domain.dns_provider,
        nameservers=domain.nameservers or [],
        verification_status=domain.verification_status,
        verified_at=domain.verified_at,
        ssl_status=domain.ssl_status,
        ssl_expires_at=domain.ssl_expires_at,
        owner_user_id=domain.owner_user_id,
        auto_renew=domain.auto_renew,
        notes=domain.notes,
        tags=domain.tags or [],
        created_at=domain.created_at,
        updated_at=domain.updated_at
    )


@router.get("/", response_model=DomainListResponse)
@rate_limit(max_requests=100, time_window_seconds=60)
@standard_exception_handler
async def list_domains(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Page size"),
    status: Optional[DomainStatus] = Query(None, description="Filter by status"),
    current_user: dict = Depends(get_current_user),
    domain_service: DomainService = Depends(get_domain_service)
):
    """List domains for the current tenant."""
    domains, total = await domain_service.get_tenant_domains(
        tenant_id=current_user["tenant_id"],
        status=status,
        page=page,
        size=size
    )
    
    domain_responses = []
    for domain in domains:
        domain_responses.append(DomainResponse(
            id=domain.id,
            domain_id=domain.domain_id,
            tenant_id=domain.tenant_id,
            domain_name=domain.domain_name,
            subdomain=domain.subdomain,
            full_domain=domain.full_domain,
            domain_status=domain.domain_status,
            is_primary=domain.is_primary,
            dns_provider=domain.dns_provider,
            nameservers=domain.nameservers or [],
            verification_status=domain.verification_status,
            ssl_status=domain.ssl_status,
            owner_user_id=domain.owner_user_id,
            created_at=domain.created_at
        ))
    
    return DomainListResponse(
        items=domain_responses,
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size
    )


@router.get("/{domain_id}", response_model=DomainResponse)
@rate_limit(max_requests=100, time_window_seconds=60)
@standard_exception_handler
async def get_domain(
    domain_id: str,
    current_user: dict = Depends(get_current_user),
    domain_service: DomainService = Depends(get_domain_service)
):
    """Get domain details."""
    result = await domain_service.get_domain(
        domain_id=domain_id,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"]
    )
    
    domain = result['domain']
    
    return DomainResponse(
        id=domain.id,
        domain_id=domain.domain_id,
        tenant_id=domain.tenant_id,
        domain_name=domain.domain_name,
        full_domain=domain.full_domain,
        domain_status=domain.domain_status,
        dns_provider=domain.dns_provider,
        verification_status=domain.verification_status,
        ssl_status=domain.ssl_status,
        owner_user_id=domain.owner_user_id,
        created_at=domain.created_at
    )


@router.put("/{domain_id}", response_model=DomainResponse)
@rate_limit(max_requests=50, time_window_seconds=60)
@standard_exception_handler
async def update_domain(
    domain_id: str,
    updates: DomainUpdate,
    current_user: dict = Depends(get_current_user),
    domain_service: DomainService = Depends(get_domain_service)
):
    """Update domain configuration."""
    result = await domain_service.update_domain(
        domain_id=domain_id,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        updates=updates.model_dump(exclude_unset=True)
    )
    
    domain = result['domain']
    
    return DomainResponse(
        id=domain.id,
        domain_id=domain.domain_id,
        tenant_id=domain.tenant_id,
        domain_name=domain.domain_name,
        full_domain=domain.full_domain,
        domain_status=domain.domain_status,
        dns_provider=domain.dns_provider,
        verification_status=domain.verification_status,
        ssl_status=domain.ssl_status,
        owner_user_id=domain.owner_user_id,
        updated_at=domain.updated_at
    )


@router.delete("/{domain_id}")
@rate_limit_strict(max_requests=5, time_window_seconds=60)
@standard_exception_handler
async def delete_domain(
    domain_id: str,
    force: bool = Query(False, description="Force delete primary domain"),
    current_user: dict = Depends(get_current_user),
    domain_service: DomainService = Depends(get_domain_service)
):
    """Delete domain."""
    success = await domain_service.delete_domain(
        domain_id=domain_id,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        force=force
    )
    
    return {"success": success, "message": "Domain deleted successfully"}


# DNS Record Management

@router.post("/{domain_id}/dns", response_model=DNSRecordResponse)
@rate_limit(max_requests=50, time_window_seconds=60)
@standard_exception_handler
async def create_dns_record(
    domain_id: str,
    record_data: DNSRecordCreate,
    current_user: dict = Depends(get_current_user),
    domain_service: DomainService = Depends(get_domain_service)
):
    """Create DNS record for domain."""
    result = await domain_service.create_dns_record(
        domain_id=domain_id,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        name=record_data.name,
        record_type=record_data.record_type,
        value=record_data.value,
        ttl=record_data.ttl,
        priority=record_data.priority
    )
    
    dns_record = result['dns_record']
    
    return DNSRecordResponse(
        id=dns_record.id,
        record_id=dns_record.record_id,
        domain_id=dns_record.domain_id,
        tenant_id=dns_record.tenant_id,
        name=dns_record.name,
        record_type=dns_record.record_type,
        value=dns_record.value,
        ttl=dns_record.ttl,
        priority=dns_record.priority,
        is_system_managed=dns_record.is_system_managed,
        is_editable=dns_record.is_editable,
        sync_status=dns_record.sync_status,
        created_at=dns_record.created_at
    )


@router.get("/{domain_id}/dns", response_model=PaginatedResponseSchema[DNSRecordResponse])
@rate_limit(max_requests=100, time_window_seconds=60)
@standard_exception_handler
async def list_dns_records(
    domain_id: str,
    record_type: Optional[DNSRecordType] = Query(None, description="Filter by record type"),
    current_user: dict = Depends(get_current_user),
    domain_service: DomainService = Depends(get_domain_service)
):
    """List DNS records for domain.\n\nReturns paginated results."""
    result = await domain_service.get_domain(
        domain_id=domain_id,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"]
    )
    
    dns_records = result['dns_records']
    
    # Filter by record type if specified
    if record_type:
        dns_records = [r for r in dns_records if r.record_type == record_type]
    
    record_responses = []
    for record in dns_records:
        record_responses.append(DNSRecordResponse(
            id=record.id,
            record_id=record.record_id,
            domain_id=record.domain_id,
            tenant_id=record.tenant_id,
            name=record.name,
            record_type=record.record_type,
            value=record.value,
            ttl=record.ttl,
            sync_status=record.sync_status,
            created_at=record.created_at
        ))
    
    return record_responses


@router.put("/dns/{record_id}", response_model=DNSRecordResponse)
@rate_limit(max_requests=50, time_window_seconds=60)
@standard_exception_handler
async def update_dns_record(
    record_id: str,
    updates: DNSRecordUpdate,
    current_user: dict = Depends(get_current_user),
    domain_service: DomainService = Depends(get_domain_service)
):
    """Update DNS record."""
    result = await domain_service.update_dns_record(
        record_id=record_id,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        updates=updates.model_dump(exclude_unset=True)
    )
    
    dns_record = result['dns_record']
    
    return DNSRecordResponse(
        id=dns_record.id,
        record_id=dns_record.record_id,
        domain_id=dns_record.domain_id,
        tenant_id=dns_record.tenant_id,
        name=dns_record.name,
        record_type=dns_record.record_type,
        value=dns_record.value,
        ttl=dns_record.ttl,
        sync_status=dns_record.sync_status,
        updated_at=dns_record.updated_at
    )


@router.delete("/dns/{record_id}")
@rate_limit_strict(max_requests=20, time_window_seconds=60)
@standard_exception_handler
async def delete_dns_record(
    record_id: str,
    current_user: dict = Depends(get_current_user),
    domain_service: DomainService = Depends(get_domain_service)
):
    """Delete DNS record."""
    success = await domain_service.delete_dns_record(
        record_id=record_id,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"]
    )
    
    return {"success": success, "message": "DNS record deleted successfully"}


# Domain Verification

@router.post("/{domain_id}/verify", response_model=Dict)
@rate_limit_strict(max_requests=10, time_window_seconds=60)
@standard_exception_handler
async def verify_domain(
    domain_id: str,
    verification_method: str = Query("DNS", regex="^(DNS|HTTP|email)$"),
    current_user: dict = Depends(get_current_user),
    domain_service: DomainService = Depends(get_domain_service)
):
    """Initiate domain verification."""
    result = await domain_service.verify_domain(
        domain_id=domain_id,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        verification_method=verification_method
    )
    
    verification = result['verification']
    instructions = result['instructions']
    
    return {
        "verification": DomainVerificationResponse(
            id=verification.id,
            verification_id=verification.verification_id,
            domain_id=verification.domain_id,
            tenant_id=verification.tenant_id,
            verification_method=verification.verification_method,
            verification_token=verification.verification_token,
            status=verification.status,
            expires_at=verification.expires_at,
            created_at=verification.created_at
        ),
        "instructions": DomainVerificationInstructions(**instructions)
    }


@router.post("/{domain_id}/verify/check")
@rate_limit(max_requests=20, time_window_seconds=60)
@standard_exception_handler
async def check_domain_verification(
    domain_id: str,
    current_user: dict = Depends(get_current_user),
    domain_service: DomainService = Depends(get_domain_service)
):
    """Check domain verification status."""
    result = await domain_service.check_domain_verification(
        domain_id=domain_id,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"]
    )
    
    return result


# SSL Certificate Management

@router.post("/{domain_id}/ssl", response_model=SSLCertificateResponse)
@rate_limit_strict(max_requests=5, time_window_seconds=60)
@standard_exception_handler
async def request_ssl_certificate(
    domain_id: str,
    certificate_authority: str = Query("letsencrypt", description="Certificate authority"),
    current_user: dict = Depends(get_current_user),
    domain_service: DomainService = Depends(get_domain_service)
):
    """Request SSL certificate for domain."""
    result = await domain_service.request_ssl_certificate(
        domain_id=domain_id,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        certificate_authority=certificate_authority
    )
    
    ssl_certificate = result['ssl_certificate']
    
    return SSLCertificateResponse(
        id=ssl_certificate.id,
        certificate_id=ssl_certificate.certificate_id,
        domain_id=ssl_certificate.domain_id,
        tenant_id=ssl_certificate.tenant_id,
        certificate_name=ssl_certificate.certificate_name,
        common_name=ssl_certificate.common_name,
        subject_alternative_names=ssl_certificate.subject_alternative_names or [],
        issuer=ssl_certificate.issuer,
        certificate_authority=ssl_certificate.certificate_authority,
        issued_at=ssl_certificate.issued_at,
        expires_at=ssl_certificate.expires_at,
        ssl_status=ssl_certificate.ssl_status,
        auto_renew=ssl_certificate.auto_renew,
        created_at=ssl_certificate.created_at
    )


@router.get("/{domain_id}/ssl", response_model=PaginatedResponseSchema[SSLCertificateResponse])
@rate_limit(max_requests=100, time_window_seconds=60)
@standard_exception_handler
async def list_ssl_certificates(
    domain_id: str,
    current_user: dict = Depends(get_current_user),
    domain_service: DomainService = Depends(get_domain_service)
):
    """List SSL certificates for domain.\n\nReturns paginated results."""
    result = await domain_service.get_domain(
        domain_id=domain_id,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"]
    )
    
    ssl_certificates = result['ssl_certificates']
    
    certificate_responses = []
    for cert in ssl_certificates:
        certificate_responses.append(SSLCertificateResponse(
            id=cert.id,
            certificate_id=cert.certificate_id,
            domain_id=cert.domain_id,
            tenant_id=cert.tenant_id,
            certificate_name=cert.certificate_name,
            common_name=cert.common_name,
            issuer=cert.issuer,
            ssl_status=cert.ssl_status,
            issued_at=cert.issued_at,
            expires_at=cert.expires_at,
            created_at=cert.created_at
        ))
    
    return certificate_responses


# Statistics and Monitoring

@router.get("/stats/tenant", response_model=DomainStatsResponse)
@rate_limit(max_requests=20, time_window_seconds=60)
@standard_exception_handler
async def get_domain_stats(
    current_user: dict = Depends(get_current_user),
    domain_service: DomainService = Depends(get_domain_service)
):
    """Get domain statistics for current tenant."""
    stats = await domain_service.get_tenant_domain_stats(current_user["tenant_id"])
    
    return DomainStatsResponse(
        tenant_id=current_user["tenant_id"],
        **stats
    )


@router.get("/expiring/domains")
@rate_limit(max_requests=50, time_window_seconds=60)
@standard_exception_handler
async def get_expiring_domains(
    days_ahead: int = Query(30, ge=1, le=365, description="Days ahead to check"),
    current_user: dict = Depends(get_current_user),
    domain_service: DomainService = Depends(get_domain_service)
):
    """Get domains expiring within specified days."""
    expiring_domains = await domain_service.get_expiring_domains(
        tenant_id=current_user["tenant_id"],
        days_ahead=days_ahead
    )
    
    return {
        "expiring_domains": [
            {
                "domain_id": domain.domain_id,
                "full_domain": domain.full_domain,
                "expiration_date": domain.expiration_date,
                "days_until_expiration": domain.days_until_expiration
            }
            for domain in expiring_domains
        ],
        "count": len(expiring_domains),
        "days_ahead": days_ahead
    }


@router.get("/expiring/ssl")
@rate_limit(max_requests=50, time_window_seconds=60)
@standard_exception_handler
async def get_expiring_ssl_certificates(
    days_ahead: int = Query(30, ge=1, le=365, description="Days ahead to check"),
    current_user: dict = Depends(get_current_user),
    domain_service: DomainService = Depends(get_domain_service)
):
    """Get SSL certificates expiring within specified days."""
    expiring_certificates = await domain_service.get_expiring_ssl_certificates(
        tenant_id=current_user["tenant_id"],
        days_ahead=days_ahead
    )
    
    return {
        "expiring_certificates": [
            {
                "certificate_id": cert.certificate_id,
                "common_name": cert.common_name,
                "expires_at": cert.expires_at,
                "days_until_expiration": cert.days_until_expiration
            }
            for cert in expiring_certificates
        ],
        "count": len(expiring_certificates),
        "days_ahead": days_ahead
    }


# Administrative Endpoints

@router.post("/admin/process-verifications")
@rate_limit_strict(max_requests=5, time_window_seconds=300)
@standard_exception_handler
async def process_pending_verifications(
    target_tenant_id: Optional[str] = Query(None, description="Target tenant ID"),
    current_user: dict = Depends(get_current_user),
    domain_service: DomainService = Depends(get_domain_service)
):
    """Process pending domain verifications (admin only)."""
    # Check if user has admin privileges
    user_roles = current_user.get("roles", [])
    if "admin" not in user_roles:
        raise PermissionError("Admin privileges required")
    
    count = await domain_service.process_pending_verifications(target_tenant_id)
    
    return {
        "processed_verifications": count,
        "message": f"Processed {count} pending verifications"
    }


@router.post("/admin/sync-dns")
@rate_limit_strict(max_requests=5, time_window_seconds=300)
@standard_exception_handler
async def sync_dns_records(
    target_tenant_id: Optional[str] = Query(None, description="Target tenant ID"),
    current_user: dict = Depends(get_current_user),
    domain_service: DomainService = Depends(get_domain_service)
):
    """Synchronize DNS records with providers (admin only)."""
    # Check if user has admin privileges
    user_roles = current_user.get("roles", [])
    if "admin" not in user_roles:
        raise PermissionError("Admin privileges required")
    
    count = await domain_service.sync_dns_records(target_tenant_id)
    
    return {
        "synced_records": count,
        "message": f"Synchronized {count} DNS records"
    }


# Health Check

@router.get("/health")
@standard_exception_handler
async def domain_service_health():
    """Check domain service health."""
    return {
        "status": "healthy",
        "service": "domain_management",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }