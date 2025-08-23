"""SaaS monitoring service for tenant health checks and alerting."""

import asyncio
import logging
import aiohttp
import json
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func, desc
from sqlalchemy.orm import selectinload

from mgmt.shared.config import get_settings
from mgmt.services.kubernetes_orchestrator.models import TenantDeployment, DeploymentStatus
from .models import (
    TenantHealthCheck, MonitoringAlert, SLAMetrics, TenantMetricsSnapshot,
    HealthStatus, AlertSeverity, AlertStatus, MonitoringMetric
)
from .exceptions import (
    MonitoringError, HealthCheckFailedError, AlertingError, 
    MetricsCollectionError, SLAViolationError
)


logger = logging.getLogger(__name__)


class SaaSMonitoringService:
    """Service for monitoring tenant deployments and SLA compliance."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.settings = get_settings()
        self._http_session = None
        
        # Default SLA targets
        self.default_sla_targets = {
            "availability_percentage": Decimal('99.9'),
            "response_time_ms": 500,
            "error_rate_percentage": Decimal('1.0')
        }
        
        # Health check timeouts
        self.health_check_timeout = 30  # seconds
        self.max_concurrent_checks = 10
        
        # Cross-platform health correlation
        self.external_health_reports = {}  # tenant_id -> latest health data
        self.health_correlation_window = 300  # 5 minutes
    
    async def _get_http_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session for health checks."""
        if self._http_session is None or self._http_session.closed:
            timeout = aiohttp.ClientTimeout(total=self.health_check_timeout)
            self._http_session = aiohttp.ClientSession(timeout=timeout)
        return self._http_session
    
    async def perform_tenant_health_check(self, tenant_id: str, 
                                        deployment: Optional[TenantDeployment] = None) -> TenantHealthCheck:
        """Perform comprehensive health check for tenant deployment."""
        try:
            logger.debug(f"Starting health check for tenant: {tenant_id}")
            
            # Get deployment info if not provided
            if not deployment:
                result = await self.session.execute(
                    select(TenantDeployment).where(TenantDeployment.tenant_id == tenant_id)
                )
                deployment = result.scalar_one_or_none()
                
                if not deployment:
                    raise HealthCheckFailedError(f"No deployment found for tenant: {tenant_id}")
            
            # Generate check ID
            check_id = f"hc-{tenant_id}-{int(datetime.utcnow().timestamp())}"
            
            # Perform individual health checks
            health_results = await self._perform_comprehensive_checks(deployment)
            
            # Determine overall status
            overall_status = self._calculate_overall_health_status(health_results)
            
            # Check SLA compliance
            sla_compliant, sla_violations = await self._check_sla_compliance(tenant_id, health_results)
            
            # Create health check record
            health_check = TenantHealthCheck(
                tenant_id=tenant_id,
                check_id=check_id,
                service_name=deployment.deployment_name,
                overall_status=overall_status,
                response_time_ms=health_results.get("response_time_ms"),
                uptime_seconds=health_results.get("uptime_seconds"),
                cpu_usage_percent=health_results.get("cpu_usage_percent"),
                memory_usage_percent=health_results.get("memory_usage_percent"),
                disk_usage_percent=health_results.get("disk_usage_percent"),
                database_status=health_results.get("database_status"),
                redis_status=health_results.get("redis_status"),
                external_apis_status=health_results.get("external_apis_status"),
                active_sessions=health_results.get("active_sessions"),
                queue_size=health_results.get("queue_size"),
                error_count=health_results.get("error_count", 0),
                warning_count=health_results.get("warning_count", 0),
                check_details=health_results,
                failed_checks=health_results.get("failed_checks", []),
                sla_compliant=sla_compliant,
                sla_violations=sla_violations,
                deployment_version=deployment.image_tag,
                kubernetes_namespace=deployment.namespace,
                check_source="automatic"
            )
            
            self.session.add(health_check)
            
            # Update deployment health status
            if overall_status == HealthStatus.HEALTHY:
                deployment.mark_healthy()
            else:
                deployment.mark_unhealthy(f"Health check failed: {overall_status.value}")
            
            await self.session.commit()
            
            # Generate alerts if needed
            if overall_status != HealthStatus.HEALTHY:
                await self._generate_health_alert(tenant_id, health_check, deployment)
            
            # Check for SLA violations and alert
            if not sla_compliant:
                await self._handle_sla_violations(tenant_id, sla_violations, health_check)
            
            logger.info(f"Health check completed for tenant {tenant_id}: {overall_status.value}")
            return health_check
            
        except Exception as e:
            logger.error(f"Health check failed for tenant {tenant_id}: {str(e)}")
            raise HealthCheckFailedError(f"Health check failed: {str(e)}")
    
    async def record_external_health_report(self, tenant_id: str, component: str, 
                                          status: str, metrics: Dict[str, Any], 
                                          details: Optional[str] = None, 
                                          timestamp: Optional[datetime] = None) -> bool:
        """Record health status report from ISP Framework instance."""
        try:
            timestamp = timestamp or datetime.utcnow()
            
            # Store external health report
            if tenant_id not in self.external_health_reports:
                self.external_health_reports[tenant_id] = {}
            
            self.external_health_reports[tenant_id][component] = {
                "status": status,
                "metrics": metrics,
                "details": details,
                "timestamp": timestamp,
                "component": component
            }
            
            # Clean up old reports (older than correlation window)
            cutoff_time = timestamp - timedelta(seconds=self.health_correlation_window)
            for component_data in list(self.external_health_reports[tenant_id].values()):
                if component_data["timestamp"] < cutoff_time:
                    component_key = component_data["component"]
                    del self.external_health_reports[tenant_id][component_key]
            
            logger.debug(f"Recorded external health report: {tenant_id}/{component} = {status}")
            
            # Trigger health correlation analysis
            await self._correlate_health_status(tenant_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Error recording external health report: {str(e)}")
            return False
    
    async def _correlate_health_status(self, tenant_id: str) -> Dict[str, Any]:
        """Correlate health status between Management Platform and ISP Framework."""
        try:
            # Get latest external health reports
            external_reports = self.external_health_reports.get(tenant_id, {})
            
            # Get latest Management Platform health check
            result = await self.session.execute(
                select(TenantHealthCheck)
                .where(TenantHealthCheck.tenant_id == tenant_id)
                .order_by(desc(TenantHealthCheck.checked_at))
                .limit(1)
            )
            mgmt_health = result.scalar_one_or_none()
            
            # Correlate health data
            correlation = {
                "tenant_id": tenant_id,
                "correlation_timestamp": datetime.utcnow(),
                "management_platform": {
                    "available": mgmt_health is not None,
                    "status": mgmt_health.overall_status.value if mgmt_health else "unknown",
                    "timestamp": mgmt_health.checked_at if mgmt_health else None,
                    "response_time_ms": float(mgmt_health.response_time_ms) if mgmt_health and mgmt_health.response_time_ms else None
                },
                "isp_framework": {
                    "available": len(external_reports) > 0,
                    "components": external_reports,
                    "overall_status": self._determine_external_overall_status(external_reports)
                },
                "consistency": {
                    "status_match": False,
                    "data_freshness": "unknown",
                    "discrepancies": []
                }
            }
            
            # Analyze consistency
            if mgmt_health and external_reports:
                mgmt_status = mgmt_health.overall_status.value
                external_status = correlation["isp_framework"]["overall_status"]
                
                correlation["consistency"]["status_match"] = mgmt_status == external_status
                
                # Check data freshness
                mgmt_age = (datetime.utcnow() - mgmt_health.checked_at).total_seconds()
                external_ages = [(datetime.utcnow() - report["timestamp"]).total_seconds() 
                               for report in external_reports.values()]
                avg_external_age = sum(external_ages) / len(external_ages) if external_ages else 0
                
                if mgmt_age < 60 and avg_external_age < 60:
                    correlation["consistency"]["data_freshness"] = "fresh"
                elif mgmt_age < 300 and avg_external_age < 300:
                    correlation["consistency"]["data_freshness"] = "recent"
                else:
                    correlation["consistency"]["data_freshness"] = "stale"
                
                # Identify discrepancies
                if not correlation["consistency"]["status_match"]:
                    correlation["consistency"]["discrepancies"].append(
                        f"Status mismatch: Management Platform={mgmt_status}, ISP Framework={external_status}"
                    )
                
                # Check for component-specific discrepancies
                if mgmt_health.database_status and "database" in external_reports:
                    db_report = external_reports["database"]
                    if mgmt_health.database_status != db_report["status"]:
                        correlation["consistency"]["discrepancies"].append(
                            f"Database status mismatch: MP={mgmt_health.database_status}, ISP={db_report['status']}"
                        )
            
            # Store correlation result
            correlation_record = {
                "tenant_id": tenant_id,
                "correlation_data": correlation,
                "created_at": datetime.utcnow()
            }
            
            # Log significant discrepancies
            if correlation["consistency"]["discrepancies"]:
                logger.warning(f"Health status discrepancies detected for {tenant_id}: {correlation['consistency']['discrepancies']}")
            
            return correlation
            
        except Exception as e:
            logger.error(f"Error correlating health status for {tenant_id}: {str(e)}")
            return {}
    
    def _determine_external_overall_status(self, external_reports: Dict[str, Dict[str, Any]]) -> str:
        """Determine overall status from external component reports."""
        if not external_reports:
            return "unknown"
        
        statuses = [report["status"] for report in external_reports.values()]
        
        # Priority: unhealthy > warning > healthy
        if "unhealthy" in statuses:
            return "unhealthy"
        elif "warning" in statuses:
            return "warning"
        elif "healthy" in statuses:
            return "healthy"
        else:
            return "unknown"
    
    async def get_health_correlation_summary(self, tenant_id: str) -> Dict[str, Any]:
        """Get health correlation summary for tenant."""
        try:
            # Get latest correlation data
            correlation = await self._correlate_health_status(tenant_id)
            
            # Get historical health checks
            result = await self.session.execute(
                select(TenantHealthCheck)
                .where(TenantHealthCheck.tenant_id == tenant_id)
                .order_by(desc(TenantHealthCheck.checked_at))
                .limit(10)
            )
            recent_checks = result.scalars().all()
            
            # Calculate health trend
            if len(recent_checks) >= 2:
                recent_statuses = [check.overall_status.value for check in recent_checks[:5]]
                if all(status == "healthy" for status in recent_statuses):
                    trend = "stable_healthy"
                elif all(status in ["unhealthy", "warning"] for status in recent_statuses):
                    trend = "stable_unhealthy"
                else:
                    trend = "fluctuating"
            else:
                trend = "insufficient_data"
            
            return {
                "tenant_id": tenant_id,
                "current_correlation": correlation,
                "health_trend": trend,
                "recent_checks_count": len(recent_checks),
                "external_components": list(self.external_health_reports.get(tenant_id, {}).keys()),
                "last_management_check": recent_checks[0].checked_at.isoformat() if recent_checks else None,
                "summary": {
                    "consistent": correlation.get("consistency", {}).get("status_match", False),
                    "data_fresh": correlation.get("consistency", {}).get("data_freshness") == "fresh",
                    "discrepancy_count": len(correlation.get("consistency", {}).get("discrepancies", []))
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting health correlation summary: {str(e)}")
            return {"error": str(e)}
    
    async def _perform_comprehensive_checks(self, deployment: TenantDeployment) -> Dict[str, Any]:
        """Perform all health checks for a deployment."""
        results = {
            "failed_checks": [],
            "warning_count": 0,
            "error_count": 0
        }
        
        # HTTP endpoint health check
        http_result = await self._check_http_endpoint(deployment)
        results.update(http_result)
        
        # Kubernetes metrics check
        k8s_result = await self._check_kubernetes_metrics(deployment)
        results.update(k8s_result)
        
        # Database connectivity check (simulate)
        db_result = await self._check_database_connectivity(deployment)
        results.update(db_result)
        
        # Redis connectivity check (simulate)
        redis_result = await self._check_redis_connectivity(deployment)
        results.update(redis_result)
        
        # External API checks (simulate)
        api_result = await self._check_external_apis(deployment)
        results.update(api_result)
        
        return results
    
    async def _check_http_endpoint(self, deployment: TenantDeployment) -> Dict[str, Any]:
        """Check HTTP endpoint health."""
        try:
            # Construct health check URL
            if deployment.domain_name:
                url = f"https://{deployment.domain_name}/health"
            else:
                # Use internal service URL (would need proper cluster access)
                url = f"http://{deployment.deployment_name}.{deployment.namespace}.svc.cluster.local/health"
            
            session = await self._get_http_session()
            start_time = datetime.utcnow()
            
            async with session.get(url, headers={"X-Tenant-ID": deployment.tenant_id}) as response:
                end_time = datetime.utcnow()
                response_time_ms = int((end_time - start_time).total_seconds() * 1000)
                
                if response.status == 200:
                    data = await response.json()
                    
                    return {
                        "response_time_ms": response_time_ms,
                        "endpoint_status": HealthStatus.HEALTHY,
                        "endpoint_details": data
                    }
                else:
                    return {
                        "response_time_ms": response_time_ms,
                        "endpoint_status": HealthStatus.UNHEALTHY,
                        "failed_checks": ["http_endpoint"],
                        "error_count": 1,
                        "endpoint_error": f"HTTP {response.status}"
                    }
                    
        except asyncio.TimeoutError:
            return {
                "endpoint_status": HealthStatus.UNHEALTHY,
                "failed_checks": ["http_endpoint"],
                "error_count": 1,
                "endpoint_error": "Timeout"
            }
        except Exception as e:
            return {
                "endpoint_status": HealthStatus.UNHEALTHY,
                "failed_checks": ["http_endpoint"], 
                "error_count": 1,
                "endpoint_error": str(e)
            }
    
    async def _check_kubernetes_metrics(self, deployment: TenantDeployment) -> Dict[str, Any]:
        """Check Kubernetes pod metrics (simulated)."""
        # In real implementation, this would use Kubernetes API or metrics server
        # For now, simulate realistic metrics
        import random
        
        # Simulate resource usage based on deployment tier
        if deployment.resource_tier.value == "micro":
            cpu_base, memory_base = 30, 40
        elif deployment.resource_tier.value == "small":
            cpu_base, memory_base = 50, 60
        else:
            cpu_base, memory_base = 70, 80
        
        cpu_usage = cpu_base + random.uniform(-15, 25)
        memory_usage = memory_base + random.uniform(-20, 30)
        disk_usage = random.uniform(10, 60)
        
        # Determine status based on usage
        resource_status = HealthStatus.HEALTHY
        if cpu_usage > 90 or memory_usage > 90:
            resource_status = HealthStatus.UNHEALTHY
        elif cpu_usage > 80 or memory_usage > 80:
            resource_status = HealthStatus.DEGRADED
        
        return {
            "cpu_usage_percent": round(cpu_usage, 2),
            "memory_usage_percent": round(memory_usage, 2),
            "disk_usage_percent": round(disk_usage, 2),
            "resource_status": resource_status,
            "uptime_seconds": random.randint(3600, 604800)  # 1 hour to 1 week
        }
    
    async def _check_database_connectivity(self, deployment: TenantDeployment) -> Dict[str, Any]:
        """Check database connectivity (simulated)."""
        # In real implementation, this would test actual database connection
        # Simulate based on deployment health
        import random
        
        if random.random() > 0.95:  # 5% chance of DB issues
            return {
                "database_status": HealthStatus.UNHEALTHY,
                "failed_checks": ["database"],
                "error_count": 1,
                "database_error": "Connection timeout"
            }
        elif random.random() > 0.9:  # 5% chance of degraded performance
            return {
                "database_status": HealthStatus.DEGRADED,
                "warning_count": 1,
                "database_response_time_ms": random.randint(1000, 3000)
            }
        else:
            return {
                "database_status": HealthStatus.HEALTHY,
                "database_response_time_ms": random.randint(10, 100)
            }
    
    async def _check_redis_connectivity(self, deployment: TenantDeployment) -> Dict[str, Any]:
        """Check Redis connectivity (simulated)."""
        import random
        
        if random.random() > 0.98:  # 2% chance of Redis issues
            return {
                "redis_status": HealthStatus.UNHEALTHY,
                "failed_checks": ["redis"],
                "error_count": 1,
                "redis_error": "Connection refused"
            }
        else:
            return {
                "redis_status": HealthStatus.HEALTHY,
                "redis_response_time_ms": random.randint(1, 10)
            }
    
    async def _check_external_apis(self, deployment: TenantDeployment) -> Dict[str, Any]:
        """Check external API connectivity (simulated)."""
        import random
        
        if random.random() > 0.96:  # 4% chance of external API issues
            return {
                "external_apis_status": HealthStatus.DEGRADED,
                "warning_count": 1,
                "external_api_error": "Some APIs responding slowly"
            }
        else:
            return {
                "external_apis_status": HealthStatus.HEALTHY,
                "active_sessions": random.randint(1, 50),
                "queue_size": random.randint(0, 10)
            }
    
    def _calculate_overall_health_status(self, results: Dict[str, Any]) -> HealthStatus:
        """Calculate overall health status from check results."""
        error_count = results.get("error_count", 0)
        failed_checks = results.get("failed_checks", [])
        
        if error_count > 0 or len(failed_checks) > 0:
            return HealthStatus.UNHEALTHY
        
        warning_count = results.get("warning_count", 0)
        if warning_count > 0:
            return HealthStatus.DEGRADED
        
        # Check individual service statuses
        statuses = [
            results.get("endpoint_status"),
            results.get("resource_status"),
            results.get("database_status"),
            results.get("redis_status"),
            results.get("external_apis_status")
        ]
        
        statuses = [s for s in statuses if s is not None]
        
        if any(s == HealthStatus.UNHEALTHY for s in statuses):
            return HealthStatus.UNHEALTHY
        elif any(s == HealthStatus.DEGRADED for s in statuses):
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY
    
    async def _check_sla_compliance(self, tenant_id: str, 
                                  health_results: Dict[str, Any]) -> Tuple[bool, Optional[List[Dict]]]:
        """Check if tenant is meeting SLA requirements."""
        violations = []
        
        # Check response time SLA
        response_time = health_results.get("response_time_ms")
        if response_time and response_time > self.default_sla_targets["response_time_ms"]:
            violations.append({
                "type": "response_time",
                "actual_value": response_time,
                "sla_target": self.default_sla_targets["response_time_ms"],
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # Check availability (based on health status)
        if health_results.get("error_count", 0) > 0:
            violations.append({
                "type": "availability",
                "description": "Service experiencing errors",
                "error_count": health_results.get("error_count"),
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # Check resource usage SLA
        cpu_usage = health_results.get("cpu_usage_percent")
        if cpu_usage and cpu_usage > 95:
            violations.append({
                "type": "resource_usage",
                "metric": "cpu",
                "actual_value": cpu_usage,
                "threshold": 95,
                "timestamp": datetime.utcnow().isoformat()
            })
        
        is_compliant = len(violations) == 0
        return is_compliant, violations if violations else None
    
    async def _generate_health_alert(self, tenant_id: str, health_check: TenantHealthCheck,
                                   deployment: TenantDeployment):
        """Generate alert for health check failures."""
        try:
            # Determine alert severity
            if health_check.overall_status == HealthStatus.UNHEALTHY:
                severity = AlertSeverity.CRITICAL
            elif health_check.overall_status == HealthStatus.DEGRADED:
                severity = AlertSeverity.WARNING
            else:
                severity = AlertSeverity.INFO
            
            # Create alert
            alert_id = f"health-{tenant_id}-{int(datetime.utcnow().timestamp())}"
            
            alert = MonitoringAlert(
                tenant_id=tenant_id,
                alert_id=alert_id,
                alert_name=f"Health Check Failed - {deployment.deployment_name}",
                alert_description=f"Health check failed for tenant {tenant_id}: {health_check.overall_status.value}",
                severity=severity,
                source_service=deployment.deployment_name,
                deployment_id=deployment.id,
                health_check_id=health_check.id,
                alert_data={
                    "failed_checks": health_check.failed_checks,
                    "error_count": health_check.error_count,
                    "warning_count": health_check.warning_count,
                    "check_details": health_check.check_details
                }
            )
            
            self.session.add(alert)
            await self.session.commit()
            
            logger.warning(f"Health alert generated for tenant {tenant_id}: {alert_id}")
            
        except Exception as e:
            logger.error(f"Failed to generate health alert: {str(e)}")
    
    async def _handle_sla_violations(self, tenant_id: str, violations: List[Dict],
                                   health_check: TenantHealthCheck):
        """Handle SLA violations with appropriate alerts."""
        try:
            for violation in violations:
                alert_id = f"sla-{tenant_id}-{violation['type']}-{int(datetime.utcnow().timestamp())}"
                
                alert = MonitoringAlert(
                    tenant_id=tenant_id,
                    alert_id=alert_id,
                    alert_name=f"SLA Violation - {violation['type'].title()}",
                    alert_description=f"SLA violation detected: {violation.get('description', violation['type'])}",
                    severity=AlertSeverity.ERROR,
                    source_service=health_check.service_name,
                    metric_name=violation['type'],
                    metric_value=violation.get('actual_value'),
                    threshold_value=violation.get('sla_target'),
                    health_check_id=health_check.id,
                    alert_data=violation
                )
                
                self.session.add(alert)
            
            await self.session.commit()
            logger.warning(f"SLA violation alerts generated for tenant {tenant_id}: {len(violations)} violations")
            
        except Exception as e:
            logger.error(f"Failed to handle SLA violations: {str(e)}")
    
    async def get_tenant_health_history(self, tenant_id: str, 
                                      hours: int = 24) -> List[TenantHealthCheck]:
        """Get health check history for tenant."""
        since = datetime.utcnow() - timedelta(hours=hours)
        
        result = await self.session.execute(
            select(TenantHealthCheck)
            .where(
                and_(
                    TenantHealthCheck.tenant_id == tenant_id,
                    TenantHealthCheck.check_timestamp >= since
                )
            )
            .order_by(desc(TenantHealthCheck.check_timestamp))
        )
        
        return result.scalars().all()
    
    async def get_active_alerts(self, tenant_id: Optional[str] = None,
                               severity: Optional[AlertSeverity] = None) -> List[MonitoringAlert]:
        """Get active alerts, optionally filtered by tenant and severity."""
        query = select(MonitoringAlert).where(MonitoringAlert.status == AlertStatus.ACTIVE)
        
        if tenant_id:
            query = query.where(MonitoringAlert.tenant_id == tenant_id)
            
        if severity:
            query = query.where(MonitoringAlert.severity == severity)
        
        query = query.order_by(desc(MonitoringAlert.first_occurred))
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def calculate_sla_metrics(self, tenant_id: str, 
                                  period: str = "daily",
                                  date_: Optional[date] = None) -> SLAMetrics:
        """Calculate SLA metrics for specified period."""
        try:
            if not date_:
                date_ = date.today()
            
            # Determine period boundaries
            if period == "daily":
                period_start = datetime.combine(date_, datetime.min.time())
                period_end = period_start + timedelta(days=1)
            elif period == "weekly":
                # Start of week (Monday)
                days_since_monday = date_.weekday()
                week_start = date_ - timedelta(days=days_since_monday)
                period_start = datetime.combine(week_start, datetime.min.time())
                period_end = period_start + timedelta(weeks=1)
            elif period == "monthly":
                period_start = datetime.combine(date_.replace(day=1), datetime.min.time())
                if date_.month == 12:
                    next_month = date_.replace(year=date_.year + 1, month=1)
                else:
                    next_month = date_.replace(month=date_.month + 1)
                period_end = datetime.combine(next_month, datetime.min.time())
            else:
                raise ValueError("Invalid period. Use 'daily', 'weekly', or 'monthly'")
            
            # Get health checks for period
            health_checks = await self.session.execute(
                select(TenantHealthCheck)
                .where(
                    and_(
                        TenantHealthCheck.tenant_id == tenant_id,
                        TenantHealthCheck.check_timestamp >= period_start,
                        TenantHealthCheck.check_timestamp < period_end
                    )
                )
            )
            
            checks = health_checks.scalars().all()
            
            if not checks:
                # No data for period, return default metrics
                return self._create_default_sla_metrics(tenant_id, period, period_start, period_end)
            
            # Calculate metrics
            total_checks = len(checks)
            healthy_checks = len([c for c in checks if c.overall_status == HealthStatus.HEALTHY])
            
            # Response time metrics
            response_times = [c.response_time_ms for c in checks if c.response_time_ms]
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            
            # Calculate percentiles
            if response_times:
                response_times.sort()
                p95_index = int(len(response_times) * 0.95)
                p99_index = int(len(response_times) * 0.99)
                p95_response_time = response_times[min(p95_index, len(response_times) - 1)]
                p99_response_time = response_times[min(p99_index, len(response_times) - 1)]
                max_response_time = max(response_times)
            else:
                p95_response_time = p99_response_time = max_response_time = 0
            
            # Calculate uptime
            total_minutes = int((period_end - period_start).total_seconds() / 60)
            downtime_checks = [c for c in checks if c.overall_status == HealthStatus.UNHEALTHY]
            downtime_minutes = len(downtime_checks) * 5  # Assume 5 min intervals
            uptime_percentage = ((total_minutes - downtime_minutes) / total_minutes * 100) if total_minutes > 0 else 100
            
            # Error calculations
            total_errors = sum(c.error_count for c in checks)
            error_rate = (total_errors / total_checks * 100) if total_checks > 0 else 0
            
            # SLA compliance
            availability_target = self.default_sla_targets["availability_percentage"]
            response_time_target = self.default_sla_targets["response_time_ms"]
            error_rate_target = self.default_sla_targets["error_rate_percentage"]
            
            availability_met = Decimal(str(uptime_percentage)) >= availability_target
            response_time_met = avg_response_time <= response_time_target
            error_rate_met = Decimal(str(error_rate)) <= error_rate_target
            
            # Get alerts for period
            alerts = await self.session.execute(
                select(MonitoringAlert)
                .where(
                    and_(
                        MonitoringAlert.tenant_id == tenant_id,
                        MonitoringAlert.first_occurred >= period_start,
                        MonitoringAlert.first_occurred < period_end
                    )
                )
            )
            
            alert_list = alerts.scalars().all()
            critical_alerts = len([a for a in alert_list if a.severity == AlertSeverity.CRITICAL])
            resolved_alerts = len([a for a in alert_list if a.status == AlertStatus.RESOLVED])
            
            # Calculate average resolution time
            resolved_alert_times = [
                (a.resolved_at - a.first_occurred).total_seconds() / 60
                for a in alert_list if a.resolved_at
            ]
            avg_resolution_time = sum(resolved_alert_times) / len(resolved_alert_times) if resolved_alert_times else None
            
            # Create SLA metrics record
            sla_metrics = SLAMetrics(
                tenant_id=tenant_id,
                measurement_period=period,
                period_start=period_start,
                period_end=period_end,
                uptime_percentage=Decimal(str(uptime_percentage)).quantize(Decimal('0.01')),
                downtime_minutes=downtime_minutes,
                total_minutes=total_minutes,
                avg_response_time_ms=avg_response_time,
                p95_response_time_ms=p95_response_time,
                p99_response_time_ms=p99_response_time,
                max_response_time_ms=max_response_time,
                total_requests=total_checks * 100,  # Estimate
                successful_requests=healthy_checks * 100,
                error_requests=total_errors,
                error_rate_percentage=Decimal(str(error_rate)).quantize(Decimal('0.01')),
                availability_sla_target=availability_target,
                response_time_sla_target_ms=response_time_target,
                error_rate_sla_target=error_rate_target,
                availability_sla_met=availability_met,
                response_time_sla_met=response_time_met,
                error_rate_sla_met=error_rate_met,
                overall_sla_met=availability_met and response_time_met and error_rate_met,
                health_checks_performed=total_checks,
                health_checks_passed=healthy_checks,
                health_checks_failed=total_checks - healthy_checks,
                alerts_generated=len(alert_list),
                critical_alerts=critical_alerts,
                alerts_resolved=resolved_alerts,
                avg_alert_resolution_minutes=avg_resolution_time
            )
            
            # Save metrics
            self.session.add(sla_metrics)
            await self.session.commit()
            
            logger.info(f"Calculated {period} SLA metrics for tenant {tenant_id}")
            return sla_metrics
            
        except Exception as e:
            logger.error(f"Error calculating SLA metrics: {str(e)}")
            raise MetricsCollectionError(f"Failed to calculate SLA metrics: {str(e)}")
    
    def _create_default_sla_metrics(self, tenant_id: str, period: str,
                                  period_start: datetime, period_end: datetime) -> SLAMetrics:
        """Create default SLA metrics when no data is available."""
        total_minutes = int((period_end - period_start).total_seconds() / 60)
        
        return SLAMetrics(
            tenant_id=tenant_id,
            measurement_period=period,
            period_start=period_start,
            period_end=period_end,
            uptime_percentage=Decimal('100.00'),
            downtime_minutes=0,
            total_minutes=total_minutes,
            overall_sla_met=True,
            availability_sla_met=True,
            response_time_sla_met=True,
            error_rate_sla_met=True
        )
    
    async def run_health_checks_for_all_tenants(self) -> Dict[str, Any]:
        """Run health checks for all active tenant deployments."""
        try:
            # Get all active deployments
            result = await self.session.execute(
                select(TenantDeployment).where(
                    TenantDeployment.status.in_([
                        DeploymentStatus.RUNNING,
                        DeploymentStatus.DEGRADED
                    ])
                )
            )
            
            deployments = result.scalars().all()
            
            if not deployments:
                logger.info("No active deployments found for health checks")
                return {"total_checked": 0, "healthy": 0, "unhealthy": 0}
            
            # Run health checks concurrently with limit
            semaphore = asyncio.Semaphore(self.max_concurrent_checks)
            
            async def check_deployment(deployment):
                async with semaphore:
                    try:
                        return await self.perform_tenant_health_check(deployment.tenant_id, deployment)
                    except Exception as e:
                        logger.error(f"Health check failed for {deployment.tenant_id}: {str(e)}")
                        return None
            
            # Execute health checks
            health_checks = await asyncio.gather(
                *[check_deployment(d) for d in deployments],
                return_exceptions=True
            )
            
            # Count results
            total_checked = len([hc for hc in health_checks if hc is not None])
            healthy = len([hc for hc in health_checks if hc and hc.is_healthy])
            unhealthy = total_checked - healthy
            
            logger.info(f"Health checks completed: {total_checked} checked, {healthy} healthy, {unhealthy} unhealthy")
            
            return {
                "total_checked": total_checked,
                "healthy": healthy,
                "unhealthy": unhealthy,
                "results": [hc for hc in health_checks if hc is not None]
            }
            
        except Exception as e:
            logger.error(f"Error running health checks for all tenants: {str(e)}")
            raise MonitoringError(f"Failed to run health checks: {str(e)}")
    
    async def close(self):
        """Clean up resources."""
        if self._http_session and not self._http_session.closed:
            await self._http_session.close()