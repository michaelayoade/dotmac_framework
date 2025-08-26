"""Transport layer contracts for SDK communication."""

from datetime import datetime
from typing import Any, Dict, Optional, List
from dataclasses import dataclass
from enum import Enum


class RequestMethod(str, Enum):
    """HTTP request methods."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class TransportProtocol(str, Enum):
    """Transport protocols."""

    HTTP = "http"
    HTTPS = "https"
    GRPC = "grpc"
    WEBSOCKET = "websocket"
    REDIS = "redis"
    KAFKA = "kafka"


@dataclass
class RequestContext:
    """Request context for SDK operations."""

    tenant_id: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    correlation_id: Optional[str] = None
    request_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        """Initialize context with defaults."""
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
        if self.headers is None:
            self.headers = {}
        if self.metadata is None:
            self.metadata = {}


@dataclass
class TransportConfig:
    """Transport configuration."""

    protocol: TransportProtocol = TransportProtocol.HTTPS
    host: str = "localhost"
    port: int = 443
    base_path: str = "/api/v1"
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    verify_ssl: bool = True
    headers: Optional[Dict[str, str]] = None
    auth_token: Optional[str] = None

    def __post_init__(self):
        """Initialize config with defaults."""
        if self.headers is None:
            self.headers = {}


@dataclass
class RequestMessage:
    """Request message structure."""

    method: RequestMethod
    endpoint: str
    headers: Optional[Dict[str, str]] = None
    query_params: Optional[Dict[str, Any]] = None
    body: Optional[Dict[str, Any]] = None
    context: Optional[RequestContext] = None
    timeout: Optional[float] = None

    def __post_init__(self):
        """Initialize request with defaults."""
        if self.headers is None:
            self.headers = {}
        if self.query_params is None:
            self.query_params = {}


@dataclass
class ResponseMessage:
    """Response message structure."""

    status_code: int
    headers: Dict[str, str]
    body: Optional[Dict[str, Any]] = None
    raw_body: Optional[str] = None
    error: Optional[str] = None
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        """Initialize response with defaults."""
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)

    @property
    def is_success(self) -> bool:
        """Check if response indicates success."""
        return 200 <= self.status_code < 300

    @property
    def is_client_error(self) -> bool:
        """Check if response indicates client error."""
        return 400 <= self.status_code < 500

    @property
    def is_server_error(self) -> bool:
        """Check if response indicates server error."""
        return 500 <= self.status_code < 600


@dataclass
class EventMessage:
    """Event message for asynchronous communication."""

    event_type: str
    payload: Dict[str, Any]
    context: Optional[RequestContext] = None
    timestamp: Optional[datetime] = None
    event_id: Optional[str] = None
    version: str = "1.0"

    def __post_init__(self):
        """Initialize event with defaults."""
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


@dataclass
class BatchRequest:
    """Batch request for multiple operations."""

    requests: List[RequestMessage]
    context: Optional[RequestContext] = None
    timeout: Optional[float] = None
    fail_fast: bool = True

    @property
    def request_count(self) -> int:
        """Get number of requests in batch."""
        return len(self.requests)


@dataclass
class BatchResponse:
    """Batch response for multiple operations."""

    responses: List[ResponseMessage]
    context: Optional[RequestContext] = None
    timestamp: Optional[datetime] = None
    success_count: int = 0
    error_count: int = 0

    def __post_init__(self):
        """Initialize batch response."""
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)

        # Count successes and errors
        self.success_count = sum(1 for r in self.responses if r.is_success)
        self.error_count = len(self.responses) - self.success_count

    @property
    def all_successful(self) -> bool:
        """Check if all requests were successful."""
        return self.error_count == 0


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""

    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    expected_recovery_time: float = 10.0
    monitor_failures: bool = True


@dataclass
class LoadBalancerConfig:
    """Load balancer configuration."""

    strategy: str = "round_robin"  # round_robin, weighted, least_connections
    health_check_interval: float = 30.0
    max_retries_per_endpoint: int = 2
    enable_sticky_sessions: bool = False
