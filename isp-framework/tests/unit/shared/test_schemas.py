"""Tests for shared schemas module."""

import pytest
from pydantic import ValidationError

from dotmac_isp.shared.schemas import PaginationParams, PaginatedResponse


class TestPaginationParams:
    """Test PaginationParams schema."""
    
    def test_offset_property(self):
        """Test offset property calculation - covers line 86."""
        # Test various page/size combinations
        test_cases = [
            (1, 10, 0),    # First page
            (2, 10, 10),   # Second page
            (3, 20, 40),   # Third page with larger size
            (5, 5, 20),    # Fifth page with small size
            (1, 100, 0),   # Large page size
        ]
        
        for page, size, expected_offset in test_cases:
            params = PaginationParams(page=page, size=size)
            
            # Call the property - this executes line 86
            offset = params.offset
            
            assert offset == expected_offset, f"Page {page}, Size {size} should give offset {expected_offset}, got {offset}"
    
    def test_pagination_params_validation(self):
        """Test PaginationParams validation."""
        # Valid params
        valid_params = PaginationParams(page=1, size=10)
        assert valid_params.page == 1
        assert valid_params.size == 10
        assert valid_params.offset == 0
        
        # Test default values
        default_params = PaginationParams()
        assert default_params.page == 1
        assert default_params.size == 10
        assert default_params.offset == 0
    
    def test_pagination_params_edge_cases(self):
        """Test edge cases for pagination params."""
        # Minimum values
        min_params = PaginationParams(page=1, size=1)
        assert min_params.offset == 0
        
        # Large values
        large_params = PaginationParams(page=1000, size=100)
        expected_offset = (1000 - 1) * 100
        assert large_params.offset == expected_offset


class TestPaginatedResponse:
    """Test PaginatedResponse schema."""
    
    def test_create_class_method(self):
        """Test create class method - covers lines 101-102."""
        items = ["item1", "item2", "item3"]
        total = 25
        page = 2
        size = 10
        
        # Call the create method - this executes lines 101-102
        response = PaginatedResponse.create(items=items, total=total, page=page, size=size)
        
        # Verify the response was created correctly
        assert response.items == items
        assert response.total == total
        assert response.page == page
        assert response.size == size
        assert response.pages == 3  # (25 + 10 - 1) // 10 = 3
    
    def test_create_method_ceiling_division(self):
        """Test create method ceiling division calculation."""
        test_cases = [
            # (total, size, expected_pages)
            (10, 10, 1),   # Exact division
            (11, 10, 2),   # One extra item
            (20, 10, 2),   # Exact division
            (21, 10, 3),   # One extra item
            (1, 10, 1),    # Less than page size
            (0, 10, 0),    # No items
            (100, 25, 4),  # Large numbers
            (101, 25, 5),  # Large numbers with remainder
        ]
        
        for total, size, expected_pages in test_cases:
            response = PaginatedResponse.create(
                items=list(range(min(total, size))), 
                total=total, 
                page=1, 
                size=size
            )
            
            assert response.pages == expected_pages, \
                f"Total {total}, Size {size} should give {expected_pages} pages, got {response.pages}"
    
    def test_create_method_with_empty_items(self):
        """Test create method with empty items list."""
        response = PaginatedResponse.create(
            items=[],
            total=0,
            page=1,
            size=10
        )
        
        assert response.items == []
        assert response.total == 0
        assert response.page == 1
        assert response.size == 10
        assert response.pages == 0
    
    def test_create_method_with_various_data_types(self):
        """Test create method with different item types."""
        # String items
        str_response = PaginatedResponse.create(
            items=["a", "b", "c"],
            total=3,
            page=1,
            size=5
        )
        assert str_response.items == ["a", "b", "c"]
        assert str_response.pages == 1
        
        # Dictionary items
        dict_items = [{"id": 1, "name": "test1"}, {"id": 2, "name": "test2"}]
        dict_response = PaginatedResponse.create(
            items=dict_items,
            total=10,
            page=1,
            size=5
        )
        assert dict_response.items == dict_items
        assert dict_response.pages == 2
        
        # Integer items
        int_response = PaginatedResponse.create(
            items=[1, 2, 3, 4, 5],
            total=15,
            page=2,
            size=5
        )
        assert int_response.items == [1, 2, 3, 4, 5]
        assert int_response.pages == 3
    
    def test_direct_instantiation(self):
        """Test direct PaginatedResponse instantiation."""
        response = PaginatedResponse(
            items=["test1", "test2"],
            total=20,
            page=2,
            size=10,
            pages=2
        )
        
        assert response.items == ["test1", "test2"]
        assert response.total == 20
        assert response.page == 2
        assert response.size == 10
        assert response.pages == 2


class TestSchemasIntegration:
    """Test integration between schemas."""
    
    def test_pagination_params_with_paginated_response(self):
        """Test using PaginationParams with PaginatedResponse."""
        # Create pagination parameters
        params = PaginationParams(page=3, size=5)
        
        # Test offset calculation
        offset = params.offset  # Should be (3-1) * 5 = 10
        assert offset == 10
        
        # Simulate getting data with these parameters
        mock_items = ["item1", "item2", "item3"]
        total_count = 23
        
        # Create paginated response
        response = PaginatedResponse.create(
            items=mock_items,
            total=total_count,
            page=params.page,
            size=params.size
        )
        
        assert response.page == 3
        assert response.size == 5
        assert response.total == 23
        assert response.pages == 5  # (23 + 5 - 1) // 5 = 5
        assert response.items == mock_items
    
    def test_edge_case_pagination_combinations(self):
        """Test edge cases in pagination combinations."""
        # Single item, single page
        single_params = PaginationParams(page=1, size=1)
        single_response = PaginatedResponse.create(
            items=["only_item"],
            total=1,
            page=single_params.page,
            size=single_params.size
        )
        
        assert single_params.offset == 0
        assert single_response.pages == 1
        
        # Last page with partial items
        last_page_params = PaginationParams(page=3, size=10)
        last_page_response = PaginatedResponse.create(
            items=["item1", "item2"],  # Only 2 items on last page
            total=22,
            page=last_page_params.page,
            size=last_page_params.size
        )
        
        assert last_page_params.offset == 20
        assert last_page_response.pages == 3  # (22 + 10 - 1) // 10 = 3
        assert len(last_page_response.items) == 2


class TestComprehensiveCoverage:
    """Ensure all missing lines are covered."""
    
    def test_all_missing_lines_coverage(self):
        """Test all originally missing lines (86, 101-102) are covered."""
        
        # Line 86: PaginationParams.offset property
        params = PaginationParams(page=5, size=20)
        offset_value = params.offset  # Line 86
        assert offset_value == 80
        
        # Lines 101-102: PaginatedResponse.create method
        items = [1, 2, 3]
        response = PaginatedResponse.create(  # Lines 101-102
            items=items,
            total=17,
            page=2,
            size=5
        )
        
        # Verify the ceiling division calculation from line 101
        expected_pages = (17 + 5 - 1) // 5  # 21 // 5 = 4
        assert response.pages == expected_pages
        assert response.items == items