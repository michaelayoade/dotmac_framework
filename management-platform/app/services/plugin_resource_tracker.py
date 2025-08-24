"""
Plugin Resource Usage Tracking Service.

Tracks and monitors resource usage by plugins including CPU, memory, disk, 
network, and database resources.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID
import json
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession
from ..repositories.plugin_additional import (
    PluginResourceUsageRepository,
    PluginInstallationRepository
)

logger = logging.getLogger(__name__)


class PluginResourceTracker:
    """Service for tracking plugin resource usage."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.usage_repo = PluginResourceUsageRepository(db)
        self.installation_repo = PluginInstallationRepository(db)
    
    async def collect_resource_usage(
        self, 
        installation_id: UUID,
        resource_data: Dict[str, Any]
    ) -> bool:
        """Collect and store resource usage data for a plugin installation."""
        try:
            # Validate installation exists
            installation = await self.installation_repo.get_by_id(installation_id)
            if not installation:
                logger.warning(f"Installation not found: {installation_id}")
                return False
            
            # Create resource usage record
            usage_record = {
                "plugin_installation_id": installation_id,
                "tenant_id": installation.tenant_id,
                "plugin_id": installation.plugin_id,
                "timestamp": datetime.utcnow(),
                "cpu_usage_percent": resource_data.get("cpu_usage_percent", 0.0),
                "memory_usage_mb": resource_data.get("memory_usage_mb", 0.0),
                "disk_usage_mb": resource_data.get("disk_usage_mb", 0.0),
                "network_in_mb": resource_data.get("network_in_mb", 0.0),
                "network_out_mb": resource_data.get("network_out_mb", 0.0),
                "database_queries": resource_data.get("database_queries", 0),
                "database_time_ms": resource_data.get("database_time_ms", 0.0),
                "api_calls_made": resource_data.get("api_calls_made", 0),
                "api_calls_received": resource_data.get("api_calls_received", 0),
                "error_count": resource_data.get("error_count", 0),
                "custom_metrics": resource_data.get("custom_metrics", {})
            }
            
            await self.usage_repo.create(usage_record)
            
            # Check for resource usage alerts
            await self._check_resource_alerts(installation_id, resource_data)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to collect resource usage: {e}")
            return False
    
    async def get_usage_summary(
        self,
        installation_id: UUID,
        time_range: str = "24h"
    ) -> Dict[str, Any]:
        """Get resource usage summary for a plugin installation."""
        try:
            # Calculate time range
            end_time = datetime.utcnow()
            if time_range == "1h":
                start_time = end_time - timedelta(hours=1)
            elif time_range == "24h":
                start_time = end_time - timedelta(hours=24)
            elif time_range == "7d":
                start_time = end_time - timedelta(days=7)
            elif time_range == "30d":
                start_time = end_time - timedelta(days=30)
            else:
                start_time = end_time - timedelta(hours=24)
            
            # Get usage data
            usage_data = await self.usage_repo.get_by_installation_and_timerange(
                installation_id, start_time, end_time
            )
            
            if not usage_data:
                return {
                    "installation_id": installation_id,
                    "time_range": time_range,
                    "data_points": 0,
                    "summary": {}
                }
            
            # Calculate statistics
            cpu_values = [u.cpu_usage_percent for u in usage_data]
            memory_values = [u.memory_usage_mb for u in usage_data]
            disk_values = [u.disk_usage_mb for u in usage_data]
            network_in_values = [u.network_in_mb for u in usage_data]
            network_out_values = [u.network_out_mb for u in usage_data]
            db_query_values = [u.database_queries for u in usage_data]
            error_values = [u.error_count for u in usage_data]
            
            summary = {
                "cpu_usage": {
                    "avg": sum(cpu_values) / len(cpu_values) if cpu_values else 0,
                    "max": max(cpu_values) if cpu_values else 0,
                    "min": min(cpu_values) if cpu_values else 0
                },
                "memory_usage_mb": {
                    "avg": sum(memory_values) / len(memory_values) if memory_values else 0,
                    "max": max(memory_values) if memory_values else 0,
                    "min": min(memory_values) if memory_values else 0
                },
                "disk_usage_mb": {
                    "current": disk_values[-1] if disk_values else 0,
                    "max": max(disk_values) if disk_values else 0,
                    "growth": disk_values[-1] - disk_values[0] if len(disk_values) > 1 else 0
                },
                "network_total_mb": {
                    "in": sum(network_in_values),
                    "out": sum(network_out_values),
                    "total": sum(network_in_values) + sum(network_out_values)
                },
                "database_activity": {
                    "total_queries": sum(db_query_values),
                    "avg_queries_per_hour": sum(db_query_values) / max(len(db_query_values), 1)
                },
                "reliability": {
                    "total_errors": sum(error_values),
                    "error_rate": sum(error_values) / max(len(error_values), 1),
                    "uptime_percentage": self._calculate_uptime_percentage(usage_data)
                }
            }
            
            return {
                "installation_id": installation_id,
                "time_range": time_range,
                "data_points": len(usage_data),
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "summary": summary,
                "time_series": self._generate_time_series(usage_data, time_range)
            }
            
        except Exception as e:
            logger.error(f"Failed to get usage summary: {e}")
            return {"error": str(e)}
    
    async def get_tenant_resource_overview(
        self,
        tenant_id: UUID,
        time_range: str = "24h"
    ) -> Dict[str, Any]:
        """Get resource usage overview for all plugins in a tenant."""
        try:
            # Get all installations for tenant
            installations = await self.installation_repo.get_active_by_tenant(tenant_id)
            
            if not installations:
                return {
                    "tenant_id": tenant_id,
                    "total_plugins": 0,
                    "resource_summary": {}
                }
            
            # Calculate time range
            end_time = datetime.utcnow()
            if time_range == "24h":
                start_time = end_time - timedelta(hours=24)
            elif time_range == "7d":
                start_time = end_time - timedelta(days=7)
            elif time_range == "30d":
                start_time = end_time - timedelta(days=30)
            else:
                start_time = end_time - timedelta(hours=24)
            
            # Get usage data for all installations
            total_usage = {
                "cpu_usage_avg": 0.0,
                "memory_usage_total_mb": 0.0,
                "disk_usage_total_mb": 0.0,
                "network_total_mb": 0.0,
                "database_queries_total": 0,
                "total_errors": 0
            }
            
            plugin_summaries = []
            
            for installation in installations:
                usage_data = await self.usage_repo.get_by_installation_and_timerange(
                    installation.id, start_time, end_time
                )
                
                if usage_data:
                    latest = usage_data[-1]
                    avg_cpu = sum(u.cpu_usage_percent for u in usage_data) / len(usage_data)
                    
                    plugin_summary = {
                        "plugin_name": installation.plugin.name if installation.plugin else "Unknown",
                        "installation_id": installation.id,
                        "cpu_usage_avg": avg_cpu,
                        "memory_usage_current": latest.memory_usage_mb,
                        "disk_usage_current": latest.disk_usage_mb,
                        "network_usage_total": sum(u.network_in_mb + u.network_out_mb for u in usage_data),
                        "database_queries_total": sum(u.database_queries for u in usage_data),
                        "error_count": sum(u.error_count for u in usage_data),
                        "last_updated": latest.timestamp.isoformat()
                    }
                    
                    plugin_summaries.append(plugin_summary)
                    
                    # Add to totals
                    total_usage["cpu_usage_avg"] += avg_cpu
                    total_usage["memory_usage_total_mb"] += latest.memory_usage_mb
                    total_usage["disk_usage_total_mb"] += latest.disk_usage_mb
                    total_usage["network_total_mb"] += plugin_summary["network_usage_total"]
                    total_usage["database_queries_total"] += plugin_summary["database_queries_total"]
                    total_usage["total_errors"] += plugin_summary["error_count"]
            
            # Calculate averages
            active_plugins = len(plugin_summaries)
            if active_plugins > 0:
                total_usage["cpu_usage_avg"] = total_usage["cpu_usage_avg"] / active_plugins
            
            return {
                "tenant_id": tenant_id,
                "time_range": time_range,
                "total_plugins": len(installations),
                "active_plugins": active_plugins,
                "resource_summary": total_usage,
                "plugin_details": plugin_summaries,
                "top_consumers": self._get_top_consumers(plugin_summaries),
                "resource_alerts": await self._get_tenant_alerts(tenant_id)
            }
            
        except Exception as e:
            logger.error(f"Failed to get tenant resource overview: {e}")
            return {"error": str(e)}
    
    async def _check_resource_alerts(
        self,
        installation_id: UUID,
        resource_data: Dict[str, Any]
    ):
        """Check for resource usage alerts and create notifications."""
        alerts = []
        
        # CPU threshold check
        cpu_usage = resource_data.get("cpu_usage_percent", 0)
        if cpu_usage > 80:
            alerts.append({
                "type": "high_cpu",
                "severity": "warning" if cpu_usage < 95 else "critical",
                "message": f"High CPU usage: {cpu_usage}%",
                "threshold": 80,
                "actual": cpu_usage
            })
        
        # Memory threshold check
        memory_usage = resource_data.get("memory_usage_mb", 0)
        if memory_usage > 1024:  # 1GB threshold
            alerts.append({
                "type": "high_memory",
                "severity": "warning" if memory_usage < 2048 else "critical",
                "message": f"High memory usage: {memory_usage}MB",
                "threshold": 1024,
                "actual": memory_usage
            })
        
        # Error rate check
        error_count = resource_data.get("error_count", 0)
        if error_count > 10:
            alerts.append({
                "type": "high_errors",
                "severity": "warning" if error_count < 50 else "critical",
                "message": f"High error count: {error_count}",
                "threshold": 10,
                "actual": error_count
            })
        
        # Store alerts if any
        if alerts:
            for alert in alerts:
                alert_record = {
                    "plugin_installation_id": installation_id,
                    "alert_type": alert["type"],
                    "severity": alert["severity"],
                    "message": alert["message"],
                    "threshold_value": alert["threshold"],
                    "actual_value": alert["actual"],
                    "timestamp": datetime.utcnow(),
                    "acknowledged": False
                }
                await self._create_alert(alert_record)
    
    async def _create_alert(self, alert_record: Dict[str, Any]):
        """Create a resource usage alert."""
        try:
            # This would integrate with the notification system
            logger.warning(f"Plugin resource alert: {alert_record['message']}")
            # TODO: Integrate with notification service to send alerts
            
        except Exception as e:
            logger.error(f"Failed to create alert: {e}")
    
    def _calculate_uptime_percentage(self, usage_data: List[Any]) -> float:
        """Calculate uptime percentage based on error data."""
        if not usage_data:
            return 100.0
        
        # Consider periods with errors as downtime
        error_periods = sum(1 for u in usage_data if u.error_count > 0)
        total_periods = len(usage_data)
        
        uptime = ((total_periods - error_periods) / total_periods) * 100
        return round(uptime, 2)
    
    def _generate_time_series(
        self,
        usage_data: List[Any],
        time_range: str
    ) -> List[Dict[str, Any]]:
        """Generate time series data for visualization."""
        time_series = []
        
        for usage in usage_data:
            time_series.append({
                "timestamp": usage.timestamp.isoformat(),
                "cpu_usage": usage.cpu_usage_percent,
                "memory_usage": usage.memory_usage_mb,
                "disk_usage": usage.disk_usage_mb,
                "network_in": usage.network_in_mb,
                "network_out": usage.network_out_mb,
                "database_queries": usage.database_queries,
                "errors": usage.error_count
            })
        
        return time_series
    
    def _get_top_consumers(self, plugin_summaries: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Get top resource consuming plugins."""
        # Sort by different metrics
        by_cpu = sorted(plugin_summaries, key=lambda x: x["cpu_usage_avg"], reverse=True)[:5]
        by_memory = sorted(plugin_summaries, key=lambda x: x["memory_usage_current"], reverse=True)[:5]
        by_disk = sorted(plugin_summaries, key=lambda x: x["disk_usage_current"], reverse=True)[:5]
        by_network = sorted(plugin_summaries, key=lambda x: x["network_usage_total"], reverse=True)[:5]
        
        return {
            "cpu": [{"plugin_name": p["plugin_name"], "value": p["cpu_usage_avg"]} for p in by_cpu],
            "memory": [{"plugin_name": p["plugin_name"], "value": p["memory_usage_current"]} for p in by_memory],
            "disk": [{"plugin_name": p["plugin_name"], "value": p["disk_usage_current"]} for p in by_disk],
            "network": [{"plugin_name": p["plugin_name"], "value": p["network_usage_total"]} for p in by_network]
        }
    
    async def _get_tenant_alerts(self, tenant_id: UUID) -> List[Dict[str, Any]]:
        """Get current alerts for a tenant."""
        try:
            # This would query the alerts repository
            # For now, return empty list
            return []
        except Exception as e:
            logger.error(f"Failed to get tenant alerts: {e}")
            return []
    
    async def cleanup_old_usage_data(self, retention_days: int = 90):
        """Clean up old resource usage data."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            deleted_count = await self.usage_repo.delete_older_than(cutoff_date)
            
            logger.info(f"Cleaned up {deleted_count} old resource usage records")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old usage data: {e}")
            return 0
    
    async def get_resource_trends(
        self,
        installation_id: UUID,
        metric: str = "cpu_usage",
        days: int = 7
    ) -> Dict[str, Any]:
        """Get resource usage trends for a plugin."""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)
            
            usage_data = await self.usage_repo.get_by_installation_and_timerange(
                installation_id, start_time, end_time
            )
            
            if not usage_data:
                return {"trend": "no_data", "data": []}
            
            # Calculate trend
            values = []
            if metric == "cpu_usage":
                values = [u.cpu_usage_percent for u in usage_data]
            elif metric == "memory_usage":
                values = [u.memory_usage_mb for u in usage_data]
            elif metric == "disk_usage":
                values = [u.disk_usage_mb for u in usage_data]
            elif metric == "network_usage":
                values = [u.network_in_mb + u.network_out_mb for u in usage_data]
            
            if len(values) < 2:
                return {"trend": "insufficient_data", "data": values}
            
            # Simple trend calculation
            first_half_avg = sum(values[:len(values)//2]) / (len(values)//2)
            second_half_avg = sum(values[len(values)//2:]) / (len(values) - len(values)//2)
            
            trend_direction = "increasing" if second_half_avg > first_half_avg else "decreasing"
            trend_percentage = ((second_half_avg - first_half_avg) / first_half_avg) * 100 if first_half_avg > 0 else 0
            
            return {
                "installation_id": installation_id,
                "metric": metric,
                "trend": trend_direction,
                "trend_percentage": round(trend_percentage, 2),
                "current_value": values[-1],
                "average_value": sum(values) / len(values),
                "data_points": len(values),
                "time_range": f"{days} days"
            }
            
        except Exception as e:
            logger.error(f"Failed to get resource trends: {e}")
            return {"error": str(e)}