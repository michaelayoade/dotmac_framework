pid_file = "/tmp/pidfile"

vault {
  address = "http://openbao:8200"
}

auto_auth {
  method "approle" {
    mount_path = "auth/approle"
    config = {
      role_id_file_path = "/vault/config/role_id"
      secret_id_file_path = "/vault/config/secret_id"
    }
  }

  sink "file" {
    config = {
      path = "/tmp/vault-token"
    }
  }
}

template {
  source      = "/vault/templates/clickhouse_user.tpl"
  destination = "/secrets/ch_user"
  perms       = 0600
}

template {
  source      = "/vault/templates/clickhouse_password.tpl"
  destination = "/secrets/ch_pass"
  perms       = 0600
}

template {
  source      = "/vault/templates/clickhouse_dsn.tpl"
  destination = "/secrets/clickhouse_dsn"
  perms       = 0600
}

template {
  source      = "/vault/templates/database_url.tpl"
  destination = "/secrets/isp_database_url"
  perms       = 0600
}

template {
  source      = "/vault/templates/redis_url.tpl"
  destination = "/secrets/isp_redis_url"
  perms       = 0600
}