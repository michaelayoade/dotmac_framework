"""Service Assurance unified SDK interface."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ..core.enums import (
    AlarmSeverity,
    AlarmType,
    CollectorStatus,
    EventType,
    FlowType,
    ProbeStatus,
    ProbeType,
    SLAComplianceStatus,
)
from ..services.alarm_service import AlarmService
from ..services.flow_service import FlowService
from ..services.probe_service import ProbeService


class ServiceAssuranceError(Exception):
    """Service Assurance SDK error."""

    pass


class ServiceAssuranceSDK:
    """Unified SDK for Service Assurance operations."""

    def __init__(
        self,
        tenant_id: str,
        database_session=None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize Service Assurance SDK."""
        self.tenant_id = tenant_id
        self.config = config or {}

        # Initialize core services
        self.alarm_service = AlarmService(tenant_id, database_session, config)
        self.flow_service = FlowService(tenant_id, database_session, config)
        self.probe_service = ProbeService(tenant_id, database_session, config)

    # ============================================
    # Service Probe Management
    # ============================================

    async def create_icmp_probe(
        self,
        probe_name: str,
        target: str,
        interval: int = 30,
        timeout: int = 10,
        sla_policy_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create ICMP ping probe."""
        return await self.probe_service.create_probe(
            probe_name=probe_name,
            probe_type=ProbeType.ICMP,
            target=target,
            interval=interval,
            timeout=timeout,
            sla_policy_id=sla_policy_id,
            **kwargs,
        )

    async def create_dns_probe(
        self,
        probe_name: str,
        target: str,
        dns_server: str = "8.8.8.8",
        record_type: str = "A",
        interval: int = 60,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create DNS resolution probe."""
        parameters = {
            "dns_server": dns_server,
            "record_type": record_type,
        }

        return await self.probe_service.create_probe(
            probe_name=probe_name,
            probe_type=ProbeType.DNS,
            target=target,
            interval=interval,
            parameters=parameters,
            **kwargs,
        )

    async def create_http_probe(
        self,
        probe_name: str,
        target: str,
        method: str = "GET",
        expected_status: int = 200,
        interval: int = 60,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create HTTP/HTTPS probe."""
        parameters = {
            "method": method,
            "expected_status": expected_status,
        }

        probe_type = (
            ProbeType.HTTPS if target.startswith("https://") else ProbeType.HTTP
        )

        return await self.probe_service.create_probe(
            probe_name=probe_name,
            probe_type=probe_type,
            target=target,
            interval=interval,
            parameters=parameters,
            **kwargs,
        )

    async def create_tcp_probe(
        self,
        probe_name: str,
        target: str,
        port: int,
        interval: int = 30,
        timeout: int = 10,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create TCP connectivity probe."""
        parameters = {
            "port": port,
        }

        # Format target with port if not already included
        if ":" not in target:
            target = f"{target}:{port}"

        return await self.probe_service.create_probe(
            probe_name=probe_name,
            probe_type=ProbeType.TCP,
            target=target,
            interval=interval,
            timeout=timeout,
            parameters=parameters,
            **kwargs,
        )

    async def execute_probe(self, probe_id: str) -> Dict[str, Any]:
        """Execute service probe and return results."""
        result = await self.probe_service.execute_probe(probe_id)

        return {
            "result_id": result["result_id"],
            "probe_id": result["probe_id"],
            "timestamp": result["timestamp"],
            "success": result["success"],
            "response_time_ms": result.get("response_time_ms"),
            "status_code": result.get("status_code"),
            "metrics": result.get("metrics", {}),
            "error": result.get("error_message"),
        }

    async def get_probe_statistics(
        self, probe_id: str, hours: int = 24
    ) -> Dict[str, Any]:
        """Get probe performance statistics."""
        return await self.probe_service.get_probe_statistics(probe_id, hours)

    async def list_probes(
        self, probe_type: Optional[str] = None, enabled_only: bool = False
    ) -> List[Dict[str, Any]]:
        """List service probes."""
        probe_type_enum = ProbeType(probe_type) if probe_type else None
        return await self.probe_service.list_probes(
            probe_type=probe_type_enum, enabled_only=enabled_only
        )

    # ============================================
    # SLA Policy Management
    # ============================================

    async def create_sla_policy(
        self,
        policy_name: str,
        availability_threshold: float = 99.9,
        latency_threshold_ms: int = 100,
        measurement_window_hours: int = 24,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create SLA policy."""
        return await self.probe_service.create_sla_policy(
            policy_name=policy_name,
            availability_threshold=availability_threshold,
            latency_threshold_ms=latency_threshold_ms,
            measurement_window_hours=measurement_window_hours,
            **kwargs,
        )

    async def check_sla_compliance(self, probe_id: str) -> Dict[str, Any]:
        """Check SLA compliance for probe."""
        return await self.probe_service.check_sla_compliance(probe_id)

    async def get_sla_violations(
        self, hours: int = 24, probe_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get recent SLA violations."""
        return await self.probe_service.get_sla_violations(hours, probe_id)

    # ============================================
    # Alarm Management
    # ============================================

    async def create_snmp_alarm_rule(
        self,
        rule_name: str,
        trap_oid: str,
        severity: str = "warning",
        alarm_type: str = "equipment",
        description_template: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create SNMP trap alarm rule."""
        match_criteria = {
            "trap_oid": trap_oid,
        }

        return await self.alarm_service.create_alarm_rule(
            rule_name=rule_name,
            event_type=EventType.SNMP_TRAP,
            match_criteria=match_criteria,
            severity=AlarmSeverity(severity),
            alarm_type=AlarmType(alarm_type),
            description_template=description_template or f"SNMP alarm: {rule_name}",
            **kwargs,
        )

    async def create_syslog_alarm_rule(
        self,
        rule_name: str,
        message_pattern: str,
        severity: str = "warning",
        alarm_type: str = "system",
        description_template: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create syslog message alarm rule."""
        match_criteria = {
            "message": message_pattern,
        }

        return await self.alarm_service.create_alarm_rule(
            rule_name=rule_name,
            event_type=EventType.SYSLOG,
            match_criteria=match_criteria,
            severity=AlarmSeverity(severity),
            alarm_type=AlarmType(alarm_type),
            description_template=description_template or f"Syslog alarm: {rule_name}",
            **kwargs,
        )

    async def process_snmp_trap(
        self,
        source_device: str,
        source_ip: str,
        trap_oid: str,
        varbinds: Dict[str, Any],
        raw_data: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Process incoming SNMP trap."""
        return await self.alarm_service.process_snmp_trap(
            source_device=source_device,
            source_ip=source_ip,
            trap_oid=trap_oid,
            varbinds=varbinds,
            raw_data=raw_data,
        )

    async def process_syslog_message(
        self,
        source_device: str,
        source_ip: str,
        message: str,
        facility: int = 16,
        severity: int = 6,
        raw_data: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Process incoming syslog message."""
        return await self.alarm_service.process_syslog_message(
            source_device=source_device,
            source_ip=source_ip,
            message=message,
            facility=facility,
            severity=severity,
            raw_data=raw_data,
        )

    async def acknowledge_alarm(
        self, alarm_id: str, acknowledged_by: str, comments: Optional[str] = None
    ) -> Dict[str, Any]:
        """Acknowledge alarm."""
        return await self.alarm_service.acknowledge_alarm(
            alarm_id, acknowledged_by, comments
        )

    async def clear_alarm(
        self, alarm_id: str, cleared_by: str, comments: Optional[str] = None
    ) -> Dict[str, Any]:
        """Clear alarm."""
        return await self.alarm_service.clear_alarm(alarm_id, cleared_by, comments)

    async def suppress_alarms(
        self,
        device_id: str,
        alarm_type: str = "*",
        duration_minutes: int = 60,
        reason: Optional[str] = None,
        suppressed_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Suppress alarms for device/type."""
        return await self.alarm_service.suppress_alarms(
            device_id, alarm_type, duration_minutes, reason, suppressed_by
        )

    async def get_active_alarms(
        self,
        device_id: Optional[str] = None,
        severity: Optional[str] = None,
        alarm_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get active alarms with filtering."""
        severity_enum = AlarmSeverity(severity) if severity else None
        alarm_type_enum = AlarmType(alarm_type) if alarm_type else None

        return await self.alarm_service.get_active_alarms(
            device_id=device_id,
            severity=severity_enum,
            alarm_type=alarm_type_enum,
            limit=limit,
        )

    async def get_alarm_statistics(
        self, device_id: Optional[str] = None, hours: int = 24
    ) -> Dict[str, Any]:
        """Get alarm statistics."""
        return await self.alarm_service.get_alarm_statistics(device_id, hours)

    # ============================================
    # Flow Analytics
    # ============================================

    async def create_netflow_collector(
        self,
        collector_name: str,
        listen_port: int,
        version: str = "9",
        sampling_rate: int = 1,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create NetFlow collector."""
        return await self.flow_service.create_flow_collector(
            collector_name=collector_name,
            flow_type=FlowType.NETFLOW,
            listen_port=listen_port,
            version=version,
            sampling_rate=sampling_rate,
            **kwargs,
        )

    async def create_sflow_collector(
        self, collector_name: str, listen_port: int, sampling_rate: int = 1024, **kwargs
    ) -> Dict[str, Any]:
        """Create sFlow collector."""
        return await self.flow_service.create_flow_collector(
            collector_name=collector_name,
            flow_type=FlowType.SFLOW,
            listen_port=listen_port,
            sampling_rate=sampling_rate,
            **kwargs,
        )

    async def ingest_flow_data(
        self,
        collector_id: str,
        exporter_ip: str,
        src_addr: str,
        dst_addr: str,
        src_port: int,
        dst_port: int,
        protocol: int,
        packets: int,
        bytes: int,
        **kwargs,
    ) -> Dict[str, Any]:
        """Ingest flow record."""
        return await self.flow_service.ingest_flow_record(
            collector_id=collector_id,
            exporter_ip=exporter_ip,
            src_addr=src_addr,
            dst_addr=dst_addr,
            src_port=src_port,
            dst_port=dst_port,
            protocol=protocol,
            packets=packets,
            bytes=bytes,
            **kwargs,
        )

    async def get_traffic_summary(
        self, hours: int = 1, collector_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get traffic summary for time period."""
        return await self.flow_service.get_traffic_summary(hours, collector_id)

    async def get_top_talkers(
        self,
        hours: int = 1,
        limit: int = 10,
        metric: str = "bytes",
        collector_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get top talkers by traffic volume."""
        talkers = await self.flow_service.get_top_talkers(
            hours, limit, metric, collector_id
        )

        # Add ranking
        return [{"rank": idx + 1, **talker} for idx, talker in enumerate(talkers)]

    async def aggregate_flows(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        group_by: Optional[List[str]] = None,
        collector_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Aggregate flow records by dimensions."""
        return await self.flow_service.aggregate_flows(
            start_time, end_time, group_by, collector_id
        )

    async def aggregate_traffic_by_subnet(
        self, subnet_mask: int = 24, hours: int = 1, collector_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Aggregate traffic by subnet."""
        return await self.flow_service.aggregate_traffic_by_subnet(
            subnet_mask, hours, collector_id
        )

    async def get_protocol_statistics(
        self, hours: int = 1, collector_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get protocol usage statistics."""
        return await self.flow_service.get_protocol_statistics(hours, collector_id)

    async def list_collectors(
        self, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List flow collectors."""
        status_enum = CollectorStatus(status) if status else None
        return await self.flow_service.list_collectors(status_enum)

    async def get_collector_statistics(self, collector_id: str) -> Dict[str, Any]:
        """Get collector statistics."""
        return await self.flow_service.get_collector_statistics(collector_id)

    # ============================================
    # Unified Analytics
    # ============================================

    async def get_service_health_dashboard(self, hours: int = 24) -> Dict[str, Any]:
        """Get unified service health dashboard."""
        # Get probe statistics
        probes = await self.list_probes()
        probe_stats = []

        for probe in probes:
            stats = await self.get_probe_statistics(probe["probe_id"], hours)
            probe_stats.append(
                {
                    "probe_id": probe["probe_id"],
                    "probe_name": probe["probe_name"],
                    "probe_type": probe["probe_type"],
                    "target": probe["target"],
                    "availability": stats["availability_percent"],
                    "avg_latency": stats["latency_stats"]["average_ms"],
                    "status": (
                        "healthy" if stats["availability_percent"] >= 95 else "degraded"
                    ),
                }
            )

        # Get alarm statistics
        alarm_stats = await self.get_alarm_statistics(hours=hours)

        # Get traffic summary if collectors exist
        collectors = await self.list_collectors()
        traffic_stats = None
        if collectors:
            traffic_stats = await self.get_traffic_summary(hours=hours)

        # Get SLA violations
        violations = await self.get_sla_violations(hours=hours)

        # Calculate overall health score
        total_probes = len(probe_stats)
        healthy_probes = len([p for p in probe_stats if p["status"] == "healthy"])
        health_score = (
            (healthy_probes / total_probes * 100) if total_probes > 0 else 100
        )

        return {
            "tenant_id": self.tenant_id,
            "generated_at": datetime.utcnow().isoformat(),
            "time_period_hours": hours,
            "overall_health": {
                "score": round(health_score, 1),
                "status": (
                    "healthy"
                    if health_score >= 95
                    else "degraded" if health_score >= 80 else "critical"
                ),
                "total_probes": total_probes,
                "healthy_probes": healthy_probes,
            },
            "service_probes": {
                "total_probes": total_probes,
                "probe_details": probe_stats[:10],  # Top 10 probes
                "avg_availability": (
                    sum(p["availability"] for p in probe_stats) / total_probes
                    if total_probes > 0
                    else 100
                ),
            },
            "alarms": {
                "total_alarms": alarm_stats["total_alarms"],
                "active_alarms": alarm_stats["active_alarms"],
                "critical_alarms": alarm_stats["severity_distribution"].get(
                    "critical", 0
                ),
                "major_alarms": alarm_stats["severity_distribution"].get("major", 0),
            },
            "sla_compliance": {
                "total_violations": len(violations),
                "recent_violations": violations[:5],  # Most recent 5
            },
            "traffic_analytics": traffic_stats,
        }

    async def get_network_performance_report(self, hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive network performance report."""
        # Get traffic analytics
        traffic_summary = await self.get_traffic_summary(hours=hours)
        top_talkers = await self.get_top_talkers(hours=hours, limit=10)
        protocol_stats = await self.get_protocol_statistics(hours=hours)
        subnet_traffic = await self.aggregate_traffic_by_subnet(hours=hours)

        # Get probe performance data
        probes = await self.list_probes()
        connectivity_stats = []

        for probe in probes[:20]:  # Limit to top 20 probes
            stats = await self.get_probe_statistics(probe["probe_id"], hours)
            connectivity_stats.append(
                {
                    "probe_name": probe["probe_name"],
                    "target": probe["target"],
                    "probe_type": probe["probe_type"],
                    "availability": stats["availability_percent"],
                    "avg_latency": stats["latency_stats"]["average_ms"],
                    "max_latency": stats["latency_stats"]["max_ms"],
                    "p95_latency": stats["latency_stats"]["p95_ms"],
                }
            )

        return {
            "tenant_id": self.tenant_id,
            "report_generated_at": datetime.utcnow().isoformat(),
            "time_period_hours": hours,
            "traffic_analysis": {
                "summary": traffic_summary,
                "top_talkers": top_talkers,
                "protocol_breakdown": protocol_stats[:10],
                "subnet_analysis": subnet_traffic[:15],
            },
            "connectivity_analysis": {
                "probe_count": len(connectivity_stats),
                "avg_availability": (
                    sum(p["availability"] for p in connectivity_stats)
                    / len(connectivity_stats)
                    if connectivity_stats
                    else 0
                ),
                "probe_details": connectivity_stats,
            },
            "performance_insights": {
                "busiest_hour_flows": traffic_summary.get("flows_per_second", 0) * 3600,
                "peak_bandwidth_bps": traffic_summary.get("bits_per_second", 0),
                "protocol_diversity": len(protocol_stats),
                "network_segments": len(subnet_traffic),
            },
        }

    # ============================================
    # Utility Methods
    # ============================================

    async def health_check(self) -> Dict[str, Any]:
        """Check SDK health and connectivity."""
        health = {
            "tenant_id": self.tenant_id,
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "alarm_service": True,
                "flow_service": True,
                "probe_service": True,
            },
            "statistics": {},
        }

        # Check alarm service
        alarm_stats = await self.get_alarm_statistics(hours=1)
        health["statistics"]["recent_alarms"] = alarm_stats["total_alarms"]

        # Check probe service
        probes = await self.list_probes()
        health["statistics"]["total_probes"] = len(probes)

        # Check flow service
        collectors = await self.list_collectors()
        health["statistics"]["total_collectors"] = len(collectors)

        health["overall_status"] = (
            "healthy" if all(health["services"].values()) else "degraded"
        )
        return health
