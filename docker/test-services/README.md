# DotMac Test Services

Comprehensive testing infrastructure for DotMac platform services including notifications, file storage, and observability.

## Notification Testing

### Overview
The notification testing service validates SMTP and SMS functionality with full tenant isolation.

### Components

#### Test SMTP (MailHog)
- **Container**: `dotmac-test-smtp`
- **SMTP Port**: 1025 
- **Web UI**: http://localhost:8025
- **Purpose**: Captures all outbound emails for testing

#### Test SMS Sink
- **Container**: `dotmac-test-sms`  
- **API Port**: 3030
- **Web UI**: http://localhost:3030
- **Purpose**: Simulates SMS provider API and webhook endpoint

#### Notification Tester
- **Container**: `dotmac-notification-tester`
- **Health Port**: 8080
- **Purpose**: Runs comprehensive notification tests

### Usage

#### Start Test Infrastructure
```bash
cd docker/test-services
docker-compose -f docker-compose.test-notifications.yml up -d
```

#### View Test Results
```bash
# Check logs
docker logs dotmac-notification-tester

# Get results via API
curl http://localhost:8080/results

# View SMTP messages
open http://localhost:8025

# View SMS messages  
open http://localhost:3030
```

#### Stop Infrastructure
```bash
docker-compose -f docker-compose.test-notifications.yml down -v
```

### Test Scenarios

#### SMTP Tests
- **Basic Send**: Simple email with tenant headers
- **Multipart Send**: HTML/text email with tenant isolation
- **Tenant Isolation**: Verify tenant-specific headers are applied

#### SMS Tests  
- **SMS Send**: Outbound SMS through sink API
- **SMS Receive**: Inbound SMS via webhook
- **Tenant Isolation**: Verify tenant-scoped message filtering

#### Workflow Tests
- **Coordinated Notification**: Simultaneous email/SMS delivery

### Tenant Isolation

All tests validate tenant isolation through:
- **Email Headers**: `X-Tenant-ID` header verification
- **SMS Metadata**: `tenant_id` field filtering
- **Message Scoping**: Per-tenant message retrieval
- **Cross-Tenant Verification**: Ensure no data leakage

### Configuration

Test scenarios are configured in `test-configs/notification-config.json`:
- Test scenario enablement
- Tenant definitions with specific email domains and SMS ranges
- Workflow coordination settings

### Integration with CI/CD

The notification tester can be integrated into CI/CD pipelines:

```bash
# Run tests and capture results
docker-compose -f docker-compose.test-notifications.yml up --abort-on-container-exit notification-tester

# Check exit code
echo $?  # 0 for success, non-zero for failures
```

### Monitoring and Observability

- **Health Checks**: All services expose `/health` endpoints
- **Metrics**: Test execution times and success rates
- **Logging**: Structured logs with tenant context
- **Results API**: JSON test results for automation

### Security

- **Non-root Containers**: All services run as non-root users
- **Network Isolation**: Services communicate via dedicated network
- **Volume Permissions**: Proper file ownership and read-only configs
- **Rate Limiting**: SMS sink includes rate limiting for webhook endpoints