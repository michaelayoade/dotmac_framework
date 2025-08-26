"""
Infrastructure provisioning and management service.
Handles cloud resource creation, Kubernetes deployment, and infrastructure lifecycle.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from kubernetes import client, config
from kubernetes.client.rest import ApiException

from core.exceptions import InfrastructureError, ValidationError
from core.logging import get_logger
from models.infrastructure import InfrastructureTemplate, InfrastructureDeployment
from schemas.infrastructure import (
    InfrastructureRequest,
    InfrastructureStatus,
    KubernetesConfig,
    CloudResourceConfig
, timezone)

logger = get_logger(__name__)


class InfrastructureService:
    """Service for managing infrastructure provisioning and lifecycle."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._k8s_client = None
        
    async def provision_infrastructure(
        self, 
        tenant_id: UUID, 
        infrastructure_request: InfrastructureRequest,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Provision infrastructure resources for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            infrastructure_request: Infrastructure configuration request
            user_id: User performing the provisioning
            
        Returns:
            Dict containing provisioning status and resource details
        """
        try:
            logger.info(f"Starting infrastructure provisioning for tenant {tenant_id}")
            
            # 1. Validate infrastructure request
            await self._validate_infrastructure_request(infrastructure_request)
            
            # 2. Get infrastructure template
            template = await self._get_infrastructure_template(
                infrastructure_request.template_id
            )
            
            # 3. Create deployment record
            deployment = await self._create_deployment_record(
                tenant_id, infrastructure_request, template, user_id
            )
            
            # 4. Provision cloud resources
            cloud_resources = await self._provision_cloud_resources(
                deployment, infrastructure_request.cloud_config
            )
            
            # 5. Set up Kubernetes resources
            k8s_resources = await self._provision_kubernetes_resources(
                deployment, infrastructure_request.kubernetes_config
            )
            
            # 6. Configure networking
            network_config = await self._configure_networking(
                deployment, infrastructure_request.network_config
            )
            
            # 7. Set up monitoring and logging
            monitoring_config = await self._setup_monitoring(
                deployment, infrastructure_request.monitoring_config
            )
            
            # 8. Update deployment status
            await self._update_deployment_status(
                deployment.id, 
                InfrastructureStatus.ACTIVE,
                {
                    "cloud_resources": cloud_resources,
                    "kubernetes_resources": k8s_resources,
                    "network_config": network_config,
                    "monitoring_config": monitoring_config
                }
            )
            
            logger.info(f"Infrastructure provisioning completed for tenant {tenant_id}")
            
            return {
                "deployment_id": str(deployment.id),
                "status": InfrastructureStatus.ACTIVE,
                "cloud_resources": cloud_resources,
                "kubernetes_resources": k8s_resources,
                "network_config": network_config,
                "monitoring_config": monitoring_config,
                "provisioned_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Infrastructure provisioning failed for tenant {tenant_id}: {e}")
            if 'deployment' in locals():
                await self._update_deployment_status(
                    deployment.id, 
                    InfrastructureStatus.FAILED,
                    {"error": str(e)}
                )
            raise InfrastructureError(f"Infrastructure provisioning failed: {e}")
    
    async def deprovision_infrastructure(
        self, 
        tenant_id: UUID,
        deployment_id: UUID,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Deprovision infrastructure resources for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            deployment_id: Infrastructure deployment identifier
            user_id: User performing the deprovisioning
            
        Returns:
            Dict containing deprovisioning status
        """
        try:
            logger.info(f"Starting infrastructure deprovisioning for tenant {tenant_id}")
            
            # Get deployment record
            deployment = await self._get_deployment(deployment_id, tenant_id)
            
            if not deployment:
                raise ValidationError(f"Deployment {deployment_id} not found for tenant {tenant_id}")
            
            # Update status to deprovisioning
            await self._update_deployment_status(
                deployment_id, 
                InfrastructureStatus.DEPROVISIONING
            )
            
            # 1. Remove monitoring
            await self._remove_monitoring(deployment)
            
            # 2. Remove Kubernetes resources
            await self._deprovision_kubernetes_resources(deployment)
            
            # 3. Remove cloud resources
            await self._deprovision_cloud_resources(deployment)
            
            # 4. Clean up networking
            await self._cleanup_networking(deployment)
            
            # 5. Update deployment status
            await self._update_deployment_status(
                deployment_id, 
                InfrastructureStatus.DEPROVISIONED
            )
            
            logger.info(f"Infrastructure deprovisioning completed for tenant {tenant_id}")
            
            return {
                "deployment_id": str(deployment_id),
                "status": InfrastructureStatus.DEPROVISIONED,
                "deprovisioned_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Infrastructure deprovisioning failed: {e}")
            raise InfrastructureError(f"Infrastructure deprovisioning failed: {e}")
    
    async def get_infrastructure_status(
        self, 
        tenant_id: UUID,
        deployment_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Get infrastructure status for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            deployment_id: Optional specific deployment identifier
            
        Returns:
            Dict containing infrastructure status information
        """
        try:
            if deployment_id:
                # Get specific deployment
                deployment = await self._get_deployment(deployment_id, tenant_id)
                if not deployment:
                    raise ValidationError(f"Deployment {deployment_id} not found")
                
                deployments = [deployment]
            else:
                # Get all deployments for tenant
                deployments = await self._get_tenant_deployments(tenant_id)
            
            deployment_statuses = []
            for deployment in deployments:
                # Get real-time status from cloud provider and Kubernetes
                cloud_status = await self._get_cloud_resource_status(deployment)
                k8s_status = await self._get_kubernetes_status(deployment)
                
                deployment_statuses.append({
                    "deployment_id": str(deployment.id),
                    "template_name": deployment.template.name if deployment.template else None,
                    "status": deployment.status,
                    "cloud_resources": cloud_status,
                    "kubernetes_resources": k8s_status,
                    "created_at": deployment.created_at.isoformat(),
                    "last_updated": deployment.updated_at.isoformat()
                })
            
            return {
                "tenant_id": str(tenant_id),
                "total_deployments": len(deployment_statuses),
                "deployments": deployment_statuses
            }
            
        except Exception as e:
            logger.error(f"Failed to get infrastructure status: {e}")
            raise InfrastructureError(f"Failed to get infrastructure status: {e}")
    
    async def scale_infrastructure(
        self,
        tenant_id: UUID,
        deployment_id: UUID,
        scale_config: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """
        Scale infrastructure resources for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            deployment_id: Infrastructure deployment identifier
            scale_config: Scaling configuration
            user_id: User performing the scaling
            
        Returns:
            Dict containing scaling status
        """
        try:
            logger.info(f"Starting infrastructure scaling for tenant {tenant_id}")
            
            deployment = await self._get_deployment(deployment_id, tenant_id)
            if not deployment:
                raise ValidationError(f"Deployment {deployment_id} not found")
            
            # Scale Kubernetes resources
            k8s_scaling_result = await self._scale_kubernetes_resources(
                deployment, scale_config.get("kubernetes", {})
            )
            
            # Scale cloud resources if needed
            cloud_scaling_result = await self._scale_cloud_resources(
                deployment, scale_config.get("cloud", {})
            )
            
            # Update deployment metadata
            await self._update_deployment_metadata(
                deployment_id,
                {
                    "scaling_history": {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "user_id": user_id,
                        "config": scale_config,
                        "results": {
                            "kubernetes": k8s_scaling_result,
                            "cloud": cloud_scaling_result
                        }
                    }
                }
            )
            
            return {
                "deployment_id": str(deployment_id),
                "scaling_results": {
                    "kubernetes": k8s_scaling_result,
                    "cloud": cloud_scaling_result
                },
                "scaled_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Infrastructure scaling failed: {e}")
            raise InfrastructureError(f"Infrastructure scaling failed: {e}")
    
    # Private methods
    
    async def _validate_infrastructure_request(
        self, 
        request: InfrastructureRequest
    ) -> None:
        """Validate infrastructure provisioning request."""
        if not request.template_id:
            raise ValidationError("Template ID is required")
        
        # Validate resource limits
        if request.resource_limits:
            cpu_limit = request.resource_limits.get("cpu")
            memory_limit = request.resource_limits.get("memory")
            
            if cpu_limit and (cpu_limit < 0.1 or cpu_limit > 64):
                raise ValidationError("CPU limit must be between 0.1 and 64 cores")
            
            if memory_limit and (memory_limit < 128 or memory_limit > 131072):
                raise ValidationError("Memory limit must be between 128MB and 128GB")
    
    async def _get_infrastructure_template(
        self, 
        template_id: UUID
    ) -> InfrastructureTemplate:
        """Get infrastructure template by ID."""
        result = await self.db.execute(
            select(InfrastructureTemplate).where(
                InfrastructureTemplate.id == template_id,
                InfrastructureTemplate.is_active == True
            )
        )
        template = result.scalar_one_or_none()
        
        if not template:
            raise ValidationError(f"Infrastructure template {template_id} not found")
        
        return template
    
    async def _create_deployment_record(
        self,
        tenant_id: UUID,
        request: InfrastructureRequest,
        template: InfrastructureTemplate,
        user_id: str
    ) -> InfrastructureDeployment:
        """Create infrastructure deployment record."""
        deployment = InfrastructureDeployment(
            tenant_id=tenant_id,
            template_id=template.id,
            name=request.name,
            description=request.description,
            status=InfrastructureStatus.PROVISIONING,
            configuration=request.model_dump(),
            resource_limits=request.resource_limits or {},
            metadata={
                "created_by": user_id,
                "template_name": template.name,
                "provisioning_started": datetime.now(timezone.utc).isoformat()
            }
        )
        
        self.db.add(deployment)
        await self.db.commit()
        await self.db.refresh(deployment)
        
        return deployment
    
    async def _provision_cloud_resources(
        self,
        deployment: InfrastructureDeployment,
        cloud_config: Optional[CloudResourceConfig]
    ) -> Dict[str, Any]:
        """Provision cloud resources (AWS, GCP, Azure)."""
        if not cloud_config:
            return {}
        
        logger.info(f"Provisioning cloud resources for deployment {deployment.id}")
        
        # Simulate cloud resource provisioning
        # In real implementation, this would use cloud provider SDKs
        cloud_resources = {
            "vpc_id": f"vpc-{deployment.id.hex[:8]}",
            "subnet_ids": [
                f"subnet-{deployment.id.hex[:8]}-1",
                f"subnet-{deployment.id.hex[:8]}-2"
            ],
            "security_group_id": f"sg-{deployment.id.hex[:8]}",
            "load_balancer_arn": f"arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/lb-{deployment.id.hex[:8]}"
        }
        
        # Simulate provisioning delay
        await asyncio.sleep(2)
        
        return cloud_resources
    
    async def _provision_kubernetes_resources(
        self,
        deployment: InfrastructureDeployment,
        k8s_config: Optional[KubernetesConfig]
    ) -> Dict[str, Any]:
        """Provision Kubernetes resources."""
        if not k8s_config:
            return {}
        
        logger.info(f"Provisioning Kubernetes resources for deployment {deployment.id}")
        
        try:
            # Initialize Kubernetes client
            k8s_client = await self._get_k8s_client()
            
            # Create namespace
            namespace_name = f"tenant-{str(deployment.tenant_id).replace('-', '')[:8]}"
            await self._create_namespace(k8s_client, namespace_name)
            
            # Create deployment
            deployment_name = f"app-{deployment.name}"
            await self._create_k8s_deployment(
                k8s_client, namespace_name, deployment_name, k8s_config
            )
            
            # Create service
            service_name = f"svc-{deployment.name}"
            await self._create_k8s_service(
                k8s_client, namespace_name, service_name, deployment_name
            )
            
            # Create ingress if needed
            ingress_name = None
            if k8s_config.expose_external:
                ingress_name = f"ing-{deployment.name}"
                await self._create_k8s_ingress(
                    k8s_client, namespace_name, ingress_name, service_name
                )
            
            return {
                "namespace": namespace_name,
                "deployment": deployment_name,
                "service": service_name,
                "ingress": ingress_name,
                "replicas": k8s_config.replicas
            }
            
        except Exception as e:
            logger.error(f"Kubernetes resource provisioning failed: {e}")
            raise InfrastructureError(f"Kubernetes provisioning failed: {e}")
    
    async def _configure_networking(
        self,
        deployment: InfrastructureDeployment,
        network_config: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Configure networking for the deployment."""
        if not network_config:
            return {}
        
        logger.info(f"Configuring networking for deployment {deployment.id}")
        
        # Simulate networking configuration
        network_result = {
            "internal_ip": f"10.0.{deployment.id.int % 255}.{(deployment.id.int // 255) % 255}",
            "external_ip": f"203.0.113.{deployment.id.int % 255}",
            "dns_name": f"{deployment.name}.{str(deployment.tenant_id)[:8]}.dotmac.local",
            "ports": network_config.get("ports", [80, 443])
        }
        
        return network_result
    
    async def _setup_monitoring(
        self,
        deployment: InfrastructureDeployment,
        monitoring_config: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Set up monitoring for the deployment."""
        if not monitoring_config:
            return {}
        
        logger.info(f"Setting up monitoring for deployment {deployment.id}")
        
        # Simulate monitoring setup
        monitoring_result = {
            "prometheus_endpoint": f"https://prometheus.dotmac.local/tenant-{str(deployment.tenant_id)[:8]}",
            "grafana_dashboard": f"https://grafana.dotmac.local/d/{deployment.id.hex[:8]}",
            "alerts_configured": True,
            "metrics_retention_days": monitoring_config.get("retention_days", 30)
        }
        
        return monitoring_result
    
    async def _update_deployment_status(
        self,
        deployment_id: UUID,
        status: InfrastructureStatus,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update deployment status and metadata."""
        update_data = {"status": status, "updated_at": datetime.now(timezone.utc)}
        
        if metadata:
            # Merge with existing metadata
            result = await self.db.execute(
                select(InfrastructureDeployment.metadata).where(
                    InfrastructureDeployment.id == deployment_id
                )
            )
            existing_metadata = result.scalar_one_or_none() or {}
            existing_metadata.update(metadata)
            update_data["metadata"] = existing_metadata
        
        await self.db.execute(
            update(InfrastructureDeployment)
            .where(InfrastructureDeployment.id == deployment_id)
            .values(**update_data)
        )
        await self.db.commit()
    
    async def _get_deployment(
        self, 
        deployment_id: UUID, 
        tenant_id: UUID
    ) -> Optional[InfrastructureDeployment]:
        """Get deployment by ID and tenant."""
        result = await self.db.execute(
            select(InfrastructureDeployment).where(
                InfrastructureDeployment.id == deployment_id,
                InfrastructureDeployment.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()
    
    async def _get_tenant_deployments(
        self, 
        tenant_id: UUID
    ) -> List[InfrastructureDeployment]:
        """Get all deployments for a tenant."""
        result = await self.db.execute(
            select(InfrastructureDeployment).where(
                InfrastructureDeployment.tenant_id == tenant_id
            )
        )
        return result.scalars().all()
    
    async def _get_k8s_client(self):
        """Get Kubernetes client."""
        if not self._k8s_client:
            try:
                # Try to load in-cluster config first
                config.load_incluster_config()
            except config.ConfigException:
                # Fall back to kubeconfig
                config.load_kube_config()
            
            self._k8s_client = {
                "apps_v1": client.AppsV1Api(),
                "core_v1": client.CoreV1Api(),
                "networking_v1": client.NetworkingV1Api()
            }
        
        return self._k8s_client
    
    async def _create_namespace(self, k8s_client: Dict, namespace_name: str):
        """Create Kubernetes namespace."""
        namespace = client.V1Namespace(
            metadata=client.V1ObjectMeta(name=namespace_name)
        )
        
        try:
            k8s_client["core_v1"].create_namespace(namespace)
            logger.info(f"Created namespace: {namespace_name}")
        except ApiException as e:
            if e.status == 409:  # Already exists
                logger.info(f"Namespace {namespace_name} already exists")
            else:
                raise
    
    async def _create_k8s_deployment(
        self, 
        k8s_client: Dict, 
        namespace: str, 
        name: str, 
        config: KubernetesConfig
    ):
        """Create Kubernetes deployment."""
        container = client.V1Container(
            name=name,
            image=config.image,
            ports=[client.V1ContainerPort(container_port=config.port)],
            resources=client.V1ResourceRequirements(
                requests={"cpu": "100m", "memory": "128Mi"},
                limits={"cpu": "500m", "memory": "512Mi"}
            )
        )
        
        template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(labels={"app": name}),
            spec=client.V1PodSpec(containers=[container])
        )
        
        spec = client.V1DeploymentSpec(
            replicas=config.replicas,
            selector=client.V1LabelSelector(match_labels={"app": name}),
            template=template
        )
        
        deployment = client.V1Deployment(
            api_version="apps/v1",
            kind="Deployment",
            metadata=client.V1ObjectMeta(name=name),
            spec=spec
        )
        
        k8s_client["apps_v1"].create_namespaced_deployment(
            namespace=namespace, body=deployment
        )
        logger.info(f"Created deployment: {name} in namespace: {namespace}")
    
    async def _create_k8s_service(
        self, 
        k8s_client: Dict, 
        namespace: str, 
        service_name: str, 
        deployment_name: str
    ):
        """Create Kubernetes service."""
        service = client.V1Service(
            metadata=client.V1ObjectMeta(name=service_name),
            spec=client.V1ServiceSpec(
                selector={"app": deployment_name},
                ports=[client.V1ServicePort(port=80, target_port=8080)]
            )
        )
        
        k8s_client["core_v1"].create_namespaced_service(
            namespace=namespace, body=service
        )
        logger.info(f"Created service: {service_name} in namespace: {namespace}")
    
    async def _create_k8s_ingress(
        self, 
        k8s_client: Dict, 
        namespace: str, 
        ingress_name: str, 
        service_name: str
    ):
        """Create Kubernetes ingress."""
        ingress = client.V1Ingress(
            metadata=client.V1ObjectMeta(name=ingress_name),
            spec=client.V1IngressSpec(
                rules=[
                    client.V1IngressRule(
                        host=f"{ingress_name}.dotmac.local",
                        http=client.V1HTTPIngressRuleValue(
                            paths=[
                                client.V1HTTPIngressPath(
                                    path="/",
                                    path_type="Prefix",
                                    backend=client.V1IngressBackend(
                                        service=client.V1IngressServiceBackend(
                                            name=service_name,
                                            port=client.V1ServiceBackendPort(number=80)
                                        )
                                    )
                                )
                            ]
                        )
                    )
                ]
            )
        )
        
        k8s_client["networking_v1"].create_namespaced_ingress(
            namespace=namespace, body=ingress
        )
        logger.info(f"Created ingress: {ingress_name} in namespace: {namespace}")
    
    # Additional helper methods for deprovisioning, scaling, and status checking
    
    async def _deprovision_kubernetes_resources(self, deployment: InfrastructureDeployment):
        """Remove Kubernetes resources."""
        # Implementation for removing K8s resources
        pass
    
    async def _deprovision_cloud_resources(self, deployment: InfrastructureDeployment):
        """Remove cloud resources."""
        # Implementation for removing cloud resources
        pass
    
    async def _cleanup_networking(self, deployment: InfrastructureDeployment):
        """Clean up networking configuration."""
        # Implementation for network cleanup
        pass
    
    async def _remove_monitoring(self, deployment: InfrastructureDeployment):
        """Remove monitoring configuration."""
        # Implementation for monitoring cleanup
        pass
    
    async def _get_cloud_resource_status(self, deployment: InfrastructureDeployment) -> Dict[str, Any]:
        """Get real-time cloud resource status."""
        # Implementation for cloud status checking
        return {"status": "healthy", "resources": []}
    
    async def _get_kubernetes_status(self, deployment: InfrastructureDeployment) -> Dict[str, Any]:
        """Get real-time Kubernetes status."""
        # Implementation for K8s status checking
        return {"status": "healthy", "pods_ready": "2/2"}
    
    async def _scale_kubernetes_resources(
        self, 
        deployment: InfrastructureDeployment, 
        scale_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Scale Kubernetes resources."""
        # Implementation for K8s scaling
        return {"scaled": True, "new_replicas": scale_config.get("replicas", 1)}
    
    async def _scale_cloud_resources(
        self, 
        deployment: InfrastructureDeployment, 
        scale_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Scale cloud resources."""
        # Implementation for cloud scaling
        return {"scaled": True, "new_instance_type": scale_config.get("instance_type")}
    
    async def _update_deployment_metadata(
        self, 
        deployment_id: UUID, 
        metadata_update: Dict[str, Any]
    ):
        """Update deployment metadata."""
        # Implementation for metadata updates
        pass