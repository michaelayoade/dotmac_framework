"""
API Endpoint Benchmarking Framework

Comprehensive API performance testing including:
- HTTP endpoint load testing
- Authentication performance testing
- Request/response size analysis
- Error rate monitoring
- Multi-tenant API performance isolation
- Rate limiting and throttling tests
"""

import asyncio
import aiohttp
import time
import json
import statistics
from typing import Any, Dict, List, Optional, Union, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
import ssl

from ...core.logging import get_logger
from ...tenant.identity import TenantContext
from ...api.exception_handlers import standard_exception_handler

logger = get_logger(__name__)


class HttpMethod(str, Enum):
    """HTTP methods for API testing"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


@dataclass
class ApiRequest:
    """API request configuration"""
    method: HttpMethod
    endpoint: str
    headers: Dict[str, str] = field(default_factory=dict)
    params: Dict[str, str] = field(default_factory=dict)
    json_body: Optional[Dict[str, Any]] = None
    data: Optional[Union[str, bytes]] = None
    timeout: float = 30.0
    
    # Authentication
    auth_token: Optional[str] = None
    basic_auth: Optional[Tuple[str, str]] = None
    
    # Tenant context
    tenant_context: Optional[TenantContext] = None


@dataclass
class ApiResponse:
    """API response metrics"""
    status_code: int
    response_time: float
    response_size: int
    content_type: Optional[str] = None
    error_message: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    content: Optional[str] = None


@dataclass
class ApiLoadTestConfig:
    """Configuration for API load testing"""
    concurrent_users: int = 10
    requests_per_user: int = 100
    ramp_up_duration: float = 10.0
    test_duration: Optional[float] = None
    think_time: float = 0.0
    
    # Request patterns
    request_distribution: Dict[str, float] = field(default_factory=dict)  # endpoint -> weight
    
    # Authentication
    shared_auth: bool = True
    auth_refresh_interval: float = 3600.0  # 1 hour
    
    # Error handling
    max_retries: int = 3
    retry_delay: float = 1.0
    acceptable_error_rate: float = 0.05  # 5%
    
    # Performance thresholds
    max_avg_response_time: float = 2.0
    max_p95_response_time: float = 5.0
    min_requests_per_second: float = 10.0


@dataclass
class ApiLoadTestResults:
    """Results from API load testing"""
    test_name: str
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    
    # Request statistics
    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate: float
    
    # Performance metrics
    requests_per_second: float
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    percentile_50: float
    percentile_95: float
    percentile_99: float
    
    # Response analysis
    avg_response_size: float
    total_bytes_transferred: int
    
    # Error analysis
    error_breakdown: Dict[int, int] = field(default_factory=dict)  # status_code -> count
    error_messages: List[str] = field(default_factory=list)
    
    # Endpoint breakdown
    endpoint_performance: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # Tenant performance (if applicable)
    tenant_performance: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # Raw measurements
    response_times: List[float] = field(default_factory=list)
    response_sizes: List[int] = field(default_factory=list)


class ApiEndpointBenchmarker:
    """
    Comprehensive API endpoint benchmarking framework.
    
    Features:
    - Load testing with concurrent users
    - Authentication performance testing
    - Multi-tenant performance isolation
    - Rate limiting and throttling validation
    - Error rate analysis and monitoring
    - Response time and throughput measurement
    - Custom request pattern simulation
    """
    
    def __init__(self, base_url: str, default_headers: Optional[Dict[str, str]] = None):
        self.base_url = base_url
        self.default_headers = default_headers or {}
        
        # Session management
        self._session: Optional[aiohttp.ClientSession] = None
        self._connector: Optional[aiohttp.TCPConnector] = None
        
        # Authentication cache
        self._auth_cache: Dict[str, str] = {}
        
        # Test results
        self.test_history: List[ApiLoadTestResults] = []
    
    async def __aenter__(self):
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._close_session()
    
    async def _ensure_session(self):
        """Ensure aiohttp session is created"""
        if not self._session:
            # Configure SSL context for HTTPS
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Create connector with connection pooling
            self._connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=30,
                ssl=ssl_context,
                enable_cleanup_closed=True
            )
            
            # Create session with default settings
            timeout = aiohttp.ClientTimeout(total=60)
            self._session = aiohttp.ClientSession(
                connector=self._connector,
                timeout=timeout,
                headers=self.default_headers
            )
    
    async def _close_session(self):
        """Close aiohttp session"""
        if self._session:
            await self._session.close()
            self._session = None
        
        if self._connector:
            await self._connector.close()
            self._connector = None
    
    @standard_exception_handler
    async def benchmark_single_request(
        self,
        request: ApiRequest,
        iterations: int = 1000
    ) -> Dict[str, Any]:
        """
        Benchmark a single API request.
        
        Args:
            request: API request configuration
            iterations: Number of iterations to run
            
        Returns:
            Benchmark results
        """
        await self._ensure_session()
        
        logger.info(f"Benchmarking {request.method.value} {request.endpoint} ({iterations} iterations)")
        
        responses = []
        start_time = time.time()
        
        for i in range(iterations):
            try:
                response = await self._execute_request(request)
                responses.append(response)
                
                # Small delay to avoid overwhelming the server
                if i < iterations - 1:
                    await asyncio.sleep(0.001)  # 1ms delay
            
            except Exception as e:
                logger.debug(f"Request {i} failed: {e}")
                error_response = ApiResponse(
                    status_code=0,
                    response_time=0.0,
                    response_size=0,
                    error_message=str(e)
                )
                responses.append(error_response)
        
        execution_time = time.time() - start_time
        
        # Calculate metrics
        successful_responses = [r for r in responses if 200 <= r.status_code < 400]
        failed_responses = [r for r in responses if r.status_code == 0 or r.status_code >= 400]
        
        response_times = [r.response_time for r in responses if r.response_time > 0]
        response_sizes = [r.response_size for r in responses]
        
        results = {
            "request": {
                "method": request.method.value,
                "endpoint": request.endpoint,
                "iterations": iterations
            },
            "performance": {
                "total_time": execution_time,
                "requests_per_second": iterations / execution_time,
                "avg_response_time": statistics.mean(response_times) if response_times else 0,
                "min_response_time": min(response_times) if response_times else 0,
                "max_response_time": max(response_times) if response_times else 0,
                "p50_response_time": self._calculate_percentile(response_times, 50),
                "p95_response_time": self._calculate_percentile(response_times, 95),
                "p99_response_time": self._calculate_percentile(response_times, 99)
            },
            "reliability": {
                "success_count": len(successful_responses),
                "failure_count": len(failed_responses),
                "success_rate": len(successful_responses) / iterations * 100
            },
            "data_transfer": {
                "avg_response_size": statistics.mean(response_sizes) if response_sizes else 0,
                "total_bytes": sum(response_sizes),
                "throughput_mbps": sum(response_sizes) / execution_time / (1024 * 1024) if execution_time > 0 else 0
            }
        }
        
        return results
    
    @standard_exception_handler
    async def run_load_test(
        self,
        requests: List[ApiRequest],
        config: ApiLoadTestConfig,
        test_name: str = "api_load_test"
    ) -> ApiLoadTestResults:
        """
        Run comprehensive API load test.
        
        Args:
            requests: List of API requests to test
            config: Load test configuration
            test_name: Name for the test run
            
        Returns:
            Detailed load test results
        """
        await self._ensure_session()
        
        logger.info(f"Starting API load test: {test_name}")
        logger.info(f"Users: {config.concurrent_users}, Requests/user: {config.requests_per_user}")
        
        start_time = datetime.now(timezone.utc)
        
        # Prepare request distribution
        if not config.request_distribution:
            # Equal distribution
            weight = 1.0 / len(requests)
            config.request_distribution = {req.endpoint: weight for req in requests}
        
        # Run concurrent user sessions
        all_responses = []
        user_tasks = []
        
        for user_id in range(config.concurrent_users):
            # Calculate ramp-up delay
            ramp_delay = (user_id / config.concurrent_users) * config.ramp_up_duration
            
            task = asyncio.create_task(
                self._simulate_user_session(
                    user_id, requests, config, ramp_delay
                )
            )
            user_tasks.append(task)
        
        # Wait for all user sessions to complete
        try:
            user_results = await asyncio.gather(*user_tasks, return_exceptions=True)
            
            # Aggregate responses
            for result in user_results:
                if isinstance(result, list):
                    all_responses.extend(result)
                elif isinstance(result, Exception):
                    logger.error(f"User session failed: {result}")
        
        except Exception as e:
            logger.error(f"Load test failed: {e}")
        
        end_time = datetime.now(timezone.utc)
        
        # Calculate comprehensive results
        results = self._calculate_load_test_results(
            test_name, start_time, end_time, all_responses, requests, config
        )
        
        self.test_history.append(results)
        
        logger.info(f"✅ Load test completed: {test_name}")
        logger.info(f"   Total requests: {results.total_requests}")
        logger.info(f"   Success rate: {results.success_rate:.1f}%")
        logger.info(f"   Avg response time: {results.avg_response_time:.3f}s")
        logger.info(f"   Requests/sec: {results.requests_per_second:.1f}")
        
        return results
    
    async def _simulate_user_session(
        self,
        user_id: int,
        requests: List[ApiRequest],
        config: ApiLoadTestConfig,
        ramp_delay: float
    ) -> List[ApiResponse]:
        """Simulate a single user session"""
        
        # Wait for ramp-up
        if ramp_delay > 0:
            await asyncio.sleep(ramp_delay)
        
        user_responses = []
        
        for request_num in range(config.requests_per_user):
            try:
                # Select request based on distribution
                request = self._select_request(requests, config.request_distribution)
                
                # Execute request
                response = await self._execute_request(request)
                response.headers['user_id'] = str(user_id)
                response.headers['request_num'] = str(request_num)
                
                user_responses.append(response)
                
                # Think time between requests
                if config.think_time > 0 and request_num < config.requests_per_user - 1:
                    await asyncio.sleep(config.think_time)
            
            except Exception as e:
                error_response = ApiResponse(
                    status_code=0,
                    response_time=0.0,
                    response_size=0,
                    error_message=str(e)
                )
                error_response.headers['user_id'] = str(user_id)
                error_response.headers['request_num'] = str(request_num)
                user_responses.append(error_response)
        
        return user_responses
    
    def _select_request(
        self,
        requests: List[ApiRequest],
        distribution: Dict[str, float]
    ) -> ApiRequest:
        """Select request based on distribution weights"""
        
        import random
        
        # Simple weighted selection
        rand_value = random.random()
        cumulative_weight = 0.0
        
        for request in requests:
            weight = distribution.get(request.endpoint, 0.0)
            cumulative_weight += weight
            
            if rand_value <= cumulative_weight:
                return request
        
        # Fallback to first request
        return requests[0]
    
    async def _execute_request(self, request: ApiRequest) -> ApiResponse:
        """Execute a single API request and measure performance"""
        
        # Build full URL
        url = urljoin(self.base_url, request.endpoint)
        
        # Prepare headers
        headers = self.default_headers.copy()
        headers.update(request.headers)
        
        # Add authentication
        if request.auth_token:
            headers['Authorization'] = f"Bearer {request.auth_token}"
        
        # Add tenant context
        if request.tenant_context:
            headers['X-Tenant-ID'] = request.tenant_context.tenant_id
            if request.tenant_context.subdomain:
                headers['X-Tenant-Subdomain'] = request.tenant_context.subdomain
        
        # Prepare request parameters
        request_kwargs = {
            'url': url,
            'method': request.method.value,
            'headers': headers,
            'params': request.params,
            'timeout': aiohttp.ClientTimeout(total=request.timeout)
        }
        
        if request.json_body:
            request_kwargs['json'] = request.json_body
        elif request.data:
            request_kwargs['data'] = request.data
        
        if request.basic_auth:
            request_kwargs['auth'] = aiohttp.BasicAuth(*request.basic_auth)
        
        # Execute request with timing
        start_time = time.time()
        
        try:
            async with self._session.request(**request_kwargs) as response:
                content = await response.text()
                response_time = time.time() - start_time
                
                return ApiResponse(
                    status_code=response.status,
                    response_time=response_time,
                    response_size=len(content.encode('utf-8')),
                    content_type=response.headers.get('content-type'),
                    headers=dict(response.headers),
                    content=content if len(content) < 1000 else content[:1000] + "..."  # Truncate large responses
                )
        
        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            return ApiResponse(
                status_code=408,  # Request Timeout
                response_time=response_time,
                response_size=0,
                error_message="Request timeout"
            )
        
        except Exception as e:
            response_time = time.time() - start_time
            return ApiResponse(
                status_code=0,
                response_time=response_time,
                response_size=0,
                error_message=str(e)
            )
    
    def _calculate_load_test_results(
        self,
        test_name: str,
        start_time: datetime,
        end_time: datetime,
        responses: List[ApiResponse],
        requests: List[ApiRequest],
        config: ApiLoadTestConfig
    ) -> ApiLoadTestResults:
        """Calculate comprehensive load test results"""
        
        duration = (end_time - start_time).total_seconds()
        
        # Basic counts
        total_requests = len(responses)
        successful_responses = [r for r in responses if 200 <= r.status_code < 400]
        failed_responses = [r for r in responses if r.status_code == 0 or r.status_code >= 400]
        
        successful_count = len(successful_responses)
        failed_count = len(failed_responses)
        success_rate = (successful_count / total_requests * 100) if total_requests > 0 else 0
        
        # Response time analysis
        response_times = [r.response_time for r in responses if r.response_time > 0]
        response_sizes = [r.response_size for r in responses]
        
        # Error analysis
        error_breakdown = {}
        error_messages = []
        
        for response in failed_responses:
            if response.status_code in error_breakdown:
                error_breakdown[response.status_code] += 1
            else:
                error_breakdown[response.status_code] = 1
            
            if response.error_message and len(error_messages) < 20:
                error_messages.append(response.error_message)
        
        # Endpoint performance breakdown
        endpoint_performance = {}
        for request in requests:
            endpoint_responses = [
                r for r in responses 
                if r.headers.get('endpoint') == request.endpoint or request.endpoint in str(r.headers)
            ]
            
            if endpoint_responses:
                endpoint_times = [r.response_time for r in endpoint_responses if r.response_time > 0]
                endpoint_performance[request.endpoint] = {
                    'avg_response_time': statistics.mean(endpoint_times) if endpoint_times else 0,
                    'request_count': len(endpoint_responses),
                    'success_rate': len([r for r in endpoint_responses if 200 <= r.status_code < 400]) / len(endpoint_responses) * 100
                }
        
        # Tenant performance (if applicable)
        tenant_performance = {}
        tenant_ids = set(r.headers.get('X-Tenant-ID', '') for r in responses if r.headers.get('X-Tenant-ID'))
        
        for tenant_id in tenant_ids:
            if tenant_id:
                tenant_responses = [r for r in responses if r.headers.get('X-Tenant-ID') == tenant_id]
                tenant_times = [r.response_time for r in tenant_responses if r.response_time > 0]
                
                tenant_performance[tenant_id] = {
                    'avg_response_time': statistics.mean(tenant_times) if tenant_times else 0,
                    'request_count': len(tenant_responses),
                    'success_rate': len([r for r in tenant_responses if 200 <= r.status_code < 400]) / len(tenant_responses) * 100
                }
        
        return ApiLoadTestResults(
            test_name=test_name,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration,
            total_requests=total_requests,
            successful_requests=successful_count,
            failed_requests=failed_count,
            success_rate=success_rate,
            requests_per_second=total_requests / duration if duration > 0 else 0,
            avg_response_time=statistics.mean(response_times) if response_times else 0,
            min_response_time=min(response_times) if response_times else 0,
            max_response_time=max(response_times) if response_times else 0,
            percentile_50=self._calculate_percentile(response_times, 50),
            percentile_95=self._calculate_percentile(response_times, 95),
            percentile_99=self._calculate_percentile(response_times, 99),
            avg_response_size=statistics.mean(response_sizes) if response_sizes else 0,
            total_bytes_transferred=sum(response_sizes),
            error_breakdown=error_breakdown,
            error_messages=error_messages,
            endpoint_performance=endpoint_performance,
            tenant_performance=tenant_performance,
            response_times=response_times if len(response_times) <= 10000 else response_times[:10000],  # Limit storage
            response_sizes=response_sizes if len(response_sizes) <= 10000 else response_sizes[:10000]
        )
    
    def _calculate_percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile value"""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        if index >= len(sorted_values):
            index = len(sorted_values) - 1
        return sorted_values[index]
    
    @standard_exception_handler
    async def test_authentication_performance(
        self,
        login_request: ApiRequest,
        authenticated_requests: List[ApiRequest],
        iterations: int = 100
    ) -> Dict[str, Any]:
        """
        Test authentication performance including login and authenticated requests.
        
        Args:
            login_request: Request for authentication/login
            authenticated_requests: Requests requiring authentication
            iterations: Number of auth cycles to test
            
        Returns:
            Authentication performance metrics
        """
        logger.info(f"Testing authentication performance ({iterations} cycles)")
        
        login_times = []
        request_times = []
        auth_failures = 0
        
        for i in range(iterations):
            try:
                # Time the login request
                start_time = time.time()
                login_response = await self._execute_request(login_request)
                login_time = time.time() - start_time
                
                if 200 <= login_response.status_code < 300:
                    login_times.append(login_time)
                    
                    # Extract auth token (assuming JSON response with token)
                    if login_response.content:
                        try:
                            auth_data = json.loads(login_response.content)
                            token = auth_data.get('token') or auth_data.get('access_token')
                            
                            if token:
                                # Test authenticated requests
                                for auth_req in authenticated_requests[:3]:  # Limit to first 3
                                    auth_req.auth_token = token
                                    auth_response = await self._execute_request(auth_req)
                                    
                                    if 200 <= auth_response.status_code < 300:
                                        request_times.append(auth_response.response_time)
                                    else:
                                        auth_failures += 1
                        except json.JSONDecodeError:
                            auth_failures += 1
                else:
                    auth_failures += 1
            
            except Exception as e:
                logger.debug(f"Auth test iteration {i} failed: {e}")
                auth_failures += 1
        
        return {
            "login_performance": {
                "avg_login_time": statistics.mean(login_times) if login_times else 0,
                "min_login_time": min(login_times) if login_times else 0,
                "max_login_time": max(login_times) if login_times else 0,
                "successful_logins": len(login_times),
                "login_success_rate": len(login_times) / iterations * 100
            },
            "authenticated_request_performance": {
                "avg_request_time": statistics.mean(request_times) if request_times else 0,
                "min_request_time": min(request_times) if request_times else 0,
                "max_request_time": max(request_times) if request_times else 0,
                "successful_requests": len(request_times)
            },
            "overall": {
                "total_auth_failures": auth_failures,
                "auth_failure_rate": auth_failures / (iterations * (len(authenticated_requests) + 1)) * 100
            }
        }
    
    def get_test_summary(self) -> Dict[str, Any]:
        """Get summary of all load test results"""
        
        if not self.test_history:
            return {"total_tests": 0, "message": "No tests executed"}
        
        total_tests = len(self.test_history)
        total_requests = sum(test.total_requests for test in self.test_history)
        avg_success_rate = statistics.mean([test.success_rate for test in self.test_history])
        avg_rps = statistics.mean([test.requests_per_second for test in self.test_history])
        avg_response_time = statistics.mean([test.avg_response_time for test in self.test_history])
        
        return {
            "total_tests": total_tests,
            "total_requests": total_requests,
            "average_success_rate": avg_success_rate,
            "average_requests_per_second": avg_rps,
            "average_response_time": avg_response_time,
            "test_names": [test.test_name for test in self.test_history],
            "latest_test": {
                "name": self.test_history[-1].test_name,
                "success_rate": self.test_history[-1].success_rate,
                "rps": self.test_history[-1].requests_per_second,
                "avg_response_time": self.test_history[-1].avg_response_time
            } if self.test_history else None
        }


# Convenience functions
async def quick_api_benchmark(
    base_url: str,
    endpoint: str,
    method: HttpMethod = HttpMethod.GET,
    iterations: int = 100,
    headers: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Quick API endpoint benchmark.
    
    Args:
        base_url: Base URL of the API
        endpoint: Endpoint to test
        method: HTTP method
        iterations: Number of requests
        headers: Optional headers
        
    Returns:
        Benchmark results
    """
    request = ApiRequest(
        method=method,
        endpoint=endpoint,
        headers=headers or {}
    )
    
    async with ApiEndpointBenchmarker(base_url) as benchmarker:
        return await benchmarker.benchmark_single_request(request, iterations)