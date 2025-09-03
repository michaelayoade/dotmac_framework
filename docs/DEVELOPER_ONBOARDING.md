# DotMac Platform Developer Onboarding Guide

## Welcome to DotMac Development Team! 🚀

This guide will help you get started with developing on the DotMac platform. By the end of this guide, you'll have a fully functional development environment and understand the codebase structure.

## Quick Start (15 minutes)

### 1. Clone and Setup
```bash
# Clone the repository
git clone https://github.com/dotmac/platform.git
cd platform

# Run quick setup script
./scripts/dev_setup.sh

# Start development environment
docker-compose up -d
```

### 2. Verify Installation
```bash
# Check services
./scripts/health_check.sh

# Access the application
open http://localhost:3000  # Frontend
open http://localhost:8000/docs  # API Documentation
```

## Development Environment Setup

### Prerequisites Installation

#### macOS
```bash
# Install Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install python@3.11 node@20 postgresql@14 redis git

# Install Docker Desktop
brew install --cask docker
```

#### Ubuntu/Debian
```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install dependencies
sudo apt-get install -y \
  python3.11 python3-pip \
  nodejs npm \
  postgresql-14 postgresql-client-14 \
  redis-server \
  git curl wget

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
```

### IDE Setup

#### VS Code (Recommended)
```bash
# Install VS Code
# Download from https://code.visualstudio.com/

# Install recommended extensions
code --install-extension ms-python.python
code --install-extension ms-python.vscode-pylance
code --install-extension dbaeumer.vscode-eslint
code --install-extension esbenp.prettier-vscode
code --install-extension ms-azuretools.vscode-docker
code --install-extension eamodio.gitlens
```

#### PyCharm
- Download from https://www.jetbrains.com/pycharm/
- Open project root directory
- Configure Python interpreter: `venv/bin/python`
- Enable Django support in settings

## Project Structure

```
dotmac_framework/
├── isp-framework/           # Backend (FastAPI)
│   ├── src/
│   │   └── dotmac_isp/
│   │       ├── core/       # Core modules (auth, db, cache)
│   │       ├── api/        # API endpoints
│   │       ├── models/     # Database models
│   │       ├── services/   # Business logic
│   │       └── utils/      # Utilities
│   ├── tests/              # Backend tests
│   └── requirements.txt    # Python dependencies
│
├── frontend/               # Frontend (React + TypeScript)
│   ├── packages/
│   │   ├── web/           # Main web application
│   │   ├── headless/      # Headless UI components
│   │   └── shared/        # Shared utilities
│   ├── apps/              # Applications
│   └── package.json       # Node dependencies
│
├── kubernetes/            # Kubernetes manifests
├── scripts/              # Utility scripts
├── docs/                 # Documentation
└── docker-compose.yml    # Docker configuration
```

## Setting Up Development Environment

### Backend Setup

```bash
# Navigate to backend
cd isp-framework

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Setup environment variables
cp .env.example .env.development
# Edit .env.development with your settings

# Run database migrations
alembic upgrade head

# Seed development data
python scripts/seed_data.py

# Start development server
uvicorn dotmac_isp.main:app --reload --port 8000
```

### Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Setup environment variables
cp .env.example .env.local
# Edit .env.local with your settings

# Start development server
npm run dev

# Access at http://localhost:3000
```

### Database Setup

```bash
# Create development database
createdb dotmac_dev

# Run migrations
cd isp-framework
alembic upgrade head

# Connect to database
psql -d dotmac_dev

# Verify tables
\dt
```

## Development Workflow

### 1. Branch Strategy

```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Create bugfix branch
git checkout -b bugfix/issue-description

# Create hotfix branch
git checkout -b hotfix/critical-fix
```

### 2. Making Changes

#### Backend Development
```python
# 1. Create new endpoint in api/
# api/v1/customers.py
from fastapi import APIRouter, Depends
from typing import List

router = APIRouter()

@router.get("/customers", response_model=List[CustomerSchema])
async def list_customers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all customers for the tenant."""
    return await customer_service.list_customers(db, current_user.tenant_id)

# 2. Add business logic in services/
# services/customer_service.py
async def list_customers(db: Session, tenant_id: str):
    """Business logic for listing customers."""
    return db.query(Customer).filter(
        Customer.tenant_id == tenant_id
    ).all()

# 3. Add tests
# tests/test_customers.py
async def test_list_customers(client, auth_headers):
    response = await client.get("/api/v1/customers", headers=auth_headers)
    assert response.status_code == 200
```

#### Frontend Development
```typescript
// 1. Create new component
// components/CustomerList.tsx
import React from 'react';
import { useCustomers } from '../hooks/useCustomers';

export const CustomerList: React.FC = () => {
  const { customers, loading, error } = useCustomers();
  
  if (loading) return <Spinner />;
  if (error) return <ErrorMessage error={error} />;
  
  return (
    <div>
      {customers.map(customer => (
        <CustomerCard key={customer.id} customer={customer} />
      ))}
    </div>
  );
};

// 2. Create custom hook
// hooks/useCustomers.ts
import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';

export const useCustomers = () => {
  return useQuery({
    queryKey: ['customers'],
    queryFn: () => api.get('/customers')
  });
};
```

### 3. Testing

#### 🚀 NEW: AI-First Testing (REQUIRED)

**Critical**: Always run deployment readiness tests FIRST. These ensure your app will actually start and run correctly.

```bash
cd isp-framework

# 1. CRITICAL: Deployment Readiness Check (Must Pass First)
make -f Makefile.readiness deployment-ready
# This validates:
# ✅ App startup works in real environment  
# ✅ Database schema matches models exactly
# ✅ All imports succeed (not mocked)
# ✅ Performance baseline meets requirements

# 2. Traditional Tests (Only runs if deployment-ready passes)
make -f Makefile.readiness test-legacy

# 3. Development Workflow
make -f Makefile.readiness dev-ready  # Complete validation + coverage
```

**Why this matters**: Traditional tests can pass while your app fails to start. Our AI-first approach tests the **entire system** as it runs in production.

📖 **Read the full guide**: [AI-First Testing Strategy](AI_FIRST_TESTING_STRATEGY.md)

#### Legacy Testing Commands (Use after AI-first tests pass)
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=dotmac_isp --cov-report=html

# Run specific test
pytest tests/test_customers.py::test_list_customers

# Run with verbose output
pytest -v
```

#### Run Frontend Tests
```bash
cd frontend

# Run all tests
npm test

# Run with coverage
npm run test:coverage

# Run in watch mode
npm run test:watch

# Run E2E tests
npm run test:e2e
```

### 4. Code Quality

#### Linting and Formatting
```bash
# Backend
black .                  # Format Python code
flake8 .                # Lint Python code
mypy .                  # Type checking
bandit -r .             # Security checks

# Frontend
npm run lint            # ESLint
npm run format          # Prettier
npm run type-check      # TypeScript checking
```

#### Pre-commit Hooks
```bash
# Install pre-commit
pip install pre-commit

# Setup hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

### 5. Pre-Commit Validation (CRITICAL)

**🚨 NEVER commit without running deployment readiness tests first!**

```bash
# 1. ALWAYS run this before committing
make -f Makefile.readiness deployment-ready

# 2. If deployment-ready passes, then commit
git add .
git commit -m "feat: add customer list endpoint"
# Types: feat, fix, docs, style, refactor, test, chore

# 3. Push to remote
git push origin feature/your-feature-name
```

**Why this prevents issues**:
- ✅ Catches import errors before they reach CI/CD
- ✅ Validates database migrations work correctly  
- ✅ Ensures performance doesn't regress
- ✅ Prevents "works on my machine" deployment failures

**Failed readiness check?** Fix the issues before committing:
```bash
# Check the detailed report
cat deployment_readiness_report.json

# Common fixes:
pip install -r requirements.txt  # Missing dependencies
alembic upgrade head             # Database out of sync
export DATABASE_URL=...          # Environment variables
```

### 6. Creating Pull Request

1. Go to GitHub repository
2. Click "New Pull Request"
3. Select your branch
4. Fill out PR template:
   - Description of changes
   - Related issues
   - Testing performed
   - Screenshots (if UI changes)
5. Request reviews
6. Address feedback
7. Merge after approval

## Debugging

### Backend Debugging

#### VS Code
```json
// .vscode/launch.json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": ["dotmac_isp.main:app", "--reload"],
      "cwd": "${workspaceFolder}/isp-framework",
      "env": {
        "PYTHONPATH": "${workspaceFolder}/isp-framework/src"
      }
    }
  ]
}
```

#### Command Line
```bash
# Enable debug mode
export DEBUG=true
export LOG_LEVEL=DEBUG

# Use debugger
import pdb; pdb.set_trace()  # Add breakpoint

# Use ipdb (better debugger)
pip install ipdb
import ipdb; ipdb.set_trace()
```

### Frontend Debugging

#### Browser DevTools
- React Developer Tools
- Redux DevTools
- Network tab for API calls
- Console for errors

#### VS Code
```json
// .vscode/launch.json
{
  "configurations": [
    {
      "name": "Chrome",
      "type": "chrome",
      "request": "launch",
      "url": "http://localhost:3000",
      "webRoot": "${workspaceFolder}/frontend"
    }
  ]
}
```

## Common Tasks

### Adding a New API Endpoint

1. **Define Schema** (`schemas/customer.py`):
```python
from pydantic import BaseModel

class CustomerCreate(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str]
```

2. **Create Model** (`models/customer.py`):
```python
from sqlalchemy import Column, String
from .base import Base

class Customer(Base):
    __tablename__ = "customers"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True)
```

3. **Add Service** (`services/customer_service.py`):
```python
async def create_customer(db: Session, data: CustomerCreate):
    customer = Customer(**data.dict())
    db.add(customer)
    await db.commit()
    return customer
```

4. **Create Endpoint** (`api/v1/customers.py`):
```python
@router.post("/customers", response_model=CustomerSchema)
async def create_customer(
    data: CustomerCreate,
    db: Session = Depends(get_db)
):
    return await customer_service.create_customer(db, data)
```

5. **Add Tests** (`tests/test_customers.py`):
```python
async def test_create_customer(client, auth_headers):
    data = {"name": "Test", "email": "test@example.com"}
    response = await client.post(
        "/api/v1/customers",
        json=data,
        headers=auth_headers
    )
    assert response.status_code == 201
```

### Adding a New Frontend Feature

1. **Create Component**:
```typescript
// components/FeatureName/index.tsx
export const FeatureName: React.FC = () => {
  return <div>Feature Content</div>;
};
```

2. **Add Route**:
```typescript
// routes/index.tsx
<Route path="/feature" element={<FeatureName />} />
```

3. **Create Store** (if using Redux):
```typescript
// store/featureSlice.ts
const featureSlice = createSlice({
  name: 'feature',
  initialState,
  reducers: {
    // Add reducers
  }
});
```

4. **Add API Integration**:
```typescript
// api/feature.ts
export const featureApi = {
  getAll: () => api.get('/feature'),
  create: (data) => api.post('/feature', data)
};
```

## Architecture Guidelines

### Design Principles
- **Domain-Driven Design (DDD)**: Organize code by business domains
- **SOLID Principles**: Write maintainable, extensible code
- **12-Factor App**: Follow cloud-native best practices
- **Security First**: Always consider security implications

### Code Standards

#### Python
- Follow PEP 8
- Use type hints
- Write docstrings for all functions
- Keep functions under 20 lines
- Max line length: 88 characters (Black default)

#### TypeScript
- Use strict mode
- Prefer functional components
- Use custom hooks for logic
- Implement proper error boundaries
- Follow React best practices

### Performance Guidelines
- Use database indexes appropriately
- Implement caching where beneficial
- Lazy load frontend components
- Optimize images and assets
- Monitor API response times

## Resources

### Documentation
- [Architecture Guide](./ARCHITECTURE.md)
- [API Documentation](./API_DOCUMENTATION.md)
- [Comprehensive Deployment Guide](./COMPREHENSIVE_DEPLOYMENT_GUIDE.md)
- [Security Production Checklist](./SECURITY_PRODUCTION_CHECKLIST.md)

### External Resources
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Docker Documentation](https://docs.docker.com/)

### Team Resources
- **Slack Channel**: #dotmac-dev
- **Wiki**: https://wiki.dotmac.internal
- **CI/CD**: https://ci.dotmac.internal
- **Monitoring**: https://grafana.dotmac.internal

## Getting Help

### Common Issues

#### Database Connection Error
```bash
# Check PostgreSQL is running
systemctl status postgresql

# Check connection string
echo $DATABASE_URL

# Test connection
psql $DATABASE_URL
```

#### Port Already in Use
```bash
# Find process using port
lsof -i :8000

# Kill process
kill -9 <PID>
```

#### Docker Issues
```bash
# Clean Docker
docker system prune -a

# Rebuild containers
docker-compose down
docker-compose build --no-cache
docker-compose up
```

### Support Channels
1. **Slack**: Post in #dotmac-dev-help
2. **GitHub Issues**: Create an issue with the `question` label
3. **Team Lead**: Schedule 1:1 for complex issues
4. **Documentation**: Check internal wiki

## Your First Week Checklist

- [ ] Environment setup complete
- [ ] Successfully run the application locally
- [ ] Complete the tutorial project
- [ ] Read architecture documentation
- [ ] Join team Slack channels
- [ ] Set up your IDE with recommended extensions
- [ ] Run and understand the test suite
- [ ] Make your first pull request (even if just docs)
- [ ] Attend team standup meetings
- [ ] Schedule 1:1 with team lead
- [ ] Review recent pull requests
- [ ] Familiarize with deployment process

## Next Steps

1. **Explore the Codebase**: Start with `main.py` and follow the imports
2. **Pick a Starter Task**: Look for issues labeled "good first issue"
3. **Shadow a Team Member**: Pair program on a feature
4. **Contribute**: Start with documentation or tests
5. **Learn the Domain**: Understand ISP business logic

Welcome aboard! We're excited to have you on the team. Don't hesitate to ask questions - we're here to help you succeed! 🎉

---

*Last Updated: August 2024*
*Version: 1.0.0*
