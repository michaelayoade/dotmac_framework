# 🚀 DotMac SaaS Platform - ISP Management at Scale

**Complete SaaS Platform for Internet Service Providers - Usage-Based Pricing**

**DotMac is a container-per-tenant SaaS platform** where ISPs get dedicated, isolated instances for managing their operations. ISPs pay per-customer pricing plus optional premium feature bundles. Each ISP gets their own secure container with complete operational independence.

**Perfect for ISPs with 50-10,000 customers** - from rural WISPs to regional cable providers.

## 🏗️ SaaS Container-per-Tenant Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                 DotMac SaaS Platform Architecture              │
├─────────────────────────────────────────────────────────────────┤
│  🎛️  Management Platform (You Operate)                        │
│  ├─ Tenant Management & Usage-Based Customer Billing         │
│  ├─ Container-per-ISP Provisioning (4min setup)              │  
│  ├─ Vendor/Reseller Partner Network                           │
│  └─ Premium Bundle Marketplace                                │
├─────────────────────────────────────────────────────────────────┤
│  📦 Per-ISP Containers (Auto-Scaled)                          │
│  ├─ 🏢 ISP Alpha: 500 customers → Competitive monthly rate   │
│  ├─ 🏢 ISP Beta: 1,500 customers → Scaled pricing            │
│  ├─ 🏢 ISP Gamma: 3,000 customers → Enterprise pricing       │
│  └─ ⚡ Auto-scaling based on customer count                   │
├─────────────────────────────────────────────────────────────────┤
│  🔧 Shared SaaS Infrastructure                                │
│  ├─ Container Management (Docker, not K8s for ISPs)          │
│  ├─ Centralized Monitoring (SignOz)                          │
│  ├─ Multi-Tenant Database Isolation                          │
│  └─ Automated Backup & Recovery                               │
└─────────────────────────────────────────────────────────────────┘
```

### 💰 **Business Model**
- **Usage-Based Pricing**: Per-customer monthly fee (competitive rates)
- **Premium Bundles**: $50-300/month (CRM, Project Management, AI Chatbot)
- **Partner Network**: Commission-based vendor/reseller program
- **Target Market**: ISPs with 50-10,000 customers

## 🚀 Quick Start

### Prerequisites (SaaS Platform Owner)
- Docker & Docker Compose (for container-per-tenant management)
- Python 3.11+ (Management Platform)
- Node.js 18+ (Partner & Admin Portals)
- PostgreSQL 15+ (Multi-tenant database)
- Redis 7+ (Shared caching layer)

### 1. SaaS Platform Setup (For You - Platform Owner)
```bash
git clone https://github.com/your-org/dotmac-saas-platform.git
cd dotmac-saas-platform

# Setup SaaS platform infrastructure
make setup-saas-platform

# Start Management Platform + Infrastructure
make start-platform
```

**Platform Owner Setup** includes:
- Management Platform API for tenant provisioning
- Container orchestration for ISP tenants
- Usage-based billing system with accurate customer tracking
- Partner portal for vendor/reseller network
- Monitoring dashboard for all ISP tenants

### 2. Alternative Setup Methods

#### For Backend Development Only
```bash
make dev-backend    # ISP + Management Platform only
```

#### For Frontend Development Only  
```bash
make dev-frontend   # Portals + minimal backend
```

#### For Lightweight Development
```bash
make dev-simple     # ISP Framework + infrastructure only
```

### 3. Verify Setup
```bash
# Check all services are healthy
make health-check

# View service URLs
make show-endpoints
```

### 🆘 If Something Goes Wrong
- Check `OPERATIONAL_RUNBOOKS.md` for troubleshooting
- Run `make restart` to restart everything
- Run `make health-check` to diagnose issues

**SaaS Platform URLs (Platform Owner):**
- **🎛️ Management API**: http://localhost:8000 (tenant provisioning, billing)
- **👨‍💼 Platform Admin**: http://localhost:3000 (manage all ISP tenants)
- **🤝 Partner Portal**: http://localhost:3002 (vendor/reseller dashboard)
- **📊 Fleet Monitoring**: http://localhost:3301 (monitor all ISP containers)

**ISP Tenant URLs (Each ISP gets their own):**
- **ISP-Alpha Container**: https://isp-alpha.dotmac.io
- **ISP-Beta Container**: https://isp-beta.dotmac.io
- **ISP-Gamma Container**: https://isp-gamma.dotmac.io

## 📁 Repository Structure

```
dotmac-platform/
├── isp-framework/                     # Core ISP Management System
│   ├── src/dotmac_isp/               # Python application code
│   ├── requirements.txt               # ISP Framework dependencies
│   ├── docker-compose.yml            # ISP-only deployment
│   └── Makefile                       # ISP Framework commands
│
├── management-platform/               # SaaS Management Platform  
│   ├── app/                          # Python application code
│   ├── requirements.txt               # Management Platform dependencies
│   ├── docker-compose.yml            # Management-only deployment
│   └── Makefile                       # Management Platform commands
│
├── frontend/                          # Shared Frontend Applications
│   ├── apps/admin/                   # Master Admin Portal
│   ├── apps/customer/                # Customer Portal
│   ├── apps/reseller/                # Reseller Portal
│   ├── apps/technician/              # Technician Mobile App
│   └── packages/headless/            # Shared frontend packages
│
├── shared/                           # Shared Resources
│   ├── deployments/                  # Kubernetes, Terraform, Helm
│   ├── docs/                         # Unified documentation
│   ├── scripts/                      # Automation scripts
│   └── backend-legacy/               # Legacy code (deprecated)
│
├── docker-compose.unified.yml         # Complete platform deployment
├── Makefile.unified                   # Unified commands
└── README.unified.md                  # This file
```

## 🎯 Platform Components

### **Management Platform** (SaaS Orchestrator)
- **Multi-Tenant Management**: Deploy and manage ISP customer instances
- **Plugin Licensing**: Tiered marketplace with usage-based billing
- **Container Orchestration**: Kubernetes-based tenant deployments
- **Reseller Network**: Channel partner management with commissions
- **Cross-Platform Monitoring**: Unified observability across all tenants

### **ISP Framework** (Per-Tenant Instance)  
- **Customer Management**: Complete customer lifecycle management
- **Billing & Invoicing**: Automated billing with payment processing
- **Network Operations**: Device monitoring, provisioning, troubleshooting
- **Support Systems**: Ticketing, knowledge base, escalation workflows
- **Portal Management**: Customer and technician self-service portals

### **Shared Infrastructure**
- **PostgreSQL**: Multi-database setup with tenant isolation
- **Redis**: Multi-instance caching and background job queues
- **OpenBao**: Unified secrets management with tenant namespaces
- **SignOz**: Complete observability stack (metrics, traces, logs)

## 💼 Business Model

### **Revenue Streams**
1. **Tenant Subscriptions**: Per-ISP monthly recurring revenue
2. **Plugin Licensing**: Tiered marketplace (Free → Basic → Premium → Enterprise)  
3. **Usage-Based Billing**: API calls, storage, transactions
4. **Reseller Network**: Channel partner revenue sharing

### **Plugin Tiers**
- **Free**: Basic customer management, simple billing
- **Basic**: Advanced billing, CRM integrations, API access  
- **Premium**: Advanced analytics, custom integrations, white-labeling
- **Enterprise**: AI insights, predictive analytics, unlimited APIs

## 🔧 Development Commands

### **Platform Management**
```bash
make up                    # Start complete platform
make down                  # Stop all services  
make status                # Show service status
make health-check          # Verify all services healthy
make restart               # Restart platform
```

### **Development Workflow**
```bash
make install-all           # Install all dependencies
make test-all              # Run all tests
make test-integration      # Cross-platform integration tests
make lint-all              # Lint both platforms
make format-all            # Format all code
```

### **Database Management**
```bash
make db-setup              # Initialize all databases
make db-migrate-all        # Run all migrations
make db-reset-all          # Reset all data (DESTRUCTIVE)
```

### **Individual Platform Commands**
```bash
# ISP Framework
make up-isp               # Start ISP Framework only
make test-isp             # Test ISP Framework
make logs-isp             # View ISP Framework logs

# Management Platform  
make up-mgmt              # Start Management Platform only
make test-mgmt            # Test Management Platform
make logs-mgmt            # View Management Platform logs
```

## 🛡️ Security Features

### **Cross-Platform Security**
- **Unified Secrets Management**: OpenBao with multi-tenant namespaces
- **Configuration Orchestration**: Synchronized secure config updates
- **Cross-Platform Audit**: Correlated audit trails across platforms
- **Disaster Recovery**: Coordinated backup and recovery procedures

### **Multi-Tenant Isolation**
- **Per-Tenant Namespaces**: Complete data and resource isolation
- **Plugin License Validation**: Secure feature gating per tenant
- **Network Segregation**: Container-level network isolation
- **Encrypted Storage**: Field-level encryption for sensitive data

## 📊 Monitoring & Observability

### **SignOz Stack** (http://localhost:3301)
- **Distributed Tracing**: Cross-platform request tracing
- **Metrics Collection**: Business and infrastructure metrics
- **Log Aggregation**: Centralized logging with correlation
- **Alert Management**: Proactive monitoring and alerting

### **Health Checks**
```bash
make health-check         # Check all service health
make monitoring           # Open SignOz dashboard
make show-endpoints       # Display all service URLs
```

## 🌍 Deployment Options

### **Development**
```bash
make dev                  # Complete development environment
```

### **Production**
- **Kubernetes**: `shared/deployments/kubernetes/`
- **Terraform**: `shared/deployments/terraform/`  
- **Helm Charts**: `shared/deployments/helm/`
- **Docker Compose**: Production-ready compose files

### **Cloud Providers**
- **AWS**: EC2, RDS, ElastiCache, ALB, Route53
- **Azure**: Virtual Machines, Azure Database, Redis Cache
- **GCP**: Compute Engine, Cloud SQL, Memorystore
- **DigitalOcean**: Droplets, Managed Databases, Load Balancers

## 🤝 Contributing

### **Development Setup**
1. Fork the repository
2. Create a feature branch
3. Make changes and add tests
4. Run `make full-check` to ensure quality
5. Submit a pull request

### **Code Standards**
- **AI-First Development**: Optimized for AI-assisted development
- **Security-First**: All features security-scanned
- **Business Outcome Focused**: Tests validate business logic
- **Cross-Platform Consistency**: Changes affecting both platforms

## 📚 Documentation

### **🎯 Start Here**
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Complete deployment guide with decision matrix
- **[OPERATIONAL_RUNBOOKS.md](OPERATIONAL_RUNBOOKS.md)** - Common scenarios and troubleshooting
- **[README.md](README.md)** - This file (overview and quick start)

### **Architecture & Design**
- `shared/docs/ARCHITECTURE.md` - Technical architecture documentation
- `shared/docs/api/` - API documentation and OpenAPI specs
- `shared/docs/guides/` - Development and deployment guides

### **Platform-Specific Docs**
- `isp-framework/README.md` - ISP Framework specific documentation
- `management-platform/README.md` - Management Platform specific documentation  
- `frontend/README.md` - Frontend development guides

### **Configuration**
- `.env.example` - Complete environment configuration template
- `.env.development` - Development-specific configuration
- `env-setup.sh` - Interactive environment setup script

## 🎯 Integration Points

### **Management Platform → ISP Framework**
```python
# Tenant orchestration
POST /api/v1/tenant-orchestration/deployments
PATCH /api/v1/tenant-orchestration/deployments/{tenant_id}
POST /api/v1/tenant-orchestration/deployments/{tenant_id}/scale

# Plugin licensing  
GET /api/v1/plugins/catalog
POST /api/v1/plugins/subscriptions
GET /api/v1/plugins/entitlements/{tenant_id}
```

### **ISP Framework → Management Platform**
```python
# Health & telemetry
POST /api/v1/monitoring/health-checks
POST /api/v1/monitoring/metrics
POST /api/v1/monitoring/alerts
POST /api/v1/plugins/usage-events
```

## 🆘 Support

### **Getting Help**
- **Documentation**: Check `shared/docs/` for comprehensive guides
- **Health Checks**: Run `make health-check` to diagnose issues
- **Logs**: Use `make logs` or `make logs-isp`/`make logs-mgmt`
- **Community**: GitHub Issues and Discussions

### **Common Issues**
```bash
# Services not starting
make down && make up

# Database connection issues  
make db-setup

# Port conflicts
docker ps  # Check for conflicting services
```

---

## 🚀 Ready for Production

This unified monorepo provides everything needed for a complete ISP management SaaS platform:

- ✅ **Production-Ready**: 240+ passing tests, comprehensive security
- ✅ **Scalable Architecture**: Multi-tenant with container orchestration  
- ✅ **Complete Observability**: Unified monitoring and alerting
- ✅ **Business-Ready**: Plugin licensing, billing, reseller network
- ✅ **Cloud-Native**: Kubernetes, Terraform, multi-cloud support

**Start building the future of ISP management today!** 🌟