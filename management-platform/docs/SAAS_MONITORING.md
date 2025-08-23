# SaaS Monitoring & Health Check Documentation

The DotMac Management Platform includes a comprehensive monitoring system designed for multi-tenant SaaS environments, providing real-time health checks, SLA compliance tracking, and automated alerting across all tenant deployments.

## 🎯 **Overview**

The SaaS monitoring system ensures reliable service delivery across all tenant instances while maintaining complete privacy isolation and providing actionable insights for platform optimization.

### **Key Capabilities**

- **Multi-Tenant Health Monitoring**: Continuous health checks for all tenant deployments
- **SLA Compliance Tracking**: Automated SLA metrics calculation and violation detection
- **Real-Time Alerting**: Severity-based alerting with automated escalation
- **Performance Analytics**: Comprehensive performance monitoring and optimization insights
- **Privacy-Preserving Analytics**: Cross-tenant insights while maintaining data isolation

## 🏗️ **Architecture**

### **Monitoring Components**

```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│   Health Check      │    │   Alert Manager     │    │   SLA Calculator    │
│   Orchestrator      │    │                     │    │                     │
│   ┌─────────────┐   │    │ ┌─────────────────┐ │    │ ┌─────────────────┐ │
│   │ HTTP Checks │   │────│ │ Severity Router │ │────│ │ Uptime Tracker  │ │
│   │ K8s Metrics│   │    │ │ Escalation Eng. │ │    │ │ Response Times  │ │
│   │ DB Conn     │   │    │ │ Notification    │ │    │ │ Error Rates     │ │
│   │ Redis Conn  │   │    │ └─────────────────┘ │    │ └─────────────────┘ │
│   └─────────────┘   │    └─────────────────────┘    └─────────────────────┘
└─────────────────────┘                               
           │                                                     │
           v                                                     v
┌─────────────────────┐                               ┌─────────────────────┐
│ Metrics Collection  │                               │  Compliance         │
│                     │                               │  Dashboard          │
│ ┌─────────────────┐ │                               │                     │
│ │ Performance     │ │                               │ ┌─────────────────┐ │
│ │ Resource Usage  │ │                               │ │ SLA Reports     │ │
│ │ Business KPIs   │ │                               │ │ Violation Alerts│ │
│ └─────────────────┘ │                               │ │ Trend Analysis  │ │
└─────────────────────┘                               └─────────────────────┘
```

### **Health Check Types**

```python
class HealthCheckType(enum.Enum):
    HTTP_ENDPOINT = "http_endpoint"
    KUBERNETES_METRICS = "kubernetes_metrics"
    DATABASE_CONNECTIVITY = "database_connectivity"
    REDIS_CONNECTIVITY = "redis_connectivity"
    EXTERNAL_APIS = "external_apis"
    PLUGIN_VALIDATION = "plugin_validation"
    BUSINESS_LOGIC = "business_logic"
```

## 📊 **SLA Metrics & Compliance**

### **Standard SLA Targets**

```python
DEFAULT_SLA_TARGETS = {
    "availability_percentage": Decimal("99.9"),    # 99.9% uptime
    "response_time_ms": 500,                       # 500ms average response
    "error_rate_percentage": Decimal("1.0"),       # <1% error rate
    "recovery_time_minutes": 15,                   # <15 min incident recovery
}

# Tier-specific SLA targets
TIER_SLA_TARGETS = {
    "basic": {
        "availability_percentage": Decimal("99.0"),
        "response_time_ms": 1000,
        "error_rate_percentage": Decimal("2.0"),
    },
    "professional": {
        "availability_percentage": Decimal("99.5"),
        "response_time_ms": 750,
        "error_rate_percentage": Decimal("1.5"),
    },
    "enterprise": {
        "availability_percentage": Decimal("99.9"),
        "response_time_ms": 500,
        "error_rate_percentage": Decimal("0.5"),
    }
}
```

### **SLA Calculation Engine**

```python
# Calculate SLA metrics for a tenant
async def calculate_tenant_sla_metrics(
    tenant_id: str, 
    period: str = "monthly"
) -> SLAMetrics:
    monitoring_service = SaaSMonitoringService(session)
    
    # Calculate metrics for specified period
    sla_metrics = await monitoring_service.calculate_sla_metrics(
        tenant_id=tenant_id,
        period=period,
        date_=date.today()
    )
    
    return {
        "tenant_id": tenant_id,
        "period": period,
        "availability": sla_metrics.uptime_percentage,
        "avg_response_time": sla_metrics.avg_response_time_ms,
        "error_rate": sla_metrics.error_rate_percentage,
        "sla_compliance": sla_metrics.overall_sla_met,
        "violations": sla_metrics.sla_violations,
        "health_score": sla_metrics.overall_health_score
    }
```

## 🔍 **Health Check System**

### **Comprehensive Health Validation**

```python
# Multi-layered health check
async def perform_comprehensive_health_check(tenant_id: str):
    monitoring_service = SaaSMonitoringService(session)
    
    # Run complete health check
    health_check = await monitoring_service.perform_tenant_health_check(tenant_id)
    
    return {
        "tenant_id": tenant_id,
        "overall_status": health_check.overall_status.value,
        "response_time": health_check.response_time_ms,
        "checks": {
            "http_endpoint": health_check.check_details.get("endpoint_status"),
            "database": health_check.database_status.value if health_check.database_status else None,
            "redis": health_check.redis_status.value if health_check.redis_status else None,
            "kubernetes": health_check.check_details.get("resource_status"),
            "external_apis": health_check.external_apis_status.value if health_check.external_apis_status else None
        },
        "resource_usage": {
            "cpu_percent": health_check.cpu_usage_percent,
            "memory_percent": health_check.memory_usage_percent,
            "disk_percent": health_check.disk_usage_percent
        },
        "sla_compliance": health_check.sla_compliant,
        "violations": health_check.sla_violations,
        "timestamp": health_check.check_timestamp
    }
```

### **Automated Health Check Scheduling**

```python
# Background task for continuous monitoring
@celery_app.task
async def run_tenant_health_checks():
    monitoring_service = SaaSMonitoringService(session)
    
    # Run health checks for all active tenants
    results = await monitoring_service.run_health_checks_for_all_tenants()
    
    logger.info(
        f"Health checks completed: {results['total_checked']} tenants, "
        f"{results['healthy']} healthy, {results['unhealthy']} unhealthy"
    )
    
    # Trigger alerts for unhealthy tenants
    for health_check in results['results']:
        if not health_check.is_healthy:
            await trigger_health_alert(health_check.tenant_id, health_check)
    
    return results

# Schedule health checks every 5 minutes
celery_app.conf.beat_schedule = {
    'tenant-health-checks': {
        'task': 'run_tenant_health_checks',
        'schedule': 300.0,  # 5 minutes
    },
}
```

## 🚨 **Alert Management System**

### **Alert Severity Levels**

```python
class AlertSeverity(enum.Enum):
    INFO = "info"           # Informational, no action required
    WARNING = "warning"     # Potential issue, monitor closely  
    ERROR = "error"         # Service impact, immediate attention
    CRITICAL = "critical"   # Severe impact, emergency response

# Alert escalation rules
ESCALATION_RULES = {
    AlertSeverity.INFO: {
        "notification_delay": 0,
        "escalation_delay": None,
        "channels": ["slack"]
    },
    AlertSeverity.WARNING: {
        "notification_delay": 60,      # 1 minute
        "escalation_delay": 900,       # 15 minutes  
        "channels": ["slack", "email"]
    },
    AlertSeverity.ERROR: {
        "notification_delay": 0,       # Immediate
        "escalation_delay": 300,       # 5 minutes
        "channels": ["slack", "email", "sms"]
    },
    AlertSeverity.CRITICAL: {
        "notification_delay": 0,       # Immediate
        "escalation_delay": 60,        # 1 minute
        "channels": ["slack", "email", "sms", "pagerduty"]
    }
}
```

### **Smart Alert Grouping**

```python
# Prevent alert storm by grouping related alerts
async def create_smart_alert(
    tenant_id: str,
    alert_type: str,
    severity: AlertSeverity,
    message: str,
    context: Dict[str, Any]
):
    # Check for existing similar alerts
    existing_alerts = await session.execute(
        select(MonitoringAlert).where(
            and_(
                MonitoringAlert.tenant_id == tenant_id,
                MonitoringAlert.metric_name == alert_type,
                MonitoringAlert.status == AlertStatus.ACTIVE,
                MonitoringAlert.first_occurred >= datetime.utcnow() - timedelta(hours=1)
            )
        )
    )
    
    similar_alert = existing_alerts.scalar_one_or_none()
    
    if similar_alert:
        # Update existing alert instead of creating new one
        similar_alert.last_occurred = datetime.utcnow()
        similar_alert.alert_data["occurrence_count"] = similar_alert.alert_data.get("occurrence_count", 1) + 1
        await session.commit()
        return similar_alert
    else:
        # Create new alert
        alert = MonitoringAlert(
            tenant_id=tenant_id,
            alert_id=f"{alert_type}-{tenant_id}-{int(datetime.utcnow().timestamp())}",
            alert_name=f"{alert_type.title()} - {tenant_id}",
            alert_description=message,
            severity=severity,
            source_service="saas_monitoring",
            metric_name=alert_type,
            alert_data=context
        )
        
        session.add(alert)
        await session.commit()
        
        # Send notification
        await send_alert_notification(alert)
        
        return alert
```

### **Alert Notification System**

```python
# Multi-channel notification dispatcher
async def send_alert_notification(alert: MonitoringAlert):
    channels = ESCALATION_RULES[alert.severity]["channels"]
    
    notification_tasks = []
    
    for channel in channels:
        if channel == "slack":
            notification_tasks.append(send_slack_alert(alert))
        elif channel == "email":
            notification_tasks.append(send_email_alert(alert))
        elif channel == "sms":
            notification_tasks.append(send_sms_alert(alert))
        elif channel == "pagerduty":
            notification_tasks.append(send_pagerduty_alert(alert))
    
    # Send all notifications concurrently
    await asyncio.gather(*notification_tasks)
    
    # Update alert with notification tracking
    alert.notifications_sent += len(channels)
    alert.last_notification_at = datetime.utcnow()
    alert.notification_channels = channels
    
    await session.commit()

# Slack notification
async def send_slack_alert(alert: MonitoringAlert):
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    
    color_map = {
        AlertSeverity.INFO: "good",
        AlertSeverity.WARNING: "warning", 
        AlertSeverity.ERROR: "danger",
        AlertSeverity.CRITICAL: "danger"
    }
    
    payload = {
        "attachments": [{
            "color": color_map[alert.severity],
            "title": alert.alert_name,
            "text": alert.alert_description,
            "fields": [
                {"title": "Tenant", "value": alert.tenant_id, "short": True},
                {"title": "Severity", "value": alert.severity.value.upper(), "short": True},
                {"title": "Time", "value": alert.first_occurred.strftime("%Y-%m-%d %H:%M:%S"), "short": True}
            ],
            "footer": "DotMac SaaS Monitoring",
            "ts": int(alert.first_occurred.timestamp())
        }]
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(webhook_url, json=payload) as response:
            if response.status != 200:
                logger.error(f"Failed to send Slack notification: {response.status}")
```

## 📈 **Performance Analytics**

### **Real-Time Metrics Collection**

```python
# Collect performance metrics across all tenants
async def collect_platform_metrics():
    metrics = {
        "timestamp": datetime.utcnow(),
        "platform_metrics": {
            "total_tenants": await get_total_tenant_count(),
            "active_tenants": await get_active_tenant_count(),
            "total_requests_per_minute": await get_platform_request_rate(),
            "average_response_time": await get_platform_avg_response_time(),
            "error_rate": await get_platform_error_rate()
        },
        "resource_metrics": {
            "cpu_utilization": await get_platform_cpu_usage(),
            "memory_utilization": await get_platform_memory_usage(),
            "disk_utilization": await get_platform_disk_usage(),
            "network_throughput": await get_platform_network_io()
        },
        "tenant_metrics": await get_per_tenant_metrics()
    }
    
    # Store metrics for historical analysis
    await store_platform_metrics(metrics)
    
    return metrics

# Per-tenant metrics snapshot
async def get_per_tenant_metrics():
    tenants = await get_active_tenants()
    tenant_metrics = {}
    
    for tenant in tenants:
        metrics = await get_tenant_performance_snapshot(tenant.tenant_id)
        tenant_metrics[tenant.tenant_id] = {
            "response_time_ms": metrics.current_response_time_ms,
            "throughput_rpm": metrics.current_throughput_rpm,
            "error_rate": metrics.current_error_rate,
            "cpu_usage": metrics.cpu_usage_percent,
            "memory_usage": metrics.memory_usage_percent,
            "active_users": metrics.active_sessions,
            "health_score": metrics.health_score
        }
    
    return tenant_metrics
```

### **Predictive Analytics**

```python
# Predict scaling needs and potential issues
async def generate_predictive_insights(tenant_id: str):
    # Get historical metrics
    historical_data = await get_tenant_metrics_history(
        tenant_id=tenant_id,
        days=30
    )
    
    # Analyze trends
    trends = analyze_performance_trends(historical_data)
    
    insights = {
        "tenant_id": tenant_id,
        "predictions": {
            "scaling_recommendation": predict_scaling_needs(trends),
            "capacity_forecast": forecast_resource_usage(trends),
            "potential_issues": identify_potential_issues(trends)
        },
        "recommendations": [
            generate_optimization_recommendations(trends),
            generate_cost_optimization_suggestions(trends)
        ]
    }
    
    return insights

def predict_scaling_needs(trends):
    cpu_trend = trends.get("cpu_usage_trend", 0)
    memory_trend = trends.get("memory_usage_trend", 0)
    request_trend = trends.get("request_rate_trend", 0)
    
    if cpu_trend > 0.1 or memory_trend > 0.1:  # 10% increase trend
        return "scale_up"
    elif cpu_trend < -0.1 and memory_trend < -0.1:  # 10% decrease trend  
        return "scale_down"
    else:
        return "maintain"
```

## 🎛️ **Dashboard & Reporting**

### **Real-Time Health Dashboard**

```python
# API endpoint for real-time health dashboard
@router.get("/monitoring/dashboard/health")
async def get_health_dashboard(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(["monitoring:read"]))
):
    monitoring_service = SaaSMonitoringService(session)
    
    # Get platform-wide health status
    platform_health = {
        "overall_status": "healthy",
        "total_tenants": 0,
        "healthy_tenants": 0,
        "unhealthy_tenants": 0,
        "degraded_tenants": 0,
        "active_alerts": 0,
        "sla_compliance": 0.0
    }
    
    # Get recent health checks
    recent_checks = await session.execute(
        select(TenantHealthCheck)
        .where(TenantHealthCheck.check_timestamp >= datetime.utcnow() - timedelta(hours=1))
        .order_by(desc(TenantHealthCheck.check_timestamp))
        .limit(100)
    )
    
    checks = recent_checks.scalars().all()
    
    # Calculate platform health summary
    if checks:
        platform_health["total_tenants"] = len(set(check.tenant_id for check in checks))
        platform_health["healthy_tenants"] = len([c for c in checks if c.is_healthy])
        platform_health["unhealthy_tenants"] = len([c for c in checks if c.overall_status == HealthStatus.UNHEALTHY])
        platform_health["degraded_tenants"] = len([c for c in checks if c.overall_status == HealthStatus.DEGRADED])
    
    # Get active alerts
    active_alerts = await monitoring_service.get_active_alerts()
    platform_health["active_alerts"] = len(active_alerts)
    
    return {
        "platform_health": platform_health,
        "recent_checks": [
            {
                "tenant_id": check.tenant_id,
                "status": check.overall_status.value,
                "response_time": check.response_time_ms,
                "timestamp": check.check_timestamp,
                "sla_compliant": check.sla_compliant
            }
            for check in checks[:20]  # Latest 20 checks
        ],
        "active_alerts": [
            {
                "alert_id": alert.alert_id,
                "tenant_id": alert.tenant_id,
                "severity": alert.severity.value,
                "message": alert.alert_description,
                "duration": (datetime.utcnow() - alert.first_occurred).total_seconds() / 60
            }
            for alert in active_alerts[:10]  # Top 10 alerts
        ]
    }
```

### **SLA Compliance Reports**

```python
# Generate comprehensive SLA report
async def generate_sla_compliance_report(
    tenant_id: Optional[str] = None,
    period: str = "monthly"
):
    report = {
        "report_period": period,
        "generated_at": datetime.utcnow(),
        "overall_compliance": {},
        "tenant_compliance": [],
        "violations": [],
        "trends": {}
    }
    
    if tenant_id:
        # Single tenant report
        sla_metrics = await calculate_tenant_sla_metrics(tenant_id, period)
        report["tenant_compliance"] = [sla_metrics]
    else:
        # Platform-wide report
        active_tenants = await get_active_tenants()
        
        for tenant in active_tenants:
            tenant_sla = await calculate_tenant_sla_metrics(tenant.tenant_id, period)
            report["tenant_compliance"].append(tenant_sla)
    
    # Calculate overall platform compliance
    if report["tenant_compliance"]:
        total_tenants = len(report["tenant_compliance"])
        compliant_tenants = len([t for t in report["tenant_compliance"] if t["sla_compliance"]])
        
        report["overall_compliance"] = {
            "total_tenants": total_tenants,
            "compliant_tenants": compliant_tenants,
            "compliance_percentage": (compliant_tenants / total_tenants) * 100,
            "average_availability": sum(t["availability"] for t in report["tenant_compliance"]) / total_tenants,
            "average_response_time": sum(t["avg_response_time"] for t in report["tenant_compliance"]) / total_tenants,
            "average_error_rate": sum(t["error_rate"] for t in report["tenant_compliance"]) / total_tenants
        }
    
    return report
```

## 🔧 **API Reference**

### **Health Check APIs**

```python
# Trigger manual health check
POST /api/v1/monitoring/health-checks/{tenant_id}
{
  "check_type": "comprehensive",
  "include_deep_checks": true
}

# Get health check history  
GET /api/v1/monitoring/health-checks/{tenant_id}?hours=24&limit=100

# Get platform health overview
GET /api/v1/monitoring/health/platform

# Get tenant health summary
GET /api/v1/monitoring/health/{tenant_id}/summary
```

### **Alert Management APIs**

```python
# Get active alerts
GET /api/v1/monitoring/alerts?severity=critical&status=active&limit=50

# Acknowledge alert
POST /api/v1/monitoring/alerts/{alert_id}/acknowledge
{
  "notes": "Investigating the issue"
}

# Resolve alert
POST /api/v1/monitoring/alerts/{alert_id}/resolve
{
  "resolution_notes": "Fixed by scaling up resources"
}

# Create custom alert
POST /api/v1/monitoring/alerts
{
  "tenant_id": "example-isp-001",
  "alert_name": "Custom Business Logic Alert",
  "severity": "warning",
  "description": "Custom alert triggered by business logic"
}
```

### **SLA & Metrics APIs**

```python
# Get SLA metrics
GET /api/v1/monitoring/sla/{tenant_id}?period=monthly

# Get performance metrics
GET /api/v1/monitoring/metrics/{tenant_id}?start_date=2025-01-01&end_date=2025-01-31

# Generate SLA report
GET /api/v1/monitoring/reports/sla?tenant_id={tenant_id}&period=quarterly&format=pdf

# Get predictive insights
GET /api/v1/monitoring/insights/{tenant_id}/predictions
```

## 🚀 **Getting Started**

### **1. Enable Monitoring for Tenant**

```bash
# Automatic monitoring enabled during tenant creation
curl -X POST http://localhost:8000/api/v1/tenant-orchestration/deployments \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_name": "Example ISP",
    "resource_tier": "medium",
    "monitoring_enabled": true,
    "sla_tier": "professional"
  }'
```

### **2. View Health Dashboard**

```bash
# Access real-time health dashboard
open http://localhost:3000/admin/monitoring/health

# API access
curl http://localhost:8000/api/v1/monitoring/dashboard/health
```

### **3. Set Up Custom Alerts**

```bash
# Create custom alert rule
curl -X POST http://localhost:8000/api/v1/monitoring/alert-rules \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "example-isp-001",
    "metric": "response_time_ms",
    "condition": "greater_than",
    "threshold": 1000,
    "severity": "warning"
  }'
```

### **4. Generate SLA Report**

```bash
# Generate monthly SLA report
curl "http://localhost:8000/api/v1/monitoring/reports/sla?period=monthly&format=json" \
  -H "Authorization: Bearer $JWT_TOKEN"
```

## 🎯 **Best Practices**

### **Health Check Strategy**
- Implement multiple health check layers (HTTP, database, business logic)
- Use appropriate check intervals (5 minutes for standard, 1 minute for critical)
- Include meaningful context in health check responses
- Monitor dependencies and external services

### **Alert Management**
- Use appropriate alert severity levels to avoid alert fatigue
- Implement smart alert grouping to prevent notification storms
- Set up escalation policies for different alert types
- Regularly review and tune alert thresholds

### **SLA Management**
- Define clear, measurable SLA targets for each service tier
- Monitor SLA compliance continuously, not just at month-end
- Implement automated SLA violation notifications
- Use SLA data to drive infrastructure and performance improvements

### **Performance Monitoring**
- Collect metrics at appropriate granularity levels
- Use predictive analytics to proactively identify issues
- Monitor business metrics alongside technical metrics
- Implement cost-aware monitoring to optimize resource usage

This comprehensive monitoring system ensures reliable service delivery across all tenant deployments while providing the insights needed for continuous improvement and optimization.