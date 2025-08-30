# Complete ISP Framework Deployment Guide

## Overview

This guide shows how to deploy a **fully integrated DotMac ISP Framework** with all services including:

- ✅ **ISP Framework** (Python FastAPI)
- ✅ **FreeRADIUS Server** (Authentication/Authorization)
- ✅ **Ansible Engine** (Network Automation)
- ✅ **VOLTHA Stack** (GPON Management)
- ✅ **Complete Infrastructure** (PostgreSQL, Redis, OpenBao, SignOz)

## Architecture Overview

```
┌─────────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│   ISP Framework     │◄─►│   FreeRADIUS     │◄─►│   PostgreSQL     │
│   (FastAPI)         │   │   (Auth Server)  │   │   (Database)     │
│   Port: 8000        │   │   Ports: 1812/13 │   │   Port: 5432     │
└─────────────────────┘   └──────────────────┘   └──────────────────┘
           ▲                         ▲                         ▲
           │                         │                         │
           ▼                         ▼                         ▼
┌─────────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│   Ansible Engine   │   │   VOLTHA Stack   │   │   Redis Cache    │
│   (Automation)      │   │   (GPON Mgmt)    │   │   Port: 6379     │
│   Port: 8080        │   │   Port: 50057    │   └──────────────────┘
└─────────────────────┘   └──────────────────┘
```

## Prerequisites

### Required Software

- **Kubernetes cluster** (1.24+) with at least 16GB RAM, 8 CPU cores
- **Helm 3.10+**
- **kubectl** configured for your cluster
- **Docker** (for building custom images)

### Storage Requirements

- **Fast SSD storage class** for databases
- **Standard storage** for logs and temporary files
- **Minimum 500GB** total storage

### Network Requirements

- **LoadBalancer** or **Ingress Controller** (NGINX recommended)
- **DNS management** (CloudFlare/Route53 for automatic tenant subdomains)

## Step 1: Prepare Custom Docker Images

### Build FreeRADIUS Integrated Image

```bash
cd /home/dotmac_framework

# Build FreeRADIUS with PostgreSQL backend
docker build -f docker/Dockerfile.freeradius-integrated \
  -t registry.dotmac.com/freeradius-integrated:latest .

# Push to registry
docker push registry.dotmac.com/freeradius-integrated:latest
```

### Build Ansible Engine Image

```bash
# Build Ansible automation engine
docker build -f docker/Dockerfile.ansible-engine \
  -t registry.dotmac.com/ansible-engine:latest .

# Push to registry
docker push registry.dotmac.com/ansible-engine:latest
```

### Build Complete ISP Framework Image

```bash
# Build ISP Framework with all integrations
docker build -f docker/Dockerfile.isp-optimized \
  --target production \
  -t registry.dotmac.com/isp-framework-complete:latest .

# Push to registry
docker push registry.dotmac.com/isp-framework-complete:latest
```

## Step 2: Install Dependencies

### Add Required Helm Repositories

```bash
# PostgreSQL and Redis
helm repo add bitnami https://charts.bitnami.com/bitnami

# OpenBao (Vault alternative)
helm repo add openbao https://openbao.github.io/openbao-helm

# NGINX Ingress
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx

# Cert Manager (for TLS)
helm repo add jetstack https://charts.jetstack.io

# Update repositories
helm repo update
```

### Install Ingress Controller

```bash
helm install nginx-ingress ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.replicaCount=2 \
  --set controller.metrics.enabled=true
```

### Install Cert Manager (for TLS certificates)

```bash
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --set installCRDs=true
```

## Step 3: Configure Values

Create your custom values file:

```bash
cat > values-production.yaml << 'EOF'
# Production configuration for DotMac Complete ISP

global:
  imageRegistry: "registry.dotmac.com"
  imageTag: "latest"
  domain: "yourdomain.com"  # Change this
  storageClass: "fast-ssd"   # Change this

# Database passwords (change these!)
postgresql:
  auth:
    postgresPassword: "your-secure-postgres-password"

redis:
  auth:
    password: "your-secure-redis-password"

clickhouse:
  auth:
    password: "your-secure-clickhouse-password"

# Enable all services
ispFramework:
  enabled: true
  replicaCount: 3

freeradius:
  enabled: true
  replicaCount: 2

ansible:
  enabled: true
  replicaCount: 2

voltha:
  enabled: true

managementPlatform:
  enabled: true

# Configure ingress for your domain
ingress:
  enabled: true
  hosts:
    - host: api.yourdomain.com
      paths:
        - path: /
          service: management-platform
          port: 8000
    - host: isp.yourdomain.com
      paths:
        - path: /
          service: isp-framework
          port: 8000
    - host: voltha.yourdomain.com
      paths:
        - path: /
          service: voltha-api
          port: 55555

# Security settings
security:
  networkPolicies:
    enabled: true
  rbac:
    enabled: true

# Backup configuration
backup:
  enabled: true
  s3:
    bucket: "your-backup-bucket"
    region: "us-east-1"
EOF
```

## Step 4: Deploy the Complete Stack

### Create Namespace

```bash
kubectl create namespace dotmac-production
```

### Install the Complete ISP Framework

```bash
helm install dotmac-isp-complete \
  ./deployments/helm/dotmac-isp-complete \
  --namespace dotmac-production \
  --values values-production.yaml \
  --timeout 20m \
  --wait
```

### Monitor Deployment

```bash
# Watch all pods
kubectl get pods -n dotmac-production -w

# Check service status
kubectl get svc -n dotmac-production

# Check ingress
kubectl get ingress -n dotmac-production
```

## Step 5: Verify Integration

### Check ISP Framework Integration

```bash
# Test ISP Framework API
curl -k https://isp.yourdomain.com/health

# Check integrations status
curl -k https://isp.yourdomain.com/integrations/status
```

### Test FreeRADIUS Integration

```bash
# Get FreeRADIUS pod
RADIUS_POD=$(kubectl get pod -n dotmac-production -l app=freeradius -o jsonpath='{.items[0].metadata.name}')

# Test RADIUS authentication
kubectl exec -n dotmac-production $RADIUS_POD -- \
  radtest test test localhost 1812 testing123

# Check database integration
kubectl exec -n dotmac-production $RADIUS_POD -- \
  psql -h postgresql -U postgres -d radius -c "SELECT * FROM radcheck LIMIT 5;"
```

### Test Ansible Integration

```bash
# Test Ansible API
curl -k https://isp.yourdomain.com/ansible/health

# Test device connection (replace with your device info)
curl -X POST -k https://isp.yourdomain.com/ansible/devices/test-connection \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "test-switch",
    "device_type": "cisco_ios",
    "ip_address": "192.168.1.1",
    "username": "admin",
    "password": "password",
    "platform": "ios"
  }'
```

### Test VOLTHA Integration

```bash
# Check VOLTHA API
VOLTHA_POD=$(kubectl get pod -n dotmac-production -l app=voltha-api -o jsonpath='{.items[0].metadata.name}')

# Test VOLTHA gRPC
kubectl exec -n dotmac-production $VOLTHA_POD -- \
  grpc_health_probe -addr localhost:55555
```

## Step 6: Configure Initial Data

### Create Initial RADIUS Users

```bash
# Connect to PostgreSQL
POSTGRES_POD=$(kubectl get pod -n dotmac-production -l app.kubernetes.io/name=postgresql -o jsonpath='{.items[0].metadata.name}')

kubectl exec -it -n dotmac-production $POSTGRES_POD -- \
  psql -U postgres -d radius -c "
INSERT INTO radcheck (username, attribute, op, value, tenant_id) VALUES
  ('customer1', 'Cleartext-Password', ':=', 'password123', 'tenant-1'),
  ('customer2', 'Cleartext-Password', ':=', 'password456', 'tenant-1');
"
```

### Create Service Profiles

```bash
kubectl exec -it -n dotmac-production $POSTGRES_POD -- \
  psql -U postgres -d radius -c "
INSERT INTO dotmac_service_profiles (profile_name, tenant_id, bandwidth_up, bandwidth_down) VALUES
  ('residential-basic', 'tenant-1', 5000000, 25000000),
  ('residential-premium', 'tenant-1', 10000000, 100000000),
  ('business-standard', 'tenant-1', 25000000, 250000000);
"
```

### Load Initial Ansible Playbooks

```bash
# Copy example playbooks to Ansible pod
ANSIBLE_POD=$(kubectl get pod -n dotmac-production -l app=ansible-engine -o jsonpath='{.items[0].metadata.name}')

kubectl cp config/ansible/playbooks/ \
  dotmac-production/$ANSIBLE_POD:/etc/ansible/playbooks/
```

## Step 7: Access the Services

### Service URLs

Once deployed, access your services at:

- **Management Platform**: <https://api.yourdomain.com>
  - API Documentation: <https://api.yourdomain.com/docs>

- **ISP Framework**: <https://isp.yourdomain.com>
  - API Documentation: <https://isp.yourdomain.com/docs>

- **VOLTHA Management**: <https://voltha.yourdomain.com>
  - gRPC endpoint: voltha.yourdomain.com:443

- **SignOz Observability**: <https://observability.yourdomain.com>

### Default Credentials

- **Management Platform Admin**: <admin@dotmac.com> / (set during deployment)
- **RADIUS Test User**: test / test
- **Database**: postgres / (password from values file)

## Step 8: Monitoring and Maintenance

### Health Checks

```bash
# Check all service health
kubectl get pods -n dotmac-production -o wide

# Check resource usage
kubectl top pods -n dotmac-production

# Check logs
kubectl logs -n dotmac-production -l app=isp-framework --tail=100
kubectl logs -n dotmac-production -l app=freeradius --tail=100
kubectl logs -n dotmac-production -l app=ansible-engine --tail=100
```

### Backup Verification

```bash
# Check backup jobs
kubectl get cronjobs -n dotmac-production

# Manual backup
kubectl create job --from=cronjob/dotmac-backup manual-backup-$(date +%Y%m%d) -n dotmac-production
```

## Step 9: Tenant Provisioning

### Create New Tenant

```bash
# Use the ISP Framework API to create a new tenant
curl -X POST -k https://isp.yourdomain.com/tenants \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "acme-isp",
    "name": "ACME Internet Services",
    "tier": "premium",
    "domain": "acme-isp.com",
    "max_customers": 5000
  }'
```

### Deploy Tenant-Specific Container

```bash
# The system will automatically create:
# - Isolated namespace: dotmac-tenant-acme-isp
# - Dedicated ISP Framework instance
# - RADIUS configuration for tenant
# - DNS records: acme-isp.yourdomain.com
```

## Troubleshooting

### Common Issues

1. **Pods stuck in Pending**

   ```bash
   # Check storage class
   kubectl get storageclass

   # Check node resources
   kubectl top nodes
   ```

2. **FreeRADIUS authentication failing**

   ```bash
   # Check database connectivity
   kubectl exec -n dotmac-production $RADIUS_POD -- \
     pg_isready -h postgresql -p 5432

   # Check RADIUS logs
   kubectl logs -n dotmac-production -l app=freeradius
   ```

3. **Ansible playbooks failing**

   ```bash
   # Check network connectivity from Ansible pod
   kubectl exec -n dotmac-production $ANSIBLE_POD -- \
     ping 192.168.1.1

   # Test SSH connectivity
   kubectl exec -n dotmac-production $ANSIBLE_POD -- \
     ssh admin@192.168.1.1 -o ConnectTimeout=5
   ```

### Support

For issues with the complete ISP deployment:

1. Check the logs of all services
2. Verify network connectivity between components
3. Ensure all required secrets are created
4. Validate DNS resolution for ingress

## Conclusion

You now have a **complete, production-ready ISP Framework** with:

- ✅ **Integrated FreeRADIUS** for customer authentication
- ✅ **Ansible automation** for network device management
- ✅ **VOLTHA stack** for GPON/fiber management
- ✅ **Full observability** with SignOz monitoring
- ✅ **Multi-tenant architecture** with container isolation
- ✅ **Enterprise security** with RBAC and network policies

This deployment provides everything needed to run a modern ISP operation at scale.
