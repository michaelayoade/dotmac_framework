"""
PII redaction for logs and data sanitization.
"""

import re
import hashlib
from typing import Any, Dict, List, Optional, Set, Pattern
from dataclasses import dataclass
from enum import Enum

import structlog

logger = structlog.get_logger(__name__)


class PIIType(str, Enum):
    """Types of PII that can be detected and redacted."""

    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    IP_ADDRESS = "ip_address"
    API_KEY = "api_key"
    PASSWORD = "password"
    TOKEN = "token"
    USER_ID = "user_id"
    CUSTOM = "custom"


@dataclass
class PIIPattern:
    """PII detection pattern."""

    pii_type: PIIType
    pattern: Pattern[str]
    replacement: str = "[REDACTED]"
    confidence: float = 1.0
    description: str = ""

    def __post_init__(self):
        if isinstance(self.pattern, str):
            self.pattern = re.compile(self.pattern, re.IGNORECASE)


class PIIDetector:
    """PII detection and redaction engine."""

    def __init__(self):
        self.patterns: List[PIIPattern] = []
        self.sensitive_fields: Set[str] = set()
        self.hash_salt = "dotmac_pii_salt_2024"
        self._initialize_default_patterns()

    def _initialize_default_patterns(self):
        """Initialize default PII detection patterns."""
        default_patterns = [
            # Email addresses
            PIIPattern(
                pii_type=PIIType.EMAIL,
                pattern=r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                replacement="[EMAIL_REDACTED]",
                description="Email address"
            ),

            # Phone numbers (US format)
            PIIPattern(
                pii_type=PIIType.PHONE,
                pattern=r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b',
                replacement="[PHONE_REDACTED]",
                description="US phone number"
            ),

            # Social Security Numbers
            PIIPattern(
                pii_type=PIIType.SSN,
                pattern=r'\b\d{3}-?\d{2}-?\d{4}\b',
                replacement="[SSN_REDACTED]",
                description="Social Security Number"
            ),

            # Credit card numbers (basic pattern)
            PIIPattern(
                pii_type=PIIType.CREDIT_CARD,
                pattern=r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
                replacement="[CARD_REDACTED]",
                description="Credit card number"
            ),

            # IP addresses
            PIIPattern(
                pii_type=PIIType.IP_ADDRESS,
                pattern=r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
                replacement="[IP_REDACTED]",
                description="IPv4 address"
            ),

            # API keys (common patterns)
            PIIPattern(
                pii_type=PIIType.API_KEY,
                pattern=r'\b[A-Za-z0-9]{32,}\b',
                replacement="[API_KEY_REDACTED]",
                confidence=0.7,
                description="Potential API key"
            ),

            # JWT tokens
            PIIPattern(
                pii_type=PIIType.TOKEN,
                pattern=r'\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b',
                replacement="[JWT_REDACTED]",
                description="JWT token"
            ),

            # Password fields (in JSON/form data)
            PIIPattern(
                pii_type=PIIType.PASSWORD,
                pattern=r'("password"\s*:\s*")[^"]*(")',
                replacement=r'\1[PASSWORD_REDACTED]\2',
                description="Password in JSON"
            ),
        ]

        self.patterns.extend(default_patterns)

        # Common sensitive field names
        self.sensitive_fields.update([
            "password", "passwd", "pwd", "secret", "token", "key", "api_key",
            "access_token", "refresh_token", "auth_token", "session_id",
            "ssn", "social_security", "credit_card", "card_number", "cvv",
            "pin", "private_key", "certificate", "signature"
        ])

    def add_pattern(self, pattern: PIIPattern):
        """Add a custom PII detection pattern."""
        self.patterns.append(pattern)
        logger.info("PII pattern added", pii_type=pattern.pii_type.value, description=pattern.description)

    def add_sensitive_field(self, field_name: str):
        """Add a sensitive field name."""
        self.sensitive_fields.add(field_name.lower())

    def detect_pii(self, text: str) -> List[Dict[str, Any]]:
        """Detect PII in text and return findings."""
        findings = []

        for pattern in self.patterns:
            matches = pattern.pattern.finditer(text)
            for match in matches:
                findings.append({
                    "pii_type": pattern.pii_type.value,
                    "start": match.start(),
                    "end": match.end(),
                    "matched_text": match.group(),
                    "confidence": pattern.confidence,
                    "description": pattern.description
                })

        return findings

    def redact_text(self, text: str, hash_pii: bool = False) -> str:
        """Redact PII from text."""
        if not text:
            return text

        redacted_text = text

        for pattern in self.patterns:
            if hash_pii and pattern.pii_type in [PIIType.EMAIL, PIIType.USER_ID]:
                # Hash instead of redact for certain types
                def hash_replacement(match):
                    original = match.group()
                    hashed = self._hash_pii(original)
                    return f"[{pattern.pii_type.value.upper()}_HASH:{hashed}]"

                redacted_text = pattern.pattern.sub(hash_replacement, redacted_text)
            else:
                redacted_text = pattern.pattern.sub(pattern.replacement, redacted_text)

        return redacted_text

    def redact_dict(self, data: Dict[str, Any], hash_pii: bool = False) -> Dict[str, Any]:
        """Redact PII from dictionary data."""
        if not isinstance(data, dict):
            return data

        redacted_data = {}

        for key, value in data.items():
            key_lower = key.lower()

            # Check if field name is sensitive
            if any(sensitive in key_lower for sensitive in self.sensitive_fields):
                if hash_pii and key_lower in ["user_id", "email"]:
                    redacted_data[key] = self._hash_pii(str(value))
                else:
                    redacted_data[key] = "[FIELD_REDACTED]"
            elif isinstance(value, str):
                redacted_data[key] = self.redact_text(value, hash_pii)
            elif isinstance(value, dict):
                redacted_data[key] = self.redact_dict(value, hash_pii)
            elif isinstance(value, list):
                redacted_data[key] = self.redact_list(value, hash_pii)
            else:
                redacted_data[key] = value

        return redacted_data

    def redact_list(self, data: List[Any], hash_pii: bool = False) -> List[Any]:
        """Redact PII from list data."""
        redacted_list = []

        for item in data:
            if isinstance(item, str):
                redacted_list.append(self.redact_text(item, hash_pii))
            elif isinstance(item, dict):
                redacted_list.append(self.redact_dict(item, hash_pii))
            elif isinstance(item, list):
                redacted_list.append(self.redact_list(item, hash_pii))
            else:
                redacted_list.append(item)

        return redacted_list

    def _hash_pii(self, value: str) -> str:
        """Hash PII value for pseudonymization."""
        combined = f"{self.hash_salt}:{value}"
        return hashlib.sha256(combined.encode()).hexdigest()[:12]

    def scan_for_pii(self, data: Any) -> Dict[str, Any]:  # noqa: C901
        """Scan data for PII and return analysis."""
        findings = {
            "has_pii": False,
            "pii_types": set(),
            "sensitive_fields": [],
            "total_findings": 0,
            "confidence_scores": []
        }

        def scan_recursive(obj, path=""):
            if isinstance(obj, str):
                text_findings = self.detect_pii(obj)
                if text_findings:
                    findings["has_pii"] = True
                    findings["total_findings"] += len(text_findings)
                    for finding in text_findings:
                        findings["pii_types"].add(finding["pii_type"])
                        findings["confidence_scores"].append(finding["confidence"])

            elif isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key

                    # Check if field name is sensitive
                    if any(sensitive in key.lower() for sensitive in self.sensitive_fields):
                        findings["sensitive_fields"].append(current_path)
                        findings["has_pii"] = True

                    scan_recursive(value, current_path)

            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    current_path = f"{path}[{i}]" if path else f"[{i}]"
                    scan_recursive(item, current_path)

        scan_recursive(data)

        # Convert set to list for JSON serialization
        findings["pii_types"] = list(findings["pii_types"])

        # Calculate average confidence
        if findings["confidence_scores"]:
            findings["avg_confidence"] = sum(findings["confidence_scores"]) / len(findings["confidence_scores"])
        else:
            findings["avg_confidence"] = 0.0

        return findings


class PIIRedactionFilter:
    """Structured logging filter for PII redaction."""

    def __init__(self, detector: PIIDetector, hash_pii: bool = False):
        self.detector = detector
        self.hash_pii = hash_pii

    def __call__(self, logger, method_name, event_dict):
        """Filter log events to redact PII."""
        try:
            # Redact PII from the main message
            if "event" in event_dict:
                event_dict["event"] = self.detector.redact_text(event_dict["event"], self.hash_pii)

            # Redact PII from all other fields
            for key, value in list(event_dict.items()):
                if key in ["timestamp", "level", "logger"]:
                    continue  # Skip system fields

                if isinstance(value, str):
                    event_dict[key] = self.detector.redact_text(value, self.hash_pii)
                elif isinstance(value, dict):
                    event_dict[key] = self.detector.redact_dict(value, self.hash_pii)
                elif isinstance(value, list):
                    event_dict[key] = self.detector.redact_list(value, self.hash_pii)

            return event_dict

        except Exception as e:
            # If redaction fails, log the error but don't break logging
            event_dict["pii_redaction_error"] = str(e)
            return event_dict


class PIIAuditLogger:
    """Audit logger for PII access and redaction events."""

    def __init__(self):
        self.audit_events: List[Dict[str, Any]] = []
        self.max_events = 10000

    def log_pii_access(
        self,
        tenant_id: str,
        user_id: Optional[str],
        operation: str,
        pii_types: List[str],
        data_classification: str = "unknown"
    ):
        """Log PII access event."""
        event = {
            "timestamp": structlog.get_logger().info.__globals__.get("time", lambda: 0)(),
            "event_type": "pii_access",
            "tenant_id": tenant_id,
            "user_id": user_id,
            "operation": operation,
            "pii_types": pii_types,
            "data_classification": data_classification
        }

        self._add_audit_event(event)

    def log_pii_redaction(
        self,
        tenant_id: str,
        redaction_type: str,
        findings_count: int,
        pii_types: List[str]
    ):
        """Log PII redaction event."""
        event = {
            "timestamp": structlog.get_logger().info.__globals__.get("time", lambda: 0)(),
            "event_type": "pii_redaction",
            "tenant_id": tenant_id,
            "redaction_type": redaction_type,
            "findings_count": findings_count,
            "pii_types": pii_types
        }

        self._add_audit_event(event)

    def _add_audit_event(self, event: Dict[str, Any]):
        """Add audit event to log."""
        self.audit_events.append(event)

        # Keep only recent events
        if len(self.audit_events) > self.max_events:
            self.audit_events = self.audit_events[-self.max_events//2:]

    def get_audit_events(
        self,
        tenant_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get audit events with optional filtering."""
        filtered_events = self.audit_events

        if tenant_id:
            filtered_events = [e for e in filtered_events if e.get("tenant_id") == tenant_id]

        if event_type:
            filtered_events = [e for e in filtered_events if e.get("event_type") == event_type]

        return filtered_events[-limit:]


class PIIComplianceManager:
    """Manager for PII compliance and data protection."""

    def __init__(self, detector: PIIDetector, audit_logger: PIIAuditLogger):
        self.detector = detector
        self.audit_logger = audit_logger
        self.compliance_rules: Dict[str, Dict[str, Any]] = {}

    def add_compliance_rule(
        self,
        rule_id: str,
        pii_types: List[PIIType],
        retention_days: int,
        redaction_required: bool = True,
        encryption_required: bool = False
    ):
        """Add a compliance rule for PII handling."""
        self.compliance_rules[rule_id] = {
            "pii_types": pii_types,
            "retention_days": retention_days,
            "redaction_required": redaction_required,
            "encryption_required": encryption_required
        }

    def check_compliance(self, data: Any, tenant_id: str) -> Dict[str, Any]:
        """Check data compliance against rules."""
        scan_results = self.detector.scan_for_pii(data)

        compliance_status = {
            "compliant": True,
            "violations": [],
            "recommendations": [],
            "pii_found": scan_results["has_pii"],
            "pii_types": scan_results["pii_types"]
        }

        if scan_results["has_pii"]:
            for rule_id, rule in self.compliance_rules.items():
                # Check if any found PII types match rule
                matching_types = set(scan_results["pii_types"]) & set([t.value for t in rule["pii_types"]])

                if matching_types:
                    if rule["redaction_required"]:
                        compliance_status["violations"].append({
                            "rule_id": rule_id,
                            "violation_type": "redaction_required",
                            "pii_types": list(matching_types),
                            "message": f"PII types {matching_types} require redaction"
                        })
                        compliance_status["compliant"] = False

                    if rule["encryption_required"]:
                        compliance_status["recommendations"].append({
                            "rule_id": rule_id,
                            "recommendation_type": "encryption_recommended",
                            "pii_types": list(matching_types),
                            "message": f"PII types {matching_types} should be encrypted"
                        })

        # Log compliance check
        self.audit_logger.log_pii_access(
            tenant_id=tenant_id,
            user_id=None,
            operation="compliance_check",
            pii_types=scan_results["pii_types"],
            data_classification="sensitive" if scan_results["has_pii"] else "public"
        )

        return compliance_status

    def sanitize_for_logging(self, data: Any, tenant_id: str) -> Any:
        """Sanitize data for safe logging."""
        if isinstance(data, str):
            redacted = self.detector.redact_text(data, hash_pii=True)
        elif isinstance(data, dict):
            redacted = self.detector.redact_dict(data, hash_pii=True)
        elif isinstance(data, list):
            redacted = self.detector.redact_list(data, hash_pii=True)
        else:
            redacted = data

        # Log redaction event
        scan_results = self.detector.scan_for_pii(data)
        if scan_results["has_pii"]:
            self.audit_logger.log_pii_redaction(
                tenant_id=tenant_id,
                redaction_type="logging",
                findings_count=scan_results["total_findings"],
                pii_types=scan_results["pii_types"]
            )

        return redacted


# Configure structured logging with PII redaction
def configure_pii_safe_logging():
    """Configure structlog with PII redaction."""
    detector = PIIDetector()
    pii_filter = PIIRedactionFilter(detector, hash_pii=True)

    structlog.configure(
        processors=[
            pii_filter,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    return detector
