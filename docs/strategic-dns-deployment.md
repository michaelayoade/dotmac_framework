# Strategic DNS Deployment Guide

## Overview

The DotMac platform now uses a **plugin-based DNS architecture** that automatically detects and leverages your existing infrastructure. No hardcoded integrations - fully extensible and strategic.

## 🎯 Strategic Approach

### What We Removed
- ❌ Hardcoded Cloudflare dependency
- ❌ Proprietary service lock-in
- ❌ Single-point-of-failure DNS

### What We Added
✅ **Plugin-based architecture** - extend with any DNS provider
✅ **Auto-detection** - uses your existing infrastructure
✅ **Multiple fallback options** - from production BIND9 to development hosts file
✅ **Zero external dependencies** - works entirely with local systems

## 🏗️ Deployment Strategies

### Strategy 1: Leverage Existing BIND9 (Recommended for Production)

If you have an existing BIND9 server (common in enterprise/ISP environments):

```bash
# The system will auto-detect BIND9 and use it
DNS_STRATEGY=auto
BIND9_ZONE_DIR=/etc/bind/zones
BIND9_RELOAD_COMMAND="rndc reload"
```

**Advantages:**
- Uses your existing DNS infrastructure
- Full control and customization
- Production-ready scalability
- Integration with existing network policies

### Strategy 2: Router/Firewall DNS Integration

Many routers (pfSense, OPNsense, enterprise firewalls) have built-in DNS:

```bash
DNS_STRATEGY=auto
ROUTER_DNS_ENABLED=true
ROUTER_DNS_API_URL=https://your-router.local/api
```

**Advantages:**
- Leverages existing network equipment
- No additional servers required
- Integrated with firewall rules
- Centralized network management

### Strategy 3: Docker Internal DNS (Easiest)

For containerized deployments:

```bash
DNS_STRATEGY=auto
DOCKER_DNS_ENABLED=true
DOCKER_DNS_BRIDGE_IP=172.20.0.1
```

**Advantages:**
- Zero configuration required
- Works with existing Docker setup
- Perfect for development and testing
- Automatic container networking

### Strategy 4: System DNS Services

Uses whatever DNS service is running on your system:

```bash
DNS_STRATEGY=auto
# Will detect: systemd-resolved, dnsmasq, etc.
```

**Advantages:**
- Uses built-in system services
- No additional software needed
- Works on most Linux distributions
- Minimal resource usage

### Strategy 5: Development Mode

For development and testing:

```bash
DEPLOYMENT_MODE=development
DNS_STRATEGY=hosts-file
```

**Advantages:**
- No root privileges required
- Works on any system
- Perfect for development
- Easy to clean up

## 📋 Quick Setup

### 1. Choose Your Strategy

```bash
# Copy configuration template
cp .env.example .env

# Edit with your preferred strategy
nano .env
```

### 2. Set Your Domain

```bash
# Your main domain (tenants get subdomains)
BASE_DOMAIN=yourdomain.com

# Where your load balancer/server is
LOAD_BALANCER_IP=your.server.ip
```

### 3. Let the System Auto-Detect

The plugin will automatically:

1. **Scan for BIND9** - checks for `named` command and zones directory
2. **Detect dnsmasq** - common on routers and embedded systems  
3. **Find systemd-resolved** - default on Ubuntu/Debian
4. **Check Docker DNS** - if running in containers
5. **Fall back to hosts file** - always available for development

### 4. Test the Setup

```bash
# Test DNS automation
./scripts/test-domain-automation.sh test-dns

# Deploy a test tenant
./scripts/test-domain-automation.sh deploy test-tenant
```

## 🔧 Configuration Examples

### Production BIND9 Setup

```env
# Production configuration
DEPLOYMENT_MODE=production
BASE_DOMAIN=yourisp.net
LOAD_BALANCER_IP=10.0.1.100

# BIND9 settings
BIND9_ZONE_DIR=/etc/bind/zones
BIND9_CONFIG_DIR=/etc/bind
DNS_AUTO_BACKUP=true
```

### Router Integration (pfSense)

```env
# Router DNS integration
DEPLOYMENT_MODE=production
ROUTER_DNS_ENABLED=true
ROUTER_DNS_API_URL=https://192.168.1.1/api
ROUTER_DNS_API_KEY=your-pfsense-api-key
```

### Docker Development

```env
# Docker development
DEPLOYMENT_MODE=development
DOCKER_DNS_ENABLED=true
BASE_DOMAIN=local.test
LOAD_BALANCER_IP=127.0.0.1
```

### Hybrid Multi-DNS

```env
# Use multiple DNS providers for redundancy
MULTI_DNS_ENABLED=true
PRIMARY_DNS_PROVIDER=bind9
SECONDARY_DNS_PROVIDER=router-dns
```

## 🚀 Advanced Features

### Plugin Extensions

Create custom DNS providers:

```python
# plugins/dns/custom_provider.py
from dotmac_isp.plugins.core.dns_plugin_base import DNSPlugin

class CustomDNSProvider(DNSPlugin):
    async def create_tenant_records(self, setup, context):
        # Your custom DNS logic here
        return {"success": True}
```

### Multi-Provider Redundancy

```env
MULTI_DNS_ENABLED=true
PRIMARY_DNS_PROVIDER=bind9
SECONDARY_DNS_PROVIDER=hosts-file
TERTIARY_DNS_PROVIDER=docker-dns
```

### Geographic DNS

```env
GEO_DNS_ENABLED=true
GEO_DNS_REGIONS=us-east,us-west,eu-central
```

## 🔍 Monitoring and Health Checks

### Built-in Health Monitoring

```bash
# Check DNS system status
curl http://localhost:8000/api/v1/dns/status

# Check specific tenant DNS health
curl http://localhost:8000/api/v1/dns/health/tenant-123
```

### Observability (SigNoz)

```env
DNS_METRICS_ENABLED=true
# Metrics are exported via OTLP to SigNoz (no /metrics scraping)
```

### Logging and Debugging

```env
# Enable detailed DNS logging
DNS_DEBUG_LOGGING=true

# Test mode (doesn't make actual changes)
DNS_TEST_MODE=true

# Dry run mode
DNS_DRY_RUN=true
```

## 🛠️ Troubleshooting

### Common Issues

1. **"No DNS provider available"**
   ```bash
   # Check what's available on your system
   which named dnsmasq systemctl
   
   # Force a specific provider
   DNS_STRATEGY=hosts-file
   ```

2. **Permission denied errors**
   ```bash
   # For BIND9 management
   sudo usermod -a -G bind dotmac-user
   
   # For hosts file access
   sudo chown dotmac-user /etc/hosts
   ```

3. **DNS records not resolving**
   ```bash
   # Check if records were created
   dig tenant-123.yourdomain.com
   
   # Check plugin status
   curl http://localhost:8000/api/v1/dns/status
   ```

### Debug Mode

```env
# Enable comprehensive debugging
DEBUG=true
DNS_DEBUG_LOGGING=true
PLUGIN_DEBUG_MODE=true
LOG_LEVEL=DEBUG
```

## 🎉 Benefits of This Approach

### For ISPs/Enterprises
- **Leverages existing infrastructure** - no new servers needed
- **Vendor-neutral** - not locked into any specific service
- **Scalable** - works with your existing DNS architecture
- **Secure** - stays within your network perimeter

### For Developers
- **No external dependencies** - works offline
- **Multiple fallback options** - always works somehow
- **Plugin extensible** - add any DNS provider
- **Easy testing** - dry-run and test modes

### For Operations
- **Auto-detection** - minimal configuration required
- **Health monitoring** - built-in status checks
- **Backup and recovery** - automatic DNS config backups
- **Multi-provider redundancy** - fault tolerance

## Next Steps

1. **Choose your deployment strategy** based on existing infrastructure
2. **Configure .env file** with your domain and settings
3. **Test with a development tenant** using the test scripts
4. **Deploy to production** with monitoring enabled
5. **Extend with custom plugins** as needed

This strategic approach ensures you're never locked into any specific DNS provider while maximizing use of your existing infrastructure!
