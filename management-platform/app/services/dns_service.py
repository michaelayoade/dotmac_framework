"""
DNS management service for domain configuration and record management.
Integrates with DNS providers like Route53, Cloudflare, and Google DNS.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from uuid import UUID
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from dns import resolver, exception as dns_exception
import boto3
from botocore.exceptions import ClientError

from ..core.exceptions import DNSError, ValidationError
from ..core.logging import get_logger
from ..models.dns import DNSZone, DNSRecord
from ..schemas.dns import (
    DNSRecordType,
    DNSRecordCreate,
    DNSRecordUpdate,
    DNSZoneCreate,
    DNSProviderConfig
)

logger = get_logger(__name__)


class DNSProvider(str, Enum):
    """Supported DNS providers."""
    ROUTE53 = "route53"
    CLOUDFLARE = "cloudflare"
    GOOGLE_DNS = "google_dns"
    BIND9 = "bind9"


class DNSService:
    """Service for managing DNS zones and records."""
    
    def __init__(self, db: AsyncSession, provider_config: Optional[DNSProviderConfig] = None):
        self.db = db
        self.provider_config = provider_config or DNSProviderConfig()
        self._route53_client = None
        self._cloudflare_client = None
    
    async def create_tenant_domain(
        self, 
        tenant_id: UUID, 
        domain_name: str,
        user_id: str,
        subdomain_prefix: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a domain/subdomain for a tenant with DNS zone configuration.
        
        Args:
            tenant_id: Tenant identifier
            domain_name: Base domain name
            subdomain_prefix: Optional subdomain prefix (e.g., 'tenant1' for tenant1.example.com)
            user_id: User performing the operation
            
        Returns:
            Dict containing domain configuration details
        """
        try:
            # Generate tenant domain
            if subdomain_prefix:
                tenant_domain = f"{subdomain_prefix}.{domain_name}"
            else:
                # Use tenant ID as subdomain prefix
                tenant_prefix = str(tenant_id).replace('-', '')[:8]
                tenant_domain = f"{tenant_prefix}.{domain_name}"
            
            logger.info(f"Creating domain {tenant_domain} for tenant {tenant_id}")
            
            # 1. Validate domain availability
            await self._validate_domain_availability(tenant_domain)
            
            # 2. Create DNS zone
            zone = await self._create_dns_zone(tenant_id, tenant_domain, user_id)
            
            # 3. Configure default DNS records
            default_records = await self._create_default_dns_records(zone)
            
            # 4. Set up SSL certificate (if supported)
            ssl_config = await self._setup_ssl_certificate(tenant_domain)
            
            # 5. Configure CDN (if enabled)
            cdn_config = await self._setup_cdn_configuration(tenant_domain)
            
            logger.info(f"Domain {tenant_domain} created successfully for tenant {tenant_id}")
            
            return {
                "tenant_id": str(tenant_id),
                "domain": tenant_domain,
                "zone_id": str(zone.id),
                "dns_records": default_records,
                "ssl_certificate": ssl_config,
                "cdn_configuration": cdn_config,
                "nameservers": await self._get_nameservers(zone),
                "created_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Domain creation failed for tenant {tenant_id}: {e}")
            raise DNSError(f"Domain creation failed: {e}")
    
    async def create_dns_record(
        self,
        tenant_id: UUID,
        zone_id: UUID,
        record_data: DNSRecordCreate,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Create a DNS record in the specified zone.
        
        Args:
            tenant_id: Tenant identifier
            zone_id: DNS zone identifier
            record_data: DNS record configuration
            user_id: User performing the operation
            
        Returns:
            Dict containing created DNS record details
        """
        try:
            logger.info(f"Creating DNS record {record_data.name} for tenant {tenant_id}")
            
            # 1. Validate zone ownership
            zone = await self._get_tenant_zone(zone_id, tenant_id)
            if not zone:
                raise ValidationError(f"DNS zone {zone_id} not found for tenant {tenant_id}")
            
            # 2. Validate record data
            await self._validate_dns_record(record_data, zone.domain)
            
            # 3. Create record in database
            dns_record = await self._create_dns_record_db(
                zone_id, record_data, user_id
            )
            
            # 4. Create record with DNS provider
            provider_record_id = await self._create_provider_record(
                zone, dns_record
            )
            
            # 5. Update record with provider ID
            await self._update_record_provider_id(
                dns_record.id, provider_record_id
            )
            
            # 6. Verify propagation
            propagation_status = await self._check_dns_propagation(
                dns_record.name, dns_record.record_type, dns_record.value
            )
            
            return {
                "record_id": str(dns_record.id),
                "zone_id": str(zone_id),
                "name": dns_record.name,
                "type": dns_record.record_type,
                "value": dns_record.value,
                "ttl": dns_record.ttl,
                "provider_record_id": provider_record_id,
                "propagation_status": propagation_status,
                "created_at": dns_record.created_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"DNS record creation failed: {e}")
            raise DNSError(f"DNS record creation failed: {e}")
    
    async def update_dns_record(
        self,
        tenant_id: UUID,
        record_id: UUID,
        record_update: DNSRecordUpdate,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Update an existing DNS record.
        
        Args:
            tenant_id: Tenant identifier
            record_id: DNS record identifier
            record_update: Updated record data
            user_id: User performing the operation
            
        Returns:
            Dict containing updated DNS record details
        """
        try:
            logger.info(f"Updating DNS record {record_id} for tenant {tenant_id}")
            
            # 1. Get existing record
            dns_record = await self._get_tenant_dns_record(record_id, tenant_id)
            if not dns_record:
                raise ValidationError(f"DNS record {record_id} not found")
            
            # 2. Validate update data
            if record_update.value:
                await self._validate_record_value(
                    dns_record.record_type, record_update.value
                )
            
            # 3. Update record with provider
            await self._update_provider_record(dns_record, record_update)
            
            # 4. Update record in database
            updated_record = await self._update_dns_record_db(
                record_id, record_update, user_id
            )
            
            # 5. Verify propagation
            propagation_status = await self._check_dns_propagation(
                updated_record.name, 
                updated_record.record_type, 
                updated_record.value
            )
            
            return {
                "record_id": str(record_id),
                "name": updated_record.name,
                "type": updated_record.record_type,
                "value": updated_record.value,
                "ttl": updated_record.ttl,
                "propagation_status": propagation_status,
                "updated_at": updated_record.updated_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"DNS record update failed: {e}")
            raise DNSError(f"DNS record update failed: {e}")
    
    async def delete_dns_record(
        self,
        tenant_id: UUID,
        record_id: UUID,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Delete a DNS record.
        
        Args:
            tenant_id: Tenant identifier
            record_id: DNS record identifier
            user_id: User performing the operation
            
        Returns:
            Dict containing deletion status
        """
        try:
            logger.info(f"Deleting DNS record {record_id} for tenant {tenant_id}")
            
            # 1. Get existing record
            dns_record = await self._get_tenant_dns_record(record_id, tenant_id)
            if not dns_record:
                raise ValidationError(f"DNS record {record_id} not found")
            
            # 2. Delete from provider
            await self._delete_provider_record(dns_record)
            
            # 3. Delete from database
            await self._delete_dns_record_db(record_id)
            
            return {
                "record_id": str(record_id),
                "deleted_at": datetime.utcnow().isoformat(),
                "deleted_by": user_id
            }
            
        except Exception as e:
            logger.error(f"DNS record deletion failed: {e}")
            raise DNSError(f"DNS record deletion failed: {e}")
    
    async def get_dns_records(
        self,
        tenant_id: UUID,
        zone_id: Optional[UUID] = None,
        record_type: Optional[DNSRecordType] = None
    ) -> Dict[str, Any]:
        """
        Get DNS records for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            zone_id: Optional zone filter
            record_type: Optional record type filter
            
        Returns:
            Dict containing DNS records
        """
        try:
            # Build query filters
            filters = [DNSRecord.zone.has(DNSZone.tenant_id == tenant_id)]
            
            if zone_id:
                filters.append(DNSRecord.zone_id == zone_id)
            
            if record_type:
                filters.append(DNSRecord.record_type == record_type)
            
            # Execute query
            result = await self.db.execute(
                select(DNSRecord).where(*filters).order_by(DNSRecord.name)
            )
            records = result.scalars().all()
            
            # Format response
            record_list = []
            for record in records:
                # Get real-time status
                propagation_status = await self._check_dns_propagation(
                    record.name, record.record_type, record.value
                )
                
                record_list.append({
                    "record_id": str(record.id),
                    "zone_id": str(record.zone_id),
                    "name": record.name,
                    "type": record.record_type,
                    "value": record.value,
                    "ttl": record.ttl,
                    "priority": record.priority,
                    "propagation_status": propagation_status,
                    "created_at": record.created_at.isoformat(),
                    "updated_at": record.updated_at.isoformat()
                })
            
            return {
                "tenant_id": str(tenant_id),
                "total_records": len(record_list),
                "records": record_list
            }
            
        except Exception as e:
            logger.error(f"Failed to get DNS records: {e}")
            raise DNSError(f"Failed to get DNS records: {e}")
    
    async def verify_domain_ownership(
        self,
        tenant_id: UUID,
        domain: str,
        verification_method: str = "txt_record"
    ) -> Dict[str, Any]:
        """
        Verify domain ownership using DNS verification.
        
        Args:
            tenant_id: Tenant identifier
            domain: Domain to verify
            verification_method: Verification method (txt_record, cname, meta_tag)
            
        Returns:
            Dict containing verification status and instructions
        """
        try:
            logger.info(f"Starting domain verification for {domain} (tenant: {tenant_id})")
            
            if verification_method == "txt_record":
                # Generate verification token
                verification_token = f"dotmac-verify-{str(tenant_id).replace('-', '')[:16]}"
                
                # Create verification record
                verification_record = f"_dotmac-verification.{domain}"
                
                # Check if verification record exists
                verification_status = await self._check_txt_record(
                    verification_record, verification_token
                )
                
                return {
                    "domain": domain,
                    "verification_method": "txt_record",
                    "verification_record": verification_record,
                    "verification_value": verification_token,
                    "status": "verified" if verification_status else "pending",
                    "instructions": f"Add TXT record '{verification_record}' with value '{verification_token}'"
                }
            
            elif verification_method == "cname":
                # CNAME verification
                cname_target = f"verify.{domain}.dotmac.local"
                cname_record = f"_dotmac-verify.{domain}"
                
                verification_status = await self._check_cname_record(
                    cname_record, cname_target
                )
                
                return {
                    "domain": domain,
                    "verification_method": "cname",
                    "verification_record": cname_record,
                    "verification_target": cname_target,
                    "status": "verified" if verification_status else "pending",
                    "instructions": f"Add CNAME record '{cname_record}' pointing to '{cname_target}'"
                }
            
            else:
                raise ValidationError(f"Unsupported verification method: {verification_method}")
            
        except Exception as e:
            logger.error(f"Domain verification failed: {e}")
            raise DNSError(f"Domain verification failed: {e}")
    
    async def setup_load_balancer_dns(
        self,
        tenant_id: UUID,
        zone_id: UUID,
        load_balancer_config: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """
        Set up DNS records for load balancer configuration.
        
        Args:
            tenant_id: Tenant identifier
            zone_id: DNS zone identifier
            load_balancer_config: Load balancer configuration
            user_id: User performing the operation
            
        Returns:
            Dict containing load balancer DNS configuration
        """
        try:
            logger.info(f"Setting up load balancer DNS for tenant {tenant_id}")
            
            zone = await self._get_tenant_zone(zone_id, tenant_id)
            if not zone:
                raise ValidationError(f"DNS zone {zone_id} not found")
            
            lb_records = []
            
            # Create A records for load balancer IPs
            if load_balancer_config.get("ipv4_addresses"):
                for i, ip in enumerate(load_balancer_config["ipv4_addresses"]):
                    record_data = DNSRecordCreate(
                        name=f"lb{i+1}.{zone.domain}",
                        record_type=DNSRecordType.A,
                        value=ip,
                        ttl=300
                    )
                    
                    record = await self.create_dns_record(
                        tenant_id, zone_id, record_data, user_id
                    )
                    lb_records.append(record)
            
            # Create AAAA records for IPv6
            if load_balancer_config.get("ipv6_addresses"):
                for i, ip in enumerate(load_balancer_config["ipv6_addresses"]):
                    record_data = DNSRecordCreate(
                        name=f"lb{i+1}.{zone.domain}",
                        record_type=DNSRecordType.AAAA,
                        value=ip,
                        ttl=300
                    )
                    
                    record = await self.create_dns_record(
                        tenant_id, zone_id, record_data, user_id
                    )
                    lb_records.append(record)
            
            # Create main application CNAME
            if load_balancer_config.get("primary_endpoint"):
                app_record_data = DNSRecordCreate(
                    name=f"app.{zone.domain}",
                    record_type=DNSRecordType.CNAME,
                    value=load_balancer_config["primary_endpoint"],
                    ttl=300
                )
                
                app_record = await self.create_dns_record(
                    tenant_id, zone_id, app_record_data, user_id
                )
                lb_records.append(app_record)
            
            # Create health check record
            health_record_data = DNSRecordCreate(
                name=f"health.{zone.domain}",
                record_type=DNSRecordType.CNAME,
                value=f"lb1.{zone.domain}",
                ttl=60
            )
            
            health_record = await self.create_dns_record(
                tenant_id, zone_id, health_record_data, user_id
            )
            lb_records.append(health_record)
            
            return {
                "tenant_id": str(tenant_id),
                "zone_id": str(zone_id),
                "load_balancer_records": lb_records,
                "endpoints": {
                    "application": f"app.{zone.domain}",
                    "health_check": f"health.{zone.domain}",
                    "load_balancers": [f"lb{i+1}.{zone.domain}" for i in range(len(load_balancer_config.get("ipv4_addresses", [])))]
                },
                "configured_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Load balancer DNS setup failed: {e}")
            raise DNSError(f"Load balancer DNS setup failed: {e}")
    
    # Private methods
    
    async def _validate_domain_availability(self, domain: str) -> None:
        """Validate that domain is available for use."""
        # Check if domain already exists in our system
        result = await self.db.execute(
            select(DNSZone).where(DNSZone.domain == domain)
        )
        existing_zone = result.scalar_one_or_none()
        
        if existing_zone:
            raise ValidationError(f"Domain {domain} is already configured")
        
        # Check if domain is resolvable (basic availability check)
        try:
            resolver.resolve(domain, 'A')
            logger.warning(f"Domain {domain} already has DNS records - proceeding with caution")
        except dns_exception.NXDOMAIN:
            # Domain doesn't exist - good for new setup
            pass
        except Exception as e:
            logger.warning(f"DNS lookup error for {domain}: {e}")
    
    async def _create_dns_zone(
        self, 
        tenant_id: UUID, 
        domain: str, 
        user_id: str
    ) -> DNSZone:
        """Create DNS zone in database."""
        zone = DNSZone(
            tenant_id=tenant_id,
            domain=domain,
            provider=self.provider_config.primary_provider,
            is_active=True,
            metadata={
                "created_by": user_id,
                "provider_config": self.provider_config.dict()
            }
        )
        
        self.db.add(zone)
        await self.db.commit()
        await self.db.refresh(zone)
        
        return zone
    
    async def _create_default_dns_records(self, zone: DNSZone) -> List[Dict[str, Any]]:
        """Create default DNS records for new zone."""
        default_records = []
        
        # SOA record
        soa_value = f"ns1.dotmac.local. admin.{zone.domain}. 1 7200 900 1209600 86400"
        soa_record = DNSRecord(
            zone_id=zone.id,
            name=zone.domain,
            record_type=DNSRecordType.SOA,
            value=soa_value,
            ttl=86400
        )
        self.db.add(soa_record)
        default_records.append({
            "name": zone.domain,
            "type": "SOA",
            "value": soa_value,
            "ttl": 86400
        })
        
        # NS records
        nameservers = ["ns1.dotmac.local.", "ns2.dotmac.local."]
        for ns in nameservers:
            ns_record = DNSRecord(
                zone_id=zone.id,
                name=zone.domain,
                record_type=DNSRecordType.NS,
                value=ns,
                ttl=86400
            )
            self.db.add(ns_record)
            default_records.append({
                "name": zone.domain,
                "type": "NS",
                "value": ns,
                "ttl": 86400
            })
        
        # Default A record (placeholder)
        a_record = DNSRecord(
            zone_id=zone.id,
            name=zone.domain,
            record_type=DNSRecordType.A,
            value="203.0.113.1",  # Placeholder IP
            ttl=300
        )
        self.db.add(a_record)
        default_records.append({
            "name": zone.domain,
            "type": "A",
            "value": "203.0.113.1",
            "ttl": 300
        })
        
        await self.db.commit()
        return default_records
    
    async def _setup_ssl_certificate(self, domain: str) -> Dict[str, Any]:
        """Set up SSL certificate for domain."""
        # Simulate SSL certificate setup
        return {
            "certificate_arn": f"arn:aws:acm:us-east-1:123456789012:certificate/{domain.replace('.', '-')}",
            "status": "issued",
            "expires_at": (datetime.utcnow() + timedelta(days=90)).isoformat(),
            "auto_renewal": True
        }
    
    async def _setup_cdn_configuration(self, domain: str) -> Dict[str, Any]:
        """Set up CDN configuration for domain."""
        # Simulate CDN setup
        return {
            "distribution_id": f"E{domain.replace('.', '').upper()[:12]}",
            "domain_name": f"{domain.replace('.', '-')}.cloudfront.net",
            "status": "deployed",
            "cache_behaviors": ["/*"]
        }
    
    async def _get_nameservers(self, zone: DNSZone) -> List[str]:
        """Get nameservers for zone."""
        # Return default nameservers
        return ["ns1.dotmac.local", "ns2.dotmac.local"]
    
    async def _validate_dns_record(self, record_data: DNSRecordCreate, zone_domain: str) -> None:
        """Validate DNS record data."""
        # Validate record name
        if not record_data.name.endswith(zone_domain) and record_data.name != zone_domain:
            if not record_data.name.endswith(f".{zone_domain}"):
                record_data.name = f"{record_data.name}.{zone_domain}"
        
        # Validate record value based on type
        await self._validate_record_value(record_data.record_type, record_data.value)
    
    async def _validate_record_value(self, record_type: DNSRecordType, value: str) -> None:
        """Validate DNS record value based on type."""
        import ipaddress
        import re
        
        if record_type == DNSRecordType.A:
            try:
                ipaddress.IPv4Address(value)
            except ipaddress.AddressValueError:
                raise ValidationError(f"Invalid IPv4 address: {value}")
        
        elif record_type == DNSRecordType.AAAA:
            try:
                ipaddress.IPv6Address(value)
            except ipaddress.AddressValueError:
                raise ValidationError(f"Invalid IPv6 address: {value}")
        
        elif record_type == DNSRecordType.CNAME:
            if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*\.$?', value):
                raise ValidationError(f"Invalid CNAME value: {value}")
        
        elif record_type == DNSRecordType.MX:
            if not re.match(r'^\d+\s+[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*\.$?', value):
                raise ValidationError(f"Invalid MX record format: {value}")
    
    async def _create_dns_record_db(
        self, 
        zone_id: UUID, 
        record_data: DNSRecordCreate, 
        user_id: str
    ) -> DNSRecord:
        """Create DNS record in database."""
        dns_record = DNSRecord(
            zone_id=zone_id,
            name=record_data.name,
            record_type=record_data.record_type,
            value=record_data.value,
            ttl=record_data.ttl,
            priority=record_data.priority,
            metadata={
                "created_by": user_id
            }
        )
        
        self.db.add(dns_record)
        await self.db.commit()
        await self.db.refresh(dns_record)
        
        return dns_record
    
    async def _create_provider_record(self, zone: DNSZone, record: DNSRecord) -> str:
        """Create DNS record with provider."""
        if zone.provider == DNSProvider.ROUTE53:
            return await self._create_route53_record(zone, record)
        elif zone.provider == DNSProvider.CLOUDFLARE:
            return await self._create_cloudflare_record(zone, record)
        else:
            # Simulate provider record creation
            return f"provider-{record.id.hex[:16]}"
    
    async def _create_route53_record(self, zone: DNSZone, record: DNSRecord) -> str:
        """Create Route53 DNS record."""
        # This would use boto3 Route53 client in real implementation
        logger.info(f"Creating Route53 record: {record.name} -> {record.value}")
        return f"route53-{record.id.hex[:16]}"
    
    async def _create_cloudflare_record(self, zone: DNSZone, record: DNSRecord) -> str:
        """Create Cloudflare DNS record."""
        # This would use Cloudflare API in real implementation
        logger.info(f"Creating Cloudflare record: {record.name} -> {record.value}")
        return f"cf-{record.id.hex[:16]}"
    
    async def _check_dns_propagation(
        self, 
        name: str, 
        record_type: DNSRecordType, 
        expected_value: str
    ) -> Dict[str, Any]:
        """Check DNS propagation status."""
        try:
            # Query multiple DNS servers
            dns_servers = ["8.8.8.8", "1.1.1.1", "208.67.222.222"]
            propagation_results = []
            
            for dns_server in dns_servers:
                try:
                    custom_resolver = resolver.Resolver()
                    custom_resolver.nameservers = [dns_server]
                    
                    answers = custom_resolver.resolve(name, record_type.value)
                    actual_values = [str(answer) for answer in answers]
                    
                    is_propagated = expected_value in actual_values
                    propagation_results.append({
                        "dns_server": dns_server,
                        "propagated": is_propagated,
                        "actual_values": actual_values
                    })
                    
                except Exception as e:
                    propagation_results.append({
                        "dns_server": dns_server,
                        "propagated": False,
                        "error": str(e)
                    })
            
            total_propagated = sum(1 for result in propagation_results if result.get("propagated", False))
            propagation_percentage = (total_propagated / len(dns_servers)) * 100
            
            return {
                "status": "fully_propagated" if propagation_percentage == 100 else "partially_propagated" if propagation_percentage > 0 else "not_propagated",
                "percentage": propagation_percentage,
                "servers_checked": len(dns_servers),
                "servers_propagated": total_propagated,
                "details": propagation_results,
                "checked_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"DNS propagation check failed: {e}")
            return {
                "status": "check_failed",
                "error": str(e),
                "checked_at": datetime.utcnow().isoformat()
            }
    
    async def _check_txt_record(self, record_name: str, expected_value: str) -> bool:
        """Check if TXT record exists with expected value."""
        try:
            answers = resolver.resolve(record_name, 'TXT')
            for answer in answers:
                if expected_value in str(answer):
                    return True
            return False
        except:
            return False
    
    async def _check_cname_record(self, record_name: str, expected_target: str) -> bool:
        """Check if CNAME record exists with expected target."""
        try:
            answers = resolver.resolve(record_name, 'CNAME')
            for answer in answers:
                if expected_target in str(answer):
                    return True
            return False
        except:
            return False
    
    async def _get_tenant_zone(self, zone_id: UUID, tenant_id: UUID) -> Optional[DNSZone]:
        """Get DNS zone for tenant."""
        result = await self.db.execute(
            select(DNSZone).where(
                DNSZone.id == zone_id,
                DNSZone.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()
    
    async def _get_tenant_dns_record(self, record_id: UUID, tenant_id: UUID) -> Optional[DNSRecord]:
        """Get DNS record for tenant."""
        result = await self.db.execute(
            select(DNSRecord).join(DNSZone).where(
                DNSRecord.id == record_id,
                DNSZone.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()
    
    async def _update_record_provider_id(self, record_id: UUID, provider_record_id: str):
        """Update record with provider ID."""
        await self.db.execute(
            update(DNSRecord)
            .where(DNSRecord.id == record_id)
            .values(
                provider_record_id=provider_record_id,
                updated_at=datetime.utcnow()
            )
        )
        await self.db.commit()
    
    async def _update_provider_record(self, record: DNSRecord, update_data: DNSRecordUpdate):
        """Update DNS record with provider."""
        # Implementation for provider record updates
        logger.info(f"Updating provider record {record.provider_record_id}")
    
    async def _delete_provider_record(self, record: DNSRecord):
        """Delete DNS record from provider."""
        # Implementation for provider record deletion
        logger.info(f"Deleting provider record {record.provider_record_id}")
    
    async def _update_dns_record_db(
        self, 
        record_id: UUID, 
        update_data: DNSRecordUpdate, 
        user_id: str
    ) -> DNSRecord:
        """Update DNS record in database."""
        update_values = {"updated_at": datetime.utcnow()}
        
        if update_data.value:
            update_values["value"] = update_data.value
        if update_data.ttl:
            update_values["ttl"] = update_data.ttl
        if update_data.priority is not None:
            update_values["priority"] = update_data.priority
        
        await self.db.execute(
            update(DNSRecord)
            .where(DNSRecord.id == record_id)
            .values(**update_values)
        )
        await self.db.commit()
        
        result = await self.db.execute(
            select(DNSRecord).where(DNSRecord.id == record_id)
        )
        return result.scalar_one()
    
    async def _delete_dns_record_db(self, record_id: UUID):
        """Delete DNS record from database."""
        await self.db.execute(
            delete(DNSRecord).where(DNSRecord.id == record_id)
        )
        await self.db.commit()