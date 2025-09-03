# 🎓 DotMac Platform Comprehensive Training Guide

Complete training materials and onboarding guide for development and operations teams.

## 📋 Table of Contents

- [New Team Member Onboarding](#new-team-member-onboarding)
- [Development Team Training](#development-team-training)
- [Operations Team Training](#operations-team-training)
- [Security Team Training](#security-team-training)
- [Customer Support Training](#customer-support-training)
- [Management Training](#management-training)
- [Certification Programs](#certification-programs)

## 👋 New Team Member Onboarding

### Week 1: Platform Overview

**Day 1: Welcome & Setup**
```bash
# Development environment setup
git clone https://github.com/dotmac/platform.git
cd dotmac-platform

# Install dependencies
make install-dev

# Run local development environment
make dev

# Verify setup
curl http://localhost:8000/health
```

**Learning Objectives:**
- [ ] Understand DotMac business model and value proposition
- [ ] Set up local development environment
- [ ] Navigate platform architecture documentation
- [ ] Complete security and compliance training
- [ ] Meet team members and understand roles

**Day 2-3: Platform Architecture**

**Required Reading:**
- [Platform Architecture Overview](ARCHITECTURE.md)
- [API Documentation](https://docs.dotmac.platform/api/)
- [Security Production Checklist](SECURITY_PRODUCTION_CHECKLIST.md)

**Hands-On Exercises:**
1. **API Exploration:**
```bash
# Test main API endpoints
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/customers
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/services
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/tickets

# Explore OpenAPI documentation
open http://localhost:8000/docs
```

2. **Database Exploration:**
```sql
-- Connect to development database
psql -h localhost -U dotmac_dev -d dotmac_dev

-- Explore key tables
\dt
SELECT * FROM customers LIMIT 5;
SELECT * FROM services LIMIT 5;
SELECT * FROM invoices LIMIT 5;
```

**Day 4-5: Core Workflows**

**Customer Lifecycle Demo:**
```python
# Create a test customer journey
import requests

base_url = "http://localhost:8000/api/v1"
headers = {"Authorization": f"Bearer {token}"}

# 1. Create customer
customer_data = {
    "first_name": "John",
    "last_name": "Doe", 
    "email": "john.doe@example.com",
    "phone": "+1234567890"
}
customer = requests.post(f"{base_url}/customers", json=customer_data, headers=headers)

# 2. Add service
service_data = {
    "customer_id": customer.json()["id"],
    "name": "Residential Internet",
    "type": "internet",
    "monthly_rate": 79.99
}
service = requests.post(f"{base_url}/services", json=service_data, headers=headers)

# 3. Generate invoice
invoice = requests.post(f"{base_url}/invoices/generate/{customer.json()['id']}", headers=headers)

print(f"Customer journey completed: {customer.json()['id']}")
```

### Week 2: Role-Specific Deep Dive

**Choose your track:**
- [Development Track](#development-team-training)
- [Operations Track](#operations-team-training)
- [Security Track](#security-team-training)
- [Support Track](#customer-support-training)

## 💻 Development Team Training

### Module 1: Codebase Architecture (Week 1)

**Learning Objectives:**
- [ ] Understand monolithic vs microservices architecture
- [ ] Master FastAPI and SQLAlchemy patterns
- [ ] Learn DRY principles and shared components
- [ ] Understand multi-tenancy implementation

**Key Concepts:**
```python
# DRY Pattern Example - RouterFactory Usage
from dotmac_shared.api.router_factory import RouterFactory
from dotmac_shared.decorators import standard_exception_handler

class CustomerRouterFactory(RouterFactory):
    @standard_exception_handler
    async def create_customer_router(self, service: CustomerService):
        """Creates customer management router following DRY patterns"""
        router = APIRouter(prefix="/customers", tags=["Customer Management"])
        
        @router.post("/", response_model=CustomerResponse)
        async def create_customer(data: CustomerCreate):
            return await service.create_customer(data)
            
        return router
```

**Hands-On Lab 1: Building a New Feature**
```bash
# Task: Add a new "Service Plans" feature
mkdir -p src/dotmac_shared/service_plans
touch src/dotmac_shared/service_plans/{models.py,schemas.py,repository.py,service.py,router.py}

# Follow DRY patterns from existing modules
# Use @standard_exception_handler decorator
# Implement RouterFactory pattern
# Add comprehensive tests
```

### Module 2: AI-First Testing & Quality Assurance (Week 2)

**🚀 AI-First Testing Philosophy:**
The DotMac platform uses an innovative **AI-First Testing Strategy** that solves the "tests pass but app breaks" problem.

**Core Principle**: *When deployment-ready tests pass → App is 100% guaranteed to work in production*

**Testing Layers:**
1. **Critical Startup Validation**: Real imports, database connectivity, route registration
2. **Database Schema Integrity**: SQLAlchemy models match Alembic migrations exactly
3. **AI-Guided Comprehensive Validation**: System-level interactions with AI property testing
4. **Legacy Test Suite**: Traditional unit/integration tests (only runs if layers 1-3 pass)

**Required Reading**: [AI-First Testing Strategy](AI_FIRST_TESTING_STRATEGY.md)

**Example Test Structure:**
```python
# tests/unit/test_customer_service.py
import pytest
from hypothesis import given, strategies as st
from dotmac_shared.customer.service import CustomerService
from dotmac_shared.customer.schemas import CustomerCreate

class TestCustomerService:
    
    @pytest.fixture
    async def service(self):
        return CustomerService(mock_repository)
    
    @given(st.text(min_size=1, max_size=100))
    async def test_create_customer_with_valid_name(self, service, name):
        """Property-based test for customer creation"""
        data = CustomerCreate(first_name=name, last_name="Test", email="test@example.com")
        customer = await service.create_customer(data)
        assert customer.first_name == name
    
    async def test_customer_lifecycle_integration(self, service):
        """Integration test for complete customer lifecycle"""
        # Create -> Update -> Add Service -> Generate Invoice -> Delete
        pass
```

**Lab 2: AI-First Testing Workflow**
```bash
# NEW WORKFLOW - 100% Reliable Development
# 1. Test deployment readiness FIRST (before writing any code)
make -f Makefile.readiness deployment-ready

# 2. Only if deployment-ready passes, develop feature
vim src/dotmac_shared/billing/new_calculations.py

# 3. Test deployment readiness again
make -f Makefile.readiness deployment-ready
# ❌ If this fails → Fix startup/schema issues before unit tests

# 4. Write traditional tests (only after readiness passes)
vim tests/unit/test_billing_calculations.py

# 5. Run AI-guided property testing
pytest tests/ai_readiness/ -v

# 6. Run full validation
make -f Makefile.readiness dev-ready
```

**Key Commands:**
- `deployment-ready`: Full validation before any deployment
- `startup-check`: Quick development validation
- `schema-check`: After database model changes
- `ai-validation`: AI-guided comprehensive testing

### Module 3: Database & Performance (Week 3)

**Database Best Practices:**
```python
# Efficient querying with SQLAlchemy
from sqlalchemy.orm import selectinload, joinedload

# Good: Eager loading to avoid N+1 queries
customers = await session.execute(
    select(Customer)
    .options(selectinload(Customer.services))
    .where(Customer.status == "active")
)

# Bad: Lazy loading causes N+1 problem
customers = await session.execute(select(Customer))
for customer in customers:
    print(len(customer.services))  # Triggers individual queries
```

**Performance Monitoring:**
```python
from dotmac_shared.monitoring import performance_monitor

@performance_monitor("customer_creation")
async def create_customer(data: CustomerCreate):
    """Monitored function with automatic metrics collection"""
    # Implementation tracks response time, success rate, etc.
    pass
```

### Module 4: Security & Authentication (Week 4)

**Security Implementation:**
```python
from dotmac_shared.auth.dependencies import require_permission
from dotmac_shared.security.validation import sanitize_input

@router.get("/customers/{customer_id}")
@require_permission("customer:read") 
async def get_customer(
    customer_id: UUID,
    current_user: User = Depends(get_current_user)
):
    # Automatic tenant isolation and permission checking
    customer_id = sanitize_input(customer_id, "uuid")
    return await service.get_customer(customer_id, current_user.tenant_id)
```

## 🛠️ Operations Team Training

### Module 1: Infrastructure Management (Week 1)

**Container Orchestration:**
```yaml
# Example Kubernetes deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dotmac-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: dotmac-api
  template:
    spec:
      containers:
      - name: api
        image: dotmac/platform:latest
        ports:
        - containerPort: 8000
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready  
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

**Lab 1: Kubernetes Deployment**
```bash
# Deploy to staging environment
kubectl apply -f k8s/staging/
kubectl get pods -n dotmac-staging
kubectl logs -f deployment/dotmac-api -n dotmac-staging

# Scale deployment
kubectl scale deployment dotmac-api --replicas=5 -n dotmac-staging

# Rolling update
kubectl set image deployment/dotmac-api api=dotmac/platform:v2.0.0 -n dotmac-staging
kubectl rollout status deployment/dotmac-api -n dotmac-staging
```

### Module 2: Monitoring & Alerting (Week 2)

**Prometheus Configuration:**
```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  
scrape_configs:
  - job_name: 'dotmac-api'
    kubernetes_sd_configs:
      - role: endpoints
        namespaces:
          names: ['dotmac-production']
    relabel_configs:
      - source_labels: [__meta_kubernetes_service_name]
        regex: dotmac-api
        action: keep
```

**Alert Rules:**
```yaml
# alert_rules.yml
groups:
  - name: dotmac-alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High error rate on {{ $labels.instance }}"
          
      - alert: ServiceDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service {{ $labels.instance }} is down"
```

**Lab 2: Setting Up Monitoring**
```bash
# Deploy monitoring stack
helm install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace

# Import DotMac dashboards
curl -X POST http://grafana:3000/api/dashboards/import \
  -H "Content-Type: application/json" \
  -d @monitoring/dashboards/dotmac-overview.json

# Configure alerts
kubectl apply -f monitoring/alerts/
```

### Module 3: Backup & Recovery (Week 3)

**Backup Strategy:**
```bash
#!/bin/bash
# Comprehensive backup script

# Database backup
pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME \
  --format=custom --compress=9 \
  --file="/backups/db-$(date +%Y%m%d-%H%M%S).dump"

# Kubernetes state backup
kubectl get all,configmaps,secrets -o yaml -n dotmac-production > \
  "/backups/k8s-state-$(date +%Y%m%d-%H%M%S).yaml"

# Persistent volume backup
kubectl create job backup-pv-$(date +%s) \
  --image=postgres:15 -- \
  /bin/bash -c "pg_dump $DATABASE_URL > /backup/full-backup.sql"
```

**Disaster Recovery Drill:**
```bash
# Simulate disaster and recovery
kubectl delete namespace dotmac-production
bash scripts/disaster_recovery.sh --restore-from=latest

# Verify data integrity
python3 scripts/verify_data_integrity.py --comprehensive
```

### Module 4: Performance Optimization (Week 4)

**Database Optimization:**
```sql
-- Query performance analysis
SELECT query, calls, total_time, mean_time, stddev_time
FROM pg_stat_statements 
ORDER BY total_time DESC 
LIMIT 20;

-- Index optimization
CREATE INDEX CONCURRENTLY idx_customers_active 
ON customers (status) WHERE status = 'active';

-- Vacuum and analyze
VACUUM ANALYZE customers;
```

**Application Performance:**
```bash
# Profile application performance
python -m cProfile -o profile.stats app.py
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative').print_stats(20)"

# Load testing
ab -n 10000 -c 100 http://localhost:8000/api/v1/customers
wrk -t12 -c400 -d30s http://localhost:8000/api/v1/health
```

## 🔒 Security Team Training

### Module 1: Security Architecture (Week 1)

**Authentication & Authorization:**
```python
# JWT token implementation
from dotmac_shared.auth.jwt_service import JWTService

class AuthenticationService:
    def __init__(self):
        self.jwt_service = JWTService()
    
    async def authenticate_user(self, username: str, password: str) -> str:
        user = await self.verify_credentials(username, password)
        if not user:
            raise AuthenticationError("Invalid credentials")
        
        # Generate JWT with proper claims
        token = self.jwt_service.create_access_token({
            "sub": str(user.id),
            "tenant_id": str(user.tenant_id),
            "permissions": user.permissions,
            "exp": datetime.utcnow() + timedelta(hours=24)
        })
        
        return token
```

**Multi-Tenant Security:**
```python
from dotmac_shared.auth.tenant_isolation import tenant_isolation

@router.get("/customers")
@tenant_isolation
async def list_customers(current_user: User = Depends(get_current_user)):
    # Automatically filtered by tenant_id
    # No cross-tenant data leakage possible
    return await customer_service.list_customers(current_user.tenant_id)
```

### Module 2: Vulnerability Management (Week 2)

**Security Scanning Pipeline:**
```yaml
# .github/workflows/security-scan.yml
name: Security Scan
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Run Semgrep
        run: |
          python -m pip install semgrep
          semgrep --config=auto --error .
          
      - name: Run Safety
        run: |
          python -m pip install safety
          safety check --json --output safety-report.json
          
      - name: Container Scan
        run: |
          docker build -t dotmac/platform:test .
          trivy image --severity HIGH,CRITICAL dotmac/platform:test
```

**Penetration Testing:**
```bash
# Regular security testing
nmap -sS -sV -O target.dotmac.platform
nikto -h https://api.dotmac.platform
sqlmap -u "https://api.dotmac.platform/api/v1/customers?id=1" --cookie="session=abc123"

# OWASP ZAP automation
docker run -t owasp/zap2docker-stable zap-baseline.py -t https://api.dotmac.platform
```

### Module 3: Incident Response (Week 3)

**Security Incident Playbook:**
```bash
# Security incident response checklist

# 1. Immediate containment
kubectl scale deployment suspicious-service --replicas=0
iptables -A INPUT -s suspicious_ip -j DROP

# 2. Evidence collection
kubectl logs deployment/affected-service > incident-logs.txt
tcpdump -i eth0 -w incident-traffic.pcap

# 3. Analysis
grep -i "injection\|xss\|sql" /var/log/nginx/access.log
python3 scripts/analyze_security_logs.py --incident-id=SEC-2024-001

# 4. Recovery
kubectl rollout restart deployment/affected-service
bash scripts/security_hardening.sh --emergency-mode
```

## 📞 Customer Support Training

### Module 1: Platform Knowledge (Week 1)

**Customer Portal Navigation:**
- Account management and billing
- Service requests and modifications  
- Support ticket creation and tracking
- Usage monitoring and reports

**Common Customer Issues:**
1. **Login Problems** - Password resets, 2FA issues
2. **Billing Questions** - Invoice discrepancies, payment failures
3. **Service Issues** - Connectivity problems, speed concerns
4. **Portal Navigation** - Feature location, report generation

### Module 2: Technical Troubleshooting (Week 2)

**Diagnostic Tools:**
```bash
# Customer connectivity testing
ping customer-gateway.example.com
traceroute customer-gateway.example.com
nslookup customer.dotmac.platform

# Service status checking
curl -I https://api.dotmac.platform/health
curl https://api.dotmac.platform/api/v1/status/customer/{customer_id}
```

**Customer Data Lookup:**
```python
# Support portal queries (read-only access)
from dotmac_shared.support import CustomerLookup

lookup = CustomerLookup()

# Find customer by various identifiers
customer = await lookup.find_by_email("customer@example.com")
customer = await lookup.find_by_phone("+1234567890") 
customer = await lookup.find_by_account_number("ACC-12345")

# Get service history
services = await lookup.get_customer_services(customer.id)
tickets = await lookup.get_support_history(customer.id)
```

### Module 3: Escalation Procedures (Week 3)

**Support Tiers:**
- **Tier 1**: General inquiries, account questions, basic troubleshooting
- **Tier 2**: Technical issues, billing problems, service modifications
- **Tier 3**: Complex technical problems, system issues, data recovery

**Escalation Triggers:**
- Customer requests manager
- Technical issue beyond tier capabilities
- Service affecting multiple customers
- Security-related concerns
- Billing discrepancies over $500

## 👔 Management Training

### Module 1: Platform Metrics & KPIs (Week 1)

**Business Metrics Dashboard:**
```python
# Executive dashboard metrics
from dotmac_shared.analytics import BusinessMetrics

metrics = BusinessMetrics()

# Revenue metrics
mrr = await metrics.monthly_recurring_revenue()
arr = await metrics.annual_recurring_revenue()
churn_rate = await metrics.customer_churn_rate()

# Operational metrics
uptime = await metrics.platform_uptime()
avg_response_time = await metrics.average_response_time()
support_ticket_resolution = await metrics.avg_ticket_resolution_time()

# Growth metrics
new_customers = await metrics.new_customers_this_month()
customer_ltv = await metrics.customer_lifetime_value()
```

**Financial Reporting:**
```sql
-- Monthly revenue report
SELECT 
  DATE_TRUNC('month', created_at) as month,
  SUM(total_amount) as revenue,
  COUNT(DISTINCT customer_id) as paying_customers,
  AVG(total_amount) as avg_invoice_amount
FROM invoices 
WHERE status = 'paid' 
  AND created_at > NOW() - INTERVAL '12 months'
GROUP BY month 
ORDER BY month;
```

### Module 2: Capacity Planning (Week 2)

**Resource Forecasting:**
```python
# Capacity planning analysis
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

def forecast_capacity_needs():
    # Load historical data
    df = pd.read_sql("""
        SELECT date, cpu_usage, memory_usage, disk_usage, active_users
        FROM system_metrics 
        WHERE date > NOW() - INTERVAL '90 days'
        ORDER BY date
    """, connection)
    
    # Forecast resource needs
    model = LinearRegression()
    X = np.array(range(len(df))).reshape(-1, 1)
    
    cpu_forecast = model.fit(X, df['cpu_usage']).predict([[len(df) + 30]])[0]
    memory_forecast = model.fit(X, df['memory_usage']).predict([[len(df) + 30]])[0]
    
    return {
        "cpu_forecast_30d": cpu_forecast,
        "memory_forecast_30d": memory_forecast,
        "scaling_recommendation": "increase" if cpu_forecast > 80 else "maintain"
    }
```

### Module 3: Incident Management (Week 3)

**Incident Response Leadership:**
```bash
# Incident commander checklist
# 1. Assess impact and severity
# 2. Assemble response team
# 3. Communicate with stakeholders
# 4. Coordinate resolution efforts
# 5. Document lessons learned

# Status page updates
curl -X POST "https://api.statuspage.io/v1/pages/$PAGE_ID/incidents" \
  -H "Authorization: OAuth $STATUSPAGE_TOKEN" \
  -d '{
    "incident": {
      "name": "API Performance Issues",
      "status": "investigating",
      "impact_override": "minor",
      "body": "We are investigating reports of slow API response times."
    }
  }'
```

## 🏆 Certification Programs

### DotMac Platform Developer Certification

**Prerequisites:**
- 6+ months development experience
- Completed development training modules
- Contributed to 5+ platform features

**Certification Requirements:**
1. **Technical Assessment** (4 hours)
   - Build a new API module following DRY patterns
   - Implement comprehensive testing
   - Add monitoring and logging
   - Document API endpoints

2. **Code Review** (1 hour)
   - Review existing pull request
   - Identify security issues
   - Suggest performance improvements
   - Ensure code quality standards

3. **Architecture Discussion** (1 hour)
   - Explain multi-tenancy design
   - Discuss scaling strategies
   - Security considerations
   - Database optimization

### DotMac Platform Operations Certification

**Prerequisites:**
- 3+ months operations experience
- Completed operations training modules
- Managed production deployments

**Certification Requirements:**
1. **Infrastructure Management** (3 hours)
   - Deploy platform to Kubernetes
   - Configure monitoring and alerting
   - Set up backup and recovery
   - Implement security hardening

2. **Incident Response Simulation** (2 hours)
   - Respond to simulated outage
   - Coordinate with team members
   - Communicate with stakeholders
   - Document resolution steps

3. **Performance Optimization** (2 hours)
   - Analyze performance bottlenecks
   - Implement optimization solutions
   - Load test improvements
   - Document performance gains

### Certification Benefits

**For Individuals:**
- Industry-recognized credential
- Salary bonus eligibility
- Career advancement opportunities
- Access to advanced training

**For Teams:**
- Improved platform reliability
- Faster incident resolution
- Better code quality
- Reduced onboarding time

## 📚 Additional Resources

### Documentation Links
- [API Reference](https://docs.dotmac.platform/api/)
- [Architecture Guide](./ARCHITECTURE.md)
- [Security Production Checklist](./SECURITY_PRODUCTION_CHECKLIST.md)
- [Production Deployment Runbook](./PRODUCTION_DEPLOYMENT_RUNBOOK.md)

### Training Videos
- Platform Overview (30 minutes)
- Development Workflow (45 minutes)
- Security Best Practices (60 minutes)
- Operations Deep Dive (90 minutes)

### Practice Environments
- **Development**: https://dev.dotmac.platform
- **Staging**: https://staging.dotmac.platform
- **Training**: https://training.dotmac.platform

### Support Channels
- **Training Questions**: training@dotmac.platform
- **Technical Support**: tech-support@dotmac.platform
- **Documentation Issues**: docs@dotmac.platform

---

**Last Updated**: 2024-12-31
**Version**: 1.0.0
