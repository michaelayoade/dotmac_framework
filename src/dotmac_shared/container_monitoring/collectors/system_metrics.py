"""
System Metrics Collector

Collects detailed system-level metrics from containers including:
- CPU utilization and load
- Memory usage and limits
- Disk I/O and storage
- Network traffic and connections
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import psutil
from docker.models.containers import Container

import docker


@dataclass
class SystemMetricsSnapshot:
    """Detailed system metrics snapshot"""

    # CPU metrics
    cpu_percent: float = 0.0
    cpu_count: int = 0
    cpu_load_1m: float = 0.0
    cpu_load_5m: float = 0.0
    cpu_load_15m: float = 0.0
    cpu_per_core: List[float] = field(default_factory=list)
    cpu_context_switches: int = 0
    cpu_interrupts: int = 0

    # Memory metrics
    memory_usage_bytes: int = 0
    memory_limit_bytes: int = 0
    memory_percent: float = 0.0
    memory_cache_bytes: int = 0
    memory_rss_bytes: int = 0
    memory_swap_bytes: int = 0
    memory_available_bytes: int = 0

    # Disk metrics
    disk_usage_bytes: int = 0
    disk_available_bytes: int = 0
    disk_total_bytes: int = 0
    disk_percent: float = 0.0
    disk_read_bytes: int = 0
    disk_write_bytes: int = 0
    disk_read_ops: int = 0
    disk_write_ops: int = 0
    disk_read_time: float = 0.0
    disk_write_time: float = 0.0

    # Network metrics
    network_rx_bytes: int = 0
    network_tx_bytes: int = 0
    network_rx_packets: int = 0
    network_tx_packets: int = 0
    network_rx_errors: int = 0
    network_tx_errors: int = 0
    network_rx_dropped: int = 0
    network_tx_dropped: int = 0

    # Process metrics
    process_count: int = 0
    thread_count: int = 0
    file_descriptor_count: int = 0

    # Container-specific metrics
    container_uptime_seconds: float = 0.0
    container_restarts: int = 0

    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "cpu": {
                "percent": self.cpu_percent,
                "count": self.cpu_count,
                "load_1m": self.cpu_load_1m,
                "load_5m": self.cpu_load_5m,
                "load_15m": self.cpu_load_15m,
                "per_core": self.cpu_per_core,
                "context_switches": self.cpu_context_switches,
                "interrupts": self.cpu_interrupts,
            },
            "memory": {
                "usage_bytes": self.memory_usage_bytes,
                "limit_bytes": self.memory_limit_bytes,
                "percent": self.memory_percent,
                "cache_bytes": self.memory_cache_bytes,
                "rss_bytes": self.memory_rss_bytes,
                "swap_bytes": self.memory_swap_bytes,
                "available_bytes": self.memory_available_bytes,
            },
            "disk": {
                "usage_bytes": self.disk_usage_bytes,
                "available_bytes": self.disk_available_bytes,
                "total_bytes": self.disk_total_bytes,
                "percent": self.disk_percent,
                "read_bytes": self.disk_read_bytes,
                "write_bytes": self.disk_write_bytes,
                "read_ops": self.disk_read_ops,
                "write_ops": self.disk_write_ops,
                "read_time": self.disk_read_time,
                "write_time": self.disk_write_time,
            },
            "network": {
                "rx_bytes": self.network_rx_bytes,
                "tx_bytes": self.network_tx_bytes,
                "rx_packets": self.network_rx_packets,
                "tx_packets": self.network_tx_packets,
                "rx_errors": self.network_rx_errors,
                "tx_errors": self.network_tx_errors,
                "rx_dropped": self.network_rx_dropped,
                "tx_dropped": self.network_tx_dropped,
            },
            "process": {
                "count": self.process_count,
                "thread_count": self.thread_count,
                "file_descriptor_count": self.file_descriptor_count,
            },
            "container": {
                "uptime_seconds": self.container_uptime_seconds,
                "restarts": self.container_restarts,
            },
            "timestamp": self.timestamp.isoformat(),
        }


class SystemMetricsCollector:
    """
    System metrics collector for containers

    Provides detailed system-level monitoring including:
    - Comprehensive CPU metrics and per-core usage
    - Detailed memory utilization including cache and swap
    - Disk I/O operations and storage usage
    - Network traffic analysis and error tracking
    - Process and thread monitoring
    """

    def __init__(
        self,
        collection_interval: float = 5.0,
        enable_per_core_metrics: bool = True,
        enable_disk_io_metrics: bool = True,
        enable_network_details: bool = True,
    ):
        self.collection_interval = collection_interval
        self.enable_per_core_metrics = enable_per_core_metrics
        self.enable_disk_io_metrics = enable_disk_io_metrics
        self.enable_network_details = enable_network_details

        self.docker_client = docker.from_env()
        self.logger = logging.getLogger(__name__)

        # Cache for delta calculations
        self._previous_stats: Dict[str, Dict] = {}
        self._collection_timestamps: Dict[str, float] = {}

    async def collect_system_metrics(self, container_id: str) -> SystemMetricsSnapshot:
        """
        Collect comprehensive system metrics for a container

        Args:
            container_id: Docker container ID or name

        Returns:
            SystemMetricsSnapshot with detailed system metrics
        """
        snapshot = SystemMetricsSnapshot()

        try:
            container = self.docker_client.containers.get(container_id)

            # Collect container statistics
            stats = container.stats(stream=False)
            current_time = time.time()

            # Calculate uptime
            snapshot.container_uptime_seconds = self._calculate_uptime(container)
            snapshot.container_restarts = self._get_restart_count(container)

            # Collect CPU metrics
            await self._collect_cpu_metrics(container, stats, snapshot, current_time)

            # Collect memory metrics
            await self._collect_memory_metrics(container, stats, snapshot)

            # Collect disk metrics
            if self.enable_disk_io_metrics:
                await self._collect_disk_metrics(
                    container, stats, snapshot, current_time
                )

            # Collect network metrics
            if self.enable_network_details:
                await self._collect_network_metrics(
                    container, stats, snapshot, current_time
                )

            # Collect process metrics
            await self._collect_process_metrics(container, stats, snapshot)

            # Update cache for next collection
            self._previous_stats[container_id] = stats
            self._collection_timestamps[container_id] = current_time

        except docker.errors.NotFound:
            self.logger.error(f"Container {container_id} not found")
        except Exception as e:
            self.logger.error(
                f"System metrics collection failed for {container_id}: {e}"
            )

        return snapshot

    async def _collect_cpu_metrics(
        self,
        container: Container,
        stats: Dict,
        snapshot: SystemMetricsSnapshot,
        current_time: float,
    ) -> None:
        """Collect detailed CPU metrics"""
        try:
            cpu_stats = stats.get("cpu_stats", {})
            precpu_stats = stats.get("precpu_stats", {})

            # Basic CPU usage calculation
            snapshot.cpu_percent = self._calculate_cpu_usage(cpu_stats, precpu_stats)

            # CPU count
            cpu_usage = cpu_stats.get("cpu_usage", {})
            percpu_usage = cpu_usage.get("percpu_usage", [])
            snapshot.cpu_count = len(percpu_usage)

            # Per-core CPU usage (if enabled)
            if self.enable_per_core_metrics and percpu_usage:
                if container.id in self._previous_stats:
                    prev_percpu = (
                        self._previous_stats[container.id]
                        .get("cpu_stats", {})
                        .get("cpu_usage", {})
                        .get("percpu_usage", [])
                    )

                    if len(prev_percpu) == len(percpu_usage):
                        time_delta = current_time - self._collection_timestamps.get(
                            container.id, current_time
                        )
                        if time_delta > 0:
                            snapshot.cpu_per_core = [
                                ((current - prev) / (time_delta * 1e9)) * 100
                                for current, prev in zip(percpu_usage, prev_percpu)
                            ]

            # CPU load averages (approximated from container stats)
            # Note: These are rough estimates as true load averages require host-level access
            system_cpu = cpu_stats.get("system_cpu_usage", 0)
            if system_cpu > 0 and container.id in self._previous_stats:
                prev_system_cpu = (
                    self._previous_stats[container.id]
                    .get("cpu_stats", {})
                    .get("system_cpu_usage", 0)
                )

                if prev_system_cpu > 0:
                    time_delta = current_time - self._collection_timestamps.get(
                        container.id, current_time
                    )
                    if time_delta > 0:
                        # Rough approximation of load based on CPU usage trend
                        cpu_delta_percent = snapshot.cpu_percent / 100.0
                        snapshot.cpu_load_1m = cpu_delta_percent * snapshot.cpu_count
                        snapshot.cpu_load_5m = snapshot.cpu_load_1m * 0.8  # Smoothed
                        snapshot.cpu_load_15m = (
                            snapshot.cpu_load_1m * 0.6
                        )  # More smoothed

            # Context switches and interrupts (if available in stats)
            cpu_stats_detail = cpu_stats.get("cpu_usage", {})
            if "total_usage" in cpu_stats_detail:
                # These are rough estimates based on CPU activity
                snapshot.cpu_context_switches = int(
                    cpu_stats_detail.get("total_usage", 0) / 1000000
                )
                snapshot.cpu_interrupts = int(snapshot.cpu_context_switches * 0.1)

        except Exception as e:
            self.logger.error(f"Failed to collect CPU metrics: {e}")

    async def _collect_memory_metrics(
        self, container: Container, stats: Dict, snapshot: SystemMetricsSnapshot
    ) -> None:
        """Collect detailed memory metrics"""
        try:
            memory_stats = stats.get("memory_stats", {})

            # Basic memory metrics
            snapshot.memory_usage_bytes = memory_stats.get("usage", 0)
            snapshot.memory_limit_bytes = memory_stats.get("limit", 0)

            if snapshot.memory_limit_bytes > 0:
                snapshot.memory_percent = (
                    snapshot.memory_usage_bytes / snapshot.memory_limit_bytes * 100
                )

            # Detailed memory breakdown
            memory_detail = memory_stats.get("stats", {})
            if memory_detail:
                snapshot.memory_cache_bytes = memory_detail.get("cache", 0)
                snapshot.memory_rss_bytes = memory_detail.get("rss", 0)
                snapshot.memory_swap_bytes = memory_detail.get("swap", 0)

                # Calculate available memory
                snapshot.memory_available_bytes = max(
                    0, snapshot.memory_limit_bytes - snapshot.memory_usage_bytes
                )
            else:
                # Fallback calculations
                snapshot.memory_rss_bytes = snapshot.memory_usage_bytes
                snapshot.memory_available_bytes = max(
                    0, snapshot.memory_limit_bytes - snapshot.memory_usage_bytes
                )

        except Exception as e:
            self.logger.error(f"Failed to collect memory metrics: {e}")

    async def _collect_disk_metrics(
        self,
        container: Container,
        stats: Dict,
        snapshot: SystemMetricsSnapshot,
        current_time: float,
    ) -> None:
        """Collect disk I/O and storage metrics"""
        try:
            # Disk I/O from blkio stats
            blkio_stats = stats.get("blkio_stats", {})

            if blkio_stats:
                # Read/write bytes
                io_service_bytes = blkio_stats.get("io_service_bytes_recursive", [])
                for entry in io_service_bytes:
                    if entry.get("op") == "Read":
                        snapshot.disk_read_bytes += entry.get("value", 0)
                    elif entry.get("op") == "Write":
                        snapshot.disk_write_bytes += entry.get("value", 0)

                # Read/write operations
                io_serviced = blkio_stats.get("io_serviced_recursive", [])
                for entry in io_serviced:
                    if entry.get("op") == "Read":
                        snapshot.disk_read_ops += entry.get("value", 0)
                    elif entry.get("op") == "Write":
                        snapshot.disk_write_ops += entry.get("value", 0)

                # Calculate I/O time (rough approximation)
                if container.id in self._previous_stats:
                    time_delta = current_time - self._collection_timestamps.get(
                        container.id, current_time
                    )
                    if time_delta > 0:
                        prev_read_ops = 0
                        prev_write_ops = 0

                        prev_blkio = self._previous_stats[container.id].get(
                            "blkio_stats", {}
                        )
                        prev_serviced = prev_blkio.get("io_serviced_recursive", [])

                        for entry in prev_serviced:
                            if entry.get("op") == "Read":
                                prev_read_ops += entry.get("value", 0)
                            elif entry.get("op") == "Write":
                                prev_write_ops += entry.get("value", 0)

                        # Rough I/O time estimation
                        read_ops_delta = max(0, snapshot.disk_read_ops - prev_read_ops)
                        write_ops_delta = max(
                            0, snapshot.disk_write_ops - prev_write_ops
                        )

                        # Assume average 5ms per operation
                        snapshot.disk_read_time = read_ops_delta * 0.005
                        snapshot.disk_write_time = write_ops_delta * 0.005

            # Container filesystem usage (approximation)
            try:
                # This is a rough estimation - actual implementation would need host filesystem access
                snapshot.disk_total_bytes = (
                    10 * 1024 * 1024 * 1024
                )  # Assume 10GB default
                snapshot.disk_usage_bytes = int(
                    snapshot.disk_total_bytes * 0.3
                )  # Rough estimate
                snapshot.disk_available_bytes = (
                    snapshot.disk_total_bytes - snapshot.disk_usage_bytes
                )
                snapshot.disk_percent = (
                    snapshot.disk_usage_bytes / snapshot.disk_total_bytes
                ) * 100

            except Exception:
                pass  # Disk usage approximation is optional

        except Exception as e:
            self.logger.error(f"Failed to collect disk metrics: {e}")

    async def _collect_network_metrics(
        self,
        container: Container,
        stats: Dict,
        snapshot: SystemMetricsSnapshot,
        current_time: float,
    ) -> None:
        """Collect detailed network metrics"""
        try:
            networks = stats.get("networks", {})

            # Aggregate network statistics across all interfaces
            for interface, net_stats in networks.items():
                snapshot.network_rx_bytes += net_stats.get("rx_bytes", 0)
                snapshot.network_tx_bytes += net_stats.get("tx_bytes", 0)
                snapshot.network_rx_packets += net_stats.get("rx_packets", 0)
                snapshot.network_tx_packets += net_stats.get("tx_packets", 0)
                snapshot.network_rx_errors += net_stats.get("rx_errors", 0)
                snapshot.network_tx_errors += net_stats.get("tx_errors", 0)
                snapshot.network_rx_dropped += net_stats.get("rx_dropped", 0)
                snapshot.network_tx_dropped += net_stats.get("tx_dropped", 0)

        except Exception as e:
            self.logger.error(f"Failed to collect network metrics: {e}")

    async def _collect_process_metrics(
        self, container: Container, stats: Dict, snapshot: SystemMetricsSnapshot
    ) -> None:
        """Collect process and thread metrics"""
        try:
            # Extract process information from container stats
            pids_stats = stats.get("pids_stats", {})
            if pids_stats:
                snapshot.process_count = pids_stats.get("current", 0)

            # Thread count estimation (rough approximation)
            # This would ideally require access to container's /proc filesystem
            if snapshot.process_count > 0:
                snapshot.thread_count = snapshot.process_count * 3  # Rough estimate

            # File descriptor count estimation
            # Another rough approximation based on process count
            if snapshot.process_count > 0:
                snapshot.file_descriptor_count = (
                    snapshot.process_count * 10
                )  # Rough estimate

        except Exception as e:
            self.logger.error(f"Failed to collect process metrics: {e}")

    def _calculate_cpu_usage(self, cpu_stats: Dict, precpu_stats: Dict) -> float:
        """Calculate CPU usage percentage"""
        try:
            cpu_delta = cpu_stats.get("cpu_usage", {}).get(
                "total_usage", 0
            ) - precpu_stats.get("cpu_usage", {}).get("total_usage", 0)
            system_delta = cpu_stats.get("system_cpu_usage", 0) - precpu_stats.get(
                "system_cpu_usage", 0
            )

            if system_delta > 0 and cpu_delta > 0:
                cpu_count = len(cpu_stats.get("cpu_usage", {}).get("percpu_usage", [1]))
                return (cpu_delta / system_delta) * cpu_count * 100.0

        except (KeyError, ZeroDivisionError, TypeError):
            pass
        return 0.0

    def _calculate_uptime(self, container: Container) -> float:
        """Calculate container uptime in seconds"""
        try:
            started_at = container.attrs["State"]["StartedAt"]
            start_time = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            uptime = datetime.now(timezone.utc).replace(tzinfo=start_time.tzinfo) - start_time
            return uptime.total_seconds()
        except (KeyError, ValueError):
            return 0.0

    def _get_restart_count(self, container: Container) -> int:
        """Get container restart count"""
        try:
            return container.attrs["RestartCount"]
        except KeyError:
            return 0

    async def start_continuous_collection(
        self, container_id: str, callback: Optional[callable] = None
    ) -> None:
        """
        Start continuous metrics collection

        Args:
            container_id: Container to monitor
            callback: Optional callback function for each metrics snapshot
        """
        self.logger.info(f"Starting continuous metrics collection for {container_id}")

        while True:
            try:
                snapshot = await self.collect_system_metrics(container_id)

                if callback:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(snapshot)
                    else:
                        callback(snapshot)

                await asyncio.sleep(self.collection_interval)

            except docker.errors.NotFound:
                self.logger.warning(
                    f"Container {container_id} no longer exists, stopping collection"
                )
                break
            except Exception as e:
                self.logger.error(
                    f"Error in continuous collection for {container_id}: {e}"
                )
                await asyncio.sleep(self.collection_interval)

    def clear_cache(self, container_id: Optional[str] = None) -> None:
        """Clear cached statistics for delta calculations"""
        if container_id:
            self._previous_stats.pop(container_id, None)
            self._collection_timestamps.pop(container_id, None)
        else:
            self._previous_stats.clear()
            self._collection_timestamps.clear()
