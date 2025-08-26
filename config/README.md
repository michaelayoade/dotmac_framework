# Configuration Management

## Directory Structure

```
config/
├── shared/           # Shared configurations across platforms
│   ├── openbao.hcl  # OpenBao configuration
│   ├── redis.conf   # Redis configuration
│   └── nginx.conf   # Nginx configuration
├── development/     # Development-specific configs
├── staging/         # Staging environment configs
└── production/      # Production environment configs
```

## Configuration Sources

### Platform-Specific Configurations
- **ISP Framework**: `/home/dotmac_framework/isp-framework/config/`
- **Management Platform**: `/home/dotmac_framework/management-platform/config/`

### Shared Infrastructure Configurations
- **Shared Configs**: `/home/dotmac_framework/config/shared/`
- **Deployment Configs**: `/home/dotmac_framework/shared/deployments/`

## Usage

### Development
```bash
# Use shared configurations for development
export CONFIG_PATH=/home/dotmac_framework/config/shared
```

### Production
```bash
# Production configs should use environment variables
export OPENBAO_CONFIG=/home/dotmac_framework/config/shared/openbao.hcl
```

## Security Guidelines

1. **Never commit secrets** to configuration files
2. **Use environment variables** for sensitive data
3. **Use external secret management** for production
4. **Validate configurations** before deployment

## Migration from Old Structure

Old duplicate configurations have been consolidated:
- ✅ OpenBao configs: 3 files → 1 unified file
- ✅ Docker compose: 9 files → 6 organized files
- ✅ Test environments: Multiple → Single testing directory