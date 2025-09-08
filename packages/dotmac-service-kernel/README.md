# dotmac-service-kernel

Service and repository kernel for DotMac applications providing consistent patterns for service architecture and data access.

## Purpose

This package provides thin interfaces and helpers for services and repositories, ensuring consistent patterns across DotMac applications without heavy framework dependencies.

## Features

- **Repository Protocols**: Generic CRUD interfaces with type safety
- **Service Framework**: Base service classes with lifecycle management
- **Pagination Utilities**: Consistent pagination helpers
- **Unit of Work**: Transaction management protocols
- **Error Handling**: Standardized service and repository exceptions

## Quick Start

### Repository Pattern

```python
from dotmac_service_kernel.protocols import RepositoryProtocol
from dotmac_service_kernel.pagination import Page
from uuid import UUID

class UserRepository(RepositoryProtocol[User, CreateUser, UpdateUser]):
    async def create(self, obj_in: CreateUser, **kwargs) -> User:
        # Implementation
        pass
    
    async def get(self, id: UUID) -> User | None:
        # Implementation  
        pass
    
    async def get_multi(self, skip=0, limit=100, **filters) -> list[User]:
        # Implementation
        pass
```

### Service Pattern

```python
from dotmac_service_kernel.protocols import ServiceProtocol
from dotmac_service_kernel.base import BaseService

class UserService(BaseService[User, CreateUser, UpdateUser]):
    def __init__(self, repository: UserRepository):
        super().__init__(repository)
    
    async def create_user(self, data: CreateUser) -> User:
        # Business logic here
        return await self.repository.create(data)
```

### Pagination

```python
from dotmac_service_kernel.pagination import Page

# Results automatically wrapped in Page container
users_page: Page[User] = await user_repository.get_page(page=1, size=20)
print(f"Found {users_page.total} users, showing page {users_page.page}")
```

## Installation

```bash
pip install dotmac-service-kernel
```

## API Reference

### Protocols

- `RepositoryProtocol[T, CreateT, UpdateT]`: Generic repository interface
- `ServiceProtocol`: Marker protocol for services  
- `UnitOfWork`: Transaction management interface

### Base Classes

- `BaseService[T, CreateT, UpdateT]`: Service base class with CRUD operations
- `BaseRepository[T, CreateT, UpdateT]`: Repository base implementation

### Utilities

- `Page[T]`: Pagination container
- `ServiceError`: Base service exception
- `RepositoryError`: Base repository exception

## Development

```bash
# Install dependencies
poetry install

# Run tests
pytest

# Lint and format
ruff check src/ tests/
mypy src/
```

## License

MIT