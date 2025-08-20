# OpenTofu & OpenBao Migration Guide

## Overview
This guide documents the migration from HashiCorp Terraform/Vault to OpenTofu/OpenBao for the DotMac Framework.

## OpenTofu Migration

### Installation

#### macOS
```bash
brew install opentofu
```

#### Linux
```bash
curl -Lo tofu.tar.gz https://github.com/opentofu/opentofu/releases/download/v1.6.0/tofu_1.6.0_linux_amd64.tar.gz
tar -xzf tofu.tar.gz
sudo mv tofu /usr/local/bin/
```

#### Windows
```powershell
choco install opentofu
```

### Migration Steps

1. **Install OpenTofu** (see above)

2. **Navigate to Terraform directory**
```bash
cd deployments/terraform
```

3. **Initialize with OpenTofu**
```bash
tofu init
```

4. **Import existing state** (if migrating from existing Terraform deployment)
```bash
# Backup existing state first
cp terraform.tfstate terraform.tfstate.backup

# Use OpenTofu with existing state
tofu plan
```

5. **Apply infrastructure**
```bash
tofu apply -var-file="production.tfvars"
```

### Key Differences from Terraform
- **Command**: Use `tofu` instead of `terraform`
- **State**: Fully compatible with Terraform state files
- **Providers**: All HashiCorp providers work with OpenTofu
- **License**: OpenTofu is MPL-2.0 licensed (open source)

## OpenBao Migration

### Installation & Setup

1. **Start OpenBao with Docker Compose**
```bash
cd deployments/openbao
docker-compose up -d
```

2. **Initialize OpenBao** (automatically done by init container)
The initialization script will:
- Enable KV v2 secrets engine
- Enable Transit engine for encryption
- Enable AppRole authentication
- Create initial secrets structure
- Set up policies

3. **Access OpenBao UI**
- URL: http://localhost:8200
- Token: Check docker logs or use `root-token-for-dev` in development

### Migration from HashiCorp Vault

#### 1. Export existing secrets from Vault
```bash
# Export from HashiCorp Vault
vault kv get -format=json secret/dotmac > dotmac-secrets.json
```

#### 2. Import to OpenBao
```bash
# Set OpenBao address
export BAO_ADDR=http://localhost:8200
export BAO_TOKEN=root-token-for-dev

# Import secrets
bao kv put secret/dotmac @dotmac-secrets.json
```

#### 3. Update application configuration
Update your `.env` files:
```env
# Old (HashiCorp Vault)
VAULT_ADDR=https://vault.hashicorp.com
VAULT_TOKEN=hvs.xxxxx

# New (OpenBao)
VAULT_ADDR=http://localhost:8200
VAULT_TOKEN=root-token-for-dev
# The Python client is API-compatible, no code changes needed
```

### Python Client Compatibility

The existing `vault_client.py` is **fully compatible** with OpenBao. No code changes required!

OpenBao maintains API compatibility with HashiCorp Vault, so the `hvac` Python library works seamlessly.

## Production Deployment

### OpenTofu Production Setup

1. **Configure backend for state storage**
```hcl
# backend.tf
terraform {
  backend "s3" {
    bucket = "dotmac-terraform-state"
    key    = "production/terraform.tfstate"
    region = "us-east-1"
    encrypt = true
    dynamodb_table = "terraform-state-lock"
  }
}
```

2. **Run OpenTofu in CI/CD**
```yaml
# .github/workflows/infrastructure.yml
- name: Setup OpenTofu
  uses: opentofu/setup-opentofu@v1
  with:
    tofu_version: 1.6.0

- name: OpenTofu Init
  run: tofu init

- name: OpenTofu Apply
  run: tofu apply -auto-approve
```

### OpenBao Production Setup

1. **Deploy on Kubernetes**
```bash
kubectl apply -f deployments/openbao/kubernetes/
```

2. **Configure auto-unseal with AWS KMS**
```hcl
seal "awskms" {
  region     = "us-east-1"
  kms_key_id = "arn:aws:kms:us-east-1:xxx:key/xxx"
}
```

3. **Enable high availability**
```hcl
storage "raft" {
  path = "/openbao/data"
  node_id = "node1"
  
  retry_join {
    leader_api_addr = "http://openbao-0.openbao-internal:8200"
  }
  retry_join {
    leader_api_addr = "http://openbao-1.openbao-internal:8200"
  }
  retry_join {
    leader_api_addr = "http://openbao-2.openbao-internal:8200"
  }
}
```

## Rollback Plan

If you need to rollback to HashiCorp tools:

### Rollback to Terraform
```bash
# OpenTofu state is compatible with Terraform
terraform init
terraform plan
# Verify no changes needed
terraform apply
```

### Rollback to HashiCorp Vault
```bash
# Export from OpenBao
bao kv get -format=json secret/dotmac > backup.json

# Import to HashiCorp Vault
vault kv put secret/dotmac @backup.json

# Update .env files with Vault address and token
```

## Benefits of Migration

### OpenTofu Benefits
- ✅ **Open Source**: MPL-2.0 license, no BSL restrictions
- ✅ **Community Driven**: Governed by Linux Foundation
- ✅ **Drop-in Compatible**: Works with existing Terraform code
- ✅ **Active Development**: Regular releases and improvements

### OpenBao Benefits
- ✅ **Open Source**: MPL-2.0 license
- ✅ **API Compatible**: Works with existing Vault clients
- ✅ **No Vendor Lock-in**: Community-driven development
- ✅ **Cost Effective**: No enterprise license fees

## Support & Resources

- **OpenTofu Documentation**: https://opentofu.org/docs
- **OpenBao Documentation**: https://openbao.org/docs
- **Migration Support**: Check `deployments/scripts/migrate-to-opentofu.sh`
- **Community**: Join OpenTofu/OpenBao Slack channels

## Verification Checklist

- [ ] OpenTofu installed and working
- [ ] Infrastructure state migrated successfully
- [ ] OpenBao deployed and accessible
- [ ] Secrets migrated from Vault to OpenBao
- [ ] Applications can authenticate with OpenBao
- [ ] Encryption/decryption working via Transit engine
- [ ] Backup and recovery procedures tested
- [ ] Monitoring and alerting configured
- [ ] Documentation updated for team