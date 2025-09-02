# OpenBao configuration for DotMac Framework
storage "file" {
  path = "/openbao/file"
}

# Development listener (TLS disabled for local development)
listener "tcp" {
  address     = "127.0.0.1:8200"
  tls_disable = 1
  
  # Enable CORS for development
  cors {
    enabled        = true
    allowed_origins = [
      "http://localhost:3000",
      "http://localhost:3001",
      "http://localhost:3002"
    ]
    allowed_headers = ["*"]
  }
}

# Production listener (TLS enabled)
listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = 0
  tls_cert_file = "/openbao/tls/tls.crt"
  tls_key_file = "/openbao/tls/tls.key"
  tls_min_version = "tls12"
  tls_cipher_suites = "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256,TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256,TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384,TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384,TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305,TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305"
  
  # Production CORS configuration
  cors {
    enabled        = true
    allowed_origins = [
      "https://admin.dotmac.com",
      "https://customer.dotmac.com", 
      "https://reseller.dotmac.com",
      "https://platform.dotmac.com",
      "https://manage.dotmac.com"
    ]
    allowed_headers = ["Authorization", "Content-Type", "X-Vault-Token", "X-Vault-Namespace"]
    allowed_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
  }
}

# Use environment-specific API addresses
api_addr = "${OPENBAO_API_ADDR}"
cluster_addr = "${OPENBAO_CLUSTER_ADDR}"
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