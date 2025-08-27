#!/bin/bash
# =============================================================================
# DotMac Management Platform - Monitoring & Observability Setup
# =============================================================================
# Complete monitoring stack with Prometheus, Grafana, AlertManager, and SignOz
# =============================================================================

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="/var/log/dotmac-monitoring-setup.log"
SETUP_ID="monitoring-$(date +%Y%m%d-%H%M%S)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# =============================================================================
# Logging Functions
# =============================================================================

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}[INFO] $1${NC}" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}[WARN] $1${NC}" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR] $1${NC}" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS] $1${NC}" | tee -a "$LOG_FILE"
}

# =============================================================================
# Phase 2.1: Prometheus Configuration
# =============================================================================

setup_prometheus_config() {
    log "📊 Phase 2.1: Setting up Prometheus configuration..."
    
    local monitoring_dir="$PROJECT_ROOT/deployment/production/monitoring"
    mkdir -p "$monitoring_dir/rules"
    
    # Main Prometheus configuration
    cat > "$monitoring_dir/prometheus.yml" << 'EOF'
# DotMac Management Platform - Prometheus Configuration
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  scrape_timeout: 10s
  external_labels:
    cluster: 'dotmac-production'
    environment: 'production'

rule_files:
  - "/etc/prometheus/rules/*.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

scrape_configs:
  # Prometheus itself
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
    scrape_interval: 30s
    metrics_path: /metrics

  # Management Platform API
  - job_name: 'mgmt-api'
    static_configs:
      - targets: ['mgmt-api:8000']
    scrape_interval: 15s
    metrics_path: /metrics
    scrape_timeout: 10s

  # PostgreSQL Exporter
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']
    scrape_interval: 30s

  # Redis Exporter
  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
    scrape_interval: 30s

  # Node Exporter (System Metrics)
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']
    scrape_interval: 30s

  # cAdvisor (Container Metrics)
  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']
    scrape_interval: 30s
    metrics_path: /metrics

  # Nginx Exporter
  - job_name: 'nginx'
    static_configs:
      - targets: ['nginx-exporter:9113']
    scrape_interval: 30s

  # Celery Flower (Background Jobs)
  - job_name: 'celery'
    static_configs:
      - targets: ['flower:5555']
    scrape_interval: 30s
    metrics_path: /metrics

  # Custom Business Metrics
  - job_name: 'business-metrics'
    static_configs:
      - targets: ['mgmt-api:8000']
    scrape_interval: 60s
    metrics_path: /metrics/business
    honor_labels: true

  # External Health Checks
  - job_name: 'blackbox'
    metrics_path: /probe
    params:
      module: [http_2xx]
    static_configs:
      - targets:
        - http://mgmt-api:8000/health
        - https://example.com  # Replace with actual external dependencies
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: blackbox-exporter:9115

# Recording rules for performance optimization
recording_rules:
  - name: dotmac.rules
    rules:
      # API Request Rate
      - record: dotmac:api_request_rate_5m
        expr: rate(http_requests_total[5m])
      
      # Error Rate
      - record: dotmac:api_error_rate_5m
        expr: rate(http_requests_total{status=~"4..|5.."}[5m]) / rate(http_requests_total[5m])
      
      # Database Connection Pool Usage
      - record: dotmac:db_pool_usage
        expr: (pg_stat_database_connections / pg_settings_max_connections) * 100
      
      # Redis Memory Usage
      - record: dotmac:redis_memory_usage_percent
        expr: (redis_memory_used_bytes / redis_memory_max_bytes) * 100
      
      # Tenant Metrics
      - record: dotmac:active_tenants
        expr: count(up{job="mgmt-api"} == 1)
      
      # Business Metrics
      - record: dotmac:revenue_per_minute
        expr: rate(billing_revenue_total[1m])
EOF
    
    log_success "Prometheus configuration created"
}

setup_alerting_rules() {
    log "🚨 Phase 2.2: Setting up alerting rules..."
    
    local rules_dir="$PROJECT_ROOT/deployment/production/monitoring/rules"
    
    # Application alerting rules
    cat > "$rules_dir/application.yml" << 'EOF'
groups:
  - name: application.alerts
    rules:
      # Critical Application Alerts
      - alert: ApplicationDown
        expr: up{job="mgmt-api"} == 0
        for: 1m
        labels:
          severity: critical
          service: application
        annotations:
          summary: "DotMac Management Platform is down"
          description: "Management Platform API has been down for more than 1 minute"
          runbook_url: "https://wiki.company.com/runbooks/application-down"

      - alert: HighErrorRate
        expr: dotmac:api_error_rate_5m > 0.1
        for: 5m
        labels:
          severity: critical
          service: application
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }} over the last 5 minutes"

      - alert: HighResponseTime
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
          service: application
        annotations:
          summary: "High response time detected"
          description: "95th percentile response time is {{ $value }}s"

      - alert: AuthenticationFailures
        expr: rate(authentication_failures_total[5m]) > 10
        for: 2m
        labels:
          severity: warning
          service: security
        annotations:
          summary: "High authentication failure rate"
          description: "{{ $value }} authentication failures per second"

      # Business Logic Alerts
      - alert: RevenueProcessingDown
        expr: rate(billing_processed_total[10m]) == 0
        for: 15m
        labels:
          severity: critical
          service: billing
        annotations:
          summary: "Revenue processing has stopped"
          description: "No billing events processed in the last 15 minutes"

      - alert: TenantProvisioningFailures
        expr: rate(tenant_provisioning_failures_total[10m]) > 0.1
        for: 5m
        labels:
          severity: warning
          service: provisioning
        annotations:
          summary: "Tenant provisioning failures detected"
          description: "{{ $value }} provisioning failures per second"

      - alert: PluginLicensingErrors
        expr: rate(plugin_licensing_errors_total[5m]) > 0
        for: 2m
        labels:
          severity: warning
          service: licensing
        annotations:
          summary: "Plugin licensing errors detected"
          description: "{{ $value }} licensing errors per second"
EOF
    
    # Infrastructure alerting rules
    cat > "$rules_dir/infrastructure.yml" << 'EOF'
groups:
  - name: infrastructure.alerts
    rules:
      # Database Alerts
      - alert: PostgreSQLDown
        expr: up{job="postgres"} == 0
        for: 1m
        labels:
          severity: critical
          service: database
        annotations:
          summary: "PostgreSQL database is down"
          description: "PostgreSQL has been down for more than 1 minute"

      - alert: DatabaseHighConnections
        expr: dotmac:db_pool_usage > 80
        for: 5m
        labels:
          severity: warning
          service: database
        annotations:
          summary: "Database connection pool usage high"
          description: "Connection pool usage is {{ $value }}%"

      - alert: DatabaseSlowQueries
        expr: rate(pg_stat_activity_max_tx_duration[5m]) > 300
        for: 5m
        labels:
          severity: warning
          service: database
        annotations:
          summary: "Slow database queries detected"
          description: "Maximum transaction duration is {{ $value }}s"

      # Redis Alerts
      - alert: RedisDown
        expr: up{job="redis"} == 0
        for: 1m
        labels:
          severity: critical
          service: cache
        annotations:
          summary: "Redis cache is down"
          description: "Redis has been down for more than 1 minute"

      - alert: RedisHighMemoryUsage
        expr: dotmac:redis_memory_usage_percent > 90
        for: 10m
        labels:
          severity: warning
          service: cache
        annotations:
          summary: "Redis memory usage high"
          description: "Redis memory usage is {{ $value }}%"

      # System Resource Alerts
      - alert: HighCPUUsage
        expr: 100 - (avg by(instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 85
        for: 10m
        labels:
          severity: warning
          service: system
        annotations:
          summary: "High CPU usage detected"
          description: "CPU usage is {{ $value }}% on {{ $labels.instance }}"

      - alert: HighMemoryUsage
        expr: (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 90
        for: 5m
        labels:
          severity: warning
          service: system
        annotations:
          summary: "High memory usage detected"
          description: "Memory usage is {{ $value }}% on {{ $labels.instance }}"

      - alert: LowDiskSpace
        expr: (1 - (node_filesystem_free_bytes{fstype!="tmpfs"} / node_filesystem_size_bytes)) * 100 > 90
        for: 5m
        labels:
          severity: critical
          service: system
        annotations:
          summary: "Low disk space"
          description: "Disk usage is {{ $value }}% on {{ $labels.instance }} for {{ $labels.mountpoint }}"

      # Container Alerts
      - alert: ContainerDown
        expr: up{job="cadvisor"} == 0
        for: 1m
        labels:
          severity: warning
          service: containers
        annotations:
          summary: "Container monitoring down"
          description: "cAdvisor container monitoring is down"

      - alert: ContainerHighMemoryUsage
        expr: (container_memory_usage_bytes / container_spec_memory_limit_bytes) * 100 > 90
        for: 5m
        labels:
          severity: warning
          service: containers
        annotations:
          summary: "Container high memory usage"
          description: "Container {{ $labels.name }} memory usage is {{ $value }}%"
EOF
    
    # Business metrics alerting rules  
    cat > "$rules_dir/business.yml" << 'EOF'
groups:
  - name: business.alerts
    rules:
      # Revenue Protection Alerts
      - alert: RevenueDropDetected
        expr: (dotmac:revenue_per_minute < dotmac:revenue_per_minute offset 1h * 0.7)
        for: 15m
        labels:
          severity: critical
          service: business
        annotations:
          summary: "Revenue drop detected"
          description: "Revenue per minute has dropped by more than 30% compared to 1 hour ago"

      - alert: BillingSystemDown
        expr: rate(billing_events_processed_total[10m]) == 0
        for: 10m
        labels:
          severity: critical
          service: billing
        annotations:
          summary: "Billing system appears to be down"
          description: "No billing events processed in the last 10 minutes"

      - alert: PaymentFailureRateHigh
        expr: rate(payment_failures_total[5m]) / rate(payment_attempts_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
          service: payments
        annotations:
          summary: "High payment failure rate"
          description: "Payment failure rate is {{ $value | humanizePercentage }}"

      # Customer Experience Alerts
      - alert: TenantOnboardingSlowdown
        expr: histogram_quantile(0.95, rate(tenant_onboarding_duration_seconds_bucket[10m])) > 300
        for: 10m
        labels:
          severity: warning
          service: onboarding
        annotations:
          summary: "Tenant onboarding is slow"
          description: "95th percentile onboarding time is {{ $value }}s (target: <5min)"

      - alert: CustomersUnableToLogin
        expr: rate(login_failures_total[5m]) > 50
        for: 2m
        labels:
          severity: critical
          service: authentication
        annotations:
          summary: "High login failure rate"
          description: "{{ $value }} login failures per second"

      # Plugin System Alerts
      - alert: PluginInstallationsFailHigh
        expr: rate(plugin_installation_failures_total[10m]) / rate(plugin_installation_attempts_total[10m]) > 0.2
        for: 5m
        labels:
          severity: warning
          service: plugins
        annotations:
          summary: "High plugin installation failure rate"
          description: "Plugin installation failure rate is {{ $value | humanizePercentage }}"

      - alert: PluginUsageBillingDown
        expr: rate(plugin_usage_billed_total[15m]) == 0
        for: 15m
        labels:
          severity: critical
          service: licensing
        annotations:
          summary: "Plugin usage billing has stopped"
          description: "No plugin usage has been billed in 15 minutes"
EOF
    
    log_success "Alerting rules configured"
}

setup_alertmanager() {
    log "📢 Phase 2.3: Setting up AlertManager..."
    
    local monitoring_dir="$PROJECT_ROOT/deployment/production/monitoring"
    
    cat > "$monitoring_dir/alertmanager.yml" << 'EOF'
# DotMac Management Platform - AlertManager Configuration
global:
  smtp_smarthost: '${SMTP_HOST:-localhost}:${SMTP_PORT:-587}'
  smtp_from: '${SMTP_FROM_ADDRESS:-alerts@dotmac.com}'
  smtp_auth_username: '${SMTP_USERNAME:-}'
  smtp_auth_password: '${SMTP_PASSWORD:-}'
  slack_api_url: '${SLACK_WEBHOOK_URL:-}'

templates:
  - '/etc/alertmanager/templates/*.tmpl'

route:
  group_by: ['alertname', 'service']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 24h
  receiver: 'web.hook'
  routes:
    # Critical alerts go to on-call immediately
    - match:
        severity: critical
      receiver: 'critical-alerts'
      group_wait: 10s
      repeat_interval: 5m
      routes:
        # Revenue/billing critical alerts
        - match_re:
            service: 'billing|payments|business'
        - receiver: 'revenue-critical'
          group_wait: 5s
          repeat_interval: 1m
    
    # Warning alerts go to team channels
    - match:
        severity: warning
      receiver: 'warning-alerts'
      group_interval: 10m
      repeat_interval: 2h
    
    # Infrastructure alerts
    - match_re:
        service: 'database|cache|system|containers'
      receiver: 'infrastructure-alerts'
      group_interval: 5m

receivers:
  - name: 'web.hook'
    webhook_configs:
      - url: 'http://mgmt-api:8000/webhooks/alerts'
        send_resolved: true

  - name: 'critical-alerts'
    email_configs:
      - to: '${ONCALL_EMAIL:-ops-oncall@dotmac.com}'
        subject: '🚨 CRITICAL: {{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
        body: |
          {{ range .Alerts }}
          **Alert:** {{ .Annotations.summary }}
          **Description:** {{ .Annotations.description }}
          **Service:** {{ .Labels.service }}
          **Severity:** {{ .Labels.severity }}
          **Runbook:** {{ .Annotations.runbook_url }}
          **Time:** {{ .StartsAt }}
          {{ end }}
    slack_configs:
      - channel: '#critical-alerts'
        title: '🚨 Critical Alert'
        text: |
          {{ range .Alerts }}
          *{{ .Annotations.summary }}*
          {{ .Annotations.description }}
          Service: {{ .Labels.service }}
          {{ end }}
        send_resolved: true

  - name: 'revenue-critical'
    email_configs:
      - to: '${REVENUE_ONCALL_EMAIL:-revenue-oncall@dotmac.com}'
        subject: '💰 REVENUE CRITICAL: {{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
        body: |
          🚨 **REVENUE IMPACTING ALERT** 🚨
          
          {{ range .Alerts }}
          **Alert:** {{ .Annotations.summary }}
          **Description:** {{ .Annotations.description }}
          **Impact:** Revenue processing may be affected
          **Time:** {{ .StartsAt }}
          
          **IMMEDIATE ACTION REQUIRED**
          {{ end }}
    slack_configs:
      - channel: '#revenue-alerts'
        title: '💰 Revenue Critical Alert'
        text: |
          <!channel> **REVENUE IMPACT DETECTED**
          {{ range .Alerts }}
          *{{ .Annotations.summary }}*
          {{ .Annotations.description }}
          {{ end }}
        send_resolved: true

  - name: 'warning-alerts'
    slack_configs:
      - channel: '#alerts'
        title: '⚠️ Warning Alert'
        text: |
          {{ range .Alerts }}
          *{{ .Annotations.summary }}*
          {{ .Annotations.description }}
          Service: {{ .Labels.service }}
          {{ end }}
        send_resolved: true

  - name: 'infrastructure-alerts'
    email_configs:
      - to: '${INFRASTRUCTURE_EMAIL:-infrastructure@dotmac.com}'
        subject: '🔧 Infrastructure Alert: {{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
    slack_configs:
      - channel: '#infrastructure'
        title: '🔧 Infrastructure Alert'
        text: |
          {{ range .Alerts }}
          *{{ .Annotations.summary }}*
          {{ .Annotations.description }}
          Instance: {{ .Labels.instance }}
          {{ end }}

inhibit_rules:
  # Inhibit warning alerts when critical alerts are firing for the same service
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['service']
  
  # Inhibit container alerts when the entire application is down
  - source_match:
      alertname: 'ApplicationDown'
    target_match_re:
      alertname: 'Container.*'
EOF
    
    log_success "AlertManager configuration created"
}

# =============================================================================
# Phase 2.4: Grafana Dashboards
# =============================================================================

setup_grafana_datasources() {
    log "📊 Phase 2.4: Setting up Grafana datasources..."
    
    local grafana_dir="$PROJECT_ROOT/deployment/production/monitoring/grafana"
    mkdir -p "$grafana_dir/datasources" "$grafana_dir/dashboards"
    
    # Datasource configuration
    cat > "$grafana_dir/datasources/datasources.yml" << 'EOF'
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    jsonData:
      httpMethod: POST
      manageAlerts: true
      prometheusType: Prometheus
      prometheusVersion: 2.40.0
      cacheLevel: 'High'
      disableRecordingRules: false
      incrementalQueryOverlapWindow: 10m

  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
    jsonData:
      maxLines: 1000
      manageAlerts: false

  - name: PostgreSQL
    type: postgres
    access: proxy
    url: postgres-primary:5432
    database: ${POSTGRES_DB}
    user: dotmac_monitor
    secureJsonData:
      password: monitor_password
    jsonData:
      sslmode: require
      maxOpenConns: 5
      maxIdleConns: 2
      connMaxLifetime: 14400

  - name: Redis
    type: redis-datasource
    access: proxy
    url: redis-master:6379
    jsonData:
      client: standalone
      poolSize: 5
      timeout: 10
    secureJsonData:
      password: ${REDIS_PASSWORD}
EOF
    
    log_success "Grafana datasources configured"
}

create_business_dashboard() {
    log "📈 Phase 2.5: Creating business metrics dashboard..."
    
    local dashboards_dir="$PROJECT_ROOT/deployment/production/monitoring/grafana/dashboards"
    
    cat > "$dashboards_dir/business-metrics.json" << 'EOF'
{
  "dashboard": {
    "id": null,
    "title": "DotMac Business Metrics",
    "tags": ["dotmac", "business", "revenue"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "Revenue per Hour",
        "type": "stat",
        "targets": [
          {
            "expr": "sum(rate(billing_revenue_total[1h]))",
            "refId": "A"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "thresholds"
            },
            "custom": {
              "align": "auto",
              "displayMode": "list"
            },
            "mappings": [],
            "thresholds": {
              "steps": [
                {
                  "color": "green",
                  "value": null
                },
                {
                  "color": "red",
                  "value": 0
                }
              ]
            },
            "unit": "currencyUSD"
          }
        },
        "gridPos": {
          "h": 8,
          "w": 12,
          "x": 0,
          "y": 0
        },
        "options": {
          "colorMode": "value",
          "graphMode": "area",
          "justifyMode": "auto",
          "orientation": "auto",
          "reduceOptions": {
            "values": false,
            "calcs": [
              "lastNotNull"
            ],
            "fields": ""
          }
        }
      },
      {
        "id": 2,
        "title": "Active Tenants",
        "type": "stat",
        "targets": [
          {
            "expr": "dotmac:active_tenants",
            "refId": "A"
          }
        ],
        "gridPos": {
          "h": 8,
          "w": 12,
          "x": 12,
          "y": 0
        }
      },
      {
        "id": 3,
        "title": "Payment Success Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "rate(payment_successes_total[5m]) / rate(payment_attempts_total[5m]) * 100",
            "refId": "A"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "percent",
            "thresholds": {
              "steps": [
                {
                  "color": "red",
                  "value": 0
                },
                {
                  "color": "yellow",
                  "value": 95
                },
                {
                  "color": "green",
                  "value": 99
                }
              ]
            }
          }
        },
        "gridPos": {
          "h": 8,
          "w": 8,
          "x": 0,
          "y": 8
        }
      },
      {
        "id": 4,
        "title": "Tenant Onboarding Time (95th percentile)",
        "type": "stat",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(tenant_onboarding_duration_seconds_bucket[10m]))",
            "refId": "A"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "s",
            "thresholds": {
              "steps": [
                {
                  "color": "green",
                  "value": 0
                },
                {
                  "color": "yellow",
                  "value": 180
                },
                {
                  "color": "red",
                  "value": 300
                }
              ]
            }
          }
        },
        "gridPos": {
          "h": 8,
          "w": 8,
          "x": 8,
          "y": 8
        }
      },
      {
        "id": 5,
        "title": "Plugin Usage Revenue",
        "type": "stat",
        "targets": [
          {
            "expr": "sum(rate(plugin_usage_revenue_total[1h]))",
            "refId": "A"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "currencyUSD"
          }
        },
        "gridPos": {
          "h": 8,
          "w": 8,
          "x": 16,
          "y": 8
        }
      },
      {
        "id": 6,
        "title": "API Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "sum(rate(http_requests_total[5m])) by (method, status)",
            "refId": "A",
            "legendFormat": "{{method}} {{status}}"
          }
        ],
        "gridPos": {
          "h": 9,
          "w": 24,
          "x": 0,
          "y": 16
        },
        "yAxes": [
          {
            "label": "Requests/sec",
            "min": 0
          }
        ]
      }
    ],
    "time": {
      "from": "now-1h",
      "to": "now"
    },
    "timepicker": {},
    "refresh": "30s"
  }
}
EOF
    
    log_success "Business metrics dashboard created"
}

create_system_dashboard() {
    log "🖥️ Phase 2.6: Creating system monitoring dashboard..."
    
    local dashboards_dir="$PROJECT_ROOT/deployment/production/monitoring/grafana/dashboards"
    
    # Create a comprehensive system dashboard
    cat > "$dashboards_dir/system-overview.json" << 'EOF'
{
  "dashboard": {
    "id": null,
    "title": "DotMac System Overview",
    "tags": ["dotmac", "system", "infrastructure"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "System Health",
        "type": "stat",
        "targets": [
          {
            "expr": "up",
            "refId": "A"
          }
        ],
        "transformations": [
          {
            "id": "reduce",
            "options": {
              "reducers": ["sum"]
            }
          }
        ],
        "gridPos": {
          "h": 8,
          "w": 6,
          "x": 0,
          "y": 0
        }
      },
      {
        "id": 2,
        "title": "CPU Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "100 - (avg by(instance) (irate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100)",
            "refId": "A",
            "legendFormat": "{{instance}}"
          }
        ],
        "yAxes": [
          {
            "label": "Percent",
            "max": 100,
            "min": 0
          }
        ],
        "gridPos": {
          "h": 8,
          "w": 9,
          "x": 6,
          "y": 0
        }
      },
      {
        "id": 3,
        "title": "Memory Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100",
            "refId": "A",
            "legendFormat": "{{instance}}"
          }
        ],
        "yAxes": [
          {
            "label": "Percent",
            "max": 100,
            "min": 0
          }
        ],
        "gridPos": {
          "h": 8,
          "w": 9,
          "x": 15,
          "y": 0
        }
      }
    ],
    "time": {
      "from": "now-1h",
      "to": "now"
    },
    "refresh": "30s"
  }
}
EOF
    
    log_success "System overview dashboard created"
}

# =============================================================================
# Phase 2.7: Log Management Setup
# =============================================================================

setup_loki_config() {
    log "📝 Phase 2.7: Setting up log management with Loki..."
    
    local logging_dir="$PROJECT_ROOT/deployment/production/logging"
    mkdir -p "$logging_dir"
    
    # Loki configuration
    cat > "$logging_dir/loki-config.yml" << 'EOF'
auth_enabled: false

server:
  http_listen_port: 3100
  grpc_listen_port: 9096

common:
  path_prefix: /loki
  storage:
    filesystem:
      chunks_directory: /loki/chunks
      rules_directory: /loki/rules
  replication_factor: 1
  ring:
    instance_addr: 127.0.0.1
    kvstore:
      store: inmemory

query_range:
  results_cache:
    cache:
      embedded_cache:
        enabled: true
        max_size_mb: 100

schema_config:
  configs:
    - from: 2020-10-24
      store: boltdb-shipper
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h

ruler:
  alertmanager_url: http://alertmanager:9093

limits_config:
  enforce_metric_name: false
  reject_old_samples: true
  reject_old_samples_max_age: 168h
  max_cache_freshness_per_query: 10m
  split_queries_by_interval: 15m

table_manager:
  retention_deletes_enabled: true
  retention_period: 168h
EOF
    
    # Promtail configuration for log collection
    cat > "$logging_dir/promtail-config.yml" << 'EOF'
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  # Management Platform API logs
  - job_name: mgmt-api
    static_configs:
      - targets:
          - localhost
        labels:
          job: mgmt-api
          service: management-platform
          __path__: /app/logs/*.log

  # Nginx access logs
  - job_name: nginx
    static_configs:
      - targets:
          - localhost
        labels:
          job: nginx
          service: reverse-proxy
          __path__: /nginx/logs/access.log
    pipeline_stages:
      - regex:
          expression: '^(?P<remote_addr>\S+) - (?P<remote_user>\S+) \[(?P<time_local>[^\]]+)\] "(?P<method>\S+) (?P<path>\S+) (?P<protocol>\S+)" (?P<status>\d+) (?P<body_bytes_sent>\d+) "(?P<http_referer>[^"]*)" "(?P<http_user_agent>[^"]*)"'
      - labels:
          method:
          status:
          path:

  # System logs
  - job_name: system
    static_configs:
      - targets:
          - localhost
        labels:
          job: system
          service: system
          __path__: /var/log/syslog
          
  # Docker container logs
  - job_name: containers
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
        refresh_interval: 5s
    relabel_configs:
      - source_labels: ['__meta_docker_container_name']
        regex: '/(.*)'
        target_label: 'container'
      - source_labels: ['__meta_docker_container_log_stream']
        target_label: 'stream'
EOF
    
    log_success "Log management configuration created"
}

# =============================================================================
# Phase 2.8: Custom Metrics Implementation
# =============================================================================

create_custom_metrics_endpoint() {
    log "📊 Phase 2.8: Creating custom business metrics endpoint..."
    
    local metrics_file="$PROJECT_ROOT/app/core/custom_metrics.py"
    
    cat > "$metrics_file" << 'EOF'
"""
Custom Business Metrics for Prometheus
Tracks business-specific KPIs and operational metrics.
"""

from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest
from prometheus_client.core import REGISTRY
from fastapi import APIRouter, Response
from fastapi.responses import PlainTextResponse
import time
import asyncio
from typing import Dict, Any
from datetime import datetime, timezone

# Custom metrics registry
business_registry = CollectorRegistry()

# Business Metrics
billing_revenue_total = Counter(
    'billing_revenue_total',
    'Total revenue processed through billing system',
    ['tenant_id', 'plan_type', 'payment_provider'],
    registry=business_registry
)

plugin_usage_total = Counter(
    'plugin_usage_total', 
    'Total plugin usage events',
    ['tenant_id', 'plugin_name', 'usage_type'],
    registry=business_registry
)

tenant_onboarding_duration = Histogram(
    'tenant_onboarding_duration_seconds',
    'Time taken for tenant onboarding process',
    ['tenant_tier'],
    buckets=(10, 30, 60, 180, 300, 600, float('inf')),
    registry=business_registry
)

active_tenants_total = Gauge(
    'active_tenants_total',
    'Number of currently active tenants',
    registry=business_registry
)

payment_attempts_total = Counter(
    'payment_attempts_total',
    'Total payment attempts',
    ['payment_provider', 'tenant_id'],
    registry=business_registry
)

payment_successes_total = Counter(
    'payment_successes_total',
    'Total successful payments',
    ['payment_provider', 'tenant_id'],
    registry=business_registry
)

payment_failures_total = Counter(
    'payment_failures_total',
    'Total failed payments',
    ['payment_provider', 'tenant_id', 'failure_reason'],
    registry=business_registry
)

authentication_attempts_total = Counter(
    'authentication_attempts_total',
    'Total authentication attempts',
    ['tenant_id', 'portal_type', 'auth_method'],
    registry=business_registry
)

authentication_failures_total = Counter(
    'authentication_failures_total',
    'Total authentication failures',
    ['tenant_id', 'portal_type', 'failure_reason'],
    registry=business_registry
)

# Plugin-specific metrics
plugin_installation_attempts_total = Counter(
    'plugin_installation_attempts_total',
    'Total plugin installation attempts',
    ['plugin_name', 'tenant_id'],
    registry=business_registry
)

plugin_installation_failures_total = Counter(
    'plugin_installation_failures_total',
    'Total plugin installation failures',
    ['plugin_name', 'tenant_id', 'failure_reason'],
    registry=business_registry
)

plugin_usage_revenue_total = Counter(
    'plugin_usage_revenue_total',
    'Revenue generated from plugin usage',
    ['plugin_name', 'tenant_id', 'billing_tier'],
    registry=business_registry
)

# Operational metrics
celery_task_duration = Histogram(
    'celery_task_duration_seconds',
    'Time taken by Celery tasks',
    ['task_name', 'status'],
    registry=business_registry
)

database_query_duration = Histogram(
    'database_query_duration_seconds',
    'Database query execution time',
    ['query_type', 'table_name'],
    registry=business_registry
)

# SLA and customer satisfaction metrics
sla_violation_total = Counter(
    'sla_violation_total',
    'Total SLA violations',
    ['tenant_id', 'sla_type', 'severity'],
    registry=business_registry
)

customer_support_tickets_total = Counter(
    'customer_support_tickets_total',
    'Total customer support tickets',
    ['tenant_id', 'priority', 'category'],
    registry=business_registry
)

# Utility functions for metric updates
class BusinessMetrics:
    """Business metrics collector and updater."""
    
    @staticmethod
    def record_revenue(tenant_id: str, amount: float, plan_type: str, payment_provider: str):
        """Record revenue from billing."""
        billing_revenue_total.labels(
            tenant_id=tenant_id,
            plan_type=plan_type,
            payment_provider=payment_provider
        ).inc(amount)
    
    @staticmethod
    def record_plugin_usage(tenant_id: str, plugin_name: str, usage_type: str, count: int = 1):
        """Record plugin usage event."""
        plugin_usage_total.labels(
            tenant_id=tenant_id,
            plugin_name=plugin_name,
            usage_type=usage_type
        ).inc(count)
    
    @staticmethod
    def record_tenant_onboarding(tenant_tier: str, duration_seconds: float):
        """Record tenant onboarding duration."""
        tenant_onboarding_duration.labels(tenant_tier=tenant_tier).observe(duration_seconds)
    
    @staticmethod
    def update_active_tenants(count: int):
        """Update active tenant count."""
        active_tenants_total.set(count)
    
    @staticmethod
    def record_payment_attempt(payment_provider: str, tenant_id: str, success: bool, failure_reason: str = None):
        """Record payment attempt and outcome."""
        payment_attempts_total.labels(
            payment_provider=payment_provider,
            tenant_id=tenant_id
        ).inc()
        
        if success:
            payment_successes_total.labels(
                payment_provider=payment_provider,
                tenant_id=tenant_id
            ).inc()
        else:
            payment_failures_total.labels(
                payment_provider=payment_provider,
                tenant_id=tenant_id,
                failure_reason=failure_reason or 'unknown'
            ).inc()
    
    @staticmethod
    def record_authentication(tenant_id: str, portal_type: str, auth_method: str, success: bool, failure_reason: str = None):
        """Record authentication attempt."""
        authentication_attempts_total.labels(
            tenant_id=tenant_id,
            portal_type=portal_type,
            auth_method=auth_method
        ).inc()
        
        if not success:
            authentication_failures_total.labels(
                tenant_id=tenant_id,
                portal_type=portal_type,
                failure_reason=failure_reason or 'unknown'
            ).inc()

# FastAPI router for metrics endpoints
router = APIRouter()

@router.get("/metrics/business")
async def business_metrics():
    """Expose business metrics in Prometheus format."""
    return PlainTextResponse(
        generate_latest(business_registry),
        media_type="text/plain; charset=utf-8"
    )

@router.get("/metrics/health")
async def metrics_health():
    """Health check for metrics collection."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics_registered": len(business_registry._collector_to_names),
        "last_collection": "ok"
    }

# Background task to update gauge metrics
async def update_gauge_metrics():
    """Periodically update gauge metrics."""
    while True:
        try:
            # Update active tenant count
            from repositories.tenant import TenantRepository
            from database import get_db
            
            async with get_db() as db:
                tenant_repo = TenantRepository(db)
                active_count = await tenant_repo.count_active_tenants()
                active_tenants_total.set(active_count)
                
        except Exception as e:
            # Log error but don't stop the loop
            import logging
            logging.error(f"Error updating gauge metrics: {e}")
        
        # Update every 60 seconds
        await asyncio.sleep(60)

# Initialize background metrics collection
def start_metrics_collection():
    """Start background metrics collection."""
    asyncio.create_task(update_gauge_metrics())
EOF
    
    log_success "Custom business metrics implementation created"
}

# =============================================================================
# Phase 2.9: Monitoring Deployment
# =============================================================================

deploy_monitoring_stack() {
    log "🚀 Phase 2.9: Deploying monitoring stack..."
    
    cd "$PROJECT_ROOT"
    
    # Create monitoring-specific Docker Compose file
    cat > "docker-compose.monitoring.yml" << 'EOF'
version: '3.8'

services:
  # Prometheus
  prometheus:
    image: prom/prometheus:latest
    container_name: dotmac-prometheus-prod
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--web.enable-lifecycle'
      - '--web.enable-admin-api'
      - '--web.listen-address=0.0.0.0:9090'
    volumes:
      - ./deployment/production/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ./deployment/production/monitoring/rules:/etc/prometheus/rules:ro
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    networks:
      - dotmac-monitoring
      - dotmac-backend
    restart: unless-stopped

  # AlertManager
  alertmanager:
    image: prom/alertmanager:latest
    container_name: dotmac-alertmanager-prod
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
      - '--storage.path=/alertmanager'
      - '--web.listen-address=0.0.0.0:9093'
    volumes:
      - ./deployment/production/monitoring/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
      - alertmanager_data:/alertmanager
    ports:
      - "9093:9093"
    networks:
      - dotmac-monitoring
    restart: unless-stopped

  # Grafana
  grafana:
    image: grafana/grafana:latest
    container_name: dotmac-grafana-prod
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD:-admin}
      - GF_USERS_ALLOW_SIGN_UP=false
      - GF_SERVER_DOMAIN=${MAIN_DOMAIN:-localhost}
      - GF_SMTP_ENABLED=true
      - GF_SMTP_HOST=${SMTP_HOST}:${SMTP_PORT}
      - GF_SMTP_USER=${SMTP_USERNAME}
      - GF_SMTP_PASSWORD=${SMTP_PASSWORD}
      - GF_SMTP_FROM_ADDRESS=${SMTP_FROM_ADDRESS}
    volumes:
      - grafana_data:/var/lib/grafana
      - ./deployment/production/monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards:ro
      - ./deployment/production/monitoring/grafana/datasources:/etc/grafana/provisioning/datasources:ro
    ports:
      - "3001:3000"
    networks:
      - dotmac-monitoring
      - dotmac-frontend
    restart: unless-stopped
    depends_on:
      - prometheus

  # Node Exporter
  node-exporter:
    image: prom/node-exporter:latest
    container_name: dotmac-node-exporter
    command:
      - '--path.rootfs=/host'
    volumes:
      - '/:/host:ro,rslave'
    ports:
      - "9100:9100"
    networks:
      - dotmac-monitoring
    restart: unless-stopped

  # cAdvisor
  cadvisor:
    image: gcr.io/cadvisor/cadvisor:latest
    container_name: dotmac-cadvisor
    privileged: true
    volumes:
      - '/:/rootfs:ro'
      - '/var/run:/var/run:rw'
      - '/sys:/sys:ro'
      - '/var/lib/docker/:/var/lib/docker:ro'
      - '/dev/disk/:/dev/disk:ro'
    ports:
      - "8080:8080"
    networks:
      - dotmac-monitoring
    restart: unless-stopped

  # PostgreSQL Exporter
  postgres-exporter:
    image: prometheuscommunity/postgres-exporter:latest
    container_name: dotmac-postgres-exporter
    environment:
      - DATA_SOURCE_NAME=postgresql://dotmac_monitor:monitor_password@postgres-primary:5432/${POSTGRES_DB}?sslmode=require
    ports:
      - "9187:9187"
    networks:
      - dotmac-monitoring
      - dotmac-backend
    restart: unless-stopped
    depends_on:
      - postgres-primary

  # Redis Exporter
  redis-exporter:
    image: oliver006/redis_exporter:latest
    container_name: dotmac-redis-exporter
    environment:
      - REDIS_ADDR=redis-master:6379
      - REDIS_PASSWORD=${REDIS_PASSWORD}
    ports:
      - "9121:9121"
    networks:
      - dotmac-monitoring
      - dotmac-backend
    restart: unless-stopped
    depends_on:
      - redis-master

  # Loki
  loki:
    image: grafana/loki:latest
    container_name: dotmac-loki-prod
    command: -config.file=/etc/loki/local-config.yaml
    volumes:
      - ./deployment/production/logging/loki-config.yml:/etc/loki/local-config.yaml:ro
      - loki_data:/loki
    ports:
      - "3100:3100"
    networks:
      - dotmac-monitoring
    restart: unless-stopped

  # Promtail
  promtail:
    image: grafana/promtail:latest
    container_name: dotmac-promtail-prod
    command: -config.file=/etc/promtail/config.yml
    volumes:
      - ./deployment/production/logging/promtail-config.yml:/etc/promtail/config.yml:ro
      - /var/log:/var/log:ro
      - mgmt_api_logs:/app/logs:ro
      - nginx_logs:/nginx/logs:ro
    networks:
      - dotmac-monitoring
    restart: unless-stopped
    depends_on:
      - loki

  # Blackbox Exporter for external monitoring
  blackbox-exporter:
    image: prom/blackbox-exporter:latest
    container_name: dotmac-blackbox-exporter
    volumes:
      - ./deployment/production/monitoring/blackbox.yml:/config/blackbox.yml:ro
    command: --config.file=/config/blackbox.yml
    ports:
      - "9115:9115"
    networks:
      - dotmac-monitoring
    restart: unless-stopped

networks:
  dotmac-monitoring:
    external: true
  dotmac-backend:
    external: true
  dotmac-frontend:
    external: true

volumes:
  prometheus_data:
    external: true
  alertmanager_data:
    external: true
  grafana_data:
    external: true
  loki_data:
    external: true
  mgmt_api_logs:
    external: true
  nginx_logs:
    external: true
EOF
    
    # Deploy monitoring stack
    log_info "Starting monitoring services..."
    docker-compose -f docker-compose.monitoring.yml up -d
    
    # Wait for services to be ready
    log_info "Waiting for Prometheus to be ready..."
    timeout 60 bash -c 'until curl -f http://localhost:9090/-/ready; do sleep 5; done'
    
    log_info "Waiting for Grafana to be ready..."
    timeout 60 bash -c 'until curl -f http://localhost:3001/api/health; do sleep 5; done'
    
    log_success "Monitoring stack deployed successfully"
}

validate_monitoring_deployment() {
    log "✅ Phase 2.10: Validating monitoring deployment..."
    
    # Test Prometheus
    log_info "Testing Prometheus..."
    if curl -s http://localhost:9090/-/ready | grep -q "Prometheus is Ready"; then
        log_success "Prometheus is healthy"
    else
        log_error "Prometheus health check failed"
        exit 1
    fi
    
    # Test Grafana
    log_info "Testing Grafana..."
    if curl -s http://localhost:3001/api/health | jq -r '.database' | grep -q "ok"; then
        log_success "Grafana is healthy"
    else
        log_error "Grafana health check failed"
        exit 1
    fi
    
    # Test AlertManager
    log_info "Testing AlertManager..."
    if curl -s http://localhost:9093/-/ready | grep -q "ok"; then
        log_success "AlertManager is healthy"
    else
        log_error "AlertManager health check failed"
        exit 1
    fi
    
    # Test if metrics are being collected
    log_info "Testing metric collection..."
    if curl -s "http://localhost:9090/api/v1/query?query=up" | jq -r '.status' | grep -q "success"; then
        log_success "Metrics collection is working"
    else
        log_error "Metrics collection failed"
        exit 1
    fi
    
    log_success "Monitoring deployment validation completed"
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    log "📊 Starting DotMac Monitoring & Observability Setup"
    log "Setup ID: $SETUP_ID"
    log "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    echo ""
    
    # Phase 2: Monitoring & Observability Implementation
    setup_prometheus_config
    setup_alerting_rules
    setup_alertmanager
    setup_grafana_datasources
    create_business_dashboard
    create_system_dashboard
    setup_loki_config
    create_custom_metrics_endpoint
    deploy_monitoring_stack
    validate_monitoring_deployment
    
    echo ""
    log_success "🎉 PHASE 2 MONITORING SETUP COMPLETED SUCCESSFULLY!"
    echo ""
    log_info "Access Points:"
    log_info "• Prometheus: http://localhost:9090"
    log_info "• Grafana: http://localhost:3001 (admin/admin)"
    log_info "• AlertManager: http://localhost:9093"
    log_info "• Business Metrics: http://localhost/metrics/business"
    echo ""
    log_info "Next steps:"
    log_info "1. Configure alert notification channels (email/Slack)"
    log_info "2. Set up custom dashboards for your specific needs"
    log_info "3. Run Phase 3: ./scripts/security-hardening.sh"
    echo ""
}

# Execute main function
main "$@"