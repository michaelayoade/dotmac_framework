# Strategic Dependency Consolidation Plan

## Current State Problems

### Duplicate Files (9 → 3)
```
BEFORE:
├── requirements.txt                           # Root level  
├── docs/requirements.txt                      # Documentation
├── docs/requirements-full.txt                 # Documentation (duplicate)
├── isp-framework/requirements.txt             # ISP Framework
├── isp-framework/requirements-dev.txt         # Dev tools (duplicate)
├── isp-framework/requirements-test.txt        # Test tools (duplicate)
├── isp-framework/requirements-ai.txt          # AI tools (duplicate)
├── management-platform/requirements.txt      # Management Platform
└── templates/*/requirements.txt               # Template dependencies

AFTER:
├── requirements.txt                           # Shared dependencies
├── isp-framework/requirements.txt             # ISP-specific only
├── management-platform/requirements.txt      # Management-specific only
└── docs/requirements.txt                      # Docs-specific only
```

## Strategic Consolidation by Dependency Type

### Shared Infrastructure Dependencies
```python
# requirements.txt (ROOT LEVEL)
# Shared across ALL components
fastapi==0.104.1                 # Web framework (standardized version)
uvicorn[standard]==0.24.0         # ASGI server
pydantic[email]==2.5.0            # Data validation
sqlalchemy[asyncio]==2.0.23       # ORM
asyncpg==0.29.0                   # PostgreSQL driver
redis[hiredis]>=4.5.2,<5.0.0     # Caching
structlog==23.2.0                 # Logging
httpx==0.25.2                     # HTTP client
cryptography>=41.0.7              # Security
python-dotenv==1.0.0              # Configuration
```

### Component-Specific Dependencies
```python
# isp-framework/requirements.txt
# EXTENDS root requirements.txt via: -r ../requirements.txt
-r ../requirements.txt

# ISP Framework specific
celery[redis]==5.3.4              # Background jobs
alembic==1.13.1                   # Database migrations
passlib[bcrypt]==1.7.4            # Authentication
python-jose[cryptography]==3.3.0  # JWT tokens
```

```python
# management-platform/requirements.txt  
# EXTENDS root requirements.txt
-r ../requirements.txt

# Management Platform specific
kubernetes==28.1.0                # Container orchestration
opentelemetry-api==1.22.0        # Observability
prometheus-client==0.19.0         # Metrics
```

```python
# docs/requirements.txt
# EXTENDS root requirements.txt for better docs
-r ../requirements.txt

# Documentation specific
sphinx==7.2.6                     # Documentation generator
sphinx-rtd-theme==2.0.0          # Theme
myst-parser==2.0.0                # Markdown support
```

## Version Conflict Resolution Strategy

### Current Conflicts → Resolutions
```yaml
Version Conflicts Fixed:
  fastapi: ['0.104.1', '0.109.0'] → '0.104.1'  # Use stable LTS
  uvicorn: ['0.25.0', '0.24.0'] → '0.24.0'      # Match FastAPI compatibility
  pydantic: ['2.5.3', '2.5.0'] → '2.5.0'       # Use stable version
  sqlalchemy: ['2.0.23', '2.0.25'] → '2.0.23'  # Match Alembic compatibility
  redis: ['>=4.5.2,<5.0.0', '5.0.1'] → '>=4.5.2,<5.0.0'  # Avoid breaking changes
  httpx: ['0.25.2', '0.26.0'] → '0.25.2'       # Use stable version
  pytest: ['7.4.4', '7.4.3'] → '7.4.3'         # Use stable version
```

### Dependency Pinning Strategy
```yaml
Pinning Rules:
  Core Infrastructure: Pin exact versions (security/stability)
  Development Tools: Pin to stable versions  
  Documentation: Allow minor version updates
  Testing: Pin to avoid CI/CD inconsistencies
  Optional/Plugin: Use version ranges for flexibility
```