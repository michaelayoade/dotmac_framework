"""
Domain Management API Router
Handles custom domain verification, DNS record management, and SSL certificate provisioning.
"""

from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field, validator
import logging

from dotmac_isp.core.dns_manager import dns_manager, DNSRecord, DNSVerificationResult

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Domain Management"])


class CustomDomainRequest(BaseModel):
    """Request model for adding custom domain"""
    domain: str = Field(..., description="Custom domain to add (e.g., portal.myisp.com)")
    tenant_id: str = Field(..., description="Tenant identifier")
    
    @validator('domain')
    def validate_domain(cls, v):
        """Basic domain validation"""
        if not v or len(v) < 3:
            raise ValueError('Domain must be at least 3 characters')
        if not '.' in v:
            raise ValueError('Domain must contain at least one dot')
        # Remove protocol if present
        if v.startswith(('http://', 'https://')):
            v = v.split('://', 1)[1]
        # Remove trailing slash
        v = v.rstrip('/')
        # Convert to lowercase
        v = v.lower()
        return v


class DomainVerificationRequest(BaseModel):
    """Request model for domain verification"""
    domain: str = Field(..., description="Domain to verify")
    
    @validator('domain')
    def validate_domain(cls, v):
        return CustomDomainRequest.validate_domain(v)


class DomainSetupResponse(BaseModel):
    """Response model for domain setup"""
    success: bool
    message: str
    tenant_id: str
    domain: str
    required_dns_records: List[Dict]
    verification_status: str = "pending"
    next_steps: List[str]


class DomainVerificationResponse(BaseModel):
    """Response model for domain verification"""
    success: bool
    message: str
    domain: str
    verification_details: Dict
    ssl_ready: bool = False


class TenantDomainStatus(BaseModel):
    """Response model for tenant domain status"""
    tenant_id: str
    primary_domain: str
    custom_domains: List[str]
    subdomain_health: Dict[str, bool]
    ssl_certificates: List[Dict]


@router.post("/setup", response_model=DomainSetupResponse)
async def setup_custom_domain(
    request: CustomDomainRequest,
    background_tasks: BackgroundTasks
) -> DomainSetupResponse:
    """
    Setup custom domain for tenant
    Returns DNS records that need to be created by the customer
    """
    try:
        logger.info(f"Setting up custom domain {request.domain} for tenant {request.tenant_id}")
        
        # Get required DNS records for the customer to create
        required_records = await dns_manager.get_required_dns_records(
            request.domain, 
            request.tenant_id
        )
        
        # Convert to dict format for response
        records_dict = [record.dict() for record in required_records]
        
        # Generate next steps instructions
        next_steps = [
            f"Add the following DNS records to your domain {request.domain}:",
            "1. Add the verification TXT record",
            "2. Add the CNAME records for your portals",
            "3. Click 'Verify Domain' to complete setup",
            f"4. Your tenant will be accessible at https://{request.domain}"
        ]
        
        return DomainSetupResponse(
            success=True,
            message=f"Custom domain setup initiated for {request.domain}",
            tenant_id=request.tenant_id,
            domain=request.domain,
            required_dns_records=records_dict,
            verification_status="pending",
            next_steps=next_steps
        )
        
    except Exception as e:
        logger.error(f"Failed to setup custom domain {request.domain}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to setup custom domain: {str(e)}"
        )


@router.post("/verify", response_model=DomainVerificationResponse)
async def verify_custom_domain(
    request: DomainVerificationRequest,
    background_tasks: BackgroundTasks
) -> DomainVerificationResponse:
    """
    Verify custom domain ownership via DNS TXT record
    """
    try:
        logger.info(f"Verifying domain ownership for {request.domain}")
        
        # Verify domain ownership
        verification_result = await dns_manager.verify_custom_domain_ownership(request.domain)
        
        if verification_result.success:
            # Domain verified - trigger SSL certificate provisioning
            logger.info(f"Domain {request.domain} verified successfully")
            
            # TODO: Trigger SSL certificate provisioning in background
            # background_tasks.add_task(provision_ssl_certificate, request.domain)
            
            return DomainVerificationResponse(
                success=True,
                message=f"Domain {request.domain} verified successfully",
                domain=request.domain,
                verification_details={
                    "verification_method": "dns_txt_record",
                    "records_found": verification_result.records_found,
                    "verified_at": "now"  # TODO: Add actual timestamp
                },
                ssl_ready=False  # Will be true after SSL provisioning
            )
        else:
            return DomainVerificationResponse(
                success=False,
                message=verification_result.message,
                domain=request.domain,
                verification_details={
                    "verification_method": "dns_txt_record",
                    "records_found": verification_result.records_found,
                    "records_missing": verification_result.records_missing,
                    "error": verification_result.message
                },
                ssl_ready=False
            )
            
    except Exception as e:
        logger.error(f"Failed to verify domain {request.domain}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Domain verification failed: {str(e)}"
        )


@router.get("/tenant/{tenant_id}/status", response_model=TenantDomainStatus)
async def get_tenant_domain_status(tenant_id: str) -> TenantDomainStatus:
    """
    Get domain status for a tenant
    """
    try:
        logger.info(f"Getting domain status for tenant {tenant_id}")
        
        # Check subdomain health
        subdomain_health = await dns_manager.check_subdomain_health(tenant_id)
        
        # TODO: Get custom domains from database
        custom_domains = []  # This would come from tenant configuration
        
        # TODO: Get SSL certificate status
        ssl_certificates = []  # This would come from certificate manager
        
        base_domain = getattr(dns_manager, 'base_domain', 'dotmac.io')
        primary_domain = f"{tenant_id}.{base_domain}"
        
        return TenantDomainStatus(
            tenant_id=tenant_id,
            primary_domain=primary_domain,
            custom_domains=custom_domains,
            subdomain_health=subdomain_health,
            ssl_certificates=ssl_certificates
        )
        
    except Exception as e:
        logger.error(f"Failed to get domain status for tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get domain status: {str(e)}"
        )


@router.delete("/tenant/{tenant_id}/domain/{domain}")
async def remove_custom_domain(
    tenant_id: str,
    domain: str,
    background_tasks: BackgroundTasks
) -> Dict[str, str]:
    """
    Remove custom domain from tenant
    """
    try:
        logger.info(f"Removing custom domain {domain} from tenant {tenant_id}")
        
        # TODO: Remove domain from tenant configuration
        # TODO: Remove SSL certificates
        # TODO: Update ingress configuration
        
        # For now, just return success
        return {
            "message": f"Custom domain {domain} removal initiated for tenant {tenant_id}",
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Failed to remove domain {domain} for tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to remove custom domain: {str(e)}"
        )


@router.get("/health")
async def domain_service_health() -> Dict[str, str]:
    """
    Check health of domain management service
    """
    try:
        # Check if DNS manager is configured
        dns_configured = dns_manager.cf is not None
        
        return {
            "status": "healthy" if dns_configured else "degraded",
            "dns_automation": "enabled" if dns_configured else "disabled",
            "message": "Domain management service is operational"
        }
        
    except Exception as e:
        logger.error(f"Domain service health check failed: {e}")
        return {
            "status": "unhealthy", 
            "message": f"Service error: {str(e)}"
        }


# Utility endpoints for development/testing

@router.get("/dns-records/{tenant_id}")
async def get_dns_records_for_tenant(
    tenant_id: str,
    custom_domain: Optional[str] = None
) -> Dict[str, List[Dict]]:
    """
    Get DNS records that should be created for a tenant
    Useful for debugging and manual setup
    """
    try:
        base_domain = getattr(dns_manager, 'base_domain', 'dotmac.io')
        load_balancer_ip = getattr(dns_manager, 'load_balancer_ip', '127.0.0.1')
        
        # Standard subdomain records
        subdomain_records = [
            {"type": "A", "name": f"{tenant_id}.{base_domain}", "content": load_balancer_ip},
            {"type": "A", "name": f"customer.{tenant_id}.{base_domain}", "content": load_balancer_ip},
            {"type": "A", "name": f"api.{tenant_id}.{base_domain}", "content": load_balancer_ip},
            {"type": "A", "name": f"billing.{tenant_id}.{base_domain}", "content": load_balancer_ip},
            {"type": "A", "name": f"support.{tenant_id}.{base_domain}", "content": load_balancer_ip},
        ]
        
        result = {
            "tenant_id": tenant_id,
            "subdomain_records": subdomain_records
        }
        
        # Custom domain records if requested
        if custom_domain:
            custom_records = await dns_manager.get_required_dns_records(custom_domain, tenant_id)
            result["custom_domain_records"] = [record.dict() for record in custom_records]
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to generate DNS records for tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate DNS records: {str(e)}"
        )