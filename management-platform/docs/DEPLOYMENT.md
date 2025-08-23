# DotMac Management Platform - Deployment Guide

This guide covers the complete deployment process for the DotMac Management Platform, including development setup, CI/CD pipeline, and production deployment.

## 🚀 Quick Start

```bash
# Clone and setup
git clone <repository-url>
cd dotmac_management_platform

# Setup development environment
make install-dev

# Start development services
make up

# Run quality checks
make check
```

## 📋 Prerequisites

### Required Software
- **Python 3.11+** with Poetry package manager
- **Docker & Docker Compose** for containerized services
- **Kubernetes Cluster** (local or cloud) for tenant orchestration
- **kubectl** for Kubernetes deployments and tenant management
- **OpenTofu/Terraform** for infrastructure management
- **Git** with pre-commit hooks

### Cloud Provider Access
- **AWS**: CLI configured with appropriate IAM permissions
- **Azure**: CLI authenticated with required subscriptions
- **GCP**: Service account JSON with billing API access
- **DigitalOcean**: API token with read/write access

### Required Secrets
Configure these in your CI/CD environment and production deployment:

```bash
# Security
SECURITY_JWT_SECRET_KEY=<32+ character secure key>

# Database
DATABASE_URL=postgresql://user:password@host:port/database

# Redis
REDIS_URL=redis://password@host:port/db

# OpenBao/Vault
OPENBAO_URL=https://vault.example.com
OPENBAO_TOKEN=<vault-token>

# External Services
STRIPE_SECRET_KEY=sk_live_...
SENDGRID_API_KEY=SG....
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...

# Cloud Providers
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AZURE_CLIENT_ID=...
AZURE_CLIENT_SECRET=...
GCP_SERVICE_ACCOUNT_JSON=...
DO_API_TOKEN=...
```

## 🛠️ Development Setup

### 1. Environment Setup
```bash
# Install dependencies and setup pre-commit hooks
make install-dev

# Copy environment template
cp .env.example .env
# Edit .env with your configuration

# Verify setup
make info
make status
```

### 2. Start Development Environment
```bash
# Start all services
make up

# View logs
make logs

# Check service health
make health-check
```

### 3. Development Workflow
```bash
# Format code
make format

# Run linting
make lint

# Run tests
make test

# Run security scans
make security

# Run all quality checks
make check
```

## 🔄 CI/CD Pipeline

### Pipeline Stages

#### 1. **Code Quality Pipeline**
- Format checking (Black, isort)
- Linting (flake8, mypy)
- Security scanning (Bandit, Safety)

#### 2. **Testing Pipeline**
- Unit tests (fast feedback)
- Integration tests (database integration)
- Security tests (auth, permissions)
- Performance tests (load testing)

#### 3. **Build Pipeline**
- Multi-architecture Docker builds
- Container security scanning
- SBOM generation

#### 4. **Deployment Pipeline**
- Staging deployment with smoke tests
- Production deployment with manual approval
- Health monitoring and rollback capabilities

### Triggering Deployments

#### Development Branch → Staging
```bash
git push origin develop
# Automatically triggers staging deployment
```

#### Main Branch → Production
```bash
git push origin main
# Triggers production deployment with approval gates
```

#### Manual Deployment
```bash
# Via GitHub Actions UI
# 1. Go to Actions → CI/CD Pipeline
# 2. Click "Run workflow"
# 3. Select environment and options
```

### Quality Gates
All deployments must pass:
- ✅ **80% test coverage** minimum
- ✅ **Zero critical security** vulnerabilities
- ✅ **All linting rules** pass
- ✅ **Performance benchmarks** met
- ✅ **Infrastructure validation** passes

## 🏗️ Infrastructure Deployment

### 1. Infrastructure Validation
```bash
# Validate OpenTofu configurations
make infra-validate

# Generate deployment plan
make infra-plan ENVIRONMENT=staging

# Review and apply changes
make infra-apply ENVIRONMENT=staging
```

### 2. Environment-Specific Deployment

#### Staging Environment
```bash
# Deploy to staging
cd deployment/opentofu/environments/staging
tofu init
tofu plan
tofu apply

# Verify deployment
curl -f https://staging.dotmac.platform/health
```

#### Production Environment
```bash
# Deploy to production (requires approval)
cd deployment/opentofu/environments/production
tofu init
tofu plan
tofu apply

# Verify deployment
curl -f https://app.dotmac.platform/health
```

### 3. Cost Monitoring Setup
```bash
# Configure cost monitoring
python scripts/cost_monitor.py --analyze --days 30

# Set up budget alerts
# Configure in Master Admin Portal → Cost Management
```

## 🐳 SaaS Container Deployment

### 1. Build SaaS Platform Images
```bash
# Build Management Platform image
make docker-build

# Build ISP Framework tenant image
cd ../dotmac_isp_framework
make docker-build

# Push to registry
make docker-push
```

### 2. Kubernetes SaaS Deployment
```bash
# Deploy Management Platform
kubectl apply -f deployment/kubernetes/management-platform/

# Deploy ISP Framework base resources
kubectl apply -f ../dotmac_isp_framework/k8s/

# Verify Management Platform deployment
kubectl get deployments -n dotmac-management
kubectl get pods -n dotmac-management
kubectl logs -f deployment/mgmt-platform -n dotmac-management
```

### 3. Tenant Deployment via API
```bash
# Deploy first tenant through orchestration API
curl -X POST https://mgmt.dotmac.app/api/v1/tenant-orchestration/deployments \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_name": "Production ISP",
    "resource_tier": "large",
    "license_tier": "enterprise",
    "domain_name": "prod-isp.dotmac.app",
    "cluster_name": "production"
  }'

# Verify tenant deployment
kubectl get pods -n dotmac-tenant-production-isp-001
kubectl get services -n dotmac-tenant-production-isp-001
```

### 3. Docker Compose (Development)
```bash
# Start all services
docker-compose up -d

# Scale specific services
docker-compose up -d --scale mgmt-api=3

# View service logs
docker-compose logs -f mgmt-api
```

## 📊 Monitoring & Observability

### 1. Health Monitoring
```bash
# Check platform health
make health-check

# View system metrics
make metrics

# Generate health report
curl https://app.dotmac.platform/api/v1/master-admin/health/platform
```

### 2. SignOz Observability
- **Metrics Dashboard**: http://localhost:3301
- **Distributed Tracing**: Automatic instrumentation
- **Log Aggregation**: Structured JSON logs
- **Custom Dashboards**: Platform-specific views

### 3. Cost Monitoring
```bash
# Run cost analysis
make cost-analysis

# View cost dashboard
# Master Admin Portal → Analytics → Cost Management

# Set up budget alerts
# Configure thresholds and notification channels
```

## 🔒 Security Deployment

### 1. Secret Management
```bash
# Configure OpenBao
# 1. Initialize vault cluster
# 2. Configure authentication methods
# 3. Set up secret engines
# 4. Define access policies

# Rotate secrets
# Automated via OpenBao TTL and renewal
```

### 2. Security Scanning
```bash
# Run comprehensive security scan
make security

# Container security scan
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image dotmac/management-platform:latest

# Infrastructure security scan
cd deployment/opentofu && tfsec .
```

### 3. Compliance Validation
```bash
# Validate configuration security
python scripts/security_check.py

# Check pre-commit hooks
make pre-commit

# Audit access logs
# Review OpenBao audit logs
# Review application audit logs
```

## 🚨 Troubleshooting

### Common Issues

#### 1. **Database Connection Failures**
```bash
# Check database status
make db-shell

# Reset database (development only)
make db-reset

# Check migrations
make db-migrate
```

#### 2. **Redis Connection Issues**
```bash
# Check Redis status
docker-compose exec redis redis-cli ping

# Clear Redis cache
docker-compose exec redis redis-cli flushall
```

#### 3. **Container Build Failures**
```bash
# Clean Docker environment
make clean

# Rebuild images
make docker-build

# Check Docker logs
docker-compose logs mgmt-api
```

#### 4. **Test Failures**
```bash
# Run specific test category
make test-unit
make test-integration

# Debug test environment
make test-fast -v

# Check test coverage
open htmlcov/index.html
```

### Performance Issues

#### 1. **Slow API Responses**
```bash
# Check resource utilization
make metrics

# Profile slow endpoints
# Use SignOz tracing dashboard

# Scale API instances
docker-compose up -d --scale mgmt-api=3
```

#### 2. **High Memory Usage**
```bash
# Check memory usage
docker stats

# Analyze memory leaks
python -m pytest tests/ -m "memory"

# Optimize database queries
# Review slow query logs
```

## 📈 Scaling

### Horizontal Scaling
```bash
# Scale API instances
kubectl scale deployment mgmt-platform --replicas=5

# Scale Celery workers
kubectl scale deployment mgmt-worker --replicas=10

# Configure auto-scaling
kubectl apply -f deployment/kubernetes/autoscaling/
```

### Vertical Scaling
```bash
# Update resource limits
kubectl patch deployment mgmt-platform -p '{"spec":{"template":{"spec":{"containers":[{"name":"mgmt-platform","resources":{"limits":{"memory":"2Gi","cpu":"1000m"}}}]}}}}'

# Monitor resource usage
kubectl top pods
kubectl top nodes
```

## 🔄 Backup & Recovery

### Database Backup
```bash
# Create backup
make backup-dev

# Restore from backup
make restore-dev

# Production backup (automated)
# Configured via cloud provider backup services
```

### Disaster Recovery
```bash
# Test disaster recovery
# 1. Simulate infrastructure failure
# 2. Restore from backups
# 3. Verify data integrity
# 4. Update DNS/load balancers
```

## 📚 Additional Resources

- [Architecture Documentation](./ARCHITECTURE.md)
- [Security Guide](./SECURITY.md)
- [API Documentation](./API.md)
- [Troubleshooting Guide](./TROUBLESHOOTING.md)
- [Cost Optimization Guide](./COST_OPTIMIZATION.md)

## 🆘 Support

For deployment issues:
1. Check the troubleshooting section above
2. Review GitHub Actions logs
3. Check service health endpoints
4. Contact the platform team via Slack #dotmac-support