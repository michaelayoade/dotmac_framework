"""
Plugin interfaces defining the contracts for different plugin types.

Provides abstract base classes that plugins must implement to integrate
with the dotmac plugin system. All interfaces support both sync and async
implementations to accommodate different plugin architectures.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union, Awaitable

try:
    from fastapi import APIRouter
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    APIRouter = None

from .types import PluginKind, PluginStatus, ExportResult, DeploymentResult, ValidationResult


class IPlugin(ABC):
    """
    Base interface that all plugins must implement.
    
    Defines the core plugin contract including metadata, lifecycle methods,
    and status tracking. Plugins can implement methods as either sync or async.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique plugin name for identification."""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """Plugin version string (preferably semver)."""
        pass
    
    @property
    @abstractmethod
    def kind(self) -> PluginKind:
        """Plugin type/category."""
        pass
    
    @property
    @abstractmethod
    def metadata(self) -> "PluginMetadata":
        """Complete plugin metadata including capabilities and permissions."""
        pass
    
    @property
    def status(self) -> PluginStatus:
        """Current plugin status (managed by registry)."""
        return getattr(self, '_status', PluginStatus.UNKNOWN)
    
    @status.setter
    def status(self, value: PluginStatus) -> None:
        """Set plugin status (typically called by registry)."""
        self._status = value
    
    @abstractmethod
    def init(self, context: "PluginContext") -> Union[bool, Awaitable[bool]]:
        """
        Initialize the plugin with given context.
        
        Called once after registration to prepare the plugin for use.
        Should return True on success, False on failure.
        
        Args:
            context: Plugin context with services, config, and permissions
            
        Returns:
            Success status (sync or async)
        """
        pass
    
    @abstractmethod
    def start(self) -> Union[bool, Awaitable[bool]]:
        """
        Start the plugin and transition to running state.
        
        Called after initialization to activate the plugin.
        Should return True on success, False on failure.
        
        Returns:
            Success status (sync or async)
        """
        pass
    
    @abstractmethod
    def stop(self) -> Union[bool, Awaitable[bool]]:
        """
        Stop the plugin and clean up resources.
        
        Called during shutdown to deactivate the plugin.
        Should return True on success, False on failure.
        
        Returns:
            Success status (sync or async)
        """
        pass
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate plugin configuration.
        
        Optional method to validate configuration before initialization.
        Default implementation returns True (no validation).
        
        Args:
            config: Configuration dictionary
            
        Returns:
            True if configuration is valid
        """
        return True
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get current plugin health status.
        
        Optional method to provide health information for monitoring.
        Default implementation returns basic status.
        
        Returns:
            Health status dictionary
        """
        return {
            "name": self.name,
            "version": self.version,
            "status": self.status.name,
            "healthy": self.status == PluginStatus.RUNNING
        }


class IExportPlugin(IPlugin):
    """
    Interface for data export plugins.
    
    Plugins implementing this interface can export data in various formats
    (CSV, Excel, PDF, etc.) for different business processes like commission
    reports, customer data exports, etc.
    """
    
    @property
    def kind(self) -> PluginKind:
        """Export plugins must be of EXPORT kind."""
        return PluginKind.EXPORT
    
    @abstractmethod
    async def export(self, task: Dict[str, Any]) -> ExportResult:
        """
        Execute export task and generate output.
        
        Args:
            task: Export task definition containing:
                - export_type: Type of export (e.g., "commissions", "customers")
                - format: Output format (e.g., "csv", "xlsx", "pdf")
                - filters: Data filters and criteria
                - options: Export-specific options
                
        Returns:
            ExportResult containing:
                - success: Boolean success status
                - file_url: URL to download generated file (if successful)
                - file_name: Name of generated file
                - error: Error message (if failed)
                - metadata: Additional export metadata
        """
        pass
    
    def get_supported_formats(self) -> list[str]:
        """
        Get list of supported export formats.
        
        Returns:
            List of format strings (e.g., ["csv", "xlsx", "pdf"])
        """
        return ["csv"]  # Default implementation
    
    def get_export_types(self) -> list[str]:
        """
        Get list of supported export types.
        
        Returns:
            List of export type strings
        """
        return []  # Default implementation


class IDeploymentProvider(IPlugin):
    """
    Interface for deployment provider plugins.
    
    Plugins implementing this interface can deploy applications to various
    platforms (Coolify, Docker, cloud providers, etc.) and manage associated
    services like databases and Redis.
    """
    
    @property
    def kind(self) -> PluginKind:
        """Deployment providers must be of DEPLOYMENT kind."""
        return PluginKind.DEPLOYMENT
    
    @abstractmethod
    async def deploy_application(self, config: Dict[str, Any]) -> DeploymentResult:
        """
        Deploy application with given configuration.
        
        Args:
            config: Deployment configuration containing:
                - app_name: Application name
                - image: Container image or source
                - environment: Environment variables
                - resources: Resource requirements
                - networking: Network configuration
                
        Returns:
            DeploymentResult containing:
                - deployment_id: Unique deployment identifier
                - status: Deployment status
                - url: Application URL (if applicable)
                - services: Created service information
                - error: Error message (if failed)
        """
        pass
    
    @abstractmethod
    async def set_domain(self, deployment_id: str, domain: str) -> bool:
        """
        Configure custom domain for deployment.
        
        Args:
            deployment_id: Deployment identifier
            domain: Custom domain to configure
            
        Returns:
            Success status
        """
        pass
    
    async def create_database_service(self, db_config: Dict[str, Any]) -> Optional[DeploymentResult]:
        """
        Create database service for application.
        
        Optional method for providers that support database provisioning.
        
        Args:
            db_config: Database configuration
            
        Returns:
            Database service information or None if not supported
        """
        return None
    
    async def create_redis_service(self, redis_config: Dict[str, Any]) -> Optional[DeploymentResult]:
        """
        Create Redis service for application.
        
        Optional method for providers that support Redis provisioning.
        
        Args:
            redis_config: Redis configuration
            
        Returns:
            Redis service information or None if not supported
        """
        return None
    
    async def get_deployment_status(self, deployment_id: str) -> Dict[str, Any]:
        """
        Get current deployment status.
        
        Args:
            deployment_id: Deployment identifier
            
        Returns:
            Deployment status information
        """
        return {"deployment_id": deployment_id, "status": "unknown"}
    
    async def delete_deployment(self, deployment_id: str) -> bool:
        """
        Delete deployment and associated resources.
        
        Args:
            deployment_id: Deployment identifier
            
        Returns:
            Success status
        """
        return False  # Default: not implemented


class IDNSProvider(IPlugin):
    """
    Interface for DNS provider plugins.
    
    Plugins implementing this interface can validate domains, check DNS
    propagation, and validate SSL certificates for domain management.
    """
    
    @property
    def kind(self) -> PluginKind:
        """DNS providers must be of DNS kind."""
        return PluginKind.DNS
    
    @abstractmethod
    async def validate_subdomain(
        self, 
        subdomain: str, 
        base_domain: Optional[str] = None
    ) -> ValidationResult:
        """
        Validate subdomain availability and format.
        
        Args:
            subdomain: Subdomain to validate
            base_domain: Base domain (if None, use provider default)
            
        Returns:
            ValidationResult containing:
                - valid: Boolean validation status
                - domain: Full validated domain
                - available: Whether domain is available
                - error: Error message (if invalid)
                - suggestions: Alternative suggestions (if applicable)
        """
        pass
    
    @abstractmethod
    async def check_propagation(
        self, 
        domain: str, 
        expected_value: Optional[str] = None
    ) -> ValidationResult:
        """
        Check DNS propagation status for domain.
        
        Args:
            domain: Domain to check
            expected_value: Expected DNS value (if None, check general propagation)
            
        Returns:
            ValidationResult containing:
                - propagated: Boolean propagation status
                - current_value: Current DNS value
                - expected_value: Expected DNS value
                - nameservers: Nameserver propagation status
                - ttl: Current TTL value
        """
        pass
    
    @abstractmethod
    async def validate_ssl_certificate(self, domain: str) -> ValidationResult:
        """
        Validate SSL certificate for domain.
        
        Args:
            domain: Domain to validate certificate for
            
        Returns:
            ValidationResult containing:
                - valid: Boolean certificate validity
                - issuer: Certificate issuer
                - expires: Expiration date
                - chain_valid: Certificate chain validity
                - error: Error message (if invalid)
        """
        pass
    
    async def create_dns_record(
        self, 
        domain: str, 
        record_type: str, 
        value: str,
        ttl: int = 300
    ) -> bool:
        """
        Create DNS record.
        
        Optional method for providers that support DNS management.
        
        Args:
            domain: Domain name
            record_type: Record type (A, CNAME, TXT, etc.)
            value: Record value
            ttl: Time to live
            
        Returns:
            Success status
        """
        return False  # Default: not implemented
    
    async def delete_dns_record(self, domain: str, record_type: str) -> bool:
        """
        Delete DNS record.
        
        Optional method for providers that support DNS management.
        
        Args:
            domain: Domain name
            record_type: Record type to delete
            
        Returns:
            Success status
        """
        return False  # Default: not implemented


class IObserver(IPlugin):
    """
    Interface for event observer plugins.
    
    Plugins implementing this interface can observe and react to system
    events, metrics, and other observability data for monitoring,
    alerting, and analytics purposes.
    """
    
    @property
    def kind(self) -> PluginKind:
        """Observer plugins must be of OBSERVER kind."""
        return PluginKind.OBSERVER
    
    @abstractmethod
    async def on_event(self, event: Dict[str, Any]) -> None:
        """
        Handle system event.
        
        Args:
            event: Event data containing:
                - type: Event type
                - source: Event source
                - timestamp: Event timestamp
                - data: Event-specific data
                - metadata: Additional metadata
        """
        pass
    
    async def on_metric(self, metric: Dict[str, Any]) -> None:
        """
        Handle metric data.
        
        Optional method for metric-specific handling.
        
        Args:
            metric: Metric data
        """
        pass
    
    def get_event_types(self) -> list[str]:
        """
        Get list of event types this observer handles.
        
        Returns:
            List of event type strings
        """
        return []  # Default: handle all events
    
    def should_handle_event(self, event: Dict[str, Any]) -> bool:
        """
        Determine if this observer should handle the given event.
        
        Args:
            event: Event to evaluate
            
        Returns:
            True if event should be handled
        """
        event_types = self.get_event_types()
        if not event_types:
            return True  # Handle all events by default
        
        event_type = event.get("type", "")
        return event_type in event_types


class IRouterPlugin(IPlugin):
    """
    Interface for FastAPI router plugins.
    
    Plugins implementing this interface can contribute API routes to
    FastAPI applications for extending functionality with custom endpoints.
    """
    
    @property
    def kind(self) -> PluginKind:
        """Router plugins must be of ROUTER kind."""
        return PluginKind.ROUTER
    
    @abstractmethod
    def get_router(self) -> "APIRouter":
        """
        Get FastAPI router with plugin-specific routes.
        
        Returns:
            Configured APIRouter instance
            
        Raises:
            ImportError: If FastAPI is not available
        """
        if not FASTAPI_AVAILABLE:
            raise ImportError(
                "FastAPI not available. Install with: pip install 'dotmac-plugins[fastapi]'"
            )
        pass
    
    def get_prefix(self) -> str:
        """
        Get URL prefix for plugin routes.
        
        Returns:
            URL prefix string (e.g., "/api/v1/myplugin")
        """
        return f"/plugins/{self.name}"
    
    def get_tags(self) -> list[str]:
        """
        Get OpenAPI tags for plugin routes.
        
        Returns:
            List of tag strings for API documentation
        """
        return [self.name.title()]
    
    def include_in_schema(self) -> bool:
        """
        Whether to include plugin routes in OpenAPI schema.
        
        Returns:
            True to include in API documentation
        """
        return True