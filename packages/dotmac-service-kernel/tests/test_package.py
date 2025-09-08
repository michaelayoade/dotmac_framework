"""
Test package imports and public API.
"""



def test_package_imports():
    """Test that all public API components can be imported."""
    from dotmac_service_kernel import (
        Page,
        RepositoryError,
        RepositoryProtocol,
        ServiceError,
        ServiceProtocol,
        UnitOfWork,
        __version__,
    )

    # Test that classes are actually classes/protocols
    assert Page is not None
    assert RepositoryProtocol is not None
    assert ServiceProtocol is not None
    assert UnitOfWork is not None

    # Test that exceptions are exception classes
    assert issubclass(ServiceError, Exception)
    assert issubclass(RepositoryError, Exception)

    # Test version
    assert isinstance(__version__, str)
    assert __version__ == "1.0.0"


def test_protocols_are_runtime_checkable():
    """Test that protocols can be used with isinstance at runtime."""
    from dotmac_service_kernel import RepositoryProtocol, ServiceProtocol, UnitOfWork

    # These should be runtime checkable protocols
    class MockRepository:
        async def create(self, obj_in, **kwargs):
            return obj_in

        async def get(self, entity_id):
            return None

        async def get_multi(self, *, skip=0, limit=100, **filters):
            return []

        async def get_page(self, *, page=1, page_size=20, **filters):
            from dotmac_service_kernel import Page
            return Page([], 0, page, page_size)

        async def update(self, db_obj, obj_in):
            return db_obj

        async def delete(self, entity_id):
            return True

        async def count(self, **filters):
            return 0

    class MockService:
        pass

    class MockUoW:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        async def commit(self):
            pass

        async def rollback(self):
            pass

    # Test isinstance checks work
    repo = MockRepository()
    service = MockService()
    uow = MockUoW()

    assert isinstance(repo, RepositoryProtocol)
    assert isinstance(service, ServiceProtocol)
    assert isinstance(uow, UnitOfWork)


def test_pagination_functionality():
    """Test basic pagination functionality."""
    from dotmac_service_kernel import Page

    # Create a page
    items = [1, 2, 3]
    page = Page(items=items, total=10, page=1, page_size=5)

    assert page.items == [1, 2, 3]
    assert page.total == 10
    assert page.page == 1
    assert page.page_size == 5
    assert page.total_pages == 2
    assert page.has_next is True
    assert page.has_prev is False


def test_error_classes():
    """Test error class functionality."""
    from dotmac_service_kernel.errors import (
        NotFoundError,
        ServiceError,
        ValidationError,
    )

    # Test basic service error
    error = ServiceError("Test error", error_code="test")
    assert str(error) == "Test error"
    assert error.error_code == "test"
    assert error.details == {}

    # Test not found error
    not_found = NotFoundError("User", "123")
    assert "User with id '123' not found" in str(not_found)
    assert not_found.error_code == "not_found"

    # Test validation error
    validation = ValidationError("Invalid data", {"email": ["Required"]})
    assert validation.error_code == "validation_error"
    assert validation.field_errors == {"email": ["Required"]}


def test_types_and_generics():
    """Test type definitions work correctly."""
    from uuid import uuid4

    from dotmac_service_kernel.types import ID

    # Test ID type alias
    str_id: ID = "test-id"
    int_id: ID = 123
    uuid_id: ID = uuid4()

    assert isinstance(str_id, str)
    assert isinstance(int_id, int)
    assert str(uuid_id)  # Should convert to string
