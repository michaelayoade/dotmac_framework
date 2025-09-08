"""
Workflow Templates System - Reusable workflow configurations and patterns.

This system provides template-based workflow creation, configuration management,
and reusable patterns for common business processes.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Type, Union
from uuid import UUID

from pydantic import BaseModel, Field, validator

from .base import BusinessWorkflow, BusinessWorkflowResult


class TemplateCategory(str, Enum):
    """Categories of workflow templates."""
    
    CUSTOMER_MANAGEMENT = "customer_management"
    BILLING_AND_FINANCE = "billing_and_finance"
    SERVICE_OPERATIONS = "service_operations"
    COMPLIANCE_AND_AUDIT = "compliance_and_audit"
    MARKETING_AND_SALES = "marketing_and_sales"
    SUPPORT_AND_MAINTENANCE = "support_and_maintenance"


class TemplateComplexity(str, Enum):
    """Complexity levels of workflow templates."""
    
    SIMPLE = "simple"          # Single workflow, minimal configuration
    MODERATE = "moderate"      # Multiple steps, moderate configuration
    COMPLEX = "complex"        # Multiple workflows, extensive configuration
    ENTERPRISE = "enterprise"  # Full process automation, advanced features


class ConfigurationType(str, Enum):
    """Types of template configuration parameters."""
    
    STRING = "string"
    INTEGER = "integer"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    ENUM = "enum"
    LIST = "list"
    OBJECT = "object"
    REFERENCE = "reference"  # Reference to another entity


class ConfigurationParameter(BaseModel):
    """Definition of a configurable parameter in a template."""
    
    name: str = Field(..., description="Parameter name")
    display_name: str = Field(..., description="Human-readable parameter name")
    description: str = Field(..., description="Parameter description")
    type: ConfigurationType = Field(..., description="Parameter data type")
    required: bool = Field(True, description="Whether parameter is required")
    default_value: Optional[Any] = Field(None, description="Default value")
    validation_rules: Dict[str, Any] = Field(default_factory=dict, description="Validation rules")
    enum_values: Optional[List[str]] = Field(None, description="Allowed values for enum type")
    depends_on: Optional[str] = Field(None, description="Parameter this depends on")
    category: str = Field("general", description="Parameter category for grouping")
    order: int = Field(0, description="Display order")
    
    @validator('enum_values')
    def validate_enum_values(cls, v, values):
        if values.get('type') == ConfigurationType.ENUM and not v:
            raise ValueError("enum_values required for ENUM type parameters")
        return v


class WorkflowTemplate(BaseModel):
    """Definition of a reusable workflow template."""
    
    template_id: str = Field(..., description="Unique template identifier")
    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    category: TemplateCategory = Field(..., description="Template category")
    complexity: TemplateComplexity = Field(..., description="Template complexity level")
    version: str = Field("1.0", description="Template version")
    author: str = Field(..., description="Template author")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Template definition
    workflow_class: str = Field(..., description="Base workflow class")
    default_steps: List[str] = Field(..., description="Default workflow steps")
    configuration_parameters: List[ConfigurationParameter] = Field(
        default_factory=list, description="Configurable parameters"
    )
    
    # Template metadata
    tags: List[str] = Field(default_factory=list, description="Template tags")
    use_cases: List[str] = Field(default_factory=list, description="Common use cases")
    prerequisites: List[str] = Field(default_factory=list, description="Prerequisites")
    estimated_duration: Optional[str] = Field(None, description="Estimated execution time")
    success_rate: Optional[float] = Field(None, description="Historical success rate")
    
    # Advanced features
    conditional_steps: Dict[str, Any] = Field(default_factory=dict, description="Conditional step logic")
    approval_gates: List[str] = Field(default_factory=list, description="Steps requiring approval")
    rollback_strategy: Dict[str, Any] = Field(default_factory=dict, description="Rollback configuration")
    monitoring_config: Dict[str, Any] = Field(default_factory=dict, description="Monitoring configuration")
    
    # Integration points
    external_integrations: List[str] = Field(default_factory=list, description="Required external integrations")
    data_dependencies: List[str] = Field(default_factory=list, description="Required data sources")
    notification_points: List[str] = Field(default_factory=list, description="Notification trigger points")


class TemplateConfiguration(BaseModel):
    """User configuration for a workflow template."""
    
    template_id: str = Field(..., description="Template identifier")
    configuration_name: str = Field(..., description="Configuration name")
    parameters: Dict[str, Any] = Field(..., description="Parameter values")
    tenant_id: Optional[str] = Field(None, description="Tenant identifier")
    user_id: Optional[str] = Field(None, description="User identifier")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Configuration metadata
    description: Optional[str] = Field(None, description="Configuration description")
    tags: List[str] = Field(default_factory=list, description="Configuration tags")
    is_default: bool = Field(False, description="Whether this is the default configuration")
    is_active: bool = Field(True, description="Whether configuration is active")


class TemplateValidationResult(BaseModel):
    """Result of template configuration validation."""
    
    is_valid: bool = Field(..., description="Whether configuration is valid")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    missing_parameters: List[str] = Field(default_factory=list, description="Missing required parameters")
    invalid_parameters: Dict[str, str] = Field(default_factory=dict, description="Invalid parameter values")


class WorkflowTemplateEngine:
    """Engine for managing and instantiating workflow templates."""
    
    def __init__(self):
        self.templates: Dict[str, WorkflowTemplate] = {}
        self.configurations: Dict[str, List[TemplateConfiguration]] = {}
        self.workflow_classes: Dict[str, Type[BusinessWorkflow]] = {}
    
    def register_template(self, template: WorkflowTemplate) -> None:
        """Register a new workflow template."""
        self.templates[template.template_id] = template
        if template.template_id not in self.configurations:
            self.configurations[template.template_id] = []
    
    def register_workflow_class(self, class_name: str, workflow_class: Type[BusinessWorkflow]) -> None:
        """Register a workflow class for template instantiation."""
        self.workflow_classes[class_name] = workflow_class
    
    def get_template(self, template_id: str) -> Optional[WorkflowTemplate]:
        """Get a template by ID."""
        return self.templates.get(template_id)
    
    def list_templates(
        self, 
        category: Optional[TemplateCategory] = None,
        complexity: Optional[TemplateComplexity] = None,
        tags: Optional[List[str]] = None
    ) -> List[WorkflowTemplate]:
        """List templates with optional filtering."""
        templates = list(self.templates.values())
        
        if category:
            templates = [t for t in templates if t.category == category]
        
        if complexity:
            templates = [t for t in templates if t.complexity == complexity]
        
        if tags:
            templates = [t for t in templates if any(tag in t.tags for tag in tags)]
        
        return templates
    
    def validate_configuration(
        self, template_id: str, parameters: Dict[str, Any]
    ) -> TemplateValidationResult:
        """Validate a configuration against a template."""
        template = self.templates.get(template_id)
        if not template:
            return TemplateValidationResult(
                is_valid=False,
                errors=[f"Template {template_id} not found"]
            )
        
        result = TemplateValidationResult(is_valid=True)
        
        # Check required parameters
        for param in template.configuration_parameters:
            if param.required and param.name not in parameters:
                result.missing_parameters.append(param.name)
                result.is_valid = False
        
        # Validate parameter types and values
        for param in template.configuration_parameters:
            if param.name in parameters:
                value = parameters[param.name]
                validation_error = self._validate_parameter_value(param, value)
                if validation_error:
                    result.invalid_parameters[param.name] = validation_error
                    result.is_valid = False
        
        # Check dependencies
        for param in template.configuration_parameters:
            if param.depends_on and param.depends_on not in parameters:
                result.warnings.append(
                    f"Parameter {param.name} depends on {param.depends_on} which is not provided"
                )
        
        return result
    
    def _validate_parameter_value(self, param: ConfigurationParameter, value: Any) -> Optional[str]:
        """Validate a single parameter value."""
        try:
            # Type validation
            if param.type == ConfigurationType.STRING and not isinstance(value, str):
                return f"Expected string, got {type(value).__name__}"
            elif param.type == ConfigurationType.INTEGER and not isinstance(value, int):
                return f"Expected integer, got {type(value).__name__}"
            elif param.type == ConfigurationType.BOOLEAN and not isinstance(value, bool):
                return f"Expected boolean, got {type(value).__name__}"
            elif param.type == ConfigurationType.LIST and not isinstance(value, list):
                return f"Expected list, got {type(value).__name__}"
            elif param.type == ConfigurationType.OBJECT and not isinstance(value, dict):
                return f"Expected object, got {type(value).__name__}"
            
            # Enum validation
            if param.type == ConfigurationType.ENUM:
                if param.enum_values and value not in param.enum_values:
                    return f"Value must be one of: {', '.join(param.enum_values)}"
            
            # Validation rules
            if param.validation_rules:
                error = self._apply_validation_rules(param.validation_rules, value)
                if error:
                    return error
            
            return None
            
        except Exception as e:
            return f"Validation error: {str(e)}"
    
    def _apply_validation_rules(self, rules: Dict[str, Any], value: Any) -> Optional[str]:
        """Apply validation rules to a value."""
        try:
            # String length validation
            if 'min_length' in rules and len(str(value)) < rules['min_length']:
                return f"Minimum length is {rules['min_length']}"
            if 'max_length' in rules and len(str(value)) > rules['max_length']:
                return f"Maximum length is {rules['max_length']}"
            
            # Numeric range validation
            if 'min_value' in rules and value < rules['min_value']:
                return f"Minimum value is {rules['min_value']}"
            if 'max_value' in rules and value > rules['max_value']:
                return f"Maximum value is {rules['max_value']}"
            
            # Pattern validation
            if 'pattern' in rules:
                import re
                if not re.match(rules['pattern'], str(value)):
                    return f"Value does not match required pattern"
            
            return None
            
        except Exception as e:
            return f"Validation rule error: {str(e)}"
    
    def save_configuration(self, config: TemplateConfiguration) -> bool:
        """Save a template configuration."""
        if config.template_id not in self.templates:
            return False
        
        # Validate configuration
        validation = self.validate_configuration(config.template_id, config.parameters)
        if not validation.is_valid:
            return False
        
        # Save configuration
        if config.template_id not in self.configurations:
            self.configurations[config.template_id] = []
        
        self.configurations[config.template_id].append(config)
        return True
    
    def get_configurations(self, template_id: str) -> List[TemplateConfiguration]:
        """Get all configurations for a template."""
        return self.configurations.get(template_id, [])
    
    def instantiate_workflow(
        self, 
        template_id: str, 
        configuration: Union[TemplateConfiguration, Dict[str, Any]],
        **kwargs
    ) -> Optional[BusinessWorkflow]:
        """Instantiate a workflow from a template and configuration."""
        template = self.templates.get(template_id)
        if not template:
            return None
        
        workflow_class = self.workflow_classes.get(template.workflow_class)
        if not workflow_class:
            return None
        
        # Prepare parameters
        if isinstance(configuration, TemplateConfiguration):
            parameters = configuration.parameters
        else:
            parameters = configuration
        
        # Validate configuration
        validation = self.validate_configuration(template_id, parameters)
        if not validation.is_valid:
            return None
        
        # Merge template defaults with configuration
        final_parameters = self._merge_parameters(template, parameters)
        
        # Add additional kwargs
        final_parameters.update(kwargs)
        
        try:
            # Instantiate workflow
            workflow = workflow_class(**final_parameters)
            
            # Apply template customizations
            if template.conditional_steps:
                workflow.conditional_steps = template.conditional_steps
            
            if template.approval_gates:
                workflow.approval_gates = set(template.approval_gates)
            
            if template.rollback_strategy:
                workflow.rollback_strategy = template.rollback_strategy
            
            return workflow
            
        except Exception:
            return None
    
    def _merge_parameters(self, template: WorkflowTemplate, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Merge template defaults with user configuration."""
        final_parameters = {}
        
        # Start with template defaults
        for param in template.configuration_parameters:
            if param.default_value is not None:
                final_parameters[param.name] = param.default_value
        
        # Override with user configuration
        final_parameters.update(parameters)
        
        return final_parameters
    
    def export_template(self, template_id: str) -> Optional[str]:
        """Export a template to JSON format."""
        template = self.templates.get(template_id)
        if not template:
            return None
        
        return template.json(indent=2)
    
    def import_template(self, template_json: str) -> bool:
        """Import a template from JSON format."""
        try:
            template_data = json.loads(template_json)
            template = WorkflowTemplate(**template_data)
            self.register_template(template)
            return True
        except Exception:
            return False


class BuiltinTemplates:
    """Built-in workflow templates for common use cases."""
    
    @staticmethod
    def customer_onboarding_simple() -> WorkflowTemplate:
        """Simple customer onboarding template."""
        return WorkflowTemplate(
            template_id="customer_onboarding_simple",
            name="Simple Customer Onboarding",
            description="Basic customer onboarding with essential verification steps",
            category=TemplateCategory.CUSTOMER_MANAGEMENT,
            complexity=TemplateComplexity.SIMPLE,
            author="DotMac Framework",
            workflow_class="CustomerOnboardingWorkflow",
            default_steps=[
                "validate_customer_info",
                "verify_identity",
                "create_account",
                "send_welcome_notification"
            ],
            configuration_parameters=[
                ConfigurationParameter(
                    name="customer_type",
                    display_name="Customer Type",
                    description="Type of customer being onboarded",
                    type=ConfigurationType.ENUM,
                    required=True,
                    enum_values=["residential", "business", "enterprise"],
                    category="customer",
                    order=1
                ),
                ConfigurationParameter(
                    name="require_identity_verification",
                    display_name="Require Identity Verification",
                    description="Whether to require identity verification",
                    type=ConfigurationType.BOOLEAN,
                    required=False,
                    default_value=True,
                    category="security",
                    order=2
                ),
                ConfigurationParameter(
                    name="welcome_email_template",
                    display_name="Welcome Email Template",
                    description="Template for welcome email",
                    type=ConfigurationType.STRING,
                    required=False,
                    default_value="default_welcome",
                    category="communication",
                    order=3
                )
            ],
            tags=["customer", "onboarding", "simple"],
            use_cases=[
                "Basic customer registration",
                "Self-service account creation",
                "Partner referral onboarding"
            ],
            estimated_duration="5-10 minutes",
            approval_gates=["verify_identity"]
        )
    
    @staticmethod
    def payment_processing_standard() -> WorkflowTemplate:
        """Standard payment processing template."""
        return WorkflowTemplate(
            template_id="payment_processing_standard",
            name="Standard Payment Processing",
            description="Standard payment processing with fraud detection and notifications",
            category=TemplateCategory.BILLING_AND_FINANCE,
            complexity=TemplateComplexity.MODERATE,
            author="DotMac Framework",
            workflow_class="PaymentProcessingWorkflow",
            default_steps=[
                "validate_payment_request",
                "perform_fraud_detection",
                "authorize_payment",
                "capture_payment",
                "process_settlement",
                "send_notifications"
            ],
            configuration_parameters=[
                ConfigurationParameter(
                    name="payment_method",
                    display_name="Payment Method",
                    description="Accepted payment method",
                    type=ConfigurationType.ENUM,
                    required=True,
                    enum_values=["credit_card", "bank_transfer", "digital_wallet"],
                    category="payment",
                    order=1
                ),
                ConfigurationParameter(
                    name="fraud_detection_enabled",
                    display_name="Enable Fraud Detection",
                    description="Enable fraud detection checks",
                    type=ConfigurationType.BOOLEAN,
                    required=False,
                    default_value=True,
                    category="security",
                    order=2
                ),
                ConfigurationParameter(
                    name="capture_immediately",
                    display_name="Capture Immediately",
                    description="Capture payment immediately after authorization",
                    type=ConfigurationType.BOOLEAN,
                    required=False,
                    default_value=True,
                    category="payment",
                    order=3
                ),
                ConfigurationParameter(
                    name="notification_email",
                    display_name="Notification Email",
                    description="Email for payment notifications",
                    type=ConfigurationType.STRING,
                    required=False,
                    validation_rules={"pattern": r"^[^@]+@[^@]+\.[^@]+$"},
                    category="communication",
                    order=4
                )
            ],
            tags=["payment", "billing", "standard"],
            use_cases=[
                "Invoice payment processing",
                "Subscription billing",
                "One-time payments"
            ],
            estimated_duration="2-5 minutes",
            approval_gates=["authorize_payment"]
        )
    
    @staticmethod
    def service_provisioning_enterprise() -> WorkflowTemplate:
        """Enterprise service provisioning template."""
        return WorkflowTemplate(
            template_id="service_provisioning_enterprise",
            name="Enterprise Service Provisioning",
            description="Comprehensive service provisioning for enterprise customers",
            category=TemplateCategory.SERVICE_OPERATIONS,
            complexity=TemplateComplexity.ENTERPRISE,
            author="DotMac Framework",
            workflow_class="ServiceProvisioningWorkflow",
            default_steps=[
                "validate_service_request",
                "check_technical_feasibility",
                "schedule_installation",
                "allocate_resources",
                "configure_infrastructure",
                "deploy_service_config",
                "perform_service_testing",
                "activate_service",
                "update_billing_system",
                "send_notifications",
                "complete_documentation"
            ],
            configuration_parameters=[
                ConfigurationParameter(
                    name="service_type",
                    display_name="Service Type",
                    description="Type of service to provision",
                    type=ConfigurationType.ENUM,
                    required=True,
                    enum_values=["internet", "voice", "iptv", "managed_wifi", "security", "business_grade"],
                    category="service",
                    order=1
                ),
                ConfigurationParameter(
                    name="bandwidth_down",
                    display_name="Download Bandwidth",
                    description="Download bandwidth specification",
                    type=ConfigurationType.STRING,
                    required=True,
                    validation_rules={"pattern": r"^\d+\s?(Mbps|Gbps)$"},
                    category="technical",
                    order=2
                ),
                ConfigurationParameter(
                    name="bandwidth_up",
                    display_name="Upload Bandwidth",
                    description="Upload bandwidth specification",
                    type=ConfigurationType.STRING,
                    required=True,
                    validation_rules={"pattern": r"^\d+\s?(Mbps|Gbps)$"},
                    category="technical",
                    order=3
                ),
                ConfigurationParameter(
                    name="sla_level",
                    display_name="SLA Level",
                    description="Service Level Agreement level",
                    type=ConfigurationType.ENUM,
                    required=True,
                    enum_values=["standard", "premium", "enterprise"],
                    category="service",
                    order=4
                ),
                ConfigurationParameter(
                    name="installation_priority",
                    display_name="Installation Priority",
                    description="Priority level for installation",
                    type=ConfigurationType.ENUM,
                    required=False,
                    default_value="normal",
                    enum_values=["low", "normal", "high", "urgent"],
                    category="operations",
                    order=5
                )
            ],
            tags=["service", "provisioning", "enterprise"],
            use_cases=[
                "Enterprise internet service provisioning",
                "Managed service deployment",
                "Business-grade service activation"
            ],
            estimated_duration="2-4 hours",
            approval_gates=["check_technical_feasibility", "perform_service_testing"],
            external_integrations=["network_management", "field_operations", "billing_system"],
            notification_points=["service_activated", "installation_scheduled", "testing_completed"]
        )


# Global template engine instance
template_engine = WorkflowTemplateEngine()

# Register built-in templates
def register_builtin_templates():
    """Register all built-in templates."""
    templates = [
        BuiltinTemplates.customer_onboarding_simple(),
        BuiltinTemplates.payment_processing_standard(),
        BuiltinTemplates.service_provisioning_enterprise()
    ]
    
    for template in templates:
        template_engine.register_template(template)

# Auto-register built-in templates
register_builtin_templates()