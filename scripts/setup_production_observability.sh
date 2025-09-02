#!/bin/bash

# Production Observability Setup Script for DotMac Framework
# This script configures the complete observability stack for production deployment

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'  
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SIGNOZ_HOST=${SIGNOZ_HOST:-"your-signoz-host:4317"}
ENVIRONMENT=${ENVIRONMENT:-"production"}
SERVICE_NAME=${SERVICE_NAME:-"dotmac-framework"}
SERVICE_VERSION=${SERVICE_VERSION:-"1.0.0"}

echo -e "${BLUE}🚀 Setting up DotMac Production Observability${NC}"
echo "========================================================"

# Check prerequisites
echo -e "${YELLOW}📋 Checking prerequisites...${NC}"

# Check if SigNoz endpoint is reachable
if command -v curl &> /dev/null; then
    echo "  ✓ curl available"
    
    # Test OTLP endpoint (strip port for HTTP check)
    SIGNOZ_HTTP_HOST=${SIGNOZ_HOST%:*}
    if curl -s --connect-timeout 5 "http://${SIGNOZ_HTTP_HOST}:3301/api/v1/version" > /dev/null; then
        echo -e "  ${GREEN}✓ SigNoz endpoint reachable${NC}"
    else
        echo -e "  ${YELLOW}⚠ SigNoz endpoint not reachable, continuing anyway${NC}"
    fi
else
    echo -e "  ${YELLOW}⚠ curl not available, skipping endpoint check${NC}"
fi

# Check Python and dependencies
if command -v python3 &> /dev/null; then
    echo "  ✓ Python 3 available"
    
    # Check if OpenTelemetry is installed
    if python3 -c "import opentelemetry" 2>/dev/null; then
        echo -e "  ${GREEN}✓ OpenTelemetry installed${NC}"
    else
        echo -e "  ${RED}✗ OpenTelemetry not installed${NC}"
        echo "Please run: pip install -e ."
        exit 1
    fi
else
    echo -e "  ${RED}✗ Python 3 not available${NC}"
    exit 1
fi

# Create production environment configuration
echo -e "${YELLOW}⚙️  Creating production environment configuration...${NC}"

cat > .env.production << EOF
# Production OpenTelemetry Configuration for DotMac Framework
OTEL_SERVICE_NAME=${SERVICE_NAME}
SERVICE_VERSION=${SERVICE_VERSION}
ENVIRONMENT=${ENVIRONMENT}

# SigNoz Configuration
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://${SIGNOZ_HOST}
OTEL_EXPORTER_OTLP_METRICS_ENDPOINT=http://${SIGNOZ_HOST}
OTEL_EXPORTER_OTLP_LOGS_ENDPOINT=http://${SIGNOZ_HOST}

# Security (adjust for your setup)
OTEL_EXPORTER_OTLP_INSECURE=false
# OTEL_EXPORTER_OTLP_HEADERS=signoz-access-token=YOUR_TOKEN

# Production Sampling (10% for cost optimization)
OTEL_TRACES_SAMPLING_RATIO=0.10

# Feature Flags (Production settings)
OTEL_ENABLE_SQL_COMMENTER=true
OTEL_ENABLE_DB_STATEMENT=false
OTEL_ENABLE_LOGGING_INSTRUMENTATION=true

# Logging Configuration
LOG_LEVEL=INFO
ENABLE_TRACE_CORRELATION=true
USE_JSON_LOGGING=true

# Performance Monitoring
SLOW_QUERY_THRESHOLD_MS=200.0
ENABLE_N_PLUS_ONE_DETECTION=true

# Context Headers
TENANT_HEADER_NAME=x-tenant-id
REQUEST_ID_HEADER_NAME=x-request-id
USER_ID_HEADER_NAME=x-user-id

# Performance Optimization
OTEL_METRIC_EXPORT_INTERVAL=60000
OTEL_BSP_MAX_QUEUE_SIZE=2048
OTEL_BSP_MAX_EXPORT_BATCH_SIZE=512
OTEL_BSP_EXPORT_TIMEOUT=30000
OTEL_BSP_SCHEDULE_DELAY=2000
EOF

echo -e "  ${GREEN}✓ Created .env.production${NC}"

# Test observability setup
echo -e "${YELLOW}🧪 Testing observability setup...${NC}"

# Create a simple test script
cat > /tmp/test_observability.py << 'EOF'
import sys
import os

# Set up environment
os.environ.setdefault('OTEL_SERVICE_NAME', 'dotmac-test')
os.environ.setdefault('ENVIRONMENT', 'test')

sys.path.insert(0, 'src')

try:
    from dotmac_shared.observability import setup_observability, get_tracer
    from fastapi import FastAPI
    
    print("✓ Imports successful")
    
    # Test basic setup
    app = FastAPI()
    tracer_provider, meter_provider = setup_observability(app, None)
    
    print("✓ Observability setup successful")
    
    # Test tracing
    tracer = get_tracer("test-service")
    with tracer.start_as_current_span("test-span") as span:
        span.set_attribute("test.key", "test.value")
        print("✓ Tracing functional")
    
    print("🎉 All tests passed!")
    
except Exception as e:
    print(f"❌ Test failed: {e}")
    sys.exit(1)
EOF

if python3 /tmp/test_observability.py; then
    echo -e "  ${GREEN}✓ Observability setup test passed${NC}"
else
    echo -e "  ${RED}✗ Observability setup test failed${NC}"
    exit 1
fi

# Clean up test file
rm -f /tmp/test_observability.py

# Generate deployment files
echo -e "${YELLOW}📦 Generating deployment files...${NC}"

# Docker Compose snippet
cat > docker-compose.observability.yml << EOF
version: '3.8'

services:
  dotmac-api:
    environment:
      - OTEL_SERVICE_NAME=${SERVICE_NAME}
      - SERVICE_VERSION=${SERVICE_VERSION}
      - ENVIRONMENT=${ENVIRONMENT}
      - OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://${SIGNOZ_HOST}
      - OTEL_EXPORTER_OTLP_METRICS_ENDPOINT=http://${SIGNOZ_HOST}
      - OTEL_TRACES_SAMPLING_RATIO=0.10
      - LOG_LEVEL=INFO
      - USE_JSON_LOGGING=true
    depends_on:
      - signoz-collector
      
  # Add SigNoz services if not external
  signoz-collector:
    image: signoz/signoz-collector:0.88.0
    # Add your SigNoz collector configuration
EOF

echo -e "  ${GREEN}✓ Created docker-compose.observability.yml${NC}"

# Kubernetes ConfigMap
cat > k8s-observability-config.yaml << EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: dotmac-observability-config
  namespace: dotmac
data:
  OTEL_SERVICE_NAME: "${SERVICE_NAME}"
  SERVICE_VERSION: "${SERVICE_VERSION}"
  ENVIRONMENT: "${ENVIRONMENT}"
  OTEL_EXPORTER_OTLP_TRACES_ENDPOINT: "http://${SIGNOZ_HOST}"
  OTEL_EXPORTER_OTLP_METRICS_ENDPOINT: "http://${SIGNOZ_HOST}"
  OTEL_TRACES_SAMPLING_RATIO: "0.10"
  LOG_LEVEL: "INFO"
  USE_JSON_LOGGING: "true"
  SLOW_QUERY_THRESHOLD_MS: "200.0"
  ENABLE_N_PLUS_ONE_DETECTION: "true"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dotmac-api
  namespace: dotmac
spec:
  template:
    spec:
      containers:
      - name: api
        envFrom:
        - configMapRef:
            name: dotmac-observability-config
EOF

echo -e "  ${GREEN}✓ Created k8s-observability-config.yaml${NC}"

# Create monitoring checklist
cat > OBSERVABILITY_CHECKLIST.md << EOF
# DotMac Production Observability Checklist

## Pre-Deployment ✅

- [ ] SigNoz instance is running and accessible
- [ ] OTLP endpoints (4317/4318) are open in firewall
- [ ] Environment variables are configured in deployment
- [ ] Service name and version are set correctly
- [ ] Sampling ratio is appropriate for production (10% recommended)

## Post-Deployment Verification ✅

- [ ] Traces appearing in SigNoz within 1-2 minutes
- [ ] Metrics being exported successfully
- [ ] Logs contain trace_id/span_id for correlation
- [ ] Database queries are being monitored
- [ ] Business metrics are being recorded
- [ ] Tenant context is propagating correctly

## Dashboard Setup ✅

- [ ] Import config/signoz-dashboards.json to SigNoz
- [ ] Configure alert notification channels
- [ ] Test alert firing and notifications
- [ ] Set up SLA monitoring dashboards
- [ ] Configure tenant-specific views

## Performance Monitoring ✅

- [ ] Monitor OTLP export performance
- [ ] Verify sampling is working correctly
- [ ] Check for high cardinality metrics
- [ ] Monitor memory usage impact (<5% overhead)
- [ ] Validate query performance impact

## Business Metrics Validation ✅

- [ ] Partner signup events are tracked
- [ ] Customer acquisition metrics work
- [ ] Commission calculations are monitored
- [ ] Revenue attribution is accurate
- [ ] SLA violations trigger alerts

## Troubleshooting Commands

\`\`\`bash
# Check if traces are being exported
curl -s http://signoz:3301/api/v1/traces

# Test OTLP endpoint
telnet your-signoz-host 4317

# View application logs with trace correlation
docker logs dotmac-api | grep trace_id

# Check metrics export
curl -s http://signoz:3301/api/v1/metrics/query?query=http_requests_total
\`\`\`

## Support

For issues:
1. Check SigNoz collector logs
2. Verify OTLP endpoint connectivity  
3. Review application startup logs
4. Validate environment configuration
EOF

echo -e "  ${GREEN}✓ Created OBSERVABILITY_CHECKLIST.md${NC}"

# Final summary
echo ""
echo -e "${GREEN}🎉 Production Observability Setup Complete!${NC}"
echo "========================================================"
echo "Files created:"
echo "  • .env.production - Production environment config"
echo "  • docker-compose.observability.yml - Docker deployment"  
echo "  • k8s-observability-config.yaml - Kubernetes config"
echo "  • OBSERVABILITY_CHECKLIST.md - Deployment checklist"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo "1. Update SIGNOZ_HOST in .env.production with your SigNoz endpoint"
echo "2. Import config/signoz-dashboards.json to your SigNoz instance"
echo "3. Deploy using your preferred method (Docker/K8s)"
echo "4. Follow OBSERVABILITY_CHECKLIST.md for verification"
echo ""
echo -e "${YELLOW}Remember:${NC}"
echo "• Test in staging first with 100% sampling"
echo "• Monitor export performance and adjust batch sizes"
echo "• Set up alert notifications for critical metrics"
echo ""
echo -e "${GREEN}Happy monitoring! 📊${NC}"