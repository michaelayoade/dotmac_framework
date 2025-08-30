"""Telemetry and metrics collection for HTTP client."""

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class TelemetryConfig:
    """Configuration for telemetry collection."""

    enabled: bool = True
    service_name: str = "dotmac-http-client"
    collect_metrics: bool = True
    collect_traces: bool = True


@dataclass
class HTTPMetrics:
    """HTTP request metrics."""

    request_count: int = 0
    error_count: int = 0
    total_duration: float = 0.0
    avg_duration: float = 0.0
    status_codes: Dict[int, int] = None

    def __post_init__(self):
        if self.status_codes is None:
            self.status_codes = {}


class SDKTelemetry:
    """Basic telemetry collection for HTTP client."""

    def __init__(self, config: TelemetryConfig):
        self.config = config
        self.metrics = HTTPMetrics()

    def record_request(
        self,
        method: str,
        url: str,
        status_code: int,
        duration: float,
        error: Optional[Exception] = None,
    ):
        """Record HTTP request metrics."""
        if not self.config.enabled:
            return

        self.metrics.request_count += 1
        self.metrics.total_duration += duration
        self.metrics.avg_duration = (
            self.metrics.total_duration / self.metrics.request_count
        )

        if status_code in self.metrics.status_codes:
            self.metrics.status_codes[status_code] += 1
        else:
            self.metrics.status_codes[status_code] = 1

        if error or status_code >= 400:
            self.metrics.error_count += 1

    def get_metrics(self) -> Dict[str, Any]:
        """Get collected metrics."""
        return {
            "request_count": self.metrics.request_count,
            "error_count": self.metrics.error_count,
            "error_rate": self.metrics.error_count / max(1, self.metrics.request_count),
            "avg_duration": self.metrics.avg_duration,
            "total_duration": self.metrics.total_duration,
            "status_codes": self.metrics.status_codes,
        }
