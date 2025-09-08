"""
Base utilities for testing DotMac framework.
"""
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest


class TestBase:
    """Base class for DotMac tests with common utilities."""

    @pytest.fixture(autouse=True)
    def setup_test(self):
        """Setup that runs before each test."""
        self.mocks = {}

    def create_mock_service(self, name: str) -> AsyncMock:
        """Create a mock service with common async methods."""
        mock_service = AsyncMock()
        mock_service.create = AsyncMock(return_value={"id": f"mock_{name}_id"})
        mock_service.get = AsyncMock(return_value={"id": f"mock_{name}_id", "name": f"mock_{name}"})
        mock_service.update = AsyncMock(return_value={"id": f"mock_{name}_id", "updated": True})
        mock_service.delete = AsyncMock(return_value=True)
        mock_service.list = AsyncMock(return_value=[])

        self.mocks[name] = mock_service
        return mock_service

    def create_mock_response(self, status_code: int = 200, json_data: dict[Any, Any] = None) -> Mock:
        """Create a mock HTTP response."""
        mock_response = Mock()
        mock_response.status_code = status_code
        mock_response.json.return_value = json_data or {}
        return mock_response
