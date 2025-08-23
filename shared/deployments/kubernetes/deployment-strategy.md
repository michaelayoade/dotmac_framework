# DotMac Platform Kubernetes Deployment Strategy

## Overview

This document outlines the production deployment strategy for the DotMac Platform with comprehensive production readiness features including Prometheus metrics, graceful shutdown, circuit breakers, and enhanced health checks.

## Production Readiness Features Implemented

### ✅ Critical Production Features

1. **Prometheus /metrics Endpoint**
   - Exposed at `/metrics` for monitoring integration
   - Comprehensive metrics collection via middleware
   - Tenant-isolated metrics with proper labeling

2. **Graceful Shutdown Handling**
   - SIGTERM signal handling with 30-second drain timeout
   - Proper resource cleanup during shutdown
   - Middleware to reject new requests during shutdown

3. **Circuit Breaker for External Calls**
   - Configurable failure thresholds and recovery timeouts
   - API endpoints for circuit breaker management
   - Integration with Prometheus metrics

4. **Enhanced Readiness Probes**
   - Comprehensive dependency health checks (database, Redis, circuit breakers)
   - Separate `/health`, `/ready`, and `/live` endpoints
   - Detailed health status reporting

5. **Kubernetes Deployment Strategy**
   - Rolling updates with proper resource limits
   - Pod disruption budgets and anti-affinity rules
   - Horizontal pod autoscaling based on CPU/memory

## Deployment Architecture

### Namespaces
- `dotmac-production`: Main application workloads
- `dotmac-monitoring`: Prometheus and monitoring stack
- `dotmac-ingress`: Ingress controllers and load balancers

### Security Features
- Non-root container execution
- Read-only root filesystem
- Security contexts with dropped capabilities
- Network policies for traffic isolation
- Secret management for sensitive data

### High Availability
- Minimum 3 replicas with pod anti-affinity
- Pod disruption budget (minimum 2 available)
- Rolling update strategy (max 1 unavailable, max 1 surge)
- Horizontal pod autoscaling (3-10 replicas)

### Monitoring & Observability
- Prometheus ServiceMonitor for metrics scraping
- Comprehensive alerting rules for critical conditions
- Health check endpoints for Kubernetes probes
- Circuit breaker state monitoring

## Deployment Steps

### 1. Prerequisites
```bash
# Create namespaces
kubectl apply -f deployments/kubernetes/namespace.yaml

# Install cert-manager for TLS certificates
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Install Prometheus Operator (if not already installed)
kubectl apply -f https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/main/bundle.yaml
```

### 2. Secrets Configuration
```bash
# Update secrets with actual values
kubectl apply -f deployments/kubernetes/secrets.yaml

# Verify secrets are created
kubectl get secrets -n dotmac-production
```

### 3. Configuration
```bash
# Apply configuration maps
kubectl apply -f deployments/kubernetes/configmap.yaml
```

### 4. Database and Dependencies
```bash
# Deploy PostgreSQL
kubectl apply -f deployments/kubernetes/postgres.yaml

# Wait for database to be ready
kubectl wait --for=condition=ready pod -l app=postgres -n dotmac-production --timeout=300s
```

### 5. Application Deployment
```bash
# Deploy the main platform
kubectl apply -f deployments/kubernetes/dotmac-platform-deployment.yaml

# Wait for deployment to be ready
kubectl wait --for=condition=available deployment/dotmac-platform -n dotmac-production --timeout=300s
```

### 6. Ingress and Networking
```bash
# Apply ingress and network policies
kubectl apply -f deployments/kubernetes/ingress.yaml
```

### 7. Monitoring Setup
```bash
# Apply monitoring configuration
kubectl apply -f deployments/kubernetes/monitoring.yaml
```

## Health Check Endpoints

### `/health` - Basic Health Check
- Simple liveness check
- Returns basic service information
- Used for general health monitoring

### `/ready` - Readiness Probe
- Comprehensive dependency checks
- Database connectivity validation
- Redis connectivity validation
- Circuit breaker status
- System resource monitoring
- Returns 503 if any critical dependency is unhealthy

### `/live` - Liveness Probe
- Minimal check for process responsiveness
- Used by Kubernetes liveness probe
- Only fails if application is completely broken

### `/metrics` - Prometheus Metrics
- Standard Prometheus exposition format
- HTTP request metrics (latency, throughput, errors)
- Database query metrics
- Circuit breaker metrics
- Business metrics with tenant isolation

## Circuit Breaker Configuration

Circuit breakers are automatically created for external service calls with configurable:
- Failure threshold (default: 5 failures)
- Recovery timeout (default: 60 seconds)
- Success threshold for half-open state (default: 3 successes)
- Request timeout (default: 30 seconds)

Management endpoints:
- `GET /api/v1/circuit-breakers/status` - View all circuit breaker status
- `POST /api/v1/circuit-breakers/{name}/reset` - Reset specific circuit breaker
- `POST /api/v1/circuit-breakers/reset-all` - Reset all circuit breakers

## Graceful Shutdown Process

1. **Signal Reception**: Application receives SIGTERM signal
2. **Stop New Requests**: Middleware starts returning 503 for new requests
3. **Drain Period**: Wait 30 seconds for existing requests to complete
4. **Resource Cleanup**: Execute registered cleanup tasks (database connections, etc.)
5. **Process Exit**: Clean application shutdown

## Monitoring and Alerting

### Key Metrics
- `http_requests_total` - Total HTTP requests with labels
- `http_request_duration_seconds` - Request latency histogram
- `circuit_breaker_state` - Circuit breaker states (0=closed, 1=open, 2=half-open)
- `database_connections_active` - Active database connections
- `cache_operations_total` - Cache operation counters

### Critical Alerts
- Platform down (no metrics for 1 minute)
- High error rate (>10% 5xx responses for 2 minutes)
- High latency (95th percentile >1s for 5 minutes)
- Circuit breaker open
- Database connection failures
- High resource usage (>90% memory or >80% CPU)

## Security Considerations

### Container Security
- Non-root user execution (UID 1000)
- Read-only root filesystem
- Dropped Linux capabilities
- Security context constraints

### Network Security
- Network policies restricting pod-to-pod communication
- TLS termination at ingress
- Rate limiting at ingress level

### Secret Management
- Kubernetes secrets for sensitive data
- Separate secrets for different components
- Regular secret rotation recommended

## Scaling Configuration

### Horizontal Pod Autoscaler
- Min replicas: 3
- Max replicas: 10
- CPU target: 70% utilization
- Memory target: 80% utilization
- Scale-up: Max 50% increase or 2 pods per minute
- Scale-down: Max 10% decrease per minute with 5-minute stabilization

### Resource Limits
- Requests: 250m CPU, 512Mi memory
- Limits: 500m CPU, 1Gi memory
- Ensures predictable resource allocation

## Troubleshooting

### Common Issues

1. **Readiness Probe Failures**
   - Check `/ready` endpoint response
   - Verify database and Redis connectivity
   - Check circuit breaker status

2. **High Memory Usage**
   - Monitor application metrics
   - Check for memory leaks
   - Consider increasing resource limits

3. **Circuit Breaker Open**
   - Check external service health
   - Review error logs
   - Consider manual reset if service recovered

### Useful Commands
```bash
# Check pod status
kubectl get pods -n dotmac-production

# View application logs
kubectl logs -f deployment/dotmac-platform -n dotmac-production

# Check readiness probe status
kubectl describe pod <pod-name> -n dotmac-production

# Port forward for local testing
kubectl port-forward service/dotmac-platform-service 8000:8000 -n dotmac-production
```

## Production Checklist Compliance

| Feature | Status | Implementation |
|---------|--------|----------------|
| Prometheus /metrics endpoint | ✅ | `/metrics` endpoint with comprehensive metrics |
| Graceful shutdown (SIGTERM → drain → 30s) | ✅ | Signal handlers with 30s drain timeout |
| Circuit breaker for external calls | ✅ | Configurable circuit breakers with management API |
| Readiness probes with dependency checks | ✅ | `/ready` endpoint with database, Redis, circuit breaker checks |
| Kubernetes deployment strategy | ✅ | Rolling updates, HPA, PDB, anti-affinity rules |

**Overall Production Readiness: 🟢 FULLY COMPLIANT (100%)**

The DotMac Platform now meets all production readiness requirements and is ready for deployment to production Kubernetes environments.
