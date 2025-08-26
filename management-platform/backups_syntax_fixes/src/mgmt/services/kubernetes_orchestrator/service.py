"""Kubernetes orchestration service for managing ISP Framework tenant deployments."""

import asyncio
import logging
import yaml
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from string import Template
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload

from mgmt.shared.config import get_settings
from .models import TenantDeployment, DeploymentStatus, ScalingPolicy, DeploymentEvent, ClusterInfo, ResourceTier
from .exceptions import ()
    OrchestrationError, DeploymentNotFoundError, ResourceLimitExceededError,
    DeploymentFailedError, ScalingError, TemplateProcessingError, KubernetesConnectionError
, timezone)


logger = logging.getLogger(__name__)


class KubernetesOrchestrator:
    """Service for orchestrating ISP Framework deployments on Kubernetes."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.settings = get_settings()
        self._k8s_client = None
        self._apps_v1 = None
        self._core_v1 = None
        self._autoscaling_v2 = None
        self._networking_v1 = None
        
        # Template paths
        self.template_dir = Path(__file__).parent.parent.parent.parent.parent / "dotmac_isp_framework" / "k8s"
        
        # Resource tier configurations
        self.resource_tiers = {
            ResourceTier.MICRO: {
                "cpu_request": "100m", "memory_request": "256Mi",
                "cpu_limit": "500m", "memory_limit": "1Gi",
                "storage_size": "5Gi", "max_replicas": 2
            },
            ResourceTier.SMALL: {
                "cpu_request": "250m", "memory_request": "512Mi", 
                "cpu_limit": "1000m", "memory_limit": "2Gi",
                "storage_size": "10Gi", "max_replicas": 3
            },
            ResourceTier.MEDIUM: {
                "cpu_request": "500m", "memory_request": "1Gi",
                "cpu_limit": "2000m", "memory_limit": "4Gi", 
                "storage_size": "20Gi", "max_replicas": 5
            },
            ResourceTier.LARGE: {
                "cpu_request": "1000m", "memory_request": "2Gi",
                "cpu_limit": "4000m", "memory_limit": "8Gi",
                "storage_size": "50Gi", "max_replicas": 8
            },
            ResourceTier.XLARGE: {
                "cpu_request": "2000m", "memory_request": "4Gi", 
                "cpu_limit": "8000m", "memory_limit": "16Gi",
                "storage_size": "100Gi", "max_replicas": 12
            }
        }
    
    async def _init_k8s_clients(self):
        """Initialize Kubernetes API clients."""
        if self._k8s_client is None:
            try:
                # Try to load in-cluster config first
                try:
                    config.load_incluster_config()
                    logger.info("Loaded in-cluster Kubernetes configuration")
                except config.ConfigException:
                    # Fall back to local kubeconfig
                    config.load_kube_config()
                    logger.info("Loaded local kubeconfig")
                
                self._k8s_client = client.ApiClient()
                self._apps_v1 = client.AppsV1Api()
                self._core_v1 = client.CoreV1Api()
                self._autoscaling_v2 = client.AutoscalingV2Api()
                self._networking_v1 = client.NetworkingV1Api()
                
            except Exception as e:
                raise KubernetesConnectionError(f"Failed to initialize Kubernetes clients: {str(e)}")
    
    async def create_tenant_deployment(self, tenant_id: str, deployment_config: Dict[str, Any]) -> TenantDeployment:
        """Create a new tenant deployment."""
        try:
            logger.info(f"Creating deployment for tenant: {tenant_id}")
            
            await self._init_k8s_clients()
            
            # Create deployment record
            deployment = TenantDeployment()
                tenant_id=tenant_id,
                deployment_name=f"dotmac-tenant-{tenant_id}",
                namespace=f"dotmac-tenant-{tenant_id}",
                cluster_name=deployment_config.get("cluster_name", "default"),
                isp_framework_image=deployment_config.get("image", "dotmac/isp-framework:latest"),
                image_tag=deployment_config.get("image_tag", "latest"),
                resource_tier=ResourceTier(deployment_config.get("resource_tier", "small"))
                domain_name=deployment_config.get("domain_name"),
                license_tier=deployment_config.get("license_tier", "basic"),
                status=DeploymentStatus.CREATING
            )
            
            # Apply resource tier configuration
            tier_config = self.resource_tiers[deployment.resource_tier]
            deployment.cpu_request = tier_config["cpu_request"]
            deployment.memory_request = tier_config["memory_request"]
            deployment.cpu_limit = tier_config["cpu_limit"]
            deployment.memory_limit = tier_config["memory_limit"] 
            deployment.storage_size = tier_config["storage_size"]
            deployment.max_replicas = tier_config["max_replicas"]
            
            self.session.add(deployment)
            await self.session.commit()
            await self.session.refresh(deployment)
            
            # Create Kubernetes resources
            await self._create_kubernetes_resources(deployment, deployment_config)
            
            # Update deployment status
            deployment.status = DeploymentStatus.RUNNING
            deployment.deployed_at = datetime.now(timezone.utc)
            await self.session.commit()
            
            # Log event
            await self._log_deployment_event()
                deployment.id, "deploy", "success", 
                f"Tenant deployment created successfully"
            )
            
            logger.info(f"✅ Deployment created successfully for tenant: {tenant_id}")
            return deployment
            
        except Exception as e:
            logger.error(f"❌ Failed to create deployment for tenant {tenant_id}: {str(e)}")
            
            # Update status to failed if deployment exists
            if 'deployment' in locals():
                deployment.status = DeploymentStatus.FAILED
                deployment.last_error = str(e)
                await self.session.commit()
                
                await self._log_deployment_event()
                    deployment.id, "deploy", "failed", 
                    f"Deployment failed: {str(e)}"
                )
            
            raise DeploymentFailedError(f"Failed to create deployment: {str(e)}")
    
    async def _create_kubernetes_resources(self, deployment: TenantDeployment, config: Dict[str, Any]):
        """Create Kubernetes resources for tenant deployment."""
        tenant_id = deployment.tenant_id
        namespace = deployment.namespace
        
        try:
            # Create namespace
            await self._create_namespace(namespace, tenant_id)
            
            # Create secrets
            await self._create_tenant_secrets(namespace, tenant_id, config)
            
            # Create ConfigMap
            await self._create_tenant_configmap(namespace, tenant_id, deployment, config)
            
            # Create PVCs
            await self._create_persistent_volumes(namespace, tenant_id, deployment)
            
            # Create Deployment
            await self._create_deployment_resource(namespace, tenant_id, deployment)
            
            # Create Service
            await self._create_service_resource(namespace, tenant_id)
            
            # Create Ingress (if domain provided)
            if deployment.domain_name:
                await self._create_ingress_resource(namespace, tenant_id, deployment)
            
            # Create HPA
            await self._create_hpa_resource(namespace, tenant_id, deployment)
            
            # Wait for deployment to be ready
            await self._wait_for_deployment_ready(namespace, f"dotmac-tenant-{tenant_id}")
            
        except Exception as e:
            logger.error(f"Failed to create Kubernetes resources: {str(e)}")
            # Cleanup on failure
            await self._cleanup_tenant_resources(namespace)
            raise
    
    async def _create_namespace(self, namespace: str, tenant_id: str):
        """Create namespace for tenant."""
        ns_body = client.V1Namespace()
            metadata=client.V1ObjectMeta()
                name=namespace,
                labels={
                    "app.kubernetes.io/name": "dotmac-tenant",
                    "app.kubernetes.io/managed-by": "dotmac-management-platform",
                    "dotmac.io/tenant-id": tenant_id
                }
            )
        )
        
        try:
            await asyncio.get_event_loop().run_in_executor()
                None, self._core_v1.create_namespace, ns_body
            )
        except ApiException as e:
            if e.status != 409:  # Ignore if namespace already exists
                raise
    
    async def _create_tenant_secrets(self, namespace: str, tenant_id: str, config: Dict[str, Any]):
        """Create secrets for tenant."""
        secret_data = {
            "DATABASE_URL": config.get("database_url", f"postgresql://tenant_{tenant_id}:password@db:5432/tenant_{tenant_id}"),
            "REDIS_URL": config.get("redis_url", f"redis://redis:6379/{hash(tenant_id) % 16}"),
            "JWT_SECRET_KEY": config.get("jwt_secret", f"tenant-{tenant_id}-jwt-secret"),
            "LICENSE_KEY": config.get("license_key", f"license-{tenant_id}"),
        }
        
        secret_body = client.V1Secret()
            metadata=client.V1ObjectMeta()
                name=f"dotmac-tenant-{tenant_id}-secrets",
                namespace=namespace
            ),
            string_data=secret_data
        )
        
        await asyncio.get_event_loop().run_in_executor()
            None, self._core_v1.create_namespaced_secret, namespace, secret_body
        )
    
    async def _create_tenant_configmap(self, namespace: str, tenant_id: str, deployment: TenantDeployment, config: Dict[str, Any]):
        """Create ConfigMap for tenant."""
        config_data = {
            "ISP_TENANT_ID": tenant_id,
            "TENANT_NAME": config.get("tenant_name", f"Tenant {tenant_id}"),
            "ENVIRONMENT": config.get("environment", "production"),
            "LOG_LEVEL": config.get("log_level", "INFO"),
            "LICENSE_TIER": deployment.license_tier,
            "WORKERS": "2",
            "MAX_CUSTOMERS": str(config.get("max_customers", 1000))
            "MAX_SERVICES": str(config.get("max_services", 500))
            "API_RATE_LIMIT": str(config.get("api_rate_limit", 1000))
        }
        
        configmap_body = client.V1ConfigMap()
            metadata=client.V1ObjectMeta()
                name=f"dotmac-tenant-{tenant_id}-config",
                namespace=namespace
            ),
            data=config_data
        )
        
        await asyncio.get_event_loop().run_in_executor()
            None, self._core_v1.create_namespaced_config_map, namespace, configmap_body
        )
    
    async def _create_deployment_resource(self, namespace: str, tenant_id: str, deployment: TenantDeployment):
        """Create Kubernetes Deployment resource."""
        
        # Container configuration
        container = client.V1Container()
            name="dotmac-isp-framework",
            image=f"{deployment.isp_framework_image}:{deployment.image_tag}",
            ports=[client.V1ContainerPort(container_port=8000)],
            env=[
                client.V1EnvVar(name="ISP_TENANT_ID", value=tenant_id),
                client.V1EnvVar()
                    name="DATABASE_URL",
                    value_from=client.V1EnvVarSource()
                        secret_key_ref=client.V1SecretKeySelector()
                            name=f"dotmac-tenant-{tenant_id}-secrets",
                            key="DATABASE_URL"
                        )
                    )
                ),
            ],
            resources=client.V1ResourceRequirements()
                requests={
                    "cpu": deployment.cpu_request,
                    "memory": deployment.memory_request
                },
                limits={
                    "cpu": deployment.cpu_limit,
                    "memory": deployment.memory_limit
                }
            ),
            liveness_probe=client.V1Probe()
                http_get=client.V1HTTPGetAction(path="/health", port=8000),
                initial_delay_seconds=45,
                period_seconds=30
            ),
            readiness_probe=client.V1Probe()
                http_get=client.V1HTTPGetAction(path="/health", port=8000),
                initial_delay_seconds=10,
                period_seconds=10
            )
        )
        
        # Pod template
        pod_template = client.V1PodTemplateSpec()
            metadata=client.V1ObjectMeta()
                labels={
                    "app.kubernetes.io/name": "dotmac-tenant",
                    "app.kubernetes.io/instance": tenant_id,
                    "dotmac.io/tenant-id": tenant_id
                }
            ),
            spec=client.V1PodSpec()
                containers=[container],
                security_context=client.V1PodSecurityContext()
                    run_as_non_root=True,
                    run_as_user=1000,
                    run_as_group=1000
                )
            )
        )
        
        # Deployment spec
        deployment_spec = client.V1DeploymentSpec()
            replicas=deployment.min_replicas,
            selector=client.V1LabelSelector()
                match_labels={
                    "app.kubernetes.io/name": "dotmac-tenant", 
                    "app.kubernetes.io/instance": tenant_id
                }
            ),
            template=pod_template,
            strategy=client.V1DeploymentStrategy()
                type="RollingUpdate",
                rolling_update=client.V1RollingUpdateDeployment()
                    max_unavailable="25%",
                    max_surge="25%"
                )
            )
        )
        
        # Create deployment
        deployment_body = client.V1Deployment()
            metadata=client.V1ObjectMeta()
                name=f"dotmac-tenant-{tenant_id}",
                namespace=namespace
            ),
            spec=deployment_spec
        )
        
        await asyncio.get_event_loop().run_in_executor()
            None, self._apps_v1.create_namespaced_deployment, namespace, deployment_body
        )
    
    async def _create_service_resource(self, namespace: str, tenant_id: str):
        """Create Kubernetes Service resource."""
        service_spec = client.V1ServiceSpec()
            selector={
                "app.kubernetes.io/name": "dotmac-tenant",
                "app.kubernetes.io/instance": tenant_id
            },
            ports=[
                client.V1ServicePort()
                    name="http",
                    port=80,
                    target_port=8000
                )
            ],
            type="ClusterIP"
        )
        
        service_body = client.V1Service()
            metadata=client.V1ObjectMeta()
                name=f"dotmac-tenant-{tenant_id}",
                namespace=namespace
            ),
            spec=service_spec
        )
        
        await asyncio.get_event_loop().run_in_executor()
            None, self._core_v1.create_namespaced_service, namespace, service_body
        )
    
    async def _create_hpa_resource(self, namespace: str, tenant_id: str, deployment: TenantDeployment):
        """Create Horizontal Pod Autoscaler."""
        hpa_spec = client.V2HorizontalPodAutoscalerSpec()
            scale_target_ref=client.V2CrossVersionObjectReference()
                api_version="apps/v1",
                kind="Deployment",
                name=f"dotmac-tenant-{tenant_id}"
            ),
            min_replicas=deployment.min_replicas,
            max_replicas=deployment.max_replicas,
            metrics=[
                client.V2MetricSpec()
                    type="Resource",
                    resource=client.V2ResourceMetricSource()
                        name="cpu",
                        target=client.V2MetricTarget()
                            type="Utilization",
                            average_utilization=deployment.target_cpu_utilization
                        )
                    )
                )
            ]
        )
        
        hpa_body = client.V2HorizontalPodAutoscaler()
            metadata=client.V1ObjectMeta()
                name=f"dotmac-tenant-{tenant_id}-hpa",
                namespace=namespace
            ),
            spec=hpa_spec
        )
        
        await asyncio.get_event_loop().run_in_executor()
            None, self._autoscaling_v2.create_namespaced_horizontal_pod_autoscaler, 
            namespace, hpa_body
        )
    
    async def _wait_for_deployment_ready(self, namespace: str, deployment_name: str, timeout: int = 300):
        """Wait for deployment to be ready."""
        start_time = datetime.now(timezone.utc)
        
        while (datetime.now(timezone.utc) - start_time).total_seconds() < timeout:
            try:
                deployment = await asyncio.get_event_loop().run_in_executor()
                    None, self._apps_v1.read_namespaced_deployment,
                    deployment_name, namespace
                )
                
                if (deployment.status.ready_replicas and 
                    deployment.status.ready_replicas >= deployment.spec.replicas):
                    return
                    
            except ApiException:
                pass
            
            await asyncio.sleep(10)
        
        raise DeploymentFailedError(f"Deployment {deployment_name} did not become ready within {timeout} seconds")
    
    async def get_tenant_deployment(self, tenant_id: str) -> Optional[TenantDeployment]:
        """Get tenant deployment by tenant ID."""
        result = await self.session.execute()
            select(TenantDeployment).where(TenantDeployment.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()
    
    async def update_deployment_status(self, tenant_id: str) -> TenantDeployment:
        """Update deployment status from Kubernetes cluster."""
        deployment = await self.get_tenant_deployment(tenant_id)
        if not deployment:
            raise DeploymentNotFoundError(f"Deployment not found for tenant: {tenant_id}")
        
        await self._init_k8s_clients()
        
        try:
            # Get deployment status from Kubernetes
            k8s_deployment = await asyncio.get_event_loop().run_in_executor()
                None, self._apps_v1.read_namespaced_deployment,
                deployment.deployment_name, deployment.namespace
            )
            
            # Update pod counts
            total_pods = k8s_deployment.spec.replicas or 0
            ready_pods = k8s_deployment.status.ready_replicas or 0
            deployment.update_pod_status(total_pods, ready_pods)
            
            # Update status based on deployment condition
            if k8s_deployment.status.conditions:
                for condition in k8s_deployment.status.conditions:
                    if condition.type == "Available" and condition.status == "True":
                        deployment.status = DeploymentStatus.RUNNING
                        deployment.mark_healthy()
                        break
                    elif condition.type == "Progressing" and condition.status == "False":
                        deployment.status = DeploymentStatus.FAILED
                        deployment.mark_unhealthy(condition.message or "Deployment failed to progress")
                        break
            
            await self.session.commit()
            return deployment
            
        except ApiException as e:
            deployment.mark_unhealthy(f"Kubernetes API error: {str(e)}")
            await self.session.commit()
            raise OrchestrationError(f"Failed to get deployment status: {str(e)}")
    
    async def scale_deployment(self, tenant_id: str, replicas: int) -> TenantDeployment:
        """Scale tenant deployment to specified number of replicas."""
        deployment = await self.get_tenant_deployment(tenant_id)
        if not deployment:
            raise DeploymentNotFoundError(f"Deployment not found for tenant: {tenant_id}")
        
        await self._init_k8s_clients()
        
        try:
            # Update deployment replicas
            await asyncio.get_event_loop().run_in_executor()
                None, self._apps_v1.patch_namespaced_deployment_scale,
                deployment.deployment_name, deployment.namespace,
                client.V1Scale(spec=client.V1ScaleSpec(replicas=replicas)
            )
            
            deployment.status = DeploymentStatus.SCALING
            await self.session.commit()
            
            # Log scaling event
            await self._log_deployment_event()
                deployment.id, "scale", "success",
                f"Scaled deployment to {replicas} replicas"
            )
            
            return deployment
            
        except ApiException as e:
            await self._log_deployment_event()
                deployment.id, "scale", "failed",
                f"Failed to scale deployment: {str(e)}"
            )
            raise ScalingError(f"Failed to scale deployment: {str(e)}")
    
    async def delete_tenant_deployment(self, tenant_id: str) -> bool:
        """Delete tenant deployment and all associated resources."""
        deployment = await self.get_tenant_deployment(tenant_id)
        if not deployment:
            return False
        
        await self._init_k8s_clients()
        
        try:
            deployment.status = DeploymentStatus.DELETING
            await self.session.commit()
            
            # Delete Kubernetes resources
            await self._cleanup_tenant_resources(deployment.namespace)
            
            # Delete deployment record
            await self.session.delete(deployment)
            await self.session.commit()
            
            # Log deletion event
            await self._log_deployment_event()
                deployment.id, "delete", "success",
                "Tenant deployment deleted successfully"
            )
            
            return True
            
        except Exception as e:
            deployment.status = DeploymentStatus.FAILED
            deployment.last_error = str(e)
            await self.session.commit()
            
            await self._log_deployment_event()
                deployment.id, "delete", "failed",
                f"Failed to delete deployment: {str(e)}"
            )
            raise DeploymentFailedError(f"Failed to delete deployment: {str(e)}")
    
    async def _cleanup_tenant_resources(self, namespace: str):
        """Clean up all Kubernetes resources for a tenant."""
        try:
            # Delete namespace (this will delete all resources in it)
            await asyncio.get_event_loop().run_in_executor()
                None, self._core_v1.delete_namespace, namespace
            )
        except ApiException as e:
            if e.status != 404:  # Ignore if namespace doesn't exist
                raise
    
    async def _log_deployment_event(self, deployment_id: str, event_type: str)
                                   event_status: str, message: str, event_data: Optional[Dict] = None):
        """Log deployment event."""
        event = DeploymentEvent()
            tenant_id=deployment_id,  # This will be fixed with proper tenant context
            deployment_id=deployment_id,
            event_type=event_type,
            event_status=event_status,
            event_message=message,
            event_data=event_data or {},
            automation_triggered=True
        )
        
        self.session.add(event)
        await self.session.commit()
    
    async def get_cluster_health(self) -> Dict[str, Any]:
        """Get overall cluster health status."""
        await self._init_k8s_clients()
        
        try:
            # Get cluster info
            cluster_info = await asyncio.get_event_loop().run_in_executor()
                None, self._core_v1.list_node
            )
            
            node_count = len(cluster_info.items)
            ready_nodes = sum(1 for node in cluster_info.items )
                            for condition in node.status.conditions
                            if condition.type == "Ready" and condition.status == "True")
            
            # Get namespace info
            namespaces = await asyncio.get_event_loop().run_in_executor()
                None, self._core_v1.list_namespace
            )
            
            tenant_namespaces = [ns for ns in namespaces.items 
                               if ns.metadata.labels and 
                               ns.metadata.labels.get("dotmac.io/tenant-id")]
            
            return {
                "cluster_healthy": ready_nodes == node_count,
                "total_nodes": node_count,
                "ready_nodes": ready_nodes,
                "total_namespaces": len(namespaces.items),
                "tenant_namespaces": len(tenant_namespaces),
                "last_check": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get cluster health: {str(e)}")
            return {
                "cluster_healthy": False,
                "error": str(e),
                "last_check": datetime.now(timezone.utc).isoformat()
            }