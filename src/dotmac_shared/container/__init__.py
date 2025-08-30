"""
Container and Kubernetes integration for DotMac services.
"""

from .lifecycle import ContainerLifecycleManager, container_lifespan

__all__ = ["ContainerLifecycleManager", "container_lifespan"]
