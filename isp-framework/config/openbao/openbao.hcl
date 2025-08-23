# OpenBao Configuration for DotMac ISP Framework

# Storage backend - using file storage for development
storage "file" {
  path = "/openbao/data"
}

# Listener configuration
listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = 1
}

# API address
api_addr = "http://0.0.0.0:8200"
cluster_addr = "http://0.0.0.0:8201"

# Disable mlock for development
disable_mlock = true

# Enable UI
ui = true

# Log level
log_level = "Info"

# Default lease TTL
default_lease_ttl = "168h"
max_lease_ttl = "720h"