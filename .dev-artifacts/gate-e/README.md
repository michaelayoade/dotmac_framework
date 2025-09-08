# Gate E: Full E2E + Observability Testing

## Overview

Gate E represents the final and most comprehensive testing gate in the DotMac framework quality assurance pipeline. It validates complete end-to-end user journeys across service boundaries and ensures the observability pipeline is functioning correctly.

## Quick Start

```bash
# Navigate to Gate E directory
cd .dev-artifacts/gate-e/

# Run all Gate E tests
./run-gate-e-tests.sh

# View results
cat gate-e-final-report.json
```

## What Gate E Tests

### 🔄 Cross-Service Flow Tests
- **Login → CRUD → Jobs → Notifications → Metrics**: Complete user journey validation
- **Multi-tenant isolation**: Ensures tenant data separation
- **Real-time features**: WebSocket communication and live updates
- **Error handling**: Graceful failure and recovery scenarios
- **Performance validation**: Response time and resource usage checks

### 📊 Observability Pipeline Tests
- **Metrics export**: Prometheus format validation
- **Distributed tracing**: Cross-service trace collection
- **Business metrics**: DotMac-specific KPI tracking
- **Service health**: Endpoint availability and performance
- **Dashboard accessibility**: Observability UI validation

## Files Structure

```
gate-e/
├── cross-service-flow.spec.ts      # Main E2E test scenarios
├── observability-sanity-checks.py  # Metrics/tracing validation
├── run-gate-e-tests.sh            # Test orchestration script
├── playwright.config.ts           # E2E test configuration
├── setup/
│   ├── global-setup.ts            # Test environment setup
│   └── global-teardown.ts         # Cleanup and reporting
├── GATE_E_IMPLEMENTATION_REPORT.md # Detailed documentation
└── README.md                      # This file
```

## Prerequisites

- **Services Running**: Management platform, ISP admin, customer portal, reseller portal
- **Docker**: For service orchestration
- **Node.js & npm**: For Playwright tests
- **Python 3**: For observability checks
- **Database**: PostgreSQL with test schema
- **Observability Stack**: SigNoz/Prometheus (optional but recommended)

## Usage Examples

### Basic Usage
```bash
# Run all tests with defaults
./run-gate-e-tests.sh
```

### Advanced Configuration
```bash
# Custom timeout and verbose output
./run-gate-e-tests.sh --timeout 25 --verbose

# Sequential execution (no parallel)  
./run-gate-e-tests.sh --no-parallel

# Skip cleanup for debugging
./run-gate-e-tests.sh --no-cleanup
```

### Individual Test Components
```bash
# Run only observability checks
python3 observability-sanity-checks.py

# Run only Playwright E2E tests
npx playwright test cross-service-flow.spec.ts --config=playwright.config.ts

# Run with debug mode
PWDEBUG=1 npx playwright test cross-service-flow.spec.ts
```

## Environment Configuration

### Service URLs
```bash
export MANAGEMENT_URL="http://localhost:8000"
export ISP_URL="http://localhost:3000"
export CUSTOMER_URL="http://localhost:3001"
export RESELLER_URL="http://localhost:3003"
export SIGNOZ_URL="http://localhost:3301"
```

### Database & Cache
```bash
export DATABASE_URL="postgresql://user:pass@localhost:5432/dotmac_test"
export REDIS_URL="redis://localhost:6379/1"
```

## Expected Results

### Success Criteria
- ✅ All cross-service flows complete successfully
- ✅ Distributed traces are collected and correlated  
- ✅ Business metrics are generated and exported
- ✅ Performance thresholds are met (API < 2s, UI < 8s)
- ✅ Multi-tenant isolation is maintained
- ✅ Error handling works as expected

### Output Files
- `gate-e-final-report.json`: Overall test results summary
- `observability-sanity-check-report.json`: Observability validation results  
- `artifacts/`: Screenshots, videos, logs, metrics snapshots
- `test-results/`: Detailed test execution results

## Troubleshooting

### Common Issues

**Services Not Started**
```bash
# Check service status
docker-compose ps

# Start services
docker-compose up -d

# Check logs
docker-compose logs management
```

**Test Timeouts**
```bash
# Increase timeout
./run-gate-e-tests.sh --timeout 30

# Run sequentially 
./run-gate-e-tests.sh --no-parallel
```

**Database Connection Issues**  
```bash
# Verify database
psql -h localhost -U test -d dotmac_test -c "SELECT 1;"

# Check environment
echo $DATABASE_URL
```

**Observability Issues**
```bash
# Test metrics endpoint
curl http://localhost:8000/metrics

# Test SigNoz health
curl http://localhost:3301/api/v1/health
```

## CI/CD Integration

### GitHub Actions
```yaml
gate-e-validation:
  name: "Gate E: Full E2E + Observability"
  runs-on: ubuntu-latest
  needs: [gate-a, gate-b, gate-c, gate-d]
  
  steps:
    - uses: actions/checkout@v4
    - name: Start Services
      run: docker-compose up -d
    - name: Run Gate E Tests
      run: .dev-artifacts/gate-e/run-gate-e-tests.sh --timeout 20
    - name: Upload Results
      uses: actions/upload-artifact@v4
      with:
        name: gate-e-results
        path: .dev-artifacts/gate-e/artifacts/
```

## Performance Thresholds

| Metric | Threshold | Description |
|--------|-----------|-------------|
| API Response | < 2.0s | Management API endpoints |
| UI Load Time | < 8.0s | Complete page load |
| Metrics Export | < 5.0s | Prometheus endpoint |
| Cross-Service | < 3.0s | Service-to-service calls |

## Business Metrics Validated

- `dotmac_customers_total`: Customer count
- `dotmac_billing_runs_total`: Billing processes
- `dotmac_api_requests_total`: API usage
- `dotmac_notifications_sent_total`: Notification delivery
- `dotmac_partner_signups_total`: Partner registrations

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review `GATE_E_IMPLEMENTATION_REPORT.md` for detailed documentation  
3. Examine artifact files in `artifacts/` directory
4. Check service logs using `docker-compose logs`

---

**Gate E validates deployment readiness through comprehensive E2E testing and observability verification.**