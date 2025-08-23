# Kubernetes Orchestration Documentation

The DotMac Management Platform uses Kubernetes as the primary container orchestration system for deploying and managing tenant-specific ISP Framework instances. This document covers the complete Kubernetes-based multi-tenant architecture.

## 🎯 **Overview**

The Kubernetes orchestration system enables true SaaS scalability by deploying isolated ISP Framework instances for each tenant customer while maintaining centralized management through the Management Platform.

### **Key Benefits**

- **Complete Tenant Isolation**: Each ISP gets their own Kubernetes namespace with resource boundaries
- **Elastic Scaling**: Automatic scaling based on subscription tier and usage patterns
- **Zero-Downtime Deployments**: Rolling updates with health validation
- **Resource Optimization**: Efficient resource allocation and cost management
- **Multi-Cloud Support**: Deploy across AWS, Azure, GCP, and DigitalOcean

## 🏗️ **Architecture**

### **Three-Tier SaaS Model**

```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│  Management         │────│ Kubernetes Cluster  │────│ ISP Framework       │
│  Platform           │    │                     │    │ (Per Tenant)        │
│  (Orchestrator)     │    │ ┌─────────────────┐ │    │                     │
│  - Tenant Onboard   │    │ │ Namespace:      │ │    │ ┌─────────────────┐ │
│  - Plugin Licensing │    │ │ tenant-isp-001  │ │    │ │ Portal Customers│ │ 
│  - Billing          │    │ │                 │ │    │ │ (End Users)     │ │
│  - Monitoring       │    │ │ Pod: isp-001-1  │ │    │ │                 │ │
│                     │    │ │ Pod: isp-001-2  │ │    │ └─────────────────┘ │
│                     │    │ └─────────────────┘ │    │                     │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
```

### **Namespace Isolation Strategy**

Each tenant receives:
- **Dedicated Namespace**: `dotmac-tenant-{tenant-id}`
- **Resource Quotas**: CPU, memory, storage limits based on subscription tier
- **Network Policies**: Traffic isolation and security boundaries
- **RBAC Policies**: Service account with limited permissions
- **Persistent Volumes**: Isolated storage for tenant data

## 🚀 **Deployment Process**

### **1. Tenant Deployment Request**

```python
# API call to create new tenant deployment
POST /api/v1/tenant-orchestration/deployments
{
  "tenant_name": "Example ISP",
  "resource_tier": "medium",
  "license_tier": "professional", 
  "domain_name": "example-isp.dotmac.app",
  "plugins": ["advanced_billing", "crm_integration", "analytics"]
}
```

### **2. Kubernetes Resource Creation**

The orchestrator creates the following resources:

```yaml
# 1. Namespace
apiVersion: v1
kind: Namespace
metadata:
  name: dotmac-tenant-example-isp-001
  labels:
    app.kubernetes.io/name: dotmac-tenant
    dotmac.io/tenant-id: example-isp-001
    dotmac.io/license-tier: professional

---
# 2. Resource Quota
apiVersion: v1
kind: ResourceQuota
metadata:
  name: tenant-quota
  namespace: dotmac-tenant-example-isp-001
spec:
  hard:
    requests.cpu: "2000m"
    requests.memory: "4Gi"
    limits.cpu: "4000m" 
    limits.memory: "8Gi"
    persistentvolumeclaims: "5"
    requests.storage: "50Gi"

---
# 3. Network Policy
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: tenant-isolation
  namespace: dotmac-tenant-example-isp-001
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: database
  - to: []
    ports:
    - protocol: TCP
      port: 443

---
# 4. Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dotmac-tenant-example-isp-001
  namespace: dotmac-tenant-example-isp-001
spec:
  replicas: 2
  selector:
    matchLabels:
      app.kubernetes.io/name: dotmac-tenant
      app.kubernetes.io/instance: example-isp-001
  template:
    metadata:
      labels:
        app.kubernetes.io/name: dotmac-tenant
        app.kubernetes.io/instance: example-isp-001
        dotmac.io/tenant-id: example-isp-001
    spec:
      containers:
      - name: isp-framework
        image: dotmac/isp-framework:latest
        env:
        - name: ISP_TENANT_ID
          value: "example-isp-001"
        - name: LICENSE_TIER
          value: "professional"
        - name: ENABLED_PLUGINS
          value: "advanced_billing,crm_integration,analytics"
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 2000m
            memory: 4Gi
```

### **3. Health Check and Validation**

```python
# Orchestrator validates deployment health
async def validate_tenant_deployment(tenant_id: str):
    # Check deployment status
    deployment = await k8s_apps_v1.read_namespaced_deployment(
        name=f"dotmac-tenant-{tenant_id}",
        namespace=f"dotmac-tenant-{tenant_id}"
    )
    
    # Verify pods are running
    if deployment.status.ready_replicas >= deployment.spec.replicas:
        return DeploymentStatus.RUNNING
    else:
        return DeploymentStatus.CREATING
```

## 📊 **Resource Tier Management**

### **Subscription Tiers**

```python
RESOURCE_TIERS = {
    "micro": {
        "cpu_request": "100m", "memory_request": "256Mi",
        "cpu_limit": "500m", "memory_limit": "1Gi", 
        "storage_size": "5Gi", "max_replicas": 2,
        "monthly_cost": "$29"
    },
    "small": {
        "cpu_request": "250m", "memory_request": "512Mi",
        "cpu_limit": "1000m", "memory_limit": "2Gi",
        "storage_size": "10Gi", "max_replicas": 3,
        "monthly_cost": "$79"
    },
    "medium": {
        "cpu_request": "500m", "memory_request": "1Gi", 
        "cpu_limit": "2000m", "memory_limit": "4Gi",
        "storage_size": "20Gi", "max_replicas": 5,
        "monthly_cost": "$199"
    },
    "large": {
        "cpu_request": "1000m", "memory_request": "2Gi",
        "cpu_limit": "4000m", "memory_limit": "8Gi",
        "storage_size": "50Gi", "max_replicas": 8,
        "monthly_cost": "$499"
    },
    "xlarge": {
        "cpu_request": "2000m", "memory_request": "4Gi",
        "cpu_limit": "8000m", "memory_limit": "16Gi", 
        "storage_size": "100Gi", "max_replicas": 12,
        "monthly_cost": "$999"
    }
}
```

### **Auto-Scaling Configuration**

```yaml
# Horizontal Pod Autoscaler per tenant
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: dotmac-tenant-{tenant-id}-hpa
  namespace: dotmac-tenant-{tenant-id}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: dotmac-tenant-{tenant-id}
  minReplicas: {min_replicas}
  maxReplicas: {max_replicas}
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## 🔧 **Operations Management**

### **Scaling Operations**

```python
# Scale tenant deployment
async def scale_tenant_deployment(tenant_id: str, replicas: int):
    orchestrator = KubernetesOrchestrator(session)
    
    # Update deployment replicas
    deployment = await orchestrator.scale_deployment(tenant_id, replicas)
    
    # Log scaling event
    await log_deployment_event(
        deployment.id, "scale", "success",
        f"Scaled to {replicas} replicas"
    )
    
    return deployment
```

### **Update Management**

```python
# Rolling update with zero downtime
async def update_tenant_deployment(tenant_id: str, new_image_tag: str):
    orchestrator = KubernetesOrchestrator(session)
    
    # Get current deployment
    deployment = await orchestrator.get_tenant_deployment(tenant_id)
    
    # Update image tag
    deployment.image_tag = new_image_tag
    deployment.status = DeploymentStatus.UPDATING
    
    # Trigger rolling update in Kubernetes
    await orchestrator.update_deployment_image(tenant_id, new_image_tag)
    
    # Wait for rollout to complete
    await orchestrator.wait_for_rollout_completion(tenant_id)
    
    deployment.status = DeploymentStatus.RUNNING
    await session.commit()
```

### **Health Monitoring**

```python
# Continuous health monitoring
async def monitor_tenant_health(tenant_id: str):
    try:
        # Check pod status
        pods = await k8s_core_v1.list_namespaced_pod(
            namespace=f"dotmac-tenant-{tenant_id}",
            label_selector=f"app.kubernetes.io/instance={tenant_id}"
        )
        
        running_pods = sum(1 for pod in pods.items if pod.status.phase == "Running")
        total_pods = len(pods.items)
        
        # Check service endpoints
        endpoints = await k8s_core_v1.read_namespaced_endpoints(
            name=f"dotmac-tenant-{tenant_id}",
            namespace=f"dotmac-tenant-{tenant_id}"
        )
        
        ready_endpoints = sum(len(subset.addresses or []) for subset in endpoints.subsets or [])
        
        health_status = {
            "tenant_id": tenant_id,
            "pods_running": running_pods,
            "pods_total": total_pods,
            "endpoints_ready": ready_endpoints,
            "health": "healthy" if running_pods == total_pods else "degraded",
            "timestamp": datetime.utcnow()
        }
        
        return health_status
        
    except Exception as e:
        return {
            "tenant_id": tenant_id,
            "health": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow()
        }
```

## 🔒 **Security & Isolation**

### **Multi-Tenant Security Model**

```yaml
# Service Account per tenant
apiVersion: v1
kind: ServiceAccount
metadata:
  name: dotmac-tenant-sa
  namespace: dotmac-tenant-{tenant-id}

---
# Role with minimal permissions
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: dotmac-tenant-{tenant-id}
  name: tenant-role
rules:
- apiGroups: [""]
  resources: ["configmaps", "secrets"]
  verbs: ["get", "list"]
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list"]

---
# Bind role to service account
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: tenant-binding
  namespace: dotmac-tenant-{tenant-id}
subjects:
- kind: ServiceAccount
  name: dotmac-tenant-sa
  namespace: dotmac-tenant-{tenant-id}
roleRef:
  kind: Role
  name: tenant-role
  apiGroup: rbac.authorization.k8s.io
```

### **Network Isolation**

```yaml
# Network policy to isolate tenant traffic
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: tenant-network-isolation
  namespace: dotmac-tenant-{tenant-id}
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  # Allow ingress from load balancer only
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000
  egress:
  # Allow egress to shared services
  - to:
    - namespaceSelector:
        matchLabels:
          name: database
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - namespaceSelector:
        matchLabels:
          name: redis
    ports:
    - protocol: TCP
      port: 6379
  # Allow HTTPS egress
  - to: []
    ports:
    - protocol: TCP
      port: 443
```

## 📈 **Monitoring & Observability**

### **Metrics Collection**

```python
# Custom metrics for tenant monitoring
TENANT_METRICS = [
    "http_requests_total",
    "http_request_duration_seconds",
    "active_users",
    "database_connections",
    "memory_usage_bytes",
    "cpu_usage_ratio"
]

# Prometheus metrics endpoint
@app.get("/metrics")
async def get_tenant_metrics():
    tenant_id = request.headers.get("X-Tenant-ID")
    
    metrics = {
        "tenant_id": tenant_id,
        "timestamp": datetime.utcnow(),
        "http_requests_total": get_request_count(),
        "active_users": get_active_user_count(),
        "database_connections": get_db_connection_count(),
        "memory_usage_bytes": get_memory_usage(),
        "cpu_usage_ratio": get_cpu_usage()
    }
    
    return metrics
```

### **Log Aggregation**

```python
# Structured logging for tenant operations
import structlog

logger = structlog.get_logger()

def log_tenant_operation(tenant_id: str, operation: str, **kwargs):
    logger.info(
        "tenant_operation",
        tenant_id=tenant_id,
        operation=operation,
        **kwargs
    )

# Example usage
log_tenant_operation(
    tenant_id="example-isp-001",
    operation="scale_deployment",
    old_replicas=2,
    new_replicas=4,
    reason="high_cpu_usage"
)
```

## 🚀 **API Reference**

### **Deployment Management**

```python
# Create tenant deployment
POST /api/v1/tenant-orchestration/deployments
{
  "tenant_name": "Example ISP",
  "resource_tier": "medium",
  "license_tier": "professional",
  "domain_name": "example-isp.dotmac.app",
  "cluster_name": "production",
  "image_tag": "v1.2.0"
}

# Scale deployment
POST /api/v1/tenant-orchestration/deployments/{tenant_id}/scale
{
  "replicas": 5,
  "reason": "increased_load"
}

# Update deployment
PATCH /api/v1/tenant-orchestration/deployments/{tenant_id}
{
  "image_tag": "v1.3.0",
  "resource_tier": "large"
}

# Get deployment status
GET /api/v1/tenant-orchestration/deployments/{tenant_id}

# List all deployments
GET /api/v1/tenant-orchestration/deployments?status=running&page=1&limit=50

# Delete deployment
DELETE /api/v1/tenant-orchestration/deployments/{tenant_id}

# Get cluster health
GET /api/v1/tenant-orchestration/cluster/health
```

### **Resource Management**

```python
# Get resource usage
GET /api/v1/tenant-orchestration/deployments/{tenant_id}/resources

# Update resource limits
PATCH /api/v1/tenant-orchestration/deployments/{tenant_id}/resources
{
  "cpu_limit": "4000m",
  "memory_limit": "8Gi", 
  "storage_limit": "100Gi"
}

# Get scaling recommendations
GET /api/v1/tenant-orchestration/deployments/{tenant_id}/recommendations
```

## 🛠️ **Development & Testing**

### **Local Development Setup**

```bash
# Start local Kubernetes cluster
make k8s-dev-start

# Deploy tenant in development
curl -X POST http://localhost:8000/api/v1/tenant-orchestration/deployments \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_name": "Dev ISP",
    "resource_tier": "micro",
    "license_tier": "basic",
    "cluster_name": "local"
  }'

# Check deployment status
kubectl get pods -n dotmac-tenant-dev-isp-001

# View logs
kubectl logs -f deployment/dotmac-tenant-dev-isp-001 -n dotmac-tenant-dev-isp-001

# Port forward for testing
kubectl port-forward deployment/dotmac-tenant-dev-isp-001 8080:8000 -n dotmac-tenant-dev-isp-001
```

### **Testing Tenant Isolation**

```python
# Test script to validate tenant isolation
import asyncio
import aiohttp

async def test_tenant_isolation():
    # Create two test tenants
    tenant_a = await create_test_tenant("test-isp-a") 
    tenant_b = await create_test_tenant("test-isp-b")
    
    # Verify they can't access each other's data
    async with aiohttp.ClientSession() as session:
        # Try to access tenant B data from tenant A
        async with session.get(
            f"https://test-isp-a.dotmac.app/api/customers",
            headers={"X-Tenant-ID": "test-isp-b"}  # Wrong tenant ID
        ) as response:
            assert response.status == 403, "Tenant isolation failed"
    
    print("✅ Tenant isolation test passed")

# Run isolation tests
asyncio.run(test_tenant_isolation())
```

## 🎯 **Best Practices**

### **Resource Management**
- Start with smaller resource tiers and scale up based on usage
- Monitor resource utilization and adjust limits accordingly
- Use horizontal scaling for traffic spikes, vertical scaling for resource-intensive workloads
- Implement resource quotas to prevent runaway resource consumption

### **Security**
- Always use dedicated namespaces for tenant isolation
- Implement network policies to control traffic flow
- Use service accounts with minimal required permissions
- Regularly rotate secrets and certificates
- Enable audit logging for security monitoring

### **Monitoring**
- Implement comprehensive health checks at application and infrastructure levels
- Set up alerting for resource usage, error rates, and performance degradation
- Use distributed tracing to debug cross-tenant issues
- Monitor costs and optimize resource allocation

### **Deployment**
- Use rolling deployments for zero-downtime updates
- Implement proper health checks to validate deployment success
- Maintain rollback capabilities for failed deployments
- Test all changes in staging environment first

This Kubernetes orchestration system provides a robust, scalable foundation for the DotMac SaaS platform, enabling efficient multi-tenant management while maintaining security and performance isolation.