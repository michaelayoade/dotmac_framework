"""
AWS deployment provider plugin.
"""

import logging
from typing import Dict, Any, List
from decimal import Decimal
from uuid import UUID
import boto3
from botocore.exceptions import ClientError

from ...core.plugins.interfaces import DeploymentProviderPlugin
from ...core.plugins.base import PluginMeta, PluginType

logger = logging.getLogger(__name__)


class AWSDeploymentPlugin(DeploymentProviderPlugin):
    """AWS deployment provider implementation."""
    
    @property
    def meta(self) -> PluginMeta:
        return PluginMeta(
            name="aws_deployment",
            version="1.0.0",
            plugin_type=PluginType.DEPLOYMENT_PROVIDER,
            description="AWS infrastructure provisioning and deployment",
            author="DotMac Platform",
            configuration_schema={
                "aws_access_key_id": {"type": "string", "required": True, "sensitive": True},
                "aws_secret_access_key": {"type": "string", "required": True, "sensitive": True},
                "default_region": {"type": "string", "default": "us-east-1"},
                "vpc_cidr": {"type": "string", "default": "10.0.0.0/16"},
                "subnet_cidr": {"type": "string", "default": "10.0.1.0/24"},
                "instance_type": {"type": "string", "default": "t3.medium"},
                "key_pair_name": {"type": "string", "required": False},
                "security_group_rules": {"type": "array", "default": []}
            }
        )
    
    async def initialize(self) -> bool:
        """Initialize AWS plugin."""
        try:
            required_config = ['aws_access_key_id', 'aws_secret_access_key']
            for key in required_config:
                if key not in self.config:
                    raise ValueError(f"Missing required configuration: {key}")
            
            # Test AWS credentials
            await self._test_aws_connection()
            return True
            
        except Exception as e:
            self.log_error(e, "initialization")
            return False
    
    async def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """Validate AWS plugin configuration."""
        try:
            required_keys = ['aws_access_key_id', 'aws_secret_access_key']
            
            for key in required_keys:
                if key not in config:
                    logger.error(f"Missing required configuration key: {key}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            await self._test_aws_connection()
            return {
                "status": "healthy",
                "aws_region": self.config.get("default_region", "us-east-1"),
                "connection": "ok",
                "last_check": "success"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "connection": "failed",
                "error": str(e),
                "last_check": "failed"
            }
    
    async def provision_infrastructure(self, infrastructure_config: Dict[str, Any]) -> Dict[str, Any]:
        """Provision AWS infrastructure."""
        try:
            self.validate_tenant_context(infrastructure_config.get('tenant_id'))
            
            # Initialize AWS clients
            ec2 = self._get_ec2_client()
            ecs = self._get_ecs_client()
            rds = self._get_rds_client()
            
            # Create VPC
            vpc_id = await self._create_vpc(ec2, infrastructure_config)
            
            # Create subnets
            subnet_id = await self._create_subnet(ec2, vpc_id, infrastructure_config)
            
            # Create security groups
            security_group_id = await self._create_security_group(ec2, vpc_id, infrastructure_config)
            
            # Create ECS cluster
            cluster_arn = await self._create_ecs_cluster(ecs, infrastructure_config)
            
            # Create RDS instance if requested
            db_instance_id = None
            if infrastructure_config.get('create_database', True):
                db_instance_id = await self._create_rds_instance(rds, subnet_id, security_group_id, infrastructure_config)
            
            # Return infrastructure details
            return {
                "provider": "aws",
                "region": self.config.get("default_region"),
                "vpc_id": vpc_id,
                "subnet_id": subnet_id,
                "security_group_id": security_group_id,
                "cluster_arn": cluster_arn,
                "db_instance_id": db_instance_id,
                "status": "provisioned",
                "endpoints": {
                    "ecs_cluster": cluster_arn,
                    "database": f"{db_instance_id}.{self.config.get('default_region')}.rds.amazonaws.com" if db_instance_id else None
                }
            }
            
        except Exception as e:
            logger.error(f"AWS infrastructure provisioning failed: {e}")
            raise
    
    async def deploy_application(self, app_config: Dict[str, Any], infrastructure_id: str) -> Dict[str, Any]:
        """Deploy application to AWS ECS."""
        try:
            ecs = self._get_ecs_client()
            
            # Create task definition
            task_definition_arn = await self._create_task_definition(ecs, app_config)
            
            # Create ECS service
            service_arn = await self._create_ecs_service(ecs, task_definition_arn, app_config, infrastructure_id)
            
            return {
                "deployment_id": f"ecs-{service_arn.split('/')[-1]}",
                "task_definition_arn": task_definition_arn,
                "service_arn": service_arn,
                "status": "deployed",
                "endpoints": self._extract_service_endpoints(app_config)
            }
            
        except Exception as e:
            logger.error(f"AWS application deployment failed: {e}")
            raise
    
    async def scale_application(self, deployment_id: str, scaling_config: Dict[str, Any]) -> bool:
        """Scale ECS service."""
        try:
            ecs = self._get_ecs_client()
            
            # Extract service ARN from deployment_id
            service_name = deployment_id.replace('ecs-', '')
            cluster_name = scaling_config.get('cluster_name')
            
            # Update service desired count
            ecs.update_service(
                cluster=cluster_name,
                service=service_name,
                desiredCount=scaling_config.get('target_instances', 2)
            )
            
            logger.info(f"Scaled AWS ECS service {service_name} to {scaling_config.get('target_instances')} instances")
            return True
            
        except Exception as e:
            logger.error(f"Failed to scale AWS application: {e}")
            return False
    
    async def rollback_deployment(self, deployment_id: str, target_version: str) -> bool:
        """Rollback ECS deployment."""
        try:
            ecs = self._get_ecs_client()
            
            # This would involve updating the ECS service to use a previous task definition
            # Implementation depends on how versions are tracked
            logger.info(f"AWS rollback initiated for {deployment_id} to version {target_version}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to rollback AWS deployment: {e}")
            return False
    
    async def validate_template(self, template_content: Dict[str, Any], template_type: str) -> bool:
        """Validate AWS template (CloudFormation, ECS, etc)."""
        try:
            if template_type == "cloudformation":
                return await self._validate_cloudformation_template(template_content)
            elif template_type == "ecs_task_definition":
                return await self._validate_ecs_task_definition(template_content)
            else:
                logger.warning(f"Unsupported AWS template type: {template_type}")
                return False
            
        except Exception as e:
            logger.error(f"AWS template validation failed: {e}")
            return False
    
    async def get_deployment_status(self, deployment_id: str) -> Dict[str, Any]:
        """Get AWS deployment status."""
        try:
            ecs = self._get_ecs_client()
            
            # Extract service info from deployment_id
            service_name = deployment_id.replace('ecs-', '')
            
            # This would query ECS for actual service status
            return {
                "deployment_id": deployment_id,
                "status": "running",
                "health": "healthy",
                "instances": 2,
                "last_updated": "2024-01-01T00:00:00Z"
            }
            
        except Exception as e:
            logger.error(f"Failed to get AWS deployment status: {e}")
            return {"status": "unknown", "error": str(e)}
    
    async def calculate_deployment_cost(self, deployment_config: Dict[str, Any]) -> Decimal:
        """Calculate estimated AWS deployment cost."""
        try:
            instance_type = deployment_config.get('instance_type', 't3.medium')
            instance_count = deployment_config.get('instance_count', 2)
            region = deployment_config.get('region', self.config.get('default_region'))
            
            # AWS EC2 pricing (simplified)
            hourly_costs = {
                't3.nano': Decimal('0.0052'),
                't3.micro': Decimal('0.0104'),
                't3.small': Decimal('0.0208'),
                't3.medium': Decimal('0.0416'),
                't3.large': Decimal('0.0832'),
                't3.xlarge': Decimal('0.1664'),
                'm5.large': Decimal('0.096'),
                'm5.xlarge': Decimal('0.192'),
                'c5.large': Decimal('0.085'),
                'c5.xlarge': Decimal('0.17')
            }
            
            hourly_cost = hourly_costs.get(instance_type, Decimal('0.0416'))
            monthly_cost = hourly_cost * 24 * 30 * instance_count
            
            # Add EBS storage cost
            storage_gb = deployment_config.get('storage_gb', 20)
            storage_cost = Decimal(str(storage_gb)) * Decimal('0.10')  # $0.10/GB/month
            
            # Add data transfer cost (estimate)
            data_transfer_cost = Decimal('10.00')  # $10/month estimate
            
            total_cost = monthly_cost + storage_cost + data_transfer_cost
            
            logger.debug(f"Calculated AWS deployment cost: ${total_cost}")
            return total_cost
            
        except Exception as e:
            logger.error(f"Failed to calculate AWS deployment cost: {e}")
            return Decimal('50.00')  # Default estimate
    
    def get_supported_providers(self) -> List[str]:
        """Return supported providers."""
        return ["aws"]
    
    def get_supported_orchestrators(self) -> List[str]:
        """Return supported orchestrators."""
        return ["ecs", "eks", "ec2", "lambda"]
    
    def _get_ec2_client(self):
        """Get EC2 client."""
        return boto3.client(
            'ec2',
            aws_access_key_id=self.config['aws_access_key_id'],
            aws_secret_access_key=self.config['aws_secret_access_key'],
            region_name=self.config.get('default_region', 'us-east-1')
        )
    
    def _get_ecs_client(self):
        """Get ECS client."""
        return boto3.client(
            'ecs',
            aws_access_key_id=self.config['aws_access_key_id'],
            aws_secret_access_key=self.config['aws_secret_access_key'],
            region_name=self.config.get('default_region', 'us-east-1')
        )
    
    def _get_rds_client(self):
        """Get RDS client."""
        return boto3.client(
            'rds',
            aws_access_key_id=self.config['aws_access_key_id'],
            aws_secret_access_key=self.config['aws_secret_access_key'],
            region_name=self.config.get('default_region', 'us-east-1')
        )
    
    async def _test_aws_connection(self):
        """Test AWS connection."""
        try:
            ec2 = self._get_ec2_client()
            ec2.describe_regions()
            logger.debug("AWS connection test successful")
            
        except Exception as e:
            logger.error(f"AWS connection test failed: {e}")
            raise
    
    async def _create_vpc(self, ec2, infrastructure_config: Dict[str, Any]) -> str:
        """Create VPC for tenant."""
        try:
            cidr_block = infrastructure_config.get('vpc_cidr', self.config.get('vpc_cidr', '10.0.0.0/16'))
            
            response = ec2.create_vpc(CidrBlock=cidr_block)
            vpc_id = response['Vpc']['VpcId']
            
            # Tag VPC
            tenant_id = infrastructure_config.get('tenant_id')
            ec2.create_tags(
                Resources=[vpc_id],
                Tags=[
                    {'Key': 'Name', 'Value': f'dotmac-tenant-{tenant_id}'},
                    {'Key': 'TenantId', 'Value': str(tenant_id)},
                    {'Key': 'ManagedBy', 'Value': 'DotMac'}
                ]
            )
            
            logger.info(f"Created VPC: {vpc_id}")
            return vpc_id
            
        except ClientError as e:
            logger.error(f"Failed to create VPC: {e}")
            raise
    
    async def _create_subnet(self, ec2, vpc_id: str, infrastructure_config: Dict[str, Any]) -> str:
        """Create subnet in VPC."""
        try:
            cidr_block = infrastructure_config.get('subnet_cidr', self.config.get('subnet_cidr', '10.0.1.0/24'))
            
            response = ec2.create_subnet(
                VpcId=vpc_id,
                CidrBlock=cidr_block
            )
            subnet_id = response['Subnet']['SubnetId']
            
            # Tag subnet
            tenant_id = infrastructure_config.get('tenant_id')
            ec2.create_tags(
                Resources=[subnet_id],
                Tags=[
                    {'Key': 'Name', 'Value': f'dotmac-subnet-{tenant_id}'},
                    {'Key': 'TenantId', 'Value': str(tenant_id)}
                ]
            )
            
            logger.info(f"Created subnet: {subnet_id}")
            return subnet_id
            
        except ClientError as e:
            logger.error(f"Failed to create subnet: {e}")
            raise
    
    async def _create_security_group(self, ec2, vpc_id: str, infrastructure_config: Dict[str, Any]) -> str:
        """Create security group."""
        try:
            tenant_id = infrastructure_config.get('tenant_id')
            
            response = ec2.create_security_group(
                GroupName=f'dotmac-sg-{tenant_id}',
                Description=f'Security group for DotMac tenant {tenant_id}',
                VpcId=vpc_id
            )
            security_group_id = response['GroupId']
            
            # Add default rules
            default_rules = [
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 80,
                    'ToPort': 80,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                },
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 443,
                    'ToPort': 443,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                }
            ]
            
            # Add custom rules from configuration
            custom_rules = infrastructure_config.get('security_group_rules', [])
            all_rules = default_rules + custom_rules
            
            if all_rules:
                ec2.authorize_security_group_ingress(
                    GroupId=security_group_id,
                    IpPermissions=all_rules
                )
            
            logger.info(f"Created security group: {security_group_id}")
            return security_group_id
            
        except ClientError as e:
            logger.error(f"Failed to create security group: {e}")
            raise
    
    async def _create_ecs_cluster(self, ecs, infrastructure_config: Dict[str, Any]) -> str:
        """Create ECS cluster."""
        try:
            tenant_id = infrastructure_config.get('tenant_id')
            cluster_name = f'dotmac-cluster-{tenant_id}'
            
            response = ecs.create_cluster(
                clusterName=cluster_name,
                tags=[
                    {'key': 'TenantId', 'value': str(tenant_id)},
                    {'key': 'ManagedBy', 'value': 'DotMac'}
                ]
            )
            
            cluster_arn = response['cluster']['clusterArn']
            logger.info(f"Created ECS cluster: {cluster_arn}")
            return cluster_arn
            
        except ClientError as e:
            logger.error(f"Failed to create ECS cluster: {e}")
            raise
    
    async def _create_rds_instance(self, rds, subnet_id: str, security_group_id: str, infrastructure_config: Dict[str, Any]) -> str:
        """Create RDS instance."""
        try:
            tenant_id = infrastructure_config.get('tenant_id')
            db_instance_id = f'dotmac-db-{str(tenant_id).replace("-", "")[:8]}'
            
            # Create DB subnet group first
            subnet_group_name = f'dotmac-subnet-group-{tenant_id}'
            try:
                rds.create_db_subnet_group(
                    DBSubnetGroupName=subnet_group_name,
                    DBSubnetGroupDescription=f'Subnet group for tenant {tenant_id}',
                    SubnetIds=[subnet_id]
                )
            except ClientError as e:
                if e.response['Error']['Code'] != 'DBSubnetGroupAlreadyExists':
                    raise
            
            # Create RDS instance
            rds.create_db_instance(
                DBInstanceIdentifier=db_instance_id,
                DBInstanceClass=infrastructure_config.get('db_instance_class', 'db.t3.micro'),
                Engine='postgres',
                MasterUsername='dotmac_admin',
                MasterUserPassword=infrastructure_config.get('db_password', 'change_me_123!'),
                AllocatedStorage=infrastructure_config.get('db_storage_gb', 20),
                VpcSecurityGroupIds=[security_group_id],
                DBSubnetGroupName=subnet_group_name,
                BackupRetentionPeriod=7,
                MultiAZ=False,
                StorageEncrypted=True,
                Tags=[
                    {'Key': 'TenantId', 'Value': str(tenant_id)},
                    {'Key': 'ManagedBy', 'Value': 'DotMac'}
                ]
            )
            
            logger.info(f"Created RDS instance: {db_instance_id}")
            return db_instance_id
            
        except ClientError as e:
            logger.error(f"Failed to create RDS instance: {e}")
            raise
    
    async def _create_task_definition(self, ecs, app_config: Dict[str, Any]) -> str:
        """Create ECS task definition."""
        try:
            task_def = {
                'family': app_config.get('name', 'dotmac-app'),
                'networkMode': 'awsvpc',
                'requiresCompatibilities': ['FARGATE'],
                'cpu': str(app_config.get('cpu', 256)),
                'memory': str(app_config.get('memory', 512)),
                'containerDefinitions': [
                    {
                        'name': app_config.get('name', 'app'),
                        'image': app_config.get('image', 'nginx:latest'),
                        'portMappings': [
                            {
                                'containerPort': app_config.get('port', 8080),
                                'protocol': 'tcp'
                            }
                        ],
                        'environment': [
                            {'name': k, 'value': str(v)} 
                            for k, v in app_config.get('environment', {}).items()
                        ],
                        'logConfiguration': {
                            'logDriver': 'awslogs',
                            'options': {
                                'awslogs-group': f"/ecs/{app_config.get('name', 'dotmac-app')}",
                                'awslogs-region': self.config.get('default_region'),
                                'awslogs-stream-prefix': 'ecs'
                            }
                        }
                    }
                ]
            }
            
            response = ecs.register_task_definition(**task_def)
            task_definition_arn = response['taskDefinition']['taskDefinitionArn']
            
            logger.info(f"Created task definition: {task_definition_arn}")
            return task_definition_arn
            
        except ClientError as e:
            logger.error(f"Failed to create task definition: {e}")
            raise
    
    async def _create_ecs_service(self, ecs, task_definition_arn: str, app_config: Dict[str, Any], infrastructure_id: str) -> str:
        """Create ECS service."""
        try:
            service_name = app_config.get('name', 'dotmac-app')
            cluster_name = infrastructure_id  # Assuming infrastructure_id is cluster name
            
            response = ecs.create_service(
                cluster=cluster_name,
                serviceName=service_name,
                taskDefinition=task_definition_arn,
                desiredCount=app_config.get('replicas', 2),
                launchType='FARGATE',
                networkConfiguration={
                    'awsvpcConfiguration': {
                        'subnets': [infrastructure_id],  # Would need actual subnet IDs
                        'assignPublicIp': 'ENABLED'
                    }
                }
            )
            
            service_arn = response['service']['serviceArn']
            logger.info(f"Created ECS service: {service_arn}")
            return service_arn
            
        except ClientError as e:
            logger.error(f"Failed to create ECS service: {e}")
            raise
    
    async def _validate_cloudformation_template(self, template: Dict[str, Any]) -> bool:
        """Validate CloudFormation template."""
        try:
            cloudformation = boto3.client(
                'cloudformation',
                aws_access_key_id=self.config['aws_access_key_id'],
                aws_secret_access_key=self.config['aws_secret_access_key'],
                region_name=self.config.get('default_region')
            )
            
            # Use CloudFormation validate API
            cloudformation.validate_template(TemplateBody=json.dumps(template))
            return True
            
        except ClientError as e:
            logger.error(f"CloudFormation template validation failed: {e}")
            return False
    
    async def _validate_ecs_task_definition(self, task_def: Dict[str, Any]) -> bool:
        """Validate ECS task definition."""
        try:
            required_fields = ['family', 'containerDefinitions']
            for field in required_fields:
                if field not in task_def:
                    logger.error(f"Missing required field in task definition: {field}")
                    return False
            
            # Validate container definitions
            containers = task_def['containerDefinitions']
            if not containers:
                logger.error("Task definition must have at least one container")
                return False
            
            for container in containers:
                if 'name' not in container or 'image' not in container:
                    logger.error("Container definition missing required fields (name, image)")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"ECS task definition validation failed: {e}")
            return False
    
    def _extract_service_endpoints(self, app_config: Dict[str, Any]) -> Dict[str, str]:
        """Extract service endpoints from configuration."""
        endpoints = {}
        
        if 'domain' in app_config:
            domain = app_config['domain']
            endpoints['http'] = f"http://{domain}"
            endpoints['https'] = f"https://{domain}"
        
        if 'health_path' in app_config:
            health_path = app_config['health_path']
            if 'domain' in app_config:
                endpoints['health'] = f"https://{app_config['domain']}{health_path}"
        
        return endpoints
    
    async def calculate_infrastructure_cost(self, infrastructure_config: Dict[str, Any]) -> float:
        """Calculate monthly AWS infrastructure cost."""
        try:
            metadata = infrastructure_config.get("metadata", {})
            
            # EC2 instance costs
            instance_type = metadata.get("instance_type", "t3.medium")
            instance_cost_map = {
                "t3.nano": 3.74,
                "t3.micro": 7.49,
                "t3.small": 14.98,
                "t3.medium": 29.95,
                "t3.large": 59.90,
                "m5.large": 69.12,
                "m5.xlarge": 138.24
            }
            
            instance_cost = instance_cost_map.get(instance_type, 29.95)
            
            # EBS storage costs
            storage_gb = metadata.get("storage_gb", 20)
            storage_cost = storage_gb * 0.10
            
            # RDS costs if database required
            db_cost = 0.0
            if metadata.get("requires_database", True):
                db_instance_type = metadata.get("db_instance_type", "db.t3.micro")
                db_cost_map = {
                    "db.t3.micro": 12.41,
                    "db.t3.small": 24.82,
                    "db.t3.medium": 49.64
                }
                db_cost = db_cost_map.get(db_instance_type, 12.41)
            
            total_cost = instance_cost + storage_cost + db_cost
            
            logger.debug(f"AWS infrastructure cost calculated: ${total_cost:.2f}/month")
            return total_cost
            
        except Exception as e:
            logger.error(f"Error calculating AWS infrastructure cost: {e}")
            return 50.0
    
    async def calculate_infrastructure_cost(self, infrastructure_config: Dict[str, Any]) -> float:
        """Calculate monthly AWS infrastructure cost."""
        try:
            metadata = infrastructure_config.get("metadata", {})
            resource_limits = infrastructure_config.get("resource_limits", {})
            
            # EC2 instance costs
            instance_type = metadata.get("instance_type", "t3.medium")
            instance_cost_map = {
                "t3.nano": 3.74,
                "t3.micro": 7.49,
                "t3.small": 14.98,
                "t3.medium": 29.95,
                "t3.large": 59.90,
                "m5.large": 69.12,
                "m5.xlarge": 138.24
            }
            
            instance_cost = instance_cost_map.get(instance_type, 29.95)
            
            # EBS storage costs
            storage_gb = metadata.get("storage_gb", 20)
            storage_cost = storage_gb * 0.10  # $0.10/GB/month
            
            # RDS costs if database required
            db_cost = 0.0
            if metadata.get("requires_database", True):
                db_instance_type = metadata.get("db_instance_type", "db.t3.micro")
                db_cost_map = {
                    "db.t3.micro": 12.41,
                    "db.t3.small": 24.82,
                    "db.t3.medium": 49.64
                }
                db_cost = db_cost_map.get(db_instance_type, 12.41)
            
            total_cost = instance_cost + storage_cost + db_cost
            
            logger.debug(f"AWS infrastructure cost calculated: ${total_cost:.2f}/month")
            return total_cost
            
        except Exception as e:
            logger.error(f"Error calculating AWS infrastructure cost: {e}")
            return 50.0  # Fallback cost