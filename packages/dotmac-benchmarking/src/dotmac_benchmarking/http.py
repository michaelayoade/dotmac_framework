"""
HTTP benchmarking utilities.

Requires the 'http' extra: pip install dotmac-benchmarking[http]
"""

import time
from typing import Any

try:
    import httpx
    HTTP_AVAILABLE = True
except ImportError:
    httpx = None
    HTTP_AVAILABLE = False


async def benchmark_http_request(
    client: "httpx.AsyncClient",
    method: str,
    url: str,
    *,
    timeout: float = 30.0,
    **kwargs: Any
) -> dict[str, Any]:
    """
    Benchmark a single HTTP request.
    
    Args:
        client: httpx AsyncClient instance
        method: HTTP method (GET, POST, etc.)
        url: Request URL
        timeout: Request timeout in seconds
        **kwargs: Additional arguments passed to httpx request
        
    Returns:
        Dictionary with timing and response information
        
    Raises:
        ImportError: If httpx is not installed
        
    Example:
        import httpx
        from dotmac_benchmarking.http import benchmark_http_request
        
        async def main():
            async with httpx.AsyncClient() as client:
                result = await benchmark_http_request(
                    client, "GET", "https://api.example.com/health"
                )
                print(f"Response time: {result['duration']:.3f}s")
                print(f"Status: {result['status_code']}")
    """
    if not HTTP_AVAILABLE:
        raise ImportError(
            "HTTP benchmarking requires httpx. Install with: pip install dotmac-benchmarking[http]"
        )

    start_time = time.perf_counter()

    try:
        response = await client.request(
            method,
            url,
            timeout=timeout,
            **kwargs
        )

        duration = time.perf_counter() - start_time

        return {
            "duration": duration,
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "content_length": len(response.content) if response.content else 0,
            "url": str(response.url),
            "method": method,
            "success": 200 <= response.status_code < 300,
            "timestamp": time.time()
        }

    except Exception as e:
        duration = time.perf_counter() - start_time

        return {
            "duration": duration,
            "error": str(e),
            "error_type": type(e).__name__,
            "url": url,
            "method": method,
            "success": False,
            "timestamp": time.time()
        }


async def benchmark_http_batch(
    client: "httpx.AsyncClient",
    requests: list[dict[str, Any]],
    *,
    concurrent: bool = True,
    max_concurrency: int = 10
) -> list[dict[str, Any]]:
    """
    Benchmark multiple HTTP requests.
    
    Args:
        client: httpx AsyncClient instance
        requests: List of request configs, each with 'method', 'url', and optional kwargs
        concurrent: Whether to run requests concurrently
        max_concurrency: Maximum concurrent requests (if concurrent=True)
        
    Returns:
        List of benchmark results for each request
        
    Example:
        requests = [
            {"method": "GET", "url": "https://api.example.com/users"},
            {"method": "GET", "url": "https://api.example.com/orders"},
        ]
        
        async with httpx.AsyncClient() as client:
            results = await benchmark_http_batch(client, requests)
    """
    if not HTTP_AVAILABLE:
        raise ImportError(
            "HTTP benchmarking requires httpx. Install with: pip install dotmac-benchmarking[http]"
        )

    if concurrent:
        import asyncio

        semaphore = asyncio.Semaphore(max_concurrency)

        async def limited_request(req_config: dict[str, Any]) -> dict[str, Any]:
            async with semaphore:
                return await benchmark_http_request(
                    client,
                    req_config.pop("method"),
                    req_config.pop("url"),
                    **req_config
                )

        tasks = [limited_request(req.copy()) for req in requests]
        return await asyncio.gather(*tasks)

    else:
        results = []
        for req_config in requests:
            result = await benchmark_http_request(
                client,
                req_config["method"],
                req_config["url"],
                **{k: v for k, v in req_config.items() if k not in ("method", "url")}
            )
            results.append(result)
        return results
