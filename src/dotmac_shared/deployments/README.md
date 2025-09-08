# DotMac Framework - Production Deployment

This directory contains production-ready deployment configurations for the DotMac ISP Framework.

## Deployment Options

### 1. Docker Compose (Simple Single-Server)

```bash
cd docker-compose
cp .env.example .env
# Edit .env with your configuration
docker-compose -f production.yml up -d
```

### 2. Kubernetes (Multi-Server)

```bash
cd kubernetes
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f postgres.yaml
kubectl apply -f dotmac-core-events.yaml
# Apply other services...
```

### 3. Helm Charts (Recommended)

```bash
cd helm
helm install dotmac-framework ./dotmac-framework \
  --namespace dotmac-production \
  --create-namespace \
  --values values-production.yaml
```

### 4. Terraform + AWS (Full Infrastructure)

```bash
cd terraform
terraform init
terraform plan -var-file="production.tfvars"
terraform apply -var-file="production.tfvars"
```

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │    │   API Gateway   │    │   Customer      │
│     (Nginx)     │────│   (FastAPI)     │────│   Portal        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐              │
         │              │   Reseller      │              │
         └──────────────│   Portal        │──────────────┘
                        └─────────────────┘
                                 │
    ┌─────────────────────────────────────────────────────────────┐
    │                    Core Planes                              │
    ├─────────────────┬─────────────────┬─────────────────────────┤
    │ dotmac_identity │ dotmac_billing  │ dotmac_networking       │
    │ dotmac_services │ dotmac_analytics│ dotmac_core_events      │
    └─────────────────┴─────────────────┴─────────────────────────┘
                                 │
    ┌─────────────────────────────────────────────────────────────┐
    │                 Microservices                               │
    ├─────────────────┬─────────────────┬─────────────────────────┤
    │ Communications  │ CRM             │ Inventory Management    │
    │ Support Desk    │ Field Ops       │ Data Import/Export      │
    └─────────────────┴─────────────────┴─────────────────────────┘
                                 │
    ┌─────────────────────────────────────────────────────────────┐
    │                Infrastructure                               │
    ├─────────────────┬─────────────────┬─────────────────────────┤
    │ PostgreSQL      │ Redis           │ RabbitMQ                │
    │ Elasticsearch   │ SigNoz          │ ClickHouse             │
    └─────────────────┴─────────────────┴─────────────────────────┘
```

## Service Dependencies

### Core Planes (Start First)

1. **dotmac_core_events** - Event bus (all services depend on this)
2. **dotmac_core_ops** - Operations plane
3. **dotmac_identity** - Customer/user management
4. **dotmac_billing** - Billing and payments
5. **dotmac_services** - Service catalog and provisioning
6. **dotmac_networking** - Network management
7. **dotmac_analytics** - Analytics and reporting

### Application Layer

8. **dotmac_api_gateway** - API gateway and routing
9. **communications** - Email, SMS, WhatsApp
10. **crm** - Customer relationship management
11. **inventory_management** - Equipment tracking
12. **customer_portal** - Self-service portal
13. **reseller_portal** - Partner portal
14. **support_desk** - Unified support inbox
15. **field_ops** - Technician dispatch
16. **data_import_export** - CSV/Excel import/export

## Production Configuration

### Environment Variables

```bash
# Database
POSTGRES_USER=dotmac_prod
POSTGRES_PASSWORD=secure_password_here
DATABASE_URL=postgresql://user:pass@postgres:5432/dotmac_core

# Redis
REDIS_PASSWORD=redis_secure_password
REDIS_URL=redis://:password@redis:6379/0

# Message Queue
RABBITMQ_USER=dotmac_mq
RABBITMQ_PASSWORD=mq_secure_password

# External Services
STRIPE_SECRET_KEY=sk_live_...
SMTP2GO_API_KEY=api-...
TWILIO_SID=AC...
TWILIO_TOKEN=...

# Security
JWT_SECRET=your_jwt_secret_here
ENCRYPTION_KEY=your_32_char_encryption_key

# Monitoring
GRAFANA_PASSWORD=admin_password_here
```

### Scaling Guidelines

#### Minimum Production Setup

- **Core Planes**: 2 replicas each
- **API Gateway**: 3 replicas
- **Portals**: 2 replicas each
- **Microservices**: 1-2 replicas each

#### High Availability Setup

- **Core Planes**: 3 replicas each
- **API Gateway**: 5 replicas
- **Portals**: 3 replicas each
- **Microservices**: 2-3 replicas each

#### Resource Requirements

```yaml
Small ISP (< 1K customers):
  CPU: 16 cores
  RAM: 32GB
  Storage: 500GB SSD

Medium ISP (1K-10K customers):
  CPU: 32 cores
  RAM: 64GB
  Storage: 1TB SSD

Large ISP (10K+ customers):
  CPU: 64+ cores
  RAM: 128GB+
  Storage: 2TB+ SSD
```

## Monitoring & Observability

### Grafana Dashboards

- **System Overview**: CPU, memory, disk usage
- **Application Metrics**: Request rates, response times
- **Business Metrics**: Customer onboarding, revenue
- **Network Metrics**: Device status, bandwidth usage

### Alerts

- High error rates (>5%)
- High response times (>2s)
- Database connection issues
- Service discovery failures
- Critical business events

### Log Aggregation

- **ELK Stack**: Elasticsearch, Logstash, Kibana
- **Structured Logging**: JSON format with correlation IDs
- **Log Retention**: 30 days for debug, 1 year for audit

## Backup Strategy

### Database Backups

- **Daily**: Full PostgreSQL backup to S3
- **Hourly**: Transaction log shipping
- **Retention**: 30 days rolling

### Application Data

- **Configuration**: Stored in Git
- **Secrets**: Encrypted and versioned
- **User Uploads**: Replicated to S3

### Disaster Recovery

- **RTO**: 4 hours (Recovery Time Objective)
- **RPO**: 1 hour (Recovery Point Objective)
- **Multi-AZ**: Database and cache clusters
- **Cross-Region**: Backup replication

## Security Hardening

### Network Security

- **Private Subnets**: All services except load balancer
- **Security Groups**: Least privilege access
- **WAF**: Web Application Firewall enabled
- **DDoS Protection**: CloudFlare or AWS Shield

### Application Security

- **TLS 1.3**: All communications encrypted
- **JWT Tokens**: Short-lived with refresh
- **Rate Limiting**: Per-user and per-service
- **Input Validation**: All API endpoints

### Data Security

- **Encryption at Rest**: Database and file storage
- **Encryption in Transit**: All network traffic
- **PII Protection**: Sensitive data redaction
- **Audit Logging**: All access logged

## Deployment Commands

### Initial Setup

```bash
# 1. Create infrastructure (Terraform)
cd terraform
terraform apply -var-file="production.tfvars"

# 2. Install DotMac Framework (Helm)
helm repo add dotmac https://charts.dotmac.com
helm install dotmac-framework dotmac/dotmac-framework \
  --namespace dotmac-production \
  --create-namespace \
  --values values-production.yaml

# 3. Configure monitoring
kubectl apply -f monitoring/

# 4. Set up backup jobs
kubectl apply -f backup/
```

### Updates

```bash
# Rolling update (zero downtime)
helm upgrade dotmac-framework dotmac/dotmac-framework \
  --namespace dotmac-production \
  --values values-production.yaml

# Force restart specific service
kubectl rollout restart deployment/dotmac-identity \
  -n dotmac-production
```

### Health Checks

```bash
# Check all services
kubectl get pods -n dotmac-production

# Check service health
curl https://api.yourdomain.com/health

# Check database connectivity
kubectl exec -it postgres-0 -n dotmac-production -- \
  psql -U dotmac -d dotmac_core -c "SELECT 1;"
```

## Troubleshooting

### Common Issues

#### Service Won't Start

```bash
# Check logs
kubectl logs -f deployment/service-name -n dotmac-production

# Check events
kubectl describe pod pod-name -n dotmac-production

# Check configuration
kubectl get configmap dotmac-config -o yaml -n dotmac-production
```

#### Database Connection Issues

```bash
# Test connectivity
kubectl run -it --rm debug --image=postgres:15 --restart=Never -- \
  psql postgresql://user:pass@postgres-service:5432/dotmac_core

# Check database status
kubectl get statefulset postgres -n dotmac-production
```

#### Performance Issues

```bash
# Check resource usage
kubectl top pods -n dotmac-production

# Check HPA status
kubectl get hpa -n dotmac-production

# Scale manually if needed
kubectl scale deployment service-name --replicas=5 -n dotmac-production
```

## Support

- **Documentation**: <https://docs.dotmac.com>
- **Issues**: <https://github.com/dotmac/framework/issues>
- **Support**: <support@dotmac.com>
- **Community**: <https://community.dotmac.com>
