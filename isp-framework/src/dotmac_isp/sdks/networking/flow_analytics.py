"""
Flow Analytics SDK - ingest/export flow records (NetFlow, sFlow, IPFIX)
"""

from datetime import datetime, timedelta
from dotmac_isp.sdks.core.datetime_utils import utc_now, utc_now_iso
from typing import Any, Dict, List
from uuid import uuid4

from ..core.exceptions import NetworkingError


class FlowAnalyticsService:
    """In-memory service for flow analytics operations."""

    def __init__(self):
        """  Init   operation."""
        self._flow_records: List[Dict[str, Any]] = []
        self._collectors: Dict[str, Dict[str, Any]] = {}
        self._exporters: Dict[str, Dict[str, Any]] = {}
        self._aggregations: Dict[str, Dict[str, Any]] = {}
        self._templates: Dict[str, Dict[str, Any]] = {}

    async def create_flow_collector(self, **kwargs) -> Dict[str, Any]:
        """Create flow collector."""
        collector_id = kwargs.get("collector_id") or str(uuid4())

        collector = {
            "collector_id": collector_id,
            "collector_name": kwargs["collector_name"],
            "flow_type": kwargs["flow_type"],  # netflow, sflow, ipfix
            "listen_port": kwargs["listen_port"],
            "listen_address": kwargs.get("listen_address", "127.0.0.1"),
            "version": kwargs.get("version", "9"),
            "sampling_rate": kwargs.get("sampling_rate", 1),
            "active_timeout": kwargs.get("active_timeout", 1800),
            "inactive_timeout": kwargs.get("inactive_timeout", 15),
            "status": kwargs.get("status", "active"),
            "created_at": utc_now().isoformat(),
            "flows_received": 0,
            "last_flow": None,
        }

        self._collectors[collector_id] = collector
        return collector

    async def ingest_flow_record(self, **kwargs) -> Dict[str, Any]:
        """Ingest flow record."""
        flow_id = str(uuid4())

        flow_record = {
            "flow_id": flow_id,
            "collector_id": kwargs.get("collector_id"),
            "exporter_ip": kwargs.get("exporter_ip", ""),
            "src_addr": kwargs.get("src_addr", ""),
            "dst_addr": kwargs.get("dst_addr", ""),
            "src_port": kwargs.get("src_port", 0),
            "dst_port": kwargs.get("dst_port", 0),
            "protocol": kwargs.get("protocol", 0),
            "tos": kwargs.get("tos", 0),
            "tcp_flags": kwargs.get("tcp_flags", 0),
            "packets": kwargs.get("packets", 0),
            "bytes": kwargs.get("bytes", 0),
            "flow_start": kwargs.get("flow_start", utc_now().isoformat()),
            "flow_end": kwargs.get("flow_end", utc_now().isoformat()),
            "input_snmp": kwargs.get("input_snmp", 0),
            "output_snmp": kwargs.get("output_snmp", 0),
            "next_hop": kwargs.get("next_hop", ""),
            "src_as": kwargs.get("src_as", 0),
            "dst_as": kwargs.get("dst_as", 0),
            "src_mask": kwargs.get("src_mask", 0),
            "dst_mask": kwargs.get("dst_mask", 0),
            "ingested_at": utc_now().isoformat(),
        }

        self._flow_records.append(flow_record)

        # Update collector stats
        if (
            kwargs.get("collector_id")
            and kwargs.get("collector_id") in self._collectors
        ):
            collector = self._collectors[kwargs.get("collector_id")]
            collector["flows_received"] += 1
            collector["last_flow"] = utc_now().isoformat()

        # Keep only last 10000 records in memory
        if len(self._flow_records) > 10000:
            self._flow_records = self._flow_records[-10000:]

        return flow_record

    async def aggregate_flows(self, **kwargs) -> Dict[str, Any]:
        """Aggregate flow records."""
        aggregation_id = str(uuid4())

        # Get flows within time window
        start_time = datetime.fromisoformat(
            kwargs.get("start_time", (utc_now() - timedelta(hours=1)).isoformat())
        )
        end_time = datetime.fromisoformat(kwargs.get("end_time", utc_now().isoformat()))

        flows_in_window = [
            flow
            for flow in self._flow_records
            if start_time <= datetime.fromisoformat(flow["ingested_at"]) <= end_time
        ]

        # Aggregate by specified dimensions
        group_by = kwargs.get("group_by", ["src_addr", "dst_addr"])
        aggregations = {}

        for flow in flows_in_window:
            # Create grouping key
            key_parts = []
            for dimension in group_by:
                key_parts.append(str(flow.get(dimension, "")))
            key = "|".join(key_parts)

            if key not in aggregations:
                aggregations[key] = {
                    "group_key": key,
                    "dimensions": {dim: flow.get(dim) for dim in group_by},
                    "total_packets": 0,
                    "total_bytes": 0,
                    "flow_count": 0,
                    "first_seen": flow["flow_start"],
                    "last_seen": flow["flow_end"],
                }

            agg = aggregations[key]
            agg["total_packets"] += flow.get("packets", 0)
            agg["total_bytes"] += flow.get("bytes", 0)
            agg["flow_count"] += 1

            agg["first_seen"] = min(agg["first_seen"], flow["flow_start"])
            agg["last_seen"] = max(agg["last_seen"], flow["flow_end"])

        aggregation_result = {
            "aggregation_id": aggregation_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "group_by": group_by,
            "total_flows": len(flows_in_window),
            "aggregated_groups": len(aggregations),
            "aggregations": list(aggregations.values()),
            "created_at": utc_now().isoformat(),
        }

        self._aggregations[aggregation_id] = aggregation_result
        return aggregation_result

    async def get_top_talkers(self, **kwargs) -> List[Dict[str, Any]]:
        """Get top talkers by traffic volume."""
        hours = kwargs.get("hours", 1)
        limit = kwargs.get("limit", 10)
        metric = kwargs.get("metric", "bytes")  # bytes or packets

        cutoff_time = utc_now() - timedelta(hours=hours)

        recent_flows = [
            flow
            for flow in self._flow_records
            if datetime.fromisoformat(flow["ingested_at"]) >= cutoff_time
        ]

        # Aggregate by source address
        talkers = {}
        for flow in recent_flows:
            src_addr = flow.get("src_addr", "unknown")
            if src_addr not in talkers:
                talkers[src_addr] = {
                    "src_addr": src_addr,
                    "total_bytes": 0,
                    "total_packets": 0,
                    "flow_count": 0,
                }

            talkers[src_addr]["total_bytes"] += flow.get("bytes", 0)
            talkers[src_addr]["total_packets"] += flow.get("packets", 0)
            talkers[src_addr]["flow_count"] += 1

        # Sort by metric and return top N
        sorted_talkers = sorted(
            talkers.values(), key=lambda t: t[f"total_{metric}"], reverse=True
        )

        return sorted_talkers[:limit]


class FlowAnalyticsSDK:
    """Minimal, reusable SDK for flow analytics."""

    def __init__(self, tenant_id: str):
        """  Init   operation."""
        self.tenant_id = tenant_id
        self._service = FlowAnalyticsService()

    async def create_netflow_collector(
        self,
        collector_name: str,
        listen_port: int,
        version: str = "9",
        sampling_rate: int = 1,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create NetFlow collector."""
        collector = await self._service.create_flow_collector(
            collector_name=collector_name,
            flow_type="netflow",
            listen_port=listen_port,
            version=version,
            sampling_rate=sampling_rate,
            tenant_id=self.tenant_id,
            **kwargs,
        )

        return {
            "collector_id": collector["collector_id"],
            "collector_name": collector["collector_name"],
            "flow_type": collector["flow_type"],
            "listen_port": collector["listen_port"],
            "listen_address": collector["listen_address"],
            "version": collector["version"],
            "sampling_rate": collector["sampling_rate"],
            "status": collector["status"],
            "created_at": collector["created_at"],
        }

    async def create_sflow_collector(
        self, collector_name: str, listen_port: int, sampling_rate: int = 1024, **kwargs
    ) -> Dict[str, Any]:
        """Create sFlow collector."""
        collector = await self._service.create_flow_collector(
            collector_name=collector_name,
            flow_type="sflow",
            listen_port=listen_port,
            sampling_rate=sampling_rate,
            tenant_id=self.tenant_id,
            **kwargs,
        )

        return {
            "collector_id": collector["collector_id"],
            "collector_name": collector["collector_name"],
            "flow_type": collector["flow_type"],
            "listen_port": collector["listen_port"],
            "sampling_rate": collector["sampling_rate"],
            "status": collector["status"],
            "created_at": collector["created_at"],
        }

    async def ingest_flow_data(  # noqa: PLR0913
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
        flow_record = await self._service.ingest_flow_record(
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

        return {
            "flow_id": flow_record["flow_id"],
            "collector_id": flow_record["collector_id"],
            "src_addr": flow_record["src_addr"],
            "dst_addr": flow_record["dst_addr"],
            "src_port": flow_record["src_port"],
            "dst_port": flow_record["dst_port"],
            "protocol": flow_record["protocol"],
            "packets": flow_record["packets"],
            "bytes": flow_record["bytes"],
            "ingested_at": flow_record["ingested_at"],
        }

    async def get_traffic_summary(self, hours: int = 1) -> Dict[str, Any]:
        """Get traffic summary for time period."""
        cutoff_time = utc_now() - timedelta(hours=hours)

        recent_flows = [
            flow
            for flow in self._service._flow_records
            if datetime.fromisoformat(flow["ingested_at"]) >= cutoff_time
        ]

        total_flows = len(recent_flows)
        total_bytes = sum(flow.get("bytes", 0) for flow in recent_flows)
        total_packets = sum(flow.get("packets", 0) for flow in recent_flows)

        # Count unique sources and destinations
        unique_sources = len(set(flow.get("src_addr", "") for flow in recent_flows))
        unique_destinations = len(
            set(flow.get("dst_addr", "") for flow in recent_flows)
        )

        # Protocol distribution
        protocols = {}
        for flow in recent_flows:
            proto = flow.get("protocol", 0)
            protocols[proto] = protocols.get(proto, 0) + 1

        return {
            "time_period_hours": hours,
            "total_flows": total_flows,
            "total_bytes": total_bytes,
            "total_packets": total_packets,
            "unique_sources": unique_sources,
            "unique_destinations": unique_destinations,
            "protocol_distribution": protocols,
            "average_flow_size_bytes": (
                total_bytes // total_flows if total_flows > 0 else 0
            ),
            "flows_per_second": total_flows // (hours * 3600) if hours > 0 else 0,
            "summary_generated_at": utc_now().isoformat(),
        }

    async def get_top_talkers(
        self, hours: int = 1, limit: int = 10, metric: str = "bytes"
    ) -> List[Dict[str, Any]]:
        """Get top talkers by traffic volume."""
        top_talkers = await self._service.get_top_talkers(
            hours=hours, limit=limit, metric=metric
        )

        return [
            {
                "rank": idx + 1,
                "src_addr": talker["src_addr"],
                "total_bytes": talker["total_bytes"],
                "total_packets": talker["total_packets"],
                "flow_count": talker["flow_count"],
                "percentage": (
                    (
                        talker[f"total_{metric}"]
                        / sum(t[f"total_{metric}"] for t in top_talkers)
                    )
                    * 100
                    if top_talkers
                    else 0
                ),
            }
            for idx, talker in enumerate(top_talkers)
        ]

    async def aggregate_traffic_by_subnet(
        self, subnet_mask: int = 24, hours: int = 1
    ) -> List[Dict[str, Any]]:
        """Aggregate traffic by subnet."""
        cutoff_time = utc_now() - timedelta(hours=hours)

        recent_flows = [
            flow
            for flow in self._service._flow_records
            if datetime.fromisoformat(flow["ingested_at"]) >= cutoff_time
        ]

        # Simple subnet aggregation (assumes IPv4)
        subnets = {}
        for flow in recent_flows:
            src_addr = flow.get("src_addr", "")
            if "." in src_addr:  # IPv4
                octets = src_addr.split(".")
                if len(octets) == 4:
                    if subnet_mask >= 24:
                        subnet = f"{octets[0]}.{octets[1]}.{octets[2]}.0/{subnet_mask}"
                    elif subnet_mask >= 16:
                        subnet = f"{octets[0]}.{octets[1]}.0.0/{subnet_mask}"
                    else:
                        subnet = f"{octets[0]}.0.0.0/{subnet_mask}"

                    if subnet not in subnets:
                        subnets[subnet] = {
                            "subnet": subnet,
                            "total_bytes": 0,
                            "total_packets": 0,
                            "flow_count": 0,
                            "unique_hosts": set(),
                        }

                    subnets[subnet]["total_bytes"] += flow.get("bytes", 0)
                    subnets[subnet]["total_packets"] += flow.get("packets", 0)
                    subnets[subnet]["flow_count"] += 1
                    subnets[subnet]["unique_hosts"].add(src_addr)

        # Convert to list and add host count
        result = []
        for subnet_data in subnets.values():
            result.append(
                {
                    "subnet": subnet_data["subnet"],
                    "total_bytes": subnet_data["total_bytes"],
                    "total_packets": subnet_data["total_packets"],
                    "flow_count": subnet_data["flow_count"],
                    "unique_hosts": len(subnet_data["unique_hosts"]),
                }
            )

        return sorted(result, key=lambda s: s["total_bytes"], reverse=True)

    async def get_protocol_statistics(self, hours: int = 1) -> List[Dict[str, Any]]:
        """Get protocol usage statistics."""
        cutoff_time = utc_now() - timedelta(hours=hours)

        recent_flows = [
            flow
            for flow in self._service._flow_records
            if datetime.fromisoformat(flow["ingested_at"]) >= cutoff_time
        ]

        protocols = {}
        total_bytes = sum(flow.get("bytes", 0) for flow in recent_flows)

        # Protocol name mapping
        protocol_names = {
            1: "ICMP",
            6: "TCP",
            17: "UDP",
            47: "GRE",
            50: "ESP",
            51: "AH",
        }

        for flow in recent_flows:
            proto_num = flow.get("protocol", 0)
            proto_name = protocol_names.get(proto_num, f"Protocol-{proto_num}")

            if proto_name not in protocols:
                protocols[proto_name] = {
                    "protocol": proto_name,
                    "protocol_number": proto_num,
                    "total_bytes": 0,
                    "total_packets": 0,
                    "flow_count": 0,
                }

            protocols[proto_name]["total_bytes"] += flow.get("bytes", 0)
            protocols[proto_name]["total_packets"] += flow.get("packets", 0)
            protocols[proto_name]["flow_count"] += 1

        # Add percentage and sort
        result = []
        for proto_data in protocols.values():
            proto_data["percentage"] = (
                (proto_data["total_bytes"] / total_bytes * 100)
                if total_bytes > 0
                else 0
            )
            result.append(proto_data)

        return sorted(result, key=lambda p: p["total_bytes"], reverse=True)

    async def list_collectors(self) -> List[Dict[str, Any]]:
        """List flow collectors."""
        return [
            {
                "collector_id": collector["collector_id"],
                "collector_name": collector["collector_name"],
                "flow_type": collector["flow_type"],
                "listen_port": collector["listen_port"],
                "status": collector["status"],
                "flows_received": collector["flows_received"],
                "last_flow": collector["last_flow"],
            }
            for collector in self._service._collectors.values()
        ]

    async def get_collector_statistics(self, collector_id: str) -> Dict[str, Any]:
        """Get collector statistics."""
        collector = self._service._collectors.get(collector_id)
        if not collector:
            raise NetworkingError(f"Collector not found: {collector_id}")

        # Count flows for this collector
        collector_flows = [
            flow
            for flow in self._service._flow_records
            if flow.get("collector_id") == collector_id
        ]

        return {
            "collector_id": collector_id,
            "collector_name": collector["collector_name"],
            "flow_type": collector["flow_type"],
            "status": collector["status"],
            "flows_received": collector["flows_received"],
            "flows_in_memory": len(collector_flows),
            "last_flow": collector["last_flow"],
            "created_at": collector["created_at"],
        }
