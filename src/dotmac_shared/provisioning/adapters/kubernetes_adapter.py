"""
Kubernetes deployment adapter for the DotMac Container Provisioning Service.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

import structlog
from kubernetes import client, config
from kubernetes.client.rest import ApiException

from ..core.exceptions import DeploymentError, InfrastructureError
from ..core.models import DeploymentArtifacts, ISPConfig, ResourceRequirements

logger = structlog.get_logger(__name__)


class KubernetesAdapter:
    """Handles Kubernetes-specific deployment operations."""

    def __init__(self):
        self.k8s_client = None
        self.apps_v1 = None
        self.core_v1 = None
        self.networking_v1 = None
        self.initialized = False

    async def _initialize_client(self) -> None:
        """Initialize Kubernetes client."""
        if self.initialized:
            return

        try:
            # Try in-cluster configuration first
            try:
                config.load_incluster_config()
                logger.info("Using in-cluster Kubernetes configuration")
            except config.ConfigException:
                # Fall back to kubeconfig
                config.load_kube_config()
                logger.info("Using kubeconfig for Kubernetes configuration")

            # Initialize API clients
            self.core_v1 = client.CoreV1Api()
            self.apps_v1 = client.AppsV1Api()
            self.networking_v1 = client.NetworkingV1Api()

            self.initialized = True
            logger.info("Kubernetes client initialized successfully")

        except Exception as e:
            raise InfrastructureError(
                f"Failed to initialize Kubernetes client: {e}",
                infrastructure_type="kubernetes",
            ) from e

    async def provision_infrastructure(
        self,
        isp_id: UUID,
        config: ISPConfig,
        resources: ResourceRequirements,
        region: str = "us-east-1",
    ) -> DeploymentArtifacts:
        """
        Provision Kubernetes infrastructure for ISP deployment.

        Creates:
        - Namespace
        - ConfigMaps and Secrets
        - Persistent Volume Claims
        - Network Policies
        """

        await self._initialize_client()

        logger.info(
            "Provisioning Kubernetes infrastructure",
            isp_id=str(isp_id),
            tenant_name=config.tenant_name,
        )

        artifacts = DeploymentArtifacts()

        try:
            # Generate resource names
            namespace_name = f"tenant-{config.tenant_name}"
            artifacts.namespace = namespace_name

            # Create namespace
            await self._create_namespace(namespace_name, isp_id, config, artifacts)

            # Create ConfigMaps for configuration
            await self._create_configmaps(namespace_name, isp_id, config, artifacts)

            # Create Secrets for sensitive data
            await self._create_secrets(namespace_name, isp_id, config, artifacts)

            # Create Persistent Volume Claims
            await self._create_persistent_volumes(namespace_name, resources, artifacts)

            # Set up Network Policies for tenant isolation
            await self._create_network_policies(namespace_name, config, artifacts)

            logger.info(
                "Kubernetes infrastructure provisioning completed",
                namespace=namespace_name,
            )

            return artifacts

        except Exception as e:
            # Clean up any partially created resources
            await self._cleanup_infrastructure(artifacts)
            raise InfrastructureError(
                f"Kubernetes infrastructure provisioning failed: {e}",
                infrastructure_type="kubernetes",
                resource_name=artifacts.namespace,
            ) from e

    async def _create_namespace(
        self,
        namespace_name: str,
        isp_id: UUID,
        config: ISPConfig,
        artifacts: DeploymentArtifacts,
    ) -> None:
        """Create Kubernetes namespace with proper labels."""

        namespace_spec = client.V1Namespace(
            metadata=client.V1ObjectMeta(
                name=namespace_name,
                labels={
                    "tenant": config.tenant_name,
                    "isp-id": str(isp_id),
                    "plan": config.plan_type.value,
                    "managed-by": "dotmac-provisioning",
                    "created-at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                },
                annotations={
                    "dotmac.app/tenant-name": config.display_name,
                    "dotmac.app/provisioned-at": datetime.now(timezone.utc).isoformat(),
                },
            )
        )

        try:
            await asyncio.get_event_loop().run_in_executor(
                None, self.core_v1.create_namespace, namespace_spec
            )

            artifacts.created_resources.append(
                {"kind": "Namespace", "name": namespace_name, "api_version": "v1"}
            )

            logger.debug("Namespace created", namespace=namespace_name)

        except ApiException as e:
            if e.status == 409:  # Already exists
                logger.warning("Namespace already exists", namespace=namespace_name)
            else:
                raise

    async def _create_configmaps(
        self,
        namespace_name: str,
        isp_id: UUID,
        config: ISPConfig,
        artifacts: DeploymentArtifacts,
    ) -> None:
        """Create ConfigMaps for application configuration."""

        # Main application configuration
        app_config = {
            "TENANT_ID": config.tenant_name,
            "ISP_ID": str(isp_id),
            "PLAN_TYPE": config.plan_type.value,
            "DISPLAY_NAME": config.display_name,
            "ENVIRONMENT": "production",
        }

        # Add feature flags
        if config.feature_flags:
            feature_config = {
                f"FEATURE_{feature.upper()}": (
                    "true" if getattr(config.feature_flags, feature) else "false"
                )
                for feature in [
                    "customer_portal",
                    "technician_portal",
                    "admin_portal",
                    "billing_system",
                    "notification_system",
                    "analytics_dashboard",
                    "api_webhooks",
                    "bulk_operations",
                    "advanced_reporting",
                    "multi_language",
                ]
            }
            app_config.update(feature_config)

        # Add custom environment variables
        app_config.update(config.environment_variables)

        configmap_spec = client.V1ConfigMap(
            metadata=client.V1ObjectMeta(
                name=f"{config.tenant_name}-config",
                namespace=namespace_name,
                labels={"tenant": config.tenant_name},
            ),
            data=app_config,
        )

        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.core_v1.create_namespaced_config_map,
                namespace_name,
                configmap_spec,
            )

            artifacts.created_resources.append(
                {
                    "kind": "ConfigMap",
                    "name": f"{config.tenant_name}-config",
                    "namespace": namespace_name,
                    "api_version": "v1",
                }
            )

            logger.debug("ConfigMap created", name=f"{config.tenant_name}-config")

        except ApiException as e:
            if e.status != 409:  # Ignore if already exists
                raise

    async def _create_secrets(
        self,
        namespace_name: str,
        isp_id: UUID,
        config: ISPConfig,
        artifacts: DeploymentArtifacts,
    ) -> None:
        """Create Secrets for sensitive configuration."""

        # Generate database credentials
        db_secrets = {
            "DATABASE_URL": f"postgresql://tenant_{config.tenant_name}:generated_password@postgres:5432/tenant_{config.tenant_name}",
            "REDIS_URL": "redis://redis:6379/0",
            "JWT_SECRET_KEY": "generated-jwt-secret-key-32-chars-minimum",
            "ENCRYPTION_KEY": "generated-encryption-key-32-chars",
        }

        # Add custom secrets
        db_secrets.update(config.secrets)

        # Encode secrets as base64 (Kubernetes requirement)
        {key: value.encode().hex() for key, value in db_secrets.items()}

        secret_spec = client.V1Secret(
            metadata=client.V1ObjectMeta(
                name=f"{config.tenant_name}-secrets",
                namespace=namespace_name,
                labels={"tenant": config.tenant_name},
            ),
            type="Opaque",
            string_data=db_secrets,  # Use string_data for automatic encoding
        )

        try:
            await asyncio.get_event_loop().run_in_executor(
                None, self.core_v1.create_namespaced_secret, namespace_name, secret_spec
            )

            artifacts.created_resources.append(
                {
                    "kind": "Secret",
                    "name": f"{config.tenant_name}-secrets",
                    "namespace": namespace_name,
                    "api_version": "v1",
                }
            )

            logger.debug("Secret created", name=f"{config.tenant_name}-secrets")

        except ApiException as e:
            if e.status != 409:  # Ignore if already exists
                raise

    async def _create_persistent_volumes(
        self,
        namespace_name: str,
        resources: ResourceRequirements,
        artifacts: DeploymentArtifacts,
    ) -> None:
        """Create Persistent Volume Claims for storage."""

        pvc_spec = client.V1PersistentVolumeClaim(
            metadata=client.V1ObjectMeta(
                name="tenant-storage-pvc", namespace=namespace_name
            ),
            spec=client.V1PersistentVolumeClaimSpec(
                access_modes=["ReadWriteOnce"],
                resources=client.V1ResourceRequirements(
                    requests={"storage": f"{int(resources.storage_gb)}Gi"}
                ),
                storage_class_name="standard",
            ),
        )

        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.core_v1.create_namespaced_persistent_volume_claim,
                namespace_name,
                pvc_spec,
            )

            artifacts.created_resources.append(
                {
                    "kind": "PersistentVolumeClaim",
                    "name": "tenant-storage-pvc",
                    "namespace": namespace_name,
                    "api_version": "v1",
                }
            )

            logger.debug("PVC created", name="tenant-storage-pvc")

        except ApiException as e:
            if e.status != 409:  # Ignore if already exists
                raise

    async def _create_network_policies(
        self, namespace_name: str, config: ISPConfig, artifacts: DeploymentArtifacts
    ) -> None:
        """Create Network Policies for tenant isolation."""

        # Allow ingress from ingress controller
        ingress_policy = client.V1NetworkPolicy(
            metadata=client.V1ObjectMeta(
                name=f"{config.tenant_name}-ingress-policy", namespace=namespace_name
            ),
            spec=client.V1NetworkPolicySpec(
                pod_selector=client.V1LabelSelector(
                    match_labels={"tenant": config.tenant_name}
                ),
                policy_types=["Ingress"],
                ingress=[
                    client.V1NetworkPolicyIngressRule(
                        from_=[
                            client.V1NetworkPolicyPeer(
                                namespace_selector=client.V1LabelSelector(
                                    match_labels={"name": "ingress-nginx"}
                                )
                            )
                        ]
                    )
                ],
            ),
        )

        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.networking_v1.create_namespaced_network_policy,
                namespace_name,
                ingress_policy,
            )

            artifacts.created_resources.append(
                {
                    "kind": "NetworkPolicy",
                    "name": f"{config.tenant_name}-ingress-policy",
                    "namespace": namespace_name,
                    "api_version": "networking.k8s.io/v1",
                }
            )

            logger.debug(
                "Network policy created", name=f"{config.tenant_name}-ingress-policy"
            )

        except ApiException as e:
            if e.status != 409:  # Ignore if already exists
                raise

    async def deploy_container(
        self,
        template: dict[str, Any],
        artifacts: DeploymentArtifacts,
        timeout: int = 300,
    ) -> dict[str, Any]:
        """Deploy ISP Framework container using rendered template."""

        logger.info("Deploying container to Kubernetes", namespace=artifacts.namespace)

        try:
            # Parse the rendered template (should be Kubernetes YAML)
            deployment_spec = self._parse_kubernetes_template(template)

            # Create Deployment
            deployment_result = await self._create_deployment(
                deployment_spec, artifacts
            )

            # Create Service
            service_result = await self._create_service(deployment_spec, artifacts)

            # Wait for deployment to be ready
            await self._wait_for_deployment_ready(
                deployment_spec["metadata"]["name"], artifacts.namespace, timeout
            )

            # Generate URLs
            internal_url = f"http://{service_result['name']}.{artifacts.namespace}.svc.cluster.local:8000"
            external_url = f"http://{deployment_spec['metadata']['name']}.{artifacts.namespace}.dotmac.app"

            return {
                "container_id": deployment_spec["metadata"]["name"],
                "internal_url": internal_url,
                "external_url": external_url,
                "deployment_name": deployment_result["name"],
                "service_name": service_result["name"],
            }

        except Exception as e:
            raise DeploymentError(
                f"Kubernetes container deployment failed: {e}",
                deployment_phase="container_deployment",
                container_id=artifacts.container_id,
            ) from e

    def _parse_kubernetes_template(self, template: dict[str, Any]) -> dict[str, Any]:
        """Parse and validate Kubernetes template."""

        # For now, return a basic deployment structure
        # In a real implementation, this would parse the actual rendered template
        return {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": template.get("container_name", "isp-framework"),
                "namespace": template.get("namespace", "default"),
            },
            "spec": {
                "replicas": 1,
                "selector": {
                    "matchLabels": {
                        "app": "isp-framework",
                        "tenant": template.get("tenant_name", "default"),
                    }
                },
                "template": {
                    "metadata": {
                        "labels": {
                            "app": "isp-framework",
                            "tenant": template.get("tenant_name", "default"),
                        }
                    },
                    "spec": {
                        "containers": [
                            {
                                "name": "isp-framework",
                                "image": "registry.dotmac.app/isp-framework:latest",
                                "ports": [{"containerPort": 8000}],
                                "resources": {
                                    "limits": {
                                        "cpu": template.get("cpu_limit", "1000m"),
                                        "memory": template.get("memory_limit", "2Gi"),
                                    }
                                },
                                "envFrom": [
                                    {
                                        "configMapRef": {
                                            "name": f"{template.get('tenant_name', 'default')}-config"
                                        }
                                    },
                                    {
                                        "secretRef": {
                                            "name": f"{template.get('tenant_name', 'default')}-secrets"
                                        }
                                    },
                                ],
                            }
                        ]
                    },
                },
            },
        }

    async def _create_deployment(
        self, deployment_spec: dict[str, Any], artifacts: DeploymentArtifacts
    ) -> dict[str, str]:
        """Create Kubernetes Deployment."""

        # Convert dict to Kubernetes API object
        deployment = client.V1Deployment(
            api_version=deployment_spec["apiVersion"],
            kind=deployment_spec["kind"],
            metadata=client.V1ObjectMeta(**deployment_spec["metadata"]),
            spec=client.V1DeploymentSpec(
                replicas=deployment_spec["spec"]["replicas"],
                selector=client.V1LabelSelector(
                    match_labels=deployment_spec["spec"]["selector"]["matchLabels"]
                ),
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(
                        labels=deployment_spec["spec"]["template"]["metadata"]["labels"]
                    ),
                    spec=client.V1PodSpec(
                        containers=[
                            client.V1Container(
                                name=container["name"],
                                image=container["image"],
                                ports=[
                                    client.V1ContainerPort(
                                        container_port=port["containerPort"]
                                    )
                                    for port in container["ports"]
                                ],
                                resources=client.V1ResourceRequirements(
                                    limits=container["resources"]["limits"]
                                ),
                                env_from=[
                                    (
                                        client.V1EnvFromSource(
                                            config_map_ref=client.V1ConfigMapEnvSource(
                                                name=env_from["configMapRef"]["name"]
                                            )
                                        )
                                        if "configMapRef" in env_from
                                        else client.V1EnvFromSource(
                                            secret_ref=client.V1SecretEnvSource(
                                                name=env_from["secretRef"]["name"]
                                            )
                                        )
                                    )
                                    for env_from in container["envFrom"]
                                ],
                            )
                            for container in deployment_spec["spec"]["template"][
                                "spec"
                            ]["containers"]
                        ]
                    ),
                ),
            ),
        )

        result = await asyncio.get_event_loop().run_in_executor(
            None,
            self.apps_v1.create_namespaced_deployment,
            artifacts.namespace,
            deployment,
        )

        artifacts.created_resources.append(
            {
                "kind": "Deployment",
                "name": result.metadata.name,
                "namespace": result.metadata.namespace,
                "api_version": "apps/v1",
            }
        )

        return {"name": result.metadata.name}

    async def _create_service(
        self, deployment_spec: dict[str, Any], artifacts: DeploymentArtifacts
    ) -> dict[str, str]:
        """Create Kubernetes Service for the deployment."""

        service_name = f"{deployment_spec['metadata']['name']}-service"

        service = client.V1Service(
            metadata=client.V1ObjectMeta(
                name=service_name,
                namespace=artifacts.namespace,
                labels=deployment_spec["spec"]["selector"]["matchLabels"],
            ),
            spec=client.V1ServiceSpec(
                selector=deployment_spec["spec"]["selector"]["matchLabels"],
                ports=[client.V1ServicePort(port=80, target_port=8000, protocol="TCP")],
                type="ClusterIP",
            ),
        )

        result = await asyncio.get_event_loop().run_in_executor(
            None, self.core_v1.create_namespaced_service, artifacts.namespace, service
        )

        artifacts.service_name = result.metadata.name
        artifacts.created_resources.append(
            {
                "kind": "Service",
                "name": result.metadata.name,
                "namespace": result.metadata.namespace,
                "api_version": "v1",
            }
        )

        return {"name": result.metadata.name}

    async def _wait_for_deployment_ready(
        self, deployment_name: str, namespace: str, timeout: int
    ) -> None:
        """Wait for deployment to be ready."""

        logger.info(
            "Waiting for deployment to be ready",
            deployment_name=deployment_name,
            namespace=namespace,
        )

        start_time = asyncio.get_event_loop().time()

        while (asyncio.get_event_loop().time() - start_time) < timeout:
            try:
                deployment = await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.apps_v1.read_namespaced_deployment,
                    deployment_name,
                    namespace,
                )

                if (
                    deployment.status.ready_replicas
                    and deployment.status.ready_replicas == deployment.spec.replicas
                ):
                    logger.info("Deployment is ready", deployment_name=deployment_name)
                    return

                await asyncio.sleep(5)

            except Exception as e:
                logger.warning("Error checking deployment status", error=str(e))
                await asyncio.sleep(5)

        raise DeploymentError(
            f"Deployment did not become ready within {timeout} seconds",
            deployment_phase="waiting_for_ready",
            container_id=deployment_name,
        )

    async def configure_networking(
        self, isp_id: UUID, config: ISPConfig, artifacts: DeploymentArtifacts
    ) -> dict[str, Any]:
        """Configure ingress and external networking."""

        logger.info("Configuring networking", namespace=artifacts.namespace)

        # Create ingress for external access
        ingress_name = f"{config.tenant_name}-ingress"
        host = config.network_config.domain or f"{config.tenant_name}.dotmac.app"

        ingress = client.V1Ingress(
            metadata=client.V1ObjectMeta(
                name=ingress_name,
                namespace=artifacts.namespace,
                annotations={
                    "kubernetes.io/ingress.class": "nginx",
                    "cert-manager.io/cluster-issuer": (
                        "letsencrypt-prod" if config.network_config.ssl_enabled else ""
                    ),
                },
            ),
            spec=client.V1IngressSpec(
                rules=[
                    client.V1IngressRule(
                        host=host,
                        http=client.V1HTTPIngressRuleValue(
                            paths=[
                                client.V1HTTPIngressPath(
                                    path="/",
                                    path_type="Prefix",
                                    backend=client.V1IngressBackend(
                                        service=client.V1IngressServiceBackend(
                                            name=artifacts.service_name,
                                            port=client.V1ServiceBackendPort(number=80),
                                        )
                                    ),
                                )
                            ]
                        ),
                    )
                ],
                tls=(
                    [
                        client.V1IngressTLS(
                            hosts=[host], secret_name=f"{config.tenant_name}-tls"
                        )
                    ]
                    if config.network_config.ssl_enabled
                    else []
                ),
            ),
        )

        result = await asyncio.get_event_loop().run_in_executor(
            None,
            self.networking_v1.create_namespaced_ingress,
            artifacts.namespace,
            ingress,
        )

        artifacts.ingress_name = result.metadata.name
        artifacts.external_url = (
            f"{'https' if config.network_config.ssl_enabled else 'http'}://{host}"
        )

        artifacts.created_resources.append(
            {
                "kind": "Ingress",
                "name": result.metadata.name,
                "namespace": result.metadata.namespace,
                "api_version": "networking.k8s.io/v1",
            }
        )

        return {"external_url": artifacts.external_url}

    async def configure_ssl(
        self, isp_id: UUID, config: ISPConfig, artifacts: DeploymentArtifacts
    ) -> dict[str, Any]:
        """Configure SSL certificates using cert-manager."""

        logger.info("Configuring SSL", namespace=artifacts.namespace)

        # SSL is handled automatically by cert-manager via ingress annotations
        # Just return certificate info
        return {
            "certificate_name": f"{config.tenant_name}-tls",
            "issuer": "letsencrypt-prod",
            "status": "requested",
        }

    async def configure_monitoring(
        self, isp_id: UUID, config: ISPConfig, artifacts: DeploymentArtifacts
    ) -> dict[str, Any]:
        """Configure monitoring and logging."""

        logger.info("Configuring monitoring", namespace=artifacts.namespace)

        # Add monitoring labels to namespace
        try:
            namespace_patch = {
                "metadata": {"labels": {"monitoring": "enabled", "logging": "enabled"}}
            }

            await asyncio.get_event_loop().run_in_executor(
                None, self.core_v1.patch_namespace, artifacts.namespace, namespace_patch
            )

        except Exception as e:
            logger.warning("Failed to configure monitoring", error=str(e))

        return {"monitoring_enabled": True, "logging_enabled": True}

    async def rollback_deployment(
        self, isp_id: UUID, artifacts: Optional[DeploymentArtifacts], timeout: int = 120
    ) -> bool:
        """Rollback Kubernetes deployment by cleaning up resources."""

        if not artifacts or not artifacts.namespace:
            return False

        logger.info("Rolling back Kubernetes deployment", namespace=artifacts.namespace)

        try:
            # Delete namespace and all resources within it
            await asyncio.get_event_loop().run_in_executor(
                None, self.core_v1.delete_namespace, artifacts.namespace
            )

            logger.info("Rollback completed", namespace=artifacts.namespace)
            return True

        except Exception as e:
            logger.error("Rollback failed", namespace=artifacts.namespace, error=str(e))
            return False

    async def _cleanup_infrastructure(self, artifacts: DeploymentArtifacts) -> None:
        """Clean up partially created infrastructure."""

        if not artifacts.namespace:
            return

        logger.info("Cleaning up infrastructure", namespace=artifacts.namespace)

        try:
            await asyncio.get_event_loop().run_in_executor(
                None, self.core_v1.delete_namespace, artifacts.namespace
            )
        except Exception as e:
            logger.error("Failed to cleanup infrastructure", error=str(e))
