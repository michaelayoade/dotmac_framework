"""
Tests for pagination utilities.
"""


from dotmac_service_kernel.pagination import (
    Page,
    PaginationParams,
    create_page,
    get_pagination_bounds,
)


class TestPage:
    """Test Page class functionality."""

    def test_page_creation(self):
        """Test creating a page with basic data."""
        items = [1, 2, 3, 4, 5]
        page = Page(items=items, total=25, page=2, page_size=5)

        assert page.items == [1, 2, 3, 4, 5]
        assert page.total == 25
        assert page.page == 2
        assert page.page_size == 5

    def test_page_calculations(self):
        """Test page calculations are correct."""
        page = Page(items=[1, 2, 3], total=13, page=2, page_size=5)

        assert page.total_pages == 3
        assert page.has_next is True
        assert page.has_prev is True
        assert page.start_index == 5
        assert page.end_index == 10

    def test_first_page(self):
        """Test first page calculations."""
        page = Page(items=[1, 2, 3], total=10, page=1, page_size=3)

        assert page.has_prev is False
        assert page.has_next is True
        assert page.start_index == 0
        assert page.end_index == 3

    def test_last_page(self):
        """Test last page calculations."""
        page = Page(items=[7, 8], total=8, page=3, page_size=3)

        assert page.total_pages == 3
        assert page.has_prev is True
        assert page.has_next is False
        assert page.start_index == 6
        assert page.end_index == 8

    def test_empty_page(self):
        """Test empty page."""
        page = Page(items=[], total=0, page=1, page_size=10)

        assert page.total_pages == 0
        assert page.has_prev is False
        assert page.has_next is False
        assert page.start_index == 0
        assert page.end_index == 0

    def test_to_dict(self):
        """Test page serialization to dictionary."""
        page = Page(items=[1, 2], total=5, page=1, page_size=2)
        data = page.to_dict()

        expected = {
            "items": [1, 2],
            "total": 5,
            "page": 1,
            "page_size": 2,
            "total_pages": 3,
            "has_next": True,
            "has_prev": False,
            "start_index": 0,
            "end_index": 2,
        }
        assert data == expected


class TestPaginationParams:
    """Test PaginationParams class functionality."""

    def test_default_params(self):
        """Test default pagination parameters."""
        params = PaginationParams()

        assert params.page == 1
        assert params.size == 20
        assert params.skip == 0
        assert params.limit == 20

    def test_custom_params(self):
        """Test custom pagination parameters."""
        params = PaginationParams(page=3, size=10)

        assert params.page == 3
        assert params.size == 10
        assert params.skip == 20
        assert params.limit == 10

    def test_param_validation(self):
        """Test parameter validation."""
        # Test negative page becomes 1
        params = PaginationParams(page=-5, size=10)
        assert params.page == 1

        # Test zero page becomes 1
        params = PaginationParams(page=0, size=10)
        assert params.page == 1

        # Test negative size becomes 1
        params = PaginationParams(page=1, size=-10)
        assert params.size == 1

        # Test zero size becomes 1
        params = PaginationParams(page=1, size=0)
        assert params.size == 1

        # Test oversized size becomes 1000
        params = PaginationParams(page=1, size=2000)
        assert params.size == 1000

    def test_skip_calculation(self):
        """Test skip calculation for different pages."""
        params1 = PaginationParams(page=1, size=10)
        assert params1.skip == 0

        params2 = PaginationParams(page=5, size=20)
        assert params2.skip == 80

        params3 = PaginationParams(page=3, size=15)
        assert params3.skip == 30


class TestPaginationUtilities:
    """Test pagination utility functions."""

    def test_create_page(self):
        """Test create_page utility function."""
        items = ["a", "b", "c"]
        page = create_page(items, total=10, page=2, page_size=3)

        assert isinstance(page, Page)
        assert page.items == ["a", "b", "c"]
        assert page.total == 10
        assert page.page == 2
        assert page.page_size == 3

    def test_create_page_validation(self):
        """Test create_page validates parameters."""
        items = [1, 2, 3]

        # Test negative values get corrected
        page = create_page(items, total=-5, page=-1, page_size=-10)
        assert page.total == 0
        assert page.page == 1
        assert page.page_size == 1

    def test_get_pagination_bounds(self):
        """Test get_pagination_bounds utility function."""
        skip, limit = get_pagination_bounds(page=1, page_size=10)
        assert skip == 0
        assert limit == 10

        skip, limit = get_pagination_bounds(page=3, page_size=20)
        assert skip == 40
        assert limit == 20

        skip, limit = get_pagination_bounds(page=5, page_size=15)
        assert skip == 60
        assert limit == 15

    def test_get_pagination_bounds_validation(self):
        """Test get_pagination_bounds validates parameters."""
        # Test negative values get corrected
        skip, limit = get_pagination_bounds(page=-1, page_size=-5)
        assert skip == 0  # (1-1) * 1
        assert limit == 1
