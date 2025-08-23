# CLAUDE.md - DotMac Management Platform

This file provides guidance to Claude Code (claude.ai/code) when working with the **DotMac Management Platform** codebase.

## Repository Overview

This is the **DotMac Management Platform** - a multi-tenant SaaS orchestration platform for managing and deploying DotMac ISP Framework instances. The platform enables ISPs to be onboarded as tenants with isolated, scalable deployments orchestrated through Kubernetes.

## Architecture

**Multi-Tenant SaaS Platform**: Enterprise-grade orchestration system for ISP Framework deployment and management:

- `app/` - Core Management Platform services (FastAPI)
- `src/mgmt/` - Management orchestration services and SDKs  
- `portals/` - Multi-tenant web interfaces (master admin, tenant admin, reseller)
- `deployment/` - Infrastructure as Code (OpenTofu, Ansible, Kubernetes)
- `config/` - Configuration templates (OpenBao, SignOz, security policies)

**Business Model**: SaaS platform with plugin licensing, usage-based billing, and reseller network.

## Essential Commands

### Quick Start
```bash
# Show all available commands
make help

# Check status and health
make status && make health-check
```

### AI-First Development Workflow (NEW PARADIGM)
```bash
# AI Safety Checks (CRITICAL - Always run first)
make ai-safety-check

# AI-Optimized Test Suite (Primary testing approach)
make test-ai-suite

# Property-based testing (AI generates thousands of test cases)  
make test-property-based

# Business behavior testing (outcome-focused)
make test-behavior

# API contract testing (schema validation)
make test-contract

# Revenue-critical smoke tests (billing, licensing, commissions)
make test-revenue-critical

# SaaS platform-specific tests (orchestration, isolation, monitoring)
make test-saas-platform
```

### Traditional Development (Legacy - Optional)
```bash
# Development setup
make install-dev

# Code quality (AI can skip these)
make format && make lint

# Traditional test suite (comprehensive but slower)
make test

# Security scanning (always important)
make security
```

### Docker Development Environment
```bash
# Build and start complete SaaS environment
make docker-build && make up

# Access points:
# - API: http://localhost:8000
# - Master Admin Portal: http://localhost:3000
# - Tenant Admin Portal: http://localhost:3001  
# - Reseller Portal: http://localhost:3002
# - SignOz Monitoring: http://localhost:3301
# - OpenBao: http://localhost:8200

# Stop environment
make down
```

### Database & Infrastructure
```bash
# Run database migrations
make db-migrate

# Reset database (development only)
make db-reset

# Infrastructure operations
make infra-validate
make infra-plan
make infra-apply ENVIRONMENT=development
```

### Service Operations
```bash
# Start API server
make run-api

# Start background workers
make run-worker
make run-beat

# Monitor logs
make logs
```

### Cost Management & Analysis
```bash
# Analyze infrastructure costs
make cost-analysis

# Monitor tenant resource usage
make metrics
```

## AI-First Code Standards

**CRITICAL PARADIGM SHIFT**: This Management Platform is optimized for AI-first development with revenue protection.

### Non-Negotiable Gates (Revenue Critical)
- **Tenant billing accuracy** - AI must never alter billing calculations incorrectly
- **Multi-tenant isolation** - AI changes must maintain complete tenant data separation  
- **Plugin licensing logic** - AI must preserve usage-based billing mechanisms
- **Reseller commission calculations** - AI must not break partner payment logic
- **Deployment orchestration safety** - AI must maintain Kubernetes deployment integrity
- **Security compliance** - AI changes must pass SOC2/GDPR/PCI compliance checks

### Optional Gates (Development Convenience)
- Code formatting - AI handles complexity better than humans
- Traditional test coverage - AI uses property-based and behavior testing
- Linting warnings - AI focuses on business outcomes over style

### AI-First Testing Philosophy
**Revenue-Critical Testing**: Focus on business outcomes that directly impact revenue:
1. **Property-based tests** (40%) - AI generates edge cases for billing/licensing logic
2. **Behavior tests** (30%) - Validate business outcomes (customer onboarding, upselling, churn prevention)
3. **Contract tests** (20%) - API schema validation for service integrations  
4. **Safety checks** (10%) - Revenue-critical path validation

## Service Architecture

**Multi-Tenant SaaS Services**:

### Core Platform Services (`app/`)
- **Tenant Service** - ISP customer lifecycle management
- **Billing Service** - Subscription billing, usage tracking, invoicing
- **Deployment Service** - Kubernetes orchestration for tenant deployments
- **Plugin Service** - Plugin marketplace and licensing management
- **User Management** - Multi-tenant authentication and RBAC

### Management Orchestration (`src/mgmt/`)
- **Kubernetes Orchestrator** - Tenant deployment automation
- **Plugin Licensing** - Usage-based billing and feature gates
- **SaaS Monitoring** - Health checks, SLA tracking, alerting
- **Reseller Network** - Partner management and commission tracking
- **Secrets Management** - Multi-tenant OpenBao orchestration

### Portal Interfaces (`portals/`)
- **Master Admin** - Platform operator interface
- **Tenant Admin** - ISP customer management portal
- **Reseller** - Partner portal with commission tracking

## Critical Business Logic Areas

### Revenue-Critical Components (PROTECTED)
1. **Tenant Billing Calculations** (`app/services/billing_service.py`)
2. **Plugin Usage Tracking** (`src/mgmt/services/plugin_licensing/`)
3. **Reseller Commission Logic** (`src/mgmt/services/reseller_network/`)
4. **Subscription State Management** (`app/models/billing.py`)
5. **Usage-Based Billing Aggregation** (`app/services/billing_service.py`)

### Multi-Tenant Isolation (SECURITY CRITICAL)
1. **Tenant Context Isolation** (`app/core/security.py`)
2. **Database Row-Level Security** (`app/models/base.py`)
3. **Kubernetes Namespace Isolation** (`src/mgmt/services/kubernetes_orchestrator/`)
4. **Secrets Namespace Separation** (`src/mgmt/shared/security/`)

### SaaS Orchestration (RELIABILITY CRITICAL)  
1. **Deployment Orchestration** (`app/services/deployment_service.py`)
2. **Auto-scaling Logic** (`src/mgmt/services/kubernetes_orchestrator/`)
3. **Health Monitoring** (`src/mgmt/services/saas_monitoring/`)
4. **Disaster Recovery** (`src/mgmt/shared/coordinated_disaster_recovery.py`)

## Development Patterns

### Multi-Tenant Patterns
- **Tenant Context**: All operations must include tenant isolation
- **Resource Quotas**: Enforce per-tenant resource limits
- **Billing Events**: Track all billable activities with audit trails
- **Plugin Entitlements**: Validate feature access based on licensing

### AI-Safe Business Logic
```python
# ✅ AI-Safe: Property-based testing protects this logic
@pytest.mark.property_based
@pytest.mark.revenue_critical
def test_billing_calculation_invariants(billing_data):
    result = calculate_monthly_cost(billing_data)
    
    # AI Safety: Never negative billing
    assert result >= Decimal("0.00")
    
    # AI Safety: Never exceed reasonable maximum
    assert result <= Decimal("100000.00")
```

### SaaS Monitoring Integration
```python  
# ✅ Health checks for tenant deployments
@app.middleware("http")
async def tenant_health_monitoring(request: Request, call_next):
    tenant_id = get_tenant_from_request(request)
    
    # Track tenant API usage for billing
    await record_api_usage(tenant_id, request.url.path)
    
    response = await call_next(request)
    
    # Monitor response times for SLA tracking
    await record_response_metrics(tenant_id, response.status_code, response_time)
    
    return response
```

## Environment Configuration

### Development Environment
- **Database**: PostgreSQL with tenant isolation
- **Cache**: Redis for session and API rate limiting  
- **Message Queue**: Redis for background job processing
- **Secrets**: OpenBao for multi-tenant secret management
- **Monitoring**: SignOz for observability across all tenants

### Multi-Tenant Configuration
```python
# Tenant-specific configuration example
TENANT_CONFIGS = {
    "resource_quotas": {
        "micro": {"cpu": "500m", "memory": "512Mi", "storage": "5Gi"},
        "small": {"cpu": "1", "memory": "2Gi", "storage": "20Gi"},
        "large": {"cpu": "4", "memory": "8Gi", "storage": "100Gi"}
    },
    "plugin_entitlements": {
        "basic": ["customer_portal", "basic_billing"],
        "professional": ["advanced_analytics", "api_access", "white_labeling"],
        "enterprise": ["custom_integrations", "priority_support", "sla_guarantees"]
    }
}
```

### Infrastructure as Code
- **OpenTofu**: Infrastructure provisioning across AWS/Azure/GCP/DigitalOcean
- **Kubernetes**: Container orchestration for tenant workloads
- **Ansible**: Configuration management and deployment automation

## Security & Compliance

### Multi-Tenant Security Model
- **Complete Data Isolation**: Each tenant's data is completely separated
- **OpenBao Integration**: Per-tenant secret namespaces with automatic rotation
- **Cross-Platform Audit**: Unified audit trails between Management Platform and ISP Framework
- **Configuration Encryption**: All sensitive configuration encrypted at rest and in transit

### Compliance Requirements
- **SOC 2 Type II**: Annual compliance audits
- **GDPR**: Data protection for EU customers
- **PCI DSS**: Payment card data security
- **ISO 27001**: Information security management

## Common Issues & Solutions

### Multi-Tenant Development Issues
- **Tenant Context Missing**: Ensure all database queries include tenant filtering
- **Resource Quota Exceeded**: Check tenant tier limits before deployment
- **Plugin Licensing Errors**: Validate entitlements before feature access
- **Billing Calculation Bugs**: Use property-based tests for edge cases

### SaaS Platform Issues
- **Deployment Failures**: Check Kubernetes cluster capacity and namespace limits
- **Performance Degradation**: Monitor per-tenant resource usage and implement auto-scaling
- **Security Violations**: Audit cross-tenant access attempts and strengthen isolation
- **Billing Discrepancies**: Reconcile usage tracking with actual plugin API calls

## Testing Strategy

### AI-First Testing Approach
1. **Property-based Testing**: Generate thousands of test cases for billing/licensing logic
2. **Business Behavior Testing**: Focus on revenue outcomes and customer experience
3. **Contract Testing**: Ensure API compatibility across service boundaries
4. **Safety Testing**: Validate revenue-critical paths and multi-tenant isolation

### Test Categories by Priority
1. **Revenue-Critical** (`@pytest.mark.revenue_critical`) - Billing, licensing, commissions
2. **Security-Critical** (`@pytest.mark.tenant_isolation`) - Multi-tenant data isolation  
3. **Reliability-Critical** (`@pytest.mark.deployment_orchestration`) - Service availability
4. **Performance-Critical** (`@pytest.mark.performance`) - SLA compliance

### Testing Commands by Business Impact
```bash
# 🚨 CRITICAL: Test revenue-generating functionality
make test-revenue-critical

# 🔒 SECURITY: Test multi-tenant isolation  
make test-smoke-critical -m "tenant_isolation"

# ⚡ PERFORMANCE: Test SLA compliance
make test-saas-platform

# 🤖 AI-GENERATED: Comprehensive edge case coverage
make test-property-based
```

## Success Metrics

### Platform Success Metrics
- **Tenant Onboarding Time**: < 5 minutes automated deployment
- **Platform Uptime**: 99.95% across all tenant deployments
- **Billing Accuracy**: 99.99% accuracy in usage-based billing
- **Partner Satisfaction**: Reseller commission accuracy and timeliness

### AI Development Success
- **Test Coverage**: Property-based tests cover 90%+ of edge cases
- **Deployment Safety**: Zero revenue-impacting bugs through AI safety checks
- **Development Velocity**: 3x faster feature development with AI-first approach
- **Business Outcome Focus**: Tests validate customer value, not just code correctness

---

# Important Instruction Reminders

NEVER create files unless absolutely necessary for achieving your goal.
ALWAYS prefer editing existing files to creating new ones.  
NEVER proactively create documentation files unless explicitly requested.

Focus on business outcomes, especially revenue-critical functionality. The Management Platform is a commercial SaaS product where billing accuracy, tenant isolation, and service reliability directly impact business success.