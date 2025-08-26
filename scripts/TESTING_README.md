# DotMac Framework Testing System

This directory contains a comprehensive testing and validation system for the DotMac Framework. The system ensures that all components are properly configured, can start successfully, and work together correctly.

## 🎯 Overview

The testing system addresses critical gaps that were identified in the deployment readiness process:

- **Docker configuration misalignments** - Fixed inconsistencies between compose files and Dockerfiles
- **Missing requirements-dev.txt files** - Added development dependencies for both platforms
- **Import validation** - Comprehensive testing that all modules can be imported successfully
- **Health check endpoints** - Validated and fixed health check endpoints for containers
- **Environment variable validation** - Ensures all required environment variables are properly configured
- **Container smoke tests** - End-to-end testing of containerized applications
- **GitHub Actions workflow dependencies** - Fixed CI/CD pipeline to use the new testing system
- **Database migration validation** - End-to-end validation of all database migrations

## 🛠️ Testing Scripts

### Core Validation Scripts

#### 1. `validate_environment.py`
**Purpose**: Validates all required environment variables are properly configured.

**What it checks**:
- Required passwords and secrets (minimum length requirements)
- Database connection strings (format validation)
- Redis URLs and connection strings
- OpenBao/Vault tokens
- External service API keys (Stripe, SendGrid)
- CORS origins configuration
- SSL certificates (for production)
- Docker-specific environment variables

**Usage**:
```bash
python3 scripts/validate_environment.py
```

**Features**:
- Generates `.env.template` file if many variables are missing
- Validates production-specific security requirements
- Warns about insecure defaults in production environment

#### 2. `validate_imports.py`
**Purpose**: Validates that all critical components can be imported successfully.

**What it checks**:
- ISP Framework core modules (app, settings, database, API routing)
- Management Platform core modules (app factory, configuration)
- Module imports (identity, billing, services, analytics)
- SDK imports (platform SDKs, networking SDKs)
- Shared component imports
- Docker entry point compatibility

**Usage**:
```bash
python3 scripts/validate_imports.py
```

**Features**:
- Tests both applications can be imported without errors
- Validates Docker entry points work correctly
- Provides detailed error reporting for failed imports

#### 3. `validate_migrations.py`
**Purpose**: Validates database migrations are consistent and can be applied successfully.

**What it checks**:
- Migration file structure and naming conventions
- Migration syntax validation (Python compilation)
- SQLite-based migration testing (doesn't require PostgreSQL)
- Rollback capability testing
- Cross-platform migration consistency

**Usage**:
```bash
python3 scripts/validate_migrations.py
```

**Features**:
- Uses SQLite for testing (no database server required)
- Tests both upgrade and downgrade operations
- Validates migration file naming conventions

#### 4. `container_smoke_tests.py`
**Purpose**: End-to-end testing of containerized applications.

**What it checks**:
- Docker network creation and isolation
- PostgreSQL container startup and health
- Redis container startup and health
- ISP Framework container build and startup
- Management Platform container build and startup
- Health endpoint accessibility
- Container cleanup and resource management

**Usage**:
```bash
python3 scripts/container_smoke_tests.py
```

**Features**:
- Creates isolated test network
- Builds containers from source
- Tests actual HTTP endpoints
- Comprehensive cleanup after testing

### Orchestration Script

#### `run_all_tests.py`
**Purpose**: Runs all validation scripts in the correct order and provides comprehensive reporting.

**Usage**:
```bash
python3 scripts/run_all_tests.py
```

**Features**:
- Runs tests in optimal order (fast tests first)
- Provides real-time output from all tests
- Comprehensive summary with success rates
- Handles both synchronous and asynchronous test execution
- Graceful handling of Docker unavailability

## 🐳 Docker Improvements

### Fixed Issues:
1. **Health check endpoints**: Updated Dockerfiles to use correct `/health` endpoints
2. **Entry point alignment**: Fixed container entry points to match actual application structure
3. **Requirements files**: Added missing `requirements-dev.txt` for both platforms
4. **Port consistency**: Aligned port configurations between Docker compose and applications

### Key Changes:
- ISP Framework Dockerfile now correctly references `dotmac_isp.app:app`
- Management Platform Dockerfile uses the proper `run_server.py` entry point
- Health checks properly target `/health` endpoints in both containers

## 🚀 CI/CD Integration

### GitHub Actions Workflow (`ai-first-deployment-ready.yml`)

**Fixed Issues**:
1. Removed dependency on missing Makefile
2. Updated dependency installation to handle both platforms
3. Integrated custom validation scripts
4. Added graceful frontend handling (optional)
5. Fixed artifact upload paths

**Workflow Structure**:
- **Environment Setup**: Python, dependencies, services (PostgreSQL, Redis)
- **Deployment Readiness Check**: Runs validation scripts to ensure deployability
- **Legacy Tests**: Runs additional tests if validation passes
- **Frontend Tests**: Optional frontend build and test (if present)
- **Branch Protection**: Prevents merging if critical tests fail

## 📊 Success Metrics

The testing system provides detailed metrics:

- **Import Success Rate**: Percentage of modules that can be imported successfully
- **Environment Validation**: Number of required variables properly configured
- **Migration Success**: Ability to apply and rollback database migrations
- **Container Readiness**: Ability to build, start, and respond to health checks

## 🎯 Usage Guidelines

### For Development:
```bash
# Quick validation (recommended before commits)
python3 scripts/validate_environment.py
python3 scripts/validate_imports.py

# Full validation suite
python3 scripts/run_all_tests.py
```

### For CI/CD:
The GitHub Actions workflow automatically runs the validation suite on:
- Push to `main` or `develop` branches
- Pull requests targeting `main` or `develop`

### For Production Deployment:
```bash
# Ensure production environment is ready
ENVIRONMENT=production python3 scripts/validate_environment.py

# Full production readiness check
python3 scripts/run_all_tests.py
```

## 🔧 Troubleshooting

### Common Issues:

1. **Import Failures**:
   - Check Python path configuration
   - Verify all dependencies are installed
   - Check for circular import dependencies

2. **Environment Variable Issues**:
   - Use generated `.env.template` as a starting point
   - Ensure all required secrets have minimum length requirements
   - Check for typos in variable names

3. **Container Tests Failing**:
   - Ensure Docker is running
   - Check available disk space
   - Verify port availability (5432, 6379, 8000, 8001)

4. **Migration Issues**:
   - Check Alembic configuration files
   - Verify database connection strings
   - Check for syntax errors in migration files

## 🚀 Future Enhancements

Potential improvements to the testing system:

1. **Performance Testing**: Add load testing capabilities
2. **Security Testing**: Integrate security vulnerability scanning
3. **Integration Testing**: More comprehensive API endpoint testing
4. **Monitoring Integration**: Connect with observability systems
5. **Deployment Testing**: Test actual deployment scenarios

## 📝 Contributing

When adding new components to the framework:

1. Update relevant validation scripts to include new modules
2. Add environment variable validation for new configuration
3. Include new database tables in migration validation
4. Update container tests for new endpoints
5. Document any new testing requirements

---

This testing system ensures the DotMac Framework maintains high quality and deployment readiness throughout its development lifecycle.