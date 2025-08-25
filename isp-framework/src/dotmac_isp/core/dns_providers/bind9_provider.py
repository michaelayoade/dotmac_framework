"""
BIND9 DNS Provider - Traditional DNS Server
File-based DNS management with zone file generation
"""

import os
import subprocess
import logging
from typing import Dict, List
from pathlib import Path

logger = logging.getLogger(__name__)


class Bind9Provider:
    """BIND9 DNS provider using zone file management"""
    
    def __init__(self):
        self.zone_dir = "/etc/bind/zones"
        self.base_domain = "dotmac.io" 
        self.zone_file = f"{self.zone_dir}/{self.base_domain}.zone"
        self.serial_file = f"{self.zone_dir}/.{self.base_domain}.serial"
        
    def get_next_serial(self) -> str:
        """Generate next DNS serial number"""
        from datetime import datetime
        base_serial = datetime.now().strftime("%Y%m%d")
        
        if os.path.exists(self.serial_file):
            with open(self.serial_file, 'r') as f:
                last_serial = f.read().strip()
                if last_serial.startswith(base_serial):
                    # Same day, increment
                    counter = int(last_serial[-2:]) + 1
                    serial = f"{base_serial}{counter:02d}"
                else:
                    # New day
                    serial = f"{base_serial}01"
        else:
            serial = f"{base_serial}01"
        
        # Save serial
        with open(self.serial_file, 'w') as f:
            f.write(serial)
        
        return serial
    
    def create_tenant_records(self, tenant_id: str, load_balancer_ip: str) -> Dict[str, bool]:
        """Add tenant records to BIND zone file"""
        try:
            records_to_add = [
                f"{tenant_id}                    IN A     {load_balancer_ip}",
                f"customer.{tenant_id}           IN A     {load_balancer_ip}",
                f"api.{tenant_id}                IN A     {load_balancer_ip}",
                f"billing.{tenant_id}            IN A     {load_balancer_ip}",
                f"support.{tenant_id}            IN A     {load_balancer_ip}",
            ]
            
            # Read existing zone file
            if os.path.exists(self.zone_file):
                with open(self.zone_file, 'r') as f:
                    zone_content = f.read()
            else:
                # Create basic zone file
                zone_content = self._create_base_zone_file()
            
            # Update serial number in SOA record
            new_serial = self.get_next_serial()
            zone_content = self._update_serial_in_zone(zone_content, new_serial)
            
            # Add tenant records
            zone_content += "\n; Tenant records for " + tenant_id + "\n"
            for record in records_to_add:
                zone_content += record + "\n"
            
            # Write updated zone file
            with open(self.zone_file, 'w') as f:
                f.write(zone_content)
            
            # Reload BIND9
            self._reload_bind9()
            
            logger.info(f"✅ Added BIND9 records for tenant: {tenant_id}")
            return {f"{tenant_id}.{self.base_domain}": True}
            
        except Exception as e:
            logger.error(f"❌ Failed to add BIND9 records for {tenant_id}: {e}")
            return {f"{tenant_id}.{self.base_domain}": False}
    
    def _create_base_zone_file(self) -> str:
        """Create basic zone file template"""
        return f"""$TTL 300
@       IN SOA  ns1.{self.base_domain}. admin.{self.base_domain}. (
                2024010101  ; Serial
                3600        ; Refresh
                1800        ; Retry  
                604800      ; Expire
                300         ; Minimum TTL
                )

; Name servers
@       IN NS   ns1.{self.base_domain}.
@       IN NS   ns2.{self.base_domain}.

; Main domain
@       IN A    127.0.0.1
ns1     IN A    127.0.0.1
ns2     IN A    127.0.0.1

"""
    
    def _update_serial_in_zone(self, zone_content: str, new_serial: str) -> str:
        """Update serial number in SOA record"""
        import re
        pattern = r'(\d{10})\s*;\s*Serial'
        return re.sub(pattern, f'{new_serial}  ; Serial', zone_content)
    
    def _reload_bind9(self):
        """Reload BIND9 configuration"""
        try:
            # Test configuration first
            result = subprocess.run(['named-checkconf'], capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"BIND9 config check failed: {result.stderr}")
                return False
            
            # Test zone file
            result = subprocess.run(['named-checkzone', self.base_domain, self.zone_file], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"Zone file check failed: {result.stderr}")
                return False
            
            # Reload BIND9
            subprocess.run(['rndc', 'reload'], check=True)
            logger.info("✅ BIND9 reloaded successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to reload BIND9: {e}")
            return False
        except FileNotFoundError:
            logger.error("BIND9 tools not found. Install with: apt-get install bind9-utils")
            return False