"""Rate limiting middleware."""

import asyncio
import time
from typing import Any, Dict

from .base import RequestMiddleware


class RateLimitMiddleware(RequestMiddleware):
    """Client-side rate limiting middleware."""

    def __init__(self, requests_per_second: float = 10.0):
        self.requests_per_second = requests_per_second
        self.min_interval = 1.0 / requests_per_second
        self.last_request_time = 0.0

    async def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply rate limiting before request."""
        now = time.time()
        time_since_last = now - self.last_request_time

        if time_since_last < self.min_interval:
            sleep_time = self.min_interval - time_since_last
            await asyncio.sleep(sleep_time)

        self.last_request_time = time.time()
        return request_data
