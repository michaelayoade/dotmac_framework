# Allow reading ClickHouse credentials
path "dotmac/clickhouse" {
  capabilities = ["read"]
}

# Allow reading ISP database/redis credentials  
path "dotmac/isp" {
  capabilities = ["read"]
}