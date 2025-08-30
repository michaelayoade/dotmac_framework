# DotMac Container Monitoring & Health Service

Comprehensive health monitoring and lifecycle management for ISP containers post-provisioning.

## Features

- **Container Health Monitoring**: CPU, memory, disk usage monitoring
- **Application Health Checks**: ISP framework endpoint monitoring
- **Database Connectivity Monitoring**: Per-container database health
- **Auto-scaling Recommendations**: Based on customer growth patterns
- **Container Lifecycle Management**: Start, stop, restart, scale operations

## Installation

```bash
pip install dotmac-container-monitoring
```

## Quick Start

```python
import asyncio
from dotmac_shared.container_monitoring import (
    monitor_container_health,
    collect_performance_metrics,
    recommend_scaling,
    manage_container_lifecycle,
    LifecycleAction
)

async def main():
    # Monitor container health
    health_report = await monitor_container_health("isp_tenant_123")
    print(f"Container health: {health_report.status}")

    # Collect performance metrics
    metrics = await collect_performance_metrics("isp_tenant_123")
    print(f"CPU Usage: {metrics.cpu_percent}%")

    # Get scaling recommendations
    recommendation = await recommend_scaling("tenant_uuid", metrics)
    print(f"Scaling recommendation: {recommendation.action}")

    # Manage container lifecycle
    success = await manage_container_lifecycle(
        "isp_tenant_123",
        LifecycleAction.RESTART
    )
    print(f"Restart successful: {success}")

asyncio.run(main())
```

## Core Components

### Health Monitor

Monitor container and application health with configurable checks and thresholds.

### Metrics Collector

Collect comprehensive performance metrics including system, application, and database metrics.

### Scaling Advisor

Analyze metrics and provide intelligent auto-scaling recommendations based on usage patterns.

### Lifecycle Manager

Manage container lifecycle operations with proper event tracking and error handling.

## Configuration

```python
from dotmac_shared.container_monitoring import ContainerHealthMonitor

monitor = ContainerHealthMonitor(
    check_interval=30,  # seconds
    health_threshold=0.8,
    cpu_threshold=80.0,
    memory_threshold=85.0,
    disk_threshold=90.0
)
```

## Contributing

See the main DotMac Framework contribution guidelines.
