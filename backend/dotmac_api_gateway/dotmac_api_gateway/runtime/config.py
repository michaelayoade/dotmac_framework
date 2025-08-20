"""
Runtime configuration templates and examples.
"""

DEVELOPMENT_CONFIG = {
    "environment": "development",
    "debug": True,
    "tenant_id": "dev-tenant",
    "server": {
        "host": "127.0.0.1",  # Secure default: localhost only
        "port": 8000,
        "workers": 1,
        "reload": True,
        "access_log": True,
        "log_level": "debug"
    },
    "authentication": {
        "default_provider": "jwt",
        "jwt_secret": "dev-secret-key",
        "jwt_algorithm": "HS256",
        "jwt_expiration": 3600,
        "api_key_header": "X-API-Key",
        "enable_bearer_tokens": True
    },
    "rate_limit": {
        "default_policy": "development",
        "requests_per_minute": 10000,
        "burst_size": 1000,
        "algorithm": "sliding_window",
        "enable_per_ip": True
    },
    "cache": {
        "type": "memory",
        "ttl": 300,
        "max_size": 1000
    },
    "upstream": {
        "timeout": 30,
        "retries": 3,
        "circuit_breaker_threshold": 5
    },
    "monitoring": {
        "enable_metrics": True,
        "enable_tracing": True,
        "metrics_port": 9090
    },
    "security": {
        "allowed_hosts": ["*"],
        "cors_origins": ["*"],
        "max_request_size": 10485760
    }
}

PRODUCTION_CONFIG = {
    "environment": "production",
    "debug": False,
    "tenant_id": "prod-tenant",
    "server": {
        "host": "127.0.0.1",  # Secure default: localhost only
        "port": 8000,
        "workers": 4,
        "reload": False,
        "access_log": True,
        "log_level": "info"
    },
    "authentication": {
        "default_provider": "jwt",
        "jwt_secret": "CHANGE_ME_IN_PRODUCTION",
        "jwt_algorithm": "RS256",
        "jwt_expiration": 3600,
        "api_key_header": "X-API-Key",
        "enable_bearer_tokens": True
    },
    "rate_limit": {
        "default_policy": "production",
        "requests_per_minute": 1000,
        "burst_size": 100,
        "algorithm": "sliding_window",
        "enable_per_ip": True
    },
    "cache": {
        "type": "redis",
        "host": "localhost",
        "port": 6379,
        "ttl": 300,
        "max_size": 10000
    },
    "upstream": {
        "timeout": 10,
        "retries": 2,
        "circuit_breaker_threshold": 3
    },
    "monitoring": {
        "enable_metrics": True,
        "enable_tracing": True,
        "metrics_port": 9090,
        "jaeger_endpoint": "http://jaeger:14268/api/traces"
    },
    "security": {
        "allowed_hosts": ["api.example.com", "gateway.example.com"],
        "cors_origins": ["https://app.example.com"],
        "max_request_size": 1048576
    }
}

def get_config_template(environment: str = "development") -> dict:
    """Get configuration template for environment."""
    if environment == "production":
        return PRODUCTION_CONFIG.copy()
    return DEVELOPMENT_CONFIG.copy()
