# DotMAC Framework Import Policy

## Overview

This document establishes coding standards for imports in the DotMAC Framework to ensure maintainability, debugging ease, and IDE support.

## Import Policy Rules

### ✅ Allowed Patterns

#### 1. Explicit Imports (Preferred)
```python
# Good - Explicit and clear
from dotmac_shared.api.dependencies import get_current_user, validate_tenant
from dotmac_shared.core.exceptions import ValidationError
from typing import Dict, List, Optional
```

#### 2. Star Imports in `__init__.py` Files Only
```python
# Acceptable in __init__.py files for package API exposure
# src/dotmac_shared/api/__init__.py
from .dependencies import *
from .exception_handlers import *
from .router_factory import *

# But prefer explicit re-exports when possible:
from .dependencies import get_current_user, validate_tenant
from .exception_handlers import standard_exception_handler

__all__ = ["get_current_user", "validate_tenant", "standard_exception_handler"]
```

#### 3. Relative Imports (Limited Depth)
```python
# Acceptable - Single level relative imports within modules
from .models import User, Tenant
from .schemas import UserSchema, TenantSchema
from ..core.exceptions import ValidationError  # Max 2 levels

# Good practice - Absolute imports for shared components
from dotmac_shared.core.exceptions import ValidationError
```

### ❌ Prohibited Patterns

#### 1. Star Imports in Non-Init Files
```python
# BAD - Pollutes namespace, hard to debug
from some_module import *
from dotmac_shared.api.dependencies import *

# GOOD - Explicit imports
from some_module import specific_function, SpecificClass
from dotmac_shared.api.dependencies import get_current_user
```

#### 2. Deep Relative Imports
```python
# BAD - Hard to follow, fragile
from ....shared.core.exceptions import ValidationError
from ...models.billing import Invoice

# GOOD - Use absolute imports for deep references  
from dotmac_shared.core.exceptions import ValidationError
from dotmac_isp.modules.billing.models import Invoice
```

#### 3. Circular Import Patterns
```python
# BAD - Creates circular dependencies
# file_a.py
from .file_b import function_b

# file_b.py  
from .file_a import function_a

# GOOD - Extract shared functionality
# shared_utils.py
def shared_function():
    pass

# file_a.py
from .shared_utils import shared_function

# file_b.py
from .shared_utils import shared_function
```

## Import Organization Standards

### 1. Import Order (PEP 8 + DotMAC Extensions)
```python
"""Module docstring."""

# 1. Standard library imports
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional

# 2. Third-party library imports  
import fastapi
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String

# 3. DotMAC shared library imports
from dotmac_shared.api.dependencies import get_current_user
from dotmac_shared.core.exceptions import ValidationError
from dotmac_shared.database.base import BaseModel as DBBaseModel

# 4. Local application imports
from .models import User, Tenant
from .schemas import UserSchema, TenantSchema
from .services import UserService

# 5. Relative imports (if necessary)
from ..core.auth import authenticate_user
```

### 2. Import Grouping Guidelines
```python
# Group related imports together with blank lines between groups
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer

from dotmac_shared.api.dependencies import get_current_user, validate_tenant
from dotmac_shared.api.exception_handlers import standard_exception_handler
from dotmac_shared.core.exceptions import ValidationError, AuthenticationError

from .models import User, Tenant, Permission
from .schemas import UserSchema, TenantSchema, PermissionSchema
from .services import UserService, TenantService
```

## Module-Specific Guidelines

### Core Modules (`src/dotmac_isp/`, `src/dotmac_management/`)
- **MUST** use absolute imports for cross-module dependencies
- **MAY** use single-level relative imports within the same module
- **MUST NOT** use star imports except in `__init__.py`
- **MUST NOT** create circular dependencies

```python
# Good patterns for core modules
from dotmac_shared.api.router_factory import create_router
from dotmac_isp.modules.billing.models import Invoice
from .schemas import BillingSchema  # Single level relative OK
```

### Shared Library (`src/dotmac_shared/`)
- **MUST** use absolute imports for external dependencies
- **MAY** use relative imports within the same package
- **SHOULD** provide explicit `__all__` lists in `__init__.py`
- **MUST** maintain backward compatibility

```python
# dotmac_shared modules should be self-contained
from typing import Dict, Any
from fastapi import APIRouter
from .base import BaseService  # Relative within same package
```

### Package Modules (`packages/`)
- **MUST** use absolute imports for all external dependencies  
- **SHOULD** minimize dependencies on other packages
- **MUST** declare dependencies clearly in package metadata

### Template Files (`templates/`)
- **MAY** use relaxed import rules (validated separately)
- **SHOULD** use absolute imports when possible
- **MAY** contain temporary workarounds during development

## Enforcement and Tools

### 1. Pre-commit Hooks
```yaml
# .pre-commit-config.yaml
repos:
- repo: local
  hooks:
  - id: import-validation
    name: Import Policy Validation
    entry: python .dev-artifacts/scripts/syntax_validator.py
    language: system
    files: \.py$
    exclude: ^templates/
```

### 2. CI/CD Validation
- Syntax validation runs on every PR
- Import pattern analysis in CI pipeline
- Separate validation for templates vs core code

### 3. IDE Configuration

#### VS Code Settings
```json
// .vscode/settings.json
{
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.linting.pylintArgs": [
        "--disable=wildcard-import,unused-wildcard-import"
    ],
    "python.sortImports.args": [
        "--profile=black",
        "--force-grid-wrap=0",
        "--multi-line=3",
        "--line-length=88",
        "--use-parentheses",
        "--trailing-comma"
    ]
}
```

#### PyCharm Settings
- Enable "Optimize imports on the fly"
- Configure import order: stdlib → third-party → dotmac_shared → local
- Warn on star imports outside `__init__.py`

### 4. Linting Configuration
```python
# pyproject.toml
[tool.isort]
profile = "black"
multi_line_output = 3
line_length = 88
known_first_party = ["dotmac_shared", "dotmac_isp", "dotmac_management"]
sections = ["FUTURE", "STDLIB", "THIRDPARTY", "FIRSTPARTY", "LOCALFOLDER"]
```

## Migration Strategy

### Phase 1: Critical Fixes (Immediate)
1. Fix syntax errors preventing imports
2. Remove star imports from non-`__init__.py` files
3. Fix circular import issues

### Phase 2: Policy Implementation (2-4 weeks)
1. Add import validation to CI/CD
2. Update existing code to follow policy
3. Add pre-commit hooks

### Phase 3: Optimization (1-2 months)
1. Refactor deep relative imports to absolute
2. Consolidate related packages
3. Optimize import performance

## Examples and Best Practices

### ✅ Good Import Examples

#### API Router Module
```python
"""User management API router."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer

from dotmac_shared.api.dependencies import get_current_user, validate_tenant
from dotmac_shared.api.router_factory import create_router
from dotmac_shared.core.exceptions import ValidationError

from .models import User
from .schemas import UserCreateSchema, UserResponseSchema, UserUpdateSchema
from .services import UserService

router = create_router(prefix="/users", tags=["users"])
security = HTTPBearer()
```

#### Service Module
```python
"""User service with business logic."""

from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from dotmac_shared.database.base import BaseService
from dotmac_shared.core.exceptions import NotFoundError, ValidationError

from .models import User
from .schemas import UserCreateSchema, UserUpdateSchema
from .repository import UserRepository

class UserService(BaseService[User, UserCreateSchema, UserUpdateSchema]):
    """User management service."""
    
    def __init__(self, db: Session):
        self.repository = UserRepository(db)
```

### ❌ Bad Import Examples

#### Problematic Patterns
```python
# BAD - Star imports everywhere
from fastapi import *
from .models import *
from ..services import *

# BAD - Deep relative imports
from ....shared.core.exceptions import ValidationError
from ....management.models.tenant import Tenant

# BAD - Mixed import styles
import fastapi
from fastapi import APIRouter
from fastapi import *  # Inconsistent style
```

## FAQ

### Q: When should I use relative vs absolute imports?
**A:** Use relative imports only for closely related modules within the same package. Use absolute imports for anything in `dotmac_shared` or cross-module dependencies.

### Q: Are star imports ever acceptable?
**A:** Only in `__init__.py` files to create package APIs, and preferably with explicit `__all__` lists.

### Q: How do I handle circular imports?
**A:** Extract shared functionality into a separate module, use dependency injection, or restructure the code to eliminate the circular dependency.

### Q: What about performance of imports?
**A:** Explicit imports are generally faster and create smaller namespaces. Avoid importing large modules unless necessary.

### Q: Should templates follow the same rules?
**A:** Templates have relaxed rules but should still avoid circular imports and prefer explicit imports when possible.

## Enforcement

This policy is enforced through:
- ✅ Pre-commit hooks (blocking)
- ✅ CI/CD pipeline validation (blocking for core/packages)  
- ✅ Code review guidelines (manual)
- ⚠️ Template validation (warning only)

**Non-compliance in core modules will block merges.**