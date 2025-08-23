# Cross-Platform Configuration Management API

## Overview

The DotMac Management Platform provides unified configuration management across the platform and all tenant ISP Framework instances, resolving the "inverted security pattern" through coordinated configuration orchestration.

## Authentication

All configuration endpoints require platform administrative privileges:

```http
Authorization: Bearer <platform-admin-jwt-token>
X-Platform-Role: management-admin
```

## Base URL

```
https://management.dotmac.app/api/v1/config
```

## Multi-Tenant Configuration Orchestration

### Tenant Secret Provisioning

#### Create Tenant Secret Namespace
```http
POST /tenant/{tenant_id}/secrets/namespace
```

**Request Body:**
```json
{
  "namespace_name": "tenant-123-production",
  "isolation_level": "strict",
  "default_rotation_policy": {
    "interval_days": 30,
    "auto_rotation": true,
    "notification_webhooks": ["https://tenant-123.dotmac.app/webhook/secret-rotation"]
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "namespace_id": "ns_abc123",
    "tenant_id": "tenant-123",
    "openbao_path": "dotmac/tenants/tenant-123",
    "created_at": "2024-01-15T10:30:00Z",
    "access_policies": [
      "tenant-123-read-secrets",
      "tenant-123-write-secrets"
    ]
  }
}
```

#### Provision Tenant Secrets
```http
POST /tenant/{tenant_id}/secrets/provision
```

**Request Body:**
```json
{
  "secrets": {
    "database": {
      "host": "tenant-123-db.internal",
      "password": "generated-secure-password",
      "ssl_cert": "-----BEGIN CERTIFICATE-----..."
    },
    "stripe": {
      "secret_key": "sk_live_tenant123...",
      "webhook_secret": "whsec_tenant123..."
    },
    "plugin_licenses": {
      "advanced_analytics": "license-key-123",
      "white_labeling": "license-key-456"
    }
  },
  "propagate_to_isp_framework": true,
  "validate_on_target": true
}
```

### Cross-Platform Configuration Updates

#### Coordinate Configuration Update
```http
PUT /tenant/{tenant_id}/config/coordinate
```

**Request Body:**
```json
{
  "configuration": {
    "billing": {
      "stripe_webhook_endpoint": "https://tenant-123.dotmac.app/webhooks/stripe",
      "payment_methods": ["card", "ach", "wire"]
    },
    "features": {
      "advanced_analytics": true,
      "white_labeling": true,
      "api_access": "unlimited"
    }
  },
  "coordination_strategy": "management_first",
  "rollback_on_failure": true,
  "validate_consistency": true
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "coordination_id": "coord_xyz789",
    "status": "completed",
    "execution_order": [
      {
        "platform": "management",
        "status": "success",
        "timestamp": "2024-01-15T10:30:00Z"
      },
      {
        "platform": "tenant_isp_framework",
        "status": "success", 
        "timestamp": "2024-01-15T10:30:15Z"
      }
    ],
    "consistency_validation": {
      "status": "consistent",
      "verified_at": "2024-01-15T10:30:30Z"
    }
  }
}
```

### Cross-Platform Hot-Reload

#### Orchestrate Hot-Reload
```http
POST /tenant/{tenant_id}/config/hot-reload/orchestrate
```

**Request Body:**
```json
{
  "component": "billing_gateway",
  "platforms": ["management", "tenant_isp_framework"],
  "coordination_mode": "synchronized",
  "validate_both_platforms": true,
  "emergency_rollback": true
}
```

### Multi-Tenant Audit Orchestration

#### Log Cross-Platform Event
```http
POST /audit/cross-platform
```

**Request Body:**
```json
{
  "source_platform": "management_platform",
  "target_platform": "tenant_isp_framework",
  "tenant_id": "tenant-123",
  "event_type": "configuration_update",
  "event_data": {
    "component": "billing_gateway",
    "change_type": "webhook_endpoint_update",
    "old_value": "https://old-webhook.example.com",
    "new_value": "https://new-webhook.example.com"
  },
  "correlation_id": "corr_def456",
  "metadata": {
    "user_id": "admin_789",
    "change_reason": "Webhook endpoint migration",
    "approval_id": "approval_ghi123"
  }
}
```

#### Get Tenant Audit Summary
```http
GET /audit/tenant/{tenant_id}/summary
```

**Query Parameters:**
- `start_date`: ISO 8601 date
- `end_date`: ISO 8601 date  
- `platforms`: Comma-separated list of platforms
- `event_types`: Filter by event types

**Response:**
```json
{
  "success": true,
  "data": {
    "tenant_id": "tenant-123",
    "summary_period": {
      "start": "2024-01-01T00:00:00Z",
      "end": "2024-01-31T23:59:59Z"
    },
    "platforms": {
      "management_platform": {
        "total_events": 45,
        "configuration_changes": 12,
        "secret_operations": 8,
        "compliance_checks": 25
      },
      "tenant_isp_framework": {
        "total_events": 123,
        "configuration_changes": 35,
        "portal_authentications": 88
      }
    },
    "cross_platform_events": {
      "coordinated_updates": 8,
      "secret_propagations": 5,
      "disaster_recoveries": 0
    },
    "compliance_status": {
      "SOC2": "compliant",
      "GDPR": "compliant", 
      "PCI_DSS": "requires_attention"
    }
  }
}
```

## Platform-Wide Operations

### Emergency Secret Rotation

#### Coordinate Emergency Rotation
```http
POST /emergency/secret-rotation
```

**Request Body:**
```json
{
  "affected_tenants": ["tenant-123", "tenant-456", "tenant-789"],
  "secret_types": ["database_passwords", "api_keys"],
  "rotation_strategy": "immediate",
  "coordination_mode": "parallel",
  "notify_tenants": true,
  "rollback_plan": "automatic"
}
```

### Disaster Recovery Coordination

#### Coordinate Multi-Tenant Disaster Recovery
```http
POST /disaster-recovery/coordinate
```

**Request Body:**
```json
{
  "disaster_scenario": "configuration_corruption",
  "affected_tenants": ["tenant-123", "tenant-456"],
  "recovery_strategy": "automated_rollback",
  "coordination_mode": "sequential",
  "validation_checks": {
    "pre_recovery": true,
    "post_recovery": true,
    "cross_platform_consistency": true
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "disaster_recovery_id": "dr_jkl012",
    "status": "in_progress",
    "affected_tenants": ["tenant-123", "tenant-456"],
    "recovery_timeline": {
      "started_at": "2024-01-15T10:30:00Z",
      "estimated_completion": "2024-01-15T10:45:00Z"
    },
    "tenant_progress": {
      "tenant-123": {
        "status": "completed",
        "recovery_actions": ["configuration_rollback", "service_restart"],
        "validation_status": "passed"
      },
      "tenant-456": {
        "status": "in_progress",
        "current_action": "configuration_rollback",
        "estimated_completion": "2024-01-15T10:40:00Z"
      }
    }
  }
}
```

### Compliance Orchestration

#### Run Platform-Wide Compliance Check
```http
POST /compliance/all-tenants/validate
```

**Request Body:**
```json
{
  "frameworks": ["SOC2", "GDPR", "PCI_DSS"],
  "tenant_filter": {
    "subscription_tiers": ["professional", "enterprise"],
    "regions": ["us", "eu"]
  },
  "validation_mode": "comprehensive",
  "generate_remediation_plans": true
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "validation_id": "val_mno345",
    "overall_status": "mixed_compliance",
    "tenant_results": {
      "tenant-123": {
        "overall_status": "compliant",
        "framework_scores": {
          "SOC2": 98,
          "GDPR": 100,
          "PCI_DSS": 95
        }
      },
      "tenant-456": {
        "overall_status": "requires_attention",
        "framework_scores": {
          "SOC2": 85,
          "GDPR": 92,
          "PCI_DSS": 78
        },
        "violations": [
          {
            "framework": "PCI_DSS",
            "code": "3.4.1",
            "tenant_issue": "Credit card key rotation overdue",
            "remediation": "Execute emergency key rotation"
          }
        ]
      }
    },
    "platform_summary": {
      "compliant_tenants": 1,
      "non_compliant_tenants": 1,
      "total_violations": 1,
      "remediation_plan_generated": true
    }
  }
}
```

## Configuration Consistency Validation

### Cross-Platform Consistency Check
```http
POST /validation/cross-platform-consistency
```

**Request Body:**
```json
{
  "tenant_ids": ["tenant-123", "tenant-456"],
  "configuration_components": ["secrets", "features", "billing"],
  "consistency_rules": {
    "secrets": "exact_match",
    "features": "entitlement_based",
    "billing": "configuration_aligned"
  }
}
```

### Tenant Configuration Drift Detection
```http
GET /tenant/{tenant_id}/config/drift
```

**Response:**
```json
{
  "success": true,
  "data": {
    "tenant_id": "tenant-123",
    "drift_detected": true,
    "drift_analysis": {
      "management_platform_config": {
        "billing_gateway": "stripe_v2",
        "feature_flags": {"analytics": true, "reporting": true}
      },
      "isp_framework_config": {
        "billing_gateway": "stripe_v1",
        "feature_flags": {"analytics": true, "reporting": false}
      },
      "differences": [
        {
          "path": "billing_gateway",
          "management_value": "stripe_v2",
          "isp_framework_value": "stripe_v1",
          "impact": "medium",
          "recommendation": "Update ISP Framework to stripe_v2"
        },
        {
          "path": "feature_flags.reporting", 
          "management_value": true,
          "isp_framework_value": false,
          "impact": "high",
          "recommendation": "Sync reporting feature flag"
        }
      ]
    }
  }
}
```

## Plugin License Management

### Provision Plugin Licenses
```http
POST /tenant/{tenant_id}/plugins/provision
```

**Request Body:**
```json
{
  "licenses": [
    {
      "plugin_id": "advanced_analytics",
      "license_tier": "enterprise",
      "usage_limits": {
        "api_calls_per_month": 100000,
        "storage_gb": 500,
        "users": "unlimited"
      },
      "expiration_date": "2024-12-31T23:59:59Z"
    },
    {
      "plugin_id": "white_labeling",
      "license_tier": "premium",
      "usage_limits": {
        "custom_domains": 5,
        "branded_emails": 10000
      }
    }
  ],
  "auto_activate": true,
  "sync_to_isp_framework": true
}
```

### Update Plugin Entitlements
```http
PUT /tenant/{tenant_id}/plugins/{plugin_id}/entitlements
```

## Multi-Tenant Monitoring

### Platform Health Dashboard Data
```http
GET /monitoring/platform-health
```

**Response:**
```json
{
  "success": true,
  "data": {
    "platform_status": "healthy",
    "total_tenants": 150,
    "healthy_tenants": 148,
    "degraded_tenants": 2,
    "failed_tenants": 0,
    "configuration_statistics": {
      "active_configurations": 150,
      "pending_updates": 5,
      "failed_updates": 0,
      "compliance_violations": 3
    },
    "cross_platform_metrics": {
      "average_consistency_score": 98.5,
      "configuration_drift_incidents": 2,
      "disaster_recoveries_this_month": 0
    }
  }
}
```

### Tenant Resource Usage
```http
GET /monitoring/tenant/{tenant_id}/usage
```

## Webhooks and Notifications

### Platform-Level Configuration Webhooks
```http
POST /webhooks/platform
```

**Request Body:**
```json
{
  "url": "https://monitoring.dotmac.internal/platform-webhook",
  "events": [
    "tenant.configuration.updated",
    "cross_platform.consistency.violation",
    "disaster_recovery.executed",
    "compliance.violation.detected"
  ],
  "tenant_filter": {
    "subscription_tiers": ["enterprise"],
    "regions": ["all"]
  }
}
```

## Error Handling

### Cross-Platform Configuration Errors

```json
{
  "success": false,
  "error": {
    "code": "CROSS_PLATFORM_SYNC_FAILED",
    "message": "Failed to synchronize configuration across platforms",
    "details": {
      "tenant_id": "tenant-123",
      "failed_platform": "tenant_isp_framework",
      "error_reason": "Connection timeout during hot-reload",
      "rollback_status": "initiated",
      "recovery_options": [
        "retry_sync",
        "manual_intervention",
        "emergency_rollback"
      ]
    }
  }
}
```

## SDK Integration

```python
from dotmac_management.sdks.config import CrossPlatformConfigClient

# Initialize client
config_client = CrossPlatformConfigClient(
    base_url="https://management.dotmac.app",
    api_key="mgmt-api-key-123"
)

# Coordinate tenant configuration update
coordination_result = await config_client.coordinate_tenant_config(
    tenant_id="tenant-123",
    configuration={
        "billing": {"stripe_webhook_endpoint": "new-endpoint"},
        "features": {"advanced_analytics": True}
    },
    coordination_strategy="management_first",
    rollback_on_failure=True
)

# Check cross-platform consistency
consistency_report = await config_client.validate_consistency(
    tenant_ids=["tenant-123", "tenant-456"],
    components=["secrets", "features", "billing"]
)

# Execute emergency disaster recovery
disaster_recovery = await config_client.coordinate_disaster_recovery(
    affected_tenants=["tenant-123"],
    recovery_strategy="automated_rollback"
)
```

## Security Considerations

### Enhanced Security Model
- **Security Parity**: Management Platform now matches ISP Framework security standards
- **Cross-Platform Encryption**: All configuration data encrypted in transit and at rest
- **Multi-Tenant Isolation**: Complete tenant separation at all configuration layers
- **Audit Orchestration**: Unified audit trails across both platforms
- **Compliance Coordination**: Synchronized compliance validation and remediation

### Access Control
- Platform administrators require explicit cross-platform configuration permissions
- Tenant-specific configuration access isolated by tenant boundaries
- Emergency operations require additional authorization
- All configuration changes logged with full audit trails