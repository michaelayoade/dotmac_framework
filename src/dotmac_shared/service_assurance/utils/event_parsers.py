"""Event parsing utilities for SNMP traps and syslog messages."""

import ipaddress
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


class SNMPTrapParser:
    """Parser for SNMP trap messages."""

    # Common SNMP trap OIDs and their meanings
    STANDARD_TRAPS = {
        "1.3.6.1.6.3.1.1.5.1": "coldStart",
        "1.3.6.1.6.3.1.1.5.2": "warmStart",
        "1.3.6.1.6.3.1.1.5.3": "linkDown",
        "1.3.6.1.6.3.1.1.5.4": "linkUp",
        "1.3.6.1.6.3.1.1.5.5": "authenticationFailure",
        "1.3.6.1.6.3.1.1.5.6": "egpNeighborLoss",
    }

    # Enterprise-specific OID prefixes
    ENTERPRISE_PREFIXES = {
        "1.3.6.1.4.1.9": "cisco",
        "1.3.6.1.4.1.2636": "juniper",
        "1.3.6.1.4.1.1916": "extreme",
        "1.3.6.1.4.1.2544": "adva",
        "1.3.6.1.4.1.6527": "alcatel",
        "1.3.6.1.4.1.11": "hp",
        "1.3.6.1.4.1.171": "dlink",
    }

    def __init__(self, timezone):
        """Initialize SNMP trap parser."""
        pass

    def parse_trap_data(self, raw_trap: str) -> Dict[str, Any]:
        """Parse raw SNMP trap data into structured format."""
        try:
            trap_data = {
                "trap_type": "unknown",
                "enterprise_oid": None,
                "enterprise_name": None,
                "trap_oid": None,
                "trap_name": None,
                "agent_addr": None,
                "generic_trap": None,
                "specific_trap": None,
                "timestamp": None,
                "varbinds": {},
                "severity": "info",
                "description": "",
                "parsing_errors": [],
            }

            # Parse basic trap information from raw data
            lines = raw_trap.strip().split("\n")

            for line in lines:
                line = line.strip()

                # Parse trap OID
                if "Trap OID:" in line:
                    oid_match = re.search(r"Trap OID:\s*([0-9.]+)", line)
                    if oid_match:
                        trap_data["trap_oid"] = oid_match.group(1)
                        trap_data["trap_name"] = self.get_trap_name(
                            trap_data["trap_oid"]
                        )

                # Parse agent address
                elif "Agent Address:" in line:
                    addr_match = re.search(r"Agent Address:\s*(\S+)", line)
                    if addr_match:
                        trap_data["agent_addr"] = addr_match.group(1)

                # Parse enterprise OID
                elif "Enterprise:" in line:
                    ent_match = re.search(r"Enterprise:\s*([0-9.]+)", line)
                    if ent_match:
                        trap_data["enterprise_oid"] = ent_match.group(1)
                        trap_data["enterprise_name"] = self.get_enterprise_name(
                            trap_data["enterprise_oid"]
                        )

                # Parse generic trap type
                elif "Generic Trap:" in line:
                    gen_match = re.search(r"Generic Trap:\s*(\d+)", line)
                    if gen_match:
                        trap_data["generic_trap"] = int(gen_match.group(1))

                # Parse specific trap type
                elif "Specific Trap:" in line:
                    spec_match = re.search(r"Specific Trap:\s*(\d+)", line)
                    if spec_match:
                        trap_data["specific_trap"] = int(spec_match.group(1))

                # Parse timestamp
                elif "Timestamp:" in line:
                    time_match = re.search(r"Timestamp:\s*(.+)", line)
                    if time_match:
                        trap_data["timestamp"] = time_match.group(1)

                # Parse varbinds
                elif "=" in line and (":" in line or "=" in line):
                    varbind = self.parse_varbind(line)
                    if varbind:
                        trap_data["varbinds"][varbind["oid"]] = varbind["value"]

            # Determine trap severity and description
            trap_data.update(self.analyze_trap_severity(trap_data))

            return trap_data

        except Exception as e:
            return {
                "trap_type": "parse_error",
                "parsing_errors": [f"Failed to parse trap: {str(e)}"],
                "raw_data": raw_trap,
            }

    def parse_varbind(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a single varbind line."""
        try:
            # Common varbind formats:
            # OID = Type: Value
            # OID: Value
            # OID = Value

            if " = " in line:
                parts = line.split(" = ", 1)
                oid = parts[0].strip()
                value_part = parts[1].strip()

                # Extract type and value if present
                if ": " in value_part:
                    type_value = value_part.split(": ", 1)
                    varbind_type = type_value[0].strip()
                    value = type_value[1].strip()
                else:
                    varbind_type = "unknown"
                    value = value_part
            elif ": " in line:
                parts = line.split(": ", 1)
                oid = parts[0].strip()
                value = parts[1].strip()
                varbind_type = "unknown"
            else:
                return None

            return {
                "oid": oid,
                "type": varbind_type,
                "value": value,
            }

        except Exception:
            return None

    def get_trap_name(self, trap_oid: str) -> str:
        """Get human-readable trap name from OID."""
        return self.STANDARD_TRAPS.get(trap_oid, f"trap_{trap_oid.replace('.', '_')}")

    def get_enterprise_name(self, enterprise_oid: str) -> str:
        """Get enterprise name from OID."""
        for prefix, name in self.ENTERPRISE_PREFIXES.items():
            if enterprise_oid.startswith(prefix):
                return name
        return "unknown"

    def analyze_trap_severity(self, trap_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze trap to determine severity and description."""
        severity = "info"
        description = ""

        trap_oid = trap_data.get("trap_oid", "")
        trap_name = trap_data.get("trap_name", "")

        # Analyze based on standard traps
        if trap_oid == "1.3.6.1.6.3.1.1.5.3":  # linkDown
            severity = "major"
            description = "Network interface went down"
        elif trap_oid == "1.3.6.1.6.3.1.1.5.4":  # linkUp
            severity = "info"
            description = "Network interface came up"
        elif trap_oid in [
            "1.3.6.1.6.3.1.1.5.1",
            "1.3.6.1.6.3.1.1.5.2",
        ]:  # cold/warm start
            severity = "warning"
            description = "Device restarted"
        elif trap_oid == "1.3.6.1.6.3.1.1.5.5":  # authenticationFailure
            severity = "warning"
            description = "SNMP authentication failure"

        # Analyze based on varbinds
        varbinds = trap_data.get("varbinds", {})
        for oid, value in varbinds.items():
            if "error" in str(value).lower():
                severity = "warning"
            elif "fail" in str(value).lower():
                severity = "major"
            elif "critical" in str(value).lower():
                severity = "critical"

        # Generate description if not set
        if not description:
            enterprise = trap_data.get("enterprise_name", "unknown")
            description = f"{enterprise} {trap_name} trap"

        return {
            "severity": severity,
            "description": description,
        }


class SyslogParser:
    """Parser for syslog messages."""

    # Syslog facilities
    FACILITIES = {
        0: "kernel",
        1: "user",
        2: "mail",
        3: "daemon",
        4: "security",
        5: "syslogd",
        6: "lpr",
        7: "news",
        8: "uucp",
        9: "cron",
        10: "authpriv",
        11: "ftp",
        16: "local0",
        17: "local1",
        18: "local2",
        19: "local3",
        20: "local4",
        21: "local5",
        22: "local6",
        23: "local7",
    }

    # Syslog severities (RFC 3164)
    SEVERITIES = {
        0: "emergency",
        1: "alert",
        2: "critical",
        3: "error",
        4: "warning",
        5: "notice",
        6: "info",
        7: "debug",
    }

    def __init__(self):
        """Initialize syslog parser."""
        self.timestamp_patterns = [
            r"(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})",  # RFC 3164: Oct 11 22:14:15
            r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?(?:Z|[+-]\d{2}:\d{2})?)",  # RFC 3339
            r"(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})",  # MM/DD/YYYY HH:MM:SS
        ]

    def parse_syslog_message(self, raw_message: str) -> Dict[str, Any]:
        """Parse raw syslog message into structured format."""
        try:
            syslog_data = {
                "facility": 16,  # Default to local0
                "severity": 6,  # Default to info
                "facility_name": "local0",
                "severity_name": "info",
                "timestamp": None,
                "hostname": None,
                "program": None,
                "pid": None,
                "message": raw_message,
                "structured_data": {},
                "parsing_errors": [],
            }

            message = raw_message.strip()

            # Parse priority (facility and severity)
            priority_match = re.match(r"^<(\d+)>", message)
            if priority_match:
                priority = int(priority_match.group(1))
                syslog_data["facility"] = priority >> 3
                syslog_data["severity"] = priority & 7
                syslog_data["facility_name"] = self.FACILITIES.get(
                    syslog_data["facility"], "unknown"
                )
                syslog_data["severity_name"] = self.SEVERITIES.get(
                    syslog_data["severity"], "unknown"
                )

                message = message[priority_match.end() :].strip()

            # Parse timestamp
            for pattern in self.timestamp_patterns:
                timestamp_match = re.search(pattern, message)
                if timestamp_match:
                    syslog_data["timestamp"] = timestamp_match.group(1)
                    message = message[timestamp_match.end() :].strip()
                    break

            # Parse hostname/IP
            hostname_match = re.match(r"^(\S+)\s+", message)
            if hostname_match:
                potential_hostname = hostname_match.group(1)
                # Check if it looks like a hostname or IP
                if self.is_valid_hostname_or_ip(potential_hostname):
                    syslog_data["hostname"] = potential_hostname
                    message = message[hostname_match.end() :].strip()

            # Parse program name and PID
            program_match = re.match(r"^(\w+)(?:\[(\d+)\])?:\s*", message)
            if program_match:
                syslog_data["program"] = program_match.group(1)
                if program_match.group(2):
                    syslog_data["pid"] = int(program_match.group(2))
                message = message[program_match.end() :].strip()

            # The remaining message is the actual log content
            syslog_data["message"] = message

            # Parse structured data if present (RFC 5424 style)
            structured_data = self.parse_structured_data(message)
            if structured_data:
                syslog_data["structured_data"] = structured_data

            # Extract additional insights
            syslog_data.update(self.analyze_message_content(message))

            return syslog_data

        except Exception as e:
            return {
                "facility": 16,
                "severity": 6,
                "message": raw_message,
                "parsing_errors": [f"Failed to parse syslog: {str(e)}"],
            }

    def parse_structured_data(self, message: str) -> Dict[str, Any]:
        """Parse structured data from syslog message."""
        structured_data = {}

        # Look for key=value pairs
        kv_pattern = r'(\w+)=(["\']?)([^"\'\s]+)\2'
        matches = re.findall(kv_pattern, message)

        for key, quote, value in matches:
            structured_data[key] = value

        return structured_data

    def is_valid_hostname_or_ip(self, text: str) -> bool:
        """Check if text is a valid hostname or IP address."""
        try:
            # Check if it's an IP address
            ipaddress.ip_address(text)
            return True
        except ValueError:
            # Check if it looks like a hostname
            hostname_pattern = r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$"
            return bool(re.match(hostname_pattern, text)) and len(text) <= 253

    def analyze_message_content(self, message: str) -> Dict[str, Any]:
        """Analyze message content for additional insights."""
        analysis = {
            "keywords": [],
            "severity_indicators": [],
            "ip_addresses": [],
            "urls": [],
            "potential_security_event": False,
        }

        message_lower = message.lower()

        # Security-related keywords
        security_keywords = [
            "failed",
            "failure",
            "error",
            "denied",
            "unauthorized",
            "attack",
            "intrusion",
            "malware",
            "virus",
            "breach",
            "compromise",
            "exploit",
        ]

        for keyword in security_keywords:
            if keyword in message_lower:
                analysis["keywords"].append(keyword)
                analysis["potential_security_event"] = True

        # Severity indicators
        severity_indicators = {
            "critical": ["critical", "fatal", "emergency"],
            "error": ["error", "err", "failed", "failure"],
            "warning": ["warning", "warn", "deprecated"],
            "info": ["info", "information", "notice"],
        }

        for severity, indicators in severity_indicators.items():
            for indicator in indicators:
                if indicator in message_lower:
                    analysis["severity_indicators"].append(severity)
                    break

        # Extract IP addresses
        ip_pattern = r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"
        analysis["ip_addresses"] = re.findall(ip_pattern, message)

        # Extract URLs
        url_pattern = r"https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9]?\.(?:com|org|net|edu|gov|mil|int|arpa|[a-z]{2})"
        analysis["urls"] = re.findall(url_pattern, message)

        return analysis


class EventNormalizer:
    """Normalize events from different sources to common format."""

    def __init__(self):
        """Initialize event normalizer."""
        self.snmp_parser = SNMPTrapParser()
        self.syslog_parser = SyslogParser()

    def normalize_snmp_trap(
        self, raw_trap: str, source_ip: str, source_device: Optional[str] = None
    ) -> Dict[str, Any]:
        """Normalize SNMP trap to common event format."""
        parsed_trap = self.snmp_parser.parse_trap_data(raw_trap)

        return {
            "event_type": "snmp_trap",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": {
                "device": source_device or source_ip,
                "ip": source_ip,
                "type": "network_device",
            },
            "severity": parsed_trap.get("severity", "info"),
            "category": "network",
            "title": f"SNMP Trap: {parsed_trap.get('trap_name', 'unknown')}",
            "description": parsed_trap.get("description", ""),
            "details": {
                "trap_oid": parsed_trap.get("trap_oid"),
                "enterprise": parsed_trap.get("enterprise_name"),
                "varbinds": parsed_trap.get("varbinds", {}),
                "agent_addr": parsed_trap.get("agent_addr"),
            },
            "raw_data": raw_trap,
            "parsing_errors": parsed_trap.get("parsing_errors", []),
        }

    def normalize_syslog_message(
        self, raw_message: str, source_ip: str, source_device: Optional[str] = None
    ) -> Dict[str, Any]:
        """Normalize syslog message to common event format."""
        parsed_syslog = self.syslog_parser.parse_syslog_message(raw_message)

        return {
            "event_type": "syslog",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": {
                "device": source_device or parsed_syslog.get("hostname") or source_ip,
                "ip": source_ip,
                "type": "system",
                "hostname": parsed_syslog.get("hostname"),
                "program": parsed_syslog.get("program"),
                "pid": parsed_syslog.get("pid"),
            },
            "severity": parsed_syslog.get("severity_name", "info"),
            "category": "system",
            "title": f"Syslog: {parsed_syslog.get('program', 'system')} message",
            "description": parsed_syslog.get("message", ""),
            "details": {
                "facility": parsed_syslog.get("facility_name"),
                "facility_code": parsed_syslog.get("facility"),
                "severity_code": parsed_syslog.get("severity"),
                "structured_data": parsed_syslog.get("structured_data", {}),
                "keywords": parsed_syslog.get("keywords", []),
                "security_event": parsed_syslog.get("potential_security_event", False),
                "ip_addresses": parsed_syslog.get("ip_addresses", []),
            },
            "raw_data": raw_message,
            "parsing_errors": parsed_syslog.get("parsing_errors", []),
        }

    def extract_event_patterns(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract patterns from a collection of events."""
        patterns = {
            "common_sources": {},
            "frequent_errors": {},
            "severity_distribution": {},
            "time_patterns": [],
            "correlation_candidates": [],
        }

        for event in events:
            # Count sources
            source_key = event.get("source", {}).get("device", "unknown")
            patterns["common_sources"][source_key] = (
                patterns["common_sources"].get(source_key, 0) + 1
            )

            # Count severities
            severity = event.get("severity", "unknown")
            patterns["severity_distribution"][severity] = (
                patterns["severity_distribution"].get(severity, 0) + 1
            )

            # Look for error patterns
            description = event.get("description", "").lower()
            if any(
                term in description
                for term in ["error", "fail", "exception", "timeout"]
            ):
                patterns["frequent_errors"][description[:50]] = (
                    patterns["frequent_errors"].get(description[:50], 0) + 1
                )

        # Sort by frequency
        patterns["common_sources"] = dict(
            sorted(patterns["common_sources"].items(), key=lambda x: x[1], reverse=True)
        )
        patterns["frequent_errors"] = dict(
            sorted(
                patterns["frequent_errors"].items(), key=lambda x: x[1], reverse=True
            )
        )

        return patterns
