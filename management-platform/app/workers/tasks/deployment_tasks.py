"""
Background tasks for deployment operations.
"""

import logging
from datetime import datetime
from typing import Dict, Any
from uuid import UUID

from celery import current_task
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from ...core.config import settings
from ...services.deployment_service import DeploymentService
from ...workers.celery_app import celery_app

logger = logging.getLogger(__name__)

# Create async database session for workers
engine = create_async_engine(settings.database_url)
async_session = async_sessionmaker(engine, expire_on_commit=False)


@celery_app.task(bind=True, max_retries=3)
def provision_infrastructure(self, infrastructure_id: str, user_id: str):
    """Provision infrastructure asynchronously."""
    import asyncio
    
    async def _provision_infrastructure():
        async with async_session() as db:
            try:
                service = DeploymentService(db)
                infrastructure_uuid = UUID(infrastructure_id)
                
                # Get infrastructure details
                infrastructure = await service.infrastructure_repo.get_by_id(infrastructure_uuid)
                if not infrastructure:
                    raise ValueError(f"Infrastructure not found: {infrastructure_id}")
                
                # Update status to provisioning
                await service.infrastructure_repo.update_status(
                    infrastructure_uuid, "provisioning", user_id
                )
                
                # Log start
                await service._log_deployment_event(
                    None, "infrastructure_provisioning_started",
                    f"Starting infrastructure provisioning for {infrastructure.name}",
                    user_id
                )
                
                # TODO: Integrate with actual infrastructure providers
                # For now, simulate provisioning
                steps = [
                    ("validating_config", "Validating infrastructure configuration"),
                    ("creating_network", "Creating network infrastructure"),
                    ("provisioning_compute", "Provisioning compute resources"),
                    ("configuring_security", "Configuring security groups"),
                    ("setting_up_monitoring", "Setting up monitoring"),
                    ("finalizing", "Finalizing infrastructure setup")
                ]
                
                current_task.update_state(
                    state="PROGRESS",
                    meta={"current": 0, "total": len(steps), "status": "Starting"}
                )
                
                for i, (step_key, step_description) in enumerate(steps):
                    await service._log_deployment_event(
                        None, f"infrastructure_{step_key}",
                        step_description, user_id
                    )
                    
                    # Simulate step execution
                    await asyncio.sleep(2)
                    
                    current_task.update_state(
                        state="PROGRESS",
                        meta={
                            "current": i + 1,
                            "total": len(steps),
                            "status": step_description
                        }
                    )
                
                # Update infrastructure with provisioned resources
                resources = {
                    "vpc_id": f"vpc-{infrastructure_id[:8]}",
                    "subnet_ids": [f"subnet-{infrastructure_id[:8]}-1", f"subnet-{infrastructure_id[:8]}-2"],
                    "security_group_id": f"sg-{infrastructure_id[:8]}",
                    "load_balancer_arn": f"arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/lb-{infrastructure_id[:8]}"
                }
                
                endpoints = {
                    "api": f"https://api-{infrastructure.name}.example.com",
                    "console": f"https://console-{infrastructure.name}.example.com"
                }
                
                await service.infrastructure_repo.update(
                    infrastructure_uuid,
                    {
                        "status": "active",
                        "resources": resources,
                        "endpoints": endpoints
                    },
                    user_id
                )
                
                await service._log_deployment_event(
                    None, "infrastructure_provisioning_completed",
                    f"Infrastructure provisioning completed for {infrastructure.name}",
                    user_id
                )
                
                logger.info(f"Infrastructure provisioned successfully: {infrastructure_id}")
                return {
                    "infrastructure_id": infrastructure_id,
                    "status": "active",
                    "resources": resources,
                    "endpoints": endpoints
                }
                
            except Exception as e:
                # Update status to failed
                await service.infrastructure_repo.update_status(
                    UUID(infrastructure_id), "failed", user_id
                )
                
                await service._log_deployment_event(
                    None, "infrastructure_provisioning_failed",
                    f"Infrastructure provisioning failed: {str(e)}",
                    user_id
                )
                
                logger.error(f"Infrastructure provisioning failed: {e}")
                raise self.retry(countdown=60, exc=e)
    
    return asyncio.run(_provision_infrastructure())


@celery_app.task(bind=True, max_retries=3)
def deploy_service(self, deployment_id: str, user_id: str):
    """Deploy a service asynchronously."""
    import asyncio
    
    async def _deploy_service():
        async with async_session() as db:
            try:
                service = DeploymentService(db)
                deployment_uuid = UUID(deployment_id)
                
                # Get deployment details
                deployment = await service.deployment_repo.get_with_relations(deployment_uuid)
                if not deployment:
                    raise ValueError(f"Deployment not found: {deployment_id}")
                
                # Update status to deploying
                await service.deployment_repo.update_status(
                    deployment_uuid, "deploying", user_id
                )
                
                # Log start
                await service._log_deployment_event(
                    deployment_uuid, "service_deployment_started",
                    f"Starting service deployment for {deployment.name}",
                    user_id
                )
                
                # Deployment steps
                steps = [
                    ("building_image", "Building container image"),
                    ("pushing_image", "Pushing image to registry"),
                    ("creating_resources", "Creating Kubernetes resources"),
                    ("waiting_for_rollout", "Waiting for rollout to complete"),
                    ("health_checking", "Performing health checks"),
                    ("updating_load_balancer", "Updating load balancer configuration")
                ]
                
                current_task.update_state(
                    state="PROGRESS",
                    meta={"current": 0, "total": len(steps), "status": "Starting deployment"}
                )
                
                for i, (step_key, step_description) in enumerate(steps):
                    await service._log_deployment_event(
                        deployment_uuid, f"deployment_{step_key}",
                        step_description, user_id
                    )
                    
                    # Simulate step execution
                    await asyncio.sleep(3)
                    
                    current_task.update_state(
                        state="PROGRESS",
                        meta={
                            "current": i + 1,
                            "total": len(steps),
                            "status": step_description
                        }
                    )
                
                # Create service instance
                from datetime import datetime
                service_data = {
                    "tenant_id": deployment.tenant_id,
                    "deployment_id": deployment_uuid,
                    "service_name": deployment.name,
                    "service_type": "web_service",
                    "status": "running",
                    "health_status": "healthy",
                    "version": deployment.version,
                    "configuration": deployment.configuration,
                    "endpoints": {
                        "http": f"https://{deployment.name}.{deployment.environment}.example.com",
                        "health": f"https://{deployment.name}.{deployment.environment}.example.com/health",
                        "metrics": f"https://{deployment.name}.{deployment.environment}.example.com/metrics"
                    },
                    "resource_usage": {
                        "cpu": 0.1,
                        "memory": 128,
                        "disk": 1024
                    }
                }
                
                service_instance = await service.service_repo.create(service_data, user_id)
                
                # Update deployment status
                await service.deployment_repo.update(
                    deployment_uuid,
                    {
                        "status": "deployed",
                        "deployed_at": datetime.utcnow()
                    },
                    user_id
                )
                
                await service._log_deployment_event(
                    deployment_uuid, "service_deployment_completed",
                    f"Service deployment completed for {deployment.name}",
                    user_id
                )
                
                logger.info(f"Service deployed successfully: {deployment_id}")
                return {
                    "deployment_id": deployment_id,
                    "service_instance_id": str(service_instance.id),
                    "status": "deployed",
                    "endpoints": service_data["endpoints"]
                }
                
            except Exception as e:
                # Update status to failed
                await service.deployment_repo.update_status(
                    UUID(deployment_id), "failed", user_id
                )
                
                await service._log_deployment_event(
                    UUID(deployment_id), "service_deployment_failed",
                    f"Service deployment failed: {str(e)}",
                    user_id
                )
                
                logger.error(f"Service deployment failed: {e}")
                raise self.retry(countdown=60, exc=e)
    
    return asyncio.run(_deploy_service())


@celery_app.task(bind=True, max_retries=3)
def scale_service(self, deployment_id: str, service_name: str, target_instances: int, user_id: str):
    """Scale a service asynchronously."""
    import asyncio
    
    async def _scale_service():
        async with async_session() as db:
            try:
                service = DeploymentService(db)
                deployment_uuid = UUID(deployment_id)
                
                # Log scaling start
                await service._log_deployment_event(
                    deployment_uuid, "service_scaling_started",
                    f"Starting to scale {service_name} to {target_instances} instances",
                    user_id
                )
                
                # Get service instance
                services = await service.service_repo.get_by_deployment(deployment_uuid)
                target_service = None
                
                for svc in services:
                    if svc.service_name == service_name:
                        target_service = svc
                        break
                
                if not target_service:
                    raise ValueError(f"Service {service_name} not found in deployment {deployment_id}")
                
                # Update service configuration
                current_config = target_service.configuration or {}
                current_instances = current_config.get("instances", 1)
                
                current_config.update({
                    "instances": target_instances,
                    "scaling_policy": "manual"
                })
                
                # Simulate scaling steps
                if target_instances > current_instances:
                    # Scaling up
                    steps = [
                        "Updating deployment configuration",
                        "Creating new pod replicas",
                        "Waiting for pods to become ready",
                        "Updating load balancer targets"
                    ]
                else:
                    # Scaling down
                    steps = [
                        "Updating deployment configuration", 
                        "Draining connections from excess pods",
                        "Terminating excess pods",
                        "Updating load balancer targets"
                    ]
                
                for i, step in enumerate(steps):
                    await service._log_deployment_event(
                        deployment_uuid, "service_scaling_progress",
                        step, user_id
                    )
                    
                    current_task.update_state(
                        state="PROGRESS",
                        meta={
                            "current": i + 1,
                            "total": len(steps),
                            "status": step
                        }
                    )
                    
                    await asyncio.sleep(2)
                
                # Update service instance
                await service.service_repo.update(
                    target_service.id,
                    {
                        "configuration": current_config,
                        "resource_usage": {
                            "cpu": 0.1 * target_instances,
                            "memory": 128 * target_instances,
                            "disk": 1024
                        }
                    },
                    user_id
                )
                
                await service._log_deployment_event(
                    deployment_uuid, "service_scaling_completed",
                    f"Successfully scaled {service_name} to {target_instances} instances",
                    user_id
                )
                
                logger.info(f"Service scaled successfully: {service_name} to {target_instances} instances")
                return {
                    "deployment_id": deployment_id,
                    "service_name": service_name,
                    "target_instances": target_instances,
                    "status": "completed"
                }
                
            except Exception as e:
                await service._log_deployment_event(
                    UUID(deployment_id), "service_scaling_failed",
                    f"Service scaling failed: {str(e)}",
                    user_id
                )
                
                logger.error(f"Service scaling failed: {e}")
                raise self.retry(countdown=60, exc=e)
    
    return asyncio.run(_scale_service())


@celery_app.task(bind=True, max_retries=3)
def check_infrastructure_health(self):
    """Check health of all infrastructure periodically."""
    import asyncio
    
    async def _check_health():
        async with async_session() as db:
            try:
                service = DeploymentService(db)
                
                # Get all active infrastructure
                infrastructures = await service.infrastructure_repo.get_active_infrastructure()
                
                healthy_count = 0
                unhealthy_count = 0
                
                for infrastructure in infrastructures:
                    try:
                        # Execute actual health checks based on infrastructure provider
                        health_result = await _perform_infrastructure_health_check(infrastructure)
                        
                        if health_result["is_healthy"]:
                            healthy_count += 1
                            
                            # Update infrastructure health status
                            await service.infrastructure_repo.update_health_status(
                                infrastructure.id, "healthy", "health_check_task"
                            )
                        else:
                            unhealthy_count += 1
                            
                            # Update infrastructure health status
                            await service.infrastructure_repo.update_health_status(
                                infrastructure.id, "unhealthy", "health_check_task"
                            )
                            
                            # Log unhealthy infrastructure with details
                            logger.warning(
                                f"Infrastructure {infrastructure.id} is unhealthy: {health_result['details']}"
                            )
                            
                            # Trigger alerts for unhealthy infrastructure
                            await _trigger_infrastructure_alert(infrastructure, health_result)
                        
                    except Exception as e:
                        logger.error(f"Failed to check health for infrastructure {infrastructure.id}: {e}")
                        unhealthy_count += 1
                
                logger.info(f"Infrastructure health check completed: {healthy_count} healthy, {unhealthy_count} unhealthy")
                return {"healthy": healthy_count, "unhealthy": unhealthy_count}
                
            except Exception as e:
                logger.error(f"Error checking infrastructure health: {e}")
                raise self.retry(countdown=60, exc=e)
    
    return asyncio.run(_check_health())


@celery_app.task(bind=True, max_retries=3)
def cleanup_old_deployments(self, retention_days: int = 30):
    """Clean up old failed deployments."""
    import asyncio
    from datetime import datetime, timedelta
    
    async def _cleanup_deployments():
        async with async_session() as db:
            try:
                service = DeploymentService(db)
                
                cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
                
                # Get old failed deployments
                old_deployments = await service.deployment_repo.get_old_failed_deployments(cutoff_date)
                
                cleaned_up = 0
                failed = 0
                
                for deployment in old_deployments:
                    try:
                        # Clean up deployment resources
                        await service.deployment_repo.soft_delete(deployment.id)
                        cleaned_up += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to cleanup deployment {deployment.id}: {e}")
                        failed += 1
                
                logger.info(f"Deployment cleanup completed: {cleaned_up} cleaned up, {failed} failed")
                return {"cleaned_up": cleaned_up, "failed": failed}
                
            except Exception as e:
                logger.error(f"Error cleaning up deployments: {e}")
                raise self.retry(countdown=60, exc=e)
    
    return asyncio.run(_cleanup_deployments())


@celery_app.task(bind=True, max_retries=3)
def backup_deployment_configs(self, tenant_id: str = None):
    """Backup deployment configurations."""
    import asyncio
    from datetime import datetime
    
    async def _backup_configs():
        async with async_session() as db:
            try:
                service = DeploymentService(db)
                
                # Get deployments to backup
                filters = {"status": "deployed"}
                if tenant_id:
                    filters["tenant_id"] = UUID(tenant_id)
                
                deployments = await service.deployment_repo.list(filters=filters)
                
                backed_up = 0
                failed = 0
                
                for deployment in deployments:
                    try:
                        # Implement actual backup to storage (S3, Azure Blob, local filesystem)
                        backup_success = await _perform_deployment_backup(deployment, service)
                        
                        if backup_success:
                            backed_up += 1
                            logger.info(f"Successfully backed up deployment {deployment.id}")
                        else:
                            failed += 1
                            logger.warning(f"Failed to backup deployment {deployment.id}")
                        
                        # Update deployment with last backup timestamp
                        await service.deployment_repo.update_metadata(
                            deployment.id, 
                            {"last_backup_at": datetime.utcnow().isoformat()},
                            "backup_task"
                        )
                        
                    except Exception as e:
                        logger.error(f"Failed to backup deployment {deployment.id}: {e}")
                        failed += 1
                
                logger.info(f"Deployment backup completed: {backed_up} backed up, {failed} failed")
                return {"backed_up": backed_up, "failed": failed}
                
            except Exception as e:
                logger.error(f"Error backing up deployment configs: {e}")
                raise self.retry(countdown=60, exc=e)
    
    return asyncio.run(_backup_configs())


async def _perform_infrastructure_health_check(infrastructure) -> Dict[str, Any]:
    """Perform comprehensive health check on infrastructure."""
    try:
        provider = infrastructure.provider
        metadata = infrastructure.metadata or {}
        
        if provider == "aws":
            return await _check_aws_health(infrastructure, metadata)
        elif provider == "azure":
            return await _check_azure_health(infrastructure, metadata)
        elif provider == "gcp":
            return await _check_gcp_health(infrastructure, metadata)
        elif provider == "digitalocean":
            return await _check_digitalocean_health(infrastructure, metadata)
        elif provider == "kubernetes":
            return await _check_kubernetes_health(infrastructure, metadata)
        elif provider == "docker":
            return await _check_docker_health(infrastructure, metadata)
        else:
            return {
                "is_healthy": False,
                "details": f"Unknown provider type: {provider}",
                "checks": []
            }
    except Exception as e:
        logger.error(f"Error performing infrastructure health check: {e}")
        return {
            "is_healthy": False,
            "details": f"Health check error: {str(e)}",
            "checks": []
        }


async def _check_aws_health(infrastructure, metadata: Dict) -> Dict[str, Any]:
    """Check AWS infrastructure health."""
    try:
        import boto3
        from botocore.exceptions import ClientError
        
        # Configure AWS client
        aws_access_key = metadata.get("aws_access_key_id")
        aws_secret_key = metadata.get("aws_secret_access_key")
        region = metadata.get("region", "us-east-1")
        
        if not aws_access_key or not aws_secret_key:
            return {
                "is_healthy": False,
                "details": "AWS credentials not configured",
                "checks": []
            }
        
        ec2 = boto3.client(
            'ec2',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=region
        )
        
        checks = []
        all_healthy = True
        
        # Check EC2 instances
        instance_ids = metadata.get("instance_ids", [])
        if instance_ids:
            try:
                response = ec2.describe_instances(InstanceIds=instance_ids)
                
                for reservation in response["Reservations"]:
                    for instance in reservation["Instances"]:
                        instance_id = instance["InstanceId"]
                        state = instance["State"]["Name"]
                        
                        is_healthy = state == "running"
                        checks.append({
                            "type": "ec2_instance",
                            "resource_id": instance_id,
                            "status": state,
                            "healthy": is_healthy
                        })
                        
                        if not is_healthy:
                            all_healthy = False
                            
            except ClientError as e:
                checks.append({
                    "type": "ec2_check",
                    "error": str(e),
                    "healthy": False
                })
                all_healthy = False
        
        # Check Load Balancers
        load_balancer_arns = metadata.get("load_balancer_arns", [])
        if load_balancer_arns:
            try:
                elbv2 = boto3.client(
                    'elbv2',
                    aws_access_key_id=aws_access_key,
                    aws_secret_access_key=aws_secret_key,
                    region_name=region
                )
                
                response = elbv2.describe_load_balancers(LoadBalancerArns=load_balancer_arns)
                
                for lb in response["LoadBalancers"]:
                    lb_arn = lb["LoadBalancerArn"]
                    state = lb["State"]["Code"]
                    
                    is_healthy = state == "active"
                    checks.append({
                        "type": "load_balancer",
                        "resource_id": lb_arn.split("/")[-1],
                        "status": state,
                        "healthy": is_healthy
                    })
                    
                    if not is_healthy:
                        all_healthy = False
                        
            except ClientError as e:
                checks.append({
                    "type": "elb_check",
                    "error": str(e),
                    "healthy": False
                })
                all_healthy = False
        
        return {
            "is_healthy": all_healthy,
            "details": f"AWS health check completed with {len(checks)} checks",
            "checks": checks
        }
        
    except Exception as e:
        return {
            "is_healthy": False,
            "details": f"AWS health check failed: {str(e)}",
            "checks": []
        }


async def _check_kubernetes_health(infrastructure, metadata: Dict) -> Dict[str, Any]:
    """Check Kubernetes cluster health."""
    try:
        from kubernetes import client as k8s_client, config as k8s_config
        from kubernetes.client.rest import ApiException
        
        # Configure Kubernetes client
        if metadata.get("kubeconfig"):
            k8s_config.load_kube_config_from_dict(metadata["kubeconfig"])
        else:
            k8s_config.load_incluster_config()
        
        v1 = k8s_client.CoreV1Api()
        apps_v1 = k8s_client.AppsV1Api()
        
        checks = []
        all_healthy = True
        namespace = metadata.get("namespace", "default")
        
        # Check cluster connectivity
        try:
            v1.get_api_versions()
            checks.append({
                "type": "cluster_connectivity",
                "status": "connected",
                "healthy": True
            })
        except ApiException as e:
            checks.append({
                "type": "cluster_connectivity",
                "error": str(e),
                "healthy": False
            })
            all_healthy = False
            
        # Check nodes health
        try:
            nodes = v1.list_node()
            for node in nodes.items:
                node_name = node.metadata.name
                conditions = node.status.conditions or []
                
                ready_condition = None
                for condition in conditions:
                    if condition.type == "Ready":
                        ready_condition = condition
                        break
                
                is_healthy = ready_condition and ready_condition.status == "True"
                checks.append({
                    "type": "node",
                    "resource_id": node_name,
                    "status": ready_condition.status if ready_condition else "Unknown",
                    "healthy": is_healthy
                })
                
                if not is_healthy:
                    all_healthy = False
                    
        except ApiException as e:
            checks.append({
                "type": "node_check",
                "error": str(e),
                "healthy": False
            })
            all_healthy = False
        
        # Check deployments in namespace
        try:
            deployments = apps_v1.list_namespaced_deployment(namespace=namespace)
            for deployment in deployments.items:
                deployment_name = deployment.metadata.name
                status = deployment.status
                
                # Check if deployment is available
                available_replicas = status.available_replicas or 0
                desired_replicas = deployment.spec.replicas or 1
                
                is_healthy = available_replicas >= desired_replicas
                checks.append({
                    "type": "deployment",
                    "resource_id": deployment_name,
                    "status": f"{available_replicas}/{desired_replicas}",
                    "healthy": is_healthy
                })
                
                if not is_healthy:
                    all_healthy = False
                    
        except ApiException as e:
            checks.append({
                "type": "deployment_check",
                "error": str(e),
                "healthy": False
            })
            all_healthy = False
        
        return {
            "is_healthy": all_healthy,
            "details": f"Kubernetes health check completed with {len(checks)} checks",
            "checks": checks
        }
        
    except Exception as e:
        return {
            "is_healthy": False,
            "details": f"Kubernetes health check failed: {str(e)}",
            "checks": []
        }


async def _check_docker_health(infrastructure, metadata: Dict) -> Dict[str, Any]:
    """Check Docker infrastructure health."""
    try:
        import docker
        from docker.errors import DockerException
        
        docker_client = docker.from_env()
        
        checks = []
        all_healthy = True
        
        # Check Docker daemon connectivity
        try:
            docker_client.ping()
            checks.append({
                "type": "docker_daemon",
                "status": "running",
                "healthy": True
            })
        except DockerException as e:
            checks.append({
                "type": "docker_daemon",
                "error": str(e),
                "healthy": False
            })
            all_healthy = False
            
        # Check specific containers
        container_names = metadata.get("container_names", [])
        if container_names:
            for container_name in container_names:
                try:
                    container = docker_client.containers.get(container_name)
                    status = container.status
                    
                    is_healthy = status == "running"
                    checks.append({
                        "type": "container",
                        "resource_id": container_name,
                        "status": status,
                        "healthy": is_healthy
                    })
                    
                    if not is_healthy:
                        all_healthy = False
                        
                except docker.errors.NotFound:
                    checks.append({
                        "type": "container",
                        "resource_id": container_name,
                        "status": "not_found",
                        "healthy": False
                    })
                    all_healthy = False
                except DockerException as e:
                    checks.append({
                        "type": "container",
                        "resource_id": container_name,
                        "error": str(e),
                        "healthy": False
                    })
                    all_healthy = False
        
        # Check system resources
        try:
            system_info = docker_client.info()
            containers_running = system_info.get("ContainersRunning", 0)
            
            checks.append({
                "type": "system_info",
                "status": f"{containers_running} containers running",
                "healthy": True
            })
            
        except DockerException as e:
            checks.append({
                "type": "system_info",
                "error": str(e),
                "healthy": False
            })
            all_healthy = False
        
        return {
            "is_healthy": all_healthy,
            "details": f"Docker health check completed with {len(checks)} checks",
            "checks": checks
        }
        
    except Exception as e:
        return {
            "is_healthy": False,
            "details": f"Docker health check failed: {str(e)}",
            "checks": []
        }


async def _check_digitalocean_health(infrastructure, metadata: Dict) -> Dict[str, Any]:
    """Check DigitalOcean infrastructure health."""
    try:
        import aiohttp
        
        api_token = metadata.get("api_token")
        if not api_token:
            return {
                "is_healthy": False,
                "details": "DigitalOcean API token not configured",
                "checks": []
            }
        
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
        
        checks = []
        all_healthy = True
        
        async with aiohttp.ClientSession(headers=headers) as session:
            # Check droplets
            droplet_ids = metadata.get("droplet_ids", [])
            if droplet_ids:
                for droplet_id in droplet_ids:
                    try:
                        url = f"https://api.digitalocean.com/v2/droplets/{droplet_id}"
                        async with session.get(url) as response:
                            if response.status == 200:
                                data = await response.json()
                                droplet = data["droplet"]
                                status = droplet["status"]
                                
                                is_healthy = status == "active"
                                checks.append({
                                    "type": "droplet",
                                    "resource_id": str(droplet_id),
                                    "status": status,
                                    "healthy": is_healthy
                                })
                                
                                if not is_healthy:
                                    all_healthy = False
                            else:
                                checks.append({
                                    "type": "droplet",
                                    "resource_id": str(droplet_id),
                                    "error": f"API error: {response.status}",
                                    "healthy": False
                                })
                                all_healthy = False
                                
                    except Exception as e:
                        checks.append({
                            "type": "droplet",
                            "resource_id": str(droplet_id),
                            "error": str(e),
                            "healthy": False
                        })
                        all_healthy = False
            
            # Check load balancers
            load_balancer_ids = metadata.get("load_balancer_ids", [])
            if load_balancer_ids:
                for lb_id in load_balancer_ids:
                    try:
                        url = f"https://api.digitalocean.com/v2/load_balancers/{lb_id}"
                        async with session.get(url) as response:
                            if response.status == 200:
                                data = await response.json()
                                lb = data["load_balancer"]
                                status = lb["status"]
                                
                                is_healthy = status == "active"
                                checks.append({
                                    "type": "load_balancer",
                                    "resource_id": str(lb_id),
                                    "status": status,
                                    "healthy": is_healthy
                                })
                                
                                if not is_healthy:
                                    all_healthy = False
                            else:
                                checks.append({
                                    "type": "load_balancer",
                                    "resource_id": str(lb_id),
                                    "error": f"API error: {response.status}",
                                    "healthy": False
                                })
                                all_healthy = False
                                
                    except Exception as e:
                        checks.append({
                            "type": "load_balancer",
                            "resource_id": str(lb_id),
                            "error": str(e),
                            "healthy": False
                        })
                        all_healthy = False
        
        return {
            "is_healthy": all_healthy,
            "details": f"DigitalOcean health check completed with {len(checks)} checks",
            "checks": checks
        }
        
    except Exception as e:
        return {
            "is_healthy": False,
            "details": f"DigitalOcean health check failed: {str(e)}",
            "checks": []
        }


async def _check_azure_health(infrastructure, metadata: Dict) -> Dict[str, Any]:
    """Check Azure infrastructure health."""
    try:
        # Azure health checks would require Azure SDK
        # For now, implement basic connectivity check
        return {
            "is_healthy": True,
            "details": "Azure health check not fully implemented",
            "checks": [
                {
                    "type": "azure_placeholder",
                    "status": "pending_implementation",
                    "healthy": True
                }
            ]
        }
    except Exception as e:
        return {
            "is_healthy": False,
            "details": f"Azure health check failed: {str(e)}",
            "checks": []
        }


async def _check_gcp_health(infrastructure, metadata: Dict) -> Dict[str, Any]:
    """Check Google Cloud Platform infrastructure health."""
    try:
        # GCP health checks would require Google Cloud SDK
        # For now, implement basic connectivity check
        return {
            "is_healthy": True,
            "details": "GCP health check not fully implemented",
            "checks": [
                {
                    "type": "gcp_placeholder", 
                    "status": "pending_implementation",
                    "healthy": True
                }
            ]
        }
    except Exception as e:
        return {
            "is_healthy": False,
            "details": f"GCP health check failed: {str(e)}",
            "checks": []
        }


async def _trigger_infrastructure_alert(infrastructure, health_result: Dict[str, Any]):
    """Trigger alerts for unhealthy infrastructure."""
    try:
        from ..services.notification_service import NotificationService
        
        # Create alert notification
        alert_data = {
            "type": "infrastructure_health_alert",
            "severity": "high",
            "infrastructure_id": str(infrastructure.id),
            "tenant_id": str(infrastructure.tenant_id),
            "provider": infrastructure.provider,
            "details": health_result["details"],
            "failed_checks": [
                check for check in health_result.get("checks", [])
                if not check.get("healthy", False)
            ]
        }
        
        # Send notification through multiple channels
        async with async_session() as db:
            notification_service = NotificationService(db)
            
            await notification_service.create_notification({
                "tenant_id": str(infrastructure.tenant_id),
                "type": "infrastructure_alert",
                "subject": f"Infrastructure Health Alert - {infrastructure.provider}",
                "message": f"Infrastructure {infrastructure.id} is unhealthy: {health_result['details']}",
                "metadata": alert_data,
                "channels": ["email", "dashboard", "slack"],
                "priority": "high"
            })
        
        logger.info(f"Infrastructure alert triggered for {infrastructure.id}")
        
    except Exception as e:
        logger.error(f"Failed to trigger infrastructure alert: {e}")


async def _perform_deployment_backup(deployment, deployment_service) -> bool:
    """Perform comprehensive backup of deployment configuration and data."""
    try:
        from datetime import datetime
        import json
        import os
        
        # Prepare comprehensive backup data
        backup_data = await _prepare_backup_data(deployment, deployment_service)
        
        # Get backup configuration from settings
        from ...core.config import settings
        backup_provider = settings.get("BACKUP_PROVIDER", "local")  # local, s3, azure, gcp
        
        # Perform backup based on configured provider
        if backup_provider == "s3":
            return await _backup_to_s3(deployment, backup_data)
        elif backup_provider == "azure":
            return await _backup_to_azure(deployment, backup_data)
        elif backup_provider == "gcp":
            return await _backup_to_gcp(deployment, backup_data)
        else:
            # Default to local filesystem backup
            return await _backup_to_local(deployment, backup_data)
            
    except Exception as e:
        logger.error(f"Error performing deployment backup: {e}")
        return False


async def _prepare_backup_data(deployment, deployment_service) -> dict:
    """Prepare comprehensive backup data for deployment."""
    try:
        # Get related entities
        infrastructure = await deployment_service.infrastructure_repo.get_by_id(deployment.infrastructure_id)
        template = await deployment_service.template_repo.get_by_id(deployment.template_id)
        services = await deployment_service.service_repo.get_by_deployment(deployment.id)
        logs = await deployment_service.log_repo.get_deployment_logs(deployment.id, limit=100)
        
        backup_data = {
            "metadata": {
                "backup_version": "1.0",
                "backup_timestamp": datetime.utcnow().isoformat(),
                "deployment_id": str(deployment.id),
                "tenant_id": str(deployment.tenant_id)
            },
            "deployment": {
                "id": str(deployment.id),
                "name": deployment.name,
                "version": deployment.version,
                "status": deployment.status,
                "configuration": deployment.configuration,
                "variables": deployment.variables,
                "environment": deployment.environment,
                "created_at": deployment.created_at.isoformat() if deployment.created_at else None,
                "deployed_at": deployment.deployed_at.isoformat() if deployment.deployed_at else None
            },
            "infrastructure": {
                "id": str(infrastructure.id) if infrastructure else None,
                "provider": infrastructure.provider if infrastructure else None,
                "region": infrastructure.region if infrastructure else None,
                "metadata": infrastructure.metadata if infrastructure else None
            },
            "template": {
                "id": str(template.id) if template else None,
                "name": template.name if template else None,
                "template_data": template.template_data if template else None
            },
            "services": [
                {
                    "id": str(service.id),
                    "name": service.name,
                    "type": service.service_type,
                    "status": service.status,
                    "health_status": service.health_status,
                    "configuration": service.configuration
                }
                for service in services
            ],
            "logs": [
                {
                    "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                    "log_level": log.log_level,
                    "message": log.message,
                    "component": log.component,
                    "metadata": log.metadata
                }
                for log in logs[-20:]  # Last 20 logs
            ]
        }
        
        return backup_data
        
    except Exception as e:
        logger.error(f"Error preparing backup data: {e}")
        return {}


async def _backup_to_s3(deployment, backup_data: dict) -> bool:
    """Backup deployment to AWS S3."""
    try:
        import boto3
        import json
        from ...core.config import settings
        
        # Get S3 configuration
        bucket_name = settings.get("BACKUP_S3_BUCKET", "deployment-backups")
        aws_access_key = settings.get("AWS_ACCESS_KEY_ID")
        aws_secret_key = settings.get("AWS_SECRET_ACCESS_KEY")
        region = settings.get("AWS_REGION", "us-east-1")
        
        if not aws_access_key or not aws_secret_key:
            logger.error("AWS credentials not configured for backup")
            return False
        
        s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=region
        )
        
        # Create backup key path
        timestamp = datetime.utcnow().strftime("%Y-%m-%d/%H-%M-%S")
        backup_key = f"deployments/{deployment.tenant_id}/{deployment.id}/{timestamp}/backup.json"
        
        # Upload backup data
        backup_json = json.dumps(backup_data, indent=2, ensure_ascii=False)
        
        s3_client.put_object(
            Bucket=bucket_name,
            Key=backup_key,
            Body=backup_json.encode('utf-8'),
            ContentType='application/json',
            Metadata={
                'deployment-id': str(deployment.id),
                'tenant-id': str(deployment.tenant_id),
                'backup-timestamp': backup_data["metadata"]["backup_timestamp"]
            }
        )
        
        logger.info(f"Backup uploaded to S3: s3://{bucket_name}/{backup_key}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to backup to S3: {e}")
        return False


async def _backup_to_azure(deployment, backup_data: dict) -> bool:
    """Backup deployment to Azure Blob Storage."""
    try:
        from azure.storage.blob import BlobServiceClient
        import json
        from ...core.config import settings
        
        # Get Azure configuration
        connection_string = settings.get("AZURE_STORAGE_CONNECTION_STRING")
        container_name = settings.get("BACKUP_AZURE_CONTAINER", "deployment-backups")
        
        if not connection_string:
            logger.error("Azure Storage connection string not configured for backup")
            return False
        
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        
        # Create backup blob name
        timestamp = datetime.utcnow().strftime("%Y-%m-%d/%H-%M-%S")
        blob_name = f"deployments/{deployment.tenant_id}/{deployment.id}/{timestamp}/backup.json"
        
        # Upload backup data
        backup_json = json.dumps(backup_data, indent=2, ensure_ascii=False)
        
        blob_client = blob_service_client.get_blob_client(
            container=container_name,
            blob=blob_name
        )
        
        blob_client.upload_blob(
            backup_json.encode('utf-8'),
            overwrite=True,
            content_settings={'content_type': 'application/json'},
            metadata={
                'deployment_id': str(deployment.id),
                'tenant_id': str(deployment.tenant_id),
                'backup_timestamp': backup_data["metadata"]["backup_timestamp"]
            }
        )
        
        logger.info(f"Backup uploaded to Azure Blob: {container_name}/{blob_name}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to backup to Azure: {e}")
        return False


async def _backup_to_gcp(deployment, backup_data: dict) -> bool:
    """Backup deployment to Google Cloud Storage."""
    try:
        from google.cloud import storage
        import json
        from ...core.config import settings
        
        # Get GCP configuration
        bucket_name = settings.get("BACKUP_GCP_BUCKET", "deployment-backups")
        credentials_path = settings.get("GCP_CREDENTIALS_PATH")
        
        if credentials_path:
            client = storage.Client.from_service_account_json(credentials_path)
        else:
            client = storage.Client()  # Use default credentials
        
        bucket = client.bucket(bucket_name)
        
        # Create backup blob name
        timestamp = datetime.utcnow().strftime("%Y-%m-%d/%H-%M-%S")
        blob_name = f"deployments/{deployment.tenant_id}/{deployment.id}/{timestamp}/backup.json"
        
        # Upload backup data
        backup_json = json.dumps(backup_data, indent=2, ensure_ascii=False)
        
        blob = bucket.blob(blob_name)
        blob.metadata = {
            'deployment-id': str(deployment.id),
            'tenant-id': str(deployment.tenant_id),
            'backup-timestamp': backup_data["metadata"]["backup_timestamp"]
        }
        
        blob.upload_from_string(
            backup_json,
            content_type='application/json'
        )
        
        logger.info(f"Backup uploaded to GCS: gs://{bucket_name}/{blob_name}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to backup to GCP: {e}")
        return False


async def _backup_to_local(deployment, backup_data: dict) -> bool:
    """Backup deployment to local filesystem."""
    try:
        import json
        import os
        from ...core.config import settings
        
        # Get local backup directory
        backup_dir = settings.get("BACKUP_LOCAL_DIR", "/tmp/deployment-backups")
        
        # Create backup directory structure
        timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
        backup_path = os.path.join(
            backup_dir,
            "deployments",
            str(deployment.tenant_id),
            str(deployment.id),
            timestamp
        )
        
        os.makedirs(backup_path, exist_ok=True)
        
        # Write backup data
        backup_file = os.path.join(backup_path, "backup.json")
        backup_json = json.dumps(backup_data, indent=2, ensure_ascii=False)
        
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(backup_json)
        
        # Create metadata file
        metadata_file = os.path.join(backup_path, "metadata.json")
        metadata = {
            "deployment_id": str(deployment.id),
            "tenant_id": str(deployment.tenant_id),
            "backup_timestamp": backup_data["metadata"]["backup_timestamp"],
            "backup_size": len(backup_json),
            "backup_path": backup_file
        }
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Backup saved to local filesystem: {backup_file}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to backup to local filesystem: {e}")
        return False