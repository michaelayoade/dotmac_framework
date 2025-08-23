"""
Background tasks for monitoring operations.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from uuid import UUID

from celery import current_task
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from ...core.config import settings
from ...services.monitoring_service import MonitoringService
from ...workers.celery_app import celery_app

logger = logging.getLogger(__name__)

# Create async database session for workers
engine = create_async_engine(settings.database_url)
async_session = async_sessionmaker(engine, expire_on_commit=False)


@celery_app.task(bind=True, max_retries=3)
def process_metrics_batch(self, metrics_batch: List[Dict[str, Any]]):
    """Process a batch of metrics asynchronously."""
    import asyncio
    
    async def _process_metrics():
        async with async_session() as db:
            try:
                service = MonitoringService(db)
                
                # Convert dict metrics to MetricCreate objects
                from ...schemas.monitoring import MetricCreate
                metrics = [MetricCreate(**metric_data) for metric_data in metrics_batch]
                
                # Ingest metrics
                success = await service.ingest_metrics(metrics, "batch_processor")
                
                if success:
                    # Process alert rules for new metrics
                    await service._evaluate_alert_rules(metrics)
                    
                    logger.info(f"Processed metrics batch: {len(metrics)} metrics")
                    return {"processed": len(metrics), "status": "success"}
                else:
                    raise Exception("Failed to ingest metrics batch")
                
            except Exception as e:
                logger.error(f"Error processing metrics batch: {e}")
                raise self.retry(countdown=30, exc=e)
    
    return asyncio.run(_process_metrics())


@celery_app.task(bind=True, max_retries=3)
def evaluate_alert_rules(self, tenant_id: str = None):
    """Evaluate alert rules periodically."""
    import asyncio
    
    async def _evaluate_rules():
        async with async_session() as db:
            try:
                service = MonitoringService(db)
                
                # Get active alert rules
                filters = {"enabled": True}
                if tenant_id:
                    filters["tenant_id"] = UUID(tenant_id)
                
                alert_rules = await service.alert_rule_repo.list(filters=filters)
                
                alerts_triggered = 0
                rules_evaluated = 0
                
                for rule in alert_rules:
                    try:
                        # Get recent metrics for this rule
                        end_time = datetime.utcnow()
                        start_time = end_time - timedelta(seconds=rule.evaluation_interval * 2)
                        
                        metrics = await service.metric_repo.get_rule_metrics(
                            rule, start_time, end_time
                        )
                        
                        # Evaluate rule against metrics
                        for metric in metrics:
                            # Convert metric to MetricCreate for evaluation
                            from ...schemas.monitoring import MetricCreate
                            metric_create = MetricCreate(
                                tenant_id=metric.tenant_id,
                                service_name=metric.service_name,
                                metric_name=metric.metric_name,
                                metric_type=metric.metric_type,
                                value=metric.value,
                                timestamp=metric.timestamp,
                                labels=metric.labels,
                                unit=metric.unit
                            )
                            
                            violation = await service._check_rule_violation(rule, metric_create)
                            if violation:
                                await service._handle_alert_violation(rule, metric_create)
                                alerts_triggered += 1
                        
                        rules_evaluated += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to evaluate alert rule {rule.id}: {e}")
                
                logger.info(f"Alert evaluation completed: {rules_evaluated} rules evaluated, {alerts_triggered} alerts triggered")
                return {"rules_evaluated": rules_evaluated, "alerts_triggered": alerts_triggered}
                
            except Exception as e:
                logger.error(f"Error evaluating alert rules: {e}")
                raise self.retry(countdown=60, exc=e)
    
    return asyncio.run(_evaluate_rules())


@celery_app.task(bind=True, max_retries=3)
def cleanup_old_metrics(self, retention_days: int = 30):
    """Clean up old metrics data."""
    import asyncio
    
    async def _cleanup_metrics():
        async with async_session() as db:
            try:
                service = MonitoringService(db)
                
                cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
                
                # Clean up old metrics
                deleted_count = await service.metric_repo.delete_old_metrics(cutoff_date)
                
                logger.info(f"Metrics cleanup completed: {deleted_count} metrics deleted")
                return {"deleted_count": deleted_count}
                
            except Exception as e:
                logger.error(f"Error cleaning up metrics: {e}")
                raise self.retry(countdown=60, exc=e)
    
    return asyncio.run(_cleanup_metrics())


@celery_app.task(bind=True, max_retries=3)
def cleanup_old_logs(self, retention_days: int = 7):
    """Clean up old log entries."""
    import asyncio
    
    async def _cleanup_logs():
        async with async_session() as db:
            try:
                service = MonitoringService(db)
                
                cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
                
                # Clean up old logs
                deleted_count = await service.log_repo.delete_old_logs(cutoff_date)
                
                logger.info(f"Logs cleanup completed: {deleted_count} log entries deleted")
                return {"deleted_count": deleted_count}
                
            except Exception as e:
                logger.error(f"Error cleaning up logs: {e}")
                raise self.retry(countdown=60, exc=e)
    
    return asyncio.run(_cleanup_logs())


@celery_app.task(bind=True, max_retries=3)
def aggregate_metrics(self, aggregation_window: int = 3600):
    """Aggregate metrics into time buckets."""
    import asyncio
    
    async def _aggregate_metrics():
        async with async_session() as db:
            try:
                service = MonitoringService(db)
                
                # Calculate aggregation period
                end_time = datetime.utcnow()
                start_time = end_time - timedelta(seconds=aggregation_window)
                
                # Get metrics to aggregate
                metrics = await service.metric_repo.get_metrics_for_aggregation(
                    start_time, end_time
                )
                
                # Group metrics by tenant, service, metric name
                aggregated_data = {}
                
                for metric in metrics:
                    key = f"{metric.tenant_id}:{metric.service_name}:{metric.metric_name}"
                    
                    if key not in aggregated_data:
                        aggregated_data[key] = {
                            "tenant_id": metric.tenant_id,
                            "service_name": metric.service_name,
                            "metric_name": metric.metric_name,
                            "values": [],
                            "count": 0,
                            "sum": 0,
                            "min": float('inf'),
                            "max": float('-inf')
                        }
                    
                    data = aggregated_data[key]
                    data["values"].append(metric.value)
                    data["count"] += 1
                    data["sum"] += metric.value
                    data["min"] = min(data["min"], metric.value)
                    data["max"] = max(data["max"], metric.value)
                
                # Store aggregated metrics
                aggregated_count = 0
                for key, data in aggregated_data.items():
                    try:
                        avg_value = data["sum"] / data["count"]
                        
                        # Create aggregated metric entry
                        aggregated_metric = {
                            "tenant_id": data["tenant_id"],
                            "service_name": data["service_name"],
                            "metric_name": f"{data['metric_name']}_avg_{aggregation_window}s",
                            "metric_type": "gauge",
                            "value": avg_value,
                            "timestamp": end_time,
                            "labels": {
                                "aggregation_window": str(aggregation_window),
                                "aggregation_type": "average"
                            },
                            "unit": "aggregated"
                        }
                        
                        await service.metric_repo.create(aggregated_metric, "aggregator")
                        aggregated_count += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to create aggregated metric for {key}: {e}")
                
                logger.info(f"Metrics aggregation completed: {aggregated_count} aggregated metrics created")
                return {"aggregated_count": aggregated_count}
                
            except Exception as e:
                logger.error(f"Error aggregating metrics: {e}")
                raise self.retry(countdown=60, exc=e)
    
    return asyncio.run(_aggregate_metrics())


@celery_app.task(bind=True, max_retries=3)
def run_synthetic_checks(self):
    """Run synthetic monitoring checks."""
    import asyncio
    
    async def _run_checks():
        async with async_session() as db:
            try:
                service = MonitoringService(db)
                
                # Get enabled synthetic checks
                checks = await service.synthetic_repo.get_enabled_checks()
                
                checks_run = 0
                checks_failed = 0
                
                for check in checks:
                    try:
                        # TODO: Implement actual synthetic check execution
                        # For now, simulate check execution
                        
                        check_result = {
                            "check_id": check.id,
                            "status": "success",  # Would be actual check result
                            "response_time": 150.0,  # Would be actual response time
                            "status_code": 200 if check.type == "http" else None,
                            "error_message": None,
                            "location": "us-east-1",
                            "timestamp": datetime.utcnow(),
                            "metadata": {"simulated": True}
                        }
                        
                        # Store check result
                        await service.synthetic_repo.create_result(check_result, "synthetic_runner")
                        
                        # Create metrics from check result
                        metrics = [
                            {
                                "tenant_id": check.tenant_id,
                                "service_name": "synthetic_monitoring",
                                "metric_name": "check_response_time",
                                "metric_type": "gauge",
                                "value": check_result["response_time"],
                                "timestamp": check_result["timestamp"],
                                "labels": {
                                    "check_name": check.name,
                                    "check_type": check.type,
                                    "target": check.target,
                                    "location": check_result["location"]
                                },
                                "unit": "milliseconds"
                            },
                            {
                                "tenant_id": check.tenant_id,
                                "service_name": "synthetic_monitoring", 
                                "metric_name": "check_status",
                                "metric_type": "gauge",
                                "value": 1.0 if check_result["status"] == "success" else 0.0,
                                "timestamp": check_result["timestamp"],
                                "labels": {
                                    "check_name": check.name,
                                    "check_type": check.type,
                                    "target": check.target,
                                    "location": check_result["location"]
                                },
                                "unit": "boolean"
                            }
                        ]
                        
                        from ...schemas.monitoring import MetricCreate
                        metric_objects = [MetricCreate(**m) for m in metrics]
                        await service.ingest_metrics(metric_objects, "synthetic_runner")
                        
                        checks_run += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to run synthetic check {check.id}: {e}")
                        checks_failed += 1
                
                logger.info(f"Synthetic checks completed: {checks_run} successful, {checks_failed} failed")
                return {"checks_run": checks_run, "checks_failed": checks_failed}
                
            except Exception as e:
                logger.error(f"Error running synthetic checks: {e}")
                raise self.retry(countdown=60, exc=e)
    
    return asyncio.run(_run_checks())


@celery_app.task(bind=True, max_retries=3)
def calculate_service_health_scores(self):
    """Calculate health scores for all services."""
    import asyncio
    
    async def _calculate_health():
        async with async_session() as db:
            try:
                service = MonitoringService(db)
                
                # Get all tenants with services
                tenants_with_services = await service.metric_repo.get_tenants_with_services()
                
                health_scores_calculated = 0
                
                for tenant_id in tenants_with_services:
                    try:
                        # Get services for tenant
                        services = await service.metric_repo.get_tenant_services(tenant_id)
                        
                        for service_name in services:
                            # Calculate health score
                            health_status = await service.get_service_health_status(
                                tenant_id, service_name
                            )
                            
                            # Store health score as metric
                            health_metric = {
                                "tenant_id": tenant_id,
                                "service_name": service_name,
                                "metric_name": "service_health_score",
                                "metric_type": "gauge",
                                "value": self._calculate_health_score(health_status),
                                "timestamp": datetime.utcnow(),
                                "labels": {
                                    "service": service_name,
                                    "status": health_status["status"]
                                },
                                "unit": "percentage"
                            }
                            
                            await service.metric_repo.create(health_metric, "health_calculator")
                            health_scores_calculated += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to calculate health for tenant {tenant_id}: {e}")
                
                logger.info(f"Service health calculation completed: {health_scores_calculated} scores calculated")
                return {"health_scores_calculated": health_scores_calculated}
                
            except Exception as e:
                logger.error(f"Error calculating service health scores: {e}")
                raise self.retry(countdown=60, exc=e)
    
    def _calculate_health_score(self, health_status: Dict[str, Any]) -> float:
        """Calculate numeric health score from health status."""
        base_score = 100.0
        
        # Deduct points for issues
        if health_status["uptime_percentage"] < 99.9:
            base_score -= (99.9 - health_status["uptime_percentage"]) * 2
        
        if health_status["error_rate"] > 1.0:
            base_score -= health_status["error_rate"] * 5
        
        if health_status["response_time_p95"] > 1000:
            base_score -= (health_status["response_time_p95"] - 1000) / 100
        
        if health_status["active_alerts"] > 0:
            base_score -= health_status["active_alerts"] * 10
        
        return max(0.0, min(100.0, base_score))
    
    return asyncio.run(_calculate_health())


@celery_app.task(bind=True, max_retries=3)
def export_monitoring_report(self, tenant_id: str, report_type: str, start_date: str, end_date: str):
    """Export monitoring report for a tenant."""
    import asyncio
    from datetime import datetime
    
    async def _export_report():
        async with async_session() as db:
            try:
                service = MonitoringService(db)
                
                start = datetime.fromisoformat(start_date)
                end = datetime.fromisoformat(end_date)
                tenant_uuid = UUID(tenant_id)
                
                if report_type == "metrics":
                    # Export metrics data
                    filters = {
                        "tenant_id": tenant_uuid,
                        "timestamp__gte": start,
                        "timestamp__lte": end
                    }
                    data = await service.metric_repo.list(filters=filters, limit=10000)
                    
                elif report_type == "alerts":
                    # Export alerts data
                    filters = {
                        "tenant_id": tenant_uuid,
                        "started_at__gte": start,
                        "started_at__lte": end
                    }
                    data = await service.alert_repo.list(filters=filters, limit=10000)
                    
                elif report_type == "logs":
                    # Export logs data
                    filters = {
                        "tenant_id": tenant_uuid,
                        "timestamp__gte": start,
                        "timestamp__lte": end
                    }
                    data = await service.log_repo.list(filters=filters, limit=10000)
                    
                else:
                    raise ValueError(f"Unknown report type: {report_type}")
                
                # TODO: Generate actual report file (CSV, JSON, etc.)
                # For now, return summary
                report_summary = {
                    "tenant_id": tenant_id,
                    "report_type": report_type,
                    "period": f"{start} to {end}",
                    "record_count": len(data),
                    "generated_at": datetime.utcnow().isoformat()
                }
                
                logger.info(f"Monitoring report exported: {report_type} for tenant {tenant_id}")
                return report_summary
                
            except Exception as e:
                logger.error(f"Error exporting monitoring report: {e}")
                raise self.retry(countdown=60, exc=e)
    
    return asyncio.run(_export_report())