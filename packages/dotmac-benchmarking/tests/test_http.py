"""
Tests for HTTP benchmarking functionality.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from dotmac_benchmarking.http import benchmark_http_batch, benchmark_http_request


class TestHttpBenchmarking:
    """Test HTTP benchmarking with mocked httpx."""

    @patch('dotmac_benchmarking.http.HTTP_AVAILABLE', True)
    @patch('dotmac_benchmarking.http.httpx')
    async def test_benchmark_http_request_success(self, mock_httpx):
        """Test successful HTTP request benchmarking."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.content = b'{"test":"data"}'
        mock_response.url = "https://api.example.com/test"

        # Setup mock client
        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response

        result = await benchmark_http_request(
            mock_client, 
            "GET", 
            "https://api.example.com/test"
        )

        assert result["success"] is True
        assert result["status_code"] == 200
        assert result["method"] == "GET"
        assert result["url"] == "https://api.example.com/test"
        assert result["content_length"] == 15
        assert "duration" in result
        assert "timestamp" in result
        assert result["headers"] == {"Content-Type": "application/json"}

        # Verify client was called correctly
        mock_client.request.assert_called_once_with(
            "GET", 
            "https://api.example.com/test", 
            timeout=30.0
        )

    @patch('dotmac_benchmarking.http.HTTP_AVAILABLE', True)
    @patch('dotmac_benchmarking.http.httpx')
    async def test_benchmark_http_request_with_kwargs(self, mock_httpx):
        """Test HTTP request with additional kwargs."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.headers = {}
        mock_response.content = b''
        mock_response.url = "https://api.example.com/users"

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response

        result = await benchmark_http_request(
            mock_client,
            "POST",
            "https://api.example.com/users",
            timeout=60.0,
            json={"name": "test"},
            headers={"Authorization": "Bearer token"}
        )

        assert result["success"] is True
        assert result["status_code"] == 201
        assert result["content_length"] == 0

        # Verify kwargs were passed through
        mock_client.request.assert_called_once_with(
            "POST",
            "https://api.example.com/users",
            timeout=60.0,
            json={"name": "test"},
            headers={"Authorization": "Bearer token"}
        )

    @patch('dotmac_benchmarking.http.HTTP_AVAILABLE', True)
    @patch('dotmac_benchmarking.http.httpx')
    async def test_benchmark_http_request_error(self, mock_httpx):
        """Test HTTP request error handling."""
        mock_client = AsyncMock()
        mock_client.request.side_effect = Exception("Connection timeout")

        result = await benchmark_http_request(
            mock_client,
            "GET",
            "https://api.example.com/test"
        )

        assert result["success"] is False
        assert result["error"] == "Connection timeout"
        assert result["error_type"] == "Exception"
        assert result["method"] == "GET"
        assert result["url"] == "https://api.example.com/test"
        assert "duration" in result
        assert "timestamp" in result

    @patch('dotmac_benchmarking.http.HTTP_AVAILABLE', False)
    async def test_benchmark_http_request_no_httpx(self):
        """Test error when httpx is not available."""
        mock_client = MagicMock()

        with pytest.raises(ImportError, match="HTTP benchmarking requires httpx"):
            await benchmark_http_request(mock_client, "GET", "https://example.com")

    @patch('dotmac_benchmarking.http.HTTP_AVAILABLE', True)
    @patch('dotmac_benchmarking.http.benchmark_http_request')
    async def test_benchmark_http_batch_sequential(self, mock_benchmark):
        """Test batch HTTP requests in sequential mode."""
        # Setup mock responses
        mock_benchmark.side_effect = [
            {"duration": 0.1, "status_code": 200, "success": True},
            {"duration": 0.2, "status_code": 404, "success": False}
        ]

        mock_client = AsyncMock()
        requests = [
            {"method": "GET", "url": "https://example.com/1"},
            {"method": "GET", "url": "https://example.com/2", "timeout": 5.0}
        ]

        results = await benchmark_http_batch(mock_client, requests, concurrent=False)

        assert len(results) == 2
        assert results[0]["status_code"] == 200
        assert results[1]["status_code"] == 404

        # Verify calls were made sequentially
        assert mock_benchmark.call_count == 2

    @patch('dotmac_benchmarking.http.HTTP_AVAILABLE', True)  
    @patch('dotmac_benchmarking.http.benchmark_http_request')
    async def test_benchmark_http_batch_concurrent(self, mock_benchmark):
        """Test batch HTTP requests in concurrent mode."""
        # Setup mock responses
        mock_benchmark.side_effect = [
            {"duration": 0.1, "status_code": 200, "success": True},
            {"duration": 0.2, "status_code": 200, "success": True}
        ]

        mock_client = AsyncMock()
        requests = [
            {"method": "GET", "url": "https://example.com/1"},
            {"method": "GET", "url": "https://example.com/2"}
        ]

        results = await benchmark_http_batch(
            mock_client, 
            requests, 
            concurrent=True, 
            max_concurrency=2
        )

        assert len(results) == 2
        assert all(r["success"] for r in results)

        # Verify calls were made
        assert mock_benchmark.call_count == 2

    @patch('dotmac_benchmarking.http.HTTP_AVAILABLE', False)
    async def test_benchmark_http_batch_no_httpx(self):
        """Test batch benchmarking error when httpx not available."""
        mock_client = MagicMock()
        requests = [{"method": "GET", "url": "https://example.com"}]

        with pytest.raises(ImportError, match="HTTP benchmarking requires httpx"):
            await benchmark_http_batch(mock_client, requests)

    @patch('dotmac_benchmarking.http.HTTP_AVAILABLE', True)
    @patch('dotmac_benchmarking.http.httpx')
    async def test_benchmark_http_request_4xx_error(self, mock_httpx):
        """Test HTTP request with 4xx status code."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.headers = {}
        mock_response.content = b'Not Found'
        mock_response.url = "https://api.example.com/missing"

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response

        result = await benchmark_http_request(
            mock_client,
            "GET", 
            "https://api.example.com/missing"
        )

        # 4xx should be marked as unsuccessful
        assert result["success"] is False
        assert result["status_code"] == 404
        assert result["content_length"] == 9

    @patch('dotmac_benchmarking.http.HTTP_AVAILABLE', True)
    @patch('dotmac_benchmarking.http.httpx') 
    async def test_benchmark_http_request_empty_content(self, mock_httpx):
        """Test HTTP request with no content."""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.headers = {}
        mock_response.content = None  # No content
        mock_response.url = "https://api.example.com/delete"

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response

        result = await benchmark_http_request(
            mock_client,
            "DELETE",
            "https://api.example.com/delete"
        )

        assert result["success"] is True
        assert result["status_code"] == 204
        assert result["content_length"] == 0