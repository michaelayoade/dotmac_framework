"""
Comprehensive Task Monitoring and Progress Tracking System

Provides real-time monitoring and analytics for task execution:
- Task execution metrics and performance tracking
- Real-time progress monitoring with WebSocket support
- Health checks and alerting
- Resource usage monitoring
- Historical data analysis and reporting
- SLA monitoring and breach detection
"""

import asyncio
import json
import statistics
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Callable, Union
from dataclasses import dataclass, field
from enum import Enum

from redis.asyncio import Redis as AsyncRedis

from .engine import TaskStatus, TaskPriority, TaskError
from .queue import RedisTaskQueue
from dotmac_shared.core.logging import get_logger
from dotmac_shared.observability.logging import get_logger as get_observability_logger

logger = get_logger(__name__)
observability_logger = get_observability_logger(__name__)


class AlertLevel(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MetricType(str, Enum):
    """Types of metrics tracked."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class TaskMetrics:
    """Comprehensive task execution metrics."""
    # Execution counts
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    cancelled_tasks: int = 0
    timeout_tasks: int = 0
    
    # Performance metrics
    total_execution_time: float = 0.0
    min_execution_time: float = float('inf')
    max_execution_time: float = 0.0
    avg_execution_time: float = 0.0
    
    # Queue metrics
    current_queue_size: int = 0
    max_queue_size: int = 0
    avg_queue_wait_time: float = 0.0
    
    # Resource metrics
    peak_memory_usage: float = 0.0
    avg_cpu_usage: float = 0.0
    
    # Rate metrics
    tasks_per_minute: float = 0.0
    tasks_per_hour: float = 0.0
    
    # Error rates
    error_rate: float = 0.0
    timeout_rate: float = 0.0
    success_rate: float = 0.0
    
    # SLA metrics
    sla_breaches: int = 0
    sla_compliance_rate: float = 0.0
    
    # Timestamps
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    measurement_window: timedelta = field(default=timedelta(hours=1))

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            'total_tasks': self.total_tasks,
            'completed_tasks': self.completed_tasks,
            'failed_tasks': self.failed_tasks,
            'cancelled_tasks': self.cancelled_tasks,
            'timeout_tasks': self.timeout_tasks,
            'total_execution_time': self.total_execution_time,
            'min_execution_time': self.min_execution_time if self.min_execution_time != float('inf') else 0,
            'max_execution_time': self.max_execution_time,
            'avg_execution_time': self.avg_execution_time,
            'current_queue_size': self.current_queue_size,
            'max_queue_size': self.max_queue_size,
            'avg_queue_wait_time': self.avg_queue_wait_time,
            'peak_memory_usage': self.peak_memory_usage,
            'avg_cpu_usage': self.avg_cpu_usage,
            'tasks_per_minute': self.tasks_per_minute,
            'tasks_per_hour': self.tasks_per_hour,
            'error_rate': self.error_rate,
            'timeout_rate': self.timeout_rate,
            'success_rate': self.success_rate,
            'sla_breaches': self.sla_breaches,
            'sla_compliance_rate': self.sla_compliance_rate,
            'last_updated': self.last_updated.isoformat(),
            'measurement_window_seconds': int(self.measurement_window.total_seconds()),
        }

    def update_execution_metrics(self, execution_time: float, status: TaskStatus):
        """Update metrics with task execution data."""
        self.total_tasks += 1
        
        if status == TaskStatus.COMPLETED:
            self.completed_tasks += 1
        elif status == TaskStatus.FAILED:
            self.failed_tasks += 1
        elif status == TaskStatus.CANCELLED:
            self.cancelled_tasks += 1
        elif status == TaskStatus.TIMEOUT:
            self.timeout_tasks += 1
        
        # Update execution time metrics
        self.total_execution_time += execution_time
        self.min_execution_time = min(self.min_execution_time, execution_time)
        self.max_execution_time = max(self.max_execution_time, execution_time)
        
        if self.total_tasks > 0:
            self.avg_execution_time = self.total_execution_time / self.total_tasks
            self.success_rate = self.completed_tasks / self.total_tasks
            self.error_rate = self.failed_tasks / self.total_tasks
            self.timeout_rate = self.timeout_tasks / self.total_tasks
        
        self.last_updated = datetime.now(timezone.utc)


@dataclass
class Alert:
    """System alert with metadata."""
    alert_id: str
    level: AlertLevel
    title: str
    message: str
    source: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            'alert_id': self.alert_id,
            'level': self.level.value,
            'title': self.title,
            'message': self.message,
            'source': self.source,
            'created_at': self.created_at.isoformat(),
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'metadata': self.metadata,
            'is_resolved': self.resolved_at is not None,
        }


class TaskMonitor:
    """
    Comprehensive task monitoring system with real-time analytics.
    
    Features:
    - Real-time task execution monitoring
    - Performance metrics collection and analysis
    - Health check monitoring
    - Alert generation and management
    - Historical data retention and analysis
    - SLA monitoring and compliance tracking
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        monitor_id: str = None,
        key_prefix: str = "dotmac_monitor",
        metrics_retention_days: int = 30,
        alert_retention_days: int = 7,
    ):
        self.redis_url = redis_url
        self.monitor_id = monitor_id or f"monitor-{int(time.time())}"
        self.key_prefix = key_prefix
        self.metrics_retention_days = metrics_retention_days
        self.alert_retention_days = alert_retention_days
        
        # Redis connection
        self._redis: Optional[AsyncRedis] = None
        self._task_queue: Optional[RedisTaskQueue] = None
        
        # Monitor state
        self._is_running = False
        self._metrics_cache: Dict[str, TaskMetrics] = {}
        self._alert_handlers: List[Callable[[Alert], None]] = []
        self._active_alerts: Dict[str, Alert] = {}
        
        # Real-time data
        self._execution_history: deque = deque(maxlen=1000)  # Last 1000 executions
        self._queue_size_history: deque = deque(maxlen=100)  # Last 100 queue size measurements
        
        # Background tasks
        self._monitoring_task: Optional[asyncio.Task] = None
        self._metrics_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        
        # SLA configuration
        self._sla_thresholds = {
            'max_execution_time': 300.0,  # 5 minutes
            'max_queue_wait_time': 60.0,   # 1 minute
            'min_success_rate': 0.95,      # 95%
            'max_error_rate': 0.05,        # 5%
        }

    async def initialize(self):
        """Initialize monitor and Redis connections."""
        try:
            # Initialize Redis connection
            self._redis = AsyncRedis.from_url(
                self.redis_url,
                encoding='utf-8',
                decode_responses=True,
                socket_connect_timeout=10,
                socket_timeout=30,
                retry_on_timeout=True,
                max_connections=30
            )
            
            await self._redis.ping()
            
            # Initialize task queue for monitoring
            self._task_queue = RedisTaskQueue(self.redis_url)
            await self._task_queue.initialize()
            
            # Load existing metrics and alerts
            await self._load_cached_metrics()
            await self._load_active_alerts()
            
            logger.info(f"Task monitor initialized", extra={
                'monitor_id': self.monitor_id,
                'cached_metrics': len(self._metrics_cache),
                'active_alerts': len(self._active_alerts)
            })
            
        except Exception as e:
            logger.error(f"Failed to initialize task monitor: {e}")
            raise TaskError(f"Monitor initialization failed: {e}")

    async def start(self):
        """Start the monitoring system."""
        if self._is_running:
            return
        
        self._is_running = True
        
        # Start background monitoring tasks
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self._metrics_task = asyncio.create_task(self._metrics_calculation_loop())
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        logger.info(f"Task monitor started", extra={'monitor_id': self.monitor_id})

    async def stop(self):
        """Stop the monitoring system."""
        logger.info("Stopping task monitor")
        
        self._is_running = False
        
        # Cancel background tasks
        tasks = [self._monitoring_task, self._metrics_task, self._cleanup_task]
        for task in tasks:
            if task:
                task.cancel()
        
        # Wait for tasks to complete
        if tasks:
            await asyncio.gather(*[t for t in tasks if t], return_exceptions=True)
        
        # Persist final state
        await self._persist_metrics()
        await self._persist_alerts()
        
        # Close connections
        if self._task_queue:
            await self._task_queue.close()
        if self._redis:
            await self._redis.close()
        
        logger.info("Task monitor stopped")

    async def record_task_execution(
        self,
        task_id: str,
        status: TaskStatus,
        execution_time: float,
        queue_name: str = "default",
        tenant_id: Optional[str] = None,
        metadata: Dict[str, Any] = None
    ):
        """Record task execution for monitoring and analytics."""
        try:
            # Create execution record
            execution_record = {
                'task_id': task_id,
                'status': status.value,
                'execution_time': execution_time,
                'queue_name': queue_name,
                'tenant_id': tenant_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'metadata': metadata or {}
            }
            
            # Add to history
            self._execution_history.append(execution_record)
            
            # Update metrics cache
            metrics_key = f"{queue_name}:{tenant_id or 'global'}"
            if metrics_key not in self._metrics_cache:
                self._metrics_cache[metrics_key] = TaskMetrics()
            
            self._metrics_cache[metrics_key].update_execution_metrics(execution_time, status)
            
            # Store execution record in Redis with TTL
            record_key = f"{self.key_prefix}:execution:{task_id}"
            await self._redis.set(
                record_key,
                json.dumps(execution_record),
                ex=86400 * self.metrics_retention_days
            )
            
            # Check for SLA violations and generate alerts
            await self._check_sla_violations(execution_record, metrics_key)
            
        except Exception as e:
            logger.error(f"Failed to record task execution: {e}")

    async def record_queue_size(self, queue_name: str, size: int, tenant_id: Optional[str] = None):
        """Record queue size for monitoring."""
        try:
            queue_record = {
                'queue_name': queue_name,
                'tenant_id': tenant_id,
                'size': size,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            self._queue_size_history.append(queue_record)
            
            # Update metrics
            metrics_key = f"{queue_name}:{tenant_id or 'global'}"
            if metrics_key not in self._metrics_cache:
                self._metrics_cache[metrics_key] = TaskMetrics()
            
            metrics = self._metrics_cache[metrics_key]
            metrics.current_queue_size = size
            metrics.max_queue_size = max(metrics.max_queue_size, size)
            
            # Check for queue size alerts
            if size > 1000:  # Alert threshold
                await self._create_alert(
                    AlertLevel.WARNING,
                    f"High Queue Size: {queue_name}",
                    f"Queue {queue_name} has {size} pending tasks",
                    source=f"queue_monitor:{queue_name}",
                    metadata={'queue_name': queue_name, 'size': size}
                )
            
        except Exception as e:
            logger.error(f"Failed to record queue size: {e}")

    async def get_metrics(
        self,
        queue_name: str = "default",
        tenant_id: Optional[str] = None,
        time_range: Optional[timedelta] = None
    ) -> TaskMetrics:
        """Get comprehensive task metrics for analysis."""
        metrics_key = f"{queue_name}:{tenant_id or 'global'}"
        
        if metrics_key in self._metrics_cache:
            return self._metrics_cache[metrics_key]
        
        # Return empty metrics if not cached
        return TaskMetrics()

    async def get_real_time_stats(self) -> Dict[str, Any]:
        """Get real-time system statistics."""
        try:
            # Calculate stats from recent execution history
            recent_executions = [
                record for record in self._execution_history
                if (datetime.now(timezone.utc) - datetime.fromisoformat(record['timestamp'])).total_seconds() < 3600
            ]
            
            total_executions = len(recent_executions)
            if total_executions == 0:
                return {'total_executions': 0, 'executions_per_minute': 0}
            
            # Calculate success rate
            successful = sum(1 for r in recent_executions if r['status'] == 'completed')
            success_rate = successful / total_executions if total_executions > 0 else 0
            
            # Calculate average execution time
            execution_times = [r['execution_time'] for r in recent_executions]
            avg_execution_time = statistics.mean(execution_times) if execution_times else 0
            
            # Calculate executions per minute
            executions_per_minute = total_executions / 60 if total_executions > 0 else 0
            
            # Get current queue sizes
            current_queue_sizes = {}
            for record in self._queue_size_history:
                if (datetime.now(timezone.utc) - datetime.fromisoformat(record['timestamp'])).total_seconds() < 300:  # Last 5 minutes
                    queue_key = f"{record['queue_name']}:{record.get('tenant_id', 'global')}"
                    current_queue_sizes[queue_key] = record['size']
            
            return {
                'total_executions': total_executions,
                'success_rate': success_rate,
                'avg_execution_time': avg_execution_time,
                'executions_per_minute': executions_per_minute,
                'current_queue_sizes': current_queue_sizes,
                'active_alerts': len([a for a in self._active_alerts.values() if not a.resolved_at]),
                'system_health': self._calculate_system_health(),
                'timestamp': datetime.now(timezone.utc).isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Failed to get real-time stats: {e}")
            return {}

    async def get_performance_report(
        self,
        time_range: timedelta = timedelta(hours=24)
    ) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        try:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - time_range
            
            # Filter executions within time range
            filtered_executions = [
                record for record in self._execution_history
                if start_time <= datetime.fromisoformat(record['timestamp']) <= end_time
            ]
            
            if not filtered_executions:
                return {'message': 'No data available for the specified time range'}
            
            # Calculate comprehensive metrics
            total_tasks = len(filtered_executions)
            completed_tasks = sum(1 for r in filtered_executions if r['status'] == 'completed')
            failed_tasks = sum(1 for r in filtered_executions if r['status'] == 'failed')
            cancelled_tasks = sum(1 for r in filtered_executions if r['status'] == 'cancelled')
            timeout_tasks = sum(1 for r in filtered_executions if r['status'] == 'timeout')
            
            # Execution time analysis
            execution_times = [r['execution_time'] for r in filtered_executions]
            
            # Queue analysis
            queue_distribution = defaultdict(int)
            tenant_distribution = defaultdict(int)
            
            for record in filtered_executions:
                queue_distribution[record['queue_name']] += 1
                tenant_distribution[record.get('tenant_id', 'global')] += 1
            
            # Performance percentiles
            execution_times.sort()
            percentiles = {}
            if execution_times:
                percentiles = {
                    'p50': execution_times[int(0.5 * len(execution_times))],
                    'p90': execution_times[int(0.9 * len(execution_times))],
                    'p95': execution_times[int(0.95 * len(execution_times))],
                    'p99': execution_times[int(0.99 * len(execution_times))],
                }
            
            return {
                'time_range': {
                    'start': start_time.isoformat(),
                    'end': end_time.isoformat(),
                    'duration_hours': time_range.total_seconds() / 3600,
                },
                'execution_summary': {
                    'total_tasks': total_tasks,
                    'completed_tasks': completed_tasks,
                    'failed_tasks': failed_tasks,
                    'cancelled_tasks': cancelled_tasks,
                    'timeout_tasks': timeout_tasks,
                    'success_rate': completed_tasks / total_tasks if total_tasks > 0 else 0,
                    'error_rate': failed_tasks / total_tasks if total_tasks > 0 else 0,
                },
                'performance_metrics': {
                    'min_execution_time': min(execution_times) if execution_times else 0,
                    'max_execution_time': max(execution_times) if execution_times else 0,
                    'avg_execution_time': statistics.mean(execution_times) if execution_times else 0,
                    'median_execution_time': statistics.median(execution_times) if execution_times else 0,
                    'std_execution_time': statistics.stdev(execution_times) if len(execution_times) > 1 else 0,
                    'percentiles': percentiles,
                },
                'throughput_metrics': {
                    'tasks_per_hour': total_tasks / (time_range.total_seconds() / 3600),
                    'tasks_per_minute': total_tasks / (time_range.total_seconds() / 60),
                },
                'distribution_analysis': {
                    'by_queue': dict(queue_distribution),
                    'by_tenant': dict(tenant_distribution),
                },
                'sla_compliance': {
                    'breaches': sum(1 for r in filtered_executions if r['execution_time'] > self._sla_thresholds['max_execution_time']),
                    'compliance_rate': self._calculate_sla_compliance_rate(filtered_executions),
                },
                'generated_at': datetime.now(timezone.utc).isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Failed to generate performance report: {e}")
            return {'error': f'Report generation failed: {e}'}

    async def create_custom_alert(
        self,
        level: AlertLevel,
        title: str,
        message: str,
        source: str = "custom",
        metadata: Dict[str, Any] = None
    ) -> str:
        """Create a custom alert."""
        return await self._create_alert(level, title, message, source, metadata or {})

    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an active alert."""
        try:
            if alert_id in self._active_alerts:
                alert = self._active_alerts[alert_id]
                alert.resolved_at = datetime.now(timezone.utc)
                
                # Persist resolved alert
                await self._persist_alert(alert)
                
                # Remove from active alerts
                del self._active_alerts[alert_id]
                
                logger.info(f"Alert resolved", extra={'alert_id': alert_id})
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to resolve alert {alert_id}: {e}")
            return False

    async def get_active_alerts(self, level: Optional[AlertLevel] = None) -> List[Dict[str, Any]]:
        """Get all active alerts, optionally filtered by level."""
        alerts = []
        for alert in self._active_alerts.values():
            if level is None or alert.level == level:
                alerts.append(alert.to_dict())
        
        return sorted(alerts, key=lambda a: a['created_at'], reverse=True)

    def add_alert_handler(self, handler: Callable[[Alert], None]):
        """Add a custom alert handler."""
        self._alert_handlers.append(handler)

    def remove_alert_handler(self, handler: Callable[[Alert], None]):
        """Remove a custom alert handler."""
        if handler in self._alert_handlers:
            self._alert_handlers.remove(handler)

    async def _monitoring_loop(self):
        """Main monitoring loop for collecting metrics."""
        logger.info("Monitoring loop started")
        
        try:
            while self._is_running:
                await self._collect_system_metrics()
                await self._check_system_health()
                await asyncio.sleep(30)  # Monitor every 30 seconds
                
        except asyncio.CancelledError:
            logger.info("Monitoring loop cancelled")
        except Exception as e:
            logger.error(f"Monitoring loop error: {e}")

    async def _metrics_calculation_loop(self):
        """Loop for calculating and persisting metrics."""
        try:
            while self._is_running:
                await self._calculate_derived_metrics()
                await self._persist_metrics()
                await asyncio.sleep(300)  # Calculate every 5 minutes
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Metrics calculation loop error: {e}")

    async def _cleanup_loop(self):
        """Loop for cleaning up old data."""
        try:
            while self._is_running:
                await self._cleanup_old_data()
                await asyncio.sleep(3600)  # Cleanup every hour
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Cleanup loop error: {e}")

    async def _collect_system_metrics(self):
        """Collect system-wide metrics from Redis."""
        try:
            # Get queue sizes for monitoring
            queues = await self._task_queue.list_queues()
            
            for queue_name in queues:
                try:
                    queue_stats = await self._task_queue.get_queue_stats(queue_name)
                    await self.record_queue_size(queue_name, queue_stats.get('current_size', 0))
                except Exception as e:
                    logger.warning(f"Failed to get stats for queue {queue_name}: {e}")
            
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")

    async def _calculate_derived_metrics(self):
        """Calculate derived metrics from raw data."""
        try:
            for metrics_key, metrics in self._metrics_cache.items():
                # Calculate rates
                time_window = metrics.measurement_window.total_seconds()
                if time_window > 0:
                    metrics.tasks_per_minute = (metrics.total_tasks / time_window) * 60
                    metrics.tasks_per_hour = (metrics.total_tasks / time_window) * 3600
                
                # Calculate queue wait time from history
                relevant_records = [
                    record for record in self._queue_size_history
                    if (datetime.now(timezone.utc) - datetime.fromisoformat(record['timestamp'])).total_seconds() < time_window
                ]
                
                if relevant_records:
                    queue_sizes = [r['size'] for r in relevant_records]
                    metrics.avg_queue_wait_time = statistics.mean(queue_sizes) * 2  # Rough estimate
                
        except Exception as e:
            logger.error(f"Failed to calculate derived metrics: {e}")

    async def _check_system_health(self):
        """Check overall system health and generate alerts."""
        try:
            health_score = self._calculate_system_health()
            
            if health_score < 0.5:  # Critical health threshold
                await self._create_alert(
                    AlertLevel.CRITICAL,
                    "System Health Critical",
                    f"System health score is {health_score:.2f}",
                    source="health_monitor",
                    metadata={'health_score': health_score}
                )
            elif health_score < 0.7:  # Warning threshold
                await self._create_alert(
                    AlertLevel.WARNING,
                    "System Health Warning",
                    f"System health score is {health_score:.2f}",
                    source="health_monitor",
                    metadata={'health_score': health_score}
                )
            
        except Exception as e:
            logger.error(f"Failed to check system health: {e}")

    def _calculate_system_health(self) -> float:
        """Calculate overall system health score (0.0 to 1.0)."""
        try:
            if not self._metrics_cache:
                return 1.0  # No data = healthy
            
            health_factors = []
            
            for metrics in self._metrics_cache.values():
                # Success rate factor (0.0 to 1.0)
                health_factors.append(metrics.success_rate)
                
                # Queue size factor (1.0 = empty, decreases with size)
                queue_factor = max(0.0, 1.0 - (metrics.current_queue_size / 1000))
                health_factors.append(queue_factor)
                
                # Execution time factor (1.0 = fast, decreases with time)
                time_factor = max(0.0, 1.0 - (metrics.avg_execution_time / 300))  # 5 min threshold
                health_factors.append(time_factor)
            
            return statistics.mean(health_factors) if health_factors else 1.0
            
        except Exception as e:
            logger.warning(f"Failed to calculate system health: {e}")
            return 0.5  # Default to moderate health on error

    async def _check_sla_violations(self, execution_record: Dict[str, Any], metrics_key: str):
        """Check for SLA violations and create alerts."""
        try:
            task_id = execution_record['task_id']
            execution_time = execution_record['execution_time']
            
            # Check execution time SLA
            if execution_time > self._sla_thresholds['max_execution_time']:
                await self._create_alert(
                    AlertLevel.WARNING,
                    "SLA Violation: Execution Time",
                    f"Task {task_id} took {execution_time:.2f}s (threshold: {self._sla_thresholds['max_execution_time']}s)",
                    source="sla_monitor",
                    metadata={
                        'task_id': task_id,
                        'execution_time': execution_time,
                        'threshold': self._sla_thresholds['max_execution_time']
                    }
                )
                
                # Update SLA breach count
                if metrics_key in self._metrics_cache:
                    self._metrics_cache[metrics_key].sla_breaches += 1
            
        except Exception as e:
            logger.error(f"Failed to check SLA violations: {e}")

    def _calculate_sla_compliance_rate(self, executions: List[Dict[str, Any]]) -> float:
        """Calculate SLA compliance rate for executions."""
        if not executions:
            return 1.0
        
        violations = sum(
            1 for r in executions
            if r['execution_time'] > self._sla_thresholds['max_execution_time']
        )
        
        return 1.0 - (violations / len(executions))

    async def _create_alert(
        self,
        level: AlertLevel,
        title: str,
        message: str,
        source: str,
        metadata: Dict[str, Any]
    ) -> str:
        """Create a new alert and notify handlers."""
        try:
            alert_id = f"{source}-{int(time.time())}-{hash(title) % 10000}"
            
            alert = Alert(
                alert_id=alert_id,
                level=level,
                title=title,
                message=message,
                source=source,
                metadata=metadata
            )
            
            self._active_alerts[alert_id] = alert
            
            # Persist alert
            await self._persist_alert(alert)
            
            # Notify handlers
            for handler in self._alert_handlers:
                try:
                    handler(alert)
                except Exception as e:
                    logger.error(f"Alert handler failed: {e}")
            
            logger.info(f"Alert created", extra={
                'alert_id': alert_id,
                'level': level.value,
                'source': source
            })
            
            return alert_id
            
        except Exception as e:
            logger.error(f"Failed to create alert: {e}")
            return ""

    async def _persist_metrics(self):
        """Persist metrics to Redis."""
        try:
            for metrics_key, metrics in self._metrics_cache.items():
                redis_key = f"{self.key_prefix}:metrics:{metrics_key}"
                metrics_data = json.dumps(metrics.to_dict())
                
                await self._redis.set(
                    redis_key,
                    metrics_data,
                    ex=86400 * self.metrics_retention_days
                )
            
        except Exception as e:
            logger.error(f"Failed to persist metrics: {e}")

    async def _persist_alert(self, alert: Alert):
        """Persist alert to Redis."""
        try:
            alert_key = f"{self.key_prefix}:alert:{alert.alert_id}"
            alert_data = json.dumps(alert.to_dict())
            
            await self._redis.set(
                alert_key,
                alert_data,
                ex=86400 * self.alert_retention_days
            )
            
        except Exception as e:
            logger.error(f"Failed to persist alert: {e}")

    async def _persist_alerts(self):
        """Persist all active alerts."""
        for alert in self._active_alerts.values():
            await self._persist_alert(alert)

    async def _load_cached_metrics(self):
        """Load cached metrics from Redis."""
        try:
            pattern = f"{self.key_prefix}:metrics:*"
            keys = await self._redis.keys(pattern)
            
            for key in keys:
                try:
                    metrics_data = await self._redis.get(key)
                    if metrics_data:
                        data = json.loads(metrics_data)
                        metrics_key = key.replace(f"{self.key_prefix}:metrics:", "")
                        
                        # Reconstruct TaskMetrics object
                        metrics = TaskMetrics()
                        for attr, value in data.items():
                            if hasattr(metrics, attr):
                                if attr == 'last_updated':
                                    setattr(metrics, attr, datetime.fromisoformat(value))
                                else:
                                    setattr(metrics, attr, value)
                        
                        self._metrics_cache[metrics_key] = metrics
                        
                except Exception as e:
                    logger.warning(f"Failed to load metrics from {key}: {e}")
            
        except Exception as e:
            logger.error(f"Failed to load cached metrics: {e}")

    async def _load_active_alerts(self):
        """Load active alerts from Redis."""
        try:
            pattern = f"{self.key_prefix}:alert:*"
            keys = await self._redis.keys(pattern)
            
            for key in keys:
                try:
                    alert_data = await self._redis.get(key)
                    if alert_data:
                        data = json.loads(alert_data)
                        
                        # Only load unresolved alerts
                        if not data.get('is_resolved', False):
                            alert = Alert(
                                alert_id=data['alert_id'],
                                level=AlertLevel(data['level']),
                                title=data['title'],
                                message=data['message'],
                                source=data['source'],
                                created_at=datetime.fromisoformat(data['created_at']),
                                resolved_at=datetime.fromisoformat(data['resolved_at']) if data.get('resolved_at') else None,
                                metadata=data.get('metadata', {})
                            )
                            
                            self._active_alerts[alert.alert_id] = alert
                            
                except Exception as e:
                    logger.warning(f"Failed to load alert from {key}: {e}")
            
        except Exception as e:
            logger.error(f"Failed to load active alerts: {e}")

    async def _cleanup_old_data(self):
        """Clean up old metrics and alert data."""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=self.metrics_retention_days)
            
            # Cleanup old execution records
            pattern = f"{self.key_prefix}:execution:*"
            keys = await self._redis.keys(pattern)
            
            deleted_count = 0
            for key in keys:
                try:
                    record_data = await self._redis.get(key)
                    if record_data:
                        record = json.loads(record_data)
                        record_time = datetime.fromisoformat(record['timestamp'])
                        
                        if record_time < cutoff_time:
                            await self._redis.delete(key)
                            deleted_count += 1
                            
                except Exception:
                    # Delete corrupted records
                    await self._redis.delete(key)
                    deleted_count += 1
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old execution records")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")

    async def get_health_check(self) -> Dict[str, Any]:
        """Get comprehensive system health check."""
        try:
            health_score = self._calculate_system_health()
            
            return {
                'status': 'healthy' if health_score > 0.7 else 'degraded' if health_score > 0.5 else 'critical',
                'health_score': health_score,
                'active_alerts': len(self._active_alerts),
                'critical_alerts': len([a for a in self._active_alerts.values() if a.level == AlertLevel.CRITICAL]),
                'monitor_status': 'running' if self._is_running else 'stopped',
                'last_update': datetime.now(timezone.utc).isoformat(),
                'uptime_seconds': time.time() - (self._monitoring_task.get_loop().time() if self._monitoring_task else time.time()),
            }
            
        except Exception as e:
            logger.error(f"Failed to get health check: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'last_update': datetime.now(timezone.utc).isoformat(),
            }