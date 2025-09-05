"""
Deployment Automation Module

Provides comprehensive deployment automation capabilities including
container orchestration, blue-green deployments, canary releases,
and CI/CD pipeline integration with health monitoring.
"""

from .automation import (
    ContainerOrchestrator,
    DeploymentAutomation,
    DeploymentAutomationFactory,
    DeploymentResult,
    DeploymentSpec,
    DeploymentStatus,
    DeploymentStrategy,
    DockerOrchestrator,
    HealthCheckConfig,
    HealthCheckType,
    KubernetesOrchestrator,
    ResourceLimits,
    setup_deployment_automation,
)
from .ci_cd import (
    CICDFactory,
    CICDPipeline,
    GitProvider,
    PipelineConfig,
    PipelineRun,
    PipelineStage,
    PipelineStatus,
    WebhookEvent,
    WebhookHandler,
    setup_cicd_pipeline,
)
from .rollout_strategies import (
    FeatureFlagManager,
    IstioTrafficManager,
    LaunchDarklyFeatureFlagManager,
    PrometheusMetricsCollector,
    RolloutConfig,
    RolloutFactory,
    RolloutMetrics,
    RolloutOrchestrator,
    RolloutPhase,
    RolloutState,
    RolloutStrategy,
    TrafficManager,
    TrafficSplit,
    setup_advanced_rollout,
)

__all__ = [
    # Automation
    "DeploymentAutomation",
    "DeploymentAutomationFactory",
    "ContainerOrchestrator",
    "DockerOrchestrator",
    "KubernetesOrchestrator",
    "DeploymentSpec",
    "DeploymentResult",
    "DeploymentStatus",
    "DeploymentStrategy",
    "HealthCheckConfig",
    "HealthCheckType",
    "ResourceLimits",
    "setup_deployment_automation",
    # CI/CD
    "CICDFactory",
    "CICDPipeline",
    "GitProvider",
    "PipelineConfig",
    "PipelineRun",
    "PipelineStage",
    "PipelineStatus",
    "WebhookEvent",
    "WebhookHandler",
    "setup_cicd_pipeline",
    # Rollout Strategies
    "FeatureFlagManager",
    "IstioTrafficManager",
    "LaunchDarklyFeatureFlagManager",
    "PrometheusMetricsCollector",
    "RolloutConfig",
    "RolloutFactory",
    "RolloutMetrics",
    "RolloutOrchestrator",
    "RolloutPhase",
    "RolloutState",
    "RolloutStrategy",
    "TrafficManager",
    "TrafficSplit",
    "setup_advanced_rollout",
]
