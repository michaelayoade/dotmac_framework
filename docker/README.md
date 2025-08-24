# Docker Configuration Guide

## Docker Compose Files Structure

### Main Deployment Files
- **`docker-compose.yml`** - Complete platform development environment
- **`docker-compose.production.yml`** - Production deployment configuration
- **`docker-compose.unified.yml`** - Unified platform with all services

### Platform-Specific Files
- **`isp-framework/docker-compose.yml`** - ISP Framework only
- **`management-platform/docker-compose.yml`** - Management Platform only

### Testing Files
- **`docker/testing/`** - Test-specific Docker configurations
  - `docker-compose.test.yml` - Full test environment
  - `docker-compose.test.simple.yml` - Minimal test setup

## Usage

### Development Environment
```bash
# Start complete platform
docker-compose up -d

# Start specific platform
cd isp-framework && docker-compose up -d
cd management-platform && docker-compose up -d
```

### Production Deployment
```bash
# Production deployment
docker-compose -f docker-compose.production.yml up -d
```

### Testing
```bash
# Run tests
docker-compose -f docker/testing/docker-compose.test.yml up --build
```

## Security Note
- All production configurations use environment variables
- No secrets are hardcoded in compose files
- SSL certificates are externally managed