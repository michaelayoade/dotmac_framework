"""
Infrastructure Adapter Factory
Factory for creating and managing infrastructure adapters
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from dotmac_shared.core.logging import get_logger
from dotmac_shared.api.exception_handlers import standard_exception_handler

from ..interfaces.deployment_provider import IDeploymentProvider
from ..interfaces.dns_provider import IDNSProvider
from ..interfaces.cache_provider import ICacheProvider
from ..interfaces.storage_provider import IStorageProvider

from ..deployment.coolify_adapter import CoolifyDeploymentAdapter
from ..dns.dns_validation_adapter import DNSValidationAdapter

logger = get_logger(__name__)


@dataclass
class AdapterConfig:
    """Configuration for an adapter instance"""
    adapter_type: str
    provider_name: str
    config: Dict[str, Any]
    enabled: bool = True


class AdapterRegistry:
    """Registry for available adapters"""
    
    DEPLOYMENT_ADAPTERS = {
        "coolify": CoolifyDeploymentAdapter,
    }
    
    DNS_ADAPTERS = {
        "dns_validation": DNSValidationAdapter,
    }
    
    CACHE_ADAPTERS = {
        # Future cache adapters will be registered here
    }
    
    STORAGE_ADAPTERS = {
        # Future storage adapters will be registered here
    }


class AdapterFactory:
    """
    Factory for creating and managing infrastructure adapters.
    Provides centralized adapter creation with configuration management.
    """
    
    def __init__(self):
        self._deployment_instances: Dict[str, IDeploymentProvider] = {}
        self._dns_instances: Dict[str, IDNSProvider] = {}
        self._cache_instances: Dict[str, ICacheProvider] = {}
        self._storage_instances: Dict[str, IStorageProvider] = {}
        self._configurations: Dict[str, AdapterConfig] = {}
        
    @standard_exception_handler
    async def initialize(self, adapter_configs: List[AdapterConfig]) -> bool:
        """Initialize factory with adapter configurations"""
        try:
            for config in adapter_configs:
                self._configurations[f"{config.adapter_type}_{config.provider_name}"] = config
            
            logger.info(f"✅ Adapter factory initialized with {len(adapter_configs)} configurations")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize adapter factory: {e}")
            return False
    
    @standard_exception_handler
    async def get_deployment_adapter(self, provider_name: str = None) -> Optional[IDeploymentProvider]:
        """Get or create deployment adapter"""
        provider_name = provider_name or "coolify"
        instance_key = f"deployment_{provider_name}"
        
        if instance_key in self._deployment_instances:
            return self._deployment_instances[instance_key]
        
        adapter_class = AdapterRegistry.DEPLOYMENT_ADAPTERS.get(provider_name)
        if not adapter_class:
            logger.error(f"Unknown deployment provider: {provider_name}")
            return None
        
        config_key = f"deployment_{provider_name}"
        adapter_config = self._configurations.get(config_key)
        
        config_dict = adapter_config.config if adapter_config else {}
        
        try:
            adapter = adapter_class(config_dict)
            
            if await adapter.initialize():
                self._deployment_instances[instance_key] = adapter
                logger.info(f"✅ Created deployment adapter: {provider_name}")
                return adapter
            else:
                logger.error(f"Failed to initialize deployment adapter: {provider_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating deployment adapter {provider_name}: {e}")
            return None
    
    @standard_exception_handler
    async def get_dns_adapter(self, provider_name: str = None) -> Optional[IDNSProvider]:
        """Get or create DNS adapter"""
        provider_name = provider_name or "dns_validation"
        instance_key = f"dns_{provider_name}"
        
        if instance_key in self._dns_instances:
            return self._dns_instances[instance_key]
        
        adapter_class = AdapterRegistry.DNS_ADAPTERS.get(provider_name)
        if not adapter_class:
            logger.error(f"Unknown DNS provider: {provider_name}")
            return None
        
        config_key = f"dns_{provider_name}"
        adapter_config = self._configurations.get(config_key)
        
        config_dict = adapter_config.config if adapter_config else {}
        
        try:
            adapter = adapter_class(config_dict)
            
            if await adapter.initialize():
                self._dns_instances[instance_key] = adapter
                logger.info(f"✅ Created DNS adapter: {provider_name}")
                return adapter
            else:
                logger.error(f"Failed to initialize DNS adapter: {provider_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating DNS adapter {provider_name}: {e}")
            return None
    
    @standard_exception_handler
    async def get_cache_adapter(self, provider_name: str) -> Optional[ICacheProvider]:
        """Get or create cache adapter"""
        instance_key = f"cache_{provider_name}"
        
        if instance_key in self._cache_instances:
            return self._cache_instances[instance_key]
        
        adapter_class = AdapterRegistry.CACHE_ADAPTERS.get(provider_name)
        if not adapter_class:
            logger.error(f"Unknown cache provider: {provider_name}")
            return None
        
        config_key = f"cache_{provider_name}"
        adapter_config = self._configurations.get(config_key)
        
        config_dict = adapter_config.config if adapter_config else {}
        
        try:
            adapter = adapter_class(config_dict)
            
            if await adapter.initialize():
                self._cache_instances[instance_key] = adapter
                logger.info(f"✅ Created cache adapter: {provider_name}")
                return adapter
            else:
                logger.error(f"Failed to initialize cache adapter: {provider_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating cache adapter {provider_name}: {e}")
            return None
    
    @standard_exception_handler
    async def get_storage_adapter(self, provider_name: str) -> Optional[IStorageProvider]:
        """Get or create storage adapter"""
        instance_key = f"storage_{provider_name}"
        
        if instance_key in self._storage_instances:
            return self._storage_instances[instance_key]
        
        adapter_class = AdapterRegistry.STORAGE_ADAPTERS.get(provider_name)
        if not adapter_class:
            logger.error(f"Unknown storage provider: {provider_name}")
            return None
        
        config_key = f"storage_{provider_name}"
        adapter_config = self._configurations.get(config_key)
        
        config_dict = adapter_config.config if adapter_config else {}
        
        try:
            adapter = adapter_class(config_dict)
            
            if await adapter.initialize():
                self._storage_instances[instance_key] = adapter
                logger.info(f"✅ Created storage adapter: {provider_name}")
                return adapter
            else:
                logger.error(f"Failed to initialize storage adapter: {provider_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating storage adapter {provider_name}: {e}")
            return None
    
    @standard_exception_handler
    async def health_check_all(self) -> Dict[str, Any]:
        """Check health of all initialized adapters"""
        health_results = {
            "deployment": {},
            "dns": {},
            "cache": {},
            "storage": {},
            "overall_healthy": True
        }
        
        # Check deployment adapters
        for key, adapter in self._deployment_instances.items():
            try:
                result = await adapter.health_check()
                health_results["deployment"][key] = result
                if not result.get("healthy", False):
                    health_results["overall_healthy"] = False
            except Exception as e:
                health_results["deployment"][key] = {"healthy": False, "error": str(e)}
                health_results["overall_healthy"] = False
        
        # Check DNS adapters
        for key, adapter in self._dns_instances.items():
            try:
                result = await adapter.health_check()
                health_results["dns"][key] = result
                if not result.get("healthy", False):
                    health_results["overall_healthy"] = False
            except Exception as e:
                health_results["dns"][key] = {"healthy": False, "error": str(e)}
                health_results["overall_healthy"] = False
        
        # Check cache adapters
        for key, adapter in self._cache_instances.items():
            try:
                result = await adapter.health_check()
                health_results["cache"][key] = result
                if not result.get("healthy", False):
                    health_results["overall_healthy"] = False
            except Exception as e:
                health_results["cache"][key] = {"healthy": False, "error": str(e)}
                health_results["overall_healthy"] = False
        
        # Check storage adapters
        for key, adapter in self._storage_instances.items():
            try:
                result = await adapter.health_check()
                health_results["storage"][key] = result
                if not result.get("healthy", False):
                    health_results["overall_healthy"] = False
            except Exception as e:
                health_results["storage"][key] = {"healthy": False, "error": str(e)}
                health_results["overall_healthy"] = False
        
        return health_results
    
    def get_available_providers(self) -> Dict[str, List[str]]:
        """Get list of available providers for each adapter type"""
        return {
            "deployment": list(AdapterRegistry.DEPLOYMENT_ADAPTERS.keys()),
            "dns": list(AdapterRegistry.DNS_ADAPTERS.keys()),
            "cache": list(AdapterRegistry.CACHE_ADAPTERS.keys()),
            "storage": list(AdapterRegistry.STORAGE_ADAPTERS.keys()),
        }
    
    @standard_exception_handler
    async def cleanup(self) -> bool:
        """Cleanup all adapter instances"""
        try:
            cleanup_tasks = []
            
            # Cleanup all adapter types
            for adapter in self._deployment_instances.values():
                cleanup_tasks.append(adapter.cleanup())
            
            for adapter in self._dns_instances.values():
                cleanup_tasks.append(adapter.cleanup())
            
            for adapter in self._cache_instances.values():
                cleanup_tasks.append(adapter.cleanup())
            
            for adapter in self._storage_instances.values():
                cleanup_tasks.append(adapter.cleanup())
            
            # Clear instance registries
            self._deployment_instances.clear()
            self._dns_instances.clear()
            self._cache_instances.clear()
            self._storage_instances.clear()
            
            logger.info("✅ Adapter factory cleanup complete")
            return True
            
        except Exception as e:
            logger.error(f"Error during adapter factory cleanup: {e}")
            return False


# Global factory instance
_adapter_factory: Optional[AdapterFactory] = None


@standard_exception_handler
async def get_adapter_factory() -> AdapterFactory:
    """Get the global adapter factory instance"""
    global _adapter_factory
    
    if _adapter_factory is None:
        _adapter_factory = AdapterFactory()
        
        # Initialize with default configurations
        default_configs = [
            AdapterConfig(
                adapter_type="deployment",
                provider_name="coolify",
                config={}
            ),
            AdapterConfig(
                adapter_type="dns",
                provider_name="dns_validation",
                config={}
            )
        ]
        
        await _adapter_factory.initialize(default_configs)
    
    return _adapter_factory