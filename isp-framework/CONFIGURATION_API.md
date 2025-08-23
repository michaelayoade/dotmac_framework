# Configuration Management API Reference

## Overview

The DotMac ISP Framework provides comprehensive configuration management APIs with enterprise-grade security, audit trails, and disaster recovery capabilities.

## Authentication

All configuration management endpoints require administrative privileges:

```http
Authorization: Bearer <admin-jwt-token>
```

## Base URL

```
https://your-instance.dotmac.app/api/v1/config
```

## Configuration Management Endpoints

### Secrets Management

#### Store Secret
```http
POST /secrets/{secret_path}
```

**Request Body:**
```json
{
  "value": "secret-value",
  "description": "Secret description",
  "rotation_interval_days": 30,
  "metadata": {
    "service": "billing",
    "environment": "production"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "secret_id": "sec_abc123",
    "path": "stripe/secret_key",
    "created_at": "2024-01-15T10:30:00Z",
    "next_rotation": "2024-02-14T10:30:00Z",
    "version": 1
  }
}
```

#### Retrieve Secret
```http
GET /secrets/{secret_path}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "value": "sk_live_...",
    "metadata": {
      "created_at": "2024-01-15T10:30:00Z",
      "version": 1,
      "rotation_status": "current"
    }
  }
}
```

#### Rotate Secret
```http
POST /secrets/{secret_path}/rotate
```

**Request Body:**
```json
{
  "new_value": "new-secret-value",
  "force_rotation": false,
  "notify_services": ["billing", "payments"]
}
```

#### List Secrets
```http
GET /secrets
```

**Query Parameters:**
- `service`: Filter by service
- `environment`: Filter by environment
- `rotation_due`: Show only secrets due for rotation

### Hot-Reload Configuration

#### Trigger Configuration Reload
```http
POST /hot-reload
```

**Request Body:**
```json
{
  "component": "database",
  "validate_only": false,
  "rollback_on_failure": true,
  "services_to_reload": ["billing", "identity"]
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "reload_id": "reload_xyz789",
    "status": "completed",
    "affected_services": ["billing", "identity"],
    "validation_results": {
      "database": {"status": "valid", "connection_test": "passed"},
      "billing": {"status": "valid", "stripe_connectivity": "passed"}
    },
    "rollback_available": true
  }
}
```

#### Get Reload Status
```http
GET /hot-reload/{reload_id}
```

#### Emergency Rollback
```http
POST /hot-reload/{reload_id}/rollback
```

### Configuration Backup & Recovery

#### Create Backup
```http
POST /backup
```

**Request Body:**
```json
{
  "backup_name": "pre-production-update",
  "include_secrets": false,
  "components": ["database", "redis", "application"]
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "backup_id": "backup_def456",
    "backup_name": "pre-production-update",
    "created_at": "2024-01-15T10:30:00Z",
    "size_bytes": 1048576,
    "components_included": ["database", "redis", "application"]
  }
}
```

#### List Backups
```http
GET /backup
```

#### Restore from Backup
```http
POST /backup/{backup_id}/restore
```

**Request Body:**
```json
{
  "components": ["database", "redis"],
  "confirm_restore": true,
  "backup_current_config": true
}
```

### Audit Trail

#### Get Configuration Audit Log
```http
GET /audit
```

**Query Parameters:**
- `start_date`: ISO 8601 date (default: 30 days ago)
- `end_date`: ISO 8601 date (default: now)
- `user_id`: Filter by user
- `component`: Filter by component
- `action`: Filter by action type

**Response:**
```json
{
  "success": true,
  "data": {
    "total_records": 150,
    "page": 1,
    "per_page": 20,
    "audit_entries": [
      {
        "id": "audit_ghi789",
        "timestamp": "2024-01-15T10:30:00Z",
        "user_id": "user_123",
        "component": "billing",
        "action": "configuration_update",
        "old_values": {"stripe_webhook_url": "old-url"},
        "new_values": {"stripe_webhook_url": "new-url"},
        "change_reason": "Updated webhook endpoint",
        "approval_status": "approved",
        "risk_score": "low"
      }
    ]
  }
}
```

#### Get Specific Audit Entry
```http
GET /audit/{audit_id}
```

### Compliance Validation

#### Run Compliance Check
```http
POST /compliance/validate
```

**Request Body:**
```json
{
  "frameworks": ["SOC2", "GDPR", "PCI_DSS", "ISO27001"],
  "components": ["database", "secrets", "audit"]
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "validation_id": "val_jkl012",
    "overall_status": "compliant",
    "frameworks": {
      "SOC2": {
        "status": "compliant",
        "score": 95,
        "violations": [],
        "recommendations": ["Enable additional audit logging"]
      },
      "GDPR": {
        "status": "compliant",
        "score": 98,
        "violations": [],
        "recommendations": []
      },
      "PCI_DSS": {
        "status": "non_compliant",
        "score": 78,
        "violations": [
          {
            "code": "PCI_3.4.1",
            "description": "Credit card encryption key rotation interval exceeds 12 months",
            "severity": "high",
            "remediation": "Reduce key rotation interval to 6 months"
          }
        ]
      }
    }
  }
}
```

#### Get Compliance Report
```http
GET /compliance/report
```

### Disaster Recovery

#### Detect Configuration Issues
```http
POST /disaster-recovery/detect
```

**Response:**
```json
{
  "success": true,
  "data": {
    "disaster_detected": true,
    "disaster_type": "configuration_corruption",
    "affected_components": ["database", "billing"],
    "severity": "high",
    "estimated_impact": "service_degradation",
    "recommended_actions": [
      "restore_from_backup",
      "emergency_rollback"
    ]
  }
}
```

#### Execute Disaster Recovery
```http
POST /disaster-recovery/execute
```

**Request Body:**
```json
{
  "disaster_id": "disaster_mno345",
  "recovery_strategy": "automated_rollback",
  "confirm_execution": true,
  "notify_stakeholders": true
}
```

## Configuration Encryption

### Field Encryption Status
```http
GET /encryption/status
```

**Response:**
```json
{
  "success": true,
  "data": {
    "encryption_enabled": true,
    "encrypted_fields": [
      {
        "field_path": "database.password",
        "encryption_type": "AES-256-GCM",
        "key_rotation_date": "2024-01-01T00:00:00Z"
      },
      {
        "field_path": "stripe.secret_key",
        "encryption_type": "AES-256-GCM",
        "key_rotation_date": "2024-01-01T00:00:00Z"
      }
    ]
  }
}
```

### Rotate Encryption Keys
```http
POST /encryption/rotate-keys
```

## Health Monitoring

### Configuration Health Check
```http
GET /health
```

**Response:**
```json
{
  "success": true,
  "data": {
    "overall_status": "healthy",
    "components": {
      "openbao": {
        "status": "healthy",
        "response_time_ms": 45,
        "last_check": "2024-01-15T10:29:00Z"
      },
      "database": {
        "status": "healthy",
        "connection_pool_size": 10,
        "active_connections": 3
      },
      "redis": {
        "status": "healthy",
        "memory_usage_mb": 256,
        "connected_clients": 5
      }
    }
  }
}
```

## Error Responses

All endpoints return standardized error responses:

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid configuration data",
    "details": {
      "field": "database.port",
      "issue": "Port must be between 1 and 65535"
    }
  },
  "timestamp": "2024-01-15T10:30:00Z",
  "request_id": "req_pqr678"
}
```

### Common Error Codes

- `VALIDATION_ERROR`: Invalid input data
- `AUTHORIZATION_ERROR`: Insufficient permissions
- `CONFIGURATION_LOCKED`: Configuration currently being modified
- `BACKUP_IN_PROGRESS`: Backup operation in progress
- `DISASTER_RECOVERY_ACTIVE`: System in disaster recovery mode
- `COMPLIANCE_VIOLATION`: Operation would violate compliance requirements

## Rate Limiting

Configuration management endpoints are rate limited:
- Standard operations: 100 requests per minute per user
- Sensitive operations (secret rotation, disaster recovery): 10 requests per minute per user

## Webhooks

Configure webhooks to receive notifications about configuration changes:

```http
POST /webhooks
```

**Request Body:**
```json
{
  "url": "https://your-app.com/config-webhook",
  "events": [
    "configuration.updated",
    "secret.rotated",
    "backup.created",
    "compliance.violation"
  ],
  "secret": "webhook-signing-secret"
}
```

## SDK Example

```python
from dotmac_isp.sdks.core.config import ConfigurationClient

# Initialize client
config_client = ConfigurationClient(
    base_url="https://your-instance.dotmac.app",
    api_key="your-api-key"
)

# Store a secret
secret = await config_client.store_secret(
    path="stripe/secret_key",
    value="sk_live_...",
    rotation_interval_days=30
)

# Hot-reload configuration
reload_result = await config_client.hot_reload(
    component="billing",
    validate_only=False
)

# Create backup before major changes
backup = await config_client.create_backup(
    name="pre-production-deployment",
    include_secrets=False
)
```

## Best Practices

### Security
1. Always use HTTPS for configuration API calls
2. Rotate API keys regularly
3. Use least-privilege access for configuration operations
4. Monitor configuration audit logs regularly

### Operations
1. Create backups before major configuration changes
2. Use `validate_only=true` to test changes before applying
3. Set up webhooks for critical configuration events
4. Implement emergency rollback procedures

### Compliance
1. Run regular compliance validations
2. Document configuration changes with change reasons
3. Maintain audit trails for regulatory requirements
4. Review and approve high-risk configuration changes