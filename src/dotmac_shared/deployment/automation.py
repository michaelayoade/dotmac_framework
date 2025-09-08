"""
Deployment Automation System

Provides comprehensive deployment automation capabilities including
container orchestration, blue-green deployments, canary releases,
and CI/CD pipeline integration with health monitoring.
"""

import asyncio
import logging
import os
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

import yaml

from ..gateway import UnifiedAPIGateway
from ..mesh import ServiceMesh
from .monitoring import MonitoringStack


class DeploymentStrategy(str, Enum):
    """Deployment strategy types."""

    ROLLING = "rolling"
    BLUE_GREEN = "blue_green"
    CANARY = "canary"
    RECREATE = "recreate"


class DeploymentStatus(str, Enum):
    """Deployment status states."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"


class HealthCheckType(str, Enum):
    """Health check types for deployments."""

    HTTP = "http"
    TCP = "tcp"
    EXEC = "exec"
    GRPC = "grpc"


@dataclass
class HealthCheckConfig:
    """Health check configuration for deployment validation."""

    type: HealthCheckType
    endpoint: str
    interval_seconds: int = 30
    timeout_seconds: int = 10
    retries: int = 3
    success_threshold: int = 1
    failure_threshold: int = 3
    headers: Optional[dict[str, str]] = None
    expected_status: int = 200


@dataclass
class ResourceLimits:
    """Resource limits for container deployment."""

    cpu: Optional[str] = None
    memory: Optional[str] = None
    disk: Optional[str] = None
    network_bandwidth: Optional[str] = None


@dataclass
class DeploymentSpec:
    """Deployment specification configuration."""

    service_name: str
    image: str
    tag: str
    replicas: int = 1
    strategy: DeploymentStrategy = DeploymentStrategy.ROLLING
    resource_limits: Optional[ResourceLimits] = None
    environment_variables: dict[str, str] = field(default_factory=dict)
    health_checks: list[HealthCheckConfig] = field(default_factory=list)
    volumes: dict[str, str] = field(default_factory=dict)
    ports: dict[int, int] = field(default_factory=dict)
    labels: dict[str, str] = field(default_factory=dict)
    annotations: dict[str, str] = field(default_factory=dict)
    rollback_timeout: int = 300  # 5 minutes
    progressive_traffic: bool = False
    canary_percentage: int = 10  # For canary deployments


@dataclass
class DeploymentResult:
    """Result of a deployment operation."""

    deployment_id: str
    service_name: str
    status: DeploymentStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    rollback_reason: Optional[str] = None
    metrics: dict[str, Any] = field(default_factory=dict)
    health_check_results: list[dict[str, Any]] = field(default_factory=list)


class ContainerOrchestrator(ABC):
    """Abstract base class for container orchestrators."""

    @abstractmethod
    async def deploy(self, spec: DeploymentSpec) -> str:
        """Deploy a service using the orchestrator."""
        pass

    @abstractmethod
    async def get_deployment_status(self, deployment_id: str) -> DeploymentStatus:
        """Get the status of a deployment."""
        pass

    @abstractmethod
    async def rollback(self, deployment_id: str) -> bool:
        """Rollback a deployment."""
        pass

    @abstractmethod
    async def scale(self, service_name: str, replicas: int) -> bool:
        """Scale a service to the specified number of replicas."""
        pass


class DockerOrchestrator(ContainerOrchestrator):
    """Docker-based container orchestrator."""

    def __init__(self, monitoring: MonitoringStack):
        self.monitoring = monitoring
        self.logger = logging.getLogger(__name__)
        self.deployments: dict[str, DeploymentResult] = {}

    async def deploy(self, spec: DeploymentSpec) -> str:
        """Deploy using Docker Compose or Docker Swarm."""
        deployment_id = (
            f"{spec.service_name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        )

        try:
            with self.monitoring.create_span(
                "docker_deploy", spec.service_name
            ) as span:
                span.set_tag("deployment_id", deployment_id)
                span.set_tag("strategy", spec.strategy)

                # Create deployment result
                result = DeploymentResult(
                    deployment_id=deployment_id,
                    service_name=spec.service_name,
                    status=DeploymentStatus.IN_PROGRESS,
                    start_time=datetime.now(),
                )
                self.deployments[deployment_id] = result

                # Generate Docker Compose configuration
                compose_config = self._generate_compose_config(spec)

                # Write temporary compose file
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".yml", delete=False
                ) as f:
                    yaml.dump(compose_config, f)
                    compose_file = f.name

                try:
                    # Deploy based on strategy
                    if spec.strategy == DeploymentStrategy.BLUE_GREEN:
                        await self._blue_green_deploy(spec, compose_file, deployment_id)
                    elif spec.strategy == DeploymentStrategy.CANARY:
                        await self._canary_deploy(spec, compose_file, deployment_id)
                    else:
                        await self._rolling_deploy(spec, compose_file, deployment_id)

                    # Update status
                    result.status = DeploymentStatus.SUCCEEDED
                    result.end_time = datetime.now()

                    self.logger.info(
                        f"Deployment {deployment_id} completed successfully"
                    )
                    return deployment_id

                finally:
                    # Cleanup temporary files
                    os.unlink(compose_file)

        except Exception as e:
            self.logger.error(f"Deployment {deployment_id} failed: {str(e)}")
            if deployment_id in self.deployments:
                self.deployments[deployment_id].status = DeploymentStatus.FAILED
                self.deployments[deployment_id].error_message = str(e)
                self.deployments[deployment_id].end_time = datetime.now()
            raise

    async def get_deployment_status(self, deployment_id: str) -> DeploymentStatus:
        """Get deployment status."""
        if deployment_id in self.deployments:
            return self.deployments[deployment_id].status
        return DeploymentStatus.FAILED

    async def rollback(self, deployment_id: str) -> bool:
        """Rollback a deployment."""
        if deployment_id not in self.deployments:
            return False

        try:
            result = self.deployments[deployment_id]
            result.status = DeploymentStatus.ROLLING_BACK

            # Find previous deployment
            previous_deployment = self._find_previous_deployment(
                result.service_name, deployment_id
            )
            if previous_deployment:
                # Restore previous version
                await self._restore_deployment(previous_deployment)
                result.status = DeploymentStatus.ROLLED_BACK
                return True

            return False

        except Exception as e:
            self.logger.error(f"Rollback failed for {deployment_id}: {str(e)}")
            return False

    async def scale(self, service_name: str, replicas: int) -> bool:
        """Scale a service."""
        try:
            cmd = ["docker", "service", "scale", f"{service_name}={replicas}"]
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                self.logger.info(f"Scaled {service_name} to {replicas} replicas")
                return True
            else:
                self.logger.error(f"Scaling failed: {stderr.decode()}")
                return False

        except Exception as e:
            self.logger.error(f"Scaling error: {str(e)}")
            return False

    def _generate_compose_config(self, spec: DeploymentSpec) -> dict[str, Any]:
        """Generate Docker Compose configuration."""
        service_config = {
            "image": f"{spec.image}:{spec.tag}",
            "deploy": {
                "replicas": spec.replicas,
                "restart_policy": {
                    "condition": "on-failure",
                    "delay": "5s",
                    "max_attempts": 3,
                },
            },
            "environment": spec.environment_variables,
            "labels": spec.labels,
        }

        # Add resource limits
        if spec.resource_limits:
            resources = {}
            if spec.resource_limits.cpu:
                resources["cpus"] = spec.resource_limits.cpu
            if spec.resource_limits.memory:
                resources["memory"] = spec.resource_limits.memory
            if resources:
                service_config["deploy"]["resources"] = {"limits": resources}

        # Add ports
        if spec.ports:
            service_config["ports"] = [
                f"{host}:{container}" for host, container in spec.ports.items()
            ]

        # Add volumes
        if spec.volumes:
            service_config["volumes"] = [
                f"{host}:{container}" for host, container in spec.volumes.items()
            ]

        # Add health check
        if spec.health_checks:
            health_check = spec.health_checks[0]  # Use first health check
            if health_check.type == HealthCheckType.HTTP:
                service_config["healthcheck"] = {
                    "test": ["CMD", "curl", "-f", health_check.endpoint],
                    "interval": f"{health_check.interval_seconds}s",
                    "timeout": f"{health_check.timeout_seconds}s",
                    "retries": health_check.retries,
                }

        return {"version": "3.8", "services": {spec.service_name: service_config}}

    async def _rolling_deploy(
        self, spec: DeploymentSpec, compose_file: str, deployment_id: str
    ):
        """Perform rolling deployment."""
        cmd = ["docker-compose", "-f", compose_file, "up", "-d", "--remove-orphans"]
        await self._run_command(cmd)

        # Wait for health checks
        await self._wait_for_health_checks(spec, deployment_id)

    async def _blue_green_deploy(
        self, spec: DeploymentSpec, compose_file: str, deployment_id: str
    ):
        """Perform blue-green deployment."""
        # Deploy to green environment
        green_service = f"{spec.service_name}-green"

        # Update compose config for green deployment
        with open(compose_file) as f:
            config = yaml.safe_load(f)

        # Rename service to green
        config["services"][green_service] = config["services"].pop(spec.service_name)

        with open(compose_file, "w") as f:
            yaml.dump(config, f)

        # Deploy green
        cmd = ["docker-compose", "-f", compose_file, "up", "-d"]
        await self._run_command(cmd)

        # Wait for health checks on green
        green_spec = DeploymentSpec(**spec.__dict__)
        green_spec.service_name = green_service
        await self._wait_for_health_checks(green_spec, deployment_id)

        # Switch traffic from blue to green
        await self._switch_traffic(spec.service_name, green_service)

        # Remove blue deployment
        await self._cleanup_blue_deployment(spec.service_name)

    async def _canary_deploy(
        self, spec: DeploymentSpec, compose_file: str, deployment_id: str
    ):
        """Perform canary deployment."""
        canary_service = f"{spec.service_name}-canary"

        # Calculate canary replicas
        canary_replicas = max(1, int(spec.replicas * spec.canary_percentage / 100))
        spec.replicas - canary_replicas

        # Deploy canary version
        canary_spec = DeploymentSpec(**spec.__dict__)
        canary_spec.service_name = canary_service
        canary_spec.replicas = canary_replicas

        # Deploy canary
        canary_compose = self._generate_compose_config(canary_spec)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(canary_compose, f)
            canary_file = f.name

        try:
            cmd = ["docker-compose", "-f", canary_file, "up", "-d"]
            await self._run_command(cmd)

            # Wait for canary health checks
            await self._wait_for_health_checks(canary_spec, deployment_id)

            # Monitor canary metrics
            canary_healthy = await self._monitor_canary_metrics(
                canary_service, deployment_id
            )

            if canary_healthy:
                # Promote canary to full deployment
                await self._promote_canary(spec, canary_service, deployment_id)
            else:
                # Rollback canary
                await self._rollback_canary(canary_service, deployment_id)
                raise Exception("Canary deployment failed health checks")

        finally:
            os.unlink(canary_file)

    async def _wait_for_health_checks(self, spec: DeploymentSpec, deployment_id: str):
        """Wait for health checks to pass."""
        if not spec.health_checks:
            await asyncio.sleep(10)  # Default wait time
            return

        for health_check in spec.health_checks:
            success_count = 0
            failure_count = 0

            while (
                success_count < health_check.success_threshold
                and failure_count < health_check.failure_threshold
            ):
                try:
                    if health_check.type == HealthCheckType.HTTP:
                        # Perform HTTP health check
                        import aiohttp

                        async with aiohttp.ClientSession(
                            timeout=aiohttp.ClientTimeout(total=30)
                        ) as session:
                            async with session.get(
                                health_check.endpoint,
                                headers=health_check.headers,
                                timeout=health_check.timeout_seconds,
                            ) as response:
                                if response.status == health_check.expected_status:
                                    success_count += 1
                                    failure_count = 0
                                else:
                                    failure_count += 1
                                    success_count = 0

                    elif health_check.type == HealthCheckType.TCP:
                        # Perform TCP health check
                        host, port = health_check.endpoint.split(":")
                        reader, writer = await asyncio.wait_for(
                            asyncio.open_connection(host, int(port)),
                            timeout=health_check.timeout_seconds,
                        )
                        writer.close()
                        await writer.wait_closed()
                        success_count += 1
                        failure_count = 0

                    # Record health check result
                    result = self.deployments[deployment_id]
                    result.health_check_results.append(
                        {
                            "timestamp": datetime.now().isoformat(),
                            "type": health_check.type,
                            "endpoint": health_check.endpoint,
                            "status": "success",
                            "success_count": success_count,
                            "failure_count": failure_count,
                        }
                    )

                except Exception as e:
                    failure_count += 1
                    success_count = 0

                    # Record failure
                    result = self.deployments[deployment_id]
                    result.health_check_results.append(
                        {
                            "timestamp": datetime.now().isoformat(),
                            "type": health_check.type,
                            "endpoint": health_check.endpoint,
                            "status": "failure",
                            "error": str(e),
                            "success_count": success_count,
                            "failure_count": failure_count,
                        }
                    )

                if failure_count < health_check.failure_threshold:
                    await asyncio.sleep(health_check.interval_seconds)

            if failure_count >= health_check.failure_threshold:
                raise Exception(f"Health check failed for {health_check.endpoint}")

    async def _run_command(self, cmd: list[str]):
        """Run a shell command asynchronously."""
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise Exception(
                f"Command failed: {' '.join(cmd)}\nError: {stderr.decode()}"
            )

        return stdout.decode()

    async def _switch_traffic(self, blue_service: str, green_service: str):
        """Switch traffic from blue to green service."""
        # Implementation would depend on load balancer/proxy configuration
        self.logger.info(f"Switching traffic from {blue_service} to {green_service}")

    async def _cleanup_blue_deployment(self, service_name: str):
        """Cleanup old blue deployment."""
        cmd = ["docker", "service", "rm", service_name]
        try:
            await self._run_command(cmd)
        except Exception as e:
            self.logger.warning(f"Failed to cleanup blue deployment: {str(e)}")

    async def _monitor_canary_metrics(
        self, canary_service: str, deployment_id: str
    ) -> bool:
        """Monitor canary deployment metrics."""
        # Monitor for 5 minutes
        monitoring_duration = 300
        check_interval = 30

        for _ in range(monitoring_duration // check_interval):
            try:
                # Check error rate, response time, etc.
                metrics = await self._collect_canary_metrics(canary_service)

                # Store metrics
                result = self.deployments[deployment_id]
                result.metrics.update(metrics)

                # Check if metrics are within acceptable thresholds
                if not self._validate_canary_metrics(metrics):
                    return False

                await asyncio.sleep(check_interval)

            except Exception as e:
                self.logger.error(f"Error monitoring canary: {str(e)}")
                return False

        return True

    async def _collect_canary_metrics(self, service_name: str) -> dict[str, float]:
        """Collect metrics for canary deployment."""
        # This would integrate with your monitoring system
        return {
            "error_rate": 0.01,  # 1% error rate
            "response_time_p95": 250.0,  # 250ms
            "cpu_usage": 45.0,  # 45%
            "memory_usage": 60.0,  # 60%
        }

    def _validate_canary_metrics(self, metrics: dict[str, float]) -> bool:
        """Validate canary metrics against thresholds."""
        thresholds = {
            "error_rate": 0.05,  # Max 5% error rate
            "response_time_p95": 500.0,  # Max 500ms response time
            "cpu_usage": 80.0,  # Max 80% CPU
            "memory_usage": 90.0,  # Max 90% memory
        }

        for metric, value in metrics.items():
            if metric in thresholds and value > thresholds[metric]:
                self.logger.warning(
                    f"Canary metric {metric} exceeded threshold: {value} > {thresholds[metric]}"
                )
                return False

        return True

    async def _promote_canary(
        self, spec: DeploymentSpec, canary_service: str, deployment_id: str
    ):
        """Promote canary to full deployment."""
        self.logger.info(f"Promoting canary {canary_service} to full deployment")

        # Scale up canary to full replicas
        await self.scale(canary_service, spec.replicas)

        # Remove old service
        await self._cleanup_blue_deployment(spec.service_name)

        # Rename canary to main service
        # This would involve service discovery updates

    async def _rollback_canary(self, canary_service: str, deployment_id: str):
        """Rollback failed canary deployment."""
        self.logger.info(f"Rolling back canary {canary_service}")

        # Remove canary service
        cmd = ["docker", "service", "rm", canary_service]
        try:
            await self._run_command(cmd)
        except Exception as e:
            self.logger.warning(f"Failed to rollback canary: {str(e)}")

    def _find_previous_deployment(
        self, service_name: str, current_deployment_id: str
    ) -> Optional[DeploymentResult]:
        """Find the previous successful deployment for rollback."""
        previous_deployments = [
            result
            for result in self.deployments.values()
            if (
                result.service_name == service_name
                and result.deployment_id != current_deployment_id
                and result.status == DeploymentStatus.SUCCEEDED
            )
        ]

        if previous_deployments:
            # Return most recent successful deployment
            return max(previous_deployments, key=lambda x: x.start_time)

        return None

    async def _restore_deployment(self, deployment: DeploymentResult):
        """Restore a previous deployment."""
        # This would restore the previous deployment configuration
        self.logger.info(f"Restoring deployment {deployment.deployment_id}")


class KubernetesOrchestrator(ContainerOrchestrator):
    """Kubernetes-based container orchestrator."""

    def __init__(self, monitoring: MonitoringStack, namespace: str = "default"):
        self.monitoring = monitoring
        self.namespace = namespace
        self.logger = logging.getLogger(__name__)
        self.deployments: dict[str, DeploymentResult] = {}

    async def deploy(self, spec: DeploymentSpec) -> str:
        """Deploy using Kubernetes."""
        deployment_id = (
            f"{spec.service_name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        )

        try:
            with self.monitoring.create_span("k8s_deploy", spec.service_name) as span:
                span.set_tag("deployment_id", deployment_id)
                span.set_tag("strategy", spec.strategy)

                # Create deployment result
                result = DeploymentResult(
                    deployment_id=deployment_id,
                    service_name=spec.service_name,
                    status=DeploymentStatus.IN_PROGRESS,
                    start_time=datetime.now(),
                )
                self.deployments[deployment_id] = result

                # Generate Kubernetes manifests
                manifests = self._generate_k8s_manifests(spec)

                # Apply manifests
                await self._apply_manifests(manifests, spec.strategy, deployment_id)

                # Update status
                result.status = DeploymentStatus.SUCCEEDED
                result.end_time = datetime.now()

                self.logger.info(
                    f"Kubernetes deployment {deployment_id} completed successfully"
                )
                return deployment_id

        except Exception as e:
            self.logger.error(f"Kubernetes deployment {deployment_id} failed: {str(e)}")
            if deployment_id in self.deployments:
                self.deployments[deployment_id].status = DeploymentStatus.FAILED
                self.deployments[deployment_id].error_message = str(e)
                self.deployments[deployment_id].end_time = datetime.now()
            raise

    async def get_deployment_status(self, deployment_id: str) -> DeploymentStatus:
        """Get Kubernetes deployment status."""
        if deployment_id in self.deployments:
            return self.deployments[deployment_id].status
        return DeploymentStatus.FAILED

    async def rollback(self, deployment_id: str) -> bool:
        """Rollback Kubernetes deployment."""
        if deployment_id not in self.deployments:
            return False

        try:
            result = self.deployments[deployment_id]
            result.status = DeploymentStatus.ROLLING_BACK

            cmd = [
                "kubectl",
                "rollout",
                "undo",
                f"deployment/{result.service_name}",
                "--namespace",
                self.namespace,
            ]
            await self._run_kubectl_command(cmd)

            result.status = DeploymentStatus.ROLLED_BACK
            return True

        except Exception as e:
            self.logger.error(
                f"Kubernetes rollback failed for {deployment_id}: {str(e)}"
            )
            return False

    async def scale(self, service_name: str, replicas: int) -> bool:
        """Scale Kubernetes deployment."""
        try:
            cmd = [
                "kubectl",
                "scale",
                f"deployment/{service_name}",
                f"--replicas={replicas}",
                "--namespace",
                self.namespace,
            ]
            await self._run_kubectl_command(cmd)
            return True
        except Exception as e:
            self.logger.error(f"Kubernetes scaling error: {str(e)}")
            return False

    def _generate_k8s_manifests(self, spec: DeploymentSpec) -> list[dict[str, Any]]:
        """Generate Kubernetes manifests."""
        deployment_manifest = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": spec.service_name,
                "namespace": self.namespace,
                "labels": spec.labels,
            },
            "spec": {
                "replicas": spec.replicas,
                "selector": {"matchLabels": {"app": spec.service_name}},
                "template": {
                    "metadata": {
                        "labels": {"app": spec.service_name, **spec.labels},
                        "annotations": spec.annotations,
                    },
                    "spec": {
                        "containers": [
                            {
                                "name": spec.service_name,
                                "image": f"{spec.image}:{spec.tag}",
                                "env": [
                                    {"name": k, "value": v}
                                    for k, v in spec.environment_variables.items()
                                ],
                                "ports": [
                                    {"containerPort": port}
                                    for port in spec.ports.values()
                                ],
                            }
                        ]
                    },
                },
            },
        }

        # Add resource limits
        if spec.resource_limits:
            resources = {}
            if spec.resource_limits.cpu or spec.resource_limits.memory:
                limits = {}
                if spec.resource_limits.cpu:
                    limits["cpu"] = spec.resource_limits.cpu
                if spec.resource_limits.memory:
                    limits["memory"] = spec.resource_limits.memory
                resources["limits"] = limits

                deployment_manifest["spec"]["template"]["spec"]["containers"][0][
                    "resources"
                ] = resources

        # Add health checks
        if spec.health_checks:
            health_check = spec.health_checks[0]
            container = deployment_manifest["spec"]["template"]["spec"]["containers"][0]

            if health_check.type == HealthCheckType.HTTP:
                probe = {
                    "httpGet": {
                        "path": health_check.endpoint,
                        "port": list(spec.ports.values())[0] if spec.ports else 8080,
                    },
                    "initialDelaySeconds": 30,
                    "periodSeconds": health_check.interval_seconds,
                    "timeoutSeconds": health_check.timeout_seconds,
                    "failureThreshold": health_check.failure_threshold,
                }
                container["livenessProbe"] = probe
                container["readinessProbe"] = probe

        # Service manifest
        service_manifest = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {"name": spec.service_name, "namespace": self.namespace},
            "spec": {
                "selector": {"app": spec.service_name},
                "ports": [
                    {"port": host_port, "targetPort": container_port}
                    for host_port, container_port in spec.ports.items()
                ],
            },
        }

        return [deployment_manifest, service_manifest]

    async def _apply_manifests(
        self,
        manifests: list[dict[str, Any]],
        strategy: DeploymentStrategy,
        deployment_id: str,
    ):
        """Apply Kubernetes manifests."""
        for manifest in manifests:
            # Write manifest to temporary file
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".yaml", delete=False
            ) as f:
                yaml.dump(manifest, f)
                manifest_file = f.name

            try:
                cmd = ["kubectl", "apply", "-f", manifest_file]
                await self._run_kubectl_command(cmd)
            finally:
                os.unlink(manifest_file)

        # Wait for deployment rollout
        if strategy != DeploymentStrategy.RECREATE:
            service_name = manifests[0]["metadata"]["name"]
            cmd = [
                "kubectl",
                "rollout",
                "status",
                f"deployment/{service_name}",
                "--namespace",
                self.namespace,
                "--timeout=600s",
            ]
            await self._run_kubectl_command(cmd)

    async def _run_kubectl_command(self, cmd: list[str]):
        """Run kubectl command."""
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise Exception(
                f"kubectl command failed: {' '.join(cmd)}\nError: {stderr.decode()}"
            )

        return stdout.decode()


class DeploymentAutomation:
    """Main deployment automation orchestrator."""

    def __init__(
        self,
        orchestrator: ContainerOrchestrator,
        monitoring: MonitoringStack,
        service_mesh: Optional[ServiceMesh] = None,
        api_gateway: Optional[UnifiedAPIGateway] = None,
    ):
        self.orchestrator = orchestrator
        self.monitoring = monitoring
        self.service_mesh = service_mesh
        self.api_gateway = api_gateway
        self.logger = logging.getLogger(__name__)
        self.deployment_history: list[DeploymentResult] = []

    async def deploy_service(self, spec: DeploymentSpec) -> DeploymentResult:
        """Deploy a service with comprehensive monitoring."""
        try:
            with self.monitoring.create_span(
                "deploy_service", spec.service_name
            ) as span:
                span.set_tag("service", spec.service_name)
                span.set_tag("strategy", spec.strategy)
                span.set_tag("replicas", spec.replicas)

                # Pre-deployment validation
                await self._validate_deployment_spec(spec)

                # Deploy using orchestrator
                deployment_id = await self.orchestrator.deploy(spec)

                # Get deployment result
                result = await self._get_deployment_result(deployment_id, spec)

                # Post-deployment integration
                if result.status == DeploymentStatus.SUCCEEDED:
                    await self._post_deployment_integration(spec, deployment_id)

                # Store in history
                self.deployment_history.append(result)

                # Emit metrics
                self.monitoring.increment_counter(
                    "deployment_total",
                    {"service": spec.service_name, "status": result.status},
                )

                if result.end_time:
                    duration = (result.end_time - result.start_time).total_seconds()
                    self.monitoring.record_histogram(
                        "deployment_duration_seconds",
                        duration,
                        {"service": spec.service_name, "strategy": spec.strategy},
                    )

                return result

        except Exception as e:
            self.logger.error(f"Deployment failed for {spec.service_name}: {str(e)}")
            self.monitoring.increment_counter(
                "deployment_errors_total",
                {"service": spec.service_name, "error": type(e).__name__},
            )
            raise

    async def rollback_service(self, deployment_id: str, reason: str = "") -> bool:
        """Rollback a service deployment."""
        try:
            with self.monitoring.create_span("rollback_service", "rollback") as span:
                span.set_tag("deployment_id", deployment_id)
                span.set_tag("reason", reason)

                success = await self.orchestrator.rollback(deployment_id)

                if success:
                    # Update deployment history
                    for result in self.deployment_history:
                        if result.deployment_id == deployment_id:
                            result.rollback_reason = reason
                            break

                    self.monitoring.increment_counter(
                        "rollback_total",
                        {"deployment_id": deployment_id, "success": str(success)},
                    )

                return success

        except Exception as e:
            self.logger.error(f"Rollback failed for {deployment_id}: {str(e)}")
            return False

    async def get_deployment_status(
        self, deployment_id: str
    ) -> Optional[DeploymentResult]:
        """Get comprehensive deployment status."""
        # Find in history
        for result in self.deployment_history:
            if result.deployment_id == deployment_id:
                # Update with current orchestrator status
                current_status = await self.orchestrator.get_deployment_status(
                    deployment_id
                )
                result.status = current_status
                return result

        return None

    async def list_deployments(
        self,
        service_name: Optional[str] = None,
        status: Optional[DeploymentStatus] = None,
        limit: int = 50,
    ) -> list[DeploymentResult]:
        """List deployment history with filtering."""
        results = self.deployment_history.copy()

        if service_name:
            results = [r for r in results if r.service_name == service_name]

        if status:
            results = [r for r in results if r.status == status]

        # Sort by start time descending
        results.sort(key=lambda x: x.start_time, reverse=True)

        return results[:limit]

    async def _validate_deployment_spec(self, spec: DeploymentSpec):
        """Validate deployment specification."""
        if not spec.service_name:
            raise ValueError("Service name is required")

        if not spec.image or not spec.tag:
            raise ValueError("Image and tag are required")

        if spec.replicas < 1:
            raise ValueError("Replicas must be at least 1")

        # Validate health checks
        for health_check in spec.health_checks:
            if health_check.type == HealthCheckType.HTTP:
                if not health_check.endpoint.startswith(("http://", "https://")):
                    raise ValueError(
                        f"Invalid HTTP health check endpoint: {health_check.endpoint}"
                    )

    async def _get_deployment_result(
        self, deployment_id: str, spec: DeploymentSpec
    ) -> DeploymentResult:
        """Get deployment result from orchestrator."""
        status = await self.orchestrator.get_deployment_status(deployment_id)

        # Create result if not exists
        result = DeploymentResult(
            deployment_id=deployment_id,
            service_name=spec.service_name,
            status=status,
            start_time=datetime.now(),
        )

        if status in [DeploymentStatus.SUCCEEDED, DeploymentStatus.FAILED]:
            result.end_time = datetime.now()

        return result

    async def _post_deployment_integration(
        self, spec: DeploymentSpec, deployment_id: str
    ):
        """Integrate deployed service with mesh and gateway."""
        try:
            # Register with service mesh
            if self.service_mesh:
                await self._register_with_service_mesh(spec)

            # Configure API gateway routes
            if self.api_gateway:
                await self._configure_gateway_routes(spec)

            self.logger.info(
                f"Post-deployment integration completed for {deployment_id}"
            )

        except Exception as e:
            self.logger.error(
                f"Post-deployment integration failed for {deployment_id}: {str(e)}"
            )

    async def _register_with_service_mesh(self, spec: DeploymentSpec):
        """Register service with service mesh."""
        try:
            # Get service mesh provider from environment or config
            mesh_provider = os.getenv('SERVICE_MESH_PROVIDER', 'istio').lower()
            
            if mesh_provider == 'istio':
                await self._register_with_istio(spec)
            elif mesh_provider == 'linkerd':
                await self._register_with_linkerd(spec)
            elif mesh_provider == 'consul':
                await self._register_with_consul_connect(spec)
            else:
                logging.warning(f"Unknown service mesh provider: {mesh_provider}")
                
        except Exception as e:
            logging.error(f"Service mesh registration failed for {spec.name}: {e}")
            # Don't fail deployment, but log the issue
    
    async def _register_with_istio(self, spec: DeploymentSpec):
        """Register service with Istio service mesh."""
        import tempfile
        import subprocess
        
        # Create Istio ServiceEntry and VirtualService
        istio_config = {
            'apiVersion': 'networking.istio.io/v1beta1',
            'kind': 'ServiceEntry',
            'metadata': {
                'name': f"{spec.name}-service-entry",
                'namespace': os.getenv('KUBERNETES_NAMESPACE', 'default')
            },
            'spec': {
                'hosts': [spec.name],
                'ports': [{'number': port, 'name': 'http', 'protocol': 'HTTP'} 
                         for port in spec.ports],
                'location': 'MESH_EXTERNAL',
                'resolution': 'DNS'
            }
        }
        
        # Apply configuration using kubectl
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(istio_config, f)
            f.flush()
            
            result = subprocess.run(
                ['kubectl', 'apply', '-f', f.name],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                logging.info(f"Successfully registered {spec.name} with Istio")
            else:
                logging.error(f"Failed to register with Istio: {result.stderr}")
        
        os.unlink(f.name)
    
    async def _register_with_linkerd(self, spec: DeploymentSpec):
        """Register service with Linkerd service mesh."""
        # Linkerd registration typically happens via annotations
        # This would patch the deployment with Linkerd annotations
        logging.info(f"Linkerd registration for {spec.name} would add linkerd.io/inject annotation")
    
    async def _register_with_consul_connect(self, spec: DeploymentSpec):
        """Register service with Consul Connect service mesh."""
        # This would register the service in Consul's service registry
        logging.info(f"Consul Connect registration for {spec.name} would register in Consul catalog")

    async def _configure_gateway_routes(self, spec: DeploymentSpec):
        """Configure API gateway routes for the service."""
        try:
            # Get gateway provider from environment or config
            gateway_provider = os.getenv('API_GATEWAY_PROVIDER', 'nginx').lower()
            
            if gateway_provider == 'nginx':
                await self._configure_nginx_routes(spec)
            elif gateway_provider == 'traefik':
                await self._configure_traefik_routes(spec)
            elif gateway_provider == 'istio-gateway':
                await self._configure_istio_gateway_routes(spec)
            elif gateway_provider == 'envoy':
                await self._configure_envoy_routes(spec)
            else:
                logging.warning(f"Unknown API gateway provider: {gateway_provider}")
                
        except Exception as e:
            logging.error(f"Gateway route configuration failed for {spec.name}: {e}")
            # Don't fail deployment, but log the issue
    
    async def _configure_nginx_routes(self, spec: DeploymentSpec):
        """Configure NGINX Ingress routes."""
        import subprocess
        
        # Create NGINX Ingress configuration
        ingress_config = {
            'apiVersion': 'networking.k8s.io/v1',
            'kind': 'Ingress',
            'metadata': {
                'name': f"{spec.name}-ingress",
                'namespace': os.getenv('KUBERNETES_NAMESPACE', 'default'),
                'annotations': {
                    'nginx.ingress.kubernetes.io/rewrite-target': '/',
                    'nginx.ingress.kubernetes.io/ssl-redirect': 'true'
                }
            },
            'spec': {
                'rules': [{
                    'host': f"{spec.name}.{os.getenv('DOMAIN_SUFFIX', 'local')}",
                    'http': {
                        'paths': [{
                            'path': '/',
                            'pathType': 'Prefix',
                            'backend': {
                                'service': {
                                    'name': spec.name,
                                    'port': {'number': spec.ports[0] if spec.ports else 8000}
                                }
                            }
                        }]
                    }
                }]
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(ingress_config, f)
            f.flush()
            
            result = subprocess.run(
                ['kubectl', 'apply', '-f', f.name],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                logging.info(f"Successfully configured NGINX routes for {spec.name}")
            else:
                logging.error(f"Failed to configure NGINX routes: {result.stderr}")
        
        os.unlink(f.name)
    
    async def _configure_traefik_routes(self, spec: DeploymentSpec):
        """Configure Traefik IngressRoute."""
        import subprocess
        
        # Create Traefik IngressRoute
        traefik_config = {
            'apiVersion': 'traefik.containo.us/v1alpha1',
            'kind': 'IngressRoute',
            'metadata': {
                'name': f"{spec.name}-route",
                'namespace': os.getenv('KUBERNETES_NAMESPACE', 'default')
            },
            'spec': {
                'entryPoints': ['web', 'websecure'],
                'routes': [{
                    'match': f"Host(`{spec.name}.{os.getenv('DOMAIN_SUFFIX', 'local')}`)",
                    'kind': 'Rule',
                    'services': [{
                        'name': spec.name,
                        'port': spec.ports[0] if spec.ports else 8000
                    }]
                }]
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(traefik_config, f)
            f.flush()
            
            result = subprocess.run(
                ['kubectl', 'apply', '-f', f.name],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                logging.info(f"Successfully configured Traefik routes for {spec.name}")
            else:
                logging.error(f"Failed to configure Traefik routes: {result.stderr}")
        
        os.unlink(f.name)
    
    async def _configure_istio_gateway_routes(self, spec: DeploymentSpec):
        """Configure Istio Gateway and VirtualService."""
        # This would create Istio Gateway and VirtualService resources
        logging.info(f"Istio Gateway configuration for {spec.name} would create Gateway and VirtualService resources")
    
    async def _configure_envoy_routes(self, spec: DeploymentSpec):
        """Configure Envoy Proxy routes."""
        # This would configure Envoy proxy with route configuration
        logging.info(f"Envoy route configuration for {spec.name} would update Envoy config")


class DeploymentAutomationFactory:
    """Factory for creating deployment automation instances."""

    @staticmethod
    def create_docker_deployment(monitoring: MonitoringStack) -> DeploymentAutomation:
        """Create Docker-based deployment automation."""
        orchestrator = DockerOrchestrator(monitoring)
        return DeploymentAutomation(orchestrator, monitoring)

    @staticmethod
    def create_kubernetes_deployment(
        monitoring: MonitoringStack, namespace: str = "default"
    ) -> DeploymentAutomation:
        """Create Kubernetes-based deployment automation."""
        orchestrator = KubernetesOrchestrator(monitoring, namespace)
        return DeploymentAutomation(orchestrator, monitoring)

    @staticmethod
    def create_integrated_deployment(
        monitoring: MonitoringStack,
        service_mesh: ServiceMesh,
        api_gateway: UnifiedAPIGateway,
        orchestrator_type: str = "kubernetes",
        namespace: str = "default",
    ) -> DeploymentAutomation:
        """Create fully integrated deployment automation."""
        if orchestrator_type == "kubernetes":
            orchestrator = KubernetesOrchestrator(monitoring, namespace)
        else:
            orchestrator = DockerOrchestrator(monitoring)

        return DeploymentAutomation(orchestrator, monitoring, service_mesh, api_gateway)


# Convenience function for easy setup
async def setup_deployment_automation(
    monitoring: MonitoringStack,
    orchestrator_type: str = "kubernetes",
    namespace: str = "default",
) -> DeploymentAutomation:
    """Setup deployment automation with monitoring integration."""
    factory = DeploymentAutomationFactory()

    if orchestrator_type == "kubernetes":
        return factory.create_kubernetes_deployment(monitoring, namespace)
    else:
        return factory.create_docker_deployment(monitoring)
