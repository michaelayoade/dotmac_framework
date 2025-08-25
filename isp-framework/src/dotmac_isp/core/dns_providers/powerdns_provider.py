"""
PowerDNS DNS Provider - Open Source Alternative
Self-hosted DNS management with API automation
"""

import asyncio
import logging
from typing import Dict, List, Optional
import aiohttp
from pydantic import BaseModel

from ..settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class PowerDNSRecord(BaseModel):
    """PowerDNS record model"""
    name: str
    type: str
    content: str
    ttl: int = 300


class PowerDNSProvider:
    """Open source DNS provider using PowerDNS"""
    
    def __init__(self):
        self.api_url = getattr(settings, 'POWERDNS_API_URL', 'http://localhost:8081')
        self.api_key = getattr(settings, 'POWERDNS_API_KEY', None)
        self.zone_name = getattr(settings, 'BASE_DOMAIN', 'dotmac.io')
        self.headers = {
            'X-API-Key': self.api_key,
            'Content-Type': 'application/json'
        }
    
    async def create_records(self, tenant_id: str) -> Dict[str, bool]:
        """Create DNS records for tenant using PowerDNS API"""
        if not self.api_key:
            logger.error("PowerDNS API key not configured")
            return {"error": "DNS provider not configured"}
        
        records_to_create = [
            f"{tenant_id}.{self.zone_name}",
            f"customer.{tenant_id}.{self.zone_name}",
            f"api.{tenant_id}.{self.zone_name}",
            f"billing.{tenant_id}.{self.zone_name}",
        ]
        
        results = {}
        load_balancer_ip = getattr(settings, 'LOAD_BALANCER_IP', '127.0.0.1')
        
        async with aiohttp.ClientSession() as session:
            for record_name in records_to_create:
                try:
                    # PowerDNS API format
                    rrsets_data = {
                        "rrsets": [
                            {
                                "name": record_name,
                                "type": "A",
                                "changetype": "REPLACE",
                                "records": [
                                    {
                                        "content": load_balancer_ip,
                                        "disabled": False
                                    }
                                ]
                            }
                        ]
                    }
                    
                    url = f"{self.api_url}/api/v1/servers/localhost/zones/{self.zone_name}"
                    
                    async with session.patch(url, json=rrsets_data, headers=self.headers) as response:
                        if response.status == 204:
                            results[record_name] = True
                            logger.info(f"✅ Created PowerDNS record: {record_name}")
                        else:
                            error_text = await response.text()
                            results[record_name] = False
                            logger.error(f"❌ Failed to create PowerDNS record {record_name}: {error_text}")
                
                except Exception as e:
                    logger.error(f"Error creating PowerDNS record {record_name}: {e}")
                    results[record_name] = False
        
        return results
    
    async def verify_domain_ownership(self, domain: str) -> Dict[str, bool]:
        """Verify domain ownership using DNS TXT record"""
        verification_record = f"_dotmac-verify.{domain}"
        
        try:
            import dns.resolver
            resolver = dns.resolver.Resolver()
            answers = resolver.resolve(verification_record, 'TXT')
            
            for rdata in answers:
                txt_content = str(rdata).strip('"')
                if "dotmac-domain-verification" in txt_content:
                    return {"success": True, "message": f"Domain {domain} verified"}
            
            return {"success": False, "message": "Verification record not found"}
            
        except Exception as e:
            logger.error(f"Domain verification failed for {domain}: {e}")
            return {"success": False, "message": str(e)}