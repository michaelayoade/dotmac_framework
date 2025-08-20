"""
Core configuration for DotMac Networking module
"""

import os
from typing import Dict, Any, Optional
from pydantic_settings import BaseSettings


class NetworkingConfig(BaseSettings):
    """Configuration settings for DotMac Networking"""
    
    # Database configuration
    database_url: str = "postgresql://dotmac:dotmac_secure_password@localhost:5432/dotmac_networking"
    redis_url: str = "redis://localhost:6379/5"
    
    # FreeRADIUS configuration
    freeradius_host: str = "localhost"
    freeradius_auth_port: int = 1812
    freeradius_acct_port: int = 1813
    freeradius_coa_port: int = 3799
    freeradius_secret: str = "dotmac-radius-secret"
    
    # VOLTHA configuration
    voltha_endpoint: str = "localhost:50057"
    voltha_enabled: bool = False
    kafka_endpoint: str = "localhost:9092"
    onos_endpoint: str = "localhost:8181"
    
    # SSH automation configuration
    ssh_max_concurrent: int = 10
    ssh_timeout: int = 30
    ssh_connection_pool_size: int = 20
    
    # Network topology configuration
    topology_auto_discovery: bool = True
    topology_cache_ttl: int = 300  # 5 minutes
    
    # Environment settings
    environment: str = "development"
    log_level: str = "INFO"
    tenant_id: Optional[str] = None
    
    class Config:
        env_prefix = "DOTMAC_NETWORKING_"
        case_sensitive = False


# Global configuration instance
config = NetworkingConfig()