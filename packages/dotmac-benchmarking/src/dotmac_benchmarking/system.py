"""
System metrics collection utilities.

Requires the 'system' extra: pip install dotmac-benchmarking[system]
"""

import time
from typing import Any

try:
    import psutil
    SYSTEM_AVAILABLE = True
except ImportError:
    psutil = None
    SYSTEM_AVAILABLE = False


def snapshot() -> dict[str, Any]:
    """
    Take a snapshot of current system metrics.
    
    Returns:
        Dictionary with CPU, memory, disk, and network metrics
        
    Raises:
        ImportError: If psutil is not installed
        
    Example:
        from dotmac_benchmarking.system import snapshot
        
        metrics = snapshot()
        print(f"CPU: {metrics['cpu_percent']}%")
        print(f"Memory: {metrics['memory_percent']}%")
        print(f"Disk: {metrics['disk_usage']}%")
    """
    if not SYSTEM_AVAILABLE:
        raise ImportError(
            "System monitoring requires psutil. Install with: pip install dotmac-benchmarking[system]"
        )

    # CPU metrics
    cpu_percent = psutil.cpu_percent(interval=0.1)
    cpu_count = psutil.cpu_count()
    cpu_count_logical = psutil.cpu_count(logical=True)

    # Memory metrics
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()

    # Disk metrics (for root filesystem)
    disk = psutil.disk_usage('/')

    # Network metrics (aggregate across all interfaces)
    network = psutil.net_io_counters()

    # Load averages (Unix-like systems only)
    load_avg = None
    try:
        load_avg = psutil.getloadavg()
    except (AttributeError, OSError):
        # Not available on Windows
        pass

    return {
        # CPU metrics
        "cpu_percent": cpu_percent,
        "cpu_count_physical": cpu_count,
        "cpu_count_logical": cpu_count_logical,
        "load_avg_1m": load_avg[0] if load_avg else None,
        "load_avg_5m": load_avg[1] if load_avg else None,
        "load_avg_15m": load_avg[2] if load_avg else None,

        # Memory metrics
        "memory_total": memory.total,
        "memory_available": memory.available,
        "memory_used": memory.used,
        "memory_percent": memory.percent,
        "swap_total": swap.total,
        "swap_used": swap.used,
        "swap_percent": swap.percent,

        # Disk metrics
        "disk_total": disk.total,
        "disk_used": disk.used,
        "disk_free": disk.free,
        "disk_usage": (disk.used / disk.total) * 100,

        # Network metrics
        "network_bytes_sent": network.bytes_sent,
        "network_bytes_recv": network.bytes_recv,
        "network_packets_sent": network.packets_sent,
        "network_packets_recv": network.packets_recv,

        # Metadata
        "timestamp": time.time(),
        "boot_time": psutil.boot_time(),
    }


def get_process_info(pid: int | None = None) -> dict[str, Any]:
    """
    Get information about a specific process.
    
    Args:
        pid: Process ID (uses current process if None)
        
    Returns:
        Dictionary with process metrics
        
    Raises:
        ImportError: If psutil is not installed
        psutil.NoSuchProcess: If process doesn't exist
    """
    if not SYSTEM_AVAILABLE:
        raise ImportError(
            "System monitoring requires psutil. Install with: pip install dotmac-benchmarking[system]"
        )

    if pid is None:
        process = psutil.Process()
    else:
        process = psutil.Process(pid)

    # Process info
    info = process.as_dict([
        'pid', 'name', 'status', 'create_time',
        'cpu_percent', 'memory_percent', 'memory_info',
        'num_threads', 'num_fds'
    ])

    # Add memory details
    memory_info = info.get('memory_info')
    if memory_info:
        info['memory_rss'] = memory_info.rss
        info['memory_vms'] = memory_info.vms

    info['timestamp'] = time.time()

    return info


class SystemMonitor:
    """
    Continuous system monitoring with history tracking.
    """

    def __init__(self, history_size: int = 100) -> None:
        """
        Initialize system monitor.
        
        Args:
            history_size: Maximum number of snapshots to keep in history
        """
        if not SYSTEM_AVAILABLE:
            raise ImportError(
                "System monitoring requires psutil. Install with: pip install dotmac-benchmarking[system]"
            )

        self.history_size = history_size
        self.history: list[dict[str, Any]] = []

    def take_snapshot(self) -> dict[str, Any]:
        """
        Take a system snapshot and add to history.
        
        Returns:
            Current system metrics
        """
        snapshot_data = snapshot()

        self.history.append(snapshot_data)

        # Trim history if needed
        if len(self.history) > self.history_size:
            self.history.pop(0)

        return snapshot_data

    def get_history(self) -> list[dict[str, Any]]:
        """Get all historical snapshots."""
        return self.history.copy()

    def get_averages(self, window: int | None = None) -> dict[str, float]:
        """
        Calculate averages over a window of snapshots.
        
        Args:
            window: Number of recent snapshots to average (all if None)
            
        Returns:
            Dictionary with averaged metrics
        """
        if not self.history:
            return {}

        snapshots = self.history[-window:] if window else self.history

        # Calculate averages for numeric fields
        numeric_fields = [
            'cpu_percent', 'memory_percent', 'swap_percent', 'disk_usage'
        ]

        averages = {}
        for field in numeric_fields:
            values = [s[field] for s in snapshots if field in s and s[field] is not None]
            if values:
                averages[f'avg_{field}'] = sum(values) / len(values)

        return averages

    def clear_history(self) -> None:
        """Clear all historical snapshots."""
        self.history.clear()
