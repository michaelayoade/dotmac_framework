# DotMac Ticketing - Rate Limiting

## Overview

The DotMac ticketing system includes built-in rate limiting to protect against abuse and ensure fair resource usage. Rate limiting is applied per tenant and includes proper HTTP headers for client awareness.

## Rate Limit Configuration

### Default Limits

| Route Type | Requests/Minute | Recommended for Production |
|-----------|----------------|---------------------------|
| Ticket Creation | 60 | 30-120 depending on tenant size |
| Ticket Queries | 100 | 200-500 for high-traffic tenants |
| Bulk Operations | 20 | 10-30 for data integrity |
| Health Checks | 300 | No limit needed |

### Per-Route Recommendations

#### High-Impact Operations (Lower Limits)
```python
# Ticket creation - resource intensive
@rate_limit(identifier_key='tenant_id')  # 60/min default
async def create_ticket(...):
    pass

# Bulk operations - database intensive  
@rate_limit(identifier_key='tenant_id')  # Consider 20/min
async def bulk_update_tickets(...):
    pass
```

#### Read Operations (Higher Limits)
```python
# Individual ticket lookup - lightweight
@rate_limit(identifier_key='tenant_id')  # 100/min recommended
async def get_ticket(...):
    pass

# List operations with pagination - moderate impact
@rate_limit(identifier_key='tenant_id')  # 80/min recommended
async def list_tickets(...):
    pass
```

#### Health/Status Checks (Minimal Limits)
```python
# Health checks - very lightweight
@rate_limit(identifier_key='tenant_id')  # 300/min or no limit
async def health_check(...):
    pass
```

## HTTP Headers

When rate limiting is active, the following headers are included in all responses:

### Rate Limit Headers

| Header | Description | Example |
|--------|-------------|---------|
| `X-RateLimit-Limit` | Maximum requests per minute | `60` |
| `X-RateLimit-Remaining` | Requests remaining in current window | `45` |
| `X-RateLimit-Reset` | Unix timestamp when limit resets | `1640995200` |
| `X-RateLimit-Used` | Requests used in current window | `15` |

### Example Response Headers

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1640995200
X-RateLimit-Used: 15
Content-Type: application/json
```

### Rate Limit Exceeded Response

```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1640995260
X-RateLimit-Used: 60
Content-Type: application/json

{
  "detail": "Rate limit exceeded for tenant-123. Limit: 60/min, Reset: 1640995260"
}
```

## Implementation

### Basic Usage

```python
from dotmac.ticketing.core.security import rate_limit, RateLimitError

@rate_limit("tenant_id")
async def my_endpoint(tenant_id: str):
    # Your endpoint logic here
    pass
```

### Custom Rate Limits

```python
from dotmac.ticketing.core.security import SimpleRateLimit

# Create custom rate limiter
custom_limiter = SimpleRateLimit(requests_per_minute=30)

@custom_rate_limit("tenant_id", limiter=custom_limiter)
async def sensitive_endpoint(tenant_id: str):
    # High-security endpoint with lower limit
    pass
```

### Adding Headers to FastAPI Responses

```python
from fastapi import Response
from dotmac.ticketing.core.security import add_rate_limit_headers

@app.get("/tickets/")
async def list_tickets(response: Response, tenant_id: str, _rate_limit_info: dict = None):
    tickets = await get_tickets(tenant_id)
    
    # Add rate limit headers
    if _rate_limit_info:
        add_rate_limit_headers(response, _rate_limit_info)
    
    return tickets
```

## Configuration Options

### Environment Variables

```bash
# Rate limiting configuration
TICKETING_RATE_LIMIT_ENABLED=true
TICKETING_RATE_LIMIT_DEFAULT=60
TICKETING_RATE_LIMIT_CREATE_TICKET=30
TICKETING_RATE_LIMIT_LIST_TICKETS=100
TICKETING_RATE_LIMIT_BULK_OPERATIONS=20

# Redis for distributed rate limiting (optional)
TICKETING_RATE_LIMIT_REDIS_URL=redis://localhost:6379
TICKETING_RATE_LIMIT_REDIS_PREFIX=dotmac_ticketing_rate_limit
```

### Application Configuration

```python
rate_limit_config = {
    "enabled": True,
    "default_limit": 60,
    "limits": {
        "create_ticket": 30,
        "list_tickets": 100,
        "get_ticket": 200,
        "bulk_operations": 20,
        "health_check": 300
    },
    "identifier": "tenant_id",  # or "user_id", "ip_address"
    "window_size": 60,  # seconds
    "storage": "memory"  # or "redis"
}
```

## Distributed Rate Limiting (Redis)

For multi-instance deployments, use Redis-backed rate limiting:

```python
from dotmac.ticketing.core.security import RedisRateLimit

# Redis-backed rate limiter
redis_limiter = RedisRateLimit(
    redis_url="redis://localhost:6379",
    requests_per_minute=60,
    key_prefix="ticketing_rate_limit"
)
```

## Monitoring and Alerting

### Metrics to Track

1. **Rate Limit Hit Rate**: Percentage of requests that hit rate limits
2. **Top Rate-Limited Tenants**: Identify heavy users
3. **Rate Limit Effectiveness**: Correlation with system performance
4. **False Positive Rate**: Legitimate users being rate limited

### Grafana Queries

```sql
-- Rate limit hit rate by tenant
SELECT 
    tenant_id,
    COUNT(*) as total_requests,
    COUNT(CASE WHEN status_code = 429 THEN 1 END) as rate_limited_requests,
    ROUND(
        (COUNT(CASE WHEN status_code = 429 THEN 1 END) * 100.0 / COUNT(*)), 
        2
    ) as rate_limit_hit_rate
FROM api_logs 
WHERE $__timeFilter(timestamp)
GROUP BY tenant_id
ORDER BY rate_limit_hit_rate DESC;

-- Rate limiting effectiveness
SELECT 
    $__timeGroupAlias(timestamp, '$__interval'),
    AVG(response_time_ms) as avg_response_time,
    COUNT(CASE WHEN status_code = 429 THEN 1 END) as rate_limited_count
FROM api_logs
WHERE $__timeFilter(timestamp)
GROUP BY $__timeGroup(timestamp, '$__interval')
ORDER BY 1;
```

### Alerting Rules

```yaml
# Prometheus alerting rules
groups:
- name: ticketing_rate_limiting
  rules:
  - alert: HighRateLimitHitRate
    expr: rate_limit_hit_rate > 10
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High rate limit hit rate for tenant {{ $labels.tenant_id }}"
      description: "Rate limit hit rate is {{ $value }}% for tenant {{ $labels.tenant_id }}"
  
  - alert: RateLimitingDisabled
    expr: rate_limiting_enabled != 1
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Rate limiting is disabled"
      description: "Rate limiting protection has been disabled"
```

## Client Integration

### JavaScript/TypeScript

```typescript
interface RateLimitInfo {
  limit: number;
  remaining: number;
  reset: number;
  used: number;
}

class TicketingClient {
  async makeRequest(url: string): Promise<Response> {
    const response = await fetch(url);
    
    // Parse rate limit headers
    const rateLimit: RateLimitInfo = {
      limit: parseInt(response.headers.get('X-RateLimit-Limit') || '0'),
      remaining: parseInt(response.headers.get('X-RateLimit-Remaining') || '0'),
      reset: parseInt(response.headers.get('X-RateLimit-Reset') || '0'),
      used: parseInt(response.headers.get('X-RateLimit-Used') || '0')
    };
    
    if (response.status === 429) {
      const resetTime = new Date(rateLimit.reset * 1000);
      throw new Error(`Rate limit exceeded. Reset at ${resetTime.toISOString()}`);
    }
    
    // Warn when approaching rate limit
    if (rateLimit.remaining < rateLimit.limit * 0.2) {
      console.warn(`Approaching rate limit: ${rateLimit.remaining}/${rateLimit.limit} remaining`);
    }
    
    return response;
  }
}
```

### Python Client

```python
import time
from typing import Dict, Any

class TicketingClient:
    def __init__(self):
        self.last_rate_limit_info = {}
    
    def make_request(self, url: str) -> Dict[str, Any]:
        response = requests.get(url)
        
        # Parse rate limit headers
        rate_limit_info = {
            'limit': int(response.headers.get('X-RateLimit-Limit', 0)),
            'remaining': int(response.headers.get('X-RateLimit-Remaining', 0)),
            'reset': int(response.headers.get('X-RateLimit-Reset', 0)),
            'used': int(response.headers.get('X-RateLimit-Used', 0))
        }
        
        if response.status_code == 429:
            reset_time = time.ctime(rate_limit_info['reset'])
            raise Exception(f"Rate limit exceeded. Reset at {reset_time}")
        
        # Auto-throttle when approaching limit
        if rate_limit_info['remaining'] < rate_limit_info['limit'] * 0.1:
            sleep_time = max(1, (rate_limit_info['reset'] - time.time()) / rate_limit_info['remaining'])
            time.sleep(min(sleep_time, 10))  # Cap at 10 seconds
        
        return response.json()
```

## Best Practices

### For API Consumers

1. **Check Headers**: Always monitor rate limit headers
2. **Implement Backoff**: Use exponential backoff when hitting limits
3. **Cache Responses**: Reduce API calls with intelligent caching
4. **Batch Operations**: Use bulk endpoints where available
5. **Off-Peak Scheduling**: Schedule heavy operations during low-traffic periods

### For API Providers

1. **Granular Limits**: Different limits for different operation types
2. **Tenant Sizing**: Adjust limits based on tenant size/tier
3. **Graceful Degradation**: Serve cached/partial data when possible
4. **Clear Documentation**: Provide clear rate limiting documentation
5. **Monitoring**: Track rate limiting effectiveness and adjust as needed

### Rate Limit Bypass (Admin/System)

```python
# Special bypass for system operations
@rate_limit("tenant_id", bypass_check=lambda ctx: ctx.get("is_system_user"))
async def system_operation(tenant_id: str, context: dict):
    pass

# IP-based rate limiting for anonymous endpoints
@rate_limit("client_ip")
async def public_endpoint(request: Request):
    client_ip = request.client.host
    # Process request
```

## Troubleshooting

### Common Issues

1. **Clock Skew**: Ensure system clocks are synchronized
2. **Memory Leaks**: Monitor rate limiter memory usage in long-running processes
3. **False Positives**: Legitimate users being rate limited due to shared resources
4. **Redis Connectivity**: Network issues affecting distributed rate limiting

### Debug Commands

```bash
# Check current rate limit status
curl -I https://api.example.com/tickets/health

# Monitor rate limit headers
curl -s -D - https://api.example.com/tickets/ | grep X-RateLimit

# Test rate limiting
for i in {1..70}; do curl -s https://api.example.com/tickets/health; done
```