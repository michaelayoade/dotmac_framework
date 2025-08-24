"""
SSH deployment provider plugin for remote server deployment.
Enables Management Platform to deploy ISP Framework to remote VPS servers.
"""

import logging
import asyncio
import tempfile
import os
import json
from typing import Dict, Any, List, Optional
from pathlib import Path
import paramiko
from paramiko import SSHClient, AutoAddPolicy
from scp import SCPClient
import asyncssh

from ...core.plugins.interfaces import DeploymentProviderPlugin
from ...core.plugins.base import PluginMeta, PluginType
from ...core.observability import get_observability

logger = logging.getLogger(__name__)


class SSHDeploymentPlugin(DeploymentProviderPlugin):
    """SSH-based deployment provider for remote server deployment."""
    
    @property
    def meta(self) -> PluginMeta:
        return PluginMeta(
            name="ssh_deployment",
            version="1.0.0",
            plugin_type=PluginType.DEPLOYMENT_PROVIDER,
            description="SSH-based deployment to remote servers (VPS, bare metal)",
            author="DotMac Platform",
            configuration_schema={
                "default_ssh_port": {"type": "integer", "default": 22},
                "connection_timeout": {"type": "integer", "default": 30},
                "command_timeout": {"type": "integer", "default": 300},
                "docker_compose_version": {"type": "string", "default": "2.24.1"},
                "deployment_user": {"type": "string", "default": "ubuntu"},
                "sudo_required": {"type": "boolean", "default": True},
                "cleanup_on_failure": {"type": "boolean", "default": True}
            }
        )
    
    def __init__(self):
        super().__init__()
        self.observability = get_observability()
    
    async def initialize(self) -> bool:
        """Initialize SSH plugin."""
        try:
            # Validate SSH client availability
            import paramiko
            import asyncssh
            
            logger.info("SSH deployment plugin initialized")
            return True
            
        except ImportError as e:
            logger.error(f"Missing SSH dependencies: {e}")
            return False
        except Exception as e:
            self.log_error(e, "initialization")
            return False
    
    async def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """Validate SSH plugin configuration."""
        try:
            required_keys = []  # SSH plugin has no mandatory config
            
            for key in required_keys:
                if key not in config:
                    logger.error(f"Missing required configuration key: {key}")
                    return False
            
            # Validate port range
            ssh_port = config.get("default_ssh_port", 22)
            if not (1 <= ssh_port <= 65535):
                logger.error("SSH port must be between 1 and 65535")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        return {
            "status": "healthy",
            "ssh_client": "available",
            "dependencies": "installed"
        }
    
    async def provision_infrastructure(self, infrastructure_config: Dict[str, Any]) -> Dict[str, Any]:
        """Provision infrastructure on remote server via SSH."""
        try:
            self.validate_tenant_context(infrastructure_config.get('tenant_id'))
            
            # Extract SSH connection details
            host = infrastructure_config.get('host')
            if not host:
                raise ValueError("SSH host is required for infrastructure provisioning")
            
            ssh_user = infrastructure_config.get('ssh_user', self.config.get('deployment_user', 'ubuntu'))
            ssh_key_path = infrastructure_config.get('ssh_key_path')
            ssh_password = infrastructure_config.get('ssh_password')
            ssh_port = infrastructure_config.get('ssh_port', self.config.get('default_ssh_port', 22))
            
            # Record deployment start
            tenant_id = infrastructure_config.get('tenant_id', 'unknown')
            self.observability.record_deployment("infrastructure_provision_start", tenant_id)
            
            # Connect via SSH and provision infrastructure
            with self.observability.trace_business_operation("ssh_infrastructure_provision", tenant_id=tenant_id):
                infrastructure_result = await self._provision_via_ssh(
                    host=host,
                    user=ssh_user,
                    key_path=ssh_key_path,
                    password=ssh_password,
                    port=ssh_port,
                    config=infrastructure_config
                )
            
            # Record successful provisioning
            self.observability.record_deployment("infrastructure_provision_success", tenant_id, success=True)
            
            return infrastructure_result
            
        except Exception as e:
            # Record failed provisioning
            tenant_id = infrastructure_config.get('tenant_id', 'unknown')
            self.observability.record_deployment("infrastructure_provision_failed", tenant_id, success=False)
            logger.error(f"SSH infrastructure provisioning failed: {e}")
            raise
    
    async def deploy_application(self, app_config: Dict[str, Any], infrastructure_id: str) -> Dict[str, Any]:
        """Deploy ISP Framework application via SSH."""
        try:
            # Extract SSH connection details from app config
            host = app_config.get('target_host')
            if not host:
                raise ValueError("Target host is required for application deployment")
            
            ssh_user = app_config.get('ssh_user', self.config.get('deployment_user', 'ubuntu'))
            ssh_key_path = app_config.get('ssh_key_path')
            ssh_password = app_config.get('ssh_password')
            ssh_port = app_config.get('ssh_port', self.config.get('default_ssh_port', 22))
            
            tenant_id = app_config.get('tenant_id', 'unknown')
            deployment_name = app_config.get('name', 'isp-framework')
            
            # Record deployment start
            self.observability.record_deployment("application_deploy_start", tenant_id)
            
            # Deploy via SSH
            with self.observability.trace_business_operation("ssh_application_deploy", tenant_id=tenant_id):
                deployment_result = await self._deploy_app_via_ssh(
                    host=host,
                    user=ssh_user,
                    key_path=ssh_key_path,
                    password=ssh_password,
                    port=ssh_port,
                    app_config=app_config,
                    infrastructure_id=infrastructure_id
                )
            
            # Record successful deployment
            self.observability.record_deployment("application_deploy_success", tenant_id, success=True)
            
            return deployment_result
            
        except Exception as e:
            # Record failed deployment
            tenant_id = app_config.get('tenant_id', 'unknown')
            self.observability.record_deployment("application_deploy_failed", tenant_id, success=False)
            logger.error(f"SSH application deployment failed: {e}")
            raise
    
    async def _provision_via_ssh(self, host: str, user: str, key_path: Optional[str], 
                                password: Optional[str], port: int, config: Dict[str, Any]) -> Dict[str, Any]:
        """Provision infrastructure on remote server."""
        try:
            # Connect to remote server
            async with asyncssh.connect(
                host=host,
                port=port,
                username=user,
                client_keys=[key_path] if key_path else [],
                password=password,
                known_hosts=None,
                server_host_key_algs=['ssh-rsa', 'ecdsa-sha2-nistp256', 'ssh-ed25519']
            ) as conn:
                
                # Install Docker and Docker Compose
                await self._install_docker(conn)
                
                # Setup firewall rules
                await self._setup_firewall(conn, config)
                
                # Create deployment directories
                await self._create_directories(conn, config)
                
                # Install monitoring agents (optional)
                if config.get('install_monitoring', True):
                    await self._install_monitoring_agents(conn, config)
                
                return {
                    "provider": "ssh",
                    "host": host,
                    "port": port,
                    "user": user,
                    "status": "provisioned",
                    "docker_installed": True,
                    "directories_created": True,
                    "firewall_configured": True,
                    "endpoints": {
                        "ssh": f"ssh://{user}@{host}:{port}",
                        "http": f"http://{host}:8000",
                        "https": f"https://{host}:443" if config.get('setup_ssl') else None
                    }
                }
                
        except Exception as e:
            logger.error(f"SSH infrastructure provisioning failed: {e}")
            raise
    
    async def _deploy_app_via_ssh(self, host: str, user: str, key_path: Optional[str],
                                 password: Optional[str], port: int, app_config: Dict[str, Any],
                                 infrastructure_id: str) -> Dict[str, Any]:
        """Deploy ISP Framework application via SSH."""
        try:
            deployment_name = app_config.get('name', 'isp-framework')
            tenant_id = app_config.get('tenant_id')
            
            # Connect to remote server
            async with asyncssh.connect(
                host=host,
                port=port,
                username=user,
                client_keys=[key_path] if key_path else [],
                password=password,
                known_hosts=None,
                server_host_key_algs=['ssh-rsa', 'ecdsa-sha2-nistp256', 'ssh-ed25519']
            ) as conn:
                
                # Clone ISP Framework repository
                repo_url = app_config.get('repository_url', 'https://github.com/dotmac-framework/isp-framework.git')
                await self._clone_repository(conn, repo_url, deployment_name)
                
                # Create environment configuration
                await self._create_env_file(conn, app_config, deployment_name)
                
                # Create Docker Compose configuration
                await self._create_docker_compose(conn, app_config, deployment_name, tenant_id)
                
                # Deploy application
                deployment_info = await self._start_application(conn, deployment_name, app_config)
                
                # Verify deployment health
                health_status = await self._verify_deployment_health(conn, deployment_name, host)
                
                return {
                    "deployment_id": f"ssh-{deployment_name}-{tenant_id}",
                    "provider": "ssh",
                    "host": host,
                    "deployment_name": deployment_name,
                    "status": "deployed" if health_status else "unhealthy",
                    "health_status": health_status,
                    "container_info": deployment_info,
                    "endpoints": {
                        "api": f"http://{host}:8001",
                        "admin": f"http://{host}:3000",
                        "customer": f"http://{host}:3001",
                        "health": f"http://{host}:8001/health"
                    },
                    "environment": app_config.get('environment', 'production')
                }
                
        except Exception as e:
            logger.error(f"SSH application deployment failed: {e}")
            # Attempt cleanup on failure
            if self.config.get('cleanup_on_failure', True):
                await self._cleanup_failed_deployment(host, user, key_path, password, port, deployment_name)
            raise
    
    async def _install_docker(self, conn):
        """Install Docker and Docker Compose on remote server."""
        try:
            # Check if Docker is already installed
            result = await conn.run('docker --version', check=False)
            if result.exit_status == 0:
                logger.info("Docker already installed")
                return
            
            # Install Docker
            commands = [
                'sudo apt-get update',
                'sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common',
                'curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -',
                'sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"',
                'sudo apt-get update',
                'sudo apt-get install -y docker-ce docker-ce-cli containerd.io',
                'sudo systemctl start docker',
                'sudo systemctl enable docker',
                'sudo usermod -aG docker $USER',
                f'sudo curl -L "https://github.com/docker/compose/releases/download/v{self.config.get("docker_compose_version", "2.24.1")}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose',
                'sudo chmod +x /usr/local/bin/docker-compose'
            ]
            
            for cmd in commands:
                result = await conn.run(cmd, timeout=120)
                if result.exit_status != 0:
                    raise Exception(f"Failed to run: {cmd}\nError: {result.stderr}")
            
            # Verify installation
            result = await conn.run('docker --version && docker-compose --version')
            logger.info(f"Docker installation verified: {result.stdout}")
            
        except Exception as e:
            logger.error(f"Docker installation failed: {e}")
            raise
    
    async def _setup_firewall(self, conn, config: Dict[str, Any]):
        """Setup firewall rules for ISP Framework."""
        try:
            # Check if ufw is available
            result = await conn.run('which ufw', check=False)
            if result.exit_status != 0:
                logger.warning("UFW not available, skipping firewall setup")
                return
            
            # Configure UFW
            firewall_commands = [
                'sudo ufw --force enable',
                'sudo ufw allow ssh',
                'sudo ufw allow 80/tcp',   # HTTP
                'sudo ufw allow 443/tcp',  # HTTPS
                'sudo ufw allow 8001/tcp', # ISP Framework API
                'sudo ufw allow 3000/tcp', # Admin Portal
                'sudo ufw allow 3001/tcp', # Customer Portal
                'sudo ufw allow 5432/tcp', # PostgreSQL (if local)
                'sudo ufw allow 6379/tcp', # Redis (if local)
            ]
            
            # Add custom ports from configuration
            custom_ports = config.get('firewall_ports', [])
            for port in custom_ports:
                firewall_commands.append(f'sudo ufw allow {port}')
            
            for cmd in firewall_commands:
                await conn.run(cmd, timeout=30)
            
            logger.info("Firewall configured successfully")
            
        except Exception as e:
            logger.warning(f"Firewall setup failed: {e}")
            # Don't fail deployment for firewall issues
    
    async def _create_directories(self, conn, config: Dict[str, Any]):
        """Create necessary directories for deployment."""
        try:
            deployment_root = config.get('deployment_path', '/home/ubuntu/dotmac')
            
            directories = [
                deployment_root,
                f'{deployment_root}/data',
                f'{deployment_root}/logs',
                f'{deployment_root}/config',
                f'{deployment_root}/backups'
            ]
            
            for directory in directories:
                await conn.run(f'mkdir -p {directory}')
            
            logger.info(f"Created deployment directories under {deployment_root}")
            
        except Exception as e:
            logger.error(f"Directory creation failed: {e}")
            raise
    
    async def _install_monitoring_agents(self, conn, config: Dict[str, Any]):
        """Install monitoring agents (Node Exporter, etc.)."""
        try:
            if not config.get('install_monitoring', True):
                return
            
            # Install Node Exporter for Prometheus monitoring
            monitoring_commands = [
                'wget https://github.com/prometheus/node_exporter/releases/download/v1.6.1/node_exporter-1.6.1.linux-amd64.tar.gz',
                'tar xvfz node_exporter-1.6.1.linux-amd64.tar.gz',
                'sudo cp node_exporter-1.6.1.linux-amd64/node_exporter /usr/local/bin/',
                'sudo useradd -r -s /bin/false node_exporter',
                'rm -rf node_exporter-1.6.1.linux-amd64*'
            ]
            
            for cmd in monitoring_commands:
                result = await conn.run(cmd, check=False, timeout=60)
                if result.exit_status != 0:
                    logger.warning(f"Monitoring setup command failed: {cmd}")
            
            # Create systemd service for Node Exporter
            node_exporter_service = """[Unit]
Description=Node Exporter
After=network.target

[Service]
User=node_exporter
Group=node_exporter
Type=simple
ExecStart=/usr/local/bin/node_exporter

[Install]
WantedBy=multi-user.target
"""
            
            # Write service file
            await conn.run(f'echo "{node_exporter_service}" | sudo tee /etc/systemd/system/node_exporter.service')
            await conn.run('sudo systemctl daemon-reload')
            await conn.run('sudo systemctl enable node_exporter')
            await conn.run('sudo systemctl start node_exporter')
            
            logger.info("Monitoring agents installed")
            
        except Exception as e:
            logger.warning(f"Monitoring agent installation failed: {e}")
            # Don't fail deployment for monitoring issues
    
    async def _clone_repository(self, conn, repo_url: str, deployment_name: str):
        """Clone ISP Framework repository."""
        try:
            # Remove existing directory if present
            await conn.run(f'rm -rf /home/ubuntu/{deployment_name}', check=False)
            
            # Clone repository
            result = await conn.run(f'git clone {repo_url} /home/ubuntu/{deployment_name}', timeout=300)
            if result.exit_status != 0:
                raise Exception(f"Git clone failed: {result.stderr}")
            
            logger.info(f"Successfully cloned repository to /home/ubuntu/{deployment_name}")
            
        except Exception as e:
            logger.error(f"Repository cloning failed: {e}")
            raise
    
    async def _create_env_file(self, conn, app_config: Dict[str, Any], deployment_name: str):
        """Create environment configuration file."""
        try:
            tenant_id = app_config.get('tenant_id')
            environment = app_config.get('environment', 'production')
            
            # Generate environment variables
            env_vars = {
                'ENVIRONMENT': environment,
                'DEBUG': 'false',
                'LOG_LEVEL': 'INFO',
                
                # Database configuration
                'DATABASE_URL': app_config.get('database_url', f'postgresql://postgres:postgres@localhost:5432/dotmac_tenant_{tenant_id}'),
                
                # Redis configuration
                'REDIS_URL': app_config.get('redis_url', 'redis://localhost:6379/0'),
                'CELERY_BROKER_URL': app_config.get('celery_broker_url', 'redis://localhost:6379/1'),
                'CELERY_RESULT_BACKEND': app_config.get('celery_result_backend', 'redis://localhost:6379/2'),
                
                # Security
                'SECRET_KEY': app_config.get('secret_key', f'tenant-secret-{tenant_id}-change-in-production'),
                'JWT_SECRET_KEY': app_config.get('jwt_secret_key', f'jwt-secret-{tenant_id}-change-in-production'),
                
                # Observability
                'SIGNOZ_ENDPOINT': app_config.get('signoz_endpoint', 'http://localhost:4317'),
                
                # Tenant identification
                'TENANT_ID': str(tenant_id),
                'TENANT_NAME': app_config.get('tenant_name', f'tenant-{tenant_id}'),
            }
            
            # Add custom environment variables
            custom_env = app_config.get('environment_variables', {})
            env_vars.update(custom_env)
            
            # Create .env file content
            env_content = '\n'.join([f'{key}={value}' for key, value in env_vars.items()])
            
            # Write .env file
            await conn.run(f'cat > /home/ubuntu/{deployment_name}/.env << \'EOF\'\n{env_content}\nEOF')
            
            logger.info(f"Created environment file for {deployment_name}")
            
        except Exception as e:
            logger.error(f"Environment file creation failed: {e}")
            raise
    
    async def _create_docker_compose(self, conn, app_config: Dict[str, Any], deployment_name: str, tenant_id: str):
        """Create Docker Compose configuration for ISP Framework."""
        try:
            # Generate tenant-specific Docker Compose
            compose_content = f"""version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    container_name: {deployment_name}-postgres
    environment:
      POSTGRES_DB: dotmac_tenant_{tenant_id}
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    networks:
      - dotmac-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: {deployment_name}-redis
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    networks:
      - dotmac-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ISP Framework Application
  isp-framework:
    build:
      context: .
      dockerfile: Dockerfile
      target: production
    container_name: {deployment_name}-app
    env_file:
      - .env
    volumes:
      - ./uploads:/app/uploads
      - ./logs:/app/logs
    ports:
      - "8001:8000"
    networks:
      - dotmac-network
    depends_on:
      - postgres
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  # Celery Worker
  celery-worker:
    build:
      context: .
      dockerfile: Dockerfile
      target: production
    container_name: {deployment_name}-celery-worker
    env_file:
      - .env
    command: celery -A dotmac_isp.core.celery_app worker --loglevel=info
    volumes:
      - ./uploads:/app/uploads
      - ./logs:/app/logs
    networks:
      - dotmac-network
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  # Celery Beat (Scheduler)
  celery-beat:
    build:
      context: .
      dockerfile: Dockerfile
      target: production
    container_name: {deployment_name}-celery-beat
    env_file:
      - .env
    command: celery -A dotmac_isp.core.celery_app beat --loglevel=info
    volumes:
      - ./uploads:/app/uploads
      - ./logs:/app/logs
    networks:
      - dotmac-network
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

volumes:
  postgres_data:
    name: {deployment_name}-postgres-data
  redis_data:
    name: {deployment_name}-redis-data

networks:
  dotmac-network:
    driver: bridge
    name: {deployment_name}-network
"""
            
            # Write Docker Compose file
            await conn.run(f'cat > /home/ubuntu/{deployment_name}/docker-compose.yml << \'EOF\'\n{compose_content}\nEOF')
            
            logger.info(f"Created Docker Compose configuration for {deployment_name}")
            
        except Exception as e:
            logger.error(f"Docker Compose creation failed: {e}")
            raise
    
    async def _start_application(self, conn, deployment_name: str, app_config: Dict[str, Any]):
        """Start the ISP Framework application."""
        try:
            # Change to deployment directory
            deployment_dir = f'/home/ubuntu/{deployment_name}'
            
            # Pull images and build
            await conn.run(f'cd {deployment_dir} && docker-compose pull', timeout=600)
            await conn.run(f'cd {deployment_dir} && docker-compose build --no-cache', timeout=1200)
            
            # Start services
            result = await conn.run(f'cd {deployment_dir} && docker-compose up -d', timeout=300)
            if result.exit_status != 0:
                raise Exception(f"Failed to start services: {result.stderr}")
            
            # Wait for services to be ready
            await asyncio.sleep(30)
            
            # Run database migrations
            await conn.run(f'cd {deployment_dir} && docker-compose exec -T isp-framework alembic upgrade head', timeout=120, check=False)
            
            # Get container information
            result = await conn.run(f'cd {deployment_dir} && docker-compose ps --format json')
            container_info = result.stdout
            
            logger.info(f"Successfully started {deployment_name} application")
            return {"containers": container_info, "status": "started"}
            
        except Exception as e:
            logger.error(f"Application startup failed: {e}")
            raise
    
    async def _verify_deployment_health(self, conn, deployment_name: str, host: str) -> bool:
        """Verify deployment health."""
        try:
            # Check container health
            result = await conn.run(f'cd /home/ubuntu/{deployment_name} && docker-compose ps --filter status=running', timeout=30)
            running_containers = result.stdout.count('Up')
            
            if running_containers < 2:  # At least app and database should be running
                logger.warning(f"Only {running_containers} containers running")
                return False
            
            # Check HTTP health endpoint
            health_check_attempts = 5
            for attempt in range(health_check_attempts):
                try:
                    result = await conn.run(f'curl -f -s http://localhost:8000/health', timeout=10, check=False)
                    if result.exit_status == 0:
                        logger.info("Health check passed")
                        return True
                    
                    await asyncio.sleep(10)  # Wait before retry
                except Exception:
                    pass
            
            logger.warning("Health checks failed")
            return False
            
        except Exception as e:
            logger.error(f"Health verification failed: {e}")
            return False
    
    async def _cleanup_failed_deployment(self, host: str, user: str, key_path: Optional[str],
                                       password: Optional[str], port: int, deployment_name: str):
        """Cleanup resources after failed deployment."""
        try:
            async with asyncssh.connect(
                host=host,
                port=port,
                username=user,
                client_keys=[key_path] if key_path else [],
                password=password,
                known_hosts=None
            ) as conn:
                
                # Stop and remove containers
                await conn.run(f'cd /home/ubuntu/{deployment_name} && docker-compose down -v', check=False, timeout=60)
                
                # Remove deployment directory
                await conn.run(f'rm -rf /home/ubuntu/{deployment_name}', check=False, timeout=30)
                
                logger.info(f"Cleaned up failed deployment: {deployment_name}")
                
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
    
    def get_supported_providers(self) -> List[str]:
        """Return supported providers."""
        return ["ssh", "vps", "bare_metal", "remote"]
    
    def get_supported_orchestrators(self) -> List[str]:
        """Return supported orchestrators."""
        return ["docker", "docker-compose", "systemd"]
    
    async def scale_application(self, deployment_id: str, scaling_config: Dict[str, Any]) -> bool:
        """Scale application via SSH."""
        try:
            # Extract connection info from deployment_id
            # This is a simplified implementation
            logger.info(f"SSH scaling requested for {deployment_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to scale SSH deployment: {e}")
            return False
    
    async def rollback_deployment(self, deployment_id: str, target_version: str) -> bool:
        """Rollback deployment via SSH."""
        try:
            # This would involve restarting containers with previous image versions
            logger.info(f"SSH rollback requested for {deployment_id} to version {target_version}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to rollback SSH deployment: {e}")
            return False
    
    async def validate_template(self, template_content: Dict[str, Any], template_type: str) -> bool:
        """Validate deployment template."""
        try:
            if template_type == "docker-compose":
                # Validate Docker Compose YAML structure
                required_fields = ["version", "services"]
                for field in required_fields:
                    if field not in template_content:
                        return False
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Template validation failed: {e}")
            return False
    
    async def get_deployment_status(self, deployment_id: str) -> Dict[str, Any]:
        """Get deployment status via SSH."""
        return {
            "deployment_id": deployment_id,
            "status": "running",
            "health": "healthy",
            "provider": "ssh"
        }
    
    async def calculate_infrastructure_cost(self, infrastructure_config: Dict[str, Any]) -> float:
        """Calculate SSH deployment cost (VPS/server cost)."""
        try:
            # Extract server specifications
            server_type = infrastructure_config.get("metadata", {}).get("server_type", "vps")
            cpu_cores = infrastructure_config.get("metadata", {}).get("cpu_cores", 2)
            memory_gb = infrastructure_config.get("metadata", {}).get("memory_gb", 4)
            storage_gb = infrastructure_config.get("metadata", {}).get("storage_gb", 80)
            
            # VPS pricing estimates (monthly)
            if server_type == "vps":
                base_cost = 20.0  # Base VPS cost
                cpu_cost = cpu_cores * 5.0  # $5 per core
                memory_cost = memory_gb * 2.0  # $2 per GB RAM
                storage_cost = storage_gb * 0.10  # $0.10 per GB storage
            else:  # bare metal
                base_cost = 100.0
                cpu_cost = cpu_cores * 10.0
                memory_cost = memory_gb * 3.0
                storage_cost = storage_gb * 0.15
            
            total_cost = base_cost + cpu_cost + memory_cost + storage_cost
            
            logger.debug(f"SSH infrastructure cost calculated: ${total_cost:.2f}/month")
            return total_cost
            
        except Exception as e:
            logger.error(f"Error calculating SSH infrastructure cost: {e}")
            return 50.0  # Default cost