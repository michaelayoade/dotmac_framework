"""
VPS Provisioning Service
Handles customer VPS deployment and management using SSH automation
"""

import asyncio
import secrets
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from dotmac_shared.core.logging import get_logger
from dotmac_shared.api.exceptions import standard_exception_handler
from dotmac_management.models.vps_customer import VPSCustomer, VPSStatus, VPSDeploymentEvent
from dotmac_management.services.vps_requirements import VPSRequirementsService
from packages.dotmac_network_automation.dotmac_network.ssh.automation import SSHAutomation
from packages.dotmac_network_automation.dotmac_network.ssh.types import (
    DeviceCredentials, SSHConnectionConfig, DeviceType
)

logger = get_logger(__name__)


class VPSProvisioningService:
    """
    Handles VPS customer deployment workflow:
    1. Validate VPS connectivity and requirements
    2. Install Docker and dependencies
    3. Deploy DotMac ISP Framework
    4. Configure monitoring and backups
    5. Run health checks and testing
    6. Provide customer access and documentation
    """
    
    def __init__(self):
        self.ssh_automation = SSHAutomation()
        self.requirements_service = VPSRequirementsService()
    
    @standard_exception_handler
    async def setup_vps_customer(self, customer_db_id: int, db: Session) -> bool:
        """
        Main VPS setup workflow - runs in background task
        """
        correlation_id = f"vps-setup-{secrets.token_hex(8)}"
        
        try:
            # Get customer from database
            customer = db.query(VPSCustomer).filter_by(id=customer_db_id).first()
            if not customer:
                logger.error(f"VPS customer {customer_db_id} not found for setup")
                return False
            
            logger.info(f"Starting VPS setup for customer {customer.customer_id} (correlation: {correlation_id})")
            
            # Step 1: Validate VPS connectivity
            if not await self._validate_vps_connectivity(db, customer, correlation_id):
                return False
            
            # Step 2: Check server requirements
            if not await self._check_server_requirements(db, customer, correlation_id):
                return False
            
            # Step 3: Install dependencies (Docker, etc.)
            if not await self._install_dependencies(db, customer, correlation_id):
                return False
            
            # Step 4: Deploy ISP Framework
            if not await self._deploy_isp_framework(db, customer, correlation_id):
                return False
            
            # Step 5: Configure monitoring
            if not await self._setup_monitoring(db, customer, correlation_id):
                return False
            
            # Step 6: Run health checks
            if not await self._run_health_checks(db, customer, correlation_id):
                return False
            
            # Step 7: Finalize setup
            await self._finalize_setup(db, customer, correlation_id)
            
            logger.info(f"✅ VPS setup completed: {customer.customer_id}")
            return True
            
        except Exception as e:
            logger.error(f"VPS setup failed: {e}")
            await self._handle_setup_failure(db, customer_db_id, str(e), correlation_id)
            return False
    
    async def _validate_vps_connectivity(
        self, db: Session, customer: VPSCustomer, correlation_id: str
    ) -> bool:
        """Test SSH connectivity to customer VPS"""
        
        try:
            await self._update_customer_status(
                db, customer, VPSStatus.CONNECTION_TEST,
                "Testing SSH connectivity", correlation_id, 1
            )
            
            # Prepare SSH credentials
            credentials = DeviceCredentials(
                username=customer.ssh_username,
                password=customer.ssh_password_hash,  # Would decrypt
                ssh_key=customer.ssh_key
            )
            
            config = SSHConnectionConfig(
                host=customer.vps_ip,
                port=customer.ssh_port,
                timeout=30
            )
            
            # Test SSH connection
            connection = await self.ssh_automation.connect(
                host=customer.vps_ip,
                credentials=credentials,
                config=config,
                device_type=DeviceType.LINUX_SERVER
            )
            
            # Run basic connectivity test
            response = await self.ssh_automation.execute_command(
                connection.connection_id,
                "echo 'SSH connectivity test successful'"
            )
            
            if not response.success:
                raise Exception(f"SSH test failed: {response.error_message}")
            
            # Update customer settings with test result
            customer.settings = customer.settings or {}
            customer.settings["ssh_test_passed"] = True
            customer.settings["ssh_test_timestamp"] = datetime.utcnow().isoformat()
            db.commit()
            
            await self._log_deployment_event(
                db, customer, "ssh_connectivity_test", "SSH connectivity verified",
                correlation_id, 1, exit_code=0, stdout=response.output
            )
            
            # Disconnect after test
            await self.ssh_automation.disconnect(connection.connection_id)
            
            return True
            
        except Exception as e:
            await self._log_deployment_error(
                db, customer, "ssh_connectivity_failed", str(e), correlation_id, 1
            )
            return False
    
    async def _check_server_requirements(
        self, db: Session, customer: VPSCustomer, correlation_id: str
    ) -> bool:
        """Check if server meets minimum requirements for plan"""
        
        try:
            await self._update_customer_status(
                db, customer, VPSStatus.REQUIREMENTS_CHECK,
                "Checking server requirements", correlation_id, 2
            )
            
            # Reconnect to VPS
            connection = await self._get_ssh_connection(customer)
            
            # Get server specifications
            specs = await self._gather_server_specs(connection.connection_id)
            
            # Calculate requirements for customer's plan
            requirements = await self.requirements_service.calculate_requirements(
                plan=customer.plan,
                expected_customers=customer.expected_customers,
                estimated_traffic=customer.estimated_traffic
            )
            
            # Validate specs against requirements
            validation_results = self.requirements_service.validate_vps_specs(
                provided_specs=specs,
                required_specs=requirements
            )
            
            # Store validation results
            customer.settings = customer.settings or {}
            customer.settings["requirements_passed"] = validation_results["overall_status"] == "pass"
            customer.settings["server_specs"] = specs
            customer.settings["validation_results"] = validation_results
            db.commit()
            
            await self._log_deployment_event(
                db, customer, "requirements_check", 
                f"Requirements check: {validation_results['overall_status']}", 
                correlation_id, 2,
                stdout=json.dumps(validation_results, indent=2)
            )
            
            await self.ssh_automation.disconnect(connection.connection_id)
            
            if validation_results["overall_status"] != "pass":
                raise Exception(f"Server requirements not met: {validation_results['failures']}")
            
            return True
            
        except Exception as e:
            await self._log_deployment_error(
                db, customer, "requirements_check_failed", str(e), correlation_id, 2
            )
            return False
    
    async def _install_dependencies(
        self, db: Session, customer: VPSCustomer, correlation_id: str
    ) -> bool:
        """Install Docker and other required dependencies"""
        
        try:
            await self._update_customer_status(
                db, customer, VPSStatus.DEPLOYING,
                "Installing dependencies", correlation_id, 3
            )
            
            connection = await self._get_ssh_connection(customer)
            
            # Install Docker if not present
            docker_check = await self.ssh_automation.execute_command(
                connection.connection_id,
                "docker --version"
            )
            
            if not docker_check.success:
                logger.info(f"Installing Docker for customer {customer.customer_id}")
                
                # Docker installation script
                install_commands = [
                    "apt-get update -y",
                    "apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release",
                    "curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg",
                    "echo \"deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable\" | tee /etc/apt/sources.list.d/docker.list > /dev/null",
                    "apt-get update -y",
                    "apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin",
                    "systemctl enable docker",
                    "systemctl start docker",
                    "usermod -aG docker $USER"
                ]
                
                for i, cmd in enumerate(install_commands):
                    response = await self.ssh_automation.execute_command(
                        connection.connection_id, cmd
                    )
                    
                    await self._log_deployment_event(
                        db, customer, f"docker_install_step_{i+1}", 
                        f"Executed: {cmd}", correlation_id, 3,
                        command_executed=cmd,
                        exit_code=response.exit_code,
                        stdout_output=response.output[:1000] if response.output else None,
                        stderr_output=response.error_message[:1000] if response.error_message else None
                    )
                    
                    if not response.success and "already" not in response.error_message.lower():
                        raise Exception(f"Docker installation failed at step {i+1}: {response.error_message}")
            
            # Verify Docker installation
            docker_verify = await self.ssh_automation.execute_command(
                connection.connection_id,
                "docker --version && docker compose version"
            )
            
            if not docker_verify.success:
                raise Exception("Docker installation verification failed")
            
            await self._log_deployment_event(
                db, customer, "dependencies_installed", "Dependencies installed successfully",
                correlation_id, 3, stdout_output=docker_verify.output
            )
            
            await self.ssh_automation.disconnect(connection.connection_id)
            return True
            
        except Exception as e:
            await self._log_deployment_error(
                db, customer, "dependency_installation_failed", str(e), correlation_id, 3
            )
            return False
    
    async def _deploy_isp_framework(
        self, db: Session, customer: VPSCustomer, correlation_id: str
    ) -> bool:
        """Deploy DotMac ISP Framework to customer VPS"""
        
        try:
            await self._update_customer_status(
                db, customer, VPSStatus.CONFIGURING,
                "Deploying ISP Framework", correlation_id, 4
            )
            
            connection = await self._get_ssh_connection(customer)
            
            # Use existing deploy-tenant.sh script
            deploy_command = f"""
                cd /tmp &&
                curl -sL https://raw.githubusercontent.com/dotmac/framework/main/scripts/deploy-tenant.sh -o deploy-tenant.sh &&
                chmod +x deploy-tenant.sh &&
                ./deploy-tenant.sh deploy {customer.subdomain} \\
                    --tier={customer.plan.value} \\
                    --domain={customer.custom_domain or f"{customer.subdomain}.yourdomain.com"} \\
                    --max-customers={customer.expected_customers}
            """
            
            response = await self.ssh_automation.execute_command(
                connection.connection_id, deploy_command
            )
            
            await self._log_deployment_event(
                db, customer, "isp_framework_deployment", "ISP Framework deployment",
                correlation_id, 4,
                command_executed=deploy_command,
                exit_code=response.exit_code,
                stdout_output=response.output[:2000] if response.output else None,
                stderr_output=response.error_message[:1000] if response.error_message else None
            )
            
            if not response.success:
                raise Exception(f"ISP Framework deployment failed: {response.error_message}")
            
            # Verify deployment
            verify_response = await self.ssh_automation.execute_command(
                connection.connection_id,
                f"docker ps | grep {customer.subdomain}"
            )
            
            if not verify_response.success or customer.subdomain not in verify_response.output:
                raise Exception("ISP Framework containers not running after deployment")
            
            await self.ssh_automation.disconnect(connection.connection_id)
            return True
            
        except Exception as e:
            await self._log_deployment_error(
                db, customer, "isp_deployment_failed", str(e), correlation_id, 4
            )
            return False
    
    async def _setup_monitoring(
        self, db: Session, customer: VPSCustomer, correlation_id: str
    ) -> bool:
        """Set up monitoring for customer VPS"""
        
        try:
            connection = await self._get_ssh_connection(customer)
            
            # Deploy monitoring stack using existing script
            monitoring_command = """
                cd /tmp &&
                curl -sL https://raw.githubusercontent.com/dotmac/framework/main/scripts/setup_monitoring.sh -o setup_monitoring.sh &&
                chmod +x setup_monitoring.sh &&
                ./setup_monitoring.sh
            """
            
            response = await self.ssh_automation.execute_command(
                connection.connection_id, monitoring_command
            )
            
            await self._log_deployment_event(
                db, customer, "monitoring_setup", "Monitoring setup",
                correlation_id, 5,
                command_executed=monitoring_command,
                stdout_output=response.output[:1000] if response.output else None
            )
            
            await self.ssh_automation.disconnect(connection.connection_id)
            return True
            
        except Exception as e:
            logger.warning(f"Monitoring setup failed for {customer.customer_id}: {e}")
            # Non-critical failure
            return True
    
    async def _run_health_checks(
        self, db: Session, customer: VPSCustomer, correlation_id: str
    ) -> bool:
        """Run comprehensive health checks on deployed system"""
        
        try:
            await self._update_customer_status(
                db, customer, VPSStatus.TESTING,
                "Running health checks", correlation_id, 6
            )
            
            # Test HTTP endpoints
            import httpx
            async with httpx.AsyncClient() as client:
                domain = customer.custom_domain or f"{customer.subdomain}.yourdomain.com"
                
                # Test ISP Framework health endpoint
                try:
                    response = await client.get(f"http://{customer.vps_ip}:8000/health", timeout=30)
                    if response.status_code != 200:
                        raise Exception(f"ISP health check failed: HTTP {response.status_code}")
                except Exception as e:
                    raise Exception(f"Could not reach ISP Framework: {e}")
            
            # Update health status
            customer.health_status = "healthy"
            customer.last_health_check = datetime.utcnow()
            db.commit()
            
            await self._log_deployment_event(
                db, customer, "health_checks_passed", "All health checks passed",
                correlation_id, 6
            )
            
            return True
            
        except Exception as e:
            await self._log_deployment_error(
                db, customer, "health_checks_failed", str(e), correlation_id, 6
            )
            return False
    
    async def _finalize_setup(
        self, db: Session, customer: VPSCustomer, correlation_id: str
    ):
        """Finalize setup and mark customer as ready"""
        
        # Update final status
        await self._update_customer_status(
            db, customer, VPSStatus.READY,
            "VPS setup completed successfully", correlation_id, 7
        )
        
        customer.deployment_completed_at = datetime.utcnow()
        customer.settings = customer.settings or {}
        customer.settings["deployment_ready"] = True
        customer.settings["setup_completed_at"] = datetime.utcnow().isoformat()
        db.commit()
        
        # Set customer to active
        await self._update_customer_status(
            db, customer, VPSStatus.ACTIVE,
            "Customer VPS is now active and ready for use", correlation_id, 8
        )
    
    async def _gather_server_specs(self, connection_id: str) -> Dict[str, Any]:
        """Gather server specifications via SSH"""
        
        commands = {
            "cpu_cores": "nproc",
            "total_memory_kb": "grep MemTotal /proc/meminfo | awk '{print $2}'",
            "disk_space_gb": "df -BG / | awk 'NR==2 {print $2}' | sed 's/G//'",
            "operating_system": "lsb_release -d | cut -f2",
            "kernel_version": "uname -r",
            "architecture": "uname -m"
        }
        
        specs = {}
        
        for spec_name, command in commands.items():
            try:
                response = await self.ssh_automation.execute_command(connection_id, command)
                if response.success:
                    value = response.output.strip()
                    # Convert numeric values
                    if spec_name in ["cpu_cores", "total_memory_kb", "disk_space_gb"]:
                        try:
                            specs[spec_name] = int(value)
                        except ValueError:
                            specs[spec_name] = value
                    else:
                        specs[spec_name] = value
                else:
                    specs[spec_name] = "unknown"
            except Exception:
                specs[spec_name] = "error"
        
        # Convert memory to GB
        if "total_memory_kb" in specs and isinstance(specs["total_memory_kb"], int):
            specs["ram_gb"] = max(1, specs["total_memory_kb"] // 1024 // 1024)
        
        return specs
    
    async def _get_ssh_connection(self, customer: VPSCustomer):
        """Get SSH connection to customer VPS"""
        
        credentials = DeviceCredentials(
            username=customer.ssh_username,
            password=customer.ssh_password_hash,  # Would decrypt
            ssh_key=customer.ssh_key
        )
        
        config = SSHConnectionConfig(
            host=customer.vps_ip,
            port=customer.ssh_port,
            timeout=60
        )
        
        return await self.ssh_automation.connect(
            host=customer.vps_ip,
            credentials=credentials,
            config=config,
            device_type=DeviceType.LINUX_SERVER
        )
    
    async def _update_customer_status(
        self, db: Session, customer: VPSCustomer, status: VPSStatus,
        message: str, correlation_id: str, step_number: Optional[int] = None
    ):
        """Update customer status and log event"""
        
        customer.status = status
        db.commit()
        
        await self._log_deployment_event(
            db, customer, f"status_change.{status.value}", message,
            correlation_id, step_number or 0
        )
        
        logger.info(f"VPS Customer {customer.customer_id}: {status.value} - {message}")
    
    async def _log_deployment_event(
        self, db: Session, customer: VPSCustomer, event_type: str,
        message: str, correlation_id: str, step_number: int,
        command_executed: str = None, exit_code: int = None,
        stdout_output: str = None, stderr_output: str = None
    ):
        """Log deployment event"""
        
        event = VPSDeploymentEvent(
            event_id=f"{correlation_id}-{event_type}-{secrets.token_hex(4)}",
            vps_customer_id=customer.id,
            event_type=event_type,
            status="success" if exit_code == 0 or exit_code is None else "failed",
            message=message,
            step_number=step_number,
            correlation_id=correlation_id,
            operator="system",
            command_executed=command_executed,
            exit_code=exit_code,
            stdout_output=stdout_output,
            stderr_output=stderr_output
        )
        
        db.add(event)
        db.commit()
    
    async def _log_deployment_error(
        self, db: Session, customer: VPSCustomer, event_type: str,
        error_message: str, correlation_id: str, step_number: int
    ):
        """Log deployment error event"""
        
        event = VPSDeploymentEvent(
            event_id=f"{correlation_id}-{event_type}-{secrets.token_hex(4)}",
            vps_customer_id=customer.id,
            event_type=event_type,
            status="failed",
            message=f"Error: {error_message}",
            step_number=step_number,
            correlation_id=correlation_id,
            operator="system",
            error_details={"error": error_message, "timestamp": datetime.utcnow().isoformat()}
        )
        
        db.add(event)
        db.commit()
    
    async def _handle_setup_failure(
        self, db: Session, customer_db_id: int, error_message: str, correlation_id: str
    ):
        """Handle setup failure"""
        
        try:
            customer = db.query(VPSCustomer).filter_by(id=customer_db_id).first()
            if customer:
                customer.status = VPSStatus.FAILED
                customer.settings = customer.settings or {}
                customer.settings["last_error"] = error_message
                customer.settings["failed_at"] = datetime.utcnow().isoformat()
                db.commit()
                
                logger.error(f"VPS setup failed: {customer.customer_id} - {error_message}")
        except Exception as e:
            logger.error(f"Failed to handle setup failure: {e}")