"""Business rule constraints and validation system for DotMac ISP Framework.

This module provides comprehensive business rule validation, constraints enforcement,
and policy-based access control for maintaining data integrity and business logic.
"""

import logging
import re
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Callable, Type, Union
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod

from sqlalchemy import event, text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, ValidationError, validator

from dotmac_isp.core.database import engine

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Severity levels for business rule violations."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class BusinessRuleType(Enum):
    """Types of business rules."""

    VALIDATION = "validation"
    CONSTRAINT = "constraint"
    POLICY = "policy"
    APPROVAL = "approval"


@dataclass
class ValidationResult:
    """Result of a business rule validation."""

    is_valid: bool
    severity: ValidationSeverity
    rule_name: str
    message: str
    field_name: Optional[str] = None
    suggested_action: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class BusinessRule:
    """Definition of a business rule."""

    name: str
    description: str
    rule_type: BusinessRuleType
    severity: ValidationSeverity
    validator: Callable
    applies_to: List[str]  # Table names or entity types
    is_active: bool = True
    priority: int = 100  # Lower number = higher priority


class BaseBusinessRuleValidator(ABC):
    """Base class for business rule validators."""

    @abstractmethod
    def validate(
        self, entity: Any, context: Dict[str, Any] = None
    ) -> List[ValidationResult]:
        """Validate an entity against business rules."""
        pass


class CustomerBusinessRules(BaseBusinessRuleValidator):
    """Business rules specific to customer management."""

    def validate(
        self, customer: Any, context: Dict[str, Any] = None
    ) -> List[ValidationResult]:
        """Validate customer business rules."""
        results = []
        context = context or {}

        # Rule: Customer number format validation
        results.append(self._validate_customer_number_format(customer))

        # Rule: Credit limit validation
        results.append(self._validate_credit_limit(customer))

        # Rule: Contact information completeness
        results.append(self._validate_contact_information(customer))

        # Rule: Business customer requirements
        if hasattr(customer, "customer_type") and customer.customer_type == "business":
            results.append(self._validate_business_customer_requirements(customer))

        # Rule: Account status transitions
        if context.get("operation") == "status_change":
            results.append(self._validate_status_transition(customer, context))

        return [r for r in results if r is not None]

    def _validate_customer_number_format(self, customer) -> Optional[ValidationResult]:
        """Validate customer number format (CUS-XXXXXX)."""
        if not hasattr(customer, "customer_number") or not customer.customer_number:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                rule_name="customer_number_required",
                message="Customer number is required",
                field_name="customer_number",
                suggested_action="Generate customer number using format CUS-XXXXXX",
            )

        pattern = r"^CUS-\d{6}$"
        if not re.match(pattern, customer.customer_number):
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                rule_name="customer_number_format",
                message="Customer number must follow format CUS-XXXXXX",
                field_name="customer_number",
                suggested_action="Use format CUS-XXXXXX where X is a digit",
            )

        return ValidationResult(
            is_valid=True,
            severity=ValidationSeverity.INFO,
            rule_name="customer_number_format",
            message="Customer number format is valid",
        )

    def _validate_credit_limit(self, customer) -> Optional[ValidationResult]:
        """Validate credit limit constraints."""
        if not hasattr(customer, "credit_limit"):
            return None

        try:
            credit_limit = Decimal(str(customer.credit_limit))
        except (TypeError, ValueError, InvalidOperation) as e:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                rule_name="credit_limit_format",
                message="Credit limit must be a valid decimal number",
                field_name="credit_limit",
            )

        # Business rule: Credit limit constraints by customer type
        max_limits = {
            "residential": Decimal("5000.00"),
            "business": Decimal("50000.00"),
            "enterprise": Decimal("500000.00"),
        }

        customer_type = getattr(customer, "customer_type", "residential")
        max_limit = max_limits.get(customer_type, Decimal("5000.00"))

        if credit_limit > max_limit:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.WARNING,
                rule_name="credit_limit_exceeded",
                message=f"Credit limit ${credit_limit} exceeds maximum ${max_limit} for {customer_type} customers",
                field_name="credit_limit",
                suggested_action="Requires management approval for higher limits",
            )

        if credit_limit < 0:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                rule_name="credit_limit_negative",
                message="Credit limit cannot be negative",
                field_name="credit_limit",
            )

        return ValidationResult(
            is_valid=True,
            severity=ValidationSeverity.INFO,
            rule_name="credit_limit_valid",
            message="Credit limit is within acceptable range",
        )

    def _validate_contact_information(self, customer) -> Optional[ValidationResult]:
        """Validate contact information completeness."""
        required_fields = []

        # Check required contact fields
        if not getattr(customer, "email", None):
            required_fields.append("email")

        if not getattr(customer, "phone", None):
            required_fields.append("phone")

        # For business customers, additional requirements
        customer_type = getattr(customer, "customer_type", "residential")
        if customer_type in ["business", "enterprise"]:
            if not getattr(customer, "company_name", None):
                required_fields.append("company_name")

        if required_fields:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.WARNING,
                rule_name="contact_information_incomplete",
                message=f"Missing required contact fields: {', '.join(required_fields)}",
                suggested_action="Complete contact information for better service delivery",
            )

        # Validate email format
        email = getattr(customer, "email", "")
        if email and not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                rule_name="email_format_invalid",
                message="Email address format is invalid",
                field_name="email",
            )

        return ValidationResult(
            is_valid=True,
            severity=ValidationSeverity.INFO,
            rule_name="contact_information_complete",
            message="Contact information is complete and valid",
        )

    def _validate_business_customer_requirements(
        self, customer
    ) -> Optional[ValidationResult]:
        """Validate additional requirements for business customers."""
        missing_fields = []

        if not getattr(customer, "company_name", None):
            missing_fields.append("company_name")

        if not getattr(customer, "street_address", None):
            missing_fields.append("street_address")

        if missing_fields:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                rule_name="business_customer_requirements",
                message=f"Business customers require: {', '.join(missing_fields)}",
                suggested_action="Complete business customer profile information",
            )

        return ValidationResult(
            is_valid=True,
            severity=ValidationSeverity.INFO,
            rule_name="business_customer_requirements",
            message="Business customer requirements satisfied",
        )

    def _validate_status_transition(
        self, customer, context: Dict[str, Any]
    ) -> Optional[ValidationResult]:
        """Validate account status transitions."""
        old_status = context.get("old_status")
        new_status = getattr(customer, "account_status", None)

        if not old_status or not new_status:
            return None

        # Define valid status transitions
        valid_transitions = {
            "pending": ["active", "cancelled"],
            "active": ["suspended", "cancelled"],
            "suspended": ["active", "cancelled"],
            "cancelled": [],  # Cannot transition from cancelled
        }

        allowed_transitions = valid_transitions.get(old_status, [])

        if new_status not in allowed_transitions:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                rule_name="invalid_status_transition",
                message=f"Cannot transition from {old_status} to {new_status}",
                field_name="account_status",
                suggested_action=f"Valid transitions from {old_status}: {', '.join(allowed_transitions)}",
            )

        # Special rules for certain transitions
        if old_status == "active" and new_status == "suspended":
            # Check if customer has outstanding invoices
            # This would require additional context or database query
            pass

        return ValidationResult(
            is_valid=True,
            severity=ValidationSeverity.INFO,
            rule_name="valid_status_transition",
            message=f"Status transition from {old_status} to {new_status} is allowed",
        )


class ServiceBusinessRules(BaseBusinessRuleValidator):
    """Business rules for service management."""

    def validate(
        self, service: Any, context: Dict[str, Any] = None
    ) -> List[ValidationResult]:
        """Validate service business rules."""
        results = []

        # Rule: Service provisioning requirements
        results.append(self._validate_provisioning_requirements(service))

        # Rule: Service compatibility
        results.append(self._validate_service_compatibility(service, context))

        # Rule: Billing configuration
        results.append(self._validate_billing_configuration(service))

        return [r for r in results if r is not None]

    def _validate_provisioning_requirements(
        self, service
    ) -> Optional[ValidationResult]:
        """Validate service provisioning requirements."""
        # Check if required provisioning data is present
        required_fields = ["service_type", "customer_id", "billing_cycle"]
        missing_fields = []

        for field in required_fields:
            if not getattr(service, field, None):
                missing_fields.append(field)

        if missing_fields:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                rule_name="service_provisioning_requirements",
                message=f"Missing required fields for service provisioning: {', '.join(missing_fields)}",
                suggested_action="Complete service configuration before activation",
            )

        return ValidationResult(
            is_valid=True,
            severity=ValidationSeverity.INFO,
            rule_name="service_provisioning_requirements",
            message="Service provisioning requirements satisfied",
        )

    def _validate_service_compatibility(
        self, service, context: Dict[str, Any] = None
    ) -> Optional[ValidationResult]:
        """Validate service compatibility with customer profile and existing services."""
        # This would check against customer's existing services, location, etc.
        # For now, basic validation

        service_type = getattr(service, "service_type", "")

        # Check for conflicting service types (example business rule)
        conflicting_types = {
            "residential_internet": ["business_internet", "enterprise_internet"],
            "business_internet": ["residential_internet"],
            "enterprise_internet": ["residential_internet"],
        }

        conflicts = conflicting_types.get(service_type, [])
        if conflicts and context and context.get("existing_services"):
            existing_types = [s.service_type for s in context["existing_services"]]
            found_conflicts = [t for t in conflicts if t in existing_types]

            if found_conflicts:
                return ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.ERROR,
                    rule_name="service_type_conflict",
                    message=f"Service type {service_type} conflicts with existing services: {', '.join(found_conflicts)}",
                    suggested_action="Remove conflicting services or choose compatible service type",
                )

        return ValidationResult(
            is_valid=True,
            severity=ValidationSeverity.INFO,
            rule_name="service_compatibility",
            message="Service is compatible with customer profile",
        )

    def _validate_billing_configuration(self, service) -> Optional[ValidationResult]:
        """Validate billing configuration for service."""
        billing_cycle = getattr(service, "billing_cycle", None)
        monthly_price = getattr(service, "monthly_price", None)

        if not billing_cycle:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                rule_name="billing_cycle_required",
                message="Billing cycle is required for service activation",
                field_name="billing_cycle",
            )

        valid_cycles = ["monthly", "quarterly", "annually"]
        if billing_cycle not in valid_cycles:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                rule_name="invalid_billing_cycle",
                message=f"Invalid billing cycle. Must be one of: {', '.join(valid_cycles)}",
                field_name="billing_cycle",
            )

        if monthly_price is not None:
            try:
                price = Decimal(str(monthly_price))
                if price < 0:
                    return ValidationResult(
                        is_valid=False,
                        severity=ValidationSeverity.ERROR,
                        rule_name="negative_price",
                        message="Service price cannot be negative",
                        field_name="monthly_price",
                    )
            except (TypeError, ValueError, InvalidOperation) as e:
                return ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.ERROR,
                    rule_name="invalid_price_format",
                    message="Service price must be a valid decimal number",
                    field_name="monthly_price",
                )

        return ValidationResult(
            is_valid=True,
            severity=ValidationSeverity.INFO,
            rule_name="billing_configuration_valid",
            message="Billing configuration is valid",
        )


class BusinessRuleEngine:
    """Central engine for managing and executing business rules."""

    def __init__(self):
        self.rules: Dict[str, BusinessRule] = {}
        self.validators: Dict[str, BaseBusinessRuleValidator] = {}
        self.rule_violations: List[ValidationResult] = []

        # Register default validators
        self._register_default_validators()

    def _register_default_validators(self):
        """Register default business rule validators."""
        self.validators["customer"] = CustomerBusinessRules()
        self.validators["service"] = ServiceBusinessRules()

    def register_rule(self, rule: BusinessRule):
        """Register a new business rule."""
        self.rules[rule.name] = rule
        logger.info(f"📋 Business rule registered: {rule.name}")

    def register_validator(
        self, entity_type: str, validator: BaseBusinessRuleValidator
    ):
        """Register a custom validator for an entity type."""
        self.validators[entity_type] = validator
        logger.info(f"📋 Validator registered for entity type: {entity_type}")

    def validate_entity(
        self, entity_type: str, entity: Any, context: Dict[str, Any] = None
    ) -> List[ValidationResult]:
        """Validate an entity against all applicable business rules."""
        validator = self.validators.get(entity_type)
        if not validator:
            logger.warning(f"No validator found for entity type: {entity_type}")
            return []

        try:
            results = validator.validate(entity, context)

            # Log violations
            violations = [r for r in results if not r.is_valid]
            if violations:
                self.rule_violations.extend(violations)
                logger.warning(
                    f"Business rule violations found for {entity_type}: {len(violations)}"
                )
                for violation in violations:
                    logger.warning(f"  - {violation.rule_name}: {violation.message}")

            return results

        except Exception as e:
            logger.error(f"Error validating {entity_type}: {e}")
            return [
                ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.CRITICAL,
                    rule_name="validation_error",
                    message=f"Validation failed: {str(e)}",
                )
            ]

    def validate_before_save(
        self, entity_type: str, entity: Any, context: Dict[str, Any] = None
    ) -> bool:
        """Validate entity before database save operation."""
        results = self.validate_entity(entity_type, entity, context)

        # Check for blocking errors
        blocking_errors = [
            r
            for r in results
            if not r.is_valid
            and r.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]
        ]

        if blocking_errors:
            error_messages = [f"{r.rule_name}: {r.message}" for r in blocking_errors]
            raise BusinessRuleViolationError(
                f"Cannot save {entity_type} due to business rule violations: {'; '.join(error_messages)}"
            )

        return True

    def get_rule_violations(
        self, severity: ValidationSeverity = None
    ) -> List[ValidationResult]:
        """Get recorded rule violations, optionally filtered by severity."""
        if severity:
            return [v for v in self.rule_violations if v.severity == severity]
        return self.rule_violations.copy()

    def clear_violations(self):
        """Clear recorded rule violations."""
        self.rule_violations.clear()


class BusinessRuleViolationError(Exception):
    """Exception raised when business rules are violated."""

    pass


# Database constraint functions
def create_database_constraints():
    """Create database-level constraints for business rules."""
    with engine.connect() as conn:
        with conn.begin():

            # Customer constraints
            conn.execute(
                text(
                    """
                -- Customer number must follow pattern CUS-XXXXXX
                ALTER TABLE customers 
                ADD CONSTRAINT IF NOT EXISTS customer_number_format_check 
                CHECK (customer_number ~ '^CUS-[0-9]{6}$');
            """
                )
            )

            conn.execute(
                text(
                    """
                -- Credit limit must be non-negative
                ALTER TABLE customers 
                ADD CONSTRAINT IF NOT EXISTS credit_limit_positive_check 
                CHECK (credit_limit::decimal >= 0);
            """
                )
            )

            conn.execute(
                text(
                    """
                -- Account status must be valid
                ALTER TABLE customers 
                ADD CONSTRAINT IF NOT EXISTS account_status_check 
                CHECK (account_status IN ('pending', 'active', 'suspended', 'cancelled'));
            """
                )
            )

            conn.execute(
                text(
                    """
                -- Customer type must be valid
                ALTER TABLE customers 
                ADD CONSTRAINT IF NOT EXISTS customer_type_check 
                CHECK (customer_type IN ('residential', 'business', 'enterprise'));
            """
                )
            )

            conn.execute(
                text(
                    """
                -- Email format validation
                ALTER TABLE customers 
                ADD CONSTRAINT IF NOT EXISTS email_format_check 
                CHECK (email IS NULL OR email ~ '^[^@]+@[^@]+\\.[^@]+$');
            """
                )
            )

            # User constraints
            conn.execute(
                text(
                    """
                -- Username format (alphanumeric, underscore, hyphen)
                ALTER TABLE users 
                ADD CONSTRAINT IF NOT EXISTS username_format_check 
                CHECK (username ~ '^[a-zA-Z0-9_-]+$');
            """
                )
            )

            conn.execute(
                text(
                    """
                -- Failed login attempts must be numeric
                ALTER TABLE users 
                ADD CONSTRAINT IF NOT EXISTS failed_attempts_numeric_check 
                CHECK (failed_login_attempts ~ '^[0-9]+$');
            """
                )
            )

            # Service constraints (if services table exists)
            try:
                conn.execute(
                    text(
                        """
                    -- Service billing cycle validation
                    ALTER TABLE services 
                    ADD CONSTRAINT IF NOT EXISTS billing_cycle_check 
                    CHECK (billing_cycle IN ('monthly', 'quarterly', 'annually'));
                """
                    )
                )

                conn.execute(
                    text(
                        """
                    -- Service price must be non-negative
                    ALTER TABLE services 
                    ADD CONSTRAINT IF NOT EXISTS price_positive_check 
                    CHECK (monthly_price IS NULL OR monthly_price::decimal >= 0);
                """
                    )
                )
            except:
                # Services table might not exist yet
                pass

            logger.info("🔒 Database constraints created successfully")


# Global business rule engine instance
business_rule_engine = BusinessRuleEngine()


def validate_business_rules(
    entity_type: str, entity: Any, context: Dict[str, Any] = None
) -> List[ValidationResult]:
    """Convenience function for validating business rules."""
    return business_rule_engine.validate_entity(entity_type, entity, context)


def initialize_business_rules():
    """Initialize business rules and database constraints."""
    try:
        # Create database constraints
        create_database_constraints()

        # Register custom business rules here
        # Example custom rules would be registered here

        logger.info("📋 Business rules initialized successfully")

    except Exception as e:
        logger.error(f"❌ Business rules initialization failed: {e}")
        raise
