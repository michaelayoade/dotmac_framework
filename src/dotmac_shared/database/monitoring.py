"""
Database monitoring and performance analytics for DotMac Framework.
Provides comprehensive monitoring, alerting, and performance insights.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from collections import deque, defaultdict

from dotmac_shared.observability.logging import get_logger
from .session import check_database_health, get_connection_pool_stats, _active_connections
from .caching import get_cache_health, smart_cache
from .query_optimization import query_profiler, get_cache_stats

logger = get_logger(__name__)


@dataclass
class QueryMetrics:
    """Query performance metrics."""
    query_name: str
    execution_time: float
    timestamp: datetime
    success: bool
    error_message: Optional[str] = None
    row_count: Optional[int] = None
    cache_hit: bool = False
    database_type: str = "write"  # write/read


@dataclass
class ConnectionMetrics:
    """Database connection metrics."""
    total_connections: int
    active_connections: int
    idle_connections: int
    pool_size: int
    overflow_connections: int
    timestamp: datetime


@dataclass
class PerformanceAlert:
    """Performance alert definition."""
    alert_id: str
    alert_type: str
    severity: str  # low, medium, high, critical
    message: str
    threshold_value: float
    actual_value: float
    timestamp: datetime
    resolved: bool = False


class DatabaseMonitor:
    """Comprehensive database monitoring system."""
    
    def __init__(self, max_metrics_history: int = 10000):
        self.max_metrics_history = max_metrics_history
        self.query_metrics = deque(maxlen=max_metrics_history)
        self.connection_metrics = deque(maxlen=max_metrics_history)
        self.performance_alerts = deque(maxlen=1000)
        
        # Performance thresholds
        self.thresholds = {
            "slow_query_seconds": 2.0,
            "very_slow_query_seconds": 5.0,
            "high_connection_usage_percent": 80.0,
            "critical_connection_usage_percent": 95.0,
            "cache_hit_ratio_low": 0.5,
            "cache_hit_ratio_critical": 0.2
        }
        
        # Monitoring state
        self.monitoring_active = False
        self.monitoring_interval = 60  # seconds
        self.alert_cooldown = {}  # Prevent alert spam
        
        # Query pattern tracking
        self.query_patterns = defaultdict(list)
        
    async def start_monitoring(self):
        """Start continuous database monitoring."""
        if self.monitoring_active:
            logger.warning("Database monitoring is already active")
            return
        
        self.monitoring_active = True
        asyncio.create_task(self._monitoring_loop())
        logger.info("Database monitoring started")
    
    async def stop_monitoring(self):
        """Stop database monitoring."""
        self.monitoring_active = False
        logger.info("Database monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                await self._collect_metrics()
                await self._check_performance_alerts()
                await asyncio.sleep(self.monitoring_interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(10)  # Short sleep on error
    
    async def _collect_metrics(self):
        """Collect current database metrics."""
        try:
            # Database health metrics
            db_health = await check_database_health()
            
            # Connection pool metrics
            pool_stats = get_connection_pool_stats()
            
            if pool_stats.get("write"):
                connection_metric = ConnectionMetrics(
                    total_connections=pool_stats["write"].get("size", 0) + pool_stats["write"].get("overflow", 0),
                    active_connections=pool_stats["write"].get("checked_out", 0),
                    idle_connections=pool_stats["write"].get("checked_in", 0),
                    pool_size=pool_stats["write"].get("size", 0),
                    overflow_connections=pool_stats["write"].get("overflow", 0),
                    timestamp=datetime.utcnow()
                )
                self.connection_metrics.append(connection_metric)
            
            # Cache metrics
            cache_health = await get_cache_health()
            
            logger.debug("Database metrics collected", extra={
                "db_healthy": db_health.get("healthy", False),
                "active_connections": len(_active_connections),
                "cache_healthy": cache_health.get("healthy", False)
            })
            
        except Exception as e:
            logger.error(f"Failed to collect database metrics: {e}")
    
    async def _check_performance_alerts(self):
        """Check for performance issues and generate alerts."""
        try:
            await self._check_query_performance_alerts()
            await self._check_connection_alerts()
            await self._check_cache_performance_alerts()
        except Exception as e:
            logger.error(f"Error checking performance alerts: {e}")
    
    async def _check_query_performance_alerts(self):
        """Check for query performance issues."""
        if not self.query_metrics:
            return
        
        # Get recent query metrics (last 5 minutes)
        cutoff_time = datetime.utcnow() - timedelta(minutes=5)
        recent_metrics = [m for m in self.query_metrics if m.timestamp >= cutoff_time]
        
        if not recent_metrics:
            return
        
        # Check for slow queries
        slow_queries = [m for m in recent_metrics if m.execution_time > self.thresholds["slow_query_seconds"]]
        very_slow_queries = [m for m in recent_metrics if m.execution_time > self.thresholds["very_slow_query_seconds"]]
        
        if very_slow_queries:
            await self._create_alert(
                "very_slow_queries",
                "critical",
                f"{len(very_slow_queries)} very slow queries detected in the last 5 minutes",
                self.thresholds["very_slow_query_seconds"],
                max(m.execution_time for m in very_slow_queries)
            )
        elif len(slow_queries) > 10:  # More than 10 slow queries
            await self._create_alert(
                "many_slow_queries",
                "high",
                f"{len(slow_queries)} slow queries detected in the last 5 minutes",
                self.thresholds["slow_query_seconds"],
                len(slow_queries)
            )
        
        # Check query failure rate
        failed_queries = [m for m in recent_metrics if not m.success]
        if failed_queries and len(failed_queries) / len(recent_metrics) > 0.1:  # >10% failure rate
            await self._create_alert(
                "high_query_failure_rate",
                "high",
                f"High query failure rate: {len(failed_queries)}/{len(recent_metrics)} queries failed",
                0.1,
                len(failed_queries) / len(recent_metrics)
            )
    
    async def _check_connection_alerts(self):
        """Check for connection pool issues."""
        if not self.connection_metrics:
            return
        
        latest_metric = self.connection_metrics[-1]
        
        if latest_metric.pool_size > 0:
            usage_percent = (latest_metric.active_connections / latest_metric.pool_size) * 100
            
            if usage_percent >= self.thresholds["critical_connection_usage_percent"]:
                await self._create_alert(
                    "critical_connection_usage",
                    "critical",
                    f"Critical database connection usage: {usage_percent:.1f}%",
                    self.thresholds["critical_connection_usage_percent"],
                    usage_percent
                )
            elif usage_percent >= self.thresholds["high_connection_usage_percent"]:
                await self._create_alert(
                    "high_connection_usage",
                    "medium",
                    f"High database connection usage: {usage_percent:.1f}%",
                    self.thresholds["high_connection_usage_percent"],
                    usage_percent
                )
    
    async def _check_cache_performance_alerts(self):
        """Check for cache performance issues."""
        try:
            cache_stats = get_cache_stats()
            hit_ratio = cache_stats.get("cache_hit_ratio", 1.0)
            
            if hit_ratio <= self.thresholds["cache_hit_ratio_critical"]:
                await self._create_alert(
                    "critical_cache_hit_ratio",
                    "critical",
                    f"Critical cache hit ratio: {hit_ratio:.2%}",
                    self.thresholds["cache_hit_ratio_critical"],
                    hit_ratio
                )
            elif hit_ratio <= self.thresholds["cache_hit_ratio_low"]:
                await self._create_alert(
                    "low_cache_hit_ratio",
                    "medium",
                    f"Low cache hit ratio: {hit_ratio:.2%}",
                    self.thresholds["cache_hit_ratio_low"],
                    hit_ratio
                )
        except Exception as e:
            logger.error(f"Error checking cache alerts: {e}")
    
    async def _create_alert(self, alert_type: str, severity: str, message: str, 
                          threshold: float, actual: float):
        """Create a performance alert with cooldown."""
        # Check cooldown to prevent alert spam
        cooldown_key = f"{alert_type}_{severity}"
        last_alert_time = self.alert_cooldown.get(cooldown_key)
        
        if last_alert_time and (datetime.utcnow() - last_alert_time).total_seconds() < 300:  # 5 minute cooldown
            return
        
        alert = PerformanceAlert(
            alert_id=f"{alert_type}_{int(time.time())}",
            alert_type=alert_type,
            severity=severity,
            message=message,
            threshold_value=threshold,
            actual_value=actual,
            timestamp=datetime.utcnow()
        )
        
        self.performance_alerts.append(alert)
        self.alert_cooldown[cooldown_key] = datetime.utcnow()
        
        # Log the alert
        logger.warning(
            f"Performance alert: {message}",
            extra={
                "alert_type": alert_type,
                "severity": severity,
                "threshold": threshold,
                "actual_value": actual
            }
        )
    
    def record_query_metric(self, query_name: str, execution_time: float, 
                          success: bool, error_message: Optional[str] = None,
                          row_count: Optional[int] = None, cache_hit: bool = False,
                          database_type: str = "write"):
        """Record a query performance metric."""
        metric = QueryMetrics(
            query_name=query_name,
            execution_time=execution_time,
            timestamp=datetime.utcnow(),
            success=success,
            error_message=error_message,
            row_count=row_count,
            cache_hit=cache_hit,
            database_type=database_type
        )
        
        self.query_metrics.append(metric)
        
        # Track query patterns
        self.query_patterns[query_name].append({
            "execution_time": execution_time,
            "timestamp": datetime.utcnow(),
            "success": success
        })
    
    def get_performance_summary(self, hours_back: int = 24) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        
        # Filter metrics by time
        recent_queries = [m for m in self.query_metrics if m.timestamp >= cutoff_time]
        recent_connections = [m for m in self.connection_metrics if m.timestamp >= cutoff_time]
        recent_alerts = [a for a in self.performance_alerts if a.timestamp >= cutoff_time and not a.resolved]
        
        # Query statistics
        query_stats = {
            "total_queries": len(recent_queries),
            "successful_queries": len([q for q in recent_queries if q.success]),
            "failed_queries": len([q for q in recent_queries if not q.success]),
            "avg_execution_time": sum(q.execution_time for q in recent_queries) / len(recent_queries) if recent_queries else 0,
            "slowest_query_time": max(q.execution_time for q in recent_queries) if recent_queries else 0,
            "cache_hits": len([q for q in recent_queries if q.cache_hit]),
            "read_queries": len([q for q in recent_queries if q.database_type == "read"]),
            "write_queries": len([q for q in recent_queries if q.database_type == "write"])
        }
        
        # Connection statistics
        connection_stats = {}
        if recent_connections:
            latest_connection = recent_connections[-1]
            connection_stats = {
                "current_active": latest_connection.active_connections,
                "current_idle": latest_connection.idle_connections,
                "pool_size": latest_connection.pool_size,
                "overflow_connections": latest_connection.overflow_connections,
                "max_active_connections": max(c.active_connections for c in recent_connections),
                "avg_active_connections": sum(c.active_connections for c in recent_connections) / len(recent_connections)
            }
        
        # Alert statistics
        alert_stats = {
            "total_alerts": len(recent_alerts),
            "critical_alerts": len([a for a in recent_alerts if a.severity == "critical"]),
            "high_alerts": len([a for a in recent_alerts if a.severity == "high"]),
            "medium_alerts": len([a for a in recent_alerts if a.severity == "medium"]),
            "low_alerts": len([a for a in recent_alerts if a.severity == "low"])
        }
        
        # Top slow queries
        slow_queries = sorted(
            [q for q in recent_queries if q.success], 
            key=lambda x: x.execution_time, 
            reverse=True
        )[:10]
        
        top_slow_queries = [
            {
                "query_name": q.query_name,
                "execution_time": q.execution_time,
                "timestamp": q.timestamp.isoformat(),
                "row_count": q.row_count
            } for q in slow_queries
        ]
        
        return {
            "monitoring_period_hours": hours_back,
            "query_statistics": query_stats,
            "connection_statistics": connection_stats,
            "alert_statistics": alert_stats,
            "top_slow_queries": top_slow_queries,
            "cache_hit_ratio": query_stats["cache_hits"] / max(query_stats["total_queries"], 1),
            "query_success_rate": query_stats["successful_queries"] / max(query_stats["total_queries"], 1),
            "read_write_ratio": query_stats["read_queries"] / max(query_stats["write_queries"], 1) if query_stats["write_queries"] > 0 else float('inf'),
            "generated_at": datetime.utcnow().isoformat()
        }
    
    def get_query_pattern_analysis(self, query_name: str = None, hours_back: int = 24) -> Dict[str, Any]:
        """Analyze query patterns for optimization opportunities."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        
        if query_name:
            patterns = {query_name: self.query_patterns.get(query_name, [])}
        else:
            patterns = self.query_patterns
        
        analysis = {}
        for name, pattern_data in patterns.items():
            recent_data = [p for p in pattern_data if p["timestamp"] >= cutoff_time]
            
            if not recent_data:
                continue
            
            successful_data = [p for p in recent_data if p["success"]]
            
            if successful_data:
                analysis[name] = {
                    "total_executions": len(recent_data),
                    "successful_executions": len(successful_data),
                    "failure_rate": (len(recent_data) - len(successful_data)) / len(recent_data),
                    "avg_execution_time": sum(p["execution_time"] for p in successful_data) / len(successful_data),
                    "min_execution_time": min(p["execution_time"] for p in successful_data),
                    "max_execution_time": max(p["execution_time"] for p in successful_data),
                    "execution_time_variance": self._calculate_variance([p["execution_time"] for p in successful_data]),
                    "optimization_score": self._calculate_optimization_score(successful_data),
                    "recommendations": self._generate_optimization_recommendations(successful_data)
                }
        
        return analysis
    
    def _calculate_variance(self, values: List[float]) -> float:
        """Calculate variance of execution times."""
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        return sum((x - mean) ** 2 for x in values) / len(values)
    
    def _calculate_optimization_score(self, execution_data: List[Dict]) -> float:
        """Calculate optimization priority score (0-100, higher means needs optimization)."""
        if not execution_data:
            return 0.0
        
        execution_times = [d["execution_time"] for d in execution_data]
        avg_time = sum(execution_times) / len(execution_times)
        max_time = max(execution_times)
        frequency = len(execution_data)
        
        # Score based on frequency and execution time
        frequency_score = min(frequency / 100 * 50, 50)  # Up to 50 points for frequency
        time_score = min(avg_time * 10, 30)  # Up to 30 points for avg execution time
        spike_score = min((max_time - avg_time) * 5, 20)  # Up to 20 points for time spikes
        
        return frequency_score + time_score + spike_score
    
    def _generate_optimization_recommendations(self, execution_data: List[Dict]) -> List[str]:
        """Generate optimization recommendations based on patterns."""
        recommendations = []
        
        if not execution_data:
            return recommendations
        
        execution_times = [d["execution_time"] for d in execution_data]
        avg_time = sum(execution_times) / len(execution_times)
        max_time = max(execution_times)
        frequency = len(execution_data)
        
        # High frequency queries
        if frequency > 100:
            recommendations.append("Consider caching - high frequency query")
        
        # Slow queries
        if avg_time > 2.0:
            recommendations.append("Investigate indexes - slow average execution time")
        
        # Inconsistent performance
        if max_time > avg_time * 3:
            recommendations.append("Check for resource contention - inconsistent execution times")
        
        # Very frequent fast queries
        if frequency > 500 and avg_time < 0.1:
            recommendations.append("Consider connection pooling optimization")
        
        return recommendations
    
    def clear_old_metrics(self, days_back: int = 7):
        """Clear metrics older than specified days."""
        cutoff_time = datetime.utcnow() - timedelta(days=days_back)
        
        # Clear old query metrics
        self.query_metrics = deque(
            [m for m in self.query_metrics if m.timestamp >= cutoff_time],
            maxlen=self.max_metrics_history
        )
        
        # Clear old connection metrics
        self.connection_metrics = deque(
            [m for m in self.connection_metrics if m.timestamp >= cutoff_time],
            maxlen=self.max_metrics_history
        )
        
        # Clear resolved alerts
        self.performance_alerts = deque(
            [a for a in self.performance_alerts if a.timestamp >= cutoff_time and not a.resolved],
            maxlen=1000
        )
        
        # Clear old query patterns
        for query_name in list(self.query_patterns.keys()):
            self.query_patterns[query_name] = [
                p for p in self.query_patterns[query_name] 
                if p["timestamp"] >= cutoff_time
            ]
            if not self.query_patterns[query_name]:
                del self.query_patterns[query_name]
        
        logger.info(f"Cleared metrics older than {days_back} days")


# Global monitoring instance
db_monitor = DatabaseMonitor()


# === PERFORMANCE DECORATORS FOR MONITORING ===

def monitor_query_performance(query_name: str, database_type: str = "write"):
    """Decorator to monitor query performance."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            error_message = None
            row_count = None
            cache_hit = False
            
            try:
                result = await func(*args, **kwargs)
                
                # Try to determine row count and cache hit
                if isinstance(result, (list, tuple)):
                    row_count = len(result)
                elif hasattr(result, '__len__'):
                    try:
                        row_count = len(result)
                    except:
                        pass
                
                # Check if result came from cache (simple heuristic)
                execution_time = time.time() - start_time
                if execution_time < 0.001:  # Very fast, likely cached
                    cache_hit = True
                
                return result
                
            except Exception as e:
                success = False
                error_message = str(e)
                raise
            finally:
                execution_time = time.time() - start_time
                db_monitor.record_query_metric(
                    query_name=query_name,
                    execution_time=execution_time,
                    success=success,
                    error_message=error_message,
                    row_count=row_count,
                    cache_hit=cache_hit,
                    database_type=database_type
                )
        
        return wrapper
    return decorator


# === MONITORING API FUNCTIONS ===

async def get_database_performance_dashboard() -> Dict[str, Any]:
    """Get comprehensive database performance dashboard data."""
    try:
        # Database health
        db_health = await check_database_health()
        
        # Cache health
        cache_health = await get_cache_health()
        
        # Performance summary
        performance_summary = db_monitor.get_performance_summary(hours_back=24)
        
        # Query profiler stats
        profiler_stats = query_profiler.get_stats()
        
        # Connection pool stats
        pool_stats = get_connection_pool_stats()
        
        dashboard = {
            "timestamp": datetime.utcnow().isoformat(),
            "database_health": db_health,
            "cache_health": cache_health,
            "performance_summary": performance_summary,
            "query_profiler_stats": profiler_stats,
            "connection_pool_stats": pool_stats,
            "monitoring_active": db_monitor.monitoring_active,
            "active_alerts": [
                asdict(alert) for alert in db_monitor.performance_alerts 
                if not alert.resolved
            ][-10:]  # Last 10 alerts
        }
        
        return dashboard
        
    except Exception as e:
        logger.error(f"Failed to generate performance dashboard: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


async def start_database_monitoring():
    """Start database monitoring system."""
    await db_monitor.start_monitoring()


async def stop_database_monitoring():
    """Stop database monitoring system."""
    await db_monitor.stop_monitoring()


async def clear_monitoring_data():
    """Clear all monitoring data."""
    db_monitor.clear_old_metrics(days_back=0)
    query_profiler.reset_stats()
    logger.info("All monitoring data cleared")