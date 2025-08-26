# DotMac Management Platform

**Multi-tenant SaaS platform for deploying and managing DotMac ISP Framework instances.**

## 🏗️ Architecture

- **Multi-Tenant SaaS**: Each ISP customer gets isolated DotMac instance
- **Automated Deployment**: One-click ISP onboarding with OpenTofu infrastructure provisioning
- **Centralized Management**: Single pane of glass for all tenant operations
- **Secrets Management**: OpenBao integration for secure credential management
- **Observability**: SignOz for unified metrics, traces, and logs across all tenants

## 🚀 Quick Start

```bash
# Install dependencies and setup development
make install-dev

# Start all services (includes Kubernetes cluster simulation)
make up

# Run quality checks
make check

# Access the management platform
open http://localhost:8000  # Management Platform API
open http://localhost:3000  # Master Admin Portal  
open http://localhost:3001  # Tenant Admin Portal
open http://localhost:3002  # Reseller Portal

# Test tenant deployment (simulates Kubernetes orchestration)
curl -X POST http://localhost:8000/api/v1/tenant-orchestration/deployments \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_name": "Demo ISP",
    "resource_tier": "small", 
    "license_tier": "professional",
    "domain_name": "demo-isp.dotmac.app"
  }'
```

## 🔧 Technology Stack

- **Backend**: Python/FastAPI with async/await
- **Database**: PostgreSQL with multi-tenant architecture
- **Cache/Queue**: Redis for caching & background jobs
- **Container Orchestration**: Kubernetes for tenant isolation and scaling
- **Plugin System**: Tiered licensing with usage tracking and billing
- **Monitoring**: Real-time health checks and SLA compliance tracking
- **Infrastructure**: OpenTofu for infrastructure + Kubernetes for workloads
- **Configuration**: **Unified Enhanced Configuration** with OpenBao integration
- **Secrets**: **Multi-Tenant OpenBao** with automatic rotation and cross-platform audit orchestration
- **Security**: **Cross-Platform Configuration Security** with encryption, hot-reloading, and disaster recovery
- **Observability**: SignOz for metrics, traces, logs + **Configuration Audit Trails**
- **Frontend**: React/Next.js with TypeScript

## 📁 Project Structure

```
src/mgmt/                    # Core management services
├── services/                # Business services
├── shared/                  # Common infrastructure  
├── api/                     # API layer
└── main.py                  # FastAPI application

deployment/                  # Infrastructure as Code
├── opentofu/                # OpenTofu templates
├── ansible/                 # Configuration management
└── docker/                  # Container configurations

portals/                     # Web interfaces
├── master_admin/            # Platform operator portal
├── tenant_admin/            # ISP customer portal
└── reseller/                # Reseller partner portal

config/                      # Configuration templates
├── openbao/                 # OpenBao policies & configs
├── monitoring/              # SignOz configurations
└── security/                # Security templates
```

## 🎯 Core Features

### ISP Customer Management
- **Automated Tenant Onboarding**: One-click ISP customer deployment to Kubernetes
- **Resource Tier Management**: Micro to XLarge deployments based on subscription plan
- **Container Orchestration**: Kubernetes-based tenant isolation and scaling
- **Real-time Health Monitoring**: Comprehensive SLA tracking and alerting

### Plugin Licensing System  
- **Tiered Plugin Marketplace**: Free, Basic, Premium, Enterprise plugin tiers
- **Usage-Based Billing**: Track API calls, storage, transactions per plugin
- **Feature Entitlements**: License-controlled access to advanced functionality
- **Trial Management**: Automated trial-to-paid conversion workflows

### SaaS Monitoring & Compliance
- **Multi-Tenant Health Checks**: Automated health validation for all tenants
- **SLA Metrics Calculation**: Availability, response time, error rate tracking
- **Real-time Alerting**: Severity-based alert escalation and incident management
- **Compliance Reporting**: Automated SLA compliance and violation tracking

### Container-Based Deployment
- **Kubernetes Orchestration**: Per-tenant namespace isolation and resource management
- **Horizontal Scaling**: Automatic scaling based on tenant subscription and usage
- **Zero-Downtime Updates**: Rolling deployments with health check validation
- **Multi-Cloud Support**: Deploy tenant workloads across AWS, Azure, GCP, DigitalOcean

### Business Operations
- **Subscription Management**: Tenant lifecycle with plugin licensing integration
- **Reseller Network**: Channel partner commission tracking with recurring revenue focus
- **Cross-Tenant Analytics**: Privacy-preserving insights across tenant base
- **Cost Optimization**: Resource usage optimization and cost management

## 🌐 Deployment Targets

- **AWS**: EC2, RDS, ElastiCache, ALB, Route53
- **Azure**: Virtual Machines, Azure Database, Redis Cache
- **Google Cloud**: Compute Engine, Cloud SQL, Memorystore
- **DigitalOcean**: Droplets, Managed Databases, Load Balancers
- **BYOV**: Bring Your Own VPS support

## 📊 Business Model

### **Core Revenue Streams**
- **Tenant Subscriptions**: Per-ISP monthly recurring revenue with resource tiers
- **Plugin Licensing**: Tiered plugin marketplace (Free → Basic → Premium → Enterprise)
- **Usage-Based Billing**: API calls, storage, transactions, and advanced feature usage
- **Reseller Network**: Channel partner revenue sharing with recurring commissions

### **Plugin Monetization**
- **Free Tier**: Basic customer management, simple billing, standard reporting
- **Basic Tier**: Advanced billing, CRM integrations, API access
- **Premium Tier**: Advanced analytics, custom integrations, white-labeling
- **Enterprise Tier**: AI insights, predictive analytics, unlimited APIs

### **SaaS Scalability**
- **Container-Based Deployment**: Kubernetes orchestration for infinite tenant scaling
- **Feature Gating**: License-controlled access to plugins and advanced features
- **Geographic Expansion**: Multi-cloud deployment for global ISP customers

## 🔐 Unified Configuration Management

### Cross-Platform Security Architecture

The Management Platform implements **unified configuration management** ensuring security parity between the orchestrator and the orchestrated ISP Framework instances:

```python
# Multi-tenant secrets management
mgmt_platform.secrets_manager.create_tenant_secret_namespace("tenant-123")
mgmt_platform.secrets_manager.provision_tenant_secrets("tenant-123", isp_framework_secrets)

# Cross-platform audit orchestration
audit_orchestrator.log_cross_platform_event(
    source="management_platform",
    target="tenant-isp-framework",
    event="configuration_update",
    tenant_id="tenant-123"
)

# Configuration hot-reload coordination
await mgmt_platform.orchestrate_config_reload(
    tenant_id="tenant-123",
    component="billing_gateway",
    validate_both_platforms=True
)
```

### Enhanced Configuration Features

#### **1. Multi-Tenant Secrets Management**
- **Per-Tenant OpenBao Namespaces**: Isolated secret storage for each ISP customer
- **Cross-Platform Secret Sync**: Automatic secret provisioning to tenant ISP Framework instances
- **Tenant-Specific License Secrets**: Plugin licensing and feature activation credentials
- **Emergency Secret Rotation**: Platform-wide emergency rotation capabilities

#### **2. Cross-Platform Configuration Orchestration**
```python
# Configuration orchestration between platforms
class ConfigurationOrchestrator:
    async def coordinate_tenant_config_update(tenant_id: str, config_data: Dict[str, Any]):
        """Coordinate configuration updates across Management Platform and ISP Framework"""
        
        # Update Management Platform tenant configuration
        await self.update_management_platform_config(tenant_id, config_data)
        
        # Propagate to tenant ISP Framework instance
        await self.update_tenant_isp_framework(tenant_id, config_data)
        
        # Validate configuration consistency
        await self.validate_cross_platform_consistency(tenant_id)
        
        # Log cross-platform audit trail
        await self.audit_orchestrator.log_coordinated_update(tenant_id, config_data)
```

#### **3. Unified Audit Trail System**
- **Cross-Platform Event Correlation**: Link configuration events between Management Platform and ISP Framework
- **Tenant Audit Aggregation**: Consolidated audit reports per ISP customer
- **Compliance Orchestration**: Coordinated compliance validation across both platforms
- **Security Event Correlation**: Unified security monitoring and incident response

#### **4. Coordinated Disaster Recovery**
```bash
# Disaster recovery coordination
curl -X POST http://management-platform:8000/admin/disaster-recovery/coordinate \
  -H "Authorization: Bearer <admin-token>" \
  -d '{
    "scenario": "configuration_corruption",
    "affected_tenants": ["tenant-123", "tenant-456"],
    "recovery_strategy": "automated_rollback"
  }'

# Cross-platform backup orchestration
curl -X POST http://management-platform:8000/admin/config/backup-all-tenants \
  -H "Authorization: Bearer <admin-token>"
```

### Configuration Management APIs

#### **Management Platform Configuration Endpoints**
```python
# Multi-tenant configuration management
POST   /api/v1/config/tenant/{tenant_id}/secrets        # Provision tenant secrets
PUT    /api/v1/config/tenant/{tenant_id}/update         # Update tenant configuration
POST   /api/v1/config/tenant/{tenant_id}/hot-reload     # Trigger hot-reload
GET    /api/v1/config/tenant/{tenant_id}/audit          # Get configuration audit trail
POST   /api/v1/config/cross-platform/validate          # Validate cross-platform consistency

# Platform-wide operations
POST   /api/v1/config/emergency-rotation                # Emergency secret rotation
POST   /api/v1/config/disaster-recovery                 # Coordinate disaster recovery
GET    /api/v1/config/compliance/all-tenants            # Platform compliance report
```

### Security Model: "Inverted Security Pattern" Resolution

Previously, the Management Platform had **weaker security** than the ISP Framework it manages - an "inverted security model" where the orchestrator was less secure than the orchestrated systems.

**Problem Resolved**: The Management Platform now implements **security parity** or **enhanced security** compared to the ISP Framework:

- ✅ **Same encryption standards** across both platforms
- ✅ **Unified secrets management** with OpenBao integration
- ✅ **Cross-platform audit orchestration** for complete visibility
- ✅ **Coordinated disaster recovery** between platforms
- ✅ **Enhanced multi-tenant isolation** at the orchestrator level