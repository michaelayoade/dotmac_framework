"""
Deployment Provider Interface
Abstract interface for deployment providers (Coolify, K8s, Docker Swarm, etc.)
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class DeploymentResult:
    """Result of a deployment operation"""
    success: bool
    deployment_id: str
    application_id: Optional[str] = None
    endpoint_url: Optional[str] = None
    status: str = "unknown"
    message: str = ""
    error: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ApplicationConfig:
    """Configuration for application deployment"""
    name: str
    docker_compose: str
    environment: Dict[str, str] = None
    domains: List[str] = None
    description: str = ""
    
    def __post_init__(self):
        if self.environment is None:
            self.environment = {}
        if self.domains is None:
            self.domains = []


@dataclass
class ServiceConfig:
    """Configuration for service deployment (database, cache, etc.)"""
    name: str
    service_type: str  # postgres, redis, mysql, etc.
    version: str = "latest"
    configuration: Dict[str, Any] = None
    persistent_storage: bool = True
    
    def __post_init__(self):
        if self.configuration is None:
            self.configuration = {}


class IDeploymentProvider(ABC):
    """
    Abstract interface for deployment providers.
    Provides deployment capabilities for applications and services.
    """
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the deployment provider"""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check provider health and connectivity"""
        pass
    
    @abstractmethod
    async def deploy_application(self, config: ApplicationConfig) -> DeploymentResult:
        """Deploy an application"""
        pass
    
    @abstractmethod
    async def deploy_service(self, config: ServiceConfig) -> DeploymentResult:
        """Deploy a service (database, cache, etc.)"""
        pass
    
    @abstractmethod
    async def get_deployment_status(self, deployment_id: str) -> Dict[str, Any]:
        """Get deployment status"""
        pass
    
    @abstractmethod
    async def get_deployment_logs(self, deployment_id: str) -> List[str]:
        """Get deployment logs"""
        pass
    
    @abstractmethod
    async def scale_deployment(self, deployment_id: str, instances: int) -> bool:
        """Scale deployment to specified number of instances"""
        pass
    
    @abstractmethod
    async def stop_deployment(self, deployment_id: str) -> bool:
        """Stop a deployment"""
        pass
    
    @abstractmethod
    async def remove_deployment(self, deployment_id: str) -> bool:
        """Remove a deployment completely"""
        pass
    
    @abstractmethod
    async def set_domain(self, deployment_id: str, domain: str) -> bool:
        """Set custom domain for deployment"""
        pass
    
    @abstractmethod
    async def get_supported_services(self) -> List[str]:
        """Get list of supported service types"""
        pass
    
    @abstractmethod
    async def validate_config(self, config: ApplicationConfig) -> Dict[str, Any]:
        """Validate deployment configuration"""
        pass
    
    @abstractmethod
    async def cleanup(self) -> bool:
        """Cleanup provider resources"""
        pass