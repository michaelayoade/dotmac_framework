"""
Basic test coverage for pagination helpers module.
"""

import pytest
from dotmac.core.db_toolkit.pagination.helpers import (
    create_query_options, 
    validate_pagination_params,
    calculate_offset,
    PaginationHelper
)


class TestPaginationHelpers:
    """Test pagination helper functions."""

    def test_validate_pagination_params_valid(self):
        """Test valid pagination parameters."""
        # Should not raise any exception
        validate_pagination_params(page=1, per_page=20)
        validate_pagination_params(page=5, per_page=100)

    def test_validate_pagination_params_invalid_page(self):
        """Test invalid page parameters."""
        with pytest.raises(ValueError):
            validate_pagination_params(page=0, per_page=20)
        
        with pytest.raises(ValueError):
            validate_pagination_params(page=-1, per_page=20)

    def test_validate_pagination_params_invalid_per_page(self):
        """Test invalid per_page parameters."""
        with pytest.raises(ValueError):
            validate_pagination_params(page=1, per_page=0)
        
        with pytest.raises(ValueError):
            validate_pagination_params(page=1, per_page=-5)
        
        with pytest.raises(ValueError):
            validate_pagination_params(page=1, per_page=1001)

    def test_calculate_offset(self):
        """Test offset calculation."""
        assert calculate_offset(1, 20) == 0
        assert calculate_offset(2, 20) == 20
        assert calculate_offset(3, 10) == 20
        assert calculate_offset(5, 25) == 100

    def test_create_query_options_basic(self):
        """Test basic query options creation."""
        options = create_query_options()
        
        assert options.pagination.page == 1
        assert options.pagination.per_page == 20
        assert options.filters == []
        assert options.sorts == []

    def test_create_query_options_custom(self):
        """Test custom query options."""
        filters = {"status": "active", "type": "premium"}
        
        options = create_query_options(
            page=3,
            per_page=50,
            filters=filters,
            sort_by="created_at",
            sort_order="desc"
        )
        
        assert options.pagination.page == 3
        assert options.pagination.per_page == 50
        assert len(options.filters) > 0
        assert len(options.sorts) > 0

    def test_pagination_helper_alias(self):
        """Test PaginationHelper alias works."""
        # This should work without errors
        assert PaginationHelper is not None
        
        # Test it has expected methods  
        assert hasattr(PaginationHelper, 'calculate_pagination_info')
