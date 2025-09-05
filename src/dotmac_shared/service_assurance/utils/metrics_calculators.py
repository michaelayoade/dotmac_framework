"""Metrics calculation and aggregation utilities."""

import statistics
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union


class PerformanceMetrics:
    """Calculate performance metrics from time series data."""

    # TODO: Fix parameter ordering - parameters without defaults must come before those with defaults
    def __init__(self, max_data_points: int = 10000, timezone: Optional[str] = None):
        """Initialize performance metrics calculator."""
        self.max_data_points = max_data_points

    def calculate_availability(
        self, measurements: list[dict[str, Any]], success_key: str = "success"
    ) -> dict[str, float]:
        """Calculate availability metrics from measurements."""
        if not measurements:
            return {
                "availability_percent": 0.0,
                "uptime_ratio": 0.0,
                "total_measurements": 0,
                "successful_measurements": 0,
            }

        successful = sum(1 for m in measurements if m.get(success_key, False))
        total = len(measurements)
        availability = (successful / total) * 100 if total > 0 else 0

        return {
            "availability_percent": round(availability, 3),
            "uptime_ratio": round(successful / total, 4) if total > 0 else 0,
            "total_measurements": total,
            "successful_measurements": successful,
            "failed_measurements": total - successful,
        }

    def calculate_latency_statistics(
        self,
        measurements: list[dict[str, Any]],
        latency_key: str = "response_time_ms",
        percentiles: Optional[list[float]] = None,
    ) -> dict[str, float]:
        """Calculate latency statistics from measurements."""
        if percentiles is None:
            percentiles = [50, 90, 95, 99]
        latency_values = [
            m.get(latency_key, 0) for m in measurements if m.get(latency_key) is not None and m.get("success", False)
        ]

        if not latency_values:
            return {
                "count": 0,
                "average_ms": 0.0,
                "median_ms": 0.0,
                "min_ms": 0.0,
                "max_ms": 0.0,
                "std_dev_ms": 0.0,
                **{f"p{int(p)}_ms": 0.0 for p in percentiles},
            }

        stats = {
            "count": len(latency_values),
            "average_ms": round(statistics.mean(latency_values), 3),
            "median_ms": round(statistics.median(latency_values), 3),
            "min_ms": round(min(latency_values), 3),
            "max_ms": round(max(latency_values), 3),
            "std_dev_ms": round(statistics.stdev(latency_values) if len(latency_values) > 1 else 0.0, 3),
        }

        # Calculate percentiles
        sorted_values = sorted(latency_values)
        for percentile in percentiles:
            index = int(len(sorted_values) * (percentile / 100)) - 1
            index = max(0, min(index, len(sorted_values) - 1))
            stats[f"p{int(percentile)}_ms"] = round(sorted_values[index], 3)

        return stats

    def calculate_throughput_metrics(
        self,
        measurements: list[dict[str, Any]],
        time_key: str = "timestamp",
        count_key: str = "count",
        window_minutes: int = 5,
    ) -> dict[str, float]:
        """Calculate throughput metrics."""
        if not measurements:
            return {
                "total_count": 0,
                "average_per_minute": 0.0,
                "peak_per_minute": 0.0,
                "window_minutes": window_minutes,
            }

        # Group measurements by time windows
        windows = defaultdict(int)
        total_count = 0

        for measurement in measurements:
            timestamp_str = measurement.get(time_key)
            count = measurement.get(count_key, 1)

            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    # Round down to window boundary
                    window_start = timestamp.replace(
                        minute=(timestamp.minute // window_minutes) * window_minutes,
                        second=0,
                        microsecond=0,
                    )
                    windows[window_start] += count
                    total_count += count
                except (ValueError, AttributeError):
                    continue

        if not windows:
            return {
                "total_count": total_count,
                "average_per_minute": 0.0,
                "peak_per_minute": 0.0,
                "window_minutes": window_minutes,
            }

        # Calculate metrics
        window_counts = list(windows.values())
        total_windows = len(windows)

        average_per_window = sum(window_counts) / total_windows if total_windows > 0 else 0
        peak_per_window = max(window_counts) if window_counts else 0

        return {
            "total_count": total_count,
            "average_per_minute": round(average_per_window / window_minutes, 3),
            "peak_per_minute": round(peak_per_window / window_minutes, 3),
            "window_minutes": window_minutes,
            "total_windows": total_windows,
        }

    def calculate_error_rate(
        self,
        measurements: list[dict[str, Any]],
        success_key: str = "success",
        time_window_minutes: int = 15,
    ) -> dict[str, Any]:
        """Calculate error rate over time."""
        if not measurements:
            return {
                "overall_error_rate": 0.0,
                "error_rate_trend": [],
                "window_minutes": time_window_minutes,
            }

        # Group by time windows
        windows = defaultdict(lambda: {"total": 0, "errors": 0})

        for measurement in measurements:
            timestamp_str = measurement.get("timestamp")
            success = measurement.get(success_key, False)

            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    window_start = timestamp.replace(
                        minute=(timestamp.minute // time_window_minutes) * time_window_minutes,
                        second=0,
                        microsecond=0,
                    )
                    windows[window_start]["total"] += 1
                    if not success:
                        windows[window_start]["errors"] += 1
                except (ValueError, AttributeError):
                    continue

        # Calculate overall error rate
        total_measurements = sum(w["total"] for w in windows.values())
        total_errors = sum(w["errors"] for w in windows.values())
        overall_error_rate = (total_errors / total_measurements * 100) if total_measurements > 0 else 0

        # Calculate trend
        trend = []
        for window_time in sorted(windows.keys()):
            window_data = windows[window_time]
            error_rate = (window_data["errors"] / window_data["total"] * 100) if window_data["total"] > 0 else 0
            trend.append(
                {
                    "timestamp": window_time.isoformat(),
                    "error_rate": round(error_rate, 2),
                    "total": window_data["total"],
                    "errors": window_data["errors"],
                }
            )

        return {
            "overall_error_rate": round(overall_error_rate, 3),
            "error_rate_trend": trend,
            "window_minutes": time_window_minutes,
            "total_measurements": total_measurements,
            "total_errors": total_errors,
        }


class SLACalculator:
    """Calculate SLA compliance metrics."""

    def __init__(self):
        """Initialize SLA calculator."""
        pass

    def calculate_sla_compliance(
        self,
        measurements: list[dict[str, Any]],
        availability_threshold: float = 99.9,
        latency_threshold_ms: float = 100.0,
        measurement_window_hours: int = 24,
    ) -> dict[str, Any]:
        """Calculate SLA compliance against thresholds."""
        if not measurements:
            return {
                "compliance_status": "insufficient_data",
                "availability_compliance": False,
                "latency_compliance": False,
                "measurements_count": 0,
            }

        # Filter measurements to window
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=measurement_window_hours)
        windowed_measurements = [m for m in measurements if self._parse_timestamp(m.get("timestamp")) >= cutoff_time]

        if not windowed_measurements:
            return {
                "compliance_status": "insufficient_data",
                "availability_compliance": False,
                "latency_compliance": False,
                "measurements_count": 0,
            }

        # Calculate availability
        availability_metrics = PerformanceMetrics().calculate_availability(windowed_measurements)
        availability_actual = availability_metrics["availability_percent"]
        availability_compliant = availability_actual >= availability_threshold

        # Calculate latency
        latency_metrics = PerformanceMetrics().calculate_latency_statistics(windowed_measurements)
        latency_actual = latency_metrics["average_ms"]
        latency_compliant = latency_actual <= latency_threshold_ms

        # Overall compliance
        overall_compliant = availability_compliant and latency_compliant

        return {
            "compliance_status": "compliant" if overall_compliant else "violation",
            "overall_compliant": overall_compliant,
            "availability": {
                "actual": availability_actual,
                "threshold": availability_threshold,
                "compliant": availability_compliant,
                "margin": round(availability_actual - availability_threshold, 3),
            },
            "latency": {
                "actual_ms": latency_actual,
                "threshold_ms": latency_threshold_ms,
                "compliant": latency_compliant,
                "margin_ms": round(latency_threshold_ms - latency_actual, 3),
            },
            "measurements_count": len(windowed_measurements),
            "measurement_window_hours": measurement_window_hours,
            "evaluation_time": datetime.now(timezone.utc).isoformat(),
        }

    def calculate_sla_credits(
        self,
        actual_availability: float,
        sla_tiers: Optional[list[dict[str, Union[float, str]]]] = None,
    ) -> dict[str, Any]:
        """Calculate SLA credits based on availability."""
        if sla_tiers is None:
            sla_tiers = [
                {"threshold": 99.95, "credit": "0%"},
                {"threshold": 99.9, "credit": "10%"},
                {"threshold": 99.0, "credit": "25%"},
                {"threshold": 95.0, "credit": "50%"},
                {"threshold": 0.0, "credit": "100%"},
            ]

        applicable_tier = None
        for tier in sla_tiers:
            if actual_availability >= tier["threshold"]:
                applicable_tier = tier
                break

        if applicable_tier is None:
            applicable_tier = sla_tiers[-1]  # Worst case

        return {
            "actual_availability": actual_availability,
            "applicable_tier": applicable_tier,
            "credit_percentage": applicable_tier["credit"],
            "threshold_met": applicable_tier["threshold"],
            "downtime_percentage": round(100 - actual_availability, 3),
        }

    def _parse_timestamp(self, timestamp_str: Optional[str]) -> datetime:
        """Parse timestamp string to datetime."""
        if not timestamp_str:
            return datetime.min

        try:
            return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return datetime.min


class TrafficAnalyzer:
    """Analyze network traffic patterns and metrics."""

    def __init__(self):
        """Initialize traffic analyzer."""
        pass

    def analyze_flow_patterns(
        self, flow_records: list[dict[str, Any]], analysis_window_hours: int = 1
    ) -> dict[str, Any]:
        """Analyze traffic flow patterns."""
        if not flow_records:
            return {
                "total_flows": 0,
                "total_bytes": 0,
                "total_packets": 0,
                "analysis_window_hours": analysis_window_hours,
            }

        # Filter to analysis window
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=analysis_window_hours)
        windowed_flows = [
            flow for flow in flow_records if self._parse_timestamp(flow.get("ingested_at")) >= cutoff_time
        ]

        if not windowed_flows:
            return {
                "total_flows": 0,
                "total_bytes": 0,
                "total_packets": 0,
                "analysis_window_hours": analysis_window_hours,
            }

        # Basic aggregations
        total_bytes = sum(flow.get("bytes", 0) for flow in windowed_flows)
        total_packets = sum(flow.get("packets", 0) for flow in windowed_flows)

        # Protocol analysis
        protocol_stats = defaultdict(lambda: {"flows": 0, "bytes": 0, "packets": 0})
        for flow in windowed_flows:
            protocol = flow.get("protocol", 0)
            protocol_stats[protocol]["flows"] += 1
            protocol_stats[protocol]["bytes"] += flow.get("bytes", 0)
            protocol_stats[protocol]["packets"] += flow.get("packets", 0)

        # Port analysis (destination ports)
        port_stats = defaultdict(lambda: {"flows": 0, "bytes": 0})
        for flow in windowed_flows:
            port = flow.get("dst_port", 0)
            if port > 0:
                port_stats[port]["flows"] += 1
                port_stats[port]["bytes"] += flow.get("bytes", 0)

        # Top talkers (source addresses)
        talker_stats = defaultdict(lambda: {"flows": 0, "bytes": 0, "packets": 0})
        for flow in windowed_flows:
            src = flow.get("src_addr", "unknown")
            talker_stats[src]["flows"] += 1
            talker_stats[src]["bytes"] += flow.get("bytes", 0)
            talker_stats[src]["packets"] += flow.get("packets", 0)

        # Calculate rates
        window_seconds = analysis_window_hours * 3600
        flows_per_second = len(windowed_flows) / window_seconds if window_seconds > 0 else 0
        bits_per_second = (total_bytes * 8) / window_seconds if window_seconds > 0 else 0
        packets_per_second = total_packets / window_seconds if window_seconds > 0 else 0

        return {
            "total_flows": len(windowed_flows),
            "total_bytes": total_bytes,
            "total_packets": total_packets,
            "analysis_window_hours": analysis_window_hours,
            "rates": {
                "flows_per_second": round(flows_per_second, 2),
                "bits_per_second": round(bits_per_second, 2),
                "packets_per_second": round(packets_per_second, 2),
                "mbps": round(bits_per_second / 1_000_000, 3),
            },
            "protocol_distribution": dict(
                sorted(protocol_stats.items(), key=lambda x: x[1]["bytes"], reverse=True)[:10]
            ),
            "top_ports": dict(sorted(port_stats.items(), key=lambda x: x[1]["bytes"], reverse=True)[:10]),
            "top_talkers": dict(sorted(talker_stats.items(), key=lambda x: x[1]["bytes"], reverse=True)[:10]),
            "flow_size_stats": self._calculate_flow_size_stats(windowed_flows),
        }

    def detect_traffic_anomalies(
        self,
        flow_records: list[dict[str, Any]],
        baseline_window_hours: int = 24,
        detection_window_minutes: int = 15,
        anomaly_threshold: float = 2.0,  # Standard deviations
    ) -> dict[str, Any]:
        """Detect traffic anomalies using statistical analysis."""
        if len(flow_records) < 10:
            return {
                "anomalies_detected": False,
                "anomalies": [],
                "baseline_insufficient": True,
            }

        # Calculate baseline statistics
        baseline_cutoff = datetime.now(timezone.utc) - timedelta(hours=baseline_window_hours)
        baseline_flows = [
            flow for flow in flow_records if self._parse_timestamp(flow.get("ingested_at")) >= baseline_cutoff
        ]

        if len(baseline_flows) < 10:
            return {
                "anomalies_detected": False,
                "anomalies": [],
                "baseline_insufficient": True,
            }

        # Group baseline into windows for statistical analysis
        window_stats = self._group_flows_by_time_windows(baseline_flows, window_minutes=detection_window_minutes)

        if len(window_stats) < 3:
            return {
                "anomalies_detected": False,
                "anomalies": [],
                "baseline_insufficient": True,
            }

        # Calculate baseline statistics
        bytes_values = [w["total_bytes"] for w in window_stats]
        flows_values = [w["total_flows"] for w in window_stats]

        baseline_bytes_mean = statistics.mean(bytes_values)
        baseline_bytes_stdev = statistics.stdev(bytes_values) if len(bytes_values) > 1 else 0
        baseline_flows_mean = statistics.mean(flows_values)
        baseline_flows_stdev = statistics.stdev(flows_values) if len(flows_values) > 1 else 0

        # Check recent windows for anomalies
        recent_cutoff = datetime.now(timezone.utc) - timedelta(minutes=detection_window_minutes * 3)
        recent_windows = [w for w in window_stats if w["window_start"] >= recent_cutoff]

        anomalies = []
        for window in recent_windows:
            # Check bytes anomaly
            if baseline_bytes_stdev > 0:
                bytes_z_score = abs(window["total_bytes"] - baseline_bytes_mean) / baseline_bytes_stdev
                if bytes_z_score > anomaly_threshold:
                    anomalies.append(
                        {
                            "type": "traffic_volume",
                            "metric": "bytes",
                            "timestamp": window["window_start"].isoformat(),
                            "value": window["total_bytes"],
                            "baseline_mean": baseline_bytes_mean,
                            "z_score": round(bytes_z_score, 2),
                            "severity": "high" if bytes_z_score > 3.0 else "medium",
                        }
                    )

            # Check flows anomaly
            if baseline_flows_stdev > 0:
                flows_z_score = abs(window["total_flows"] - baseline_flows_mean) / baseline_flows_stdev
                if flows_z_score > anomaly_threshold:
                    anomalies.append(
                        {
                            "type": "flow_count",
                            "metric": "flows",
                            "timestamp": window["window_start"].isoformat(),
                            "value": window["total_flows"],
                            "baseline_mean": baseline_flows_mean,
                            "z_score": round(flows_z_score, 2),
                            "severity": "high" if flows_z_score > 3.0 else "medium",
                        }
                    )

        return {
            "anomalies_detected": len(anomalies) > 0,
            "anomalies": anomalies,
            "baseline_insufficient": False,
            "baseline_stats": {
                "window_count": len(window_stats),
                "bytes_mean": round(baseline_bytes_mean, 2),
                "bytes_stdev": round(baseline_bytes_stdev, 2),
                "flows_mean": round(baseline_flows_mean, 2),
                "flows_stdev": round(baseline_flows_stdev, 2),
            },
            "detection_config": {
                "baseline_window_hours": baseline_window_hours,
                "detection_window_minutes": detection_window_minutes,
                "anomaly_threshold": anomaly_threshold,
            },
        }

    def _calculate_flow_size_stats(self, flows: list[dict[str, Any]]) -> dict[str, float]:
        """Calculate flow size statistics."""
        sizes = [flow.get("bytes", 0) for flow in flows if flow.get("bytes", 0) > 0]

        if not sizes:
            return {
                "count": 0,
                "average_bytes": 0,
                "median_bytes": 0,
                "min_bytes": 0,
                "max_bytes": 0,
            }

        return {
            "count": len(sizes),
            "average_bytes": round(statistics.mean(sizes), 2),
            "median_bytes": round(statistics.median(sizes), 2),
            "min_bytes": min(sizes),
            "max_bytes": max(sizes),
        }

    def _group_flows_by_time_windows(
        self, flows: list[dict[str, Any]], window_minutes: int = 15
    ) -> list[dict[str, Any]]:
        """Group flows by time windows for analysis."""
        windows = defaultdict(
            lambda: {
                "total_flows": 0,
                "total_bytes": 0,
                "total_packets": 0,
                "unique_sources": set(),
                "unique_destinations": set(),
            }
        )

        for flow in flows:
            timestamp_str = flow.get("ingested_at")
            if not timestamp_str:
                continue

            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                window_start = timestamp.replace(
                    minute=(timestamp.minute // window_minutes) * window_minutes,
                    second=0,
                    microsecond=0,
                )

                window_data = windows[window_start]
                window_data["total_flows"] += 1
                window_data["total_bytes"] += flow.get("bytes", 0)
                window_data["total_packets"] += flow.get("packets", 0)

                if flow.get("src_addr"):
                    window_data["unique_sources"].add(flow["src_addr"])
                if flow.get("dst_addr"):
                    window_data["unique_destinations"].add(flow["dst_addr"])

            except (ValueError, AttributeError):
                continue

        # Convert to list and add computed fields
        result = []
        for window_start, data in windows.items():
            result.append(
                {
                    "window_start": window_start,
                    "total_flows": data["total_flows"],
                    "total_bytes": data["total_bytes"],
                    "total_packets": data["total_packets"],
                    "unique_sources": len(data["unique_sources"]),
                    "unique_destinations": len(data["unique_destinations"]),
                }
            )

        return sorted(result, key=lambda x: x["window_start"])

    def _parse_timestamp(self, timestamp_str: Optional[str]) -> datetime:
        """Parse timestamp string to datetime."""
        if not timestamp_str:
            return datetime.min

        try:
            return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return datetime.min


class AlertingThresholds:
    """Calculate dynamic alerting thresholds based on historical data."""

    def __init__(self):
        """Initialize alerting thresholds calculator."""
        pass

    def calculate_dynamic_thresholds(
        self,
        historical_values: list[float],
        confidence_level: float = 0.95,
        seasonal_adjustment: bool = True,
    ) -> dict[str, float]:
        """Calculate dynamic thresholds based on historical data."""
        if len(historical_values) < 10:
            return {
                "warning_upper": 0,
                "critical_upper": 0,
                "warning_lower": 0,
                "critical_lower": 0,
                "insufficient_data": True,
            }

        # Remove outliers
        cleaned_values = self._remove_outliers(historical_values)

        if len(cleaned_values) < 5:
            return {
                "warning_upper": 0,
                "critical_upper": 0,
                "warning_lower": 0,
                "critical_lower": 0,
                "insufficient_data": True,
            }

        # Calculate statistics
        mean_val = statistics.mean(cleaned_values)
        stdev_val = statistics.stdev(cleaned_values) if len(cleaned_values) > 1 else 0

        # Calculate z-scores for confidence level
        # 95% confidence ≈ 1.96 standard deviations
        # 99% confidence ≈ 2.58 standard deviations
        z_warning = 1.96 if confidence_level == 0.95 else 2.58
        z_critical = 2.58 if confidence_level == 0.95 else 3.29

        # Calculate thresholds
        warning_upper = mean_val + (z_warning * stdev_val)
        critical_upper = mean_val + (z_critical * stdev_val)
        warning_lower = max(0, mean_val - (z_warning * stdev_val))
        critical_lower = max(0, mean_val - (z_critical * stdev_val))

        return {
            "warning_upper": round(warning_upper, 3),
            "critical_upper": round(critical_upper, 3),
            "warning_lower": round(warning_lower, 3),
            "critical_lower": round(critical_lower, 3),
            "mean": round(mean_val, 3),
            "standard_deviation": round(stdev_val, 3),
            "confidence_level": confidence_level,
            "data_points": len(cleaned_values),
            "insufficient_data": False,
        }

    def _remove_outliers(self, values: list[float], method: str = "iqr") -> list[float]:
        """Remove outliers from data using IQR method."""
        if len(values) < 4:
            return values

        if method == "iqr":
            # Interquartile Range method
            sorted_values = sorted(values)
            n = len(sorted_values)
            q1_idx = n // 4
            q3_idx = 3 * n // 4

            q1 = sorted_values[q1_idx]
            q3 = sorted_values[q3_idx]
            iqr = q3 - q1

            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

            return [v for v in values if lower_bound <= v <= upper_bound]

        elif method == "zscore":
            # Z-score method
            mean_val = statistics.mean(values)
            stdev_val = statistics.stdev(values) if len(values) > 1 else 0

            if stdev_val == 0:
                return values

            return [v for v in values if abs((v - mean_val) / stdev_val) < 3.0]

        return values
