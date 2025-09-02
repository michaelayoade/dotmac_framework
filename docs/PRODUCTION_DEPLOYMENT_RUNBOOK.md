# Production Deployment Runbook

## Overview

This runbook provides step-by-step instructions for deploying the DotMac Framework to production environments. It covers both Kubernetes and Docker/Coolify deployment scenarios with comprehensive security, monitoring, and operational procedures.

## Pre-Deployment Checklist

### ✅ Infrastructure Requirements

**Minimum Production Requirements:**
- **Kubernetes**: v1.25+ with 8 CPU cores, 16GB RAM, 100GB SSD per node (3 nodes minimum)
- **Docker/Coolify**: 4 CPU cores, 8GB RAM, 50GB SSD per instance
- **PostgreSQL**: v15+ with connection pooling (PgBouncer recommended)
- **Redis**: v7+ with persistence enabled
- **Load Balancer**: NGINX Ingress Controller or equivalent

**Security Requirements:**
- TLS certificates from trusted CA (Let's Encrypt or commercial)
- OpenBao/Vault instance with TLS enabled and unsealed
- Network isolation between services
- Firewall rules limiting external access

### ✅ Environment Configuration

**Required Environment Variables:**
```bash
# Core Application
export ENVIRONMENT=production
export SECRET_KEY=<32-character-minimum-secure-key>
export DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
export REDIS_URL=redis://host:6379/0

# OpenBao Configuration
export OPENBAO_ADDR=https://openbao.dotmac.com:8200
export OPENBAO_API_ADDR=https://openbao.dotmac.com:8200
export OPENBAO_CLUSTER_ADDR=https://openbao:8201

# Monitoring
export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://signoz:4317
export OTEL_EXPORTER_OTLP_METRICS_ENDPOINT=http://signoz:4318
export OTEL_SERVICE_NAME=dotmac-framework

# Business Configuration
export CORS_ORIGINS=https://admin.dotmac.com,https://customer.dotmac.com
export ADMIN_EMAIL=admin@dotmac.com
```

## Deployment Methods

### Method 1: Kubernetes Deployment (Recommended for Scale)

#### Step 1: Prepare Kubernetes Environment

```bash
# 1. Verify cluster access
kubectl cluster-info
kubectl get nodes

# 2. Create production namespace
kubectl create namespace dotmac-prod

# 3. Install required operators
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo add cert-manager https://charts.jetstack.io
helm repo update

helm install ingress-nginx ingress-nginx/ingress-nginx --namespace ingress-nginx --create-namespace
helm install cert-manager cert-manager/cert-manager --namespace cert-manager --create-namespace --set installCRDs=true
```

#### Step 2: Deploy OpenBao (Secrets Management)

```bash
# 1. Generate TLS certificates
./scripts/generate-openbao-tls.sh /tmp/openbao-certs

# 2. Create OpenBao secrets
kubectl create secret tls openbao-tls \
  --cert=/tmp/openbao-certs/server.crt \
  --key=/tmp/openbao-certs/server-key.pem \
  --namespace=dotmac-prod

# 3. Deploy OpenBao
kubectl apply -f k8s/base/openbao-deployment.yaml -n dotmac-prod

# 4. Initialize and unseal OpenBao
kubectl exec -it openbao-0 -n dotmac-prod -- bao operator init
kubectl exec -it openbao-0 -n dotmac-prod -- bao operator unseal <unseal-key-1>
kubectl exec -it openbao-0 -n dotmac-prod -- bao operator unseal <unseal-key-2>
kubectl exec -it openbao-0 -n dotmac-prod -- bao operator unseal <unseal-key-3>

# 5. Configure authentication
kubectl exec -it openbao-0 -n dotmac-prod -- bao auth enable kubernetes
# Follow OpenBao setup procedures from topology guide
```

#### Step 3: Deploy Database and Infrastructure

```bash
# 1. Deploy PostgreSQL with backup configuration
helm install postgresql bitnami/postgresql \
  --namespace dotmac-prod \
  --set auth.postgresPassword=<secure-password> \
  --set auth.database=dotmac_production \
  --set primary.persistence.size=100Gi \
  --set primary.resources.requests.memory=4Gi \
  --set metrics.enabled=true

# 2. Deploy Redis with persistence
helm install redis bitnami/redis \
  --namespace dotmac-prod \
  --set auth.password=<secure-password> \
  --set master.persistence.size=20Gi \
  --set replica.persistence.size=20Gi

# 3. Deploy SigNoz for observability
helm install signoz signoz/signoz \
  --namespace observability --create-namespace \
  --set frontend.ingress.enabled=true \
  --set frontend.ingress.hosts[0].host=monitoring.dotmac.com
```

#### Step 4: Deploy DotMac Framework

```bash
# 1. Update production configuration
kubectl apply -f k8s/overlays/production/

# 2. Verify deployment
kubectl get pods -n dotmac-prod
kubectl get ingress -n dotmac-prod
kubectl logs -f deployment/dotmac-platform -n dotmac-prod

# 3. Run health checks
curl -k https://api.dotmac.com/health
curl -k https://admin.dotmac.com/health
```

### Method 2: Docker/Coolify Deployment (Recommended for Simplicity)

#### Step 1: Coolify Instance Setup

```bash
# 1. Access Coolify dashboard at http://your-server:8000
# 2. Complete initial setup and create admin account
# 3. Add server resources and configure domains

# 4. Create project: "DotMac Production"
# 5. Configure environment variables in Coolify UI
```

#### Step 2: Database Services

```bash
# 1. Add PostgreSQL service
# - Service Type: PostgreSQL 15
# - Database: dotmac_production
# - Username: dotmac_prod
# - Password: <secure-32-char-password>
# - Resources: 2 CPU, 4GB RAM, 50GB Storage

# 2. Add Redis service  
# - Service Type: Redis 7
# - Password: <secure-32-char-password>
# - Resources: 1 CPU, 2GB RAM, 10GB Storage
```

#### Step 3: OpenBao Deployment

```bash
# 1. Generate certificates
./scripts/generate-openbao-tls.sh /data/openbao-tls

# 2. Create OpenBao service in Coolify
# - Service Type: Docker Compose
# - Repository: Upload docker-compose.openbao.yml
# - Environment: OPENBAO_CONFIG_PATH=/openbao/config/openbao-production.hcl

# 3. Initialize and configure as per Kubernetes instructions
```

#### Step 4: DotMac Framework Deployment

```bash
# 1. Add DotMac service
# - Service Type: Docker Deploy
# - Image: ghcr.io/dotmac/dotmac-framework:stable
# - Configuration: docker-compose.coolify.yml

# 2. Configure domains
# - admin.dotmac.com → dotmac-management:8001
# - customer.dotmac.com → dotmac-isp:8000  
# - api.dotmac.com → dotmac-platform:8000

# 3. Enable SSL certificates (Let's Encrypt)
# 4. Configure health checks and monitoring
```

## Post-Deployment Verification

### Health and Connectivity Checks

```bash
# 1. Service health checks
curl -f https://api.dotmac.com/health || echo "API health check failed"
curl -f https://admin.dotmac.com/health || echo "Admin health check failed" 
curl -f https://customer.dotmac.com/health || echo "Customer health check failed"

# 2. Database connectivity
kubectl exec -it deployment/dotmac-platform -n dotmac-prod -- \
  python -c "from dotmac_shared.database.base import AsyncDatabase; print('DB OK')"

# 3. OpenBao connectivity
curl -k https://openbao.dotmac.com:8200/v1/sys/health

# 4. Monitoring stack
curl -f https://monitoring.dotmac.com || echo "SigNoz unavailable"
```

### Smoke Tests

```bash
# 1. User authentication flow
curl -X POST https://api.dotmac.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"test"}'

# 2. Partner creation
curl -X POST https://api.dotmac.com/api/v1/partners \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Partner","tier":"standard"}'

# 3. Customer provisioning
curl -X POST https://api.dotmac.com/api/v1/customers \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Customer","email":"test@example.com"}'
```

### Monitoring and Alerting Verification

```bash
# 1. Verify metrics are flowing
curl -s https://monitoring.dotmac.com/api/v1/query?query=up | jq .

# 2. Test critical alerts
# Trigger test alert and verify notification delivery
curl -X POST https://api.dotmac.com/api/v1/test/alerts/critical

# 3. Check dashboard accessibility
open https://monitoring.dotmac.com
```

## Security Hardening

### TLS and Certificate Management

```bash
# 1. Verify TLS configuration
openssl s_client -connect admin.dotmac.com:443 -servername admin.dotmac.com
openssl s_client -connect api.dotmac.com:443 -servername api.dotmac.com

# 2. Check certificate expiration
curl -vI https://admin.dotmac.com 2>&1 | grep -A2 -B2 expire

# 3. Verify HSTS headers
curl -I https://api.dotmac.com | grep -i strict-transport-security
```

### Security Audit

```bash
# 1. Remove bootstrap credentials (CRITICAL)
curl -X POST https://api.dotmac.com/admin/remove-bootstrap-credentials \
  -H "Authorization: Bearer <admin-token>"

# 2. Verify no hardcoded secrets
grep -r "password\|secret\|key" k8s/ | grep -v "example\|template\|CHANGE_ME"

# 3. Check file permissions
find /app -name "*.key" -exec ls -la {} \;
find /app -name "*.crt" -exec ls -la {} \;

# 4. Validate network policies
kubectl get networkpolicies -n dotmac-prod
kubectl describe networkpolicy dotmac-platform-network-policy -n dotmac-prod
```

## Operations and Maintenance

### Database Migrations

```bash
# 1. Pre-migration backup
kubectl exec -it postgresql-0 -n dotmac-prod -- \
  pg_dump -U postgres dotmac_production > backup-$(date +%Y%m%d).sql

# 2. Run migrations
kubectl apply -f k8s/base/db-migrate-job.yaml -n dotmac-prod
kubectl logs -f job/db-migrate -n dotmac-prod

# 3. Verify migration success
kubectl exec -it deployment/dotmac-platform -n dotmac-prod -- \
  alembic current -v
```

### Scaling and Performance

```bash
# 1. Monitor HPA status
kubectl get hpa -n dotmac-prod
kubectl describe hpa dotmac-platform-hpa -n dotmac-prod

# 2. Manual scaling (if needed)
kubectl scale deployment dotmac-platform --replicas=5 -n dotmac-prod

# 3. Resource monitoring
kubectl top pods -n dotmac-prod
kubectl top nodes
```

### Backup and Disaster Recovery

```bash
# 1. Database backup
kubectl create job --from=cronjob/postgresql-backup backup-$(date +%Y%m%d) -n dotmac-prod

# 2. OpenBao snapshot
kubectl exec -it openbao-0 -n dotmac-prod -- \
  bao operator raft snapshot save /backups/openbao-$(date +%Y%m%d).snap

# 3. Configuration backup
kubectl get all,configmap,secret -n dotmac-prod -o yaml > \
  dotmac-prod-config-$(date +%Y%m%d).yaml
```

## Troubleshooting

### Common Issues

**1. Pod CrashLoopBackOff**
```bash
kubectl logs -f deployment/dotmac-platform -n dotmac-prod --previous
kubectl describe pod <pod-name> -n dotmac-prod
```

**2. Database Connection Issues**
```bash
kubectl exec -it postgresql-0 -n dotmac-prod -- psql -U postgres -c "\l"
kubectl exec -it deployment/dotmac-platform -n dotmac-prod -- \
  python -c "import asyncpg; print('PostgreSQL accessible')"
```

**3. OpenBao Sealed**
```bash
kubectl exec -it openbao-0 -n dotmac-prod -- bao status
kubectl exec -it openbao-0 -n dotmac-prod -- bao operator unseal <key>
```

**4. Ingress/SSL Issues**
```bash
kubectl get ingress -n dotmac-prod
kubectl describe ingress dotmac-platform-ingress -n dotmac-prod
kubectl logs -f deployment/ingress-nginx-controller -n ingress-nginx
```

### Performance Issues

**1. High Latency**
```bash
# Check database query performance
kubectl exec -it postgresql-0 -n dotmac-prod -- \
  psql -U postgres -c "SELECT query, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"

# Monitor application metrics
curl -s https://monitoring.dotmac.com/api/v1/query?query=http_request_duration_ms_bucket
```

**2. Memory Issues**
```bash
# Check memory usage
kubectl top pods -n dotmac-prod --containers

# Adjust resource limits if needed
kubectl patch deployment dotmac-platform -n dotmac-prod -p \
  '{"spec":{"template":{"spec":{"containers":[{"name":"dotmac-platform","resources":{"limits":{"memory":"2Gi"}}}]}}}}'
```

## Rollback Procedures

### Application Rollback

```bash
# 1. Check rollout history
kubectl rollout history deployment/dotmac-platform -n dotmac-prod

# 2. Rollback to previous version
kubectl rollout undo deployment/dotmac-platform -n dotmac-prod

# 3. Rollback to specific revision
kubectl rollout undo deployment/dotmac-platform --to-revision=2 -n dotmac-prod

# 4. Monitor rollback
kubectl rollout status deployment/dotmac-platform -n dotmac-prod
```

### Database Rollback

```bash
# 1. Stop application
kubectl scale deployment dotmac-platform --replicas=0 -n dotmac-prod

# 2. Restore database backup
kubectl exec -i postgresql-0 -n dotmac-prod -- \
  psql -U postgres -d dotmac_production < backup-20241201.sql

# 3. Run migration rollback if needed
kubectl exec -it deployment/dotmac-platform -n dotmac-prod -- \
  alembic downgrade <revision>

# 4. Restart application
kubectl scale deployment dotmac-platform --replicas=3 -n dotmac-prod
```

## Contacts and Escalation

**Technical Support:**
- Platform Engineering: platform-eng@dotmac.com
- Database Issues: dba@dotmac.com  
- Security Issues: security@dotmac.com

**Emergency Contacts:**
- On-Call Engineer: +1-555-ONCALL
- Platform Lead: platform-lead@dotmac.com
- Security Lead: security-lead@dotmac.com

**Escalation Matrix:**
1. **P1 - Critical**: Service down, security breach, data loss
   - Response: 15 minutes
   - Resolution: 2 hours
   
2. **P2 - High**: Performance degradation, partial service disruption  
   - Response: 30 minutes
   - Resolution: 4 hours
   
3. **P3 - Medium**: Feature issues, minor bugs
   - Response: 2 hours
   - Resolution: 1 business day

This runbook should be updated regularly and validated through disaster recovery exercises.