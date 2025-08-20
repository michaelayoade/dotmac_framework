"""
Runtime configuration for dotmac_networking.
"""

import os

from pydantic import BaseModel, Field


class NetworkConfig(BaseModel):
    """Network configuration."""

    ipam_default_vrf: str = Field("default", description="Default VRF for IPAM")
    ipam_enable_ipv6: bool = Field(True, description="Enable IPv6 support")
    vlan_range_start: int = Field(100, description="VLAN range start")
    vlan_range_end: int = Field(4094, description="VLAN range end")


class RADIUSConfig(BaseModel):
    """RADIUS configuration."""

    server_host: str = Field("localhost", description="RADIUS server host")
    server_port: int = Field(1812, description="RADIUS server port")
    secret: str = Field("radiussecret", description="RADIUS shared secret")


class MonitoringConfig(BaseModel):
    """Monitoring configuration."""

    scrape_interval: int = Field(30, description="SNMP scrape interval in seconds")
    retention_days: int = Field(30, description="Metrics retention in days")


class RuntimeConfig(BaseModel):
    """Complete runtime configuration for networking services."""

    environment: str = Field("development", description="Runtime environment")
    debug: bool = Field(False, description="Debug mode")

    network: NetworkConfig
    radius: RADIUSConfig
    monitoring: MonitoringConfig


def load_config() -> RuntimeConfig:
    """Load configuration from environment variables."""

    network_config = NetworkConfig(
        ipam_default_vrf=os.getenv("DOTMAC_IPAM_DEFAULT_VRF", "default"),
        ipam_enable_ipv6=os.getenv("DOTMAC_IPAM_ENABLE_IPV6", "true").lower() == "true",
        vlan_range_start=int(os.getenv("DOTMAC_VLAN_RANGE_START", "100")),
        vlan_range_end=int(os.getenv("DOTMAC_VLAN_RANGE_END", "4094"))
    )

    radius_config = RADIUSConfig(
        server_host=os.getenv("DOTMAC_RADIUS_SERVER_HOST", "localhost"),
        server_port=int(os.getenv("DOTMAC_RADIUS_SERVER_PORT", "1812")),
        secret=os.getenv("DOTMAC_RADIUS_SECRET", "radiussecret")
    )

    monitoring_config = MonitoringConfig(
        scrape_interval=int(os.getenv("DOTMAC_MONITORING_SCRAPE_INTERVAL", "30")),
        retention_days=int(os.getenv("DOTMAC_MONITORING_RETENTION_DAYS", "30"))
    )

    return RuntimeConfig(
        environment=os.getenv("ENVIRONMENT", "development"),
        debug=os.getenv("DEBUG", "false").lower() == "true",
        network=network_config,
        radius=radius_config,
        monitoring=monitoring_config
    )
