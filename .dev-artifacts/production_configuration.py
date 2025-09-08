#!/usr/bin/env python3
"""
Production Configuration Generator for Workflow Orchestration
Phase 4: Production Readiness

This module creates all production configuration files needed for deploying
workflow orchestration in a production environment.
"""

import os
from pathlib import Path
from typing import Dict, Any
import yaml
import json
from datetime import datetime


class ProductionConfigurationGenerator:
    """Generates production configuration files for workflow orchestration."""
    
    def __init__(self, base_path: str = "/home/dotmac_framework"):
        self.base_path = Path(base_path)
        self.config_dir = self.base_path / ".dev-artifacts" / "production-config"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
    def generate_all_configurations(self) -> Dict[str, str]:
        """Generate all production configuration files."""
        configs_generated = {}
        
        # Generate Docker Compose for production
        configs_generated["docker_compose"] = self._create_production_docker_compose()
        
        # Generate environment configuration
        configs_generated["environment"] = self._create_production_environment()
        
        # Generate Kubernetes manifests
        configs_generated["kubernetes"] = self._create_kubernetes_manifests()
        
        # Generate Nginx configuration
        configs_generated["nginx"] = self._create_nginx_configuration()
        
        # Generate systemd service files
        configs_generated["systemd"] = self._create_systemd_services()
        
        # Generate application configuration
        configs_generated["app_config"] = self._create_application_configuration()
        
        return configs_generated
    
    def _create_production_docker_compose(self) -> str:
        """Create production Docker Compose configuration."""
        config = {
            "version": "3.8",
            "services": {
                "dotmac-management": {
                    "build": {
                        "context": ".",
                        "dockerfile": "Dockerfile.management"
                    },
                    "environment": [
                        "DATABASE_URL=${DATABASE_URL}",
                        "REDIS_URL=${REDIS_URL}",
                        "BUSINESS_LOGIC_WORKFLOWS_ENABLED=true",
                        "WORKFLOW_DATABASE_POOL_SIZE=20",
                        "WORKFLOW_MAX_CONCURRENT_SAGAS=100",
                        "PROMETHEUS_METRICS_ENABLED=true",
                        "LOG_LEVEL=INFO"
                    ],
                    "ports": [
                        "8000:8000"
                    ],
                    "volumes": [
                        "./logs:/app/logs",
                        "./config/production.yaml:/app/config/production.yaml:ro"
                    ],
                    "depends_on": [
                        "postgres",
                        "redis",
                        "prometheus"
                    ],
                    "restart": "unless-stopped",
                    "healthcheck": {
                        "test": ["CMD", "curl", "-f", "http://localhost:8000/api/workflows/health"],
                        "interval": "30s",
                        "timeout": "10s",
                        "retries": 3,
                        "start_period": "60s"
                    }
                },
                "dotmac-isp": {
                    "build": {
                        "context": ".",
                        "dockerfile": "Dockerfile.isp"
                    },
                    "environment": [
                        "DATABASE_URL=${DATABASE_URL}",
                        "REDIS_URL=${REDIS_URL}",
                        "BUSINESS_LOGIC_WORKFLOWS_ENABLED=true",
                        "WORKFLOW_DATABASE_POOL_SIZE=15",
                        "LOG_LEVEL=INFO"
                    ],
                    "ports": [
                        "8001:8000"
                    ],
                    "depends_on": [
                        "postgres",
                        "redis"
                    ],
                    "restart": "unless-stopped",
                    "healthcheck": {
                        "test": ["CMD", "curl", "-f", "http://localhost:8000/health"],
                        "interval": "30s",
                        "timeout": "10s",
                        "retries": 3
                    }
                },
                "postgres": {
                    "image": "postgres:15-alpine",
                    "environment": [
                        "POSTGRES_DB=dotmac_production",
                        "POSTGRES_USER=${POSTGRES_USER}",
                        "POSTGRES_PASSWORD=${POSTGRES_PASSWORD}"
                    ],
                    "volumes": [
                        "postgres_data:/var/lib/postgresql/data",
                        "./sql/init-workflow-tables.sql:/docker-entrypoint-initdb.d/10-workflow-tables.sql:ro"
                    ],
                    "ports": [
                        "5432:5432"
                    ],
                    "restart": "unless-stopped",
                    "healthcheck": {
                        "test": ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d dotmac_production"],
                        "interval": "10s",
                        "timeout": "5s",
                        "retries": 5
                    }
                },
                "redis": {
                    "image": "redis:7-alpine",
                    "ports": [
                        "6379:6379"
                    ],
                    "volumes": [
                        "redis_data:/data"
                    ],
                    "restart": "unless-stopped",
                    "healthcheck": {
                        "test": ["CMD", "redis-cli", "ping"],
                        "interval": "10s",
                        "timeout": "3s",
                        "retries": 3
                    }
                },
                "prometheus": {
                    "image": "prom/prometheus:latest",
                    "ports": [
                        "9090:9090"
                    ],
                    "volumes": [
                        "./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro",
                        "./monitoring/alert-rules.yml:/etc/prometheus/alert-rules.yml:ro",
                        "prometheus_data:/prometheus"
                    ],
                    "command": [
                        "--config.file=/etc/prometheus/prometheus.yml",
                        "--storage.tsdb.path=/prometheus",
                        "--web.console.libraries=/etc/prometheus/console_libraries",
                        "--web.console.templates=/etc/prometheus/consoles",
                        "--storage.tsdb.retention.time=30d",
                        "--web.enable-lifecycle"
                    ],
                    "restart": "unless-stopped"
                },
                "grafana": {
                    "image": "grafana/grafana:latest",
                    "ports": [
                        "3000:3000"
                    ],
                    "volumes": [
                        "grafana_data:/var/lib/grafana",
                        "./monitoring/grafana-datasources.yml:/etc/grafana/provisioning/datasources/datasources.yml:ro",
                        "./monitoring/grafana-dashboards.yml:/etc/grafana/provisioning/dashboards/dashboards.yml:ro",
                        "./monitoring/dashboards:/var/lib/grafana/dashboards:ro"
                    ],
                    "environment": [
                        "GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}",
                        "GF_USERS_ALLOW_SIGN_UP=false"
                    ],
                    "restart": "unless-stopped"
                },
                "alertmanager": {
                    "image": "prom/alertmanager:latest",
                    "ports": [
                        "9093:9093"
                    ],
                    "volumes": [
                        "./monitoring/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro"
                    ],
                    "restart": "unless-stopped"
                }
            },
            "volumes": {
                "postgres_data": {},
                "redis_data": {},
                "prometheus_data": {},
                "grafana_data": {}
            },
            "networks": {
                "default": {
                    "driver": "bridge"
                }
            }
        }
        
        config_path = self.config_dir / "docker-compose.production.yml"
        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        
        return str(config_path)
    
    def _create_production_environment(self) -> str:
        """Create production environment configuration."""
        env_content = """# DotMac Framework Production Environment Configuration
# Phase 4: Production Readiness

# Database Configuration
DATABASE_URL=postgresql://dotmac_prod:${POSTGRES_PASSWORD}@postgres:5432/dotmac_production
POSTGRES_USER=dotmac_prod
POSTGRES_PASSWORD=change_this_secure_password

# Redis Configuration
REDIS_URL=redis://redis:6379/0

# Workflow Orchestration Configuration
BUSINESS_LOGIC_WORKFLOWS_ENABLED=true
WORKFLOW_DATABASE_POOL_SIZE=20
WORKFLOW_DATABASE_POOL_TIMEOUT=30
WORKFLOW_MAX_CONCURRENT_SAGAS=100
WORKFLOW_SAGA_TIMEOUT_MINUTES=60
WORKFLOW_IDEMPOTENCY_TTL_HOURS=24
WORKFLOW_RETRY_MAX_ATTEMPTS=3
WORKFLOW_RETRY_BACKOFF_SECONDS=5

# Monitoring and Observability
PROMETHEUS_METRICS_ENABLED=true
PROMETHEUS_PORT=9090
GRAFANA_ADMIN_PASSWORD=change_this_admin_password
LOG_LEVEL=INFO
STRUCTURED_LOGGING=true
CORRELATION_ID_ENABLED=true

# Security Configuration
SECRET_KEY=change_this_secret_key_to_something_very_secure
JWT_SECRET_KEY=change_this_jwt_secret_key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Application Configuration
ENVIRONMENT=production
DEBUG=false
API_V1_STR=/api/v1
BACKEND_CORS_ORIGINS=["https://yourdomain.com"]
ALLOWED_HOSTS=["yourdomain.com", "api.yourdomain.com"]

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=1000
RATE_LIMIT_BURST_SIZE=100

# Health Check Configuration
HEALTH_CHECK_TIMEOUT_SECONDS=10
HEALTH_CHECK_INTERVAL_SECONDS=30

# Backup Configuration
DATABASE_BACKUP_ENABLED=true
DATABASE_BACKUP_SCHEDULE=0 2 * * *
DATABASE_BACKUP_RETENTION_DAYS=30

# Email Configuration (for alerts)
SMTP_HOST=smtp.yourdomain.com
SMTP_PORT=587
SMTP_USERNAME=alerts@yourdomain.com
SMTP_PASSWORD=change_this_smtp_password
SMTP_FROM_EMAIL=alerts@yourdomain.com

# Sentry Configuration (optional)
SENTRY_DSN=
SENTRY_ENVIRONMENT=production

# Feature Flags
FEATURE_TENANT_PROVISIONING_SAGA=true
FEATURE_BILLING_IDEMPOTENCY=true
FEATURE_WORKFLOW_MONITORING=true
FEATURE_PERFORMANCE_METRICS=true
"""
        
        env_path = self.config_dir / ".env.production"
        with open(env_path, "w") as f:
            f.write(env_content)
        
        return str(env_path)
    
    def _create_kubernetes_manifests(self) -> str:
        """Create Kubernetes deployment manifests."""
        k8s_dir = self.config_dir / "kubernetes"
        k8s_dir.mkdir(exist_ok=True)
        
        # Namespace
        namespace = {
            "apiVersion": "v1",
            "kind": "Namespace",
            "metadata": {
                "name": "dotmac-production"
            }
        }
        
        # ConfigMap for application configuration
        configmap = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": "dotmac-config",
                "namespace": "dotmac-production"
            },
            "data": {
                "BUSINESS_LOGIC_WORKFLOWS_ENABLED": "true",
                "PROMETHEUS_METRICS_ENABLED": "true",
                "LOG_LEVEL": "INFO",
                "ENVIRONMENT": "production"
            }
        }
        
        # Secret for sensitive data
        secret = {
            "apiVersion": "v1",
            "kind": "Secret",
            "metadata": {
                "name": "dotmac-secrets",
                "namespace": "dotmac-production"
            },
            "type": "Opaque",
            "stringData": {
                "DATABASE_URL": "postgresql://dotmac_prod:password@postgres:5432/dotmac_production",
                "REDIS_URL": "redis://redis:6379/0",
                "SECRET_KEY": "change-this-secret-key",
                "JWT_SECRET_KEY": "change-this-jwt-secret-key"
            }
        }
        
        # Management Service Deployment
        management_deployment = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": "dotmac-management",
                "namespace": "dotmac-production"
            },
            "spec": {
                "replicas": 3,
                "selector": {
                    "matchLabels": {
                        "app": "dotmac-management"
                    }
                },
                "template": {
                    "metadata": {
                        "labels": {
                            "app": "dotmac-management"
                        }
                    },
                    "spec": {
                        "containers": [
                            {
                                "name": "dotmac-management",
                                "image": "dotmac/management:latest",
                                "ports": [
                                    {
                                        "containerPort": 8000,
                                        "name": "http"
                                    }
                                ],
                                "envFrom": [
                                    {
                                        "configMapRef": {
                                            "name": "dotmac-config"
                                        }
                                    },
                                    {
                                        "secretRef": {
                                            "name": "dotmac-secrets"
                                        }
                                    }
                                ],
                                "livenessProbe": {
                                    "httpGet": {
                                        "path": "/api/workflows/health",
                                        "port": 8000
                                    },
                                    "initialDelaySeconds": 60,
                                    "periodSeconds": 30,
                                    "timeoutSeconds": 10
                                },
                                "readinessProbe": {
                                    "httpGet": {
                                        "path": "/api/workflows/health",
                                        "port": 8000
                                    },
                                    "initialDelaySeconds": 30,
                                    "periodSeconds": 10,
                                    "timeoutSeconds": 5
                                },
                                "resources": {
                                    "requests": {
                                        "memory": "512Mi",
                                        "cpu": "500m"
                                    },
                                    "limits": {
                                        "memory": "1Gi",
                                        "cpu": "1000m"
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        }
        
        # Service for Management
        management_service = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": "dotmac-management-service",
                "namespace": "dotmac-production"
            },
            "spec": {
                "selector": {
                    "app": "dotmac-management"
                },
                "ports": [
                    {
                        "protocol": "TCP",
                        "port": 80,
                        "targetPort": 8000
                    }
                ],
                "type": "ClusterIP"
            }
        }
        
        # Write all manifests
        manifests = [
            ("namespace.yaml", namespace),
            ("configmap.yaml", configmap),
            ("secret.yaml", secret),
            ("management-deployment.yaml", management_deployment),
            ("management-service.yaml", management_service)
        ]
        
        for filename, manifest in manifests:
            with open(k8s_dir / filename, "w") as f:
                yaml.dump(manifest, f, default_flow_style=False)
        
        return str(k8s_dir)
    
    def _create_nginx_configuration(self) -> str:
        """Create Nginx configuration for load balancing and SSL termination."""
        nginx_config = """# Nginx Configuration for DotMac Framework Production
# Phase 4: Production Readiness

upstream dotmac_management {
    server 127.0.0.1:8000;
    server 127.0.0.1:8001 backup;
    keepalive 32;
}

upstream dotmac_isp {
    server 127.0.0.1:8002;
    server 127.0.0.1:8003 backup;
    keepalive 32;
}

# Rate limiting zones
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/m;
limit_req_zone $binary_remote_addr zone=auth_limit:10m rate=10r/m;

server {
    listen 80;
    server_name api.yourdomain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;
    
    # SSL Configuration
    ssl_certificate /etc/ssl/certs/yourdomain.com.crt;
    ssl_certificate_key /etc/ssl/private/yourdomain.com.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self'" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Gzip Configuration
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml;
    
    # Management Platform Routes
    location /api/management {
        # Rate limiting
        limit_req zone=api_limit burst=20 nodelay;
        
        # Proxy settings
        proxy_pass http://dotmac_management;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Workflow-specific headers
        proxy_set_header X-Correlation-ID $request_id;
        
        # Connection settings
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        proxy_buffering off;
        
        # Health check bypass
        location /api/management/health {
            access_log off;
            proxy_pass http://dotmac_management;
        }
    }
    
    # Workflow Orchestration Routes (internal only)
    location /api/workflows {
        # Restrict to internal network
        allow 10.0.0.0/8;
        allow 172.16.0.0/12;
        allow 192.168.0.0/16;
        deny all;
        
        proxy_pass http://dotmac_management;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Internal-Request "true";
    }
    
    # ISP Platform Routes
    location /api/isp {
        # Rate limiting
        limit_req zone=api_limit burst=50 nodelay;
        
        proxy_pass http://dotmac_isp;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Correlation-ID $request_id;
    }
    
    # Authentication Routes (stricter rate limiting)
    location /api/auth {
        limit_req zone=auth_limit burst=5 nodelay;
        
        proxy_pass http://dotmac_management;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Monitoring endpoints (Prometheus)
    location /metrics {
        # Restrict to monitoring network
        allow 10.0.0.0/8;
        deny all;
        
        proxy_pass http://dotmac_management;
        proxy_set_header Host $host;
    }
    
    # Static files and root
    location / {
        return 404;
    }
}

# Monitoring server
server {
    listen 8080;
    server_name monitoring.internal;
    
    # Internal monitoring access only
    allow 10.0.0.0/8;
    allow 172.16.0.0/12;
    allow 192.168.0.0/16;
    deny all;
    
    # Grafana
    location /grafana/ {
        proxy_pass http://127.0.0.1:3000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Prometheus
    location /prometheus/ {
        proxy_pass http://127.0.0.1:9090/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
"""
        
        nginx_path = self.config_dir / "nginx.conf"
        with open(nginx_path, "w") as f:
            f.write(nginx_config)
        
        return str(nginx_path)
    
    def _create_systemd_services(self) -> str:
        """Create systemd service files for production deployment."""
        systemd_dir = self.config_dir / "systemd"
        systemd_dir.mkdir(exist_ok=True)
        
        # Main service file
        service_content = """[Unit]
Description=DotMac Framework Management Platform
After=network.target postgresql.service redis.service
Wants=postgresql.service redis.service

[Service]
Type=exec
User=dotmac
Group=dotmac
WorkingDirectory=/opt/dotmac
Environment=PYTHONPATH=/opt/dotmac/src
EnvironmentFile=/opt/dotmac/.env.production
ExecStart=/opt/dotmac/.venv/bin/uvicorn src.dotmac_management.main:app --host 0.0.0.0 --port 8000 --workers 4
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=dotmac-management

# Security settings
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/opt/dotmac/logs /tmp
PrivateTmp=yes
ProtectKernelTunables=yes
ProtectControlGroups=yes
RestrictRealtime=yes

# Resource limits
LimitNOFILE=65536
MemoryMax=2G
CPUQuota=200%

[Install]
WantedBy=multi-user.target
"""
        
        with open(systemd_dir / "dotmac-management.service", "w") as f:
            f.write(service_content)
        
        # ISP service file
        isp_service_content = """[Unit]
Description=DotMac Framework ISP Platform
After=network.target postgresql.service redis.service
Wants=postgresql.service redis.service

[Service]
Type=exec
User=dotmac
Group=dotmac
WorkingDirectory=/opt/dotmac
Environment=PYTHONPATH=/opt/dotmac/src
EnvironmentFile=/opt/dotmac/.env.production
ExecStart=/opt/dotmac/.venv/bin/uvicorn src.dotmac_isp.main:app --host 0.0.0.0 --port 8002 --workers 2
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=dotmac-isp

# Security settings
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/opt/dotmac/logs /tmp
PrivateTmp=yes
ProtectKernelTunables=yes
ProtectControlGroups=yes
RestrictRealtime=yes

# Resource limits
LimitNOFILE=32768
MemoryMax=1G
CPUQuota=100%

[Install]
WantedBy=multi-user.target
"""
        
        with open(systemd_dir / "dotmac-isp.service", "w") as f:
            f.write(isp_service_content)
        
        # Workflow health monitor service
        monitor_service_content = """[Unit]
Description=DotMac Workflow Health Monitor
After=dotmac-management.service
Wants=dotmac-management.service

[Service]
Type=exec
User=dotmac
Group=dotmac
WorkingDirectory=/opt/dotmac
Environment=PYTHONPATH=/opt/dotmac/src
EnvironmentFile=/opt/dotmac/.env.production
ExecStart=/opt/dotmac/.venv/bin/python /opt/dotmac/.dev-artifacts/workflow_health_monitor.py
Restart=always
RestartSec=30
StandardOutput=journal
StandardError=journal
SyslogIdentifier=dotmac-workflow-monitor

[Install]
WantedBy=multi-user.target
"""
        
        with open(systemd_dir / "dotmac-workflow-monitor.service", "w") as f:
            f.write(monitor_service_content)
        
        return str(systemd_dir)
    
    def _create_application_configuration(self) -> str:
        """Create application-specific configuration files."""
        app_config_dir = self.config_dir / "app-config"
        app_config_dir.mkdir(exist_ok=True)
        
        # Production application configuration
        app_config = {
            "environment": "production",
            "debug": False,
            "testing": False,
            
            # Database configuration
            "database": {
                "pool_size": 20,
                "pool_timeout": 30,
                "pool_recycle": 3600,
                "pool_pre_ping": True,
                "echo_sql": False
            },
            
            # Workflow orchestration configuration
            "workflows": {
                "enabled": True,
                "max_concurrent_sagas": 100,
                "saga_timeout_minutes": 60,
                "idempotency_ttl_hours": 24,
                "retry_max_attempts": 3,
                "retry_backoff_seconds": 5,
                "metrics_enabled": True,
                "health_check_interval_seconds": 30
            },
            
            # Redis configuration
            "redis": {
                "connection_pool_size": 10,
                "socket_timeout": 5,
                "socket_connect_timeout": 5,
                "retry_on_timeout": True,
                "decode_responses": True
            },
            
            # Security configuration
            "security": {
                "cors": {
                    "allow_origins": ["https://yourdomain.com"],
                    "allow_methods": ["GET", "POST", "PUT", "DELETE"],
                    "allow_headers": ["*"],
                    "allow_credentials": True
                },
                "rate_limiting": {
                    "enabled": True,
                    "requests_per_minute": 1000,
                    "burst_size": 100
                }
            },
            
            # Logging configuration
            "logging": {
                "level": "INFO",
                "format": "json",
                "correlation_id_enabled": True,
                "handlers": [
                    {
                        "type": "file",
                        "filename": "/opt/dotmac/logs/application.log",
                        "max_size": "100MB",
                        "backup_count": 10
                    },
                    {
                        "type": "console",
                        "stream": "stdout"
                    }
                ]
            },
            
            # Monitoring configuration
            "monitoring": {
                "prometheus": {
                    "enabled": True,
                    "port": 9090,
                    "path": "/metrics"
                },
                "health_checks": {
                    "enabled": True,
                    "timeout_seconds": 10,
                    "interval_seconds": 30
                },
                "sentry": {
                    "enabled": False,
                    "environment": "production"
                }
            }
        }
        
        config_path = app_config_dir / "production.yaml"
        with open(config_path, "w") as f:
            yaml.dump(app_config, f, default_flow_style=False)
        
        return str(config_path)
    
    def create_deployment_script(self) -> str:
        """Create automated deployment script."""
        script_content = """#!/bin/bash
# DotMac Framework Production Deployment Script
# Phase 4: Production Readiness

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CONFIG_DIR="${SCRIPT_DIR}/production-config"

echo "🚀 Starting DotMac Framework Production Deployment"
echo "Project Root: ${PROJECT_ROOT}"
echo "Config Directory: ${CONFIG_DIR}"

# Check prerequisites
check_prerequisites() {
    echo "🔍 Checking prerequisites..."
    
    # Check if running as root for system services
    if [[ $EUID -ne 0 ]]; then
        echo "❌ This script must be run as root for system service installation"
        exit 1
    fi
    
    # Check required commands
    local required_commands=("docker" "docker-compose" "systemctl" "nginx")
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            echo "❌ Required command '$cmd' not found"
            exit 1
        fi
    done
    
    echo "✅ Prerequisites check passed"
}

# Create application user and directories
setup_system() {
    echo "🔧 Setting up system configuration..."
    
    # Create dotmac user if doesn't exist
    if ! id "dotmac" &>/dev/null; then
        useradd -r -m -s /bin/bash dotmac
        usermod -aG docker dotmac
    fi
    
    # Create application directories
    mkdir -p /opt/dotmac/{logs,config,data}
    chown -R dotmac:dotmac /opt/dotmac
    
    # Copy application code (assuming it's in /tmp/dotmac-deploy)
    if [[ -d "/tmp/dotmac-deploy" ]]; then
        cp -r /tmp/dotmac-deploy/* /opt/dotmac/
        chown -R dotmac:dotmac /opt/dotmac
    fi
    
    echo "✅ System setup completed"
}

# Install and configure services
install_services() {
    echo "🏗️ Installing systemd services..."
    
    # Copy service files
    cp "${CONFIG_DIR}/systemd/"*.service /etc/systemd/system/
    
    # Reload systemd and enable services
    systemctl daemon-reload
    systemctl enable dotmac-management.service
    systemctl enable dotmac-isp.service
    systemctl enable dotmac-workflow-monitor.service
    
    echo "✅ Services installed"
}

# Configure Nginx
configure_nginx() {
    echo "🌐 Configuring Nginx..."
    
    # Backup existing configuration
    if [[ -f "/etc/nginx/sites-available/default" ]]; then
        cp /etc/nginx/sites-available/default /etc/nginx/sites-available/default.backup
    fi
    
    # Install DotMac configuration
    cp "${CONFIG_DIR}/nginx.conf" /etc/nginx/sites-available/dotmac
    ln -sf /etc/nginx/sites-available/dotmac /etc/nginx/sites-enabled/
    
    # Test configuration
    nginx -t
    
    # Reload Nginx
    systemctl reload nginx
    
    echo "✅ Nginx configured"
}

# Deploy with Docker Compose
deploy_docker() {
    echo "🐳 Deploying with Docker Compose..."
    
    cd "${PROJECT_ROOT}"
    
    # Copy production compose file
    cp "${CONFIG_DIR}/docker-compose.production.yml" ./
    
    # Copy environment file
    cp "${CONFIG_DIR}/.env.production" ./
    
    echo "⚠️  IMPORTANT: Please update the .env.production file with your actual passwords!"
    echo "Required changes:"
    echo "  - POSTGRES_PASSWORD"
    echo "  - GRAFANA_ADMIN_PASSWORD"
    echo "  - SECRET_KEY"
    echo "  - JWT_SECRET_KEY"
    echo ""
    read -p "Have you updated the .env.production file? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Please update the .env.production file before continuing"
        exit 1
    fi
    
    # Build and start services
    docker-compose -f docker-compose.production.yml build
    docker-compose -f docker-compose.production.yml up -d
    
    echo "✅ Docker services deployed"
}

# Run database migrations
run_migrations() {
    echo "🗄️ Running database migrations..."
    
    # Wait for database to be ready
    echo "Waiting for database to be ready..."
    sleep 30
    
    # Run migrations
    cd "${PROJECT_ROOT}"
    docker-compose -f docker-compose.production.yml exec dotmac-management /opt/dotmac/.venv/bin/alembic upgrade head
    
    echo "✅ Database migrations completed"
}

# Verify deployment
verify_deployment() {
    echo "✅ Verifying deployment..."
    
    # Check systemd services
    echo "Checking systemd services..."
    systemctl is-active --quiet dotmac-management && echo "✅ dotmac-management service is running" || echo "❌ dotmac-management service failed"
    systemctl is-active --quiet dotmac-isp && echo "✅ dotmac-isp service is running" || echo "❌ dotmac-isp service failed"
    
    # Check Docker services
    echo "Checking Docker services..."
    cd "${PROJECT_ROOT}"
    docker-compose -f docker-compose.production.yml ps
    
    # Check health endpoints
    echo "Checking health endpoints..."
    sleep 10
    curl -f http://localhost:8000/api/workflows/health && echo "✅ Management health check passed" || echo "❌ Management health check failed"
    curl -f http://localhost:8001/health && echo "✅ ISP health check passed" || echo "❌ ISP health check failed"
    
    echo "✅ Deployment verification completed"
}

# Main deployment flow
main() {
    check_prerequisites
    setup_system
    install_services
    configure_nginx
    deploy_docker
    run_migrations
    verify_deployment
    
    echo ""
    echo "🎉 DotMac Framework Production Deployment Complete!"
    echo ""
    echo "Access points:"
    echo "  • Management API: https://api.yourdomain.com/api/management"
    echo "  • ISP API: https://api.yourdomain.com/api/isp"
    echo "  • Grafana: http://monitoring.internal:8080/grafana"
    echo "  • Prometheus: http://monitoring.internal:8080/prometheus"
    echo ""
    echo "Next steps:"
    echo "  1. Configure SSL certificates"
    echo "  2. Update DNS records"
    echo "  3. Configure monitoring alerts"
    echo "  4. Set up backup schedules"
    echo ""
}

# Run main function
main "$@"
"""
        
        script_path = self.config_dir / "deploy.sh"
        with open(script_path, "w") as f:
            f.write(script_content)
        
        # Make executable
        os.chmod(script_path, 0o755)
        
        return str(script_path)


def main():
    """Generate all production configuration files."""
    print("🔧 Generating Production Configuration for Workflow Orchestration")
    print("Phase 4: Production Readiness")
    print()
    
    generator = ProductionConfigurationGenerator()
    
    try:
        # Generate all configurations
        configs = generator.generate_all_configurations()
        
        # Create deployment script
        deploy_script = generator.create_deployment_script()
        
        print("✅ Production Configuration Generated Successfully!")
        print()
        print("Generated files:")
        for config_type, path in configs.items():
            print(f"  • {config_type}: {path}")
        print(f"  • deployment_script: {deploy_script}")
        print()
        
        print("📋 Next Steps:")
        print("1. Review and update configuration files with your environment-specific values")
        print("2. Update passwords and secrets in .env.production")
        print("3. Configure SSL certificates for Nginx")
        print("4. Run the deployment script: sudo ./deploy.sh")
        print("5. Set up DNS records for your domain")
        print("6. Configure monitoring alert recipients")
        print()
        
        print("🔒 Security Checklist:")
        print("• Change all default passwords in .env.production")
        print("• Generate secure secret keys")
        print("• Configure SSL certificates")
        print("• Review Nginx security headers")
        print("• Set up firewall rules")
        print("• Configure backup encryption")
        
    except Exception as e:
        print(f"❌ Error generating production configuration: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())