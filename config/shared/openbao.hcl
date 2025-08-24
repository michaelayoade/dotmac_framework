# OpenBao configuration for DotMac Framework
storage "file" {
  path = "/openbao/file"
}

listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = 1
  
  # Enable CORS for frontend applications
  cors {
    enabled        = true
    allowed_origins = [
      "http://localhost:3000",
      "http://localhost:3001",
      "http://localhost:3002",
      "https://admin.dotmac.local",
      "https://customer.dotmac.local",
      "https://reseller.dotmac.local"
    ]
    allowed_headers = ["*"]
  }
}

api_addr = "http://0.0.0.0:8200"
cluster_addr = "http://0.0.0.0:8201"
ui = true

# Default TTL settings
default_lease_ttl = "168h"
max_lease_ttl = "720h"

# Enable audit logging
audit {
  enabled = true
  path = "/openbao/logs/audit.log"
}

# Performance tuning
cache_size = 131072

# Telemetry configuration
telemetry {
  prometheus_retention_time = "0s"
  disable_hostname = true
}