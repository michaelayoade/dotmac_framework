"""
System-wide Performance Metrics Collection

Comprehensive system metrics collection including:
- CPU usage and performance metrics
- Memory utilization and allocation patterns
- Disk I/O performance
- Network latency and throughput
- Process-level resource monitoring
- Container/K8s resource metrics
"""

import asyncio
import json
import os
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import psutil

from ...api.exception_handlers import standard_exception_handler
from ...core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SystemMetricsSnapshot:
    """Single point-in-time system metrics snapshot"""

    timestamp: datetime

    # CPU metrics
    cpu_percent: float
    cpu_count: int
    cpu_freq_current: float
    cpu_freq_min: float
    cpu_freq_max: float
    load_average_1m: float
    load_average_5m: float
    load_average_15m: float

    # Memory metrics
    memory_total: int
    memory_available: int
    memory_used: int
    memory_free: int
    memory_percent: float
    swap_total: int
    swap_used: int
    swap_free: int
    swap_percent: float

    # Disk I/O metrics
    disk_usage_total: int
    disk_usage_used: int
    disk_usage_free: int
    disk_usage_percent: float
    disk_read_bytes: int
    disk_write_bytes: int
    disk_read_ops: int
    disk_write_ops: int

    # Network metrics
    network_bytes_sent: int
    network_bytes_recv: int
    network_packets_sent: int
    network_packets_recv: int
    network_errors_in: int
    network_errors_out: int

    # Process metrics
    process_count: int
    active_connections: int

    # Additional context
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessMetrics:
    """Process-specific performance metrics"""

    pid: int
    name: str
    cpu_percent: float
    memory_percent: float
    memory_rss: int  # Resident Set Size
    memory_vms: int  # Virtual Memory Size
    num_threads: int
    num_fds: int  # File descriptors (Unix)
    create_time: datetime
    status: str

    # I/O metrics (if available)
    io_read_bytes: Optional[int] = None
    io_write_bytes: Optional[int] = None
    io_read_chars: Optional[int] = None
    io_write_chars: Optional[int] = None


class SystemMetricsCollector:
    """
    Comprehensive system metrics collection with historical tracking.

    Features:
    - Real-time system resource monitoring
    - Historical metrics storage and analysis
    - Process-level monitoring
    - Container and Kubernetes integration
    - Custom metric collection
    - Performance baseline establishment
    """

    def __init__(self, collection_interval: float = 1.0, history_size: int = 3600):
        self.collection_interval = collection_interval
        self.history_size = history_size

        # Metrics storage
        self.metrics_history: deque = deque(maxlen=history_size)
        self.process_metrics: dict[int, ProcessMetrics] = {}

        # Collection state
        self._collecting = False
        self._collection_task: Optional[asyncio.Task] = None
        self._collection_thread: Optional[threading.Thread] = None

        # Baseline metrics
        self.baseline_metrics: Optional[dict[str, float]] = None

        # Custom collectors
        self._custom_collectors: list[Callable] = []

        # Kubernetes/Container detection
        self._is_containerized = self._detect_containerization()
        self._k8s_info = self._detect_kubernetes_info()

    @standard_exception_handler
    async def start_collection(self) -> bool:
        """Start continuous system metrics collection"""
        if self._collecting:
            logger.warning("Metrics collection already running")
            return True

        try:
            self._collecting = True
            self._collection_task = asyncio.create_task(self._collection_loop())

            logger.info(f"Started system metrics collection (interval: {self.collection_interval}s)")
            return True

        except Exception as e:
            logger.error(f"Failed to start metrics collection: {e}")
            self._collecting = False
            return False

    async def stop_collection(self) -> bool:
        """Stop system metrics collection"""
        if not self._collecting:
            return True

        try:
            self._collecting = False

            if self._collection_task:
                self._collection_task.cancel()
                try:
                    await self._collection_task
                except asyncio.CancelledError:
                    pass
                self._collection_task = None

            logger.info("Stopped system metrics collection")
            return True

        except Exception as e:
            logger.error(f"Error stopping metrics collection: {e}")
            return False

    async def _collection_loop(self):
        """Main metrics collection loop"""
        while self._collecting:
            try:
                # Collect system snapshot
                snapshot = await self._collect_system_snapshot()
                self.metrics_history.append(snapshot)

                # Collect process metrics
                await self._collect_process_metrics()

                # Run custom collectors
                for collector in self._custom_collectors:
                    try:
                        await self._run_custom_collector(collector)
                    except Exception as e:
                        logger.debug(f"Custom collector failed: {e}")

                await asyncio.sleep(self.collection_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
                await asyncio.sleep(self.collection_interval)

    async def _collect_system_snapshot(self) -> SystemMetricsSnapshot:
        """Collect comprehensive system metrics snapshot"""

        timestamp = datetime.now(timezone.utc)

        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()

        # Load average (Unix systems)
        try:
            load_avg = os.getloadavg()
            load_average_1m, load_average_5m, load_average_15m = load_avg
        except (OSError, AttributeError):
            load_average_1m = load_average_5m = load_average_15m = 0.0

        # Memory metrics
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()

        # Disk metrics
        disk_usage = psutil.disk_usage("/")
        disk_io = psutil.disk_io_counters()

        # Network metrics
        network_io = psutil.net_io_counters()

        # Process metrics
        process_count = len(psutil.pids())

        # Connection count
        try:
            active_connections = len(psutil.net_connections())
        except (psutil.AccessDenied, OSError):
            active_connections = 0

        # Container/K8s metadata
        metadata = {}
        if self._is_containerized:
            metadata["containerized"] = True
            metadata["container_info"] = self._get_container_info()

        if self._k8s_info:
            metadata["kubernetes"] = self._k8s_info

        return SystemMetricsSnapshot(
            timestamp=timestamp,
            cpu_percent=cpu_percent,
            cpu_count=cpu_count,
            cpu_freq_current=cpu_freq.current if cpu_freq else 0.0,
            cpu_freq_min=cpu_freq.min if cpu_freq else 0.0,
            cpu_freq_max=cpu_freq.max if cpu_freq else 0.0,
            load_average_1m=load_average_1m,
            load_average_5m=load_average_5m,
            load_average_15m=load_average_15m,
            memory_total=memory.total,
            memory_available=memory.available,
            memory_used=memory.used,
            memory_free=memory.free,
            memory_percent=memory.percent,
            swap_total=swap.total,
            swap_used=swap.used,
            swap_free=swap.free,
            swap_percent=swap.percent,
            disk_usage_total=disk_usage.total,
            disk_usage_used=disk_usage.used,
            disk_usage_free=disk_usage.free,
            disk_usage_percent=disk_usage.used / disk_usage.total * 100,
            disk_read_bytes=disk_io.read_bytes if disk_io else 0,
            disk_write_bytes=disk_io.write_bytes if disk_io else 0,
            disk_read_ops=disk_io.read_count if disk_io else 0,
            disk_write_ops=disk_io.write_count if disk_io else 0,
            network_bytes_sent=network_io.bytes_sent,
            network_bytes_recv=network_io.bytes_recv,
            network_packets_sent=network_io.packets_sent,
            network_packets_recv=network_io.packets_recv,
            network_errors_in=network_io.errin,
            network_errors_out=network_io.errout,
            process_count=process_count,
            active_connections=active_connections,
            metadata=metadata,
        )

    async def _collect_process_metrics(self):
        """Collect metrics for current process and related processes"""
        try:
            current_process = psutil.Process()

            # Current process metrics
            self.process_metrics[current_process.pid] = self._get_process_metrics(current_process)

            # Related processes (same name/command)
            try:
                for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                    if proc.info["name"] == current_process.name():
                        try:
                            self.process_metrics[proc.pid] = self._get_process_metrics(proc)
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
            except Exception as e:
                logger.debug(f"Error collecting related process metrics: {e}")

        except Exception as e:
            logger.debug(f"Error collecting process metrics: {e}")

    def _get_process_metrics(self, process: psutil.Process) -> ProcessMetrics:
        """Extract metrics from a process object"""

        try:
            with process.oneshot():
                # Basic process info
                memory_info = process.memory_info()

                # I/O counters (if available)
                io_counters = None
                try:
                    io_counters = process.io_counters()
                except (psutil.AccessDenied, AttributeError):
                    pass

                return ProcessMetrics(
                    pid=process.pid,
                    name=process.name(),
                    cpu_percent=process.cpu_percent(),
                    memory_percent=process.memory_percent(),
                    memory_rss=memory_info.rss,
                    memory_vms=memory_info.vms,
                    num_threads=process.num_threads(),
                    num_fds=process.num_fds() if hasattr(process, "num_fds") else 0,
                    create_time=datetime.fromtimestamp(process.create_time(), tz=timezone.utc),
                    status=process.status(),
                    io_read_bytes=io_counters.read_bytes if io_counters else None,
                    io_write_bytes=io_counters.write_bytes if io_counters else None,
                    io_read_chars=io_counters.read_chars
                    if io_counters and hasattr(io_counters, "read_chars")
                    else None,
                    io_write_chars=io_counters.write_chars
                    if io_counters and hasattr(io_counters, "write_chars")
                    else None,
                )

        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            raise e

    async def _run_custom_collector(self, collector: Callable):
        """Run a custom metrics collector"""
        if asyncio.iscoroutinefunction(collector):
            await collector()
        else:
            collector()

    def add_custom_collector(self, collector: Callable):
        """Add a custom metrics collector function"""
        self._custom_collectors.append(collector)
        logger.info(f"Added custom metrics collector: {collector.__name__}")

    def remove_custom_collector(self, collector: Callable):
        """Remove a custom metrics collector function"""
        if collector in self._custom_collectors:
            self._custom_collectors.remove(collector)
            logger.info(f"Removed custom metrics collector: {collector.__name__}")

    @standard_exception_handler
    def establish_baseline(self, duration_seconds: int = 60) -> dict[str, float]:
        """
        Establish performance baseline by collecting metrics for specified duration.

        Args:
            duration_seconds: How long to collect baseline metrics

        Returns:
            Baseline metrics summary
        """
        logger.info(f"Establishing performance baseline over {duration_seconds} seconds")

        if not self._collecting:
            logger.error("Metrics collection not active - cannot establish baseline")
            return {}

        # Mark start of baseline collection
        baseline_start = len(self.metrics_history)

        # Wait for collection period
        time.sleep(duration_seconds)

        # Calculate baseline from collected metrics
        baseline_metrics = []
        for i in range(baseline_start, len(self.metrics_history)):
            if i < len(self.metrics_history):
                baseline_metrics.append(self.metrics_history[i])

        if not baseline_metrics:
            logger.warning("No metrics collected during baseline period")
            return {}

        # Calculate baseline statistics
        cpu_values = [m.cpu_percent for m in baseline_metrics]
        memory_values = [m.memory_percent for m in baseline_metrics]
        disk_values = [m.disk_usage_percent for m in baseline_metrics]
        load_values = [m.load_average_1m for m in baseline_metrics]

        self.baseline_metrics = {
            "avg_cpu_percent": sum(cpu_values) / len(cpu_values),
            "max_cpu_percent": max(cpu_values),
            "avg_memory_percent": sum(memory_values) / len(memory_values),
            "max_memory_percent": max(memory_values),
            "avg_disk_percent": sum(disk_values) / len(disk_values),
            "max_disk_percent": max(disk_values),
            "avg_load_1m": sum(load_values) / len(load_values),
            "max_load_1m": max(load_values),
            "sample_count": len(baseline_metrics),
            "duration_seconds": duration_seconds,
        }

        logger.info("✅ Performance baseline established")
        logger.info(f"   Avg CPU: {self.baseline_metrics['avg_cpu_percent']:.1f}%")
        logger.info(f"   Avg Memory: {self.baseline_metrics['avg_memory_percent']:.1f}%")
        logger.info(f"   Avg Load: {self.baseline_metrics['avg_load_1m']:.2f}")

        return self.baseline_metrics

    def get_current_metrics(self) -> Optional[SystemMetricsSnapshot]:
        """Get the most recent metrics snapshot"""
        return self.metrics_history[-1] if self.metrics_history else None

    def get_metrics_summary(self, duration_seconds: Optional[int] = None) -> dict[str, Any]:
        """
        Get summary statistics for collected metrics.

        Args:
            duration_seconds: Optional time window for analysis

        Returns:
            Comprehensive metrics summary
        """
        if not self.metrics_history:
            return {"status": "no_data", "message": "No metrics collected"}

        # Determine analysis window
        if duration_seconds:
            cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=duration_seconds)
            relevant_metrics = [m for m in self.metrics_history if m.timestamp >= cutoff_time]
        else:
            relevant_metrics = list(self.metrics_history)

        if not relevant_metrics:
            return {"status": "no_data", "message": "No metrics in specified time window"}

        # Calculate statistics
        cpu_values = [m.cpu_percent for m in relevant_metrics]
        memory_values = [m.memory_percent for m in relevant_metrics]
        disk_values = [m.disk_usage_percent for m in relevant_metrics]
        load_values = [m.load_average_1m for m in relevant_metrics]

        current_metrics = relevant_metrics[-1]

        summary = {
            "collection_period": {
                "start_time": relevant_metrics[0].timestamp.isoformat(),
                "end_time": relevant_metrics[-1].timestamp.isoformat(),
                "duration_seconds": (relevant_metrics[-1].timestamp - relevant_metrics[0].timestamp).total_seconds(),
                "sample_count": len(relevant_metrics),
            },
            "current_snapshot": {
                "timestamp": current_metrics.timestamp.isoformat(),
                "cpu_percent": current_metrics.cpu_percent,
                "memory_percent": current_metrics.memory_percent,
                "disk_percent": current_metrics.disk_usage_percent,
                "load_average_1m": current_metrics.load_average_1m,
                "process_count": current_metrics.process_count,
                "active_connections": current_metrics.active_connections,
            },
            "statistics": {
                "cpu": {
                    "average": sum(cpu_values) / len(cpu_values),
                    "minimum": min(cpu_values),
                    "maximum": max(cpu_values),
                    "current": current_metrics.cpu_percent,
                },
                "memory": {
                    "average": sum(memory_values) / len(memory_values),
                    "minimum": min(memory_values),
                    "maximum": max(memory_values),
                    "current": current_metrics.memory_percent,
                },
                "disk": {
                    "average": sum(disk_values) / len(disk_values),
                    "minimum": min(disk_values),
                    "maximum": max(disk_values),
                    "current": current_metrics.disk_usage_percent,
                },
                "load": {
                    "average": sum(load_values) / len(load_values),
                    "minimum": min(load_values),
                    "maximum": max(load_values),
                    "current": current_metrics.load_average_1m,
                },
            },
        }

        # Add baseline comparison if available
        if self.baseline_metrics:
            summary["baseline_comparison"] = {
                "cpu_vs_baseline": current_metrics.cpu_percent - self.baseline_metrics["avg_cpu_percent"],
                "memory_vs_baseline": current_metrics.memory_percent - self.baseline_metrics["avg_memory_percent"],
                "load_vs_baseline": current_metrics.load_average_1m - self.baseline_metrics["avg_load_1m"],
                "baseline_established": True,
            }
        else:
            summary["baseline_comparison"] = {"baseline_established": False}

        # Add process information
        if self.process_metrics:
            current_process = next(iter(self.process_metrics.values()))
            summary["process_metrics"] = {
                "current_process": {
                    "pid": current_process.pid,
                    "name": current_process.name,
                    "cpu_percent": current_process.cpu_percent,
                    "memory_percent": current_process.memory_percent,
                    "memory_mb": current_process.memory_rss / (1024 * 1024),
                    "threads": current_process.num_threads,
                    "status": current_process.status,
                },
                "total_related_processes": len(self.process_metrics),
            }

        return summary

    def _detect_containerization(self) -> bool:
        """Detect if running in a container"""
        try:
            # Check for common container indicators
            if os.path.exists("/.dockerenv"):
                return True

            # Check cgroup for container indicators
            with open("/proc/1/cgroup") as f:
                cgroup_content = f.read()
                if "docker" in cgroup_content or "containerd" in cgroup_content:
                    return True

            return False
        except (FileNotFoundError, PermissionError):
            return False

    def _detect_kubernetes_info(self) -> Optional[dict[str, str]]:
        """Detect Kubernetes environment information"""
        k8s_info = {}

        # Check for Kubernetes environment variables
        k8s_vars = [
            "KUBERNETES_SERVICE_HOST",
            "KUBERNETES_SERVICE_PORT",
            "POD_NAME",
            "POD_NAMESPACE",
            "NODE_NAME",
            "CLUSTER_NAME",
        ]

        for var in k8s_vars:
            value = os.getenv(var)
            if value:
                k8s_info[var.lower()] = value

        return k8s_info if k8s_info else None

    def _get_container_info(self) -> dict[str, str]:
        """Get container-specific information"""
        container_info = {}

        # Try to get container ID
        try:
            with open("/proc/self/cgroup") as f:
                for line in f:
                    if "docker" in line:
                        container_id = line.split("/")[-1].strip()
                        if container_id:
                            container_info["container_id"] = container_id[:12]  # Short ID
                        break
        except (FileNotFoundError, PermissionError):
            pass

        return container_info

    async def export_metrics(self, filepath: str, format: str = "json") -> bool:
        """
        Export collected metrics to file.

        Args:
            filepath: Output file path
            format: Export format ("json" or "csv")

        Returns:
            True if export successful
        """
        try:
            if not self.metrics_history:
                logger.warning("No metrics to export")
                return False

            if format == "json":
                metrics_data = []
                for snapshot in self.metrics_history:
                    metrics_data.append(
                        {
                            "timestamp": snapshot.timestamp.isoformat(),
                            "cpu_percent": snapshot.cpu_percent,
                            "memory_percent": snapshot.memory_percent,
                            "memory_used_mb": snapshot.memory_used / (1024 * 1024),
                            "disk_percent": snapshot.disk_usage_percent,
                            "load_average_1m": snapshot.load_average_1m,
                            "network_bytes_sent": snapshot.network_bytes_sent,
                            "network_bytes_recv": snapshot.network_bytes_recv,
                            "process_count": snapshot.process_count,
                            "active_connections": snapshot.active_connections,
                            "metadata": snapshot.metadata,
                        }
                    )

                with open(filepath, "w") as f:
                    json.dump(metrics_data, f, indent=2)

            elif format == "csv":
                import csv

                with open(filepath, "w", newline="") as f:
                    writer = csv.writer(f)

                    # Write header
                    writer.writerow(
                        [
                            "timestamp",
                            "cpu_percent",
                            "memory_percent",
                            "memory_used_mb",
                            "disk_percent",
                            "load_average_1m",
                            "network_bytes_sent",
                            "network_bytes_recv",
                            "process_count",
                            "active_connections",
                        ]
                    )

                    # Write data
                    for snapshot in self.metrics_history:
                        writer.writerow(
                            [
                                snapshot.timestamp.isoformat(),
                                snapshot.cpu_percent,
                                snapshot.memory_percent,
                                snapshot.memory_used / (1024 * 1024),
                                snapshot.disk_usage_percent,
                                snapshot.load_average_1m,
                                snapshot.network_bytes_sent,
                                snapshot.network_bytes_recv,
                                snapshot.process_count,
                                snapshot.active_connections,
                            ]
                        )

            logger.info(f"Metrics exported to {filepath}")
            return True

        except Exception as e:
            logger.error(f"Failed to export metrics: {e}")
            return False


# Convenience functions
async def collect_system_metrics(duration_seconds: int = 60, interval: float = 1.0) -> dict[str, Any]:
    """
    Collect system metrics for specified duration and return summary.

    Args:
        duration_seconds: How long to collect metrics
        interval: Collection interval in seconds

    Returns:
        Metrics summary
    """
    collector = SystemMetricsCollector(collection_interval=interval)

    await collector.start_collection()
    await asyncio.sleep(duration_seconds)
    await collector.stop_collection()

    return collector.get_metrics_summary()


def get_instant_system_snapshot() -> SystemMetricsSnapshot:
    """Get immediate system metrics snapshot"""
    collector = SystemMetricsCollector()
    return asyncio.run(collector._collect_system_snapshot())
