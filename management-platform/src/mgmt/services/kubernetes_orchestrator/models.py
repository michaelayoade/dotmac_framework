"""Database models for Kubernetes orchestration service."""

import enum
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import uuid4
from sqlalchemy import Column, String, Boolean, Text, Integer, DateTime, Enum, JSON, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from mgmt.shared.database.base import TenantModel, TimestampMixin


class DeploymentStatus(enum.Enum):
    """Status of tenant deployment."""
    PENDING = "pending"
    CREATING = "creating"
    RUNNING = "running"
    UPDATING = "updating"
    SCALING = "scaling"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"
    DELETING = "deleting"
    DELETED = "deleted"


class ResourceTier(enum.Enum):
    """Resource tier for tenant deployments."""
    MICRO = "micro"      # 1 vCPU, 1GB RAM
    SMALL = "small"      # 2 vCPU, 2GB RAM
    MEDIUM = "medium"    # 4 vCPU, 4GB RAM
    LARGE = "large"      # 8 vCPU, 8GB RAM
    XLARGE = "xlarge"    # 16 vCPU, 16GB RAM
    CUSTOM = "custom"    # Custom resource allocation


class TenantDeployment(TenantModel):
    """Model for tracking tenant Kubernetes deployments."""
    
    __tablename__ = "tenant_deployments"
    __table_args__ = (
        UniqueConstraint('tenant_id', 'deployment_name', name='uq_tenant_deployment_name'),
        Index('idx_tenant_deployment_status', 'status'),
        Index('idx_tenant_deployment_cluster', 'cluster_name'),
    )
    
    # Deployment identification
    deployment_name = Column(String(255), nullable=False, index=True)
    namespace = Column(String(255), nullable=False)
    cluster_name = Column(String(255), nullable=False, default="default")
    
    # Deployment configuration
    isp_framework_image = Column(String(500), nullable=False)
    image_tag = Column(String(100), default="latest", nullable=False)
    
    # Resource allocation
    resource_tier = Column(Enum(ResourceTier), default=ResourceTier.SMALL, nullable=False)
    cpu_request = Column(String(20), default="250m", nullable=False)
    memory_request = Column(String(20), default="512Mi", nullable=False)
    cpu_limit = Column(String(20), default="1000m", nullable=False)
    memory_limit = Column(String(20), default="2Gi", nullable=False)
    storage_size = Column(String(20), default="10Gi", nullable=False)
    
    # Scaling configuration
    min_replicas = Column(Integer, default=1, nullable=False)
    max_replicas = Column(Integer, default=3, nullable=False)
    target_cpu_utilization = Column(Integer, default=70, nullable=False)
    
    # Network configuration
    domain_name = Column(String(255), nullable=True)
    ssl_enabled = Column(Boolean, default=True, nullable=False)
    custom_domains = Column(JSONB, nullable=True)  # Additional domains
    
    # Status and lifecycle
    status = Column(Enum(DeploymentStatus), default=DeploymentStatus.PENDING, nullable=False, index=True)
    desired_state = Column(String(50), default="running", nullable=False)
    
    # Timestamps
    deployed_at = Column(DateTime(timezone=True), nullable=True)
    last_updated = Column(DateTime(timezone=True), nullable=True)
    last_health_check = Column(DateTime(timezone=True), nullable=True)
    
    # Health and monitoring
    health_status = Column(String(20), default="unknown", nullable=False)
    health_message = Column(Text, nullable=True)
    pod_count = Column(Integer, default=0, nullable=False)
    ready_pods = Column(Integer, default=0, nullable=False)
    
    # Configuration and metadata
    environment_vars = Column(JSONB, nullable=True)
    deployment_config = Column(JSONB, nullable=True)  # Full K8s deployment config
    service_config = Column(JSONB, nullable=True)     # Service configuration
    ingress_config = Column(JSONB, nullable=True)     # Ingress configuration
    
    # Backup and disaster recovery
    backup_enabled = Column(Boolean, default=True, nullable=False)
    backup_schedule = Column(String(100), default="0 2 * * *", nullable=False)  # Cron format
    backup_retention_days = Column(Integer, default=30, nullable=False)
    
    # License and billing integration
    license_tier = Column(String(50), default="basic", nullable=False)
    billing_plan_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Error tracking
    error_count = Column(Integer, default=0, nullable=False)
    last_error = Column(Text, nullable=True)
    
    def mark_healthy(self):
        """Mark deployment as healthy."""
        self.health_status = "healthy"
        self.health_message = None
        self.last_health_check = datetime.utcnow()
    
    def mark_unhealthy(self, message: str):
        """Mark deployment as unhealthy with error message."""
        self.health_status = "unhealthy"
        self.health_message = message
        self.last_health_check = datetime.utcnow()
        self.error_count += 1
    
    def update_pod_status(self, total_pods: int, ready_pods: int):
        """Update pod count information."""
        self.pod_count = total_pods
        self.ready_pods = ready_pods
        
        # Update health based on pod readiness
        if ready_pods == 0:
            self.mark_unhealthy("No pods are ready")
        elif ready_pods < total_pods:
            self.health_status = "degraded"
            self.health_message = f"Only {ready_pods}/{total_pods} pods are ready"
        else:
            self.mark_healthy()


class ScalingPolicy(TenantModel):
    """Model for tenant-specific scaling policies."""
    
    __tablename__ = "scaling_policies"
    __table_args__ = (
        UniqueConstraint('tenant_id', 'deployment_id', name='uq_tenant_scaling_policy'),
        Index('idx_scaling_policy_deployment', 'deployment_id'),
    )
    
    # Reference to deployment
    deployment_id = Column(UUID(as_uuid=True), nullable=False)
    
    # Scaling parameters
    min_replicas = Column(Integer, default=1, nullable=False)
    max_replicas = Column(Integer, default=10, nullable=False)
    
    # CPU-based scaling
    target_cpu_percentage = Column(Integer, default=70, nullable=False)
    cpu_scale_up_threshold = Column(Integer, default=80, nullable=False)
    cpu_scale_down_threshold = Column(Integer, default=30, nullable=False)
    
    # Memory-based scaling
    target_memory_percentage = Column(Integer, default=80, nullable=False)
    memory_scale_up_threshold = Column(Integer, default=85, nullable=False)
    memory_scale_down_threshold = Column(Integer, default=40, nullable=False)
    
    # Custom metrics
    custom_metrics = Column(JSONB, nullable=True)
    
    # Scaling behavior
    scale_up_stabilization_window = Column(Integer, default=60, nullable=False)  # seconds
    scale_down_stabilization_window = Column(Integer, default=300, nullable=False)  # seconds
    scale_up_pods_per_minute = Column(Integer, default=2, nullable=False)
    scale_down_pods_per_minute = Column(Integer, default=1, nullable=False)
    
    # Time-based scaling
    schedule_enabled = Column(Boolean, default=False, nullable=False)
    schedule_config = Column(JSONB, nullable=True)  # Cron-like scheduling
    
    # Cost optimization
    cost_optimization_enabled = Column(Boolean, default=True, nullable=False)
    max_cost_per_hour = Column(Integer, nullable=True)  # cents per hour


class DeploymentEvent(TenantModel):
    """Model for tracking deployment events and operations."""
    
    __tablename__ = "deployment_events"
    __table_args__ = (
        Index('idx_deployment_event_deployment', 'deployment_id'),
        Index('idx_deployment_event_timestamp', 'created_at'),
        Index('idx_deployment_event_type', 'event_type'),
    )
    
    # Reference to deployment
    deployment_id = Column(UUID(as_uuid=True), nullable=False)
    
    # Event details
    event_type = Column(String(50), nullable=False, index=True)  # deploy, scale, update, delete, health_check
    event_status = Column(String(20), nullable=False)           # success, failed, in_progress
    event_message = Column(Text, nullable=False)
    
    # Event data
    event_data = Column(JSONB, nullable=True)  # Additional structured data
    
    # User and context
    triggered_by_user_id = Column(UUID(as_uuid=True), nullable=True)
    automation_triggered = Column(Boolean, default=False, nullable=False)
    
    # Performance tracking
    duration_seconds = Column(Integer, nullable=True)
    resource_usage_before = Column(JSONB, nullable=True)
    resource_usage_after = Column(JSONB, nullable=True)
    
    # Error details
    error_details = Column(JSONB, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    
    # Correlation
    correlation_id = Column(String(255), nullable=True)
    parent_event_id = Column(UUID(as_uuid=True), nullable=True)


class ClusterInfo(TenantModel):
    """Model for tracking Kubernetes cluster information."""
    
    __tablename__ = "cluster_info"
    __table_args__ = (
        UniqueConstraint('tenant_id', 'cluster_name', name='uq_tenant_cluster_name'),
        Index('idx_cluster_status', 'status'),
    )
    
    # Cluster identification
    cluster_name = Column(String(255), nullable=False, index=True)
    cluster_endpoint = Column(String(500), nullable=False)
    cluster_region = Column(String(100), nullable=True)
    cluster_provider = Column(String(50), nullable=False)  # aws, gcp, azure, on-premise
    
    # Cluster status
    status = Column(String(20), default="unknown", nullable=False, index=True)
    kubernetes_version = Column(String(50), nullable=True)
    node_count = Column(Integer, default=0, nullable=False)
    
    # Resource capacity
    total_cpu_cores = Column(Integer, nullable=True)
    total_memory_gb = Column(Integer, nullable=True)
    total_storage_gb = Column(Integer, nullable=True)
    
    # Usage statistics
    cpu_usage_percentage = Column(Integer, nullable=True)
    memory_usage_percentage = Column(Integer, nullable=True)
    storage_usage_percentage = Column(Integer, nullable=True)
    
    # Cost tracking
    estimated_hourly_cost = Column(Integer, nullable=True)  # cents per hour
    
    # Configuration
    cluster_config = Column(JSONB, nullable=True)
    
    # Monitoring
    last_health_check = Column(DateTime(timezone=True), nullable=True)
    health_message = Column(Text, nullable=True)