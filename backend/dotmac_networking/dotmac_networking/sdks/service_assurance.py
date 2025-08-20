"""
Service Assurance SDK - ICMP/DNS/HTTP probes, SLA checks
"""

import secrets
from datetime import datetime, timedelta
from dotmac_networking.core.datetime_utils import utc_now, utc_now_iso
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..core.exceptions import NetworkingError


class ServiceAssuranceService:
    """In-memory service for service assurance operations."""

    def __init__(self):
        self._probes: Dict[str, Dict[str, Any]] = {}
        self._probe_results: Dict[str, List[Dict[str, Any]]] = {}
        self._sla_policies: Dict[str, Dict[str, Any]] = {}
        self._sla_violations: List[Dict[str, Any]] = []

    async def create_probe(self, **kwargs) -> Dict[str, Any]:
        """Create service assurance probe."""
        probe_id = kwargs.get("probe_id") or str(uuid4())

        probe = {
            "probe_id": probe_id,
            "probe_name": kwargs["probe_name"],
            "probe_type": kwargs["probe_type"],  # icmp, dns, http, tcp
            "target": kwargs["target"],
            "interval": kwargs.get("interval", 30),
            "timeout": kwargs.get("timeout", 10),
            "parameters": kwargs.get("parameters", {}),
            "enabled": kwargs.get("enabled", True),
            "sla_policy_id": kwargs.get("sla_policy_id"),
            "created_at": utc_now().isoformat(),
            "last_run": None,
        }

        self._probes[probe_id] = probe
        self._probe_results[probe_id] = []

        return probe

    async def execute_icmp_probe(self, probe_id: str) -> Dict[str, Any]:
        """Execute ICMP ping probe."""
        if probe_id not in self._probes:
            raise NetworkingError(f"Probe not found: {probe_id}")

        probe = self._probes[probe_id]

        # Simulate ICMP probe
        success = secrets.randbelow(4) < 3  # 75% success rate
        rtt = (secrets.randbelow(4900) + 100) / 100 if success else None  # 1-50 range
        packet_loss = 0 if success else 100

        result = {
            "result_id": str(uuid4()),
            "probe_id": probe_id,
            "timestamp": utc_now().isoformat(),
            "success": success,
            "rtt_ms": rtt,
            "packet_loss_percent": packet_loss,
            "error": None if success else "Request timeout",
        }

        self._probe_results[probe_id].append(result)
        probe["last_run"] = result["timestamp"]

        # Keep only last 1000 results
        if len(self._probe_results[probe_id]) > 1000:
            self._probe_results[probe_id] = self._probe_results[probe_id][-1000:]

        return result

    async def execute_dns_probe(self, probe_id: str) -> Dict[str, Any]:
        """Execute DNS resolution probe."""
        if probe_id not in self._probes:
            raise NetworkingError(f"Probe not found: {probe_id}")

        probe = self._probes[probe_id]

        # Simulate DNS probe
        success = secrets.randbelow(5) < 4  # 80% success rate
        response_time = (secrets.randbelow(9500) + 500) / 100 if success else None  # 5-100 range

        result = {
            "result_id": str(uuid4()),
            "probe_id": probe_id,
            "timestamp": utc_now().isoformat(),
            "success": success,
            "response_time_ms": response_time,
            "resolved_ips": ["192.168.1.1", "192.168.1.2"] if success else [],
            "error": None if success else "DNS resolution failed",
        }

        self._probe_results[probe_id].append(result)
        probe["last_run"] = result["timestamp"]

        return result

    async def execute_http_probe(self, probe_id: str) -> Dict[str, Any]:
        """Execute HTTP probe."""
        if probe_id not in self._probes:
            raise NetworkingError(f"Probe not found: {probe_id}")

        probe = self._probes[probe_id]

        # Simulate HTTP probe
        success = secrets.randbelow(4) < 3  # 75% success rate
        response_time = (secrets.randbelow(4500) + 500) / 10 if success else None  # 50-500 range
        status_codes = [200, 200, 200, 404, 500]
        status_code = status_codes[secrets.randbelow(len(status_codes))] if success else None

        result = {
            "result_id": str(uuid4()),
            "probe_id": probe_id,
            "timestamp": utc_now().isoformat(),
            "success": success,
            "response_time_ms": response_time,
            "status_code": status_code,
            "content_length": secrets.randbelow(9001) + 1000 if success else None,
            "error": None if success else "Connection failed",
        }

        self._probe_results[probe_id].append(result)
        probe["last_run"] = result["timestamp"]

        return result

    async def create_sla_policy(self, **kwargs) -> Dict[str, Any]:
        """Create SLA policy."""
        policy_id = kwargs.get("policy_id") or str(uuid4())

        policy = {
            "policy_id": policy_id,
            "policy_name": kwargs["policy_name"],
            "availability_threshold": kwargs.get("availability_threshold", 99.9),
            "latency_threshold_ms": kwargs.get("latency_threshold_ms", 100),
            "measurement_window_hours": kwargs.get("measurement_window_hours", 24),
            "violation_threshold": kwargs.get("violation_threshold", 3),
            "notification_enabled": kwargs.get("notification_enabled", True),
            "status": kwargs.get("status", "active"),
            "created_at": utc_now().isoformat(),
        }

        self._sla_policies[policy_id] = policy
        return policy

    async def check_sla_compliance(self, probe_id: str) -> Dict[str, Any]:
        """Check SLA compliance for probe."""
        if probe_id not in self._probes:
            raise NetworkingError(f"Probe not found: {probe_id}")

        probe = self._probes[probe_id]
        sla_policy_id = probe.get("sla_policy_id")

        if not sla_policy_id or sla_policy_id not in self._sla_policies:
            return {"compliance_status": "no_policy", "probe_id": probe_id}

        policy = self._sla_policies[sla_policy_id]
        window_hours = policy["measurement_window_hours"]

        # Get results within measurement window
        cutoff_time = utc_now() - timedelta(hours=window_hours)
        results = self._probe_results.get(probe_id, [])

        window_results = [
            result for result in results
            if datetime.fromisoformat(result["timestamp"]) >= cutoff_time
        ]

        if not window_results:
            return {"compliance_status": "insufficient_data", "probe_id": probe_id}

        # Calculate availability
        successful_probes = sum(1 for result in window_results if result["success"])
        availability = (successful_probes / len(window_results)) * 100

        # Calculate average latency
        successful_results = [r for r in window_results if r["success"]]
        avg_latency = 0
        if successful_results:
            latency_values = [r.get("rtt_ms") or r.get("response_time_ms", 0) for r in successful_results]
            avg_latency = sum(latency_values) / len(latency_values)

        # Check compliance
        availability_compliant = availability >= policy["availability_threshold"]
        latency_compliant = avg_latency <= policy["latency_threshold_ms"]

        compliance_status = "compliant" if (availability_compliant and latency_compliant) else "violation"

        if compliance_status == "violation":
            violation = {
                "violation_id": str(uuid4()),
                "probe_id": probe_id,
                "policy_id": sla_policy_id,
                "availability_actual": availability,
                "availability_threshold": policy["availability_threshold"],
                "latency_actual": avg_latency,
                "latency_threshold": policy["latency_threshold_ms"],
                "measurement_window_hours": window_hours,
                "detected_at": utc_now().isoformat(),
            }
            self._sla_violations.append(violation)

        return {
            "compliance_status": compliance_status,
            "probe_id": probe_id,
            "policy_id": sla_policy_id,
            "availability_actual": availability,
            "availability_threshold": policy["availability_threshold"],
            "latency_actual": avg_latency,
            "latency_threshold": policy["latency_threshold_ms"],
            "measurement_period": f"{window_hours} hours",
            "total_measurements": len(window_results),
            "successful_measurements": successful_probes,
        }


class ServiceAssuranceSDK:
    """Minimal, reusable SDK for service assurance."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._service = ServiceAssuranceService()

    async def create_icmp_probe(
        self,
        probe_name: str,
        target: str,
        interval: int = 30,
        timeout: int = 10,
        sla_policy_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create ICMP ping probe."""
        probe = await self._service.create_probe(
            probe_name=probe_name,
            probe_type="icmp",
            target=target,
            interval=interval,
            timeout=timeout,
            sla_policy_id=sla_policy_id,
            tenant_id=self.tenant_id,
            **kwargs
        )

        return {
            "probe_id": probe["probe_id"],
            "probe_name": probe["probe_name"],
            "probe_type": probe["probe_type"],
            "target": probe["target"],
            "interval": probe["interval"],
            "timeout": probe["timeout"],
            "enabled": probe["enabled"],
            "sla_policy_id": probe["sla_policy_id"],
            "created_at": probe["created_at"],
        }

    async def create_dns_probe(
        self,
        probe_name: str,
        target: str,
        dns_server: Optional[str] = None,
        record_type: str = "A",
        interval: int = 60,
        **kwargs
    ) -> Dict[str, Any]:
        """Create DNS resolution probe."""
        parameters = {
            "dns_server": dns_server or "8.8.8.8",
            "record_type": record_type,
        }

        probe = await self._service.create_probe(
            probe_name=probe_name,
            probe_type="dns",
            target=target,
            interval=interval,
            parameters=parameters,
            tenant_id=self.tenant_id,
            **kwargs
        )

        return {
            "probe_id": probe["probe_id"],
            "probe_name": probe["probe_name"],
            "probe_type": probe["probe_type"],
            "target": probe["target"],
            "interval": probe["interval"],
            "parameters": probe["parameters"],
            "enabled": probe["enabled"],
            "created_at": probe["created_at"],
        }

    async def create_http_probe(
        self,
        probe_name: str,
        target: str,
        method: str = "GET",
        expected_status: int = 200,
        interval: int = 60,
        **kwargs
    ) -> Dict[str, Any]:
        """Create HTTP probe."""
        parameters = {
            "method": method,
            "expected_status": expected_status,
        }

        probe = await self._service.create_probe(
            probe_name=probe_name,
            probe_type="http",
            target=target,
            interval=interval,
            parameters=parameters,
            tenant_id=self.tenant_id,
            **kwargs
        )

        return {
            "probe_id": probe["probe_id"],
            "probe_name": probe["probe_name"],
            "probe_type": probe["probe_type"],
            "target": probe["target"],
            "interval": probe["interval"],
            "parameters": probe["parameters"],
            "enabled": probe["enabled"],
            "created_at": probe["created_at"],
        }

    async def execute_probe(self, probe_id: str) -> Dict[str, Any]:
        """Execute service assurance probe."""
        probe = self._service._probes.get(probe_id)
        if not probe:
            raise NetworkingError(f"Probe not found: {probe_id}")

        if probe["probe_type"] == "icmp":
            result = await self._service.execute_icmp_probe(probe_id)
        elif probe["probe_type"] == "dns":
            result = await self._service.execute_dns_probe(probe_id)
        elif probe["probe_type"] == "http":
            result = await self._service.execute_http_probe(probe_id)
        else:
            raise NetworkingError(f"Unsupported probe type: {probe['probe_type']}")

        return {
            "result_id": result["result_id"],
            "probe_id": result["probe_id"],
            "timestamp": result["timestamp"],
            "success": result["success"],
            "metrics": {k: v for k, v in result.items() if k not in ["result_id", "probe_id", "timestamp", "success", "error"]},
            "error": result["error"],
        }

    async def create_sla_policy(
        self,
        policy_name: str,
        availability_threshold: float = 99.9,
        latency_threshold_ms: int = 100,
        measurement_window_hours: int = 24,
        **kwargs
    ) -> Dict[str, Any]:
        """Create SLA policy."""
        policy = await self._service.create_sla_policy(
            policy_name=policy_name,
            availability_threshold=availability_threshold,
            latency_threshold_ms=latency_threshold_ms,
            measurement_window_hours=measurement_window_hours,
            **kwargs
        )

        return {
            "policy_id": policy["policy_id"],
            "policy_name": policy["policy_name"],
            "availability_threshold": policy["availability_threshold"],
            "latency_threshold_ms": policy["latency_threshold_ms"],
            "measurement_window_hours": policy["measurement_window_hours"],
            "violation_threshold": policy["violation_threshold"],
            "notification_enabled": policy["notification_enabled"],
            "status": policy["status"],
            "created_at": policy["created_at"],
        }

    async def check_sla_compliance(self, probe_id: str) -> Dict[str, Any]:
        """Check SLA compliance for probe."""
        compliance = await self._service.check_sla_compliance(probe_id)

        return {
            "probe_id": compliance["probe_id"],
            "compliance_status": compliance["compliance_status"],
            "policy_id": compliance.get("policy_id"),
            "availability": {
                "actual": compliance.get("availability_actual"),
                "threshold": compliance.get("availability_threshold"),
                "compliant": compliance.get("availability_actual", 0) >= compliance.get("availability_threshold", 100) if compliance.get("availability_actual") is not None else None,
            },
            "latency": {
                "actual_ms": compliance.get("latency_actual"),
                "threshold_ms": compliance.get("latency_threshold_ms"),
                "compliant": compliance.get("latency_actual", float("inf")) <= compliance.get("latency_threshold_ms", 0) if compliance.get("latency_actual") is not None else None,
            },
            "measurement_period": compliance.get("measurement_period"),
            "total_measurements": compliance.get("total_measurements"),
            "successful_measurements": compliance.get("successful_measurements"),
        }

    async def get_probe_statistics(self, probe_id: str, hours: int = 24) -> Dict[str, Any]:
        """Get probe statistics."""
        if probe_id not in self._service._probes:
            raise NetworkingError(f"Probe not found: {probe_id}")

        cutoff_time = utc_now() - timedelta(hours=hours)
        results = self._service._probe_results.get(probe_id, [])

        period_results = [
            result for result in results
            if datetime.fromisoformat(result["timestamp"]) >= cutoff_time
        ]

        if not period_results:
            return {
                "probe_id": probe_id,
                "period_hours": hours,
                "total_measurements": 0,
                "availability_percent": 0,
                "average_latency_ms": 0,
            }

        successful_results = [r for r in period_results if r["success"]]
        availability = (len(successful_results) / len(period_results)) * 100

        # Calculate average latency from successful results
        avg_latency = 0
        if successful_results:
            latency_values = []
            for result in successful_results:
                if "rtt_ms" in result and result["rtt_ms"] is not None:
                    latency_values.append(result["rtt_ms"])
                elif "response_time_ms" in result and result["response_time_ms"] is not None:
                    latency_values.append(result["response_time_ms"])

            if latency_values:
                avg_latency = sum(latency_values) / len(latency_values)

        return {
            "probe_id": probe_id,
            "period_hours": hours,
            "total_measurements": len(period_results),
            "successful_measurements": len(successful_results),
            "failed_measurements": len(period_results) - len(successful_results),
            "availability_percent": round(availability, 2),
            "average_latency_ms": round(avg_latency, 2),
            "min_latency_ms": min([r.get("rtt_ms") or r.get("response_time_ms", 0) for r in successful_results]) if successful_results else 0,
            "max_latency_ms": max([r.get("rtt_ms") or r.get("response_time_ms", 0) for r in successful_results]) if successful_results else 0,
        }

    async def list_probes(self, probe_type: Optional[str] = None, enabled_only: bool = False) -> List[Dict[str, Any]]:
        """List service assurance probes."""
        probes = list(self._service._probes.values())

        if probe_type:
            probes = [p for p in probes if p["probe_type"] == probe_type]

        if enabled_only:
            probes = [p for p in probes if p["enabled"]]

        return [
            {
                "probe_id": probe["probe_id"],
                "probe_name": probe["probe_name"],
                "probe_type": probe["probe_type"],
                "target": probe["target"],
                "interval": probe["interval"],
                "enabled": probe["enabled"],
                "last_run": probe["last_run"],
                "sla_policy_id": probe["sla_policy_id"],
            }
            for probe in probes
        ]

    async def get_sla_violations(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent SLA violations."""
        cutoff_time = utc_now() - timedelta(hours=hours)

        recent_violations = [
            violation for violation in self._service._sla_violations
            if datetime.fromisoformat(violation["detected_at"]) >= cutoff_time
        ]

        return [
            {
                "violation_id": violation["violation_id"],
                "probe_id": violation["probe_id"],
                "policy_id": violation["policy_id"],
                "availability_actual": violation["availability_actual"],
                "availability_threshold": violation["availability_threshold"],
                "latency_actual": violation["latency_actual"],
                "latency_threshold": violation["latency_threshold"],
                "detected_at": violation["detected_at"],
            }
            for violation in sorted(recent_violations, key=lambda v: v["detected_at"], reverse=True)
        ]
