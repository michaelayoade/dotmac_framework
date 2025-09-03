"""
Dashboard provisioning and management for observability platforms.
"""

import json
import logging
import os
import warnings
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from typing_extensions import Literal

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

logger = logging.getLogger(__name__)

PlatformType = Literal["signoz", "grafana"]


@dataclass
class DashboardConfig:
    """Configuration for dashboard provisioning."""
    platform_type: PlatformType
    base_url: str
    api_key: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    verify_ssl: bool = True
    timeout: int = 30
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for the platform."""
        if self.platform_type == "signoz":
            if self.api_key:
                return {"Authorization": f"Bearer {self.api_key}"}
            elif self.username and self.password:
                import base64
                credentials = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
                return {"Authorization": f"Basic {credentials}"}
        elif self.platform_type == "grafana":
            if self.api_key:
                return {"Authorization": f"Bearer {self.api_key}"}
            elif self.username and self.password:
                import base64
                credentials = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
                return {"Authorization": f"Basic {credentials}"}
        
        return {}


@dataclass
class DashboardTemplate:
    """Dashboard template definition."""
    name: str
    title: str
    description: str
    tags: List[str]
    template_content: Dict[str, Any]
    variables: Optional[Dict[str, str]] = None
    
    def render(self, custom_variables: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Render the dashboard template with variables."""
        content = self.template_content.copy()
        
        # Merge variables
        variables = {}
        if self.variables:
            variables.update(self.variables)
        if custom_variables:
            variables.update(custom_variables)
        
        # Simple variable substitution
        content_str = json.dumps(content)
        for key, value in variables.items():
            content_str = content_str.replace(f"${{{key}}}", str(value))
        
        return json.loads(content_str)


@dataclass
class DashboardProvisioningResult:
    """Result of dashboard provisioning operation."""
    success: bool
    platform_type: PlatformType
    dashboards_created: List[str] = field(default_factory=list)
    dashboards_updated: List[str] = field(default_factory=list)
    dashboards_failed: List[str] = field(default_factory=list)
    datasources_created: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    @property
    def total_dashboards(self) -> int:
        """Total number of dashboards processed."""
        return len(self.dashboards_created) + len(self.dashboards_updated) + len(self.dashboards_failed)
    
    def add_error(self, error: str) -> None:
        """Add an error message."""
        self.errors.append(error)
        if self.success and self.dashboards_failed:
            self.success = False
    
    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        self.warnings.append(warning)


class DashboardManager:
    """Manager for dashboard provisioning across different platforms."""
    
    def __init__(self, config: DashboardConfig):
        self.config = config
        self._client: Optional["httpx.Client"] = None
        
        if not HTTPX_AVAILABLE:
            warnings.warn(
                "Dashboard provisioning requires httpx. Install with: pip install 'dotmac-observability[dashboards]'",
                UserWarning,
                stacklevel=2
            )
    
    def __enter__(self) -> "DashboardManager":
        """Context manager entry."""
        if HTTPX_AVAILABLE:
            self._client = httpx.Client(
                base_url=self.config.base_url,
                headers=self.config.get_auth_headers(),
                verify=self.config.verify_ssl,
                timeout=self.config.timeout,
            )
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        if self._client:
            self._client.close()
    
    def provision_dashboards(
        self,
        templates: List[DashboardTemplate],
        tenant_id: Optional[str] = None,
        custom_variables: Optional[Dict[str, str]] = None,
        auto_create_datasources: bool = True,
    ) -> DashboardProvisioningResult:
        """
        Provision dashboards from templates.
        
        Args:
            templates: List of dashboard templates
            tenant_id: Optional tenant ID for scoping
            custom_variables: Custom template variables
            auto_create_datasources: Whether to auto-create datasources
            
        Returns:
            Provisioning result
        """
        result = DashboardProvisioningResult(
            success=True,
            platform_type=self.config.platform_type,
        )
        
        if not HTTPX_AVAILABLE:
            result.success = False
            result.add_error("httpx not available for dashboard provisioning")
            return result
        
        if not self._client:
            result.success = False
            result.add_error("HTTP client not initialized")
            return result
        
        # Create datasources if needed
        if auto_create_datasources:
            self._create_default_datasources(result)
        
        # Provision each dashboard
        for template in templates:
            try:
                self._provision_single_dashboard(template, result, tenant_id, custom_variables)
            except Exception as e:
                result.add_error(f"Failed to provision dashboard {template.name}: {e}")
                result.dashboards_failed.append(template.name)
        
        return result
    
    def _provision_single_dashboard(
        self,
        template: DashboardTemplate,
        result: DashboardProvisioningResult,
        tenant_id: Optional[str],
        custom_variables: Optional[Dict[str, str]],
    ) -> None:
        """Provision a single dashboard."""
        if not self._client:
            raise RuntimeError("HTTP client not available")
        
        # Prepare variables
        variables = {}
        if tenant_id:
            variables["tenant_id"] = tenant_id
        if custom_variables:
            variables.update(custom_variables)
        
        # Render template
        dashboard_config = template.render(variables)
        
        if self.config.platform_type == "signoz":
            self._provision_signoz_dashboard(template, dashboard_config, result)
        elif self.config.platform_type == "grafana":
            self._provision_grafana_dashboard(template, dashboard_config, result)
        else:
            raise ValueError(f"Unsupported platform type: {self.config.platform_type}")
    
    def _provision_signoz_dashboard(
        self,
        template: DashboardTemplate,
        dashboard_config: Dict[str, Any],
        result: DashboardProvisioningResult,
    ) -> None:
        """Provision dashboard in SigNoz."""
        if not self._client:
            raise RuntimeError("HTTP client not available")
        
        # SigNoz dashboard API format
        payload = {
            "title": template.title,
            "description": template.description,
            "tags": template.tags,
            "dashboard": dashboard_config,
        }
        
        try:
            # Check if dashboard exists
            response = self._client.get(f"/api/v1/dashboards?title={template.title}")
            
            if response.status_code == 200:
                dashboards = response.json().get("data", [])
                existing_dashboard = next((d for d in dashboards if d.get("title") == template.title), None)
                
                if existing_dashboard:
                    # Update existing dashboard
                    dashboard_id = existing_dashboard["id"]
                    response = self._client.put(f"/api/v1/dashboards/{dashboard_id}", json=payload)
                    
                    if response.status_code == 200:
                        result.dashboards_updated.append(template.name)
                        logger.info(f"Updated SigNoz dashboard: {template.title}")
                    else:
                        raise Exception(f"Failed to update dashboard: {response.text}")
                else:
                    # Create new dashboard
                    response = self._client.post("/api/v1/dashboards", json=payload)
                    
                    if response.status_code == 201:
                        result.dashboards_created.append(template.name)
                        logger.info(f"Created SigNoz dashboard: {template.title}")
                    else:
                        raise Exception(f"Failed to create dashboard: {response.text}")
            else:
                # Assume dashboard doesn't exist, create new
                response = self._client.post("/api/v1/dashboards", json=payload)
                
                if response.status_code == 201:
                    result.dashboards_created.append(template.name)
                    logger.info(f"Created SigNoz dashboard: {template.title}")
                else:
                    raise Exception(f"Failed to create dashboard: {response.text}")
                    
        except Exception as e:
            result.add_error(f"SigNoz dashboard provisioning failed for {template.name}: {e}")
            result.dashboards_failed.append(template.name)
    
    def _provision_grafana_dashboard(
        self,
        template: DashboardTemplate,
        dashboard_config: Dict[str, Any],
        result: DashboardProvisioningResult,
    ) -> None:
        """Provision dashboard in Grafana."""
        if not self._client:
            raise RuntimeError("HTTP client not available")
        
        # Grafana dashboard API format
        payload = {
            "dashboard": {
                "title": template.title,
                "description": template.description,
                "tags": template.tags,
                **dashboard_config,
            },
            "overwrite": True,
            "message": f"Provisioned by dotmac-observability",
        }
        
        try:
            response = self._client.post("/api/dashboards/db", json=payload)
            
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get("status") == "success":
                    if response_data.get("version") == 1:
                        result.dashboards_created.append(template.name)
                        logger.info(f"Created Grafana dashboard: {template.title}")
                    else:
                        result.dashboards_updated.append(template.name)
                        logger.info(f"Updated Grafana dashboard: {template.title}")
                else:
                    raise Exception(f"Grafana API returned error: {response_data}")
            else:
                raise Exception(f"Failed to provision dashboard: {response.text}")
                
        except Exception as e:
            result.add_error(f"Grafana dashboard provisioning failed for {template.name}: {e}")
            result.dashboards_failed.append(template.name)
    
    def _create_default_datasources(self, result: DashboardProvisioningResult) -> None:
        """Create default datasources for the platform."""
        if not self._client:
            return
        
        try:
            if self.config.platform_type == "signoz":
                self._create_signoz_datasources(result)
            elif self.config.platform_type == "grafana":
                self._create_grafana_datasources(result)
        except Exception as e:
            result.add_warning(f"Failed to create datasources: {e}")
    
    def _create_signoz_datasources(self, result: DashboardProvisioningResult) -> None:
        """Create default datasources for SigNoz."""
        # SigNoz typically has built-in datasources, so this might be a no-op
        pass
    
    def _create_grafana_datasources(self, result: DashboardProvisioningResult) -> None:
        """Create default datasources for Grafana."""
        if not self._client:
            return
        
        # Create Prometheus datasource
        prometheus_ds = {
            "name": "DotMac-Prometheus",
            "type": "prometheus",
            "url": os.getenv("PROMETHEUS_URL", "http://localhost:9090"),
            "access": "proxy",
            "basicAuth": False,
            "isDefault": True,
        }
        
        try:
            response = self._client.post("/api/datasources", json=prometheus_ds)
            if response.status_code == 200:
                result.datasources_created.append("DotMac-Prometheus")
                logger.info("Created Grafana Prometheus datasource")
        except Exception as e:
            result.add_warning(f"Failed to create Prometheus datasource: {e}")


def get_default_dashboard_templates() -> List[DashboardTemplate]:
    """Get default dashboard templates for DotMac services."""
    return [
        DashboardTemplate(
            name="dotmac_service_overview",
            title="DotMac Service Overview",
            description="Overview dashboard for DotMac services",
            tags=["dotmac", "overview"],
            template_content={
                "panels": [
                    {
                        "title": "HTTP Requests",
                        "type": "graph",
                        "targets": [
                            {
                                "expr": f"rate(http_requests_total{{service=\"{'{service}'}\"}}[5m])",
                                "legendFormat": "{{method}} {{endpoint}}",
                            }
                        ],
                    },
                    {
                        "title": "HTTP Request Duration",
                        "type": "graph",
                        "targets": [
                            {
                                "expr": f"histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{{service=\"{'{service}'}\"}}[5m]))",
                                "legendFormat": "95th percentile",
                            }
                        ],
                    },
                    {
                        "title": "Business Metrics - Success Rate",
                        "type": "graph",
                        "targets": [
                            {
                                "expr": f"rate(login_success_rate_success{{tenant_id=\"{'{tenant_id}'}\"}}[5m]) / rate(login_success_rate_total{{tenant_id=\"{'{tenant_id}'}\"}}[5m])",
                                "legendFormat": "Login Success Rate",
                            }
                        ],
                    },
                ],
            },
            variables={"service": "${service}", "tenant_id": "${tenant_id}"},
        ),
        DashboardTemplate(
            name="dotmac_slo_overview",
            title="DotMac SLO Overview",
            description="SLO monitoring dashboard",
            tags=["dotmac", "slo"],
            template_content={
                "panels": [
                    {
                        "title": "SLO Status",
                        "type": "stat",
                        "targets": [
                            {
                                "expr": f"avg(rate(api_request_success_rate_success{{tenant_id=\"{'{tenant_id}'}\"}}[5m]) / rate(api_request_success_rate_total{{tenant_id=\"{'{tenant_id}'}\"}}[5m]))",
                                "legendFormat": "API Success Rate",
                            }
                        ],
                    },
                ],
            },
            variables={"tenant_id": "${tenant_id}"},
        ),
    ]


def provision_platform_dashboards(
    platform_type: PlatformType,
    tenant_id: Optional[str] = None,
    custom_variables: Optional[Dict[str, str]] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> DashboardProvisioningResult:
    """
    Provision platform dashboards for DotMac observability.
    
    Args:
        platform_type: Target platform ("signoz" or "grafana")
        tenant_id: Optional tenant ID for scoping
        custom_variables: Custom template variables
        base_url: Platform base URL (from env if not provided)
        api_key: API key (from env if not provided)
        
    Returns:
        Provisioning result
    """
    # Get configuration from environment if not provided
    if base_url is None:
        if platform_type == "signoz":
            base_url = os.getenv("SIGNOZ_URL", "http://localhost:3301")
        else:  # grafana
            base_url = os.getenv("GRAFANA_URL", "http://localhost:3000")
    
    if api_key is None:
        if platform_type == "signoz":
            api_key = os.getenv("SIGNOZ_API_KEY")
        else:  # grafana
            api_key = os.getenv("GRAFANA_API_KEY")
    
    # Create dashboard config
    config = DashboardConfig(
        platform_type=platform_type,
        base_url=base_url,
        api_key=api_key,
    )
    
    # Get default templates
    templates = get_default_dashboard_templates()
    
    # Provision dashboards
    with DashboardManager(config) as manager:
        result = manager.provision_dashboards(
            templates=templates,
            tenant_id=tenant_id,
            custom_variables=custom_variables,
        )
    
    return result