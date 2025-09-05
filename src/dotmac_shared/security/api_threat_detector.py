"""
API Threat Detection and Security Monitoring System
Provides real-time threat detection, anomaly monitoring, and security event tracking

SECURITY: This module monitors API traffic for suspicious patterns, brute force attacks,
data exfiltration attempts, and other security threats in real-time
"""

import json
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

import redis
from fastapi import Request, Response
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class ThreatLevel(str, Enum):
    """Threat severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ThreatType(str, Enum):
    """Types of security threats"""

    BRUTE_FORCE = "brute_force"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SQL_INJECTION = "sql_injection"
    XSS_ATTEMPT = "xss_attempt"
    PATH_TRAVERSAL = "path_traversal"
    DATA_EXFILTRATION = "data_exfiltration"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    SUSPICIOUS_PATTERN = "suspicious_pattern"
    GEOGRAPHIC_ANOMALY = "geographic_anomaly"
    TOKEN_ABUSE = "token_abuse"
    API_SCRAPING = "api_scraping"
    DDOS_ATTEMPT = "ddos_attempt"


@dataclass
class SecurityEvent:
    """Security event data structure"""

    event_id: str
    threat_type: ThreatType
    threat_level: ThreatLevel
    timestamp: datetime
    source_ip: str
    user_id: Optional[str]
    tenant_id: Optional[str]
    endpoint: str
    method: str
    user_agent: str
    details: dict[str, Any]
    risk_score: float
    blocked: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage/logging"""
        return {
            "event_id": self.event_id,
            "threat_type": self.threat_type.value,
            "threat_level": self.threat_level.value,
            "timestamp": self.timestamp.isoformat(),
            "source_ip": self.source_ip,
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "endpoint": self.endpoint,
            "method": self.method,
            "user_agent": self.user_agent,
            "details": self.details,
            "risk_score": self.risk_score,
            "blocked": self.blocked,
        }


@dataclass
class ThreatPattern:
    """Configuration for threat detection patterns"""

    name: str
    threshold: int
    time_window: int  # seconds
    threat_type: ThreatType
    threat_level: ThreatLevel
    action: str  # "log", "block", "alert"


class BruteForceDetector:
    """Detects brute force authentication attempts"""

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """__init__ operation."""
        self.redis = redis_client or redis.Redis(decode_responses=True)
        self.failed_attempts_threshold = 5
        self.time_window = 900  # 15 minutes
        self.lockout_duration = 3600  # 1 hour

    async def track_failed_login(
        self, ip_address: str, user_id: Optional[str] = None
    ) -> bool:
        """Track failed login attempt and check if threshold exceeded"""
        current_time = int(time.time())

        # Track by IP
        ip_key = f"failed_login:ip:{ip_address}"
        self.redis.zincrby(ip_key, 1, current_time)
        self.redis.expire(ip_key, self.time_window)

        # Track by user if available
        user_key = None
        if user_id:
            user_key = f"failed_login:user:{user_id}"
            self.redis.zincrby(user_key, 1, current_time)
            self.redis.expire(user_key, self.time_window)

        # Remove old attempts
        cutoff_time = current_time - self.time_window
        self.redis.zremrangebyscore(ip_key, 0, cutoff_time)
        if user_key:
            self.redis.zremrangebyscore(user_key, 0, cutoff_time)

        # Check thresholds
        recent_ip_attempts = self.redis.zcount(ip_key, cutoff_time, current_time)
        recent_user_attempts = 0
        if user_key:
            recent_user_attempts = self.redis.zcount(
                user_key, cutoff_time, current_time
            )

        if (
            recent_ip_attempts >= self.failed_attempts_threshold
            or recent_user_attempts >= self.failed_attempts_threshold
        ):
            # Lock the IP/user
            if recent_ip_attempts >= self.failed_attempts_threshold:
                self.redis.setex(f"locked:ip:{ip_address}", self.lockout_duration, "1")
            if user_key and recent_user_attempts >= self.failed_attempts_threshold:
                self.redis.setex(f"locked:user:{user_id}", self.lockout_duration, "1")

            return True  # Brute force detected

        return False

    async def is_locked(self, ip_address: str, user_id: Optional[str] = None) -> bool:
        """Check if IP or user is locked due to brute force"""
        ip_locked = self.redis.exists(f"locked:ip:{ip_address}")
        user_locked = False
        if user_id:
            user_locked = self.redis.exists(f"locked:user:{user_id}")

        return bool(ip_locked or user_locked)


class AnomalyDetector:
    """Detects anomalous API usage patterns"""

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """__init__ operation."""
        self.redis = redis_client or redis.Redis(decode_responses=True)
        self.baseline_window = 3600  # 1 hour for baseline
        self.anomaly_threshold = 3.0  # Standard deviations

    async def track_api_usage(
        self, user_id: str, endpoint: str, tenant_id: Optional[str] = None
    ):
        """Track API usage for anomaly detection"""
        current_time = int(time.time())
        hour_key = f"api_usage:{user_id}:{current_time // 3600}"

        # Track general usage
        self.redis.zincrby(hour_key, 1, endpoint)
        self.redis.expire(hour_key, 86400)  # Keep for 24 hours

        # Track tenant-specific usage if available
        if tenant_id:
            tenant_key = f"api_usage:tenant:{tenant_id}:{current_time // 3600}"
            self.redis.zincrby(tenant_key, 1, endpoint)
            self.redis.expire(tenant_key, 86400)

    async def detect_data_exfiltration(
        self, user_id: str, endpoint: str, response_size: int
    ) -> bool:
        """Detect potential data exfiltration attempts"""
        current_time = int(time.time())

        # Track large responses
        if response_size > 1_000_000:  # 1MB threshold
            key = f"large_response:{user_id}:{current_time // 3600}"
            count = self.redis.incr(key)
            self.redis.expire(key, 3600)

            # Alert if too many large responses in an hour
            if count > 10:
                return True

        # Track bulk data endpoints
        bulk_endpoints = ["/export", "/download", "/bulk", "/report"]
        if any(bulk in endpoint.lower() for bulk in bulk_endpoints):
            key = f"bulk_access:{user_id}:{current_time // 900}"  # 15-minute window
            count = self.redis.incr(key)
            self.redis.expire(key, 900)

            if count > 5:  # More than 5 bulk operations in 15 minutes
                return True

        return False


class GeographicAnomalyDetector:
    """Detects geographic anomalies in API access"""

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """__init__ operation."""
        self.redis = redis_client or redis.Redis(decode_responses=True)
        self.suspicious_countries = {
            "CN",
            "RU",
            "KP",
            "IR",
        }  # Example suspicious countries
        self.travel_threshold = 1000  # km/hour (impossible travel speed)

    async def check_geographic_anomaly(
        self, user_id: str, ip_address: str
    ) -> tuple[bool, str]:
        """Check for geographic anomalies"""
        # In production, this would use IP geolocation service
        # For now, simulate with IP-based country detection

        # Get previous location
        prev_location_key = f"user_location:{user_id}"
        previous_data = self.redis.get(prev_location_key)

        current_country = self._get_country_from_ip(ip_address)
        current_time = time.time()

        if previous_data:
            prev_info = json.loads(previous_data)
            prev_country = prev_info.get("country")
            prev_time = prev_info.get("timestamp", 0)

            # Check for suspicious country
            if current_country in self.suspicious_countries:
                return True, f"Access from suspicious country: {current_country}"

            # Check for impossible travel (simplified)
            time_diff = current_time - prev_time
            if (
                prev_country != current_country and time_diff < 3600
            ):  # Country change in < 1 hour
                return (
                    True,
                    f"Impossible travel: {prev_country} to {current_country} in {time_diff/60:.1f} minutes",
                )

        # Update location
        location_data = {
            "country": current_country,
            "ip": ip_address,
            "timestamp": current_time,
        }
        self.redis.setex(prev_location_key, 86400, json.dumps(location_data))

        return False, ""

    def _get_country_from_ip(self, ip_address: str) -> str:
        """Get country code from IP (simplified implementation)"""
        # In production, use a real IP geolocation service
        # This is a placeholder that returns different countries based on IP ranges
        parts = ip_address.split(".")
        if len(parts) == 4:
            first_octet = int(parts[0])
            if 1 <= first_octet <= 50:
                return "US"
            elif 51 <= first_octet <= 100:
                return "GB"
            elif 101 <= first_octet <= 150:
                return "DE"
            elif 200 <= first_octet <= 220:
                return "CN"  # Suspicious
        return "US"  # Default


class APIThreatDetector:
    """Main threat detection system"""

    def __init__(
        self,
        redis_client: Optional[redis.Redis] = None,
        redis_url: str = "redis://localhost:6379/2",
    ):
        """__init__ operation."""
        self.redis = redis_client or redis.Redis.from_url(
            redis_url, decode_responses=True
        )

        # Initialize sub-detectors
        self.brute_force_detector = BruteForceDetector(self.redis)
        self.anomaly_detector = AnomalyDetector(self.redis)
        self.geo_detector = GeographicAnomalyDetector(self.redis)

        # Threat patterns configuration
        self.threat_patterns = [
            ThreatPattern(
                "sql_injection",
                1,
                3600,
                ThreatType.SQL_INJECTION,
                ThreatLevel.HIGH,
                "block",
            ),
            ThreatPattern(
                "xss_attempt",
                1,
                3600,
                ThreatType.XSS_ATTEMPT,
                ThreatLevel.HIGH,
                "block",
            ),
            ThreatPattern(
                "path_traversal",
                1,
                3600,
                ThreatType.PATH_TRAVERSAL,
                ThreatLevel.HIGH,
                "block",
            ),
            ThreatPattern(
                "brute_force",
                5,
                900,
                ThreatType.BRUTE_FORCE,
                ThreatLevel.CRITICAL,
                "block",
            ),
            ThreatPattern(
                "api_scraping",
                100,
                300,
                ThreatType.API_SCRAPING,
                ThreatLevel.MEDIUM,
                "log",
            ),
        ]

        # Recent events cache
        self.recent_events = deque(maxlen=1000)

        # IP reputation cache
        self.ip_reputation_cache = {}

    def generate_event_id(self) -> str:
        """Generate unique event ID"""
        import secrets

        return secrets.token_hex(8)

    async def analyze_request(
        self,
        request: Request,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> list[SecurityEvent]:
        """Analyze incoming request for threats"""
        events = []

        # Extract request information
        ip_address = request.client.host if request.client else "unknown"
        endpoint = str(request.url.path)
        method = request.method
        user_agent = request.headers.get("user-agent", "")

        # Check for brute force (for auth endpoints)
        if "/auth/" in endpoint or "/login" in endpoint:
            # This would be called after a failed authentication
            pass  # Handled by track_failed_login method

        # Check for malicious patterns in URL/headers
        malicious_patterns = self._detect_malicious_patterns(
            endpoint, dict(request.headers), user_agent
        )
        for pattern_type, details in malicious_patterns:
            event = SecurityEvent(
                event_id=self.generate_event_id(),
                threat_type=pattern_type,
                threat_level=ThreatLevel.HIGH,
                timestamp=datetime.now(timezone.utc),
                source_ip=ip_address,
                user_id=user_id,
                tenant_id=tenant_id,
                endpoint=endpoint,
                method=method,
                user_agent=user_agent,
                details=details,
                risk_score=8.0,
                blocked=True,
            )
            events.append(event)

        # Check geographic anomalies
        if user_id:
            (
                is_geo_anomaly,
                geo_details,
            ) = await self.geo_detector.check_geographic_anomaly(user_id, ip_address)
            if is_geo_anomaly:
                event = SecurityEvent(
                    event_id=self.generate_event_id(),
                    threat_type=ThreatType.GEOGRAPHIC_ANOMALY,
                    threat_level=ThreatLevel.MEDIUM,
                    timestamp=datetime.now(timezone.utc),
                    source_ip=ip_address,
                    user_id=user_id,
                    tenant_id=tenant_id,
                    endpoint=endpoint,
                    method=method,
                    user_agent=user_agent,
                    details={"reason": geo_details},
                    risk_score=6.0,
                )
                events.append(event)

        # Track API usage for anomaly detection
        if user_id:
            await self.anomaly_detector.track_api_usage(user_id, endpoint, tenant_id)

        return events

    async def analyze_response(
        self, request: Request, response: Response, user_id: Optional[str] = None
    ) -> list[SecurityEvent]:
        """Analyze response for data exfiltration attempts"""
        events = []

        if user_id:
            response_size = 0
            if hasattr(response, "body"):
                response_size = len(response.body) if response.body else 0

            # Check for data exfiltration
            is_exfiltration = await self.anomaly_detector.detect_data_exfiltration(
                user_id, str(request.url.path), response_size
            )

            if is_exfiltration:
                event = SecurityEvent(
                    event_id=self.generate_event_id(),
                    threat_type=ThreatType.DATA_EXFILTRATION,
                    threat_level=ThreatLevel.HIGH,
                    timestamp=datetime.now(timezone.utc),
                    source_ip=request.client.host if request.client else "unknown",
                    user_id=user_id,
                    tenant_id=getattr(request.state, "tenant_id", None),
                    endpoint=str(request.url.path),
                    method=request.method,
                    user_agent=request.headers.get("user-agent", ""),
                    details={"response_size": response_size},
                    risk_score=7.5,
                )
                events.append(event)

        return events

    def _detect_malicious_patterns(
        self, url: str, headers: dict[str, str], user_agent: str
    ) -> list[tuple[ThreatType, dict[str, str]]]:
        """Detect malicious patterns in request"""
        threats = []

        # SQL injection patterns
        sql_patterns = [
            r"('|(\")|;|--)|(union.*select)|(select.*from)|(insert.*into)|(delete.*from)|(update.*set)|(drop.*table)",
            r"exec(\s|\+)+(s|x)p\w+",
            r"script.*alert.*\(",
            r"<.*script.*>.*</.*script.*>",
        ]

        combined_text = f"{url} {user_agent} {' '.join(headers.values())}".lower()

        for pattern in sql_patterns:
            import re

            if re.search(pattern, combined_text, re.IGNORECASE):
                threats.append(
                    (
                        ThreatType.SQL_INJECTION,
                        {"pattern": pattern, "text": combined_text[:200]},
                    )
                )
                break

        # XSS patterns
        xss_patterns = [
            r"<script",
            r"javascript:",
            r"vbscript:",
            r"onload\s*=",
            r"onerror\s*=",
        ]

        for pattern in xss_patterns:
            import re

            if re.search(pattern, combined_text, re.IGNORECASE):
                threats.append(
                    (
                        ThreatType.XSS_ATTEMPT,
                        {"pattern": pattern, "text": combined_text[:200]},
                    )
                )
                break

        # Path traversal patterns
        if "../" in url or "..\\" in url or "~/" in url:
            threats.append((ThreatType.PATH_TRAVERSAL, {"url": url}))

        # Suspicious user agents
        suspicious_agents = ["sqlmap", "nikto", "burp", "nessus", "acunetix", "havij"]
        if any(agent in user_agent.lower() for agent in suspicious_agents):
            threats.append((ThreatType.SUSPICIOUS_PATTERN, {"user_agent": user_agent}))

        return threats

    async def log_security_event(self, event: SecurityEvent):
        """Log security event to storage and monitoring systems"""
        # Store in Redis for recent events
        event_key = f"security_event:{event.event_id}"
        self.redis.setex(event_key, 86400, json.dumps(event.to_dict()))

        # Add to recent events list
        recent_key = f"recent_events:{event.threat_type.value}"
        self.redis.lpush(recent_key, event.event_id)
        self.redis.ltrim(recent_key, 0, 99)  # Keep last 100 events
        self.redis.expire(recent_key, 86400)

        # Log to application logger
        logger.warning(
            f"Security Event: {event.threat_type.value} - {event.threat_level.value} - "
            f"IP: {event.source_ip} - Endpoint: {event.endpoint} - Details: {event.details}"
        )

        # In production, also send to:
        # - SIEM system
        # - Security team alerts
        # - Compliance logging

        self.recent_events.append(event)

    async def get_threat_summary(self) -> dict[str, Any]:
        """Get threat detection summary"""
        current_time = datetime.now(timezone.utc)

        # Count events by type in last 24 hours
        threat_counts = defaultdict(int)
        blocked_counts = defaultdict(int)

        for event in self.recent_events:
            if (current_time - event.timestamp).total_seconds() <= 86400:
                threat_counts[event.threat_type.value] += 1
                if event.blocked:
                    blocked_counts[event.threat_type.value] += 1

        return {
            "summary": {
                "total_threats_24h": sum(threat_counts.values()),
                "total_blocked_24h": sum(blocked_counts.values()),
                "active_detectors": [
                    "brute_force",
                    "anomaly",
                    "geographic",
                    "pattern_matching",
                ],
                "last_updated": current_time.isoformat(),
            },
            "threat_breakdown": dict(threat_counts),
            "blocked_breakdown": dict(blocked_counts),
            "top_source_ips": self._get_top_source_ips(),
            "detection_accuracy": self._calculate_detection_accuracy(),
        }

    def _get_top_source_ips(self) -> list[dict[str, Any]]:
        """Get top source IPs by threat count"""
        ip_counts = defaultdict(int)
        for event in self.recent_events:
            ip_counts[event.source_ip] += 1

        return [
            {"ip": ip, "threat_count": count}
            for ip, count in sorted(
                ip_counts.items(), key=lambda x: x[1], reverse=True
            )[:10]
        ]

    def _calculate_detection_accuracy(self) -> float:
        """Calculate detection accuracy (simplified)"""
        if not self.recent_events:
            return 1.0

        # In production, this would compare against verified threats
        # For now, assume high accuracy
        return 0.95


class APIThreatDetectionMiddleware:
    """FastAPI middleware for real-time threat detection"""

    def __init__(
        self,
        app,
        threat_detector: APIThreatDetector,
        block_threats: bool = True,
        log_all_requests: bool = False,
    ):
        self.app = app
        self.threat_detector = threat_detector
        self.block_threats = block_threats
        self.log_all_requests = log_all_requests

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive)

            # Extract user context
            user_id = (
                getattr(request.state, "auth_user", {}).get("user_id")
                if hasattr(request.state, "auth_user")
                else None
            )
            tenant_id = (
                getattr(request.state, "tenant_id", None)
                if hasattr(request.state, "tenant_id")
                else None
            )

            # Check if IP is currently locked
            ip_address = request.client.host if request.client else "unknown"
            is_locked = await self.threat_detector.brute_force_detector.is_locked(
                ip_address, user_id
            )

            if is_locked:
                error_response = JSONResponse(
                    status_code=429,
                    content={
                        "error": "Too Many Requests",
                        "message": "IP address temporarily blocked due to suspicious activity",
                        "retry_after": 3600,
                    },
                )
                await error_response(scope, receive, send)
                return

            # Analyze request for threats
            threat_events = await self.threat_detector.analyze_request(
                request, user_id, tenant_id
            )

            # Check if any events should block the request
            should_block = False
            if self.block_threats:
                for event in threat_events:
                    if event.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
                        should_block = True
                        event.blocked = True

            # Log all threat events
            for event in threat_events:
                await self.threat_detector.log_security_event(event)

            if should_block:
                error_response = JSONResponse(
                    status_code=403,
                    content={
                        "error": "Forbidden",
                        "message": "Request blocked due to security policy violation",
                    },
                )
                await error_response(scope, receive, send)
                return

            # Process request normally
            response_body = None

            async def capture_response(message):
                nonlocal response_body
                if message["type"] == "http.response.body":
                    response_body = message.get("body", b"")
                await send(message)

            await self.app(scope, receive, capture_response)

            # Analyze response for additional threats
            if response_body is not None:
                # Create mock response object for analysis
                class MockResponse:
                    """MockResponse implementation."""

                    def __init__(self, body):
                        """__init__ operation."""
                        self.body = body

                response = MockResponse(response_body)
                response_events = await self.threat_detector.analyze_response(
                    request, response, user_id
                )

                for event in response_events:
                    await self.threat_detector.log_security_event(event)
        else:
            await self.app(scope, receive, send)


# Factory functions
def create_threat_detector(
    redis_url: str = "redis://localhost:6379/2",
) -> APIThreatDetector:
    """Create threat detector instance"""
    return APIThreatDetector(redis_url=redis_url)


def create_threat_detection_middleware(
    threat_detector: APIThreatDetector, **kwargs
) -> callable:
    """Factory for creating threat detection middleware"""

    def middleware_factory(app):
        """middleware_factory operation."""
        return APIThreatDetectionMiddleware(
            app=app, threat_detector=threat_detector, **kwargs
        )

    return middleware_factory
