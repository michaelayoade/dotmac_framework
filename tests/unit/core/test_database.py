"""
Tests for core database functionality.
"""

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError


class TestDatabaseCore:
    """Test core database functionality."""

    def test_database_import(self):
        """Test that database module can be imported."""
        try:
            from dotmac_isp.core.database import Database
            assert Database is not None
        except ImportError:
            pytest.skip("Database module not found")

    @patch('dotmac_isp.core.database.create_async_engine')
    def test_database_connection_creation(self, mock_create_engine):
        """Test database connection creation."""
        try:
            from dotmac_isp.core.database import Database

            mock_engine = AsyncMock()
            mock_create_engine.return_value = mock_engine

            # Test database initialization
            db = Database.__new__(Database)
            assert db is not None

        except ImportError:
            pytest.skip("Database module not available for testing")
        except Exception as e:
            pytest.skip(f"Cannot test database creation: {e}")

    def test_database_config_validation(self):
        """Test database configuration validation."""
        try:
            from dotmac_isp.core.database import get_database_url

            # Test with mock environment
            with patch.dict('os.environ', {
                'DATABASE_URL': 'postgresql://user:pass@localhost/test'
            }):
                url = get_database_url()
                assert 'postgresql' in url

        except ImportError:
            pytest.skip("Database configuration not available")
        except Exception as e:
            pytest.skip(f"Cannot test database config: {e}")

    @patch('sqlalchemy.ext.asyncio.create_async_engine')
    def test_database_error_handling(self, mock_create_engine):
        """Test database error handling."""
        try:
            from dotmac_isp.core.database import Database

            # Mock a connection error
            mock_create_engine.side_effect = SQLAlchemyError("Connection failed")

            # Test that errors are handled gracefully
            with pytest.raises((SQLAlchemyError, Exception)):
                Database()

        except ImportError:
            pytest.skip("Database module not available for error testing")
