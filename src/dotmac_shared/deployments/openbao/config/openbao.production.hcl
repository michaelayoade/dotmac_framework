# OpenBao production configuration for DotMac Framework
storage "postgresql" {
  connection_url = "postgres://openbao_user:CHANGE_ME_IN_PRODUCTION@postgres-shared:5432/openbao?sslmode=require"
  ha_enabled     = true
}

listener "tcp" {
  address       = "0.0.0.0:8200"
  tls_cert_file = "/openbao/certs/openbao.crt"
  tls_key_file  = "/openbao/certs/openbao.key"

  # Enable CORS for production frontends
  cors {
    enabled        = true
    allowed_origins = [
      "https://admin.dotmac.com",
      "https://customer.dotmac.com",
      "https://reseller.dotmac.com",
      "https://mgmt.dotmac.com"
    ]
    allowed_headers = ["Authorization", "Content-Type"]
    allowed_methods = ["GET", "POST", "PUT", "DELETE"]
  }
}

cluster_addr = "https://openbao:8201"
api_addr = "https://vault.dotmac.com:8200"

ui = true

# Production TTL settings
default_lease_ttl = "24h"
max_lease_ttl = "168h"

# Enable comprehensive audit logging
audit {
  enabled = true
  path = "/openbao/logs/audit.log"
  format = "json"
  log_raw = false
}

# High availability
ha_storage {
  redirect_addr = "https://vault.dotmac.com:8200"
  cluster_addr = "https://openbao:8201"
}

# Performance tuning for production
cache_size = 262144

# Enhanced telemetry
telemetry {
  prometheus_retention_time = "24h"
  disable_hostname = false
  usage_gauge_period = "10m"
  maximum_gauge_cardinality = 500

  statsd_address = "statsd:8125"
  statsite_address = "statsite:8125"
}
