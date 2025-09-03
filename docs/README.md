# DotMac Framework Documentation

**Complete documentation navigation for the DotMac Framework**

## 🚀 Quick Start

**New to the platform?** Start here:
1. **[Main README](../README.md)** - Project overview with new operational capabilities
2. **[Production Deployment Runbook](./PRODUCTION_DEPLOYMENT_RUNBOOK.md)** - ⭐ Complete operational procedures and management
3. **[Developer Onboarding](./DEVELOPER_ONBOARDING.md)** - Development environment setup

## 📚 Core Documentation

### Operations & Management (NEW)
- **[Production Deployment Runbook](./PRODUCTION_DEPLOYMENT_RUNBOOK.md)** - ⭐ Complete operational procedures and management
- **[Security Production Checklist](./SECURITY_PRODUCTION_CHECKLIST.md)** - Security hardening and validation
- **[API Documentation](./api/README.md)** - Complete API reference and testing

### Getting Started
- **[README.md](../README.md)** - Project overview, architecture, and operational capabilities
- **[Developer Onboarding](./DEVELOPER_ONBOARDING.md)** - Complete development environment setup
- **[Comprehensive Deployment Guide](./COMPREHENSIVE_DEPLOYMENT_GUIDE.md)** - Docker/Kubernetes deployment and configuration

### Development
- **[🚀 AI-First Testing Strategy](AI_FIRST_TESTING_STRATEGY.md)** - NEW: 100% deployment readiness guarantee
- **[Developer Onboarding Guide](DEVELOPER_ONBOARDING.md)** - Complete development workflow with AI-first testing

### Status & Planning
- **[Security Production Checklist](./SECURITY_PRODUCTION_CHECKLIST.md)** - Go-live requirements and verification steps
- Documentation status and gaps: see `CHANGELOG.md` and inline doc notes

## 🔧 Technical Documentation

### API Documentation
- **[API Overview](api/README.md)** - Generated OpenAPI specifications
- **[OpenAPI Artifacts](../src/dotmac_shared/docs/api/)** - JSON/YAML and Postman collection

### Architecture
- **[Platform Architecture](./ARCHITECTURE.md)** - ISP and Management Platform overview
- **[Frontend Applications](../frontend/README.md)** - React/Next.js portal applications

## 🎯 By Role

### **New Developers**
1. [Main README](../README.md) - Understand the project
2. [Developer Onboarding](./DEVELOPER_ONBOARDING.md) - Set up your environment  
3. [AI‑First Testing Strategy](./AI_FIRST_TESTING_STRATEGY.md) - Learn the testing approach

### **DevOps/Deployment**
1. [Comprehensive Deployment Guide](./COMPREHENSIVE_DEPLOYMENT_GUIDE.md) - Deployment methods
2. [Security Production Checklist](./SECURITY_PRODUCTION_CHECKLIST.md) - Critical checks
3. [Config Documentation](../config/README.md) - Configuration management

### **API Developers**
1. [API Documentation](api/README.md) - Generated specifications
2. [OpenAPI Artifacts](../src/dotmac_shared/docs/api/) - JSON/YAML and Postman collection

### **Frontend Developers**  
1. [Frontend README](../frontend/README.md) - Portal applications overview
2. [Developer Onboarding](./DEVELOPER_ONBOARDING.md) - Development environment setup

### **Operations Teams** (NEW)
1. **[Production Deployment Runbook](./PRODUCTION_DEPLOYMENT_RUNBOOK.md)** - Complete operational procedures
2. **[Security Production Checklist](./SECURITY_PRODUCTION_CHECKLIST.md)** - Security hardening details
3. **Quick Commands**: `sudo bash deployment/scripts/deploy.sh` → `bash monitoring/setup_monitoring.sh` → `python3 scripts/apply_security_hardening.py --force`

## ✅ New Operational Capabilities

**Production Operations Now Available:**
- ✅ **Complete deployment automation** - One-command production deployment
- ✅ **Comprehensive monitoring** - Prometheus + Grafana + AlertManager stack
- ✅ **Security hardening** - Full security implementation and validation
- ✅ **Backup & disaster recovery** - Automated backup and recovery systems
- ✅ **Performance optimization** - Database, cache, and application tuning
- ✅ **API documentation** - Automated documentation generation
- ✅ **Advanced logging** - Centralized logging with audit trails
- ✅ **Development automation** - One-command development environment setup

**Quick Setup:**
```bash
# Complete operational setup sequence
sudo bash deployment/scripts/deploy.sh              # Production deployment
bash monitoring/setup_monitoring.sh                 # Monitoring stack
python3 scripts/apply_security_hardening.py --force # Security hardening
sudo bash deployment/scripts/setup_backups.sh       # Automated backups
```

**Documentation Status**: Operational procedures are fully documented with step-by-step guides.

---

**Need help?** Start with the [main README](../README.md) and [Developer Onboarding](./DEVELOPER_ONBOARDING.md).
