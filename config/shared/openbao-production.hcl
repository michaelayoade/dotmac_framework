# OpenBao Production Configuration for DotMac Framework
# High-availability, secure production deployment

# Shared storage for production clustering
storage "consul" {
  address = "${CONSUL_ADDRESS:-127.0.0.1:8500}"
  path    = "openbao/"
  token   = "${CONSUL_TOKEN}"
  
  # Enable consistency for production
  consistency_mode = "strong"
  
  # Session TTL for lock management
  session_ttl = "15s"
  lock_wait_time = "15s"
}

# Alternative: PostgreSQL storage for existing infrastructure
# storage "postgresql" {
#   connection_url = "${POSTGRES_CONNECTION_URL}"
#   table          = "openbao_kv_store"
#   max_parallel   = 128
# }

# High-availability clustering
cluster_addr = "${OPENBAO_CLUSTER_ADDR:-https://openbao:8201}"
api_addr     = "${OPENBAO_API_ADDR:-https://openbao.dotmac.com:8200}"

# Production TLS listener
listener "tcp" {
  address       = "0.0.0.0:8200"
  tls_disable   = 0
  tls_cert_file = "/openbao/tls/server.crt"
  tls_key_file  = "/openbao/tls/server.key"
  tls_ca_file   = "/openbao/tls/ca.crt"
  
  # Modern TLS configuration
  tls_min_version = "tls12"
  tls_max_version = "tls13"
  tls_prefer_server_cipher_suites = true
  
  # Strong cipher suites for production
  tls_cipher_suites = "TLS_AES_256_GCM_SHA384,TLS_CHACHA20_POLY1305_SHA256,TLS_AES_128_GCM_SHA256,TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384,TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384"
  
  # Client certificate authentication (optional)
  tls_require_and_verify_client_cert = false
  
  # Production CORS policy - strict origins
  cors {
    enabled = true
    allowed_origins = [
      "https://admin.dotmac.com",
      "https://customer.dotmac.com",
      "https://reseller.dotmac.com", 
      "https://platform.dotmac.com",
      "https://manage.dotmac.com",
      "https://api.dotmac.com"
    ]
    allowed_headers = [
      "Authorization",
      "Content-Type", 
      "X-Vault-Token",
      "X-Vault-Namespace",
      "X-Request-Id"
    ]
    allowed_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "LIST"]
  }
  
  # Connection limits for production
  max_request_size     = 33554432  # 32MB
  max_request_duration = "90s"
}

# Cluster communication listener  
listener "tcp" {
  address     = "0.0.0.0:8201"
  tls_disable = 0
  tls_cert_file = "/openbao/tls/server.crt"
  tls_key_file  = "/openbao/tls/server.key"
  tls_ca_file   = "/openbao/tls/ca.crt"
  
  # Cluster-only communication
  purpose = "cluster"
}

# Enable UI for administration
ui = true

# Production TTL settings - shorter for security
default_lease_ttl = "24h"   # 24 hours instead of 168h
max_lease_ttl     = "168h"  # 7 days instead of 720h

# Enhanced audit logging for production
audit {
  enabled = true
  
  # File audit device
  file {
    file_path = "/openbao/logs/audit.log" 
    format    = "json"
    
    # Log request and response data (sanitized)
    log_raw             = false
    hmac_accessor       = true
    elide_list_responses = false
  }
  
  # Syslog audit device for centralized logging
  syslog {
    facility = "AUTH"
    tag      = "openbao"
    format   = "json"
  }
}

# Enhanced telemetry for production monitoring
telemetry {
  # Prometheus metrics
  prometheus_retention_time = "24h"
  disable_hostname         = false
  
  # StatsD metrics for additional monitoring
  statsd_address = "${STATSD_ADDRESS:-127.0.0.1:8125}"
  
  # Circonus integration (if used)
  circonus_api_token    = "${CIRCONUS_API_TOKEN}"
  circonus_api_app      = "openbao-dotmac"
  circonus_broker_id    = "${CIRCONUS_BROKER_ID}"
  circonus_submission_interval = "10s"
}

# Performance and security tuning
cache_size = 524288  # 512KB cache for production

# Disable mlock for containerized environments (if needed)
disable_mlock = false

# Enable raw storage endpoint (disable in high-security environments)
raw_storage_endpoint = false

# Plugin directory for custom authentication methods
plugin_directory = "/openbao/plugins"

# Enterprise features (if using OpenBao Enterprise)
license_path = "/openbao/license/license.hclic"

# Seal configuration for auto-unseal (AWS KMS example)
seal "awskms" {
  region     = "${AWS_REGION:-us-east-1}"
  kms_key_id = "${AWS_KMS_KEY_ID}"
  endpoint   = "${AWS_KMS_ENDPOINT}"
  
  # Optional: custom access credentials
  access_key = "${AWS_ACCESS_KEY_ID}"
  secret_key = "${AWS_SECRET_ACCESS_KEY}"
}

# Alternative: Azure Key Vault seal
# seal "azurekeyvault" {
#   tenant_id     = "${AZURE_TENANT_ID}"
#   client_id     = "${AZURE_CLIENT_ID}" 
#   client_secret = "${AZURE_CLIENT_SECRET}"
#   vault_name    = "${AZURE_VAULT_NAME}"
#   key_name      = "${AZURE_KEY_NAME}"
# }

# Log level for production
log_level = "INFO"
log_format = "json"

# Enable request forwarding for HA
enable_response_header_hostname = true
enable_response_header_raft_node_id = true