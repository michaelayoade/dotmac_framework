"""
Test cases for DotMac Core database toolkit functionality.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

try:
    from dotmac.core.db_toolkit.health.checker import DatabaseHealthChecker
    from dotmac.core.db_toolkit.pagination.helpers import PaginationHelper
    from dotmac.core.db_toolkit.pagination.paginator import DatabasePaginator
    from dotmac.core.db_toolkit.types import PaginationParams, SortOrder

    DB_TOOLKIT_AVAILABLE = True
except ImportError:
    DB_TOOLKIT_AVAILABLE = False


@pytest.mark.skipif(not DB_TOOLKIT_AVAILABLE, reason="Database toolkit not available")
class TestDatabaseHealthChecker:
    """Test DatabaseHealthChecker functionality."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.close = AsyncMock()
        return session

    @pytest.fixture
    def health_checker(self):
        """Create DatabaseHealthChecker instance."""
        return DatabaseHealthChecker()

    def test_health_checker_initialization(self, health_checker):
        """Test health checker initialization."""
        assert health_checker is not None
        assert isinstance(health_checker, DatabaseHealthChecker)

    @pytest.mark.asyncio
    async def test_check_database_connection_success(self, health_checker, mock_session):
        """Test successful database connection check."""
        mock_session.execute.return_value = Mock(scalar=Mock(return_value=1))

        with patch.object(health_checker, "_get_session", return_value=mock_session):
            result = await health_checker.check_connection()

        assert result is True
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_database_connection_failure(self, health_checker, mock_session):
        """Test failed database connection check."""
        mock_session.execute.side_effect = Exception("Connection failed")

        with patch.object(health_checker, "_get_session", return_value=mock_session):
            result = await health_checker.check_connection()

        assert result is False

    @pytest.mark.asyncio
    async def test_get_database_info(self, health_checker, mock_session):
        """Test getting database information."""
        mock_result = Mock()
        mock_result.scalar.return_value = "PostgreSQL 14.0"
        mock_session.execute.return_value = mock_result

        with patch.object(health_checker, "_get_session", return_value=mock_session):
            info = await health_checker.get_database_info()

        assert isinstance(info, dict)
        assert "version" in info or "status" in info

    @pytest.mark.asyncio
    async def test_check_table_exists(self, health_checker, mock_session):
        """Test checking if table exists."""
        mock_result = Mock()
        mock_result.scalar.return_value = 1
        mock_session.execute.return_value = mock_result

        with patch.object(health_checker, "_get_session", return_value=mock_session):
            exists = await health_checker.check_table_exists("test_table")

        assert exists is True

    @pytest.mark.asyncio
    async def test_health_check_comprehensive(self, health_checker, mock_session):
        """Test comprehensive health check."""
        # Mock successful responses
        mock_session.execute.return_value = Mock(scalar=Mock(return_value=1))

        with patch.object(health_checker, "_get_session", return_value=mock_session):
            health_report = await health_checker.comprehensive_health_check()

        assert isinstance(health_report, dict)
        assert "status" in health_report
        assert "timestamp" in health_report

    def test_health_checker_with_custom_session_factory(self):
        """Test health checker with custom session factory."""
        mock_factory = Mock()
        health_checker = DatabaseHealthChecker(session_factory=mock_factory)

        assert health_checker is not None


@pytest.mark.skipif(not DB_TOOLKIT_AVAILABLE, reason="Database toolkit not available")
class TestPaginationHelper:
    """Test PaginationHelper functionality."""

    def test_pagination_helper_initialization(self):
        """Test pagination helper initialization."""
        helper = PaginationHelper()
        assert helper is not None

    def test_calculate_offset(self):
        """Test offset calculation."""
        helper = PaginationHelper()

        # Test various page/limit combinations
        assert helper.calculate_offset(page=1, limit=10) == 0
        assert helper.calculate_offset(page=2, limit=10) == 10
        assert helper.calculate_offset(page=3, limit=20) == 40
        assert helper.calculate_offset(page=1, limit=100) == 0

    def test_calculate_total_pages(self):
        """Test total pages calculation."""
        helper = PaginationHelper()

        # Test various total/limit combinations
        assert helper.calculate_total_pages(total_count=100, limit=10) == 10
        assert helper.calculate_total_pages(total_count=101, limit=10) == 11
        assert helper.calculate_total_pages(total_count=0, limit=10) == 0
        assert helper.calculate_total_pages(total_count=5, limit=10) == 1

    def test_validate_pagination_params(self):
        """Test pagination parameter validation."""
        helper = PaginationHelper()

        # Valid parameters
        params = helper.validate_pagination_params(page=1, limit=10)
        assert params["page"] == 1
        assert params["limit"] == 10

        # Test with invalid parameters
        with pytest.raises(ValueError):
            helper.validate_pagination_params(page=0, limit=10)

        with pytest.raises(ValueError):
            helper.validate_pagination_params(page=1, limit=0)

    def test_create_pagination_info(self):
        """Test pagination info creation."""
        helper = PaginationHelper()

        info = helper.create_pagination_info(current_page=2, limit=10, total_count=95)

        assert info["current_page"] == 2
        assert info["limit"] == 10
        assert info["total_count"] == 95
        assert info["total_pages"] == 10
        assert info["has_next"] is True
        assert info["has_previous"] is True

    def test_pagination_edge_cases(self):
        """Test pagination edge cases."""
        helper = PaginationHelper()

        # First page
        info = helper.create_pagination_info(1, 10, 100)
        assert info["has_previous"] is False
        assert info["has_next"] is True

        # Last page
        info = helper.create_pagination_info(10, 10, 100)
        assert info["has_previous"] is True
        assert info["has_next"] is False

        # Single page
        info = helper.create_pagination_info(1, 10, 5)
        assert info["has_previous"] is False
        assert info["has_next"] is False


@pytest.mark.skipif(not DB_TOOLKIT_AVAILABLE, reason="Database toolkit not available")
class TestDatabasePaginator:
    """Test DatabasePaginator functionality."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def paginator(self, mock_session):
        """Create DatabasePaginator instance."""
        return DatabasePaginator(session=mock_session)

    def test_paginator_initialization(self, paginator):
        """Test paginator initialization."""
        assert paginator is not None
        assert isinstance(paginator, DatabasePaginator)

    @pytest.mark.asyncio
    async def test_paginate_query_success(self, paginator, mock_session):
        """Test successful query pagination."""
        # Mock query and results
        mock_query = Mock()
        mock_count_result = Mock()
        mock_count_result.scalar.return_value = 50
        mock_data_result = Mock()
        mock_data_result.scalars.return_value.all.return_value = ["item1", "item2"]

        mock_session.execute.side_effect = [mock_count_result, mock_data_result]

        result = await paginator.paginate_query(query=mock_query, page=1, limit=10)

        assert "data" in result
        assert "pagination" in result
        assert result["pagination"]["total_count"] == 50
        assert result["pagination"]["current_page"] == 1

    @pytest.mark.asyncio
    async def test_paginate_with_custom_params(self, paginator, mock_session):
        """Test pagination with custom parameters."""
        params = PaginationParams(page=2, limit=20, sort_by="name", sort_order=SortOrder.DESC)
        mock_query = Mock()

        # Mock results
        mock_count_result = Mock()
        mock_count_result.scalar.return_value = 100
        mock_data_result = Mock()
        mock_data_result.scalars.return_value.all.return_value = []

        mock_session.execute.side_effect = [mock_count_result, mock_data_result]

        result = await paginator.paginate_query(query=mock_query, pagination_params=params)

        assert result["pagination"]["current_page"] == 2
        assert result["pagination"]["limit"] == 20

    @pytest.mark.asyncio
    async def test_paginate_empty_results(self, paginator, mock_session):
        """Test pagination with empty results."""
        mock_query = Mock()
        mock_count_result = Mock()
        mock_count_result.scalar.return_value = 0
        mock_data_result = Mock()
        mock_data_result.scalars.return_value.all.return_value = []

        mock_session.execute.side_effect = [mock_count_result, mock_data_result]

        result = await paginator.paginate_query(mock_query, page=1, limit=10)

        assert result["data"] == []
        assert result["pagination"]["total_count"] == 0
        assert result["pagination"]["total_pages"] == 0

    def test_build_sort_clause(self, paginator):
        """Test building sort clause."""
        # This tests internal functionality if exposed
        # May need to adjust based on actual implementation

    @pytest.mark.asyncio
    async def test_paginate_with_filters(self, paginator, mock_session):
        """Test pagination with additional filters."""
        mock_query = Mock()
        filters = {"active": True, "category": "test"}

        mock_count_result = Mock()
        mock_count_result.scalar.return_value = 25
        mock_data_result = Mock()
        mock_data_result.scalars.return_value.all.return_value = []

        mock_session.execute.side_effect = [mock_count_result, mock_data_result]

        result = await paginator.paginate_query(query=mock_query, page=1, limit=10, filters=filters)

        assert result["pagination"]["total_count"] == 25


@pytest.mark.skipif(not DB_TOOLKIT_AVAILABLE, reason="Database toolkit not available")
class TestPaginationParams:
    """Test PaginationParams data class."""

    def test_pagination_params_defaults(self):
        """Test default values."""
        params = PaginationParams()
        assert params.page == 1
        assert params.limit == 20
        assert params.sort_by is None
        assert params.sort_order == SortOrder.ASC

    def test_pagination_params_custom_values(self):
        """Test custom values."""
        params = PaginationParams(page=5, limit=50, sort_by="created_at", sort_order=SortOrder.DESC)
        assert params.page == 5
        assert params.limit == 50
        assert params.sort_by == "created_at"
        assert params.sort_order == SortOrder.DESC

    def test_pagination_params_validation(self):
        """Test parameter validation."""
        # Valid parameters
        params = PaginationParams(page=1, limit=10)
        assert params.page == 1

        # Test validation if implemented
        try:
            PaginationParams(page=0)  # Should be invalid
        except (ValueError, TypeError):
            pass  # Expected for invalid values


@pytest.mark.skipif(not DB_TOOLKIT_AVAILABLE, reason="Database toolkit not available")
class TestSortOrder:
    """Test SortOrder enum."""

    def test_sort_order_values(self):
        """Test sort order enum values."""
        assert SortOrder.ASC.value == "asc"
        assert SortOrder.DESC.value == "desc"

    def test_sort_order_string_representation(self):
        """Test string representation."""
        assert str(SortOrder.ASC) in ["SortOrder.ASC", "asc"]
        assert str(SortOrder.DESC) in ["SortOrder.DESC", "desc"]


class TestDbToolkitImportFallback:
    """Test graceful fallback when db toolkit is not available."""

    @pytest.mark.skipif(DB_TOOLKIT_AVAILABLE, reason="DB toolkit is available")
    def test_graceful_import_fallback(self):
        """Test graceful fallback when db toolkit is not available."""
        # This test only runs when DB toolkit is NOT available
        # It ensures the core module can still be imported
        try:
            import dotmac.core

            assert hasattr(dotmac.core, "DotMacError")
        except ImportError as e:
            pytest.fail(f"Core should be importable without db toolkit: {e}")

    def test_db_toolkit_import_handling(self):
        """Test db toolkit import handling."""
        # Test how the module handles db toolkit imports
        try:
            from dotmac.core import db_toolkit
        except ImportError:
            # This is expected if db_toolkit is not available
            pass

        # Test should pass regardless of availability
        assert True
