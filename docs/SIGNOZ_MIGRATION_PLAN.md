# Migration Plan: Prometheus/Grafana → SignOz Unified Platform

## 🎯 Executive Summary

Consolidating all observability (metrics, traces, logs) into SignOz eliminates tool sprawl, reduces costs, and provides unified correlation across telemetry signals.

## 📊 Current State vs Target State

### Current State (Legacy)
```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Services   │────▶│  Prometheus  │────▶│   Grafana   │
└─────────────┘     └──────────────┘     └─────────────┘
      │                                          │
      │             ┌──────────────┐            │
      └────────────▶│     Loki     │────────────┘
                    └──────────────┘
```

### Target State (SignOz Unified)
```
┌─────────────┐     ┌──────────────────────────────┐
│  Services   │────▶│         SignOz               │
└─────────────┘     │  - Metrics (ClickHouse)     │
                    │  - Traces (ClickHouse)      │
                    │  - Logs (ClickHouse)        │
                    │  - Dashboards (Native)      │
                    │  - Alerts (Integrated)      │
                    └──────────────────────────────┘
```

## 🔄 Migration Phases

### Phase 1: Parallel Run (Week 1-2)
**Goal**: Run SignOz alongside existing stack for validation

- [x] Deploy SignOz infrastructure
- [x] Configure dual export (Prometheus + SignOz)
- [ ] Validate data parity
- [ ] Train team on SignOz UI

### Phase 2: Dashboard Migration (Week 2-3)
**Goal**: Recreate all Grafana dashboards in SignOz

- [ ] Export Grafana dashboard JSONs
- [ ] Convert to SignOz dashboard format
- [ ] Validate visualizations
- [ ] Add SignOz-specific enhancements

### Phase 3: Alert Migration (Week 3-4)
**Goal**: Move all Prometheus alerts to SignOz

- [ ] Export Prometheus rules
- [ ] Convert to SignOz alert format
- [ ] Test alert routing
- [ ] Update runbooks

### Phase 4: Cutover (Week 4)
**Goal**: Switch to SignOz as primary platform

- [ ] Update all services to use SignOz only
- [ ] Disable Prometheus scrapers
- [ ] Archive historical data
- [ ] Decommission legacy stack

### Phase 5: Optimization (Week 5+)
**Goal**: Optimize SignOz for production

- [ ] Tune retention policies
- [ ] Optimize query performance
- [ ] Implement cost controls
- [ ] Document operations

## 📦 Component Mapping

| Prometheus/Grafana Component | SignOz Replacement | Migration Effort |
|----------------------------|-------------------|-----------------|
| Prometheus Server | SignOz ClickHouse + Query Service | Automatic |
| Prometheus Pushgateway | OTLP Collector | Low |
| Prometheus Alertmanager | SignOz Alerts + Channels | Medium |
| Grafana Dashboards | SignOz Dashboards | High |
| Grafana Alerts | SignOz Alert Rules | Medium |
| Loki Log Aggregation | SignOz Logs | Low |
| Tempo Tracing | SignOz Traces (Native) | None |
| VictoriaMetrics | ClickHouse | Automatic |

## 🔧 Technical Changes Required

### 1. Service Instrumentation
```python
# OLD: Prometheus metrics
from prometheus_client import Counter, Histogram
request_count = Counter('http_requests_total', 'Total requests')
request_duration = Histogram('http_request_duration_seconds', 'Request duration')

# NEW: SignOz unified (via OpenTelemetry)
from opentelemetry import metrics
meter = metrics.get_meter("service-name")
request_count = meter.create_counter('http_requests_total', 'Total requests')
request_duration = meter.create_histogram('http_request_duration_seconds', 'Request duration')
```

### 2. Metrics Export
```yaml
# OLD: Prometheus scrape config
scrape_configs:
  - job_name: 'services'
    static_configs:
      - targets: ['service:8000']

# NEW: SignOz OTLP push
OTEL_EXPORTER_OTLP_ENDPOINT: http://signoz-collector:4317
OTEL_METRICS_EXPORTER: otlp
```

### 3. Query Language
```sql
-- OLD: PromQL
sum(rate(http_requests_total[5m])) by (service)

-- NEW: SignOz ClickHouse SQL
SELECT 
  service,
  sum(value) as request_rate
FROM signoz_metrics.distributed_samples_v2
WHERE 
  metric_name = 'http_requests_total'
  AND timestamp >= now() - INTERVAL 5 MINUTE
GROUP BY service
```

## 📊 Dashboard Conversion Guide

### Grafana → SignOz Dashboard Migration

#### Step 1: Export Grafana Dashboard
```bash
# Export all dashboards
for dashboard in $(curl -s http://grafana:3000/api/search | jq -r '.[].uri'); do
  curl -s http://grafana:3000/api/dashboards/$dashboard > $(basename $dashboard).json
done
```

#### Step 2: Convert to SignOz Format
```python
# Conversion script (see grafana_to_signoz.py)
def convert_dashboard(grafana_json):
    signoz_dashboard = {
        "title": grafana_json["dashboard"]["title"],
        "description": grafana_json["dashboard"]["description"],
        "tags": grafana_json["dashboard"]["tags"],
        "widgets": []
    }
    
    for panel in grafana_json["dashboard"]["panels"]:
        widget = convert_panel_to_widget(panel)
        signoz_dashboard["widgets"].append(widget)
    
    return signoz_dashboard
```

## 🚨 Alert Rule Migration

### Prometheus → SignOz Alerts

#### OLD: Prometheus Rule
```yaml
groups:
  - name: service_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: High error rate detected
```

#### NEW: SignOz Alert
```json
{
  "alert": "HighErrorRate",
  "expr": "SELECT count(*) FROM signoz_traces.distributed_signoz_index_v2 WHERE statusCode >= 500 AND timestamp >= now() - INTERVAL 5 MINUTE",
  "for": "5m",
  "labels": {
    "severity": "critical"
  },
  "annotations": {
    "summary": "High error rate detected"
  },
  "condition": {
    "type": "QUERY",
    "target": {
      "queryType": "clickhouse",
      "query": "SELECT count(*) as error_count..."
    },
    "op": ">",
    "threshold": 0.05
  }
}
```

## 💾 Data Migration Strategy

### Historical Data Options

1. **Clean Start** (Recommended)
   - Keep Prometheus data archived
   - Start fresh with SignOz
   - Reference old data when needed

2. **Selective Migration**
   - Export critical metrics via PromQL
   - Import into ClickHouse
   - 30-day window typically sufficient

3. **Full Migration**
   - Use remote_write to backfill
   - Resource intensive
   - 6-12 months of data

### Export Script
```bash
#!/bin/bash
# Export Prometheus data to SignOz

# Set time range
START_TIME="2024-01-01T00:00:00Z"
END_TIME="2024-02-01T00:00:00Z"

# Export metrics
curl -G http://prometheus:9090/api/v1/query_range \
  --data-urlencode "query=up" \
  --data-urlencode "start=$START_TIME" \
  --data-urlencode "end=$END_TIME" \
  --data-urlencode "step=60s" \
  | jq '.data.result' > metrics_export.json

# Convert and import to SignOz
python3 import_to_signoz.py metrics_export.json
```

## 🔍 Validation Checklist

### Pre-Migration
- [ ] All services sending metrics to SignOz
- [ ] Data retention policies configured
- [ ] Backup of Grafana dashboards
- [ ] Backup of Prometheus rules
- [ ] Team trained on SignOz

### During Migration
- [ ] Metrics parity validated
- [ ] Dashboards recreated
- [ ] Alerts configured
- [ ] Notification channels tested
- [ ] Performance benchmarked

### Post-Migration
- [ ] Legacy stack decommissioned
- [ ] Documentation updated
- [ ] Runbooks revised
- [ ] Cost savings calculated
- [ ] Team feedback collected

## 📈 Benefits After Migration

### Immediate Benefits
- **Unified Interface**: Single pane of glass for all telemetry
- **Correlation**: Automatic trace-metric-log correlation
- **Cost Reduction**: ~40% reduction in infrastructure costs
- **Simplified Operations**: One system to maintain

### Long-term Benefits
- **Better MTTR**: Faster root cause analysis with correlated data
- **Improved Performance**: ClickHouse faster than Prometheus for large datasets
- **Native Tracing**: No need for separate Jaeger/Tempo
- **Flexible Retention**: Different retention per signal type

## 🚀 Migration Commands

### 1. Update Service Configuration
```bash
# Update all services to use SignOz
find backend -name "*.py" -exec sed -i 's/prometheus_client/opentelemetry.metrics/g' {} \;

# Update environment variables
sed -i 's/PROMETHEUS_ENABLED=true/SIGNOZ_ENABLED=true/g' .env
```

### 2. Deploy SignOz-Only Stack
```bash
# Stop Prometheus/Grafana
docker-compose -f docker-compose.monitoring.yml down

# Start SignOz
docker-compose -f docker-compose.signoz.yml up -d
```

### 3. Verify Migration
```bash
# Check SignOz health
curl http://localhost:3301/api/v1/health

# Verify metrics ingestion
curl http://localhost:8889/metrics | grep -c "^dotmac_"

# Check trace ingestion
curl http://localhost:8080/api/v1/traces | jq '.data | length'
```

## 🔐 Security Considerations

### Authentication Migration
- Grafana users → SignOz RBAC
- API keys → SignOz access tokens
- LDAP/SAML → SignOz SSO

### Network Security
- Close Prometheus ports (9090, 3000)
- Restrict SignOz access (3301)
- Enable TLS for OTLP (4317)

## 📚 Training Resources

1. **SignOz Documentation**: https://signoz.io/docs/
2. **Query Guide**: ClickHouse SQL for metrics
3. **Dashboard Guide**: Creating SignOz dashboards
4. **Alert Guide**: SignOz alerting best practices
5. **Troubleshooting**: Common migration issues

## 🎯 Success Criteria

- ✅ All metrics visible in SignOz
- ✅ All critical dashboards recreated
- ✅ All alerts functioning
- ✅ Team comfortable with SignOz
- ✅ Legacy stack decommissioned
- ✅ Cost reduction achieved
- ✅ Performance improved

## 📅 Timeline

| Week | Phase | Status | Owner |
|------|-------|--------|-------|
| 1-2 | Parallel Run | 🟡 In Progress | DevOps |
| 2-3 | Dashboard Migration | ⏳ Pending | Platform |
| 3-4 | Alert Migration | ⏳ Pending | SRE |
| 4 | Cutover | ⏳ Pending | All |
| 5+ | Optimization | ⏳ Pending | Platform |

## 🆘 Rollback Plan

If issues occur during migration:

1. **Immediate**: Switch services back to Prometheus export
2. **Short-term**: Run dual export until issues resolved
3. **Long-term**: Maintain Prometheus backup for 30 days

```bash
# Quick rollback
docker-compose -f docker-compose.monitoring.yml up -d
sed -i 's/SIGNOZ_ENABLED=true/PROMETHEUS_ENABLED=true/g' .env
docker-compose restart
```