# User Management System

Production-ready, comprehensive user management system for DotMac Framework built with DRY principles, Pydantic 2, and Poetry.

## Overview

This system provides unified user management across ISP and Management platforms with:
- **Complete data layer** with optimized SQLAlchemy models  
- **Pydantic 2 validation** with comprehensive business rules
- **DRY service layer** leveraging existing shared systems
- **RouterFactory integration** for consistent APIs
- **Multi-tenant support** with proper isolation
- **Production security** features and audit trails

## Architecture

```
user_management/
├── models/           # SQLAlchemy models with relationships
├── schemas/          # Pydantic 2 schemas with validation
├── repositories/     # Data access layer with DRY patterns  
├── services/         # Business logic and workflows
├── api/              # FastAPI routers using RouterFactory
└── tests/            # Comprehensive test suite
```

## Key Features

### 🔐 Authentication & Security
- Password strength validation with configurable policies
- Multi-factor authentication (TOTP, SMS, Email)
- Session management with device fingerprinting
- Account lockout and rate limiting
- Password history and expiry management
- API key management for programmatic access

### 👤 User Management  
- Comprehensive user profiles with contact information
- Role-based access control (RBAC) with fine-grained permissions
- User lifecycle management (registration → activation → deactivation)
- Bulk operations for administrative tasks
- Advanced search and filtering capabilities
- User invitation and onboarding workflows

### 🏢 Multi-tenant Support
- Tenant isolation at data and service layers
- Configurable user types per platform
- Tenant-specific preferences and settings
- Cross-tenant user management for platform admins

### 📊 Audit & Compliance
- Comprehensive audit trails for all user actions
- GDPR-compliant data management
- Legal compliance tracking (terms, privacy)
- Security event logging and monitoring

## Database Schema

### Core Tables
- **users_v2**: Primary user data with comprehensive fields
- **user_profiles_v2**: Extended profile information  
- **user_contact_info_v2**: Contact and address data
- **user_preferences_v2**: UI and notification preferences

### Authentication Tables
- **user_passwords_v2**: Secure password management
- **password_history_v2**: Password reuse prevention
- **user_sessions_v2**: Session tracking with metadata
- **user_mfa_v2**: Multi-factor authentication settings
- **user_api_keys_v2**: API key management
- **auth_audit_v2**: Authentication event logging

## Usage Examples

### Creating Users

```python
from dotmac_management.user_management.services import UserService
from dotmac_management.user_management.schemas import UserCreateSchema, UserType

# Create user service
user_service = UserService(db_session, tenant_id)

# Create user
user_data = UserCreateSchema(
    username="johndoe",
    email="john@example.com", 
    first_name="John",
    last_name="Doe",
    user_type=UserType.CUSTOMER,
    password="SecurePass123!",
    terms_accepted=True,
    privacy_accepted=True
)

user = await user_service.create_user(user_data)
```

### User Authentication

```python
from dotmac_management.user_management.services import AuthService

auth_service = AuthService(db_session, tenant_id)

# Authenticate user
login_result = await auth_service.authenticate_user(
    username="johndoe",
    password="SecurePass123!",
    client_ip="192.168.1.100"
)

if login_result.success:
    # User authenticated successfully
    access_token = login_result.access_token
    session_id = login_result.session_id
```

### User Search

```python  
from dotmac_management.user_management.schemas import UserSearchSchema, UserType

# Search users with filters
search_params = UserSearchSchema(
    query="john",
    user_type=UserType.CUSTOMER,
    is_active=True,
    page=1,
    page_size=20
)

users, total_count = await user_service.search_users(search_params)
```

### API Endpoints

The system provides RESTful APIs using RouterFactory:

```python
# Include routers in your FastAPI app
from dotmac_management.user_management.api import user_router, auth_router

app.include_router(user_router, prefix="/api/v2")
app.include_router(auth_router, prefix="/api/v2")
```

#### Available Endpoints:

**User Management:**
- `GET /users/me` - Get current user profile
- `PUT /users/me` - Update current user profile  
- `POST /users` - Create new user (admin only)
- `GET /users/{user_id}` - Get user by ID
- `PUT /users/{user_id}` - Update user
- `POST /users/search` - Search users with filters
- `POST /users/bulk-operation` - Bulk operations

**User Status:**
- `POST /users/{user_id}/activate` - Activate user
- `POST /users/{user_id}/deactivate` - Deactivate user
- `POST /users/{user_id}/suspend` - Suspend user

**Authentication:**
- `POST /auth/login` - User login
- `POST /auth/logout` - User logout
- `POST /auth/refresh` - Refresh token
- `POST /auth/password/change` - Change password
- `POST /auth/mfa/setup` - Setup MFA

## Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/dotmac

# Authentication
JWT_SECRET=your-super-secret-jwt-key
JWT_EXPIRY_HOURS=24

# Security  
PASSWORD_MIN_LENGTH=8
ACCOUNT_LOCKOUT_ATTEMPTS=5
SESSION_TIMEOUT_MINUTES=480

# Multi-factor Authentication
MFA_ISSUER=DotMac
MFA_BACKUP_CODES_COUNT=10
```

### Security Configuration

```python
# Configure password policy
SECURITY_CONFIG = {
    "password_policy": {
        "min_length": 8,
        "require_uppercase": True,
        "require_lowercase": True, 
        "require_numbers": True,
        "require_symbols": True,
        "max_age_days": 90,
        "history_count": 5,
    },
    "login_policy": {
        "max_failed_attempts": 5,
        "lockout_duration_minutes": 30,
        "session_timeout_minutes": 480,
        "require_mfa_for_admin": True,
    }
}
```

## Testing

Run the comprehensive test suite:

```bash
# Unit tests
poetry run pytest tests/unit/user_management/

# Integration tests
poetry run pytest tests/integration/user_management/

# All tests with coverage
poetry run pytest --cov=dotmac_shared.user_management
```

## Migration

Apply database migrations:

```bash
# Run migrations
alembic upgrade head

# Create new migration  
alembic revision --autogenerate -m "Add user management v2"
```

## Performance Considerations

### Database Optimizations
- Comprehensive indexing strategy for search performance
- Separate tables for profile data to optimize core user queries
- JSON columns for flexible metadata storage
- Connection pooling and query optimization

### Caching Strategy
- User profile caching with Redis
- Session data caching for quick validation
- Permission caching for authorization checks

### Monitoring & Observability
- Structured logging with correlation IDs
- Metrics for authentication and user operations
- Health checks for service dependencies
- Performance monitoring for database queries

## Security Features

### Password Security
- Bcrypt hashing with configurable rounds
- Password strength validation
- Password history prevention (last 5 passwords)
- Automatic password expiry
- Secure password reset workflows

### Session Management
- JWT tokens with proper expiry
- Session fingerprinting for security
- Geographic login tracking
- Suspicious activity detection
- Device trust management

### Data Protection
- Field-level encryption for sensitive data
- GDPR-compliant data deletion
- Audit trails for all user actions
- Rate limiting and abuse prevention

## Production Deployment

### Requirements
- Python 3.9+
- PostgreSQL 13+
- Redis 6+ (for caching)
- Poetry for dependency management

### Deployment Steps

1. **Install dependencies:**
   ```bash
   poetry install --only=main
   ```

2. **Run database migrations:**
   ```bash
   alembic upgrade head
   ```

3. **Configure environment:**
   ```bash
   export DATABASE_URL="postgresql+asyncpg://..."
   export JWT_SECRET="your-secret-key"
   export REDIS_URL="redis://localhost:6379"
   ```

4. **Start the application:**
   ```bash
   poetry run uvicorn main:app --host 0.0.0.0 --port 8000
   ```

### Production Checklist

- [ ] Database connection pooling configured
- [ ] Redis caching enabled
- [ ] JWT secrets properly configured
- [ ] HTTPS enabled for all endpoints
- [ ] Rate limiting configured
- [ ] Monitoring and logging set up
- [ ] Backup and recovery procedures tested
- [ ] Security scanning completed

## Contributing

1. Follow the existing DRY patterns and RouterFactory usage
2. Add comprehensive tests for new functionality
3. Update documentation for any API changes
4. Follow Pydantic 2 best practices for schemas
5. Ensure proper error handling and logging

## License

This is proprietary software for DotMac Framework. All rights reserved.