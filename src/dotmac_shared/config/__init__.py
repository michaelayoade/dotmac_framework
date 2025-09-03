"""
Shared Configuration Management Module
====================================
Provides centralized configuration management with OpenBao integration
for the entire DotMac Framework.
"""

from .secure_config import (
    SecureConfigManager,
    SecureConfigValue,
    get_config_manager,
    get_jwt_secret,
    get_jwt_secret_sync,
    get_database_url,
    get_redis_url,
    initialize_development_secrets
)

__all__ = [
    'SecureConfigManager',
    'SecureConfigValue', 
    'get_config_manager',
    'get_jwt_secret',
    'get_jwt_secret_sync',
    'get_database_url',
    'get_redis_url',
    'initialize_development_secrets'
]