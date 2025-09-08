"""
Reliability testing utilities for circuit breakers, retries, and resilience patterns
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


class ReliabilityTester:
    """
    Utilities for testing reliability patterns like circuit breakers, retries, etc.
    """

    def __init__(self):
        self._circuit_breaker_states = {}
        self._service_states = {}
        self._failure_injections = {}

    async def configure_circuit_breaker(
        self, service: str, failure_threshold: int, recovery_timeout: int, test_id: str
    ):
        """Configure circuit breaker for a service"""
        circuit_config = {
            "service": service,
            "failure_threshold": failure_threshold,
            "recovery_timeout": recovery_timeout,
            "test_id": test_id,
            "status": "CLOSED",
            "failure_count": 0,
            "last_failure_time": None,
            "configured_at": datetime.utcnow().isoformat(),
        }

        circuit_key = f"{service}:{test_id}"
        self._circuit_breaker_states[circuit_key] = circuit_config

        logger.info(f"Configured circuit breaker for {service} with threshold {failure_threshold}")

    async def get_circuit_breaker_state(self, service: str, test_id: str) -> dict[str, Any]:
        """Get current circuit breaker state"""
        circuit_key = f"{service}:{test_id}"
        state = self._circuit_breaker_states.get(circuit_key, {})

        # Simulate circuit breaker logic
        if state.get("failure_count", 0) >= state.get("failure_threshold", 3):
            state["status"] = "OPEN"

            # Check if recovery timeout has passed
            if state.get("last_failure_time"):
                last_failure = datetime.fromisoformat(state["last_failure_time"])
                recovery_timeout = state.get("recovery_timeout", 5)

                if datetime.utcnow() > last_failure + timedelta(seconds=recovery_timeout):
                    state["status"] = "HALF_OPEN"

        return state.copy()

    async def simulate_service_failure(self, service: str, test_id: str):
        """Simulate a service failure"""
        circuit_key = f"{service}:{test_id}"

        if circuit_key in self._circuit_breaker_states:
            state = self._circuit_breaker_states[circuit_key]
            state["failure_count"] = state.get("failure_count", 0) + 1
            state["last_failure_time"] = datetime.utcnow().isoformat()

            logger.info(f"Simulated failure for {service}, count: {state['failure_count']}")

    async def simulate_service_recovery(self, service: str):
        """Simulate service recovery"""
        # Mark service as recovered
        self._service_states[service] = {
            "status": "healthy",
            "recovered_at": datetime.utcnow().isoformat(),
        }

        # Reset circuit breaker states for this service
        for circuit_key in self._circuit_breaker_states:
            if circuit_key.startswith(f"{service}:"):
                state = self._circuit_breaker_states[circuit_key]
                state["status"] = "CLOSED"
                state["failure_count"] = 0

        logger.info(f"Simulated recovery for {service}")

    async def inject_failure(self, service: str, failure_type: str, duration: int = 10):
        """Inject a failure into a service"""
        failure_config = {
            "service": service,
            "failure_type": failure_type,
            "injected_at": datetime.utcnow().isoformat(),
            "duration": duration,
            "expires_at": (datetime.utcnow() + timedelta(seconds=duration)).isoformat(),
        }

        self._failure_injections[service] = failure_config
        logger.info(f"Injected {failure_type} failure into {service} for {duration}s")

        # Auto-expire the failure
        await asyncio.sleep(duration)
        if service in self._failure_injections:
            del self._failure_injections[service]
            logger.info(f"Failure injection expired for {service}")

    async def is_failure_active(self, service: str) -> bool:
        """Check if a failure injection is currently active"""
        if service not in self._failure_injections:
            return False

        failure = self._failure_injections[service]
        expires_at = datetime.fromisoformat(failure["expires_at"])

        if datetime.utcnow() > expires_at:
            del self._failure_injections[service]
            return False

        return True

    async def test_retry_mechanism(
        self, operation_func, max_retries: int = 3, backoff_factor: float = 1.0
    ) -> dict[str, Any]:
        """Test retry mechanism for an operation"""
        results = {
            "attempts": [],
            "total_attempts": 0,
            "success": False,
            "total_time": 0,
        }

        start_time = datetime.utcnow()

        for attempt in range(max_retries + 1):
            attempt_start = datetime.utcnow()

            try:
                await operation_func()
                results["success"] = True
                results["attempts"].append(
                    {
                        "attempt": attempt + 1,
                        "result": "success",
                        "timestamp": attempt_start.isoformat(),
                    }
                )
                break

            except Exception as e:
                results["attempts"].append(
                    {
                        "attempt": attempt + 1,
                        "result": "failed",
                        "error": str(e),
                        "timestamp": attempt_start.isoformat(),
                    }
                )

                if attempt < max_retries:
                    delay = backoff_factor * (2**attempt)
                    await asyncio.sleep(delay)

        end_time = datetime.utcnow()
        results["total_attempts"] = len(results["attempts"])
        results["total_time"] = (end_time - start_time).total_seconds()

        return results

    async def test_bulkhead_isolation(
        self, critical_service: str, non_critical_service: str, load_factor: int = 10
    ) -> dict[str, Any]:
        """Test bulkhead isolation between services"""
        results = {
            "critical_service_performance": [],
            "non_critical_service_performance": [],
            "isolation_effective": False,
        }

        # Simulate high load on non-critical service
        non_critical_tasks = []
        for _i in range(load_factor):
            task = asyncio.create_task(self._simulate_service_load(non_critical_service))
            non_critical_tasks.append(task)

        # Test critical service performance under load
        critical_start = datetime.utcnow()
        await self._simulate_service_operation(critical_service)
        critical_end = datetime.utcnow()

        critical_response_time = (critical_end - critical_start).total_seconds()
        results["critical_service_performance"].append(
            {
                "response_time": critical_response_time,
                "timestamp": critical_start.isoformat(),
            }
        )

        # Clean up non-critical tasks
        for task in non_critical_tasks:
            task.cancel()

        # Determine if isolation was effective (critical service wasn't significantly impacted)
        results["isolation_effective"] = critical_response_time < 1.0  # Threshold for acceptable performance

        return results

    async def _simulate_service_load(self, service: str):
        """Simulate load on a service"""
        await asyncio.sleep(0.5)  # Simulate processing time

    async def _simulate_service_operation(self, service: str):
        """Simulate a service operation"""
        await asyncio.sleep(0.1)  # Normal operation time

    async def test_graceful_degradation(self, primary_service: str, fallback_service: str) -> dict[str, Any]:
        """Test graceful degradation when primary service fails"""
        results = {
            "primary_attempts": 0,
            "fallback_used": False,
            "degraded_functionality": False,
            "response_time": 0,
        }

        start_time = datetime.utcnow()

        # Try primary service first
        try:
            await self._simulate_service_operation(primary_service)
            results["primary_attempts"] = 1
        except Exception:
            results["primary_attempts"] = 1

            # Fall back to secondary service
            try:
                await self._simulate_service_operation(fallback_service)
                results["fallback_used"] = True
                results["degraded_functionality"] = True
            except Exception:
                # Complete failure
                pass

        end_time = datetime.utcnow()
        results["response_time"] = (end_time - start_time).total_seconds()

        return results
