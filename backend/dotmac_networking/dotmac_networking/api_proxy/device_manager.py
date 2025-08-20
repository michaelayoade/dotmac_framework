"""
Unified Device Manager - Combines DotMac networking SDKs with OpenWISP Controller.
Identifies overlaps and provides single interface for device management.
"""

from typing import Any, Dict, List, Optional, Union
from uuid import uuid4
import asyncio

from ..core.database import db_manager
from ..repositories.base_repository import BaseRepository
from ..sdks.device_inventory import DeviceInventorySDK
from ..sdks.device_config import DeviceConfigSDK
from ..sdks.device_provisioning import DeviceProvisioningSDK
from .openwisp_proxy import OpenWISPProxy


class UnifiedDeviceManager:
    """
    Unified device management combining:
    - DotMac Device Inventory SDK (local device registry)
    - DotMac Device Config SDK (configuration templates)
    - DotMac Device Provisioning SDK (orchestration workflows)
    - OpenWISP Controller API (OpenWrt device management)
    
    OVERLAP ANALYSIS:
    ┌─────────────────────┬──────────────────┬──────────────────────┐
    │ Capability          │ DotMac SDK       │ OpenWISP Controller  │
    ├─────────────────────┼──────────────────┼──────────────────────┤
    │ Device Registry     │ ✅ Full ISP      │ ❌ OpenWrt only      │
    │ Config Templates    │ ✅ Multi-vendor  │ ✅ OpenWrt + UCI     │
    │ Config Deployment   │ ❌ SSH/NETCONF   │ ✅ Agent-based      │
    │ Provisioning        │ ✅ Orchestration │ ❌ Basic            │
    │ Multi-tenant        │ ✅ Per tenant    │ ✅ Organizations    │
    │ Vendor Support      │ ✅ Cisco/Juniper │ ✅ OpenWrt focus    │
    │ Config Drift        │ ✅ Detection     │ ✅ Monitoring       │
    └─────────────────────┴──────────────────┴──────────────────────┘
    
    STRATEGY: Use DotMac as primary registry, OpenWISP for OpenWrt management
    """
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        
        # DotMac SDKs for comprehensive device management
        self.inventory = DeviceInventorySDK(tenant_id)
        self.config = DeviceConfigSDK(tenant_id) 
        self.provisioning = DeviceProvisioningSDK(tenant_id)
        
        # OpenWISP proxy for OpenWrt-specific operations
        self.openwisp = OpenWISPProxy()
        
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Initialize database connections."""
        if not self._initialized:
            # Initialize database pool if needed
            if db_manager._pool is None:
                await db_manager.initialize_pool()
            self._initialized = True
    
    # =============================================================================
    # UNIFIED DEVICE REGISTRY (Primary: DotMac, Sync: OpenWISP)
    # =============================================================================
    
    async def register_device(
        self, 
        device_id: str,
        device_type: str,
        vendor: str,
        model: str,
        site_id: str,
        management_ip: Optional[str] = None,
        is_openwisp_managed: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Register device in unified registry.
        - Stores in DotMac inventory (all vendors)
        - If OpenWrt device, also registers in OpenWISP
        """
        await self._ensure_initialized()
        
        # Register in DotMac inventory (primary registry)
        device = await self.inventory.register_device(
            device_id=device_id,
            device_type=device_type,
            vendor=vendor,
            model=model,
            site_id=site_id,
            management_ip=management_ip,
            **kwargs
        )
        
        # If OpenWrt device, also register in OpenWISP
        openwisp_device = None
        if is_openwisp_managed and vendor.lower() in ['openwrt', 'openwrt-device']:
            try:
                openwisp_data = {
                    'name': device_id,
                    'mac_address': kwargs.get('mac_address', ''),
                    'management_ip': management_ip,
                    'model': model,
                    'os': 'OpenWrt',
                    'organization': self._get_openwisp_org_id(),
                    **kwargs
                }
                
                openwisp_device = await self.openwisp.devices.create_device(openwisp_data)
                
                # Update DotMac record with OpenWISP device ID
                device['openwisp_device_id'] = openwisp_device.get('id')
                
            except Exception as e:
                print(f"Warning: Failed to register device in OpenWISP: {e}")
        
        return {
            'device_id': device['device_id'],
            'device_type': device['device_type'],
            'vendor': device['vendor'],
            'model': device['model'],
            'site_id': device['site_id'],
            'management_ip': device.get('management_ip'),
            'dotmac_managed': True,
            'openwisp_managed': bool(openwisp_device),
            'openwisp_device_id': openwisp_device.get('id') if openwisp_device else None,
            'created_at': device['created_at']
        }
    
    async def get_device(self, device_id: str, include_openwisp: bool = True) -> Optional[Dict[str, Any]]:
        """Get device from unified registry with optional OpenWISP data."""
        await self._ensure_initialized()
        
        # Get from DotMac inventory
        device = await self.inventory.get_device(device_id)
        if not device:
            return None
        
        # Enrich with OpenWISP data if available
        if include_openwisp and device.get('openwisp_device_id'):
            try:
                openwisp_device = await self.openwisp.devices.get_device(device['openwisp_device_id'])
                device['openwisp_data'] = openwisp_device
                device['config_status'] = openwisp_device.get('config', {}).get('status')
                device['last_seen'] = openwisp_device.get('last_ip')
            except Exception as e:
                print(f"Warning: Failed to fetch OpenWISP data: {e}")
        
        return device
    
    async def list_devices(
        self, 
        site_id: Optional[str] = None,
        device_type: Optional[str] = None,
        vendor: Optional[str] = None,
        include_openwisp: bool = False
    ) -> List[Dict[str, Any]]:
        """List devices from unified registry."""
        await self._ensure_initialized()
        
        # Get from DotMac inventory
        devices = await self.inventory.list_devices(
            site_id=site_id,
            device_type=device_type, 
            vendor=vendor
        )
        
        # Optionally enrich with OpenWISP data
        if include_openwisp:
            openwisp_devices = {}
            try:
                openwisp_list = await self.openwisp.devices.list_devices(
                    organization_id=self._get_openwisp_org_id()
                )
                openwisp_devices = {d['id']: d for d in openwisp_list}
            except Exception as e:
                print(f"Warning: Failed to fetch OpenWISP devices: {e}")
            
            for device in devices:
                openwisp_id = device.get('openwisp_device_id')
                if openwisp_id and openwisp_id in openwisp_devices:
                    openwisp_data = openwisp_devices[openwisp_id]
                    device['config_status'] = openwisp_data.get('config', {}).get('status')
                    device['last_seen'] = openwisp_data.get('last_ip')
        
        return devices
    
    # =============================================================================
    # UNIFIED CONFIGURATION MANAGEMENT (Smart routing)
    # =============================================================================
    
    async def create_config_template(
        self,
        template_name: str,
        device_type: str,
        vendor: str,
        template_content: str,
        is_openwisp_template: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create configuration template.
        - Routes to OpenWISP for OpenWrt devices
        - Uses DotMac SDK for other vendors
        """
        await self._ensure_initialized()
        
        if is_openwisp_template and vendor.lower() in ['openwrt', 'openwrt-device']:
            # Create in OpenWISP for OpenWrt
            openwisp_data = {
                'name': template_name,
                'backend': 'netjsonconfig.OpenWrt',
                'config': template_content if isinstance(template_content, dict) else {},
                'organization': self._get_openwisp_org_id(),
                **kwargs
            }
            
            openwisp_template = await self.openwisp.configs.create_template(openwisp_data)
            
            # Also store reference in DotMac
            dotmac_template = await self.config.create_config_template(
                template_name=template_name,
                device_type=device_type,
                vendor=vendor,
                template_content=str(template_content),
                openwisp_template_id=openwisp_template.get('id'),
                **kwargs
            )
            
            return {
                'template_id': dotmac_template['template_id'],
                'template_name': template_name,
                'device_type': device_type,
                'vendor': vendor,
                'openwisp_managed': True,
                'openwisp_template_id': openwisp_template.get('id'),
                'created_at': dotmac_template['created_at']
            }
        else:
            # Create in DotMac for other vendors
            template = await self.config.create_config_template(
                template_name=template_name,
                device_type=device_type,
                vendor=vendor,
                template_content=template_content,
                **kwargs
            )
            
            return {
                'template_id': template['template_id'],
                'template_name': template['template_name'],
                'device_type': template['device_type'],
                'vendor': template['vendor'],
                'openwisp_managed': False,
                'created_at': template['created_at']
            }
    
    async def deploy_config(
        self,
        device_id: str,
        template_id: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Deploy configuration to device.
        - Routes to OpenWISP for OpenWrt devices
        - Uses DotMac provisioning for others
        """
        await self._ensure_initialized()
        
        device = await self.get_device(device_id, include_openwisp=False)
        if not device:
            raise DeviceNotFoundError(f"Device not found: {device_id}")
        
        if device.get('openwisp_device_id'):
            # Deploy via OpenWISP for OpenWrt devices
            try:
                # Assign template to device in OpenWISP
                update_data = {
                    'config': {
                        'templates': [template_id]  # Assign template
                    }
                }
                
                result = await self.openwisp.devices.update_device(
                    device['openwisp_device_id'],
                    update_data
                )
                
                return {
                    'device_id': device_id,
                    'template_id': template_id,
                    'deployment_method': 'openwisp',
                    'status': 'deployed',
                    'openwisp_config_id': result.get('config', {}).get('id')
                }
                
            except Exception as e:
                raise ConfigDeploymentError(f"OpenWISP deployment failed: {e}")
        else:
            # Deploy via DotMac provisioning
            intent = await self.config.create_config_intent(
                device_id=device_id,
                template_id=template_id,
                parameters=parameters or {}
            )
            
            # Start provisioning workflow
            workflow = await self.provisioning.create_provisioning_workflow(
                workflow_name=f"Config deployment for {device_id}",
                device_id=device_id,
                activities=['render_config', 'deploy_config', 'validate_config']
            )
            
            return {
                'device_id': device_id,
                'template_id': template_id,
                'deployment_method': 'dotmac_provisioning',
                'intent_id': intent['intent_id'],
                'workflow_id': workflow['workflow_id'],
                'status': 'pending'
            }
    
    # =============================================================================
    # DEVICE-SPECIFIC OPERATIONS
    # =============================================================================
    
    async def get_device_config(self, device_id: str) -> Dict[str, Any]:
        """Get current device configuration."""
        device = await self.get_device(device_id, include_openwisp=False)
        if not device:
            raise DeviceNotFoundError(f"Device not found: {device_id}")
        
        if device.get('openwisp_device_id'):
            # Get config from OpenWISP
            config_data = await self.openwisp.devices.download_device_config(
                device['openwisp_device_id']
            )
            return {
                'device_id': device_id,
                'source': 'openwisp',
                'config_data': config_data
            }
        else:
            # Get config from DotMac inventory
            config = await self.inventory.get_device_config(device_id)
            return {
                'device_id': device_id,
                'source': 'dotmac',
                'config_data': config
            }
    
    async def get_device_status(self, device_id: str) -> Dict[str, Any]:
        """Get comprehensive device status."""
        device = await self.get_device(device_id, include_openwisp=True)
        if not device:
            raise DeviceNotFoundError(f"Device not found: {device_id}")
        
        status = {
            'device_id': device_id,
            'management_method': 'openwisp' if device.get('openwisp_device_id') else 'dotmac',
            'device_info': {
                'vendor': device['vendor'],
                'model': device['model'],
                'device_type': device['device_type']
            }
        }
        
        if device.get('openwisp_data'):
            openwisp_data = device['openwisp_data']
            status.update({
                'config_status': openwisp_data.get('config', {}).get('status'),
                'last_seen': openwisp_data.get('last_ip'),
                'is_online': bool(openwisp_data.get('last_ip')),
                'openwisp_status': openwisp_data.get('status')
            })
        
        return status
    
    # =============================================================================
    # HELPER METHODS
    # =============================================================================
    
    def _get_openwisp_org_id(self) -> str:
        """Get OpenWISP organization ID for tenant mapping."""
        # Map tenant_id to OpenWISP organization
        # In production, this should be configured in a mapping table
        return self.tenant_id  # Simplified mapping
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of unified device management."""
        await self._ensure_initialized()
        
        # Check DotMac components
        db_healthy = await db_manager.health_check()
        
        # Check OpenWISP
        openwisp_health = await self.openwisp.health_check()
        
        return {
            'dotmac_database': 'healthy' if db_healthy else 'unhealthy',
            'openwisp_controller': openwisp_health.get('controller', 'unknown'),
            'tenant_id': self.tenant_id,
            'status': 'healthy' if db_healthy else 'degraded'
        }
    
    async def cleanup(self) -> None:
        """Cleanup resources."""
        await self.openwisp.close()


# Custom exceptions
class DeviceNotFoundError(Exception):
    """Device not found in registry."""
    pass


class ConfigDeploymentError(Exception):
    """Configuration deployment failed."""
    pass