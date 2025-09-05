"""
Dashboard and Alert Management for DotMac Applications.
Automatically provisions dashboards and alerts for Grafana and Signoz.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)


class DashboardManager:
    """
    Manages dashboard and alert provisioning for DotMac applications.

    Features:
    - Automatic dashboard provisioning for Grafana and Signoz
    - Alert rule management
    - Tenant-specific dashboard generation
    - Template variable substitution
    - Dashboard versioning and updates
    """

    def __init__(self, dashboards_path: Optional[str] = None):
        self.dashboards_path = dashboards_path or Path(__file__).parent
        self.signoz_path = Path(self.dashboards_path) / "signoz"
        self.alerts_path = Path(self.dashboards_path) / "alerts"

    async def provision_dashboards_for_platform(
        self,
        platform_type: str,
        tenant_id: Optional[str] = None,
        custom_variables: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Provision dashboards for a specific platform type.

        Args:
            platform_type: 'management' or 'isp'
            tenant_id: Optional tenant ID for tenant-specific dashboards
            custom_variables: Custom variables for template substitution

        Returns:
            Dictionary with provisioning results
        """
        logger.info(f"Provisioning dashboards for platform: {platform_type}")

        results = {
            "platform_type": platform_type,
            "tenant_id": tenant_id,
            "signoz_dashboards": [],
            "alerts": [],
            "errors": [],
        }

        try:
            # Load dashboard templates
            dashboard_configs = await self._load_dashboard_configs(platform_type)

            # Apply template variables
            variables = self._prepare_template_variables(
                platform_type, tenant_id, custom_variables
            )

            # Process Signoz dashboards
            signoz_results = await self._process_signoz_dashboards(
                dashboard_configs.get("signoz", []), variables
            )
            results["signoz_dashboards"] = signoz_results

            # Process alert rules
            alert_results = await self._process_alert_rules(platform_type, variables)
            results["alerts"] = alert_results

            logger.info(f"✅ Dashboard provisioning complete for {platform_type}")
            logger.info(f"   Signoz dashboards: {len(signoz_results)}")
            logger.info(f"   Alert rules: {len(alert_results)}")

        except Exception as e:
            error_msg = f"Dashboard provisioning failed for {platform_type}: {e}"
            logger.error(error_msg)
            results["errors"].append(error_msg)

        return results

    async def _load_dashboard_configs(
        self, platform_type: str
    ) -> dict[str, list[dict]]:
        """Load dashboard configuration files for platform type."""
        configs = {"signoz": []}

        try:
            # Load Signoz dashboards
            if platform_type == "management":
                signoz_file = self.signoz_path / "management_platform_dashboard.json"
            else:  # isp
                signoz_file = self.signoz_path / "isp_framework_dashboard.json"

            if signoz_file.exists():
                with open(signoz_file) as f:
                    configs["signoz"].append(json.load(f))

        except Exception as e:
            logger.error(f"Failed to load dashboard configs: {e}")

        return configs

    def _prepare_template_variables(
        self,
        platform_type: str,
        tenant_id: Optional[str],
        custom_variables: Optional[dict[str, Any]],
    ) -> dict[str, Any]:
        """Prepare template variables for dashboard generation."""
        variables = {
            "platform_type": platform_type,
            "service_name": f"dotmac-{platform_type}"
            if platform_type == "management"
            else "isp-framework",
            "environment": os.getenv("ENVIRONMENT", "production"),
            "cluster_name": os.getenv("CLUSTER_NAME", "dotmac-cluster"),
            "namespace": os.getenv("KUBERNETES_NAMESPACE", "default"),
        }

        if tenant_id:
            variables.update(
                {
                    "tenant_id": tenant_id,
                    "tenant_namespace": f"tenant-{tenant_id.lower().replace('_', '-')}",
                    "service_name": f"isp-{tenant_id}"
                    if platform_type == "isp"
                    else variables["service_name"],
                }
            )

        if custom_variables:
            variables.update(custom_variables)

        return variables

    async def _process_signoz_dashboards(
        self, dashboard_configs: list[dict], variables: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Process and prepare Signoz dashboards."""
        results = []

        for config in dashboard_configs:
            try:
                # Apply template variable substitution
                processed_config = self._substitute_template_variables(
                    config, variables
                )

                # Add tenant-specific modifications if needed
                if variables.get("tenant_id"):
                    processed_config = self._customize_for_tenant(
                        processed_config, variables
                    )

                results.append(
                    {
                        "dashboard_config": processed_config,
                        "title": processed_config.get("title", "Unknown"),
                        "tags": processed_config.get("tags", []),
                        "provisioning_status": "ready",
                    }
                )

            except Exception as e:
                logger.error(f"Failed to process Signoz dashboard: {e}")
                results.append({"error": str(e), "provisioning_status": "failed"})

        return results

    async def _process_alert_rules(
        self, platform_type: str, variables: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Process and prepare alert rules."""
        results = []

        try:
            # Load Prometheus alert rules
            prometheus_alerts_file = self.alerts_path / "business_slo_alerts.yml"
            if prometheus_alerts_file.exists():
                with open(prometheus_alerts_file) as f:
                    prometheus_alerts = yaml.safe_load(f)

                # Apply template substitution
                processed_prometheus = self._substitute_template_variables(
                    prometheus_alerts, variables
                )

                results.append(
                    {
                        "type": "prometheus",
                        "rules": processed_prometheus,
                        "provisioning_status": "ready",
                    }
                )

            # Load Signoz alert rules
            signoz_alerts_file = self.alerts_path / "signoz_alerts.json"
            if signoz_alerts_file.exists():
                with open(signoz_alerts_file) as f:
                    signoz_alerts = json.load(f)

                # Apply template substitution and filter by platform
                filtered_alerts = [
                    alert
                    for alert in signoz_alerts
                    if self._alert_applies_to_platform(alert, platform_type)
                ]

                processed_signoz = [
                    self._substitute_template_variables(alert, variables)
                    for alert in filtered_alerts
                ]

                results.append(
                    {
                        "type": "signoz",
                        "alerts": processed_signoz,
                        "provisioning_status": "ready",
                    }
                )

        except Exception as e:
            logger.error(f"Failed to process alert rules: {e}")
            results.append({"error": str(e), "provisioning_status": "failed"})

        return results

    def _substitute_template_variables(
        self, config: Any, variables: dict[str, Any]
    ) -> Any:
        """Recursively substitute template variables in configuration."""
        if isinstance(config, dict):
            return {
                key: self._substitute_template_variables(value, variables)
                for key, value in config.items()
            }
        elif isinstance(config, list):
            return [
                self._substitute_template_variables(item, variables) for item in config
            ]
        elif isinstance(config, str):
            # Simple template variable substitution
            for key, value in variables.items():
                placeholder = f"{{{key}}}"
                if placeholder in config:
                    config = config.replace(placeholder, str(value))
            return config
        else:
            return config

    def _customize_for_tenant(
        self, config: dict[str, Any], variables: dict[str, Any]
    ) -> dict[str, Any]:
        """Customize dashboard configuration for specific tenant."""
        tenant_id = variables.get("tenant_id")
        if not tenant_id:
            return config

        # Add tenant-specific title suffix
        if "dashboard" in config and "title" in config["dashboard"]:
            config["dashboard"]["title"] += f" - Tenant {tenant_id}"
        elif "title" in config:
            config["title"] += f" - Tenant {tenant_id}"

        # Add tenant filter to template variables
        if "dashboard" in config and "templating" in config["dashboard"]:
            templating = config["dashboard"]["templating"]
            if "list" in templating:
                # Add tenant filter as default
                for variable in templating["list"]:
                    if (
                        variable.get("name") == "tenant"
                        and "defaultValue" not in variable
                    ):
                        variable["defaultValue"] = tenant_id

        return config

    def _alert_applies_to_platform(
        self, alert: dict[str, Any], platform_type: str
    ) -> bool:
        """Check if an alert rule applies to the given platform type."""
        labels = alert.get("labels", {})
        service = labels.get("service", "")

        if platform_type == "management":
            return "management" in service or "dotmac" in service
        elif platform_type == "isp":
            return "isp" in service

        return True  # Include generic alerts

    async def export_dashboard_configs(
        self, platform_type: str, export_path: str, tenant_id: Optional[str] = None
    ) -> dict[str, Any]:
        """Export dashboard configurations to files."""
        logger.info(f"Exporting dashboard configs for {platform_type} to {export_path}")

        try:
            # Provision dashboards
            results = await self.provision_dashboards_for_platform(
                platform_type, tenant_id
            )

            # Create export directory
            export_dir = Path(export_path)
            export_dir.mkdir(parents=True, exist_ok=True)

            # Export Signoz dashboards
            signoz_dir = export_dir / "signoz"
            signoz_dir.mkdir(exist_ok=True)

            for i, dashboard in enumerate(results["signoz_dashboards"]):
                if dashboard.get("provisioning_status") == "ready":
                    filename = f"{platform_type}_dashboard_{i}.json"
                    with open(signoz_dir / filename, "w") as f:
                        json.dump(dashboard["dashboard_config"], f, indent=2)

            # Export alert rules
            alerts_dir = export_dir / "alerts"
            alerts_dir.mkdir(exist_ok=True)

            for _, alert_set in enumerate(results["alerts"]):
                if alert_set.get("provisioning_status") == "ready":
                    if alert_set["type"] == "prometheus":
                        filename = f"{platform_type}_prometheus_alerts.yml"
                        with open(alerts_dir / filename, "w") as f:
                            yaml.dump(alert_set["rules"], f, default_flow_style=False)
                    elif alert_set["type"] == "signoz":
                        filename = f"{platform_type}_signoz_alerts.json"
                        with open(alerts_dir / filename, "w") as f:
                            json.dump(alert_set["alerts"], f, indent=2)

            return {
                "status": "success",
                "export_path": str(export_dir),
                "exported_files": len(list(export_dir.rglob("*"))),
            }

        except Exception as e:
            error_msg = f"Failed to export dashboard configs: {e}"
            logger.error(error_msg)
            return {"status": "error", "error": error_msg}


async def provision_platform_dashboards(
    platform_type: str,
    tenant_id: Optional[str] = None,
    custom_variables: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Convenience function to provision dashboards for a platform.

    Args:
        platform_type: 'management' or 'isp'
        tenant_id: Optional tenant ID
        custom_variables: Custom template variables

    Returns:
        Provisioning results dictionary
    """
    dashboard_manager = DashboardManager()
    return await dashboard_manager.provision_dashboards_for_platform(
        platform_type, tenant_id, custom_variables
    )


async def export_platform_dashboards(
    platform_type: str, export_path: str, tenant_id: Optional[str] = None
) -> dict[str, Any]:
    """
    Convenience function to export dashboard configurations.

    Args:
        platform_type: 'management' or 'isp'
        export_path: Directory to export to
        tenant_id: Optional tenant ID

    Returns:
        Export results dictionary
    """
    dashboard_manager = DashboardManager()
    return await dashboard_manager.export_dashboard_configs(
        platform_type, export_path, tenant_id
    )
