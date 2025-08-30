# Module Reference

Auto-generated from source code analysis

## __init__

DotMac Framework - Unified ISP Management Platform
)
This is the main source package containing all shared components and utilities.

*Source: /home/dotmac_framework/src/__init__.py*

## dotmac_isp.__init__

DotMac ISP Framework - Comprehensive modular monolith for Internet Service Provider management.

This package provides a complete ISP management solution including:

- Customer identity and authentication management
- Billing and subscription management
- Service provisioning and lifecycle
- Network infrastructure management
- Sales and CRM capabilities
- Support ticketing and knowledge base
- Reseller partner management
- Analytics and business intelligence
- Inventory and equipment tracking
- Field operations management
- Compliance and regulatory tools
- Notification systems
- Feature licensing management

Architecture: Modular monolith with FastAPI, SQLAlchemy 2.0, and Pydantic v2

*Source: /home/dotmac_framework/src/dotmac_isp/__init__.py*

## dotmac_isp.api.__init__

API package for DotMac ISP Framework.

*Source: /home/dotmac_framework/src/dotmac_isp/api/__init__.py*

## dotmac_isp.api.file_router

File Handling API Router for Frontend Integration.

### Classes

#### ExportRequest

Data export request model.

#### InvoicePDFRequest

Invoice PDF generation request model.

#### FileMetadataResponse

File metadata response model.

*Source: /home/dotmac_framework/src/dotmac_isp/api/file_router.py*

## dotmac_isp.api.routers

API router registration for DotMac ISP Framework.

*Source: /home/dotmac_framework/src/dotmac_isp/api/routers.py*

## dotmac_isp.api.ticketing_router

Ticketing API router for ISP Framework.
Uses the shared dotmac_shared.ticketing package.

*Source: /home/dotmac_framework/src/dotmac_isp/api/ticketing_router.py*

## dotmac_isp.api.websocket_router

WebSocket Router for Real-time Frontend Communication.

*Source: /home/dotmac_framework/src/dotmac_isp/api/websocket_router.py*

## dotmac_isp.app

FastAPI application factory for the DotMac ISP Framework using shared factory.

*Source: /home/dotmac_framework/src/dotmac_isp/app.py*

## dotmac_isp.core.__init__

Core framework components and shared infrastructure.

*Source: /home/dotmac_framework/src/dotmac_isp/core/__init__.py*

## dotmac_isp.core.application

Clean application initialization with optimal performance systems.
Zero legacy code, 100% production-ready integration.

*Source: /home/dotmac_framework/src/dotmac_isp/core/application.py*

## dotmac_isp.core.auth

Centralized authentication utilities for API endpoints.

### Classes

#### CurrentUser

Current authenticated user information.

**Methods:**

- `__init__()`

*Source: /home/dotmac_framework/src/dotmac_isp/core/auth.py*

## dotmac_isp.core.cache_system

Clean, optimal cache system for dotMAC Framework.
Zero legacy code, 100% production-ready implementation.

### Classes

#### CacheStrategy

Cache strategies for different data types.

#### CacheConfig

Cache configuration for different endpoint types.

#### OptimalCacheKeyGenerator

Production-optimal cache key generation with zero collisions.

**Methods:**

- `__init__()`
- `generate_key()`
- `get_cache_config()`

#### SmartCacheMiddleware

Intelligent cache middleware with optimal performance.

**Methods:**

- `__init__()`
- `async dispatch()`
- `async _get_cached_response()`
- `async _cache_response()`
- `get_metrics()`

#### CacheInvalidationManager

Intelligent cache invalidation based on business events.

**Methods:**

- `__init__()`
- `async invalidate_by_event()`
- `async smart_warm_cache()`

*Source: /home/dotmac_framework/src/dotmac_isp/core/cache_system.py*

## dotmac_isp.core.communication_bridge

Strategic Communication Bridge for ISP Framework

Modern communication bridge that connects the ISP Framework with the strategic plugin system.
Provides clean integration without legacy fallback patterns.

### Classes

#### ISPCommunicationBridge

Strategic bridge between ISP Framework and plugin system.

**Methods:**

- `__init__()`
- `async _ensure_strategic_system_ready()`
- `async initialize_bridge()`
- `async send_message()`
- `async send_customer_notification()`
- `async _get_customer_recipient()`
- `async _render_template()`
- `async get_available_channels()`
- `async get_system_status()`

*Source: /home/dotmac_framework/src/dotmac_isp/core/communication_bridge.py*

## dotmac_isp.core.config.handlers.__init__

Configuration handlers using Chain of Responsibility pattern.
Replaces the 22-complexity _perform_reload method.

*Source: /home/dotmac_framework/src/dotmac_isp/core/config/handlers/__init__.py*

## dotmac_isp.core.config.handlers.handler_chain

Configuration handler chain orchestrator.
Coordinates multiple handlers using Chain of Responsibility pattern.

### Classes

#### ConfigurationHandlerChain

Orchestrates configuration file processing through handler chain.

REFACTORED: Replaces 22-complexity _perform_reload method with
focused, single-responsibility handlers.

**Methods:**

- `__init__()`
- `process_configurations()`
- `add_handler()`
- `get_supported_extensions()`
- `validate_configuration_files()`
- `get_chain_info()`
- `reset_chain()`

*Source: /home/dotmac_framework/src/dotmac_isp/core/config/handlers/handler_chain.py*

## dotmac_isp.core.config.handlers.validation_handler

Configuration validation handler.
Validates merged configuration data for consistency and security.

### Classes

#### ValidationHandler

Handler for validating merged configuration data.

**Methods:**

- `can_handle()`
- `handle()`

*Source: /home/dotmac_framework/src/dotmac_isp/core/config/handlers/validation_handler.py*

## dotmac_isp.core.database

Database configuration and session management.

*Source: /home/dotmac_framework/src/dotmac_isp/core/database.py*

## dotmac_isp.core.db_monitoring

Database performance monitoring and slow query detection.

This module provides comprehensive PostgreSQL database monitoring capabilities
including slow query detection, performance metrics collection, and automated
optimization suggestions.

Key Features:
    - Real-time slow query detection using pg_stat_statements
    - Query pattern classification and analysis
    - Tenant-aware monitoring for multi-tenant databases
    - Index suggestion based on query patterns
    - Prometheus metrics integration
    - Automatic alert generation for performance issues

Requirements:
    - PostgreSQL 14+ with pg_stat_statements extension
    - asyncpg for async database operations
    - Prometheus client for metrics export

Example:
    Basic usage with FastAPI::

        from dotmac_isp.core.db_monitoring import DatabaseMonitor

        monitor = DatabaseMonitor(db_pool, config)
        await monitor.start()

        # Get slow queries
        slow_queries = await monitor.get_slow_queries(threshold_ms=1000)

        # Get optimization suggestions
        suggestions = await monitor.get_index_suggestions()

Author: DotMac Engineering Team
Version: 1.0.0
Since: 2024-08-24

### Classes

#### SlowQuery

Represents a slow database query with performance metrics.

This dataclass encapsulates all relevant information about a slow query
including execution statistics, query classification, and tenant context.

Attributes:
    query (str): The SQL query text
    mean_time_ms (float): Average execution time in milliseconds
    calls (int): Number of times the query was executed
    total_time_ms (float): Total execution time across all calls
    min_time_ms (float): Minimum execution time
    max_time_ms (float): Maximum execution time
    stddev_time_ms (float): Standard deviation of execution times
    rows (int): Total number of rows returned/affected
    query_type (str): Type of query (SELECT, INSERT, UPDATE, DELETE, etc.)
    tenant_id (Optional[str]): Tenant identifier if multi-tenant
    table_name (Optional[str]): Primary table accessed by the query
    timestamp (datetime): When this slow query was detected

Example:
    >>> slow_query = SlowQuery(
    ...     query="SELECT * FROM customers WHERE status = $1",
    ...     mean_time_ms=1500.5,
    ...     calls=100,
    ...     total_time_ms=150050.0,
    ...     min_time_ms=800.0,
    ...     max_time_ms=3000.0,
    ...     stddev_time_ms=450.3,
    ...     rows=10000,
    ...     query_type="SELECT",
    ...     tenant_id="tenant_001",
    ...     table_name="customers"
    ... )

#### DatabaseMonitor

Monitor database performance and detect slow queries.

This class provides comprehensive database monitoring capabilities including
slow query detection, performance metrics collection, and optimization
suggestions. It uses PostgreSQL's pg_stat_statements extension for detailed
query statistics.

Attributes:
    db_pool (asyncpg.Pool): Connection pool for database access
    slow_query_threshold_ms (float): Threshold for slow query detection
    monitoring_interval (int): Interval between monitoring cycles in seconds
    alert_thresholds (Dict): Thresholds for various alert conditions

Methods:
    start(): Start the monitoring loop
    stop(): Stop the monitoring loop
    get_slow_queries(): Retrieve current slow queries
    get_metrics(): Get current database metrics
    get_index_suggestions(): Get index optimization suggestions
    analyze_query_patterns(): Analyze query patterns for optimization

Example:
    >>> pool = await asyncpg.create_pool(DATABASE_URL)
    >>> monitor = DatabaseMonitor(pool, {
    ...     'slow_query_threshold_ms': 1000,
    ...     'monitoring_interval': 60
    ... })
    >>> await monitor.start()

**Methods:**

- `__init__()`
- `async start()`
- `async stop()`
- `async _monitoring_loop()`
- `async check_slow_queries()`
- `async update_connection_metrics()`
- `async update_cache_metrics()`
- `async get_slow_queries()`
- `async get_metrics()`

*Source: /home/dotmac_framework/src/dotmac_isp/core/db_monitoring.py*

## dotmac_isp.core.dns_providers.coredns_provider

CoreDNS Provider - Modern Kubernetes-Native DNS
File-based or etcd-backed DNS with simple management

### Classes

#### CoreDNSProvider

CoreDNS provider using hosts plugin or etcd backend

**Methods:**

- `__init__()`
- `async create_tenant_records()`
- `generate_corefile()`

*Source: /home/dotmac_framework/src/dotmac_isp/core/dns_providers/coredns_provider.py*

## dotmac_isp.core.events.__init__

Adapters package for dotmac_core_events.

Provides adapter implementations for different event streaming backends:

- Redis Streams adapter
- Kafka adapter
- In-memory adapter (for testing)
- Database adapter (for outbox pattern)

*Source: /home/dotmac_framework/src/dotmac_isp/core/events/__init__.py*

## dotmac_isp.core.events.base

Base adapter interface for event streaming backends.

Defines the abstract interface that all event adapters must implement:

- Event publishing and consumption
- Topic management
- Consumer group management
- Offset management

### Classes

#### AdapterConfig

Base configuration for event adapters.

#### EventRecord

Event record model for adapter interface.

#### PublishResult

Result of publishing an event.

#### ConsumerRecord

Consumer record with offset information.

#### EventAdapter

Abstract base class for event streaming adapters.

All event adapters must implement this interface to provide
consistent event streaming capabilities across different backends.

**Methods:**

- `__init__()`
- `async connect()`
- `async disconnect()`
- `async publish()`
- `async subscribe()`
- `async commit_offset()`
- `async create_topic()`
- `async delete_topic()`
- `async list_topics()`
- `async get_topic_info()`
- `async list_consumer_groups()`
- `async delete_consumer_group()`
- `async get_consumer_group_info()`
- `async seek_to_beginning()`
- `async seek_to_end()`
- `async seek_to_offset()`
- `async get_latest_offset()`
- `async get_earliest_offset()`
- `async health_check()`

*Source: /home/dotmac_framework/src/dotmac_isp/core/events/base.py*

## dotmac_isp.core.file_handlers

File Handling Utilities for Frontend Integration.

### Classes

#### FileMetadata

File metadata structure.

**Methods:**

- `__post_init__()`

#### PDFGenerator

PDF generation utilities for invoices, reports, and documents.

**Methods:**

- `__init__()`
- `generate_invoice_pdf()`
- `generate_report_pdf()`

#### CSVExporter

CSV export utilities for data export functionality.

**Methods:**

- `export_to_csv()`
- `export_to_excel()`

#### FileUploadManager

File upload management for frontend integration.

**Methods:**

- `__init__()`
- `async upload_file()`
- `async _validate_file()`
- `async delete_file()`
- `get_file_url()`

*Source: /home/dotmac_framework/src/dotmac_isp/core/file_handlers.py*

## dotmac_isp.core.secrets.secrets

### Classes

#### Secrets

Centralized secret management with validation

**Methods:**

- `validate_jwt_secret()`
- `validate_db_password()`
- `validate_redis_password()`
- `get_database_url()`
- `get_redis_url()`

*Source: /home/dotmac_framework/src/dotmac_isp/core/secrets/secrets.py*

## dotmac_isp.core.security.audit

Audit logging for security events.

### Classes

#### AuditEventType

Audit event types.

#### AuditLogger

Audit logger for security events.

**Methods:**

- `__init__()`
- `async log_event()`
- `async _store_to_database()`
- `async log_login()`
- `async log_logout()`
- `async log_permission_denied()`
- `async log_security_violation()`
- `async log_data_access()`

*Source: /home/dotmac_framework/src/dotmac_isp/core/security/audit.py*

## dotmac_isp.core.security.input_sanitizer

Input sanitization utilities.

### Classes

#### InputSanitizer

Input sanitizer for preventing injection attacks.

**Methods:**

- `__init__()`
- `sanitize_string()`
- `sanitize_dict()`
- `sanitize_list()`
- `url_encode()`
- `validate_email()`
- `validate_phone()`

*Source: /home/dotmac_framework/src/dotmac_isp/core/security/input_sanitizer.py*

## dotmac_isp.core.security.rate_limiting

Rate limiting implementation.

### Classes

#### RateLimiter

Rate limiter for API endpoints.

**Methods:**

- `__init__()`
- `async check_rate_limit()`
- `get_remaining_requests()`
- `reset_limit()`

*Source: /home/dotmac_framework/src/dotmac_isp/core/security/rate_limiting.py*

## dotmac_isp.core.tenant_cache

Tenant-aware cache service with Redis namespacing.

This module provides tenant-isolated caching to prevent data leakage
between tenants in the container-per-tenant architecture.

### Classes

#### TenantCacheService

Redis cache service with tenant namespace isolation.

**Methods:**

- `__init__()`
- `async connect()`
- `async disconnect()`
- `async get()`
- `async set()`
- `async delete()`
- `async exists()`
- `async hset()`
- `async hget()`
- `async hgetall()`
- `async lpush()`
- `async lrange()`
- `async expire()`
- `async incr()`
- `async get_tenant_keys()`
- `async flush_tenant_cache()`

*Source: /home/dotmac_framework/src/dotmac_isp/core/tenant_cache.py*

## dotmac_isp.core.validation_types

Validation types and enums shared across validation modules.

### Classes

#### ValidationSeverity

Severity levels for validation issues.

#### ValidationCategory

Categories of validation checks.

#### ComplianceFramework

Supported compliance frameworks.

#### ValidationIssue

Represents a validation issue found during configuration validation.

#### ValidationRule

Defines a validation rule for configuration fields.

#### ValidationResult

Result of a configuration validation run.

*Source: /home/dotmac_framework/src/dotmac_isp/core/validation_types.py*

## dotmac_isp.integrations.__init__

Integration modules for external systems and services.

*Source: /home/dotmac_framework/src/dotmac_isp/integrations/__init__.py*

## dotmac_isp.main

Main entry point for the DotMac ISP Framework.

*Source: /home/dotmac_framework/src/dotmac_isp/main.py*

## dotmac_isp.modules.__init__

DotMac ISP Framework modules.

*Source: /home/dotmac_framework/src/dotmac_isp/modules/__init__.py*

## dotmac_isp.modules.analytics.__init__

Analytics module for metrics, reports, dashboards and alerting.

*Source: /home/dotmac_framework/src/dotmac_isp/modules/analytics/__init__.py*

## dotmac_isp.modules.analytics.schemas

Analytics schemas for API requests and responses.

### Classes

#### MetricDataPoint

Schema for metric data points used in analytics and reporting.

#### MetricType

Available metric types for analytics.

#### ReportType

Available report types.

#### AlertSeverity

Alert severity levels.

#### MetricBase

Base metric schema.

#### ServiceAnalyticsResponse

Response schema for service analytics data.

#### ServiceMetricsRequest

Request schema for service metrics.

#### CustomReportRequest

Request schema for custom reports.

#### CustomReportResponse

Response schema for custom reports.

#### RealTimeMetricsResponse

Response schema for real-time metrics.

#### MetricCreate

Schema for creating metrics.

#### MetricUpdate

Schema for updating metrics.

#### MetricResponse

Schema for metric responses.

#### MetricValueBase

Base metric value schema.

#### MetricValueCreate

Schema for creating metric values.

#### MetricValueResponse

Schema for metric value responses.

#### ReportBase

Base report schema.

#### ReportCreate

Schema for creating reports.

#### ReportUpdate

Schema for updating reports.

#### ReportResponse

Schema for report responses.

#### DashboardBase

Base dashboard schema.

#### DashboardCreate

Schema for creating dashboards.

#### DashboardUpdate

Schema for updating dashboards.

#### DashboardResponse

Schema for dashboard responses.

#### WidgetBase

Base widget schema.

#### WidgetCreate

Schema for creating widgets.

#### WidgetUpdate

Schema for updating widgets.

#### WidgetResponse

Schema for widget responses.

#### AlertBase

Base alert schema.

#### AlertCreate

Schema for creating alerts.

#### AlertUpdate

Schema for updating alerts.

#### AlertResponse

Schema for alert responses.

#### DataSourceBase

Base data source schema.

#### DataSourceCreate

Schema for creating data sources.

#### DataSourceUpdate

Schema for updating data sources.

#### DataSourceResponse

Schema for data source responses.

#### AnalyticsOverviewResponse

Schema for analytics overview.

#### MetricAggregationRequest

Schema for metric aggregation requests.

#### MetricAggregationResponse

Schema for metric aggregation responses.

#### ReportExportRequest

Schema for report export requests.

#### ReportExportResponse

Schema for report export responses.

#### DashboardMetricsResponse

Schema for dashboard metrics.

#### AlertTestRequest

Schema for testing alert conditions.

#### AlertTestResponse

Schema for alert test responses.

#### DashboardOverviewResponse

Schema for dashboard overview response.

#### ExecutiveReportResponse

Schema for executive report response.

#### CustomerAnalyticsResponse

Schema for customer analytics response.

#### RevenueAnalyticsResponse

Schema for revenue analytics response.

*Source: /home/dotmac_framework/src/dotmac_isp/modules/analytics/schemas.py*

## dotmac_isp.modules.analytics.shared_analytics_adapter

Adapter to replace ISP analytics module with shared analytics service.
This provides backward compatibility while using the shared service.

### Classes

#### ISPAnalyticsAdapter

Adapter that provides ISP analytics interface using shared analytics service.
Maintains backward compatibility with existing ISP analytics API.

**Methods:**

- `__init__()`
- `async initialize()`
- `async track_event()`
- `async get_metrics()`
- `async create_metric()`
- `async create_report()`
- `async get_dashboard_data()`
- `async health_check()`

*Source: /home/dotmac_framework/src/dotmac_isp/modules/analytics/shared_analytics_adapter.py*

## dotmac_isp.modules.analytics.tasks

Analytics and reporting background tasks.

*Source: /home/dotmac_framework/src/dotmac_isp/modules/analytics/tasks.py*

## dotmac_isp.modules.billing.__init__

Billing module - Invoices, payments, and subscription management.

*Source: /home/dotmac_framework/src/dotmac_isp/modules/billing/__init__.py*

## dotmac_isp.modules.billing.domain.__init__

Billing domain services package.

*Source: /home/dotmac_framework/src/dotmac_isp/modules/billing/domain/__init__.py*

## dotmac_isp.modules.billing.domain.calculation_service

Billing calculation domain service implementation.

### Classes

#### BillingCalculationService

Service layer - exceptions bubble up to router @standard_exception_handler.

**Methods:**

- `__init__()`
- `calculate_tax()`
- `calculate_discount()`
- `calculate_line_item_total()`
- `calculate_invoice_total()`
- `calculate_proration()`
- `calculate_late_fee()`
- `calculate_compound_tax()`
- `calculate_payment_schedule()`
- `validate_calculation_inputs()`

*Source: /home/dotmac_framework/src/dotmac_isp/modules/billing/domain/calculation_service.py*

## dotmac_isp.modules.billing.file_handler

File handling utilities for billing module.

### Classes

#### FileUploadConfig

Configuration for file uploads.

#### FileValidator

Validate uploaded files.

**Methods:**

- `__init__()`
- `async validate_file()`
- `validate_csv_structure()`

#### FileStorageManager

Manage file storage operations.

**Methods:**

- `__init__()`
- `async store_file()`
- `async retrieve_file()`
- `async delete_file()`
- `get_file_info()`

#### BulkImportProcessor

Process bulk import files.

**Methods:**

- `__init__()`
- `async process_invoice_import()`
- `async process_payment_import()`

#### FileUploadService

Main service for handling file uploads.

**Methods:**

- `__init__()`
- `async upload_invoice_attachment()`
- `async upload_payment_receipt()`
- `async upload_bulk_import()`
- `async get_file()`
- `async delete_file()`
- `get_file_info()`

*Source: /home/dotmac_framework/src/dotmac_isp/modules/billing/file_handler.py*

## dotmac_isp.modules.billing.pdf_generator

PDF generation utilities for billing documents.

### Classes

#### InvoicePDFGenerator

Generate PDF documents for invoices.

**Methods:**

- `__init__()`
- `async generate_invoice_pdf()`

#### ReceiptPDFGenerator

Generate PDF receipts for payments.

**Methods:**

- `__init__()`
- `async generate_receipt_pdf()`

#### PDFBatchProcessor

Process multiple PDFs in batch operations.

**Methods:**

- `__init__()`
- `async generate_monthly_invoices()`
- `async generate_payment_receipts()`

*Source: /home/dotmac_framework/src/dotmac_isp/modules/billing/pdf_generator.py*

## dotmac_isp.modules.billing.router

Production-ready Billing API router using mandatory DRY patterns.
All manual router patterns have been eliminated.

*Source: /home/dotmac_framework/src/dotmac_isp/modules/billing/router.py*

## dotmac_isp.modules.billing.schemas

Billing module schemas.

### Classes

#### InvoiceStatus

Invoice status enumeration.

#### PaymentStatus

Payment status enumeration.

#### PaymentMethod

Payment method enumeration.

#### TaxType

Tax type enumeration.

#### LineItemBase

Base line item schema.

#### LineItemCreate

Create line item schema.

#### InvoiceLineItemCreate

Create invoice line item schema.

#### LineItem

Line item schema.

#### InvoiceBase

Base invoice schema.

#### InvoiceCreate

Create invoice schema.

#### InvoiceUpdate

Update invoice schema.

#### Invoice

Invoice schema.

#### InvoiceResponse

Invoice response schema.

#### CreditNoteBase

Base credit note schema.

#### CreditNoteCreate

Create credit note schema.

#### CreditNote

Credit note schema.

#### PaymentBase

Base payment schema.

#### PaymentCreate

Create payment schema.

#### PaymentUpdate

Update payment schema.

#### Payment

Payment schema.

#### PaymentResponse

Payment response schema.

#### ReceiptBase

Base receipt schema.

#### ReceiptCreate

Create receipt schema.

#### Receipt

Receipt schema.

#### TaxRateBase

Base tax rate schema.

#### TaxRateCreate

Create tax rate schema.

#### TaxRate

Tax rate schema.

#### SubscriptionBase

Base subscription schema.

#### SubscriptionCreate

Create subscription schema.

#### SubscriptionUpdate

Update subscription schema.

#### Subscription

Subscription schema.

#### BillingReport

Billing report schema.

#### InvoiceCreateRequest

Schema for creating invoice requests.

#### PaymentRequest

Schema for payment requests.

#### CreditNoteRequest

Schema for credit note requests.

#### BillingRuleRequest

Schema for billing rule requests.

#### InvoiceCalculationResult

Schema for invoice calculation results.

*Source: /home/dotmac_framework/src/dotmac_isp/modules/billing/schemas.py*

## dotmac_isp.modules.billing.services.__init__

Billing services.

*Source: /home/dotmac_framework/src/dotmac_isp/modules/billing/services/__init__.py*

## dotmac_isp.modules.billing.services.billing_service

DEPRECATED: Billing service - use modules/billing/service.py instead.

This file has been consolidated into the main billing service.
Use: from dotmac_isp.modules.billing.service import BillingService

This implementation will be removed in a future version.

### Classes

#### BillingService

DEPRECATED: Use main BillingService instead.

**Methods:**

- `__init__()`
- `async create_invoice()`
- `async process_payment()`
- `async create_subscription()`
- `async get_customer_balance()`

*Source: /home/dotmac_framework/src/dotmac_isp/modules/billing/services/billing_service.py*

## dotmac_isp.modules.billing.services.credit_service

Credit service for managing credits and credit notes.

### Classes

#### CreditService

Service for credit management and credit note operations.

**Methods:**

- `__init__()`
- `async create_credit_note()`
- `async apply_credit_note()`
- `async get_credit_notes_by_customer()`
- `async get_customer_credit_balance()`

*Source: /home/dotmac_framework/src/dotmac_isp/modules/billing/services/credit_service.py*

## dotmac_isp.modules.billing.services.invoice_service

Invoice service for managing invoices.

### Classes

#### InvoiceService

Service for invoice operations.

**Methods:**

- `__init__()`
- `async get_invoice_by_id()`
- `async get_invoices_by_customer()`
- `async mark_invoice_overdue()`
- `async calculate_invoice_totals()`

*Source: /home/dotmac_framework/src/dotmac_isp/modules/billing/services/invoice_service.py*

## dotmac_isp.modules.billing.services.payment_service

Payment service for managing payments.

### Classes

#### PaymentService

Service for payment operations.

**Methods:**

- `__init__()`
- `async get_payment_by_id()`
- `async get_payments_by_invoice()`
- `async update_payment_status()`
- `async process_refund()`

*Source: /home/dotmac_framework/src/dotmac_isp/modules/billing/services/payment_service.py*

## dotmac_isp.modules.billing.services.recurring_billing_service

Recurring billing service for automated billing cycles.

### Classes

#### RecurringBillingService

Service for managing recurring billing operations.

**Methods:**

- `__init__()`
- `async process_recurring_billing()`
- `async _create_invoice_from_subscription()`
- `async _update_next_billing_date()`
- `async create_recurring_invoice()`

*Source: /home/dotmac_framework/src/dotmac_isp/modules/billing/services/recurring_billing_service.py*

## dotmac_isp.modules.billing.services.subscription_service

Subscription service for managing subscriptions.

### Classes

#### SubscriptionService

Service for subscription operations.

**Methods:**

- `__init__()`
- `async get_subscription_by_id()`
- `async get_subscriptions_by_customer()`
- `async cancel_subscription()`
- `async update_subscription_amount()`
- `async get_due_subscriptions()`

*Source: /home/dotmac_framework/src/dotmac_isp/modules/billing/services/subscription_service.py*

## dotmac_isp.modules.billing.services.tax_service

Tax service for calculating taxes on invoices.

### Classes

#### TaxService

Service for tax calculations and management.

**Methods:**

- `__init__()`
- `async calculate_tax()`
- `async get_applicable_tax_rate()`
- `async create_tax_rate()`
- `async get_tax_rates_by_location()`

*Source: /home/dotmac_framework/src/dotmac_isp/modules/billing/services/tax_service.py*

## dotmac_isp.modules.billing.shared_event_adapter

Adapter to replace ISP billing event publisher with shared EventBus.
Maintains backward compatibility while using shared event system.

### Classes

#### SharedBillingEventPublisher

Adapter that provides ISP billing event interface using shared EventBus.
Maintains backward compatibility with existing billing event API.

**Methods:**

- `__init__()`
- `async publish_invoice_created()`
- `async publish_invoice_paid()`
- `async publish_payment_received()`
- `async publish_invoice_updated()`
- `async publish_invoice_overdue()`

*Source: /home/dotmac_framework/src/dotmac_isp/modules/billing/shared_event_adapter.py*

## dotmac_isp.modules.billing.websocket_manager

WebSocket integration for real-time billing events.

### Classes

#### BillingEventType

Billing event types for WebSocket notifications.

#### BillingEvent

Billing event data structure.

**Methods:**

- `to_dict()`

#### WebSocketConnectionManager

Manages WebSocket connections for billing events.

**Methods:**

- `__init__()`
- `async initialize()`
- `async connect()`
- `async disconnect()`
- `async broadcast_event()`
- `async _send_with_retry()`
- `async _send_to_websocket()`
- `async _publish_to_redis()`
- `async subscribe_to_redis_events()`
- `async get_connection_count()`
- `async health_check()`

#### BillingEventPublisher

Service for publishing billing events.

**Methods:**

- `__init__()`
- `async publish_invoice_created()`
- `async publish_invoice_paid()`
- `async publish_payment_failed()`
- `async publish_subscription_cancelled()`

*Source: /home/dotmac_framework/src/dotmac_isp/modules/billing/websocket_manager.py*

## dotmac_isp.modules.captive_portal.__init__

Captive Portal module for WiFi hotspot authentication and session management.

This module provides enterprise-grade captive portal functionality integrated
with the DotMac ISP Framework infrastructure, including existing identity,
billing, and analytics modules.

Features:

- Multi-authentication methods (social, voucher, RADIUS, SMS)
- Session management with usage tracking
- Integration with existing billing and customer systems
- Portal customization and branding
- Analytics and reporting

*Source: /home/dotmac_framework/src/dotmac_isp/modules/captive_portal/__init__.py*

## dotmac_isp.modules.captive_portal.auth_providers.__init__

Authentication providers for captive portal access.

*Source: /home/dotmac_framework/src/dotmac_isp/modules/captive_portal/auth_providers/__init__.py*

## dotmac_isp.modules.captive_portal.auth_providers.base

Base authentication provider interface.

### Classes

#### AuthenticationResult

Result of authentication attempt.

#### BaseAuthProvider

Base class for authentication providers.

**Methods:**

- `__init__()`
- `async authenticate()`
- `async prepare_authentication()`
- `validate_request()`

*Source: /home/dotmac_framework/src/dotmac_isp/modules/captive_portal/auth_providers/base.py*

## dotmac_isp.modules.captive_portal.auth_providers.manager

Authentication manager for coordinating captive portal auth providers.

### Classes

#### AuthenticationManager

Manages multiple authentication providers for captive portal.

**Methods:**

- `__init__()`
- `register_provider()`
- `async authenticate()`
- `async prepare_authentication()`
- `get_available_methods()`
- `async _log_authentication_attempt()`
- `update_provider_config()`
- `get_provider_status()`

*Source: /home/dotmac_framework/src/dotmac_isp/modules/captive_portal/auth_providers/manager.py*

## dotmac_isp.modules.captive_portal.auth_providers.voucher

Voucher authentication provider for captive portal.

### Classes

#### VoucherAuthProvider

Voucher-based authentication provider for prepaid access.

**Methods:**

- `__init__()`
- `async authenticate()`
- `async prepare_authentication()`
- `validate_request()`
- `async _check_device_limits()`
- `async _create_guest_user()`
- `async get_voucher_info()`

*Source: /home/dotmac_framework/src/dotmac_isp/modules/captive_portal/auth_providers/voucher.py*

## dotmac_isp.modules.captive_portal.models

Captive Portal models integrated with DotMac ISP Framework.

### Classes

#### SessionStatus

Captive portal session status.

#### AuthMethodType

Supported authentication methods.

#### PortalStatus

Portal configuration status.

#### VoucherStatus

Voucher status.

#### CaptivePortalConfig

Captive portal configuration linked to customers/locations.

#### CaptivePortalSession

User session for captive portal access - integrates with existing User model.

**Methods:**

- `duration_minutes()`
- `total_bytes()`
- `is_active()`

#### AuthMethod

Authentication method configuration for captive portals.

#### Voucher

Access vouchers for pre-paid captive portal access.

**Methods:**

- `is_expired()`
- `is_valid_for_redemption()`

#### VoucherBatch

Batch management for bulk voucher generation.

**Methods:**

- `is_complete()`

#### PortalCustomization

Portal customization and branding settings.

#### PortalUsageStats

Usage statistics and analytics for captive portals.

*Source: /home/dotmac_framework/src/dotmac_isp/modules/captive_portal/models.py*

## dotmac_isp.modules.captive_portal.router

Captive Portal API router for WiFi hotspot authentication and session management.

*Source: /home/dotmac_framework/src/dotmac_isp/modules/captive_portal/router.py*

## dotmac_isp.modules.captive_portal.schemas

Captive Portal Pydantic schemas for API requests and responses.

### Classes

#### TenantAwareSchema

Base schema for tenant-aware models.

#### CaptivePortalConfigBase

Base captive portal configuration.

#### CaptivePortalConfigCreate

Schema for creating a captive portal configuration.

#### CaptivePortalConfigUpdate

Schema for updating a captive portal configuration.

#### CaptivePortalConfigResponse

Schema for captive portal configuration responses.

#### AuthenticationRequest

Base authentication request.

#### EmailAuthRequest

Email authentication request.

#### SocialAuthRequest

Social media authentication request.

#### VoucherAuthRequest

Voucher authentication request.

#### RadiusAuthRequest

RADIUS authentication request.

#### AuthenticationResponse

Authentication response.

#### SessionResponse

Session information response.

#### SessionTerminateRequest

Request to terminate a session.

#### SessionListResponse

List of sessions response.

#### VoucherBase

Base voucher schema.

#### VoucherCreateRequest

Request to create vouchers.

#### VoucherResponse

Voucher information response.

#### VoucherBatchCreateRequest

Request to create a voucher batch.

#### VoucherBatchResponse

Voucher batch response.

#### PortalCustomizationBase

Base portal customization schema.

#### PortalCustomizationUpdate

Schema for updating portal customization.

#### PortalCustomizationResponse

Portal customization response.

#### UsageStatsRequest

Request for usage statistics.

#### UsageStatsResponse

Usage statistics response.

#### ErrorDetail

Error detail schema.

#### ErrorResponse

API error response.

#### PaginationParams

Pagination parameters.

#### PaginatedResponse

Paginated response wrapper.

**Methods:**

- `create()`

*Source: /home/dotmac_framework/src/dotmac_isp/modules/captive_portal/schemas.py*

## dotmac_isp.modules.identity.__init__

Identity module - Customer, user, and authentication management.

*Source: /home/dotmac_framework/src/dotmac_isp/modules/identity/__init__.py*

## dotmac_isp.modules.identity.domain.__init__

Identity domain services package.

*Source: /home/dotmac_framework/src/dotmac_isp/modules/identity/domain/__init__.py*

## dotmac_isp.modules.identity.domain.interfaces

Service interfaces for identity domain.

### Classes

#### ICustomerService

Interface for customer domain service.

**Methods:**

- `async create_customer()`
- `async get_customer()`
- `async update_customer()`
- `async deactivate_customer()`
- `async search_customers()`
- `async validate_customer_data()`
- `async generate_customer_number()`

#### IUserService

Interface for user domain service.

**Methods:**

- `async create_user()`
- `async get_user()`
- `async get_user_by_email()`
- `async update_user()`
- `async change_password()`
- `async reset_password()`
- `async assign_role()`
- `async remove_role()`

#### IAuthenticationService

Interface for authentication domain service.

**Methods:**

- `async authenticate_user()`
- `async refresh_token()`
- `async logout_user()`
- `async validate_token()`
- `async create_session()`
- `async get_active_sessions()`
- `async revoke_session()`

#### IAuthorizationService

Interface for authorization domain service.

**Methods:**

- `async check_permission()`
- `async get_user_permissions()`
- `async has_role()`
- `async get_user_roles()`
- `async check_resource_access()`

#### IPortalService

Interface for portal management domain service.

**Methods:**

- `async generate_portal_id()`
- `async create_portal_account()`
- `async get_portal_account()`
- `async update_portal_preferences()`
- `async reset_portal_access()`

#### IPasswordService

Interface for password management domain service.

**Methods:**

- `hash_password()`
- `verify_password()`
- `generate_password()`
- `validate_password_strength()`
- `generate_reset_token()`

#### IUserValidationService

Interface for user validation domain service.

**Methods:**

- `async validate_email_format()`
- `async validate_email_uniqueness()`
- `async validate_username_uniqueness()`
- `async validate_phone_format()`
- `async validate_customer_number_uniqueness()`

#### IIdentityEventService

Interface for identity event handling service.

**Methods:**

- `async publish_customer_created()`
- `async publish_user_created()`
- `async publish_user_authenticated()`
- `async publish_password_changed()`
- `async publish_account_deactivated()`

#### IIdentityIntegrationService

Interface for identity integration service.

**Methods:**

- `async sync_with_external_system()`
- `async import_users_from_ldap()`
- `async sync_customer_with_billing()`
- `async notify_crm_customer_change()`

*Source: /home/dotmac_framework/src/dotmac_isp/modules/identity/domain/interfaces.py*

## dotmac_isp.modules.identity.intelligence_service

Lightweight customer intelligence service for portal enhancements.

### Classes

#### CustomerIntelligenceService

Simple customer intelligence for immediate ROI.

**Methods:**

- `__init__()`
- `async get_customer_health_scores()`
- `async get_churn_alerts()`

*Source: /home/dotmac_framework/src/dotmac_isp/modules/identity/intelligence_service.py*

## dotmac_isp.modules.identity.portal_models

Portal Account models for authentication and account management.

### Classes

#### PortalAccountType

Portal account type enumeration.

#### PortalAccountStatus

Portal account status enumeration.

*Source: /home/dotmac_framework/src/dotmac_isp/modules/identity/portal_models.py*

## dotmac_isp.modules.identity.schemas

Identity schemas for API requests and responses.

### Classes

#### UserBase

Base user schema.

#### UserCreate

Schema for creating users.

#### UserUpdate

Schema for updating users.

#### UserResponse

Schema for user responses.

**Methods:**

- `full_name()`

#### RoleBase

Base role schema.

#### RoleCreate

Schema for creating roles.

#### RoleUpdate

Schema for updating roles.

#### RoleResponse

Schema for role responses.

#### CustomerCreateAPI

API schema for creating customers - extends SDK schema with contact/address info.

#### CustomerUpdateAPI

API schema for updating customers - extends SDK schema with contact/address info.

#### CustomerResponseAPI

API schema for customer responses - includes portal_id as primary identifier.

**Methods:**

- `from_sdk_response()`

#### LoginRequest

Schema for login requests.

#### LoginResponse

Schema for login responses.

#### TokenResponse

Schema for token refresh responses.

#### TokenRefreshRequest

Schema for token refresh requests.

#### PasswordChangeRequest

Schema for password change requests.

#### PasswordResetRequest

Schema for password reset requests.

#### PasswordResetConfirm

Schema for password reset confirmation.

#### UserProfileUpdate

Schema for user profile updates.

#### CustomerStateTransition

Schema for customer state transitions.

#### CustomerActivation

Schema for customer activation.

#### CustomerSuspension

Schema for customer suspension.

#### CustomerCancellation

Schema for customer cancellation.

#### CustomerFilters

Schema for customer filtering and search.

#### CustomerListResponse

Schema for paginated customer list responses.

*Source: /home/dotmac_framework/src/dotmac_isp/modules/identity/schemas.py*

## dotmac_isp.modules.identity.services.__init__

Identity domain services.

*Source: /home/dotmac_framework/src/dotmac_isp/modules/identity/services/__init__.py*

## dotmac_isp.modules.identity.services.base_service

Base service for identity domain services.

### Classes

#### BaseIdentityService

Base class for identity domain services.

**Methods:**

- `__init__()`

*Source: /home/dotmac_framework/src/dotmac_isp/modules/identity/services/base_service.py*

## dotmac_isp.modules.identity.services.customer_service

DEPRECATED Customer service module.

This module has been deprecated. Use dotmac_isp.modules.identity.service.CustomerService instead.

### Classes

#### CustomerService

DEPRECATED: Customer service for identity module.

**Methods:**

- `__init__()`
- `async create_customer()`
- `async get_customer()`
- `async update_customer()`
- `async list_customers()`
- `async activate_customer()`
- `async suspend_customer()`

*Source: /home/dotmac_framework/src/dotmac_isp/modules/identity/services/customer_service.py*

## dotmac_isp.modules.identity.services.identity_orchestrator

Identity orchestrator service that coordinates all identity domain services.

### Classes

#### IdentityOrchestrator

Orchestrator service that coordinates all identity domain services.

This maintains the same interface as the original monolithic services
while delegating to focused domain services internally.

**Methods:**

- `__init__()`
- `async create_customer()`
- `async get_customer()`
- `async update_customer()`
- `async list_customers()`
- `async activate_customer()`
- `async suspend_customer()`
- `async create_user()`
- `async get_user()`
- `async get_user_by_username()`
- `async get_user_by_email()`
- `async update_user()`
- `async deactivate_user()`
- `async activate_user()`
- `async verify_user()`
- `async login()`
- `async refresh_token()`
- `async logout()`
- `async verify_token()`
- `async change_password()`
- `async request_password_reset()`
- `async reset_password()`
- `async create_portal_account()`
- `async activate_portal_account()`
- `async get_portal_account()`
- `async authenticate_portal_user()`
- `async assign_user_roles()`
- `async remove_user_roles()`
- `async get_user_roles()`
- `async handle_customer_onboarding()`
- `async handle_user_authentication_flow()`
- `async handle_account_recovery()`

*Source: /home/dotmac_framework/src/dotmac_isp/modules/identity/services/identity_orchestrator.py*

## dotmac_isp.modules.portal_management.models

Portal Management Models - Portal ID system for customer authentication.

### Classes

#### PortalAccountStatus

Portal account status enumeration.

#### PortalAccountType

Portal account type enumeration.

#### PortalAccount

Portal Account model for customer portal authentication.

This is the PRIMARY authentication mechanism for ISP customer portals.
Each customer gets a unique Portal ID that serves as their login credential.

**Methods:**

- `__init__()`
- `is_locked()`
- `is_active()`
- `password_expired()`
- `lock_account()`
- `unlock_account()`
- `record_failed_login()`
- `record_successful_login()`

#### PortalSession

Portal session model for tracking active customer sessions.

**Methods:**

- `is_expired()`
- `is_valid()`
- `duration_minutes()`
- `extend_session()`
- `terminate_session()`

#### PortalLoginAttempt

Portal login attempt tracking for security monitoring.

**Methods:**

- `is_high_risk()`
- `calculate_risk_score()`

#### SessionStatus

Session status enumeration.

#### PortalPreferences

Portal user preferences model.

*Source: /home/dotmac_framework/src/dotmac_isp/modules/portal_management/models.py*

## dotmac_isp.modules.portal_management.schemas

Portal Management Schemas - Pydantic models for Portal ID system.

### Classes

#### PortalAccountBase

Base Portal Account schema.

#### PortalAccountCreate

Schema for creating a new Portal Account.

**Methods:**

- `validate_password_strength()`

#### PortalAccountUpdate

Schema for updating Portal Account.

#### PortalAccountResponse

Schema for Portal Account response.

#### PortalLoginRequest

Schema for portal login request.

#### PortalLoginResponse

Schema for portal login response.

#### PortalPasswordChangeRequest

Schema for portal password change.

**Methods:**

- `validate_password_strength()`

#### PortalPasswordResetRequest

Schema for portal password reset request.

#### PortalPasswordResetConfirm

Schema for portal password reset confirmation.

**Methods:**

- `validate_password_strength()`

#### Portal2FASetupRequest

Schema for 2FA setup request.

#### Portal2FASetupResponse

Schema for 2FA setup response.

#### Portal2FAVerifyRequest

Schema for 2FA verification.

#### PortalSessionResponse

Schema for portal session information.

#### PortalSecurityEventResponse

Schema for portal security events.

#### PortalAccountAdminCreate

Schema for admin creation of Portal Account.

#### PortalAccountAdminUpdate

Schema for admin updates to Portal Account.

#### PortalBulkOperationRequest

Schema for bulk operations on Portal Accounts.

#### PortalBulkOperationResponse

Schema for bulk operation response.

#### PortalAnalyticsResponse

Schema for portal analytics data.

#### PortalPreferencesBase

Base portal preferences schema.

#### PortalPreferencesCreate

Schema for creating portal preferences.

#### PortalPreferencesUpdate

Schema for updating portal preferences.

#### PortalPreferences

Portal preferences response schema.

#### PortalSession

Portal session response schema.

#### PortalAccount

Portal account response schema.

*Source: /home/dotmac_framework/src/dotmac_isp/modules/portal_management/schemas.py*

## dotmac_isp.modules.resellers.__init__

Reseller management module for ISP Framework.

*Source: /home/dotmac_framework/src/dotmac_isp/modules/resellers/__init__.py*

## dotmac_isp.modules.resellers.router

FastAPI router for ISP reseller management.
Provides REST endpoints for reseller operations using shared reseller service.

*Source: /home/dotmac_framework/src/dotmac_isp/modules/resellers/router.py*

## dotmac_isp.modules.resellers.schemas

Pydantic schemas for ISP reseller operations.
These schemas interface with the shared reseller models.

### Classes

#### ResellerTypeEnum

#### ResellerTierEnum

#### CommissionStatusEnum

#### ResellerCreate

Schema for creating a new reseller.

**Methods:**

- `validate_start_date()`
- `validate_end_date()`

#### ResellerUpdate

Schema for updating reseller information.

#### ResellerOpportunityCreate

Schema for assigning an opportunity to a reseller.

#### CommissionCalculation

Schema for commission calculation requests.

#### CommissionRecord

Schema for recording commissions.

#### ResellerResponse

Schema for reseller response.

#### ResellerOpportunityResponse

Schema for reseller opportunity response.

#### CommissionResponse

Schema for commission response.

#### CommissionCalculationResponse

Schema for commission calculation response.

#### ResellerPerformanceResponse

Schema for reseller performance metrics.

#### ResellerListResponse

Schema for paginated reseller list.

#### ResellerHealthResponse

Schema for reseller service health check.

#### Config

#### Config

#### Config

#### Config

#### Config

#### Config

#### Config

#### Config

#### Config

#### Config

#### Config

#### Config

*Source: /home/dotmac_framework/src/dotmac_isp/modules/resellers/schemas.py*

## dotmac_isp.modules.services.__init__

Services module for service provisioning and lifecycle management.

*Source: /home/dotmac_framework/src/dotmac_isp/modules/services/__init__.py*

## dotmac_isp.modules.services.customer_intelligence_service

Customer service intelligence for proactive portal notifications.

### Classes

#### CustomerServiceIntelligenceService

Simple service intelligence for customer portal enhancements.

**Methods:**

- `__init__()`
- `async get_proactive_notifications()`
- `async get_usage_insights()`

*Source: /home/dotmac_framework/src/dotmac_isp/modules/services/customer_intelligence_service.py*

## dotmac_isp.modules.services.schemas

Services schemas for API requests and responses.

### Classes

#### ServiceType

Service type enumeration.

#### ServiceStatus

Service status enumeration.

#### ProvisioningStatus

Provisioning status enumeration.

#### BandwidthUnit

Bandwidth unit enumeration.

#### ServicePlanBase

Base service plan schema.

#### ServicePlanCreate

Schema for creating service plans.

#### ServicePlanUpdate

Schema for updating service plans.

#### ServicePlanResponse

Schema for service plan responses.

#### ServiceInstanceBase

Base service instance schema.

#### ServiceInstanceCreate

Schema for creating service instances.

#### ServiceInstanceUpdate

Schema for updating service instances.

#### ServiceStatusUpdate

Schema for updating service status.

#### ServiceInstanceResponse

Schema for service instance responses.

#### ProvisioningTaskBase

Base provisioning task schema.

#### ProvisioningTaskCreate

Schema for creating provisioning tasks.

#### ProvisioningTaskUpdate

Schema for updating provisioning tasks.

#### ProvisioningTaskStatusUpdate

Schema for updating provisioning task status.

#### ProvisioningTaskResponse

Schema for provisioning task responses.

#### ServiceAddonBase

Base service add-on schema.

#### ServiceAddonCreate

Schema for creating service add-ons.

#### ServiceAddonResponse

Schema for service add-on responses.

#### ServiceUsageBase

Base service usage schema.

#### ServiceUsageCreate

Schema for creating service usage records.

#### ServiceUsageResponse

Schema for service usage responses.

#### ServiceActivationRequest

Schema for service activation requests.

#### ServiceActivationResponse

Schema for service activation responses.

#### ServiceModificationRequest

Schema for service modification requests.

#### ServiceProvisioningRequest

Service provisioning request schema.

#### ServiceDashboard

Service dashboard metrics.

#### ServicePerformanceMetrics

Service performance metrics.

#### BulkServiceOperation

Schema for bulk service operations.

#### BulkServiceOperationResponse

Schema for bulk service operation responses.

*Source: /home/dotmac_framework/src/dotmac_isp/modules/services/schemas.py*

## dotmac_isp.modules.services.tasks

Service provisioning background tasks.

*Source: /home/dotmac_framework/src/dotmac_isp/modules/services/tasks.py*

## dotmac_isp.portals.__init__

Portal interfaces for different user types.

*Source: /home/dotmac_framework/src/dotmac_isp/portals/__init__.py*

## dotmac_isp.portals.admin.__init__

Admin portal - ISP administrator interface for system management.

*Source: /home/dotmac_framework/src/dotmac_isp/portals/admin/__init__.py*

## dotmac_isp.portals.admin.schemas

Admin portal API schemas.

### Classes

#### AdminDashboard

Admin dashboard overview data.

#### CustomerOverview

Customer overview for admin.

#### ServicesOverview

Services overview for admin.

#### FinancialOverview

Financial overview for admin.

#### SupportOverview

Support overview for admin.

#### SystemHealth

System health status.

#### AvailableReports

Available admin reports.

#### ActivityLogEntry

Activity log entry.

#### NetworkMetrics

Network performance metrics.

#### CustomerManagementData

Customer management data for admin.

#### ServiceManagementData

Service management data for admin.

#### BillingManagementData

Billing management data for admin.

*Source: /home/dotmac_framework/src/dotmac_isp/portals/admin/schemas.py*

## dotmac_isp.portals.customer.__init__

Customer portal - End customer self-service interface.

*Source: /home/dotmac_framework/src/dotmac_isp/portals/customer/__init__.py*

## dotmac_isp.portals.customer.schemas

Customer portal API schemas.

### Classes

#### CustomerDashboard

Customer dashboard data.

#### CustomerProfileUpdate

Customer profile update schema.

#### ServiceUsageResponse

Service usage response.

#### PaymentMethodBase

Base payment method schema.

#### PaymentMethodCreate

Create payment method schema.

#### PaymentMethodResponse

Payment method response schema.

#### PaymentRequest

Payment request schema.

#### CustomerServicesList

Customer services list response.

#### CustomerInvoicesList

Customer invoices list response.

#### CustomerTicketsList

Customer tickets list response.

*Source: /home/dotmac_framework/src/dotmac_isp/portals/customer/schemas.py*

## dotmac_isp.portals.reseller.__init__

Reseller portal - ISP reseller partner management interface.

*Source: /home/dotmac_framework/src/dotmac_isp/portals/reseller/__init__.py*

## dotmac_isp.portals.reseller.router

*Source: /home/dotmac_framework/src/dotmac_isp/portals/reseller/router.py*

## dotmac_isp.portals.technician.__init__

Technician portal - Field technician mobile app interface.

*Source: /home/dotmac_framework/src/dotmac_isp/portals/technician/__init__.py*

## dotmac_isp.sdks.analytics.__init__

Analytics SDK package - Individual SDK exports for composable usage.

*Source: /home/dotmac_framework/src/dotmac_isp/sdks/analytics/__init__.py*

## dotmac_isp.sdks.analytics.core

Core analytics SDK module.

### Classes

#### MetricType

Metric type enumeration.

#### MetricData

Metric data schema.

#### AnalyticsCoreSDK

Core analytics SDK for basic analytics operations.

**Methods:**

- `__init__()`
- `async record_metric()`
- `async get_metrics()`

*Source: /home/dotmac_framework/src/dotmac_isp/sdks/analytics/core.py*

## dotmac_isp.sdks.contracts.__init__

SDK contract definitions.

*Source: /home/dotmac_framework/src/dotmac_isp/sdks/contracts/__init__.py*

## dotmac_isp.sdks.contracts.audit

Audit contract definitions.

### Classes

#### AuditEventType

Audit event type enumeration.

#### AuditSeverity

Audit event severity levels.

#### AuditOutcome

Audit event outcomes.

#### AuditEvent

Audit event definition.

**Methods:**

- `__post_init__()`

#### AuditQuery

Audit query filter.

#### AuditQueryResponse

Audit query response.

#### AuditExportRequest

Audit export request.

#### AuditExportResponse

Audit export response.

#### AuditMetrics

Audit metrics response.

#### AuditHealthCheck

Audit system health check response.

**Methods:**

- `__post_init__()`

#### AuditRetentionPolicy

Audit retention policy definition.

**Methods:**

- `__post_init__()`

#### AuditStats

Audit statistics response.

**Methods:**

- `__post_init__()`

*Source: /home/dotmac_framework/src/dotmac_isp/sdks/contracts/audit.py*

## dotmac_isp.sdks.contracts.auth

Authentication contracts and schemas for the DotMac ISP Framework.

### Classes

#### AuthenticationMethod

Authentication method types.

#### TokenType

Token types for authentication.

#### AuthenticationStatus

Authentication status values.

#### AuthRequest

Basic auth request schema.

#### AuthenticationRequest

Authentication request data.

#### AuthenticationResponse

Authentication response data.

#### TokenValidationRequest

Token validation request.

#### TokenValidationResponse

Token validation response.

#### SessionInfo

Session information.

#### PasswordChangeRequest

Password change request.

#### PasswordResetRequest

Password reset request.

#### MFASetupRequest

Multi-factor authentication setup request.

#### MFAVerificationRequest

Multi-factor authentication verification request.

#### AuthenticationLog

Authentication log entry.

#### RolePermission

Role and permission mapping.

#### UserAuthProfile

User authentication profile.

#### AuthResponse

Authentication response (alias for AuthenticationResponse).

#### AuthToken

Authentication token data.

#### LogoutRequest

Logout request data.

#### LogoutResponse

Logout response data.

#### TokenRefreshRequest

Token refresh request.

#### TokenRefreshResponse

Token refresh response.

*Source: /home/dotmac_framework/src/dotmac_isp/sdks/contracts/auth.py*

## dotmac_isp.sdks.contracts.base

Base contract definitions.

### Classes

#### BaseContract

Base contract for SDK operations.

**Methods:**

- `to_dict()`

*Source: /home/dotmac_framework/src/dotmac_isp/sdks/contracts/base.py*

## dotmac_isp.sdks.contracts.common_schemas

Common schema definitions.

### Classes

#### ExecutionStatus

Workflow execution status enumeration.

#### Priority

Task/workflow priority enumeration.

#### APIResponse

Standard API response schema.

#### PaginationInfo

Pagination information.

#### ErrorInfo

Error information schema.

#### ExecutionContext

Workflow execution context.

#### OperationMetadata

Metadata for operations and workflows.

#### RetryPolicy

Retry policy configuration.

**Methods:**

- `__post_init__()`

#### TimeoutPolicy

Timeout policy configuration for operations.

*Source: /home/dotmac_framework/src/dotmac_isp/sdks/contracts/common_schemas.py*

## dotmac_isp.sdks.contracts.rbac

RBAC (Role-Based Access Control) contract definitions.

### Classes

#### PermissionType

Permission type enumeration.

#### ResourceType

Resource type enumeration.

#### UserRole

User role enumeration.

#### PermissionScope

Permission scope enumeration.

#### Permission

Permission definition.

#### Role

Role definition.

#### RoleAssignment

Role assignment definition.

#### AccessRequest

Access request for permission checking.

#### RoleAssignmentRequest

Role assignment request.

#### RoleAssignmentResponse

Role assignment response.

#### RoleHierarchyResponse

Role hierarchy response.

#### AccessResponse

Access response for permission checking.

#### BulkPermissionCheckRequest

Bulk permission check request.

#### BulkPermissionCheckResponse

Bulk permission check response.

#### UserRolesResponse

User roles response.

*Source: /home/dotmac_framework/src/dotmac_isp/sdks/contracts/rbac.py*

## dotmac_isp.sdks.contracts.transport

Transport layer contracts for SDK communication.

### Classes

#### RequestMethod

HTTP request methods.

#### TransportProtocol

Transport protocols.

#### RequestContext

Request context for SDK operations.

**Methods:**

- `__post_init__()`

#### TransportConfig

Transport configuration.

**Methods:**

- `__post_init__()`

#### RequestMessage

Request message structure.

**Methods:**

- `__post_init__()`

#### ResponseMessage

Response message structure.

**Methods:**

- `__post_init__()`
- `is_success()`
- `is_client_error()`
- `is_server_error()`

#### EventMessage

Event message for asynchronous communication.

**Methods:**

- `__post_init__()`

#### BatchRequest

Batch request for multiple operations.

**Methods:**

- `request_count()`

#### BatchResponse

Batch response for multiple operations.

**Methods:**

- `__post_init__()`
- `all_successful()`

#### CircuitBreakerConfig

Circuit breaker configuration.

#### LoadBalancerConfig

Load balancer configuration.

*Source: /home/dotmac_framework/src/dotmac_isp/sdks/contracts/transport.py*

## dotmac_isp.sdks.contracts.workflow

Workflow contract definitions.

### Classes

#### WorkflowStep

Individual workflow step.

#### WorkflowContract

Workflow execution contract.

**Methods:**

- `add_step()`
- `to_dict()`

*Source: /home/dotmac_framework/src/dotmac_isp/sdks/contracts/workflow.py*

## dotmac_isp.sdks.core.config

Core configuration utilities for SDKs.

### Classes

#### SDKConfig

Base SDK configuration.

**Methods:**

- `to_dict()`

*Source: /home/dotmac_framework/src/dotmac_isp/sdks/core/config.py*

## dotmac_isp.sdks.core.datetime_utils

DateTime utilities for SDKs.

*Source: /home/dotmac_framework/src/dotmac_isp/sdks/core/datetime_utils.py*

## dotmac_isp.sdks.core.exceptions

Common exceptions for all DotMac SDKs.

### Classes

#### SDKError

Base exception for all SDK errors.

**Methods:**

- `__init__()`
- `__str__()`
- `to_dict()`

#### SDKConnectionError

Raised when connection to service fails.

#### SDKAuthenticationError

Raised when authentication fails.

#### SDKValidationError

Raised when request validation fails.

#### AlarmStormDetectedError

Raised when alarm storm is detected in network monitoring.

#### ConfigDriftDetectedError

Raised when configuration drift is detected in network devices.

#### RoutingError

Raised when routing fails in gateway.

#### ConfigurationError

Raised when SDK configuration is invalid.

#### ValidationError

Raised when data validation fails.

#### SDKRateLimitError

Raised when rate limit is exceeded.

**Methods:**

- `__init__()`

#### SDKTimeoutError

Raised when request times out.

#### SDKNotFoundError

Raised when requested resource is not found.

#### SDKConflictError

Raised when resource conflict occurs.

#### SDKServiceUnavailableError

Raised when service is temporarily unavailable.

#### SDKDeprecationWarning

Warning for deprecated SDK methods or parameters.

#### ConsentError

Raised when consent-related operations fail.

#### AnalyticsError

Raised when analytics operations fail.

#### AlarmError

Raised when alarm/alert operations fail.

#### GatewayError

Raised when API gateway operations fail.

#### CustomerError

Raised when customer operations fail.

#### PortalError

Raised when portal operations fail.

#### PortalNotFoundError

Raised when portal is not found.

#### AccountError

Raised when account operations fail.

#### OrganizationError

Raised when organization operations fail.

#### ProfileError

Raised when profile operations fail.

#### VerificationError

Raised when verification operations fail.

#### VerificationExpiredError

Raised when verification token has expired.

#### VerificationFailedError

Raised when verification fails.

#### ConfigError

Raised when configuration operations fail.

#### ResourceAllocationError

Raised when resource allocation fails.

#### ResourceBindingError

Raised when resource binding fails.

#### PolicyIntentError

Raised when policy intent operations fail.

#### PricingRuleError

Raised when pricing rule operations fail.

#### TariffError

Raised when tariff operations fail.

#### InvalidStateTransitionError

Raised when invalid state transition is attempted.

#### ProvisioningError

Raised when provisioning operations fail.

#### ServiceNotFoundError

Raised when service is not found.

#### ServiceStateError

Raised when service state operations fail.

#### NotFoundError

Generic not found error.

#### DeviceError

Raised when device operations fail.

#### AddOnError

Raised when add-on operations fail.

#### DeviceNotFoundError

Raised when device is not found.

#### BundleError

Raised when bundle operations fail.

#### ServiceDefinitionError

Raised when service definition operations fail.

#### MonitoringDataUnavailableError

Raised when monitoring data is unavailable.

#### ServicePlanError

Raised when service plan operations fail.

#### MonitoringError

Raised when monitoring operations fail.

#### NetworkingError

Raised when networking operations fail.

#### RepositoryError

Raised when repository operations fail.

#### IPAddressConflictError

Raised when IP address conflicts occur.

#### IPAMError

Raised when IPAM (IP Address Management) operations fail.

#### AutomationError

Raised when network automation operations fail.

#### TopologyError

Raised when network topology operations fail.

#### RADIUSError

Raised when RADIUS operations fail.

#### RADIUSAuthenticationError

Raised when RADIUS authentication fails.

#### CoAFailedError

Raised when RADIUS Change of Authorization (CoA) fails.

#### VLANError

Raised when VLAN operations fail.

#### VLANConflictError

Raised when VLAN conflicts occur.

*Source: /home/dotmac_framework/src/dotmac_isp/sdks/core/exceptions.py*

## dotmac_isp.sdks.events.__init__

SDK package for dotmac_core_events.

Provides core SDKs for:

- Event Bus operations with Redis Streams and Kafka adapters
- Schema Registry with JSON Schema validation
- Transactional Outbox pattern implementation

*Source: /home/dotmac_framework/src/dotmac_isp/sdks/events/__init__.py*

## dotmac_isp.sdks.gateway.__init__

SDK package for DotMac API Gateway - Individual SDK exports for composable usage.

*Source: /home/dotmac_framework/src/dotmac_isp/sdks/gateway/__init__.py*

## dotmac_isp.sdks.identity.schemas

Base schemas for Identity SDK.

These are minimal schemas that can be extended by modules
without creating circular imports.

### Classes

#### CustomerCreate

Base schema for creating customers.

#### CustomerUpdate

Base schema for updating customers.

#### CustomerResponse

Base schema for customer responses.

#### CustomerListFilters

Base schema for filtering customer lists.

*Source: /home/dotmac_framework/src/dotmac_isp/sdks/identity/schemas.py*

## dotmac_isp.sdks.models.accounts

Account-related models for SDKs.

### Classes

#### MFAFactorType

Multi-factor authentication factor types.

#### AccountStatus

Account status enumeration.

#### MFAFactor

MFA factor model.

**Methods:**

- `__init__()`

#### Account

Account model.

**Methods:**

- `__init__()`
- `is_locked()`
- `lock_account()`
- `unlock_account()`

*Source: /home/dotmac_framework/src/dotmac_isp/sdks/models/accounts.py*

## dotmac_isp.sdks.models.addresses

Address models for SDK operations.

### Classes

#### AddressType

Address type enumeration.

#### AddressModel

Address model for customer and service locations.

*Source: /home/dotmac_framework/src/dotmac_isp/sdks/models/addresses.py*

## dotmac_isp.sdks.models.contacts

Contact models for SDK.

### Classes

#### ContactType

Contact type enumeration.

#### EmailType

Email type enumeration.

#### PhoneType

Phone type enumeration.

#### Contact

Contact model.

#### ContactEmail

Contact email model.

#### ContactPhone

Contact phone model.

*Source: /home/dotmac_framework/src/dotmac_isp/sdks/models/contacts.py*

## dotmac_isp.sdks.models.customers

Customer models for SDK.

### Classes

#### CustomerStatus

Customer status enumeration.

#### CustomerType

Customer type enumeration.

#### Customer

Customer model.

#### CustomerProfile

Customer profile model.

#### CustomerNote

Customer note model.

*Source: /home/dotmac_framework/src/dotmac_isp/sdks/models/customers.py*

## dotmac_isp.sdks.models.dashboards

Dashboard models for analytics.

### Classes

#### ChartType

Chart type enumeration.

#### ChartWidget

Dashboard chart widget.

**Methods:**

- `__post_init__()`

#### Dashboard

Analytics dashboard model.

**Methods:**

- `__post_init__()`
- `add_widget()`
- `remove_widget()`
- `get_widget()`

*Source: /home/dotmac_framework/src/dotmac_isp/sdks/models/dashboards.py*

## dotmac_isp.sdks.models.datasets

Dataset models for analytics SDK.

### Classes

#### DataSourceType

Data source type enumeration.

#### DataSource

Data source model.

#### Dataset

Dataset model.

#### DataPoint

Data point model.

*Source: /home/dotmac_framework/src/dotmac_isp/sdks/models/datasets.py*

## dotmac_isp.sdks.models.enums

Common enums for SDK models.

### Classes

#### AggregationMethod

Aggregation method enumeration.

#### AlertSeverity

Alert severity enumeration.

#### MetricType

Metric type enumeration.

#### TimeGranularity

Time granularity enumeration.

#### DataSourceType

Data source type enumeration.

#### ReportType

Report type enumeration.

#### EventType

Event type enumeration.

#### SegmentOperator

Segment operator enumeration.

*Source: /home/dotmac_framework/src/dotmac_isp/sdks/models/enums.py*

## dotmac_isp.sdks.models.organizations

Organization-related models for SDKs.

### Classes

#### OrganizationType

Organization type enumeration.

#### MemberRole

Organization member role enumeration.

#### OrganizationStatus

Organization status enumeration.

#### Organization

Organization model.

**Methods:**

- `__init__()`
- `is_active()`
- `suspend()`
- `activate()`

#### OrganizationMember

Organization member model.

**Methods:**

- `__init__()`
- `has_role()`
- `can_manage_members()`
- `can_admin()`
- `promote_to_role()`
- `deactivate()`

*Source: /home/dotmac_framework/src/dotmac_isp/sdks/models/organizations.py*

## dotmac_isp.sdks.models.portals

Portal-related models for SDKs.

### Classes

#### AccessLevel

Portal access levels.

#### BindingStatus

Portal binding status.

#### CustomerPortalBinding

Customer portal binding model.

**Methods:**

- `__init__()`

#### PortalType

Portal type enumeration.

#### PortalStatus

Portal status enumeration.

#### PortalSettings

Portal settings model.

**Methods:**

- `__init__()`

#### Portal

Portal model.

**Methods:**

- `__init__()`
- `is_active()`
- `is_maintenance_mode()`
- `activate()`
- `deactivate()`
- `enter_maintenance()`
- `record_access()`

#### ResellerPortalAccess

Reseller portal access model.

**Methods:**

- `__init__()`
- `is_expired()`
- `is_valid()`
- `revoke()`
- `record_access()`

*Source: /home/dotmac_framework/src/dotmac_isp/sdks/models/portals.py*

## dotmac_isp.sdks.models.profiles

Profile-related models for SDKs.

### Classes

#### ProfileVisibility

Profile visibility enumeration.

#### ProfileStatus

Profile status enumeration.

#### UserProfile

User profile model.

**Methods:**

- `__init__()`
- `get_full_name()`
- `is_active()`
- `is_public()`
- `update_last_active()`
- `set_preference()`
- `get_preference()`
- `activate()`
- `deactivate()`
- `suspend()`

*Source: /home/dotmac_framework/src/dotmac_isp/sdks/models/profiles.py*

## dotmac_isp.sdks.models.reports

Report models for analytics SDK.

### Classes

#### ReportStatus

Report execution status.

#### Report

Report model.

#### ReportExecution

Report execution model.

#### ReportSubscription

Report subscription model.

*Source: /home/dotmac_framework/src/dotmac_isp/sdks/models/reports.py*

## dotmac_isp.sdks.models.segments

Segment models for analytics SDK.

### Classes

#### SegmentRule

Segment rule model.

#### Segment

Segment model.

**Methods:**

- `__post_init__()`

#### SegmentMembership

Segment membership model.

*Source: /home/dotmac_framework/src/dotmac_isp/sdks/models/segments.py*

## dotmac_isp.sdks.models.verification

Verification-related models for SDKs.

### Classes

#### VerificationStatus

Verification status enumeration.

#### DeliverabilityStatus

Email deliverability status enumeration.

#### EmailVerification

Email verification model.

**Methods:**

- `__init__()`
- `is_expired()`
- `can_retry()`
- `mark_verified()`
- `mark_failed()`

#### PhoneVerification

Phone verification model.

**Methods:**

- `__init__()`
- `is_expired()`
- `can_retry()`
- `mark_verified()`
- `mark_failed()`

*Source: /home/dotmac_framework/src/dotmac_isp/sdks/models/verification.py*

## dotmac_isp.sdks.networking.__init__

Minimal, reusable SDKs for DotMac Networking.

*Source: /home/dotmac_framework/src/dotmac_isp/sdks/networking/__init__.py*

## dotmac_isp.sdks.networking.device_config

Device Config SDK - intent → template, diff, drift, approvals, maintenance windows

### Classes

#### DeviceConfigService

In-memory service for device configuration operations.

**Methods:**

- `__init__()`
- `async create_config_template()`
- `async create_config_intent()`
- `async render_config()`
- `async calculate_diff()`
- `async detect_drift()`
- `async create_maintenance_window()`

#### DeviceConfigSDK

Minimal, reusable SDK for device configuration management with NetJSON support.

**Methods:**

- `__init__()`
- `async create_config_template()`
- `async create_config_intent()`
- `async render_configuration()`
- `async calculate_config_diff()`
- `async detect_config_drift()`
- `async create_maintenance_window()`
- `async approve_config_intent()`
- `async get_pending_approvals()`
- `async get_maintenance_windows()`

*Source: /home/dotmac_framework/src/dotmac_isp/sdks/networking/device_config.py*

## dotmac_isp.sdks.networking.netjson_support

NetJSON Support for DotMac - Adds OpenWrt UCI generation capability.
Lightweight alternative to full OpenWISP Controller integration.

### Classes

#### NetJSONRenderer

Convert NetJSON DeviceConfiguration to OpenWrt UCI commands.
Provides the key OpenWISP functionality without the overhead.

**Methods:**

- `__init__()`
- `render_openwrt_config()`

#### NetJSONValidator

Validate NetJSON configuration before rendering.

**Methods:**

- `validate_netjson()`

#### NetJSONTemplateEngine

Template engine for NetJSON configurations with variable substitution.

**Methods:**

- `__init__()`
- `set_variables()`
- `render_template()`

#### NetJSONConfigMixin

Mixin to add NetJSON support to existing DeviceConfigSDK.

**Methods:**

- `__init__()`
- `async create_netjson_template()`
- `async render_netjson_to_uci()`

*Source: /home/dotmac_framework/src/dotmac_isp/sdks/networking/netjson_support.py*

## dotmac_isp.sdks.platform.config_query_filters

Configuration query filter strategies using Strategy pattern.
Replaces the 24-complexity _matches_query method with focused filter strategies.

### Classes

#### ConfigEntry

Configuration entry for type hints.

#### ConfigQuery

Configuration query for type hints.

#### ConfigFilterStrategy

Base strategy for configuration filtering.

**Methods:**

- `matches()`

#### ScopeFilterStrategy

Filter by configuration scope.

**Methods:**

- `matches()`

#### TenantFilterStrategy

Filter by tenant ID.

**Methods:**

- `matches()`

#### UserFilterStrategy

Filter by user ID.

**Methods:**

- `matches()`

#### ServiceFilterStrategy

Filter by service name.

**Methods:**

- `matches()`

#### KeyFilterStrategy

Filter by configuration key patterns.

**Methods:**

- `matches()`

#### CategoryFilterStrategy

Filter by configuration category.

**Methods:**

- `matches()`

#### EnvironmentFilterStrategy

Filter by environment.

**Methods:**

- `matches()`

#### DataTypeFilterStrategy

Filter by data types.

**Methods:**

- `matches()`

#### SecretFilterStrategy

Filter by secret flag.

**Methods:**

- `matches()`

#### ReadOnlyFilterStrategy

Filter by readonly flag.

**Methods:**

- `matches()`

#### TagsFilterStrategy

Filter by tags.

**Methods:**

- `matches()`

#### ConfigQueryMatcher

Configuration query matcher using Strategy pattern.

REFACTORED: Replaces 24-complexity _matches_query method with
focused, testable filter strategies (Complexity: 3).

**Methods:**

- `__init__()`
- `matches_query()`
- `add_filter_strategy()`
- `remove_filter_strategy()`
- `get_active_strategies()`

*Source: /home/dotmac_framework/src/dotmac_isp/sdks/platform/config_query_filters.py*

## dotmac_isp.sdks.platform.repositories.auth

Authentication repositories for Platform SDK.

This module provides SDK-specific repository abstractions for authentication operations.
It wraps the actual identity module repositories to maintain proper architectural boundaries.

### Classes

#### UserRepository

Platform SDK wrapper for user repository operations.

**Methods:**

- `__init__()`
- `async find_by_id()`
- `async find_by_username()`
- `async find_by_email()`
- `async create()`
- `async update()`
- `async delete()`

#### UserSessionRepository

Platform SDK repository for user session operations.

This is a simplified session repository for SDK purposes.
In a full implementation, this would connect to a dedicated session store.

**Methods:**

- `__init__()`
- `async create_session()`
- `async find_session()`
- `async update_session()`
- `async delete_session()`
- `async find_sessions_by_user()`

*Source: /home/dotmac_framework/src/dotmac_isp/sdks/platform/repositories/auth.py*

## dotmac_isp.sdks.platform.repositories.base

Platform SDK repositories for data access.

### Classes

#### BaseRepository

Base repository for platform SDK data access.

**Methods:**

- `async find_by_id()`
- `async create()`
- `async update()`
- `async delete()`

#### ConfigurationRepository

Repository for configuration management.

**Methods:**

- `async find_by_id()`
- `async create()`
- `async update()`
- `async delete()`
- `async find_by_tenant()`

#### FeatureFlagsRepository

Repository for feature flags management.

**Methods:**

- `async find_by_id()`
- `async create()`
- `async update()`
- `async delete()`
- `async find_active_flags()`

#### MetricsRepository

Repository for metrics data.

**Methods:**

- `async find_by_id()`
- `async create()`
- `async update()`
- `async delete()`
- `async find_metrics_by_timerange()`

*Source: /home/dotmac_framework/src/dotmac_isp/sdks/platform/repositories/base.py*

## dotmac_isp.sdks.platform.utils.__init__

Platform utilities module.

*Source: /home/dotmac_framework/src/dotmac_isp/sdks/platform/utils/__init__.py*

## dotmac_isp.sdks.platform.utils.datetime_compat

DateTime compatibility utilities for cross-platform support.

*Source: /home/dotmac_framework/src/dotmac_isp/sdks/platform/utils/datetime_compat.py*

## dotmac_isp.sdks.services.account_service

Account service for SDK operations.

This is a minimal implementation for SDK compatibility.

### Classes

#### AccountService

Simple in-memory account service for SDK operations.

**Methods:**

- `__init__()`
- `async create_account()`
- `async get_account()`
- `async get_account_by_username()`
- `async get_account_by_email()`
- `async update_account()`
- `async delete_account()`
- `async add_mfa_factor()`
- `async get_mfa_factors()`
- `async remove_mfa_factor()`
- `async verify_mfa_factor()`

*Source: /home/dotmac_framework/src/dotmac_isp/sdks/services/account_service.py*

## dotmac_isp.sdks.services.events

Events handling for services SDK.

### Classes

#### EventType

Event type enumeration.

#### Event

Event data structure.

**Methods:**

- `__init__()`
- `to_dict()`

#### EventBus

Event bus for handling service events.

**Methods:**

- `__init__()`
- `subscribe()`
- `unsubscribe()`
- `async publish()`
- `async publish_service_created()`
- `async publish_service_provisioned()`

#### EventHandler

Base class for event handlers.

**Methods:**

- `__init__()`
- `async handle_event()`

#### ServiceEventHandler

Handler for service-related events.

**Methods:**

- `async handle_service_created()`
- `async handle_service_provisioned()`

#### BillingEventHandler

Handler for billing-related events.

**Methods:**

- `async handle_billing_event()`

#### EventService

Service for managing events and event handling.

**Methods:**

- `__init__()`
- `async publish_event()`
- `register_handler()`
- `async process_events()`

*Source: /home/dotmac_framework/src/dotmac_isp/sdks/services/events.py*

## dotmac_isp.sdks.services.metrics

Metrics service for Services SDK.

This module provides metrics-related service operations for analytics integration.

### Classes

#### MetricService

Service for handling metrics operations in the Services SDK.

**Methods:**

- `__init__()`
- `async create_metric()`
- `async get_metric()`
- `async query_metrics()`
- `async aggregate_metrics()`
- `async delete_metric()`
- `async get_metrics_summary()`

*Source: /home/dotmac_framework/src/dotmac_isp/sdks/services/metrics.py*

## dotmac_isp.sdks.utils.__init__

SDK utility functions.

*Source: /home/dotmac_framework/src/dotmac_isp/sdks/utils/__init__.py*

## dotmac_isp.sdks.utils.datetime_compat

DateTime compatibility utilities.

*Source: /home/dotmac_framework/src/dotmac_isp/sdks/utils/datetime_compat.py*

## dotmac_isp.sdks.utils.formatters

Data formatting utilities.

*Source: /home/dotmac_framework/src/dotmac_isp/sdks/utils/formatters.py*

## dotmac_isp.sdks.utils.validators

Data validation utilities.

*Source: /home/dotmac_framework/src/dotmac_isp/sdks/utils/validators.py*

## dotmac_isp.sdks.workflows.__init__

Core SDKs for operations plane functionality.

This module provides SDKs for:

- Workflow orchestration and management
- Task execution and coordination
- Automation rules and engines
- Scheduling and cron jobs
- State machine management
- Saga pattern implementation
- Job queue orchestration

*Source: /home/dotmac_framework/src/dotmac_isp/sdks/workflows/__init__.py*

## dotmac_isp.shared.__init__

Shared utilities and common code across all modules.

*Source: /home/dotmac_framework/src/dotmac_isp/shared/__init__.py*

## dotmac_isp.shared.base_repository

Base Repository Classes

ARCHITECTURE IMPROVEMENT: Provides reusable CRUD operations and patterns
to eliminate code duplication across modules. Implements Repository pattern
with consistent error handling and tenant isolation.

### Classes

#### BaseRepository

Base repository providing common CRUD operations.

PATTERN: Repository Pattern with Generic Types

- Encapsulates database access logic
- Provides consistent error handling
- Supports tenant isolation
- Reduces code duplication across modules

Features:

- Generic CRUD operations
- Query building with filters, sorting, pagination
- Tenant-aware operations
- Bulk operations
- Consistent error handling
- Audit trail support

**Methods:**

- `__init__()`
- `create()`
- `get_by_id()`
- `get_by_id_or_raise()`
- `update()`
- `delete()`
- `list()`
- `count()`
- `bulk_create()`
- `bulk_update()`
- `exists()`

#### BaseTenantRepository

Base repository for tenant-aware entities.

Extends BaseRepository with additional tenant-specific functionality.

**Methods:**

- `__init__()`
- `get_tenant_stats()`

*Source: /home/dotmac_framework/src/dotmac_isp/shared/base_repository.py*

## dotmac_isp.shared.base_service

Base Service Classes

ARCHITECTURE IMPROVEMENT: Provides reusable business logic patterns
to eliminate code duplication across modules. Implements Service pattern
with consistent error handling, validation, and transaction management.

### Classes

#### BaseService

Service layer - exceptions bubble up to router @standard_exception_handler.

**Methods:**

- `__init__()`
- `async create()`
- `async get_by_id()`
- `async get_by_id_or_raise()`
- `async update()`
- `async delete()`
- `async list()`
- `async count()`
- `async _pre_create_hook()`
- `async _post_create_hook()`
- `async _pre_update_hook()`
- `async _post_update_hook()`
- `async _pre_delete_hook()`
- `async _post_delete_hook()`
- `async _validate_create_rules()`
- `async _validate_update_rules()`
- `async _validate_delete_rules()`
- `async _apply_access_control_filters()`

#### BaseTenantService

Base service for tenant-aware entities.

Extends BaseService with additional tenant-specific functionality.

**Methods:**

- `__init__()`
- `async get_tenant_stats()`
- `async _apply_access_control_filters()`

#### BaseReadOnlyService

Base service for read-only operations.

Useful for reporting, analytics, and view-only services.

**Methods:**

- `__init__()`
- `async get_by_id()`
- `async list()`
- `async count()`

*Source: /home/dotmac_framework/src/dotmac_isp/shared/base_service.py*

## dotmac_isp.shared.database.relationship_registry

### Classes

#### RelationshipRegistry

Registry for deferred cross-module relationships.

**Methods:**

- `__init__()`
- `register_relationship()`
- `configure_all_relationships()`
- `reset()`

*Source: /home/dotmac_framework/src/dotmac_isp/shared/database/relationship_registry.py*

## dotmac_isp.shared.enums

Shared enums to eliminate duplication across the ISP framework.

### Classes

#### CommonStatus

Common status values used across multiple modules.

#### EntityLifecycle

Standard entity lifecycle states.

#### ProcessingStatus

Status values for processing workflows.

#### PaymentStatus

Payment and financial status values.

#### AlertSeverity

Alert and notification severity levels.

#### Priority

Priority levels for tasks, tickets, etc.

#### NetworkStatus

Network-related status values.

#### DeliveryStatus

Delivery and notification status values.

#### AuditAction

Audit log action types.

#### ComplianceStatus

Compliance and regulatory status values.

#### ContractStatus

Contract and agreement status values.

#### UserStatus

User account status values.

#### ServiceStatus

Service provisioning status values.

#### OrderStatus

Order processing status values.

#### InventoryMovementType

Inventory movement types.

#### WorkOrderStatus

Work order status values.

#### InstallationStatus

Installation and deployment status values.

#### CommunicationChannel

Communication channel types.

#### ContactType

Contact relationship types.

#### AddressType

Address types for locations.

#### DeviceType

Network device types.

#### MetricType

Metric and measurement types.

#### ReportFormat

Report output formats.

#### TimeZone

Common timezone values.

#### Currency

Currency codes.

#### Country

Common country codes.

#### LanguageCode

Language codes for localization.

*Source: /home/dotmac_framework/src/dotmac_isp/shared/enums.py*

## dotmac_isp.shared.exceptions

Shared exceptions for the DotMac ISP Framework.

### Classes

#### DotMacISPError

Base exception for DotMac ISP Framework.

**Methods:**

- `__init__()`

#### ValidationError

Raised when data validation fails.

**Methods:**

- `__init__()`

#### NotFoundError

Raised when a requested resource is not found.

**Methods:**

- `__init__()`

#### ConflictError

Raised when a resource conflict occurs.

**Methods:**

- `__init__()`

#### AuthenticationError

Raised when authentication fails.

**Methods:**

- `__init__()`

#### AuthorizationError

Raised when authorization fails.

**Methods:**

- `__init__()`

#### ServiceError

Raised when a service operation fails.

**Methods:**

- `__init__()`

#### ExternalServiceError

Raised when an external service call fails.

**Methods:**

- `__init__()`

#### NetworkError

Raised when network-related operations fail.

**Methods:**

- `__init__()`

#### BillingError

Raised when billing operations fail.

**Methods:**

- `__init__()`

#### TenantError

Raised when tenant-related operations fail.

**Methods:**

- `__init__()`

#### RateLimitError

Raised when rate limit is exceeded.

**Methods:**

- `__init__()`

#### ConfigurationError

Raised when configuration is invalid or missing.

**Methods:**

- `__init__()`

#### EntityNotFoundError

Raised when a requested entity is not found in the database.

**Methods:**

- `__init__()`

#### BusinessRuleError

Raised when a business rule is violated.

**Methods:**

- `__init__()`

#### DuplicateEntityError

Raised when attempting to create a duplicate entity.

**Methods:**

- `__init__()`

#### DatabaseError

Raised when a database operation fails.

**Methods:**

- `__init__()`

#### NotImplementedError

Raised when a feature is not implemented.

**Methods:**

- `__init__()`

*Source: /home/dotmac_framework/src/dotmac_isp/shared/exceptions.py*

## dotmac_management.__init__

DotMac Management Platform - Monolithic SaaS Application

*Source: /home/dotmac_framework/src/dotmac_management/__init__.py*

## dotmac_management.api.__init__

API routes for the DotMac Management Platform.

*Source: /home/dotmac_framework/src/dotmac_management/api/__init__.py*

## dotmac_management.api.portal_handlers.__init__

Portal-specific API endpoints.

*Source: /home/dotmac_framework/src/dotmac_management/api/portal_handlers/__init__.py*

## dotmac_management.api.portals

Portal-specific API routes for different user interfaces.

*Source: /home/dotmac_framework/src/dotmac_management/api/portals.py*

## dotmac_management.api.v1.__init__

from dotmac_shared.api.exception_handlers import standard_exception_handler
API v1 routes.

*Source: /home/dotmac_framework/src/dotmac_management/api/v1/__init__.py*

## dotmac_management.api.v1.monitoring

from dotmac_shared.api.exception_handlers import standard_exception_handler
API endpoints for monitoring and health checks.

### Classes

#### HealthResponse

Health check response model.

*Source: /home/dotmac_framework/src/dotmac_management/api/v1/monitoring.py*

## dotmac_management.api.v1.partners.__init__

Partner management API endpoints

*Source: /home/dotmac_framework/src/dotmac_management/api/v1/partners/__init__.py*

## dotmac_management.api_new.__init__

Management Platform API package.

*Source: /home/dotmac_framework/src/dotmac_management/api_new/__init__.py*

## dotmac_management.api_new.websocket.router

WebSocket Router for Management Platform Real-time Communication.

*Source: /home/dotmac_framework/src/dotmac_management/api_new/websocket/router.py*

## dotmac_management.config

Application configuration with environment-specific settings.

### Classes

#### BaseServiceSettings

#### Settings

Management Platform specific settings that extend base configuration.

**Methods:**

- `validate_aws_region()`
- `validate_k8s_namespace_prefix()`
- `validate_management_platform_config()`
- `get_database_url()`

#### Config

*Source: /home/dotmac_framework/src/dotmac_management/config.py*

## dotmac_management.core.__init__

DotMac Management Platform Core Module

This module provides core functionality for the management platform including
configuration, database, and shared utilities.

*Source: /home/dotmac_framework/src/dotmac_management/core/__init__.py*

## dotmac_management.core.auth

Authentication dependencies and utilities.

*Source: /home/dotmac_framework/src/dotmac_management/core/auth.py*

## dotmac_management.core.commission

Commission calculation engine for partner management

### Classes

#### CommissionTier

Commission tier configuration

#### CommissionResult

Commission calculation result

#### CommissionCalculator

Commission calculation engine

**Methods:**

- `__init__()`
- `calculate_customer_commission()`
- `create_commission_record()`
- `update_commission_record()`
- `validate_commission()`
- `determine_eligible_tier()`
- `calculate_batch_commissions()`

*Source: /home/dotmac_framework/src/dotmac_management/core/commission.py*

## dotmac_management.core.database

Core database utilities and transaction management.

*Source: /home/dotmac_framework/src/dotmac_management/core/database.py*

## dotmac_management.core.multi_app_config

Enhanced tenant configuration for multi-application deployments.

Extends the existing TenantConfig to support multiple applications within a single tenant container.

### Classes

#### ApplicationStatus

Status of an application deployment.

#### ApplicationDeployment

Configuration for a single application deployment within a tenant.

**Methods:**

- `get_effective_config()`
- `get_effective_environment()`
- `get_deployment_name()`

#### NetworkConfiguration

Network configuration for tenant applications.

#### MultiAppTenantConfig

Enhanced tenant configuration supporting multiple applications.

**Methods:**

- `__post_init__()`
- `add_application()`
- `remove_application()`
- `get_application()`
- `get_applications_by_type()`
- `validate_configuration()`
- `get_deployment_order()`
- `to_legacy_tenant_config()`
- `from_legacy_tenant_config()`

*Source: /home/dotmac_framework/src/dotmac_management/core/multi_app_config.py*

## dotmac_management.core.plugins.__init__

Plugin system for DotMac Management Platform.

*Source: /home/dotmac_framework/src/dotmac_management/core/plugins/__init__.py*

## dotmac_management.core.plugins.base

Base plugin classes and interfaces for the DotMac Management Platform.

### Classes

#### PluginType

Types of plugins supported by the platform.

#### PluginStatus

Plugin execution status.

#### PluginMeta

Plugin metadata and configuration.

#### PluginError

Base exception for plugin-related errors.

**Methods:**

- `__init__()`

#### PluginValidationError

Raised when plugin validation fails.

#### PluginExecutionError

Raised when plugin execution fails.

#### PluginConfigurationError

Raised when plugin configuration is invalid.

#### BasePlugin

Base class for all management platform plugins.

**Methods:**

- `__init__()`
- `meta()`
- `async initialize()`
- `async validate_configuration()`
- `async health_check()`
- `async shutdown()`
- `async get_status()`
- `log_error()`
- `validate_tenant_context()`

#### PluginCapability

Base class for plugin capabilities.

**Methods:**

- `get_capability_name()`
- `async execute()`

#### EventBasedPlugin

Base class for event-driven plugins.

**Methods:**

- `get_supported_events()`
- `async handle_event()`

#### AsyncPlugin

Base class for asynchronous background plugins.

**Methods:**

- `async start_background_task()`
- `async stop_background_task()`
- `async get_task_status()`

#### TenantAwarePlugin

Base class for plugins that need tenant context.

**Methods:**

- `__init__()`
- `async validate_tenant_permissions()`
- `ensure_tenant_context()`

#### BillablePlugin

Base class for plugins that generate billable usage.

**Methods:**

- `async record_usage()`
- `async get_usage_summary()`
- `get_billing_category()`

*Source: /home/dotmac_framework/src/dotmac_management/core/plugins/base.py*

## dotmac_management.core.plugins.essential_plugins

Essential plugins initialization for the management platform.

*Source: /home/dotmac_framework/src/dotmac_management/core/plugins/essential_plugins.py*

## dotmac_management.core.plugins.hooks

Plugin hook system for event-driven plugin execution.

### Classes

#### PluginHooks

Event-driven plugin hook system.

**Methods:**

- `__init__()`
- `async register_hook()`
- `async unregister_plugin_hooks()`
- `async trigger_hook()`
- `async trigger_hook_first_success()`
- `list_hooks()`
- `get_plugin_hooks()`

#### HookNames

Standard hook names for management platform events.

*Source: /home/dotmac_framework/src/dotmac_management/core/plugins/hooks.py*

## dotmac_management.core.plugins.interfaces

Plugin interfaces for extending management platform services.

### Classes

#### MonitoringProviderPlugin

Interface for monitoring and alerting provider plugins.

**Methods:**

- `meta()`
- `async send_alert()`
- `async collect_metrics()`
- `async execute_health_check()`
- `async create_dashboard()`
- `get_supported_channels()`

#### DeploymentProviderPlugin

Interface for deployment and infrastructure provider plugins.

**Methods:**

- `meta()`
- `async provision_infrastructure()`
- `async deploy_application()`
- `async scale_application()`
- `async rollback_deployment()`
- `async validate_template()`
- `async get_deployment_status()`
- `async calculate_deployment_cost()`
- `get_supported_providers()`
- `get_supported_orchestrators()`
- `async calculate_infrastructure_cost()`

#### NotificationChannelPlugin

Interface for notification delivery channel plugins.

**Methods:**

- `meta()`
- `async send_notification()`
- `async send_alert()`
- `async send_digest()`
- `validate_recipient()`
- `get_channel_type()`
- `get_supported_message_types()`

#### PaymentProviderPlugin

Interface for payment processing provider plugins.

**Methods:**

- `meta()`
- `async process_payment()`
- `async create_subscription()`
- `async cancel_subscription()`
- `async handle_webhook()`
- `async refund_payment()`
- `get_supported_currencies()`
- `get_supported_payment_methods()`

#### BillingCalculatorPlugin

Interface for custom billing calculation plugins.

**Methods:**

- `meta()`
- `async calculate_usage_cost()`
- `async calculate_tax()`
- `async calculate_commission()`
- `async apply_discounts()`
- `get_supported_billing_models()`

#### SecurityScannerPlugin

Interface for security scanning plugins.

**Methods:**

- `meta()`
- `async scan_plugin_code()`
- `async scan_dependencies()`
- `async validate_plugin_permissions()`
- `get_supported_scan_types()`

#### BackupProviderPlugin

Interface for backup and disaster recovery plugins.

**Methods:**

- `meta()`
- `async create_backup()`
- `async restore_backup()`
- `async list_backups()`
- `async delete_backup()`
- `async test_restore()`
- `get_supported_backup_types()`

#### AnalyticsProviderPlugin

Interface for analytics and reporting plugins.

**Methods:**

- `meta()`
- `async generate_report()`
- `async track_event()`
- `async get_tenant_analytics()`
- `get_supported_report_types()`

*Source: /home/dotmac_framework/src/dotmac_management/core/plugins/interfaces.py*

## dotmac_management.core.plugins.loader

Plugin loader for dynamic plugin discovery and loading.

### Classes

#### PluginLoader

Loader for discovering and loading plugins dynamically.

**Methods:**

- `__init__()`
- `async discover_plugins()`
- `async load_plugin_by_name()`
- `async _load_plugin_from_directory()`
- `async _load_plugin_from_file()`
- `async _load_plugin_config()`
- `get_loaded_modules()`
- `async reload_module()`

*Source: /home/dotmac_framework/src/dotmac_management/core/plugins/loader.py*

## dotmac_management.core.plugins.registry

Plugin registry and management system.

### Classes

#### PluginRegistry

Central registry for managing plugins.

**Methods:**

- `__init__()`
- `async register_plugin()`
- `async unregister_plugin()`
- `get_plugin()`
- `get_plugins_by_type()`
- `get_active_plugins()`
- `list_plugins()`
- `async health_check_all()`
- `async reload_plugin()`
- `async _validate_plugin()`
- `async discover_and_load_plugins()`
- `async get_plugin_metrics()`

*Source: /home/dotmac_framework/src/dotmac_management/core/plugins/registry.py*

## dotmac_management.core.security_validator

Security validation utilities for configuration and runtime security checks.

### Classes

#### SecurityValidator

Validates security configuration and identifies potential issues.

**Methods:**

- `generate_secure_secret()`
- `validate_secret_strength()`
- `validate_production_config()`
- `create_secure_env_template()`
- `validate_runtime_security()`

*Source: /home/dotmac_framework/src/dotmac_management/core/security_validator.py*

## dotmac_management.core.websocket_manager

WebSocket manager for real-time tenant deployment and management updates.

### Classes

#### ManagementWebSocketManager

WebSocket manager for Management Platform real-time updates.

Handles tenant deployment status, infrastructure monitoring,
billing updates, and administrative notifications.

**Methods:**

- `__init__()`
- `async start()`
- `async stop()`
- `async connect_admin()`
- `async connect_tenant()`
- `async connect_partner()`
- `async disconnect()`
- `async broadcast_to_admins()`
- `async send_to_tenant()`
- `async send_to_partner()`
- `async broadcast_deployment_update()`
- `async broadcast_billing_update()`
- `async broadcast_infrastructure_alert()`
- `async _send_to_websocket()`
- `async _monitor_connections()`
- `async _close_all_connections()`
- `get_connection_stats()`

*Source: /home/dotmac_framework/src/dotmac_management/core/websocket_manager.py*

## dotmac_management.main

FastAPI application factory for the DotMac Management Platform using shared factory.

The Management Platform is the core SaaS service that provides:

- Multi-tenant ISP Framework deployment and management
- Partner and reseller portal management
- Infrastructure monitoring and billing
- Automated tenant provisioning and scaling
- Real-time deployment status and analytics

*Source: /home/dotmac_framework/src/dotmac_management/main.py*

## dotmac_management.models.__init__

SQLAlchemy models for the DotMac Management Platform.

*Source: /home/dotmac_framework/src/dotmac_management/models/__init__.py*

## dotmac_management.models.base

Base model with common fields and utilities.

### Classes

#### GUID

Platform-independent GUID type.

Uses PostgreSQL UUID when possible, otherwise stores as string.

**Methods:**

- `__init__()`
- `load_dialect_impl()`
- `process_bind_param()`
- `process_result_value()`

#### BaseModel

Base model with common fields.

**Methods:**

- `__tablename__()`
- `to_dict()`
- `update_from_dict()`
- `soft_delete()`
- `restore()`
- `is_active()`
- `__repr__()`

*Source: /home/dotmac_framework/src/dotmac_management/models/base.py*

## dotmac_management.models.billing

Billing and subscription models.

### Classes

#### SubscriptionStatus

Subscription status enumeration.

#### PricingPlanType

Pricing plan type.

#### InvoiceStatus

Invoice status enumeration.

#### PaymentStatus

Payment status enumeration.

#### CommissionStatus

Commission status enumeration.

#### PricingPlan

Pricing plans for tenant subscriptions.

**Methods:**

- `__repr__()`
- `monthly_price()`
- `annual_price()`

#### Subscription

Tenant subscription management.

**Methods:**

- `__repr__()`
- `is_active()`
- `is_trial()`
- `days_until_renewal()`
- `cancel()`
- `reactivate()`

#### Invoice

Invoice management.

**Methods:**

- `__repr__()`
- `total_amount()`
- `is_overdue()`
- `is_paid()`
- `mark_paid()`

#### Payment

Payment tracking.

**Methods:**

- `__repr__()`
- `amount()`
- `mark_succeeded()`
- `mark_failed()`

#### UsageRecord

Usage-based billing records.

**Methods:**

- `__repr__()`
- `total_cost()`

#### Commission

Reseller commission tracking.

**Methods:**

- `__repr__()`
- `commission_amount()`
- `base_amount()`
- `mark_paid()`

*Source: /home/dotmac_framework/src/dotmac_management/models/billing.py*

## dotmac_management.models.customer

Customer models for tenant customer management.

### Classes

#### CustomerStatus

Customer status enumeration.

#### ServiceStatus

Service status enumeration.

#### Customer

Customer model for tenant customers.

**Methods:**

- `__repr__()`
- `full_name()`
- `display_name()`
- `address()`

#### CustomerService

Customer service model for services provided to customers.

**Methods:**

- `__repr__()`
- `is_active()`

#### CustomerUsageRecord

Customer usage tracking.

**Methods:**

- `__repr__()`

#### ServiceUsageRecord

Service-level usage tracking.

**Methods:**

- `__repr__()`

*Source: /home/dotmac_framework/src/dotmac_management/models/customer.py*

## dotmac_management.models.deployment

Deployment and infrastructure models.

### Classes

#### DeploymentStatus

Deployment status enumeration.

#### CloudProvider

Cloud provider enumeration.

#### ResourceTier

Resource tier enumeration.

#### DeploymentEventType

Deployment event types.

#### InfrastructureTemplate

Infrastructure deployment templates.

**Methods:**

- `__repr__()`
- `estimated_monthly_cost()`

#### Deployment

Tenant deployment tracking.

**Methods:**

- `__repr__()`
- `is_running()`
- `is_healthy()`
- `estimated_monthly_cost()`
- `current_hourly_cost()`
- `start_deployment()`
- `complete_deployment()`
- `fail_deployment()`
- `update_health()`
- `scale()`

#### DeploymentEvent

Deployment event tracking.

**Methods:**

- `__repr__()`

#### DeploymentResource

Cloud resources created for deployments.

**Methods:**

- `__repr__()`
- `hourly_cost()`

*Source: /home/dotmac_framework/src/dotmac_management/models/deployment.py*

## dotmac_management.models.monitoring

Monitoring and analytics models.

### Classes

#### HealthStatus

Health status enumeration.

#### AlertSeverity

Alert severity levels.

#### AlertStatus

Alert status enumeration.

#### MetricType

Metric type enumeration.

#### HealthCheck

Health check results for tenants and deployments.

**Methods:**

- `__repr__()`
- `is_healthy()`
- `is_overdue()`
- `schedule_next_check()`

#### Metric

Metric data collection.

**Methods:**

- `__repr__()`
- `value_float()`

#### Alert

Alert management.

**Methods:**

- `__repr__()`
- `is_active()`
- `is_critical()`
- `duration_minutes()`
- `acknowledge()`
- `resolve()`
- `suppress()`

#### SLARecord

Service Level Agreement tracking.

**Methods:**

- `__repr__()`
- `uptime_percentage_float()`
- `sla_score()`
- `credit_amount()`

*Source: /home/dotmac_framework/src/dotmac_management/models/monitoring.py*

## dotmac_management.models.partner

Partner and Customer database models

### Classes

#### Partner

Partner/Reseller model

#### PartnerCustomer

Customer managed by a partner

#### Commission

Commission records for partners

#### Territory

Partner territory definitions

#### PartnerPerformanceMetrics

Historical partner performance metrics

*Source: /home/dotmac_framework/src/dotmac_management/models/partner.py*

## dotmac_management.models.plugin

Plugin licensing and management models.

### Classes

#### PluginStatus

Plugin status enumeration.

#### LicenseTier

Plugin license tiers.

#### LicenseStatus

Plugin license status.

#### PluginCategory

Plugin category management.

**Methods:**

- `__repr__()`

#### Plugin

Plugin catalog and management.

**Methods:**

- `__repr__()`
- `basic_monthly_price()`
- `premium_monthly_price()`
- `enterprise_monthly_price()`
- `get_price_for_tier()`

#### PluginLicense

Plugin license management for tenants.

**Methods:**

- `__repr__()`
- `is_active()`
- `is_trial()`
- `is_expired()`
- `days_until_expiry()`
- `usage_percentage()`
- `activate()`
- `suspend()`
- `expire()`
- `renew()`
- `record_usage()`

#### PluginUsage

Plugin usage tracking for billing and analytics.

**Methods:**

- `__repr__()`
- `total_cost()`

*Source: /home/dotmac_framework/src/dotmac_management/models/plugin.py*

## dotmac_management.models.tenant

Tenant management models - strategically aligned with migration schema.

This represents the true architectural vision: a container-per-tenant SaaS platform
where each tenant (ISP customer) gets their own isolated container deployment.

### Classes

#### TenantStatus

Tenant lifecycle status - matching migration schema.

#### Tenant

Core tenant model - each tenant represents an ISP customer
who will get their own containerized ISP framework deployment.

Matches the migration schema exactly.

**Methods:**

- `__repr__()`
- `is_active()`
- `can_deploy()`
- `get_container_name()`
- `get_container_url()`

#### TenantConfiguration

Tenant configuration model - matches migration schema.
Stores configuration for tenant's ISP framework container.

**Methods:**

- `__repr__()`

#### TenantInvitation

Tenant invitation model - for inviting users to join a tenant's ISP management.
This is a logical model that may not have a direct table yet.

**Methods:**

- `__repr__()`

*Source: /home/dotmac_framework/src/dotmac_management/models/tenant.py*

## dotmac_management.models.user

User and authentication models.

### Classes

#### UserRole

User role constants.

#### User

User model for authentication and authorization.

**Methods:**

- `__repr__()`
- `full_name()`
- `is_master_admin()`
- `is_tenant_admin()`
- `is_locked()`
- `lock_account()`
- `unlock_account()`
- `record_login()`

#### UserSession

User session tracking.

**Methods:**

- `is_expired()`
- `extend_session()`
- `revoke()`

#### UserInvitation

User invitation for tenant access.

**Methods:**

- `is_expired()`
- `is_valid()`

*Source: /home/dotmac_framework/src/dotmac_management/models/user.py*

## dotmac_management.modules.__init__

Management Platform modules package.

*Source: /home/dotmac_framework/src/dotmac_management/modules/__init__.py*

## dotmac_management.modules.monitoring.router

from dotmac_shared.api.exception_handlers import standard_exception_handler
API endpoints for monitoring and health checks.

### Classes

#### HealthResponse

Health check response model.

*Source: /home/dotmac_framework/src/dotmac_management/modules/monitoring/router.py*

## dotmac_management.modules.test_module.__init__

Test module to demonstrate standardized structure.

*Source: /home/dotmac_framework/src/dotmac_management/modules/test_module/__init__.py*

## dotmac_management.plugins.deployment.__init__

Deployment provider plugins initialization.

*Source: /home/dotmac_framework/src/dotmac_management/plugins/deployment/__init__.py*

## dotmac_management.repositories.base

Base repository with common CRUD operations.

### Classes

#### BaseRepository

Base repository with common CRUD operations.

**Methods:**

- `__init__()`
- `async create()`
- `async get_by_id()`
- `async get_by_field()`
- `async list()`
- `async list_paginated()`
- `async cursor_paginate()`
- `async count()`
- `async update()`
- `async delete()`
- `async bulk_create()`
- `async exists()`
- `async search()`

*Source: /home/dotmac_framework/src/dotmac_management/repositories/base.py*

## dotmac_management.repositories.billing

Billing repository for subscription and payment operations.

### Classes

#### PricingPlanRepository

Repository for pricing plan operations.

**Methods:**

- `__init__()`
- `async get_by_slug()`
- `async get_active_plans()`
- `async get_by_stripe_price_id()`

#### SubscriptionRepository

Repository for subscription operations.

**Methods:**

- `__init__()`
- `async get_by_tenant()`
- `async get_active_subscription()`
- `async get_by_stripe_id()`
- `async get_expiring_trials()`
- `async get_subscriptions_for_renewal()`
- `async update_usage()`

#### InvoiceRepository

Repository for invoice operations.

**Methods:**

- `__init__()`
- `async get_by_number()`
- `async get_by_subscription()`
- `async get_overdue_invoices()`
- `async get_unpaid_invoices()`
- `async generate_invoice_number()`
- `async mark_as_paid()`

#### PaymentRepository

Repository for payment operations.

**Methods:**

- `__init__()`
- `async get_by_invoice()`
- `async get_by_stripe_payment_intent()`
- `async get_successful_payments()`
- `async get_failed_payments()`
- `async calculate_revenue()`

#### UsageRecordRepository

Repository for usage-based billing records.

**Methods:**

- `__init__()`
- `async get_unbilled_usage()`
- `async mark_as_billed()`
- `async get_usage_summary()`

#### CommissionRepository

Repository for reseller commission operations.

**Methods:**

- `__init__()`
- `async get_by_reseller()`
- `async get_unpaid_commissions()`
- `async calculate_total_commission()`
- `async approve_commissions()`
- `async mark_as_paid()`

*Source: /home/dotmac_framework/src/dotmac_management/repositories/billing.py*

## dotmac_management.repositories.billing_additional

Additional billing repository methods that are expected by the service layer.

### Classes

#### BillingPlanRepository

Repository for billing plan operations.

**Methods:**

- `__init__()`

#### PricingPlanRepository

Repository for pricing plan operations (alias for BillingPlanRepository).

**Methods:**

- `__init__()`

#### SubscriptionRepository

Repository for subscription operations.

**Methods:**

- `__init__()`
- `async get_active_subscription()`
- `async get_with_plan()`
- `async update_status()`
- `async get_expiring_subscriptions()`
- `async get_usage_based_subscriptions()`
- `async count_active_subscriptions()`

#### InvoiceRepository

Repository for invoice operations.

**Methods:**

- `__init__()`
- `async update_status()`
- `async get_overdue_invoices()`
- `async get_tenant_invoices()`
- `async get_unpaid_invoices()`
- `async get_tenant_invoices_for_period()`

#### PaymentRepository

Repository for payment operations.

**Methods:**

- `__init__()`
- `async update_status()`
- `async get_tenant_payments()`
- `async get_pending_payments()`
- `async get_payments_in_period()`
- `async get_tenant_payments_for_period()`

#### UsageRecordRepository

Repository for usage record operations.

**Methods:**

- `__init__()`
- `async get_period_usage()`
- `async get_period_usage_detailed()`
- `async get_tenant_usage_for_period()`

*Source: /home/dotmac_framework/src/dotmac_management/repositories/billing_additional.py*

## dotmac_management.repositories.customer

Customer repository for customer management operations.

### Classes

#### CustomerRepository

Repository for customer operations.

**Methods:**

- `__init__()`
- `async get_by_email()`
- `async get_tenant_customers()`
- `async get_customer_metrics()`
- `async get_customer_with_services()`
- `async get_customer_services()`
- `async get_customer_usage_summary()`

#### CustomerServiceRepository

Repository for customer service operations.

**Methods:**

- `__init__()`
- `async get_service_usage_stats()`

*Source: /home/dotmac_framework/src/dotmac_management/repositories/customer.py*

## dotmac_management.repositories.deployment

Deployment repository implementations.

### Classes

#### InfrastructureTemplateRepository

Repository for infrastructure template operations.

**Methods:**

- `__init__()`

#### DeploymentRepository

Repository for deployment operations.

**Methods:**

- `__init__()`

*Source: /home/dotmac_framework/src/dotmac_management/repositories/deployment.py*

## dotmac_management.repositories.deployment_additional

Additional deployment repository methods.

### Classes

#### DeploymentTemplateRepository

Repository for deployment template operations.

**Methods:**

- `__init__()`

#### InfrastructureRepository

Repository for infrastructure operations.

**Methods:**

- `__init__()`
- `async update_status()`
- `async get_by_tenant_and_environment()`
- `async get_by_tenant()`
- `async get_active_infrastructure()`

#### DeploymentRepository

Repository for deployment operations.

**Methods:**

- `__init__()`
- `async update_status()`
- `async get_with_relations()`
- `async get_by_infrastructure()`
- `async get_by_tenant()`
- `async get_old_failed_deployments()`

*Source: /home/dotmac_framework/src/dotmac_management/repositories/deployment_additional.py*

## dotmac_management.repositories.monitoring

Monitoring repository for health checks, alerts, and SLA tracking.

### Classes

#### MonitoringRepository

Repository for monitoring operations.

**Methods:**

- `__init__()`
- `async get_tenant_health_checks()`
- `async get_active_alerts()`
- `async get_latest_sla_record()`
- `async get_tenant_metrics()`
- `async record_health_check()`
- `async record_metric()`
- `async create_alert()`
- `async resolve_alert()`
- `async get_tenant_alert_summary()`

#### HealthCheckRepository

Repository for health check operations.

**Methods:**

- `__init__()`

#### MetricRepository

Repository for metric operations.

**Methods:**

- `__init__()`
- `async get_metrics_aggregate()`

#### AlertRepository

Repository for alert operations.

**Methods:**

- `__init__()`
- `async get_alert_history()`

#### SLARecordRepository

Repository for SLA record operations.

**Methods:**

- `__init__()`
- `async get_sla_history()`
- `async get_sla_compliance_summary()`

*Source: /home/dotmac_framework/src/dotmac_management/repositories/monitoring.py*

## dotmac_management.repositories.plugin

Plugin repository implementations.

### Classes

#### PluginCategoryRepository

Repository for plugin category operations.

**Methods:**

- `__init__()`

#### PluginRepository

Repository for plugin operations.

**Methods:**

- `__init__()`

#### PluginLicenseRepository

Repository for plugin license operations.

**Methods:**

- `__init__()`

*Source: /home/dotmac_framework/src/dotmac_management/repositories/plugin.py*

## dotmac_management.repositories.plugin_additional

Additional plugin repository methods.

### Classes

#### PluginRepository

Repository for plugin operations.

**Methods:**

- `__init__()`
- `async get_by_name()`
- `async increment_download_count()`
- `async update_rating()`
- `async search_plugins()`
- `async count_search_results()`

#### PluginLicenseRepository

Repository for plugin license operations.

**Methods:**

- `__init__()`
- `async get_by_tenant_and_plugin()`
- `async get_with_plugin()`
- `async get_by_tenant()`
- `async get_by_plugin()`
- `async update_status()`
- `async get_auto_update_enabled()`

#### PluginUsageRepository

Repository for plugin usage tracking.

**Methods:**

- `__init__()`
- `async get_by_license()`
- `async get_by_plugin()`

#### PluginInstallationRepository

Alias for PluginLicense repository - installations are managed via licenses.

**Methods:**

- `__init__()`
- `async get_by_tenant_and_plugin()`

#### PluginResourceUsageRepository

Repository for plugin resource usage tracking.

**Methods:**

- `__init__()`
- `async get_resource_usage_by_license()`
- `async get_resource_usage_by_plugin()`

#### PluginSecurityScanRepository

Repository for plugin security scan operations.

**Methods:**

- `__init__()`
- `async get_plugins_for_security_scan()`
- `async update_security_status()`

#### PluginVersionRepository

Repository for plugin version management.

**Methods:**

- `__init__()`
- `async get_plugin_versions()`
- `async get_latest_version()`
- `async check_compatibility()`

*Source: /home/dotmac_framework/src/dotmac_management/repositories/plugin_additional.py*

## dotmac_management.repositories.tenant

Tenant repository for multi-tenant operations.

### Classes

#### TenantRepository

Repository for tenant operations.

**Methods:**

- `__init__()`
- `async get_by_name()`
- `async get_by_slug()`
- `async get_by_domain()`
- `async get_with_configurations()`
- `async get_active_tenants()`
- `async get_tenants_by_status()`
- `async search_tenants()`
- `async get_tenants_with_relationships()`
- `async get_tenants_summary_bulk()`
- `async get_tenant_count_by_status()`
- `async update_status()`
- `async check_slug_availability()`

#### TenantConfigurationRepository

Repository for tenant configuration operations.

**Methods:**

- `__init__()`
- `async get_tenant_configurations()`
- `async get_configuration_by_key()`
- `async upsert_configuration()`
- `async bulk_update_configurations()`

#### TenantInvitationRepository

Repository for tenant invitation operations.

**Methods:**

- `__init__()`
- `async get_by_token()`
- `async get_tenant_invitations()`
- `async get_invitations_by_email()`
- `async accept_invitation()`

#### TenantUsageRepository

Repository for tenant usage records.

**Methods:**

- `__init__()`
- `async get_latest_usage()`
- `async get_usage_range()`
- `async record_usage()`

*Source: /home/dotmac_framework/src/dotmac_management/repositories/tenant.py*

## dotmac_management.repositories.user

User repository for authentication and user management.

### Classes

#### UserRepository

Repository for user operations.

**Methods:**

- `__init__()`
- `async get_by_email()`
- `async get_by_username()`
- `async get_active_users()`
- `async get_users_by_role()`
- `async update_last_login()`
- `async increment_failed_login()`
- `async lock_user()`
- `async unlock_user()`

#### UserSessionRepository

Repository for user session operations.

**Methods:**

- `__init__()`
- `async get_by_token()`
- `async get_active_sessions()`
- `async revoke_all_sessions()`
- `async cleanup_expired_sessions()`

#### UserInvitationRepository

Repository for user invitation operations.

**Methods:**

- `__init__()`
- `async get_by_token()`
- `async get_pending_invitations()`
- `async get_invitations_by_email()`
- `async accept_invitation()`
- `async cleanup_expired_invitations()`

*Source: /home/dotmac_framework/src/dotmac_management/repositories/user.py*

## dotmac_management.schemas.__init__

Pydantic schemas for request/response validation.

*Source: /home/dotmac_framework/src/dotmac_management/schemas/__init__.py*

## dotmac_management.schemas.admin

Admin dashboard schemas for validation and serialization.

### Classes

#### TenantStats

Tenant statistics schema.

#### UserStats

User statistics schema.

#### SubscriptionStats

Subscription statistics schema.

#### RevenueStats

Revenue statistics schema.

#### InfrastructureStats

Infrastructure statistics schema.

#### NotificationStats

Notification statistics schema.

#### AdminDashboardStats

Main admin dashboard statistics schema.

#### TenantOverview

Tenant overview schema.

#### UserOverview

User overview schema.

#### SystemComponentHealth

System component health schema.

#### SystemHealth

Overall system health schema.

#### UserActivity

User activity schema.

#### RevenueMetrics

Revenue metrics schema.

#### InfrastructureMetrics

Infrastructure metrics schema.

#### NotificationMetrics

Notification metrics schema.

#### ActivityLog

Activity log entry schema.

#### PaginatedActivityLogs

Paginated activity logs schema.

#### TenantActionRequest

Tenant action request schema.

#### TenantActionResponse

Tenant action response schema.

#### SystemMetrics

System-wide metrics schema.

#### AlertConfiguration

Alert configuration schema.

#### Alert

Alert with database fields.

#### AlertHistory

Alert history entry schema.

#### MaintenanceWindow

Maintenance window schema.

#### BackupStatus

Backup status schema.

#### SecurityEvent

Security event schema.

#### PerformanceMetrics

Performance metrics schema.

#### ConfigurationChange

Configuration change schema.

*Source: /home/dotmac_framework/src/dotmac_management/schemas/admin.py*

## dotmac_management.schemas.analytics

Analytics and reporting schemas for validation and serialization.

### Classes

#### AnalyticsTimeframe

Analytics timeframe options.

#### MetricType

Metric types for analytics.

#### ReportFormat

Report output formats.

#### ChartType

Chart types for visualization.

#### AnalyticsFilter

Analytics filter schema.

**Methods:**

- `validate_operator()`

#### AnalyticsQuery

Analytics query schema.

**Methods:**

- `validate_dates()`

#### TimeSeriesDataPoint

Time series data point schema.

#### MetricSummary

Metric summary schema.

#### KPI

Key Performance Indicator schema.

#### TenantAnalytics

Tenant analytics schema.

#### UserAnalytics

User analytics schema.

#### RevenueAnalytics

Revenue analytics schema.

#### UsageAnalytics

Usage analytics schema.

#### PerformanceMetrics

Performance metrics schema.

#### CustomReport

Custom report schema.

#### ReportSchedule

Report schedule schema.

#### AnalyticsDashboard

Analytics dashboard schema.

#### DashboardWidget

Dashboard widget schema.

#### ExportRequest

Data export request schema.

#### ExportJob

Data export job schema.

#### AnalyticsAlert

Analytics alert schema.

#### AlertTrigger

Alert trigger event schema.

#### MetricDefinition

Metric definition schema.

#### DataSource

Data source schema for analytics.

#### AnalyticsConfig

Analytics configuration schema.

#### AnalyticsInsight

Analytics insight schema.

#### AnalyticsSummary

Analytics summary schema.

*Source: /home/dotmac_framework/src/dotmac_management/schemas/analytics.py*

## dotmac_management.schemas.api_docs

API documentation schemas for validation and serialization.

### Classes

#### SDKLanguage

Supported SDK languages.

#### DocumentationFormat

Documentation output formats.

#### APIEndpointMethod

HTTP methods for API endpoints.

#### APIEndpoint

API endpoint schema.

#### CodeSample

Code sample schema.

#### APIDocumentation

API documentation schema.

#### SDKDocumentation

SDK documentation schema.

#### DeveloperGuide

Developer guide schema.

#### GuideSection

Guide section schema.

#### ChangelogEntry

Changelog entry schema.

#### ChangelogChange

Individual changelog change schema.

#### PostmanCollection

Postman collection schema.

#### OpenAPISpec

OpenAPI specification schema.

#### InteractiveDocsConfig

Interactive documentation configuration schema.

#### APIExample

API example schema.

#### APIMetrics

API usage metrics schema.

#### DeveloperResource

Developer resource schema.

#### APITestCase

API test case schema.

#### DocumentationFeedback

Documentation feedback schema.

#### APIDocumentationRequest

API documentation generation request schema.

#### SDKGenerationRequest

SDK generation request schema.

#### DocumentationStats

Documentation statistics schema.

*Source: /home/dotmac_framework/src/dotmac_management/schemas/api_docs.py*

## dotmac_management.schemas.billing

Billing and subscription schemas for validation and serialization.

### Classes

#### StripeCustomerCreate

Schema for creating Stripe customer.

#### StripeSubscriptionCreate

Schema for creating Stripe subscription.

#### StripeWebhookEvent

Schema for Stripe webhook events.

#### PaymentIntentCreate

Schema for creating payment intent.

#### PaymentIntentResponse

Schema for payment intent response.

#### BillingPlanBase

#### BillingPlanCreate

#### BillingPlanUpdate

#### BillingPlan

#### PricingPlanBase

Base schema for pricing plans.

#### PricingPlanCreate

Schema for creating a pricing plan.

#### PricingPlanUpdate

Schema for updating a pricing plan.

#### PricingPlan

Schema for pricing plan response.

#### SubscriptionBase

#### SubscriptionCreate

#### SubscriptionUpdate

#### Subscription

#### InvoiceBase

#### InvoiceCreate

#### InvoiceUpdate

#### Invoice

#### InvoiceLineItemBase

#### InvoiceLineItemCreate

#### InvoiceLineItem

#### PaymentBase

#### PaymentCreate

#### PaymentUpdate

#### Payment

#### UsageRecordBase

#### UsageRecordCreate

#### UsageRecord

#### BillingPlanListResponse

#### SubscriptionListResponse

#### InvoiceListResponse

#### PaymentListResponse

#### UsageRecordListResponse

#### BillingAnalytics

#### TenantBillingOverview

*Source: /home/dotmac_framework/src/dotmac_management/schemas/billing.py*

## dotmac_management.schemas.deployment

Deployment and infrastructure schemas for validation and serialization.

### Classes

#### DeploymentTemplateBase

#### DeploymentTemplateCreate

#### DeploymentTemplateUpdate

#### DeploymentTemplate

#### InfrastructureBase

#### InfrastructureCreate

#### InfrastructureUpdate

#### Infrastructure

#### DeploymentBase

#### DeploymentCreate

#### DeploymentUpdate

#### Deployment

#### ServiceInstanceBase

#### ServiceInstanceCreate

#### ServiceInstanceUpdate

#### ServiceInstance

#### DeploymentLogBase

#### DeploymentLogCreate

#### DeploymentLog

#### DeploymentTemplateListResponse

#### InfrastructureListResponse

#### DeploymentListResponse

#### ServiceInstanceListResponse

#### DeploymentLogListResponse

#### DeploymentRequest

#### ScalingRequest

#### RollbackRequest

#### DeploymentStatus

#### InfrastructureHealth

#### TenantDeploymentOverview

*Source: /home/dotmac_framework/src/dotmac_management/schemas/deployment.py*

## dotmac_management.schemas.monitoring

Monitoring and observability schemas for validation and serialization.

### Classes

#### MetricBase

#### MetricCreate

#### Metric

#### AlertRuleBase

#### AlertRuleCreate

#### AlertRuleUpdate

#### AlertRule

#### AlertBase

#### AlertCreate

#### AlertUpdate

#### Alert

#### NotificationChannelBase

#### NotificationChannelCreate

#### NotificationChannelUpdate

#### NotificationChannel

#### NotificationBase

#### NotificationCreate

#### NotificationUpdate

#### Notification

#### DashboardBase

#### DashboardCreate

#### DashboardUpdate

#### Dashboard

#### LogEntryBase

#### LogEntryCreate

#### LogEntry

#### MetricListResponse

#### AlertRuleListResponse

#### AlertListResponse

#### NotificationChannelListResponse

#### NotificationListResponse

#### DashboardListResponse

#### LogEntryListResponse

#### MetricQuery

#### MetricQueryResult

#### MetricQueryResponse

#### LogQuery

#### ServiceHealthStatus

#### TenantMonitoringOverview

#### SyntheticCheckBase

#### SyntheticCheckCreate

#### SyntheticCheckUpdate

#### SyntheticCheck

#### SyntheticCheckResultBase

#### SyntheticCheckResultCreate

#### SyntheticCheckResult

*Source: /home/dotmac_framework/src/dotmac_management/schemas/monitoring.py*

## dotmac_management.schemas.plugin

Plugin system schemas for validation and serialization.

### Classes

#### PluginBase

#### PluginCreate

#### PluginUpdate

#### Plugin

#### PluginInstallationBase

#### PluginInstallationCreate

#### PluginInstallationUpdate

#### PluginInstallation

#### PluginHookBase

#### PluginHookCreate

#### PluginHookUpdate

#### PluginHook

#### PluginReviewBase

#### PluginReviewCreate

#### PluginReviewUpdate

#### PluginReview

#### PluginEventBase

#### PluginEventCreate

#### PluginEvent

#### PluginListResponse

#### PluginInstallationListResponse

#### PluginHookListResponse

#### PluginReviewListResponse

#### PluginEventListResponse

#### PluginInstallRequest

#### PluginUpdateRequest

#### PluginConfigurationUpdate

#### BulkPluginOperation

#### PluginSearchFilters

#### PluginSearchRequest

#### PluginAnalytics

#### TenantPluginOverview

#### PluginSubmission

#### PluginValidationResult

*Source: /home/dotmac_framework/src/dotmac_management/schemas/plugin.py*

## dotmac_management.schemas.portal

Tenant portal schemas for validation and serialization.

### Classes

#### TenantProfile

Tenant profile schema.

#### TenantProfileUpdate

Tenant profile update schema.

#### UserInvitation

User invitation schema.

#### UserProfile

User profile schema.

#### SubscriptionInfo

Subscription information schema.

#### InvoiceInfo

Invoice information schema.

#### PaymentInfo

Payment information schema.

#### BillingOverview

Billing overview schema.

#### UsageMetric

Usage metric schema.

#### UsageMetrics

Usage metrics collection schema.

#### InfrastructureDeployment

Infrastructure deployment schema.

#### NotificationTemplate

Notification template schema.

#### ActivityItem

Activity item schema.

#### PortalDashboard

Portal dashboard schema.

#### SupportTicket

Support ticket schema.

#### SupportTicketResponse

Support ticket response schema.

#### NotificationSettings

Notification settings schema.

#### SecuritySettings

Security settings schema.

#### BillingSettings

Billing settings schema.

#### InfrastructureSettings

Infrastructure settings schema.

#### ServiceConfiguration

Service configuration schema.

#### ApiKey

API key schema.

#### ApiKeyCreate

API key creation schema.

#### ApiKeyResponse

API key response schema.

#### WebhookEndpoint

Webhook endpoint schema.

#### WebhookEndpointCreate

Webhook endpoint creation schema.

#### WebhookDelivery

Webhook delivery schema.

#### BackupInfo

Backup information schema.

#### BackupCreate

Backup creation schema.

#### AuditLog

Audit log entry schema.

#### AuditLogQuery

Audit log query parameters.

#### TeamMember

Team member schema.

#### TeamInvitation

Team invitation schema.

#### RolePermissions

Role permissions schema.

#### TenantSettings

Tenant settings schema.

#### QuotaUsage

Quota usage schema.

#### QuotaOverview

Quota overview schema.

*Source: /home/dotmac_framework/src/dotmac_management/schemas/portal.py*

## dotmac_management.schemas.tenant

Tenant schemas aligned with database migration schema.

### Classes

#### TenantBase

Base tenant schema matching database schema.

#### TenantCreate

Schema for creating a new tenant.

**Methods:**

- `validate_name()`
- `validate_contact_email()`
- `validate_contact_name()`
- `validate_slug()`

#### TenantUpdate

Schema for updating tenant information.

**Methods:**

- `validate_name()`
- `validate_contact_email()`
- `validate_contact_name()`

#### TenantResponse

Tenant response schema.

#### TenantListResponse

Tenant list response schema.

#### TenantStatusUpdate

Schema for updating tenant status.

#### TenantConfigurationBase

Base tenant configuration schema.

#### TenantConfigurationCreate

Schema for creating tenant configuration.

#### TenantConfigurationUpdate

Schema for updating tenant configuration.

#### TenantConfigurationResponse

Tenant configuration response schema.

#### TenantInvitationCreate

Schema for tenant invitation.

#### TenantInvitationResponse

Tenant invitation response schema.

#### TenantOnboardingRequest

Schema for tenant onboarding.

#### TenantOnboardingResponse

Tenant onboarding response schema.

#### TenantSummary

Tenant summary for dashboard.

*Source: /home/dotmac_framework/src/dotmac_management/schemas/tenant.py*

## dotmac_management.schemas.user

User schemas for authentication and user management.

### Classes

#### UserBase

Base user schema.

#### UserCreate

Schema for creating a new user.

#### UserUpdate

Schema for updating user information.

#### UserPasswordUpdate

Schema for password update.

#### UserResponse

User response schema.

#### UserLogin

User login schema.

#### UserLoginResponse

Login response schema.

#### TokenRefresh

Token refresh schema.

#### UserInvitationCreate

Schema for creating user invitation.

#### UserInvitationResponse

User invitation response schema.

#### UserInvitationAccept

Schema for accepting user invitation.

#### UserProfileUpdate

Schema for user profile updates.

#### TwoFactorSetup

Schema for two-factor authentication setup.

#### UserSessionResponse

User session response schema.

#### UserListResponse

User list response schema.

#### ForgotPassword

Forgot password schema.

#### ResetPassword

Reset password schema.

#### ChangeEmail

Change email schema.

#### UserPermissions

User permissions schema.

#### UserActivity

User activity log schema.

*Source: /home/dotmac_framework/src/dotmac_management/schemas/user.py*

## dotmac_management.schemas.user_management

User management schemas for validation and serialization.

### Classes

#### UserCreate

User creation schema.

**Methods:**

- `validate_role()`

#### UserUpdate

User update schema.

**Methods:**

- `validate_role()`

#### UserInvite

User invitation schema.

**Methods:**

- `validate_role()`

#### UserInviteResponse

User invitation response schema.

#### AcceptInvitation

Accept invitation schema.

#### PasswordReset

Password reset schema.

#### PasswordChange

Password change schema.

#### UserStatus

User status schema.

#### UserProfile

User profile schema.

#### RoleDefinition

Role definition schema.

#### PermissionDefinition

Permission definition schema.

#### PermissionAssignment

Permission assignment schema.

#### PermissionRevocation

Permission revocation schema.

#### RoleCreate

Role creation schema (for custom roles).

#### RoleUpdate

Role update schema.

#### UserSession

User session schema.

#### UserActivity

User activity schema.

#### UserLoginAttempt

User login attempt schema.

#### UserAuditLog

User audit log schema.

#### UserSecuritySettings

User security settings schema.

#### TwoFactorSetup

Two-factor authentication setup schema.

#### TwoFactorVerification

Two-factor authentication verification schema.

#### ApiKeyCreate

API key creation schema.

#### ApiKey

API key schema.

#### ApiKeyResponse

API key creation response schema.

#### UserBulkOperation

Bulk user operation schema.

#### UserBulkOperationResult

Bulk user operation result schema.

#### UserImport

User import schema.

#### UserImportResult

User import result schema.

#### UserExport

User export schema.

#### UserStatistics

User statistics schema.

*Source: /home/dotmac_framework/src/dotmac_management/schemas/user_management.py*

## dotmac_management.services.__init__

Service layer for business logic.

*Source: /home/dotmac_framework/src/dotmac_management/services/__init__.py*

## dotmac_management.services.application_orchestrator

Multi-application orchestration extension for existing TenantProvisioningService.

Extends the proven provisioning workflow to support multiple applications within
a single tenant container, leveraging existing infrastructure and deployment patterns.

### Classes

#### MultiAppProvisioningStage

Extended provisioning stages for multi-application deployment.

#### ApplicationDeploymentResult

Result of deploying a single application.

**Methods:**

- `success()`
- `failed()`

#### MultiAppProvisioningResult

Extended result for multi-application tenant provisioning.

**Methods:**

- `get_successful_deployments()`
- `get_failed_deployments()`
- `get_deployment_summary()`

#### EnhancedTenantProvisioningService

Enhanced tenant provisioning service with multi-application support.

Extends the existing TenantProvisioningService to support deploying
multiple applications within a single tenant container while maintaining
all existing functionality and patterns.

**Methods:**

- `__init__()`
- `async provision_multi_app_tenant()`
- `async add_application_to_existing_tenant()`
- `async _validate_multi_app_configuration()`
- `async _deploy_shared_services()`
- `async _deploy_applications_in_order()`
- `async _deploy_single_application_with_existing_provisioner()`
- `async _configure_inter_app_networking()`

*Source: /home/dotmac_framework/src/dotmac_management/services/application_orchestrator.py*

## dotmac_management.services.enhanced_tenant_service

Enhanced Tenant Service with multi-application support.

Extends the existing TenantService to support multi-application tenant configurations
while maintaining full backward compatibility with existing functionality.

### Classes

#### EnhancedTenantService

Service layer - exceptions bubble up to router @standard_exception_handler.

**Methods:**

- `__init__()`
- `async create_multi_app_tenant()`
- `async add_application_to_tenant()`
- `async get_tenant_applications()`
- `async remove_application_from_tenant()`
- `async get_service_registry_status()`
- `async _store_multi_app_configuration()`
- `async _get_multi_app_configuration()`
- `async _add_application_to_tenant_config()`
- `async _remove_application_from_tenant_config()`

*Source: /home/dotmac_framework/src/dotmac_management/services/enhanced_tenant_service.py*

## dotmac_management.shared.__init__

Shared utilities and base classes for management platform.

*Source: /home/dotmac_framework/src/dotmac_management/shared/__init__.py*

## dotmac_management.shared.base_service

Shared base service following ISP Framework standardization patterns.

### Classes

#### BaseManagementService

Service layer - exceptions bubble up to router @standard_exception_handler.

**Methods:**

- `__init__()`
- `async _validate_create_rules()`
- `async _validate_update_rules()`
- `async _validate_delete_rules()`
- `async _post_create_hook()`
- `async _post_update_hook()`
- `async _post_delete_hook()`
- `async _pre_create_hook()`
- `async _pre_update_hook()`
- `async create()`
- `async get_by_id()`
- `async update()`
- `async delete()`
- `async list()`
- `async count()`
- `async exists()`

*Source: /home/dotmac_framework/src/dotmac_management/shared/base_service.py*

## dotmac_management.workers.__init__

Background workers for asynchronous task processing.

*Source: /home/dotmac_framework/src/dotmac_management/workers/__init__.py*

## dotmac_management.workers.tasks.__init__

Background task modules.

*Source: /home/dotmac_framework/src/dotmac_management/workers/tasks/__init__.py*

## dotmac_network_visualization.__init__

DotMac Network Visualization Package

A comprehensive network topology mapping and visualization framework with GIS integration,
NetworkX graph processing, and interactive network representation tools.

This package provides:

- Graph-based network topology representation
- NetworkX integration for advanced graph algorithms
- GIS coordinate-based distance calculations
- Network resilience and critical infrastructure analysis
- Visual network representation tools
- Multi-tenant network topology management

*Source: /home/dotmac_framework/src/dotmac_network_visualization/__init__.py*

## dotmac_network_visualization.core.__init__

Core network topology and graph processing components.

*Source: /home/dotmac_framework/src/dotmac_network_visualization/core/__init__.py*

## dotmac_network_visualization.exceptions

Exception hierarchy for DotMac Network Visualization package.

### Classes

#### NetworkVisualizationError

Base exception for network visualization package.

#### TopologyError

Exception for topology-related errors.

#### GraphError

Exception for graph processing errors.

#### GISError

Exception for GIS and coordinate system errors.

#### VisualizationError

Exception for visualization rendering errors.

#### NetworkXError

Exception for NetworkX integration errors.

#### CacheError

Exception for caching-related errors.

#### TenantError

Exception for tenant isolation errors.

*Source: /home/dotmac_framework/src/dotmac_network_visualization/exceptions.py*

## dotmac_network_visualization.gis.__init__

GIS integration components for network topology mapping.

*Source: /home/dotmac_framework/src/dotmac_network_visualization/gis/__init__.py*

## dotmac_network_visualization.gis.coordinate_utils

GIS coordinate utilities and distance calculations.

### Classes

#### CoordinateSystem

Supported coordinate systems.

#### GISUtils

GIS utility functions for network topology mapping.

**Methods:**

- `validate_coordinates()`
- `normalize_coordinates()`
- `degrees_to_radians()`
- `radians_to_degrees()`
- `calculate_bearing()`
- `calculate_midpoint()`

#### DistanceCalculator

Advanced distance calculations for network topology.

**Methods:**

- `haversine_distance()`
- `euclidean_distance()`
- `calculate_distance_matrix()`
- `find_nearest_locations()`
- `calculate_coverage_area()`

*Source: /home/dotmac_framework/src/dotmac_network_visualization/gis/coordinate_utils.py*

## dotmac_network_visualization.visualization.__init__

Network visualization and rendering components.

*Source: /home/dotmac_framework/src/dotmac_network_visualization/visualization/__init__.py*

## dotmac_sdk.__init__

DotMac Framework Python SDK

Official Python SDK for the DotMac Platform API.

### Classes

#### _LegacyDotMacClient

Main client for DotMac Platform API.

**Methods:**

- `__init__()`
- `request()`

#### CustomerService

Customer management operations.

**Methods:**

- `__init__()`
- `create()`
- `get()`
- `list()`
- `update()`
- `activate()`
- `suspend()`
- `delete()`

#### InvoiceService

Invoice and billing operations.

**Methods:**

- `__init__()`
- `list()`
- `get()`
- `create()`

#### ServiceManagement

Service provisioning and management.

**Methods:**

- `__init__()`
- `list()`
- `provision()`
- `activate()`
- `suspend()`

#### NetworkService

Network management operations.

**Methods:**

- `__init__()`
- `get_status()`
- `list_devices()`
- `get_device()`

#### DotMacAPIError

Base exception for DotMac API errors.

#### AuthenticationError

Authentication failed.

#### RateLimitError

Rate limit exceeded.

#### ValidationError

Request validation failed.

*Source: /home/dotmac_framework/src/dotmac_sdk/__init__.py*

## dotmac_sdk.exceptions

DotMac SDK Exception Classes

### Classes

#### DotMacAPIError

Base exception for DotMac API errors.

#### DotMacAuthError

Authentication failed.

#### DotMacConfigError

Configuration error.

#### RateLimitError

Rate limit exceeded.

#### ValidationError

Request validation failed.

*Source: /home/dotmac_framework/src/dotmac_sdk/exceptions.py*

## dotmac_sdk.services

DotMac SDK Service Classes

Individual service clients for different API endpoints.

### Classes

#### CustomerService

Customer management operations.

**Methods:**

- `__init__()`
- `create()`
- `get()`
- `list()`

#### InvoiceService

Invoice and billing operations.

**Methods:**

- `__init__()`
- `list()`
- `get()`

#### ServiceManagement

Service provisioning and management.

**Methods:**

- `__init__()`
- `list()`

#### NetworkService

Network management operations.

**Methods:**

- `__init__()`
- `get_status()`
- `list_devices()`

*Source: /home/dotmac_framework/src/dotmac_sdk/services.py*

## dotmac_sdk_core.__init__

DotMac SDK Core - HTTP Client Framework with Observability

A comprehensive HTTP client framework for DotMac services providing:

- Standardized HTTP client with async/sync support
- Retry logic with exponential backoff
- Circuit breaker patterns for resilience
- OpenTelemetry observability and metrics
- Centralized error handling and logging
- Request/response middleware
- Authentication and tenant context

Author: DotMac Framework Team
License: MIT

*Source: /home/dotmac_framework/src/dotmac_sdk_core/__init__.py*

## dotmac_sdk_core.auth.__init__

Authentication providers for HTTP client.

*Source: /home/dotmac_framework/src/dotmac_sdk_core/auth/__init__.py*

## dotmac_sdk_core.auth.providers

Authentication providers for HTTP client.

### Classes

#### AuthProvider

Base authentication provider.

**Methods:**

- `get_auth_headers()`
- `is_valid()`

#### BearerTokenAuth

Bearer token authentication.

**Methods:**

- `__init__()`
- `get_auth_headers()`
- `is_valid()`

#### APIKeyAuth

API key authentication.

**Methods:**

- `__init__()`
- `get_auth_headers()`
- `is_valid()`

#### JWTAuth

JWT token authentication.

**Methods:**

- `__init__()`
- `get_auth_headers()`
- `is_valid()`

*Source: /home/dotmac_framework/src/dotmac_sdk_core/auth/providers.py*

## dotmac_sdk_core.client.__init__

HTTP client components for DotMac SDK Core.

*Source: /home/dotmac_framework/src/dotmac_sdk_core/client/__init__.py*

## dotmac_sdk_core.client.http_client

DotMac HTTP Client - Core HTTP client framework with observability and resilience.

Provides standardized HTTP communication for DotMac services with built-in:

- Async and sync client support
- Retry logic with configurable strategies
- Circuit breaker integration
- OpenTelemetry instrumentation
- Middleware pipeline
- Error handling and response parsing

### Classes

#### HTTPClientConfig

Configuration for DotMac HTTP client.

#### HTTPResponse

Standardized HTTP response wrapper.

**Methods:**

- `is_success()`
- `is_client_error()`
- `is_server_error()`

#### HTTPError

HTTP-specific error with response details.

**Methods:**

- `__init__()`

#### DotMacHTTPClient

DotMac HTTP client with observability and resilience features.

Provides both async and sync interfaces with standardized error handling,
retry logic, circuit breakers, and OpenTelemetry instrumentation.

**Methods:**

- `__init__()`
- `async __aenter__()`
- `async __aexit__()`
- `__enter__()`
- `__exit__()`
- `async close()`
- `close_sync()`
- `async request()`
- `request_sync()`
- `async _execute_request_async()`
- `async _apply_rate_limiting()`
- `async get()`
- `async post()`
- `async put()`
- `async patch()`
- `async delete()`
- `get_sync()`
- `post_sync()`
- `put_sync()`
- `patch_sync()`
- `delete_sync()`
- `async stream()`
- `get_circuit_breaker_stats()`

*Source: /home/dotmac_framework/src/dotmac_sdk_core/client/http_client.py*

## dotmac_sdk_core.middleware.__init__

HTTP middleware for request/response processing.

*Source: /home/dotmac_framework/src/dotmac_sdk_core/middleware/__init__.py*

## dotmac_sdk_core.middleware.base

Base HTTP middleware classes.

### Classes

#### HTTPMiddleware

Base HTTP middleware class.

**Methods:**

- `async process_request()`
- `async process_response()`

#### RequestMiddleware

Middleware that only processes requests.

**Methods:**

- `async process_response()`

#### ResponseMiddleware

Middleware that only processes responses.

**Methods:**

- `async process_request()`

*Source: /home/dotmac_framework/src/dotmac_sdk_core/middleware/base.py*

## dotmac_sdk_core.middleware.logging_middleware

Logging middleware for HTTP requests.

### Classes

#### LoggingMiddleware

HTTP request/response logging middleware.

**Methods:**

- `__init__()`
- `async process_request()`
- `async process_response()`

*Source: /home/dotmac_framework/src/dotmac_sdk_core/middleware/logging_middleware.py*

## dotmac_sdk_core.middleware.rate_limiting

Rate limiting middleware.

### Classes

#### RateLimitMiddleware

Client-side rate limiting middleware.

**Methods:**

- `__init__()`
- `async process_request()`

*Source: /home/dotmac_framework/src/dotmac_sdk_core/middleware/rate_limiting.py*

## dotmac_sdk_core.middleware.tenant_context

Tenant context middleware.

### Classes

#### TenantContextMiddleware

Middleware for handling tenant context.

**Methods:**

- `__init__()`
- `async process_request()`

*Source: /home/dotmac_framework/src/dotmac_sdk_core/middleware/tenant_context.py*

## dotmac_sdk_core.observability.__init__

Observability components for HTTP client.

*Source: /home/dotmac_framework/src/dotmac_sdk_core/observability/__init__.py*

## dotmac_sdk_core.observability.telemetry

Telemetry and metrics collection for HTTP client.

### Classes

#### TelemetryConfig

Configuration for telemetry collection.

#### HTTPMetrics

HTTP request metrics.

**Methods:**

- `__post_init__()`

#### SDKTelemetry

Basic telemetry collection for HTTP client.

**Methods:**

- `__init__()`
- `record_request()`
- `get_metrics()`

*Source: /home/dotmac_framework/src/dotmac_sdk_core/observability/telemetry.py*

## dotmac_sdk_core.observability.tracing

Tracing components for HTTP client.

### Classes

#### SpanAttributes

HTTP span attributes.

#### TraceableHTTPClient

HTTP client with tracing capabilities.

**Methods:**

- `__init__()`
- `async request()`

*Source: /home/dotmac_framework/src/dotmac_sdk_core/observability/tracing.py*

## dotmac_sdk_core.resilience.__init__

Resilience patterns for HTTP client including circuit breakers and retry strategies.

*Source: /home/dotmac_framework/src/dotmac_sdk_core/resilience/__init__.py*

## dotmac_sdk_core.resilience.circuit_breaker

Circuit Breaker Pattern Implementation

Provides resilient HTTP client communication by monitoring failures and
temporarily stopping requests when a service is unhealthy to prevent
cascade failures.

### Classes

#### CircuitBreakerState

Circuit breaker states.

#### CircuitBreakerError

Raised when circuit breaker is open.

**Methods:**

- `__init__()`

#### CircuitBreakerStats

Circuit breaker statistics.

#### CircuitBreaker

Circuit breaker implementation for HTTP clients.

Monitors request failures and transitions between states:

- CLOSED: Normal operation, requests proceed
- OPEN: Too many failures, requests blocked
- HALF_OPEN: Testing recovery, limited requests allowed

**Methods:**

- `__init__()`
- `state()`
- `is_closed()`
- `is_open()`
- `is_half_open()`
- `async call()`
- `call_sync()`
- `async _should_allow_request()`
- `async _record_success()`
- `async _record_failure()`
- `async _transition_to_open()`
- `async _transition_to_half_open()`
- `async _transition_to_closed()`
- `reset()`
- `get_stats()`

*Source: /home/dotmac_framework/src/dotmac_sdk_core/resilience/circuit_breaker.py*

## dotmac_sdk_core.resilience.retry_strategies

Retry Strategies for HTTP Client

Provides various retry strategies with configurable backoff algorithms
for resilient HTTP communication.

### Classes

#### RetryContext

Context information for retry attempts.

#### RetryStrategy

Abstract base class for retry strategies.

**Methods:**

- `should_retry()`
- `get_delay()`
- `get_max_attempts()`

#### ExponentialBackoffStrategy

Exponential backoff retry strategy.

Delay increases exponentially with each attempt:
delay = base_delay * (multiplier ^ attempt) + random jitter

**Methods:**

- `__init__()`
- `should_retry()`
- `get_delay()`

#### FixedDelayStrategy

Fixed delay retry strategy with optional jitter.

**Methods:**

- `__init__()`
- `should_retry()`
- `get_delay()`

#### LinearBackoffStrategy

Linear backoff retry strategy.

**Methods:**

- `__init__()`
- `should_retry()`
- `get_delay()`

#### CustomRetryStrategy

Custom retry strategy with user-defined logic.

Allows for complex retry logic based on response codes,
exception types, elapsed time, etc.

**Methods:**

- `__init__()`
- `should_retry()`
- `get_delay()`

#### AdaptiveRetryStrategy

Adaptive retry strategy that adjusts based on observed patterns.

Monitors success/failure rates and adapts retry behavior accordingly.

**Methods:**

- `__init__()`
- `should_retry()`
- `get_delay()`
- `record_outcome()`
- `get_stats()`

*Source: /home/dotmac_framework/src/dotmac_sdk_core/resilience/retry_strategies.py*

## dotmac_sdk_core.utils.__init__

Utility modules for DotMac SDK Core.

*Source: /home/dotmac_framework/src/dotmac_sdk_core/utils/__init__.py*

## dotmac_sdk_core.utils.request_builder

Request builder for constructing HTTP requests with DotMac conventions.

Provides standardized request construction with authentication,
tenant context, and DotMac-specific headers.

### Classes

#### RequestBuilder

Builds standardized HTTP requests for DotMac services.

Handles authentication, tenant context, headers, and request formatting
according to DotMac conventions.

**Methods:**

- `__init__()`
- `build_request()`
- `build_pagination_params()`
- `build_filter_params()`
- `build_include_params()`

*Source: /home/dotmac_framework/src/dotmac_sdk_core/utils/request_builder.py*

## dotmac_shared.__init__

DotMac Framework Shared Components

Cross-module utilities and common code for the DotMac Framework ecosystem.

*Source: /home/dotmac_framework/src/dotmac_shared/__init__.py*

## dotmac_shared.api.__init__

Shared API components for DRY patterns across the ISP framework.

*Source: /home/dotmac_framework/src/dotmac_shared/api/__init__.py*

## dotmac_shared.api.dependencies

Production-ready consolidated dependency injection patterns.
Enforces DRY principles with strict type safety and validation.

### Classes

#### StandardDependencies

Production-ready standard dependencies with validation.

**Methods:**

- `__init__()`

#### PaginatedDependencies

Standard dependencies with pagination support.

**Methods:**

- `__init__()`

#### SearchParams

Common search parameters used across multiple endpoints.

**Methods:**

- `__init__()`

#### FileUploadParams

Standard file upload parameters and validation.

**Methods:**

- `__init__()`

#### BulkOperationParams

Parameters for bulk operations with safety limits.

**Methods:**

- `__init__()`

*Source: /home/dotmac_framework/src/dotmac_shared/api/dependencies.py*

## dotmac_shared.application.__init__

Shared application factory for all DotMac platforms.

This module provides a unified way to create FastAPI applications with:

- Consistent startup/shutdown procedures
- Standardized middleware stacks
- Deployment-aware configuration
- Container optimization
- Multi-tenant isolation

*Source: /home/dotmac_framework/src/dotmac_shared/application/__init__.py*

## dotmac_shared.application.endpoints

Standard endpoints for all DotMac applications.

### Classes

#### StandardEndpoints

Standard endpoints that all DotMac applications should have.

**Methods:**

- `__init__()`
- `add_to_app()`

*Source: /home/dotmac_framework/src/dotmac_shared/application/endpoints.py*

## dotmac_shared.application.factory

Main application factory for DotMac platforms.

### Classes

#### DotMacApplicationFactory

Unified application factory for all DotMac platforms.

**Methods:**

- `__init__()`
- `async create_app()`
- `get_app()`
- `list_created_apps()`

#### DeploymentAwareApplicationFactory

Enhanced factory with deployment-specific optimizations.

**Methods:**

- `async create_tenant_container_app()`
- `async create_management_platform_app()`
- `async create_development_app()`

*Source: /home/dotmac_framework/src/dotmac_shared/application/factory.py*

## dotmac_shared.application.lifecycle

Standard lifecycle management for DotMac applications.

### Classes

#### StandardLifecycleManager

Standard lifecycle management for all DotMac applications.

**Methods:**

- `__init__()`
- `async lifespan()`
- `async _execute_startup_sequence()`
- `async _execute_startup_task()`
- `async _execute_shutdown_sequence()`
- `async _execute_shutdown_task()`
- `async _initialize_database()`
- `async _initialize_cache()`
- `async _initialize_observability()`
- `async _setup_health_checks()`
- `async _initialize_security()`
- `async _configure_tenant_isolation()`
- `async _initialize_ssl_manager()`
- `async _start_celery_monitoring()`
- `async _initialize_usage_reporting()`
- `async _initialize_plugin_system()`
- `async _start_tenant_monitoring()`
- `async _configure_kubernetes_client()`
- `async _initialize_websocket_manager()`
- `async _shutdown_observability()`
- `async _close_database()`
- `async _close_cache()`
- `async _shutdown_ssl_manager()`
- `async _shutdown_usage_reporting()`
- `async _shutdown_websocket_manager()`
- `async _shutdown_plugins()`
- `async _initialize_services()`
- `async _shutdown_services()`

*Source: /home/dotmac_framework/src/dotmac_shared/application/lifecycle.py*

## dotmac_shared.application.middleware

Standard middleware stack for all DotMac applications.

### Classes

#### StandardMiddlewareStack

Standard middleware stack applied to all DotMac applications.

**Methods:**

- `__init__()`
- `apply_to_app()`

*Source: /home/dotmac_framework/src/dotmac_shared/application/middleware.py*

## dotmac_shared.application.routing

Safe router registry system for deployment-aware applications.

### Classes

#### SafeRouterLoader

Safe router loading with validation and error handling.

**Methods:**

- `__init__()`
- `load_router()`

#### RouterRegistry

Central router registration system.

**Methods:**

- `__init__()`
- `register_all_routers()`
- `get_registration_report()`

*Source: /home/dotmac_framework/src/dotmac_shared/application/routing.py*

## dotmac_shared.auth.__init__

DotMac Shared Authentication Service

A comprehensive, secure authentication and authorization package for the DotMac framework.
Provides JWT token management, RBAC, session management, MFA, and multi-platform integration.

*Source: /home/dotmac_framework/src/dotmac_shared/auth/__init__.py*

## dotmac_shared.auth.adapters.__init__

Platform adapters.

This module contains adapters for integrating the authentication service
with different platforms in the DotMac framework:

- ISP Framework integration
- Management Platform integration

*Source: /home/dotmac_framework/src/dotmac_shared/auth/adapters/__init__.py*

## dotmac_shared.auth.adapters.isp_adapter

ISP Framework authentication adapter.

Placeholder implementation - will be completed in Week 4.

### Classes

#### ISPAuthAdapter

Authentication adapter for ISP Framework (placeholder).

**Methods:**

- `__init__()`
- `async authenticate_user()`
- `async get_user_permissions()`

*Source: /home/dotmac_framework/src/dotmac_shared/auth/adapters/isp_adapter.py*

## dotmac_shared.auth.adapters.management_adapter

Management Platform authentication adapter.

Placeholder implementation - will be completed in Week 4.

### Classes

#### ManagementAuthAdapter

Authentication adapter for Management Platform (placeholder).

**Methods:**

- `__init__()`
- `async authenticate_admin()`
- `async get_admin_permissions()`

*Source: /home/dotmac_framework/src/dotmac_shared/auth/adapters/management_adapter.py*

## dotmac_shared.auth.cache_integration

Cache Service Integration for Authentication

Provides integration layers between the authentication service components
and Developer A's cache service, enabling distributed session storage,
token blacklisting, and rate limiting.

### Classes

#### CacheServiceSessionStore

Session store implementation using Developer A's cache service.

Provides distributed session storage with tenant isolation,
automatic expiration, and high performance.

**Methods:**

- `__init__()`
- `async store_session()`
- `async get_session()`
- `async delete_session()`
- `async get_user_sessions()`
- `async cleanup_expired_sessions()`

#### CacheServiceTokenBlacklist

Token blacklisting implementation using Developer A's cache service.

Provides distributed token revocation for secure logout and
token invalidation across multiple application instances.

**Methods:**

- `__init__()`
- `async add_to_blacklist()`
- `async is_blacklisted()`
- `async remove_from_blacklist()`

#### CacheServiceRateLimitStore

Rate limiting store implementation using Developer A's cache service.

Provides distributed rate limiting with sliding windows,
account lockouts, and high-performance counters.

**Methods:**

- `__init__()`
- `async increment_counter()`
- `async get_counter()`
- `async reset_counter()`
- `async add_lockout()`
- `async is_locked_out()`
- `async remove_lockout()`
- `async get_rate_limit_stats()`

#### CacheIntegrationFactory

Factory for creating cache-integrated authentication components.

Provides a central place to create all cache-integrated components
with proper configuration and error handling.

**Methods:**

- `async create_integrated_components()`
- `async create_session_manager_with_cache()`
- `async create_jwt_manager_with_cache()`
- `async create_rate_limiter_with_cache()`

*Source: /home/dotmac_framework/src/dotmac_shared/auth/cache_integration.py*

## dotmac_shared.auth.core.__init__

Core authentication components.

This module contains the fundamental building blocks of the authentication system:

- JWT token management with RS256 security
- Role-based access control (RBAC)
- Session management
- Multi-factor authentication

*Source: /home/dotmac_framework/src/dotmac_shared/auth/core/__init__.py*

## dotmac_shared.auth.core.multi_factor

Multi-Factor Authentication (MFA) System

Implements comprehensive MFA support with:

- TOTP (Time-based One-Time Password) authentication
- SMS-based authentication support
- Backup codes generation and validation
- MFA enforcement policies
- Recovery mechanisms for lost devices
- QR code generation for authenticator apps

### Classes

#### MFAMethod

Multi-factor authentication methods.

#### MFAStatus

MFA status for users.

#### MFASecret

MFA secret container.

**Methods:**

- `to_dict()`
- `from_dict()`

#### BackupCode

Backup code for MFA recovery.

**Methods:**

- `use_code()`

#### MFAAttempt

MFA authentication attempt.

#### MFAProvider

Abstract MFA provider interface.

**Methods:**

- `async store_mfa_secret()`
- `async get_mfa_secret()`
- `async delete_mfa_secret()`
- `async store_backup_codes()`
- `async get_backup_codes()`
- `async log_mfa_attempt()`

#### SMSProvider

Abstract SMS provider interface.

**Methods:**

- `async send_sms()`

#### EmailProvider

Abstract email provider interface.

**Methods:**

- `async send_email()`

#### MFAManager

Multi-Factor Authentication Manager.

Features:

- TOTP authentication with QR code generation
- SMS-based authentication
- Backup codes for recovery
- MFA enforcement policies
- Attempt logging and rate limiting
- Device trust management

**Methods:**

- `__init__()`
- `generate_totp_secret()`
- `async setup_totp()`
- `generate_qr_code()`
- `async validate_totp()`
- `async send_sms_code()`
- `async validate_sms_code()`
- `generate_backup_codes()`
- `async setup_backup_codes()`
- `async validate_backup_code()`
- `async get_backup_codes_status()`
- `async get_mfa_status()`
- `async disable_mfa_method()`
- `async disable_all_mfa()`
- `async is_user_locked_out()`
- `async record_failed_attempt()`
- `clear_failed_attempts()`
- `async validate_mfa()`

*Source: /home/dotmac_framework/src/dotmac_shared/auth/core/multi_factor.py*

## dotmac_shared.auth.core.permissions

Role-Based Access Control (RBAC) System

Implements comprehensive RBAC with:

- Hierarchical permission system
- Tenant-scoped permissions
- Dynamic permission checking
- Role inheritance
- Resource-based access control

### Classes

#### Permission

System permissions following resource:action pattern.

**Methods:**

- `from_resource_action()`

#### Role

System roles with hierarchical structure.

#### PermissionScope

Defines the scope of a permission.

#### UserPermissions

User permission container.

**Methods:**

- `has_role()`
- `has_any_role()`
- `is_super_admin()`
- `is_tenant_admin()`

#### PermissionProvider

Abstract base class for permission providers.

**Methods:**

- `async get_user_permissions()`
- `async get_role_permissions()`
- `async check_resource_access()`

#### PermissionManager

Core permission management system.

Handles role-based access control with:

- Hierarchical roles and permissions
- Tenant isolation
- Resource-based access control
- Permission inheritance
- Dynamic permission evaluation

**Methods:**

- `__init__()`
- `get_role_permissions()`
- `get_user_effective_permissions()`
- `check_permission()`
- `check_multiple_permissions()`
- `can_access_tenant()`
- `get_accessible_tenants()`
- `validate_role_assignment()`
- `async get_user_permissions()`
- `clear_user_cache()`
- `get_permission_summary()`

*Source: /home/dotmac_framework/src/dotmac_shared/auth/core/permissions.py*

## dotmac_shared.auth.core.portal_auth

Portal authentication service for DotMac Framework.

This module provides portal-specific authentication with different access patterns
for admin, customer, technician, and reseller portals.

### Classes

#### PortalType

Portal types.

#### AuthenticationMethod

Authentication methods.

#### PortalConfig

Portal-specific configuration.

**Methods:**

- `__post_init__()`

#### AuthenticationContext

Authentication context for portal access.

#### PortalSession

Portal session information.

#### PortalAuthService

Portal-specific authentication service.

Manages authentication across different portals with specific
access controls and session management for each portal type.

**Methods:**

- `__init__()`
- `authenticate_portal_user()`
- `validate_portal_access()`
- `refresh_portal_session()`
- `logout_portal_user()`
- `get_portal_permissions_for_user()`
- `get_active_portal_sessions()`
- `update_portal_config()`
- `get_portal_config()`
- `cleanup_expired_sessions()`

*Source: /home/dotmac_framework/src/dotmac_shared/auth/core/portal_auth.py*

## dotmac_shared.auth.core.rbac_engine

RBAC (Role-Based Access Control) engine for DotMac Framework.

This module provides comprehensive role-based access control with hierarchical
permissions, multi-tenant support, and dynamic permission evaluation.

### Classes

#### AccessDecision

Access control decision.

#### AccessRequest

Access control request.

#### AccessResult

Access control result.

#### PolicyRule

Policy rule for access control.

**Methods:**

- `__init__()`
- `evaluate()`

#### TenantPolicy

Tenant-specific access policy.

**Methods:**

- `__init__()`
- `add_rule()`
- `remove_rule()`
- `evaluate()`

#### RBACEngine

Advanced RBAC engine with policy support.

Provides hierarchical role-based access control with:

- Multi-tenant permission isolation
- Dynamic policy evaluation
- Custom permission rules
- Audit logging
- Performance optimization

**Methods:**

- `__init__()`
- `check_access()`
- `has_permission()`
- `has_role()`
- `get_user_permissions_list()`
- `get_user_roles_list()`
- `add_tenant_policy()`
- `remove_tenant_policy()`
- `add_global_policy()`
- `remove_global_policy()`
- `grant_tenant_permission()`
- `revoke_tenant_permission()`
- `block_tenant_action()`
- `unblock_tenant_action()`
- `bulk_check_permissions()`
- `get_tenant_policy_summary()`
- `enable_cache()`
- `disable_cache()`
- `get_cache_stats()`

*Source: /home/dotmac_framework/src/dotmac_shared/auth/core/rbac_engine.py*

## dotmac_shared.auth.core.sessions

Session Management System

Implements secure session management with:

- Distributed session storage (Redis integration)
- Concurrent session handling
- Session timeout and cleanup
- Session hijacking protection
- Device/browser tracking
- Integration with cache service

### Classes

#### SessionStatus

Session status enumeration.

#### SessionInfo

Session information container.

**Methods:**

- `__post_init__()`
- `is_expired()`
- `is_active()`
- `time_until_expiry()`
- `to_dict()`
- `from_dict()`

#### DeviceInfo

Device information for session tracking.

**Methods:**

- `is_trusted()`

#### SessionStore

Abstract session storage interface.

**Methods:**

- `async store_session()`
- `async get_session()`
- `async delete_session()`
- `async get_user_sessions()`
- `async cleanup_expired_sessions()`

#### CacheServiceSessionStore

Session store implementation using cache service (Redis).

**Methods:**

- `__init__()`
- `async store_session()`
- `async get_session()`
- `async delete_session()`
- `async get_user_sessions()`
- `async cleanup_expired_sessions()`

#### InMemorySessionStore

In-memory session store for development/testing.

**Methods:**

- `__init__()`
- `async store_session()`
- `async get_session()`
- `async delete_session()`
- `async get_user_sessions()`
- `async cleanup_expired_sessions()`

#### SessionManager

Comprehensive session management system.

Features:

- Distributed session storage with Redis
- Concurrent session management
- Session security and hijacking protection
- Device tracking and trusted devices
- Automatic session cleanup
- Session analytics and monitoring

**Methods:**

- `__init__()`
- `async create_session()`
- `async get_session()`
- `async update_session_activity()`
- `async extend_session()`
- `async terminate_session()`
- `async terminate_all_user_sessions()`
- `async get_user_sessions()`
- `async validate_session_security()`
- `async cleanup_expired_sessions()`
- `async _enforce_session_limit()`
- `async _check_suspicious_activity()`

*Source: /home/dotmac_framework/src/dotmac_shared/auth/core/sessions.py*

## dotmac_shared.auth.core.tenant_security

Tenant security and multi-tenant isolation for DotMac Framework.

This module provides comprehensive tenant security including data isolation,
resource quotas, security policies, and tenant-specific access controls.

### Classes

#### TenantStatus

Tenant status.

#### SecurityLevel

Tenant security level.

#### IsolationLevel

Data isolation level.

#### ResourceQuota

Resource quota configuration.

#### SecurityPolicy

Tenant security policy.

#### TenantInfo

Tenant information.

#### DataAccessContext

Data access context for tenant isolation.

#### SecurityAuditEvent

Security audit event.

#### TenantSecurityService

Tenant security and isolation service.

Provides comprehensive multi-tenant security including:

- Data isolation and access controls
- Resource quota management
- Security policy enforcement
- Audit logging and compliance
- Threat detection and response

**Methods:**

- `__init__()`
- `register_tenant()`
- `get_tenant_info()`
- `validate_tenant_access()`
- `create_data_access_context()`
- `apply_tenant_isolation_filter()`
- `check_resource_quota()`
- `increment_resource_usage()`
- `decrement_resource_usage()`
- `update_security_policy()`
- `suspend_tenant()`
- `reactivate_tenant()`
- `get_tenant_audit_events()`
- `detect_suspicious_activity()`

*Source: /home/dotmac_framework/src/dotmac_shared/auth/core/tenant_security.py*

## dotmac_shared.auth.core.tokens

JWT Token Management with RS256 Security

Implements secure JWT token generation, validation, and management following
2024 security best practices including:

- RS256 algorithm with proper key management
- Automatic key rotation support
- Token blacklisting for secure logout
- Refresh token mechanism with rotation
- Comprehensive token validation

### Classes

#### TokenType

JWT token types.

#### TokenError

Base exception for token-related errors.

#### TokenExpiredError

Token has expired.

#### TokenInvalidError

Token is invalid.

#### TokenRevokedError

Token has been revoked.

#### TokenPair

Access and refresh token pair.

#### RSAKeyPair

RSA key pair for JWT signing.

#### JWTTokenManager

Secure JWT token manager using RS256 algorithm.

Features:

- RS256 signing with 2048-bit RSA keys
- Automatic key rotation support
- Token blacklisting for revocation
- Refresh token rotation
- JWKS endpoint support
- Comprehensive security validation

**Methods:**

- `__init__()`
- `generate_access_token()`
- `generate_refresh_token()`
- `generate_token_pair()`
- `validate_token()`
- `refresh_access_token()`
- `revoke_token()`
- `get_jwks()`
- `needs_key_rotation()`
- `export_keys()`

*Source: /home/dotmac_framework/src/dotmac_shared/auth/core/tokens.py*

## dotmac_shared.auth.current_user

Current user dependency injection for FastAPI applications.
Provides get_current_user and get_current_tenant functions.

*Source: /home/dotmac_framework/src/dotmac_shared/auth/current_user.py*

## dotmac_shared.auth.middleware.__init__

Authentication middleware.

This module contains middleware components for integrating authentication
with web frameworks and providing security features:

- FastAPI middleware integration
- Rate limiting and brute force protection
- Authentication audit logging

*Source: /home/dotmac_framework/src/dotmac_shared/auth/middleware/__init__.py*

## dotmac_shared.auth.middleware.audit_logging

Audit Logging Middleware

Implements comprehensive authentication audit logging:

- Authentication event logging
- Security event tracking
- Failed login attempt monitoring
- Suspicious activity detection
- Structured logging with metadata
- Configurable log levels and filters

### Classes

#### AuditEventType

Types of audit events.

#### AuditSeverity

Audit event severity levels.

#### AuditEvent

Audit event data structure.

**Methods:**

- `to_dict()`
- `to_json()`

#### AuditLogger

Abstract audit logger interface.

**Methods:**

- `async log_event()`
- `async query_events()`

#### FileAuditLogger

File-based audit logger.

**Methods:**

- `__init__()`
- `async log_event()`
- `async query_events()`

#### DatabaseAuditLogger

Database-based audit logger (interface).

**Methods:**

- `__init__()`
- `async log_event()`
- `async query_events()`

#### AuditManager

Audit management system.

Features:

- Multiple audit loggers
- Event filtering and routing
- Suspicious activity detection
- Alert generation for security events
- Metrics and reporting

**Methods:**

- `__init__()`
- `async log_event()`
- `async log_authentication_event()`
- `async log_mfa_event()`
- `async log_permission_event()`
- `async log_security_event()`
- `async query_events()`
- `async get_security_summary()`
- `async _check_suspicious_activity()`
- `async _generate_alert()`

#### AuditLoggingMiddleware

FastAPI/Starlette middleware for audit logging.

Automatically logs authentication-related requests and responses.

**Methods:**

- `__init__()`
- `async dispatch()`
- `async _log_request_response()`

*Source: /home/dotmac_framework/src/dotmac_shared/auth/middleware/audit_logging.py*

## dotmac_shared.auth.middleware.fastapi_middleware

FastAPI middleware integration for authentication service.

Placeholder implementation to fix imports - will be completed in Week 4.

### Classes

#### AuthenticationMiddleware

FastAPI authentication middleware (placeholder).

**Methods:**

- `__init__()`
- `async __call__()`

*Source: /home/dotmac_framework/src/dotmac_shared/auth/middleware/fastapi_middleware.py*

## dotmac_shared.auth.middleware.rate_limiting

Rate Limiting Middleware

Implements comprehensive rate limiting and brute force protection:

- Per-IP rate limiting
- Per-user rate limiting
- Account lockout policies
- Distributed rate limiting with Redis
- Configurable time windows and limits
- Suspicious activity detection

### Classes

#### RateLimitType

Types of rate limiting.

#### RateLimitRule

Rate limiting rule configuration.

**Methods:**

- `matches_request()`

#### RateLimitAttempt

Rate limit attempt record.

#### RateLimitStore

Abstract rate limiting storage interface.

**Methods:**

- `async increment_counter()`
- `async get_counter()`
- `async reset_counter()`
- `async add_lockout()`
- `async is_locked_out()`
- `async remove_lockout()`

#### RedisRateLimitStore

Redis-based rate limiting storage.

**Methods:**

- `__init__()`
- `async increment_counter()`
- `async get_counter()`
- `async reset_counter()`
- `async add_lockout()`
- `async is_locked_out()`
- `async remove_lockout()`

#### InMemoryRateLimitStore

In-memory rate limiting storage for development.

**Methods:**

- `__init__()`
- `async increment_counter()`
- `async get_counter()`
- `async reset_counter()`
- `async add_lockout()`
- `async is_locked_out()`
- `async remove_lockout()`

#### RateLimiter

Comprehensive rate limiting system.

Features:

- Multiple rate limiting strategies
- Configurable rules per endpoint
- Account lockout protection
- Suspicious activity detection
- Distributed storage support

**Methods:**

- `__init__()`
- `add_rule()`
- `remove_rule()`
- `async check_rate_limits()`
- `async _is_locked_out()`
- `async _should_lockout()`
- `async _add_lockout()`
- `async remove_lockout()`
- `async reset_user_limits()`
- `async get_user_limit_status()`

#### RateLimitingMiddleware

FastAPI/Starlette middleware for rate limiting.

Automatically applies rate limiting rules to requests and returns
appropriate HTTP 429 responses for violations.

**Methods:**

- `__init__()`
- `async dispatch()`
- `async _add_rate_limit_headers()`

*Source: /home/dotmac_framework/src/dotmac_shared/auth/middleware/rate_limiting.py*

## dotmac_shared.auth.providers.__init__

Authentication providers.

This module contains different authentication providers:

- Local database authentication
- OAuth2/OIDC integration
- LDAP/Active Directory integration

*Source: /home/dotmac_framework/src/dotmac_shared/auth/providers/__init__.py*

## dotmac_shared.billing.__init__

DotMac Billing Package

A comprehensive, reusable billing system for ISP and service provider applications.
Designed for multi-tenant, scalable deployments with pluggable integrations.

Key Features:

- Multi-tenant billing with tenant isolation
- Flexible pricing models (flat rate, usage-based, tiered)
- Subscription and one-time billing support
- Payment processing integration
- Invoice generation and management
- Revenue recognition and reporting
- Plugin architecture for custom billing rules
- Audit trail and compliance features

Usage:
    from dotmac_shared.billing import BillingService, InvoiceService

    billing = BillingService(config)
    invoice = await billing.create_invoice(customer_id, line_items)

*Source: /home/dotmac_framework/src/dotmac_shared/billing/__init__.py*

## dotmac_shared.billing.adapters.__init__

Platform adapters for billing package integration.

*Source: /home/dotmac_framework/src/dotmac_shared/billing/adapters/__init__.py*

## dotmac_shared.billing.adapters.isp_platform_adapter

ISP Platform Billing Adapter.

This adapter integrates the shared billing service with the ISP Framework,
mapping ISP-specific models and providing ISP-tailored billing functionality.

### Classes

#### ISPBillingAdapter

Adapter that integrates shared billing service with ISP Framework.

Provides ISP-specific billing operations while leveraging the shared
billing service for core functionality.

**Methods:**

- `__init__()`
- `async create_service_subscription()`
- `async cancel_service_subscription()`
- `async record_service_usage()`
- `async generate_service_invoice()`
- `async process_service_payment()`
- `async run_isp_billing_cycle()`
- `async _get_or_create_billing_plan()`
- `async _get_subscription_by_service_instance()`
- `async _calculate_isp_billing_period()`
- `async _add_isp_usage_details()`
- `async _get_service_type_breakdown()`
- `async _calculate_regulatory_fees()`
- `async _calculate_usage_overages()`
- `async _trigger_isp_post_billing_tasks()`

#### ISPBillingService

ISP Framework billing service that wraps the shared billing adapter.

This maintains compatibility with existing ISP Framework patterns
while leveraging the shared billing service.

**Methods:**

- `__init__()`
- `async create_service_subscription()`
- `async cancel_service_subscription()`
- `async record_service_usage()`
- `async generate_service_invoice()`
- `async process_service_payment()`
- `async run_isp_billing_cycle()`

*Source: /home/dotmac_framework/src/dotmac_shared/billing/adapters/isp_platform_adapter.py*

## dotmac_shared.billing.adapters.management_platform_adapter

Management Platform Billing Adapter.

This adapter integrates the shared billing service with the Management Platform,
providing tenant billing, plugin licensing, and SaaS subscription management.

### Classes

#### ManagementPlatformBillingAdapter

Adapter that integrates shared billing service with Management Platform.

Handles tenant subscriptions, plugin licensing, resource usage billing,
and SaaS-specific billing operations.

**Methods:**

- `__init__()`
- `async create_tenant_subscription()`
- `async upgrade_tenant_subscription()`
- `async create_plugin_license()`
- `async record_resource_usage()`
- `async generate_tenant_invoice()`
- `async process_tenant_payment()`
- `async run_saas_billing_cycle()`
- `async _get_or_create_saas_billing_plan()`
- `async _get_or_create_plugin_billing_plan()`
- `async _get_or_create_tenant_customer()`
- `async _get_tenant_customer_id()`
- `async _get_tenant_subscription_id()`
- `async _create_tenant_subscription_record()`
- `async _setup_tenant_resource_limits()`
- `async _check_usage_limits()`
- `async _trigger_saas_post_billing_tasks()`

#### ManagementPlatformBillingService

Management Platform billing service that wraps the shared billing adapter.

Provides SaaS-specific billing operations while maintaining compatibility
with existing Management Platform patterns.

**Methods:**

- `__init__()`
- `async create_tenant_subscription()`
- `async upgrade_tenant_subscription()`
- `async create_plugin_license()`
- `async record_resource_usage()`
- `async generate_tenant_invoice()`
- `async process_tenant_payment()`
- `async run_saas_billing_cycle()`

*Source: /home/dotmac_framework/src/dotmac_shared/billing/adapters/management_platform_adapter.py*

## dotmac_shared.billing.adapters.service_factory

Service factory for creating platform-specific billing service instances.

This factory provides a unified way to create billing services that work
with different platform configurations while maintaining consistent interfaces.

### Classes

#### BillingServiceFactory

Factory for creating billing service instances.

**Methods:**

- `__init__()`
- `register_payment_gateway()`
- `register_notification_service()`
- `register_tax_service()`
- `register_pdf_generator()`
- `create_billing_service()`

*Source: /home/dotmac_framework/src/dotmac_shared/billing/adapters/service_factory.py*

## dotmac_shared.billing.core.__init__

Core billing models and enumerations.

*Source: /home/dotmac_framework/src/dotmac_shared/billing/core/__init__.py*

## dotmac_shared.billing.core.models

Core billing models for the DotMac Billing Package.

These models provide the foundation for billing functionality across
ISP and service provider applications with multi-tenant support.

### Classes

#### InvoiceStatus

Invoice status enumeration.

#### PaymentStatus

Payment status enumeration.

#### PaymentMethod

Payment method enumeration.

#### BillingCycle

Billing cycle enumeration.

#### SubscriptionStatus

Subscription status enumeration.

#### TaxType

Tax type enumeration.

#### PricingModel

Pricing model enumeration.

#### BillingModelMixin

Base mixin for billing models with common fields.

#### Customer

Customer model for billing management.

#### BillingPlan

Billing plan template for services and products.

#### PricingTier

Pricing tiers for tiered billing models.

#### Subscription

Customer subscription to billing plans.

#### Invoice

Invoice for billing customers.

**Methods:**

- `is_paid()`
- `is_overdue()`

#### InvoiceLineItem

Line items for invoices.

#### Payment

Payment records for invoices.

#### UsageRecord

Usage tracking for usage-based billing.

#### BillingPeriod

Billing periods for subscription lifecycle management.

*Source: /home/dotmac_framework/src/dotmac_shared/billing/core/models.py*

## dotmac_shared.billing.examples.__init__

Integration examples for the DotMac Billing Package.

*Source: /home/dotmac_framework/src/dotmac_shared/billing/examples/__init__.py*

## dotmac_shared.billing.examples.integration_examples

Integration examples showing how to use the DotMac Billing Package
in different platform scenarios.

*Source: /home/dotmac_framework/src/dotmac_shared/billing/examples/integration_examples.py*

## dotmac_shared.billing.repositories.__init__

Repository implementations for billing entities.

*Source: /home/dotmac_framework/src/dotmac_shared/billing/repositories/__init__.py*

## dotmac_shared.billing.repositories.base_repository

Base repository implementation for the DotMac Billing Package.

Provides common database operations with multi-tenant support and
platform-agnostic implementation using SQLAlchemy.

### Classes

#### BaseBillingRepository

Base repository providing common CRUD operations for billing models.

**Methods:**

- `__init__()`
- `async create()`
- `async get()`
- `async get_multi()`
- `async update()`
- `async delete()`
- `async count()`
- `async exists()`
- `async get_by_field()`
- `async bulk_create()`
- `async soft_delete()`

*Source: /home/dotmac_framework/src/dotmac_shared/billing/repositories/base_repository.py*

## dotmac_shared.billing.repositories.billing_repositories

Concrete repository implementations for billing entities.

These repositories implement the protocol interfaces and provide
specialized query methods for each billing entity type.

### Classes

#### CustomerRepository

Repository for customer operations.

**Methods:**

- `__init__()`
- `async get_by_email()`
- `async get_by_customer_code()`
- `async get_active_customers()`
- `async search_customers()`

#### BillingPlanRepository

Repository for billing plan operations.

**Methods:**

- `__init__()`
- `async get_by_plan_code()`
- `async get_active_plans()`
- `async get_public_plans()`

#### SubscriptionRepository

Repository for subscription operations.

**Methods:**

- `__init__()`
- `async get_by_customer()`
- `async get_active_subscriptions()`
- `async get_due_for_billing()`
- `async get_by_subscription_number()`
- `async get_expiring_subscriptions()`

#### InvoiceRepository

Repository for invoice operations.

**Methods:**

- `__init__()`
- `async get_by_customer()`
- `async get_by_subscription()`
- `async get_by_status()`
- `async get_overdue_invoices()`
- `async get_by_invoice_number()`
- `async get_revenue_by_period()`

#### PaymentRepository

Repository for payment operations.

**Methods:**

- `__init__()`
- `async get_by_customer()`
- `async get_by_invoice()`
- `async get_by_status()`
- `async get_failed_payments()`
- `async get_payments_by_date_range()`

#### UsageRepository

Repository for usage record operations.

**Methods:**

- `__init__()`
- `async get_by_subscription()`
- `async get_unprocessed_usage()`
- `async get_usage_summary_by_subscription()`
- `async bulk_mark_processed()`

*Source: /home/dotmac_framework/src/dotmac_shared/billing/repositories/billing_repositories.py*

## dotmac_shared.billing.schemas.__init__

Billing schemas for API requests and responses.

*Source: /home/dotmac_framework/src/dotmac_shared/billing/schemas/__init__.py*

## dotmac_shared.billing.schemas.billing_schemas

Pydantic schemas for the DotMac Billing Package.

These schemas define the request/response models for API endpoints
and provide validation for billing operations.

### Classes

#### BillingBaseSchema

Base schema with common configuration.

#### CustomerBase

Base customer schema with common fields.

**Methods:**

- `validate_email()`
- `validate_currency()`

#### CustomerCreate

Schema for creating a new customer.

#### CustomerUpdate

Schema for updating customer information.

#### CustomerResponse

Schema for customer API responses.

#### CustomerListResponse

Schema for paginated customer list responses.

#### BillingPlanBase

Base billing plan schema.

#### BillingPlanCreate

Schema for creating a billing plan.

#### BillingPlanUpdate

Schema for updating a billing plan.

#### BillingPlanResponse

Schema for billing plan API responses.

#### BillingPlanListResponse

Schema for paginated billing plan list responses.

#### SubscriptionBase

Base subscription schema.

#### SubscriptionCreate

Schema for creating a subscription.

#### SubscriptionUpdate

Schema for updating a subscription.

#### SubscriptionResponse

Schema for subscription API responses.

#### SubscriptionListResponse

Schema for paginated subscription list responses.

#### InvoiceLineItemBase

Base invoice line item schema.

#### InvoiceLineItemResponse

Schema for invoice line item responses.

#### InvoiceBase

Base invoice schema.

#### InvoiceCreate

Schema for creating an invoice.

#### InvoiceUpdate

Schema for updating an invoice.

#### InvoiceResponse

Schema for invoice API responses.

**Methods:**

- `is_paid()`
- `is_overdue()`

#### InvoiceListResponse

Schema for paginated invoice list responses.

#### PaymentBase

Base payment schema.

#### PaymentCreate

Schema for creating a payment.

#### PaymentResponse

Schema for payment API responses.

#### PaymentListResponse

Schema for paginated payment list responses.

#### UsageRecordBase

Base usage record schema.

#### UsageRecordCreate

Schema for creating a usage record.

#### UsageRecordResponse

Schema for usage record API responses.

#### UsageRecordListResponse

Schema for paginated usage record list responses.

#### RevenueMetricsResponse

Schema for revenue analytics.

#### CustomerMetricsResponse

Schema for customer analytics.

#### SubscriptionMetricsResponse

Schema for subscription analytics.

#### BillingAnalyticsResponse

Schema for comprehensive billing analytics.

*Source: /home/dotmac_framework/src/dotmac_shared/billing/schemas/billing_schemas.py*

## dotmac_shared.billing.services.__init__

Billing services for the DotMac Billing Package.

*Source: /home/dotmac_framework/src/dotmac_shared/billing/services/__init__.py*

## dotmac_shared.billing.services.billing_service

Core billing service implementation.

This service orchestrates all billing operations including subscription management,
invoice generation, payment processing, and usage tracking.

### Classes

#### BillingService

Main billing service implementation.

**Methods:**

- `__init__()`
- `async create_subscription()`
- `async cancel_subscription()`
- `async generate_invoice()`
- `async process_payment()`
- `async record_usage()`
- `async run_billing_cycle()`
- `async _calculate_billing_period()`

*Source: /home/dotmac_framework/src/dotmac_shared/billing/services/billing_service.py*

## dotmac_shared.billing.services.protocols

Service protocols for the DotMac Billing Package.

These protocols define the interfaces that billing services must implement,
allowing for platform-specific customization while maintaining consistency.

### Classes

#### DatabaseSessionProtocol

Protocol for database session objects.

**Methods:**

- `async commit()`
- `async rollback()`
- `async refresh()`

#### BaseRepositoryProtocol

Base protocol for repository operations.

**Methods:**

- `async create()`
- `async get()`
- `async get_multi()`
- `async update()`
- `async delete()`
- `async count()`

#### CustomerRepositoryProtocol

Protocol for customer repository operations.

**Methods:**

- `async get_by_email()`
- `async get_by_customer_code()`
- `async get_active_customers()`

#### BillingPlanRepositoryProtocol

Protocol for billing plan repository operations.

**Methods:**

- `async get_by_plan_code()`
- `async get_active_plans()`
- `async get_public_plans()`

#### SubscriptionRepositoryProtocol

Protocol for subscription repository operations.

**Methods:**

- `async get_by_customer()`
- `async get_active_subscriptions()`
- `async get_due_for_billing()`
- `async get_by_subscription_number()`

#### InvoiceRepositoryProtocol

Protocol for invoice repository operations.

**Methods:**

- `async get_by_customer()`
- `async get_by_subscription()`
- `async get_by_status()`
- `async get_overdue_invoices()`
- `async get_by_invoice_number()`

#### PaymentRepositoryProtocol

Protocol for payment repository operations.

**Methods:**

- `async get_by_customer()`
- `async get_by_invoice()`
- `async get_by_status()`

#### UsageRepositoryProtocol

Protocol for usage record repository operations.

**Methods:**

- `async get_by_subscription()`
- `async get_unprocessed_usage()`

#### PaymentGatewayProtocol

Protocol for payment gateway integrations.

**Methods:**

- `async process_payment()`
- `async refund_payment()`
- `async get_payment_status()`

#### NotificationServiceProtocol

Protocol for notification services.

**Methods:**

- `async send_invoice_notification()`
- `async send_payment_notification()`
- `async send_subscription_notification()`

#### TaxCalculationServiceProtocol

Protocol for tax calculation services.

**Methods:**

- `async calculate_tax()`
- `async validate_tax_id()`

#### PdfGeneratorProtocol

Protocol for PDF generation services.

**Methods:**

- `async generate_invoice_pdf()`
- `async generate_statement_pdf()`

#### BillingServiceProtocol

Main billing service protocol.

**Methods:**

- `async create_subscription()`
- `async cancel_subscription()`
- `async generate_invoice()`
- `async process_payment()`
- `async record_usage()`
- `async run_billing_cycle()`

#### InvoiceServiceProtocol

Invoice-specific service protocol.

**Methods:**

- `async create_invoice()`
- `async finalize_invoice()`
- `async send_invoice()`
- `async void_invoice()`

#### PaymentServiceProtocol

Payment-specific service protocol.

**Methods:**

- `async create_payment()`
- `async process_payment()`
- `async refund_payment()`

#### SubscriptionServiceProtocol

Subscription-specific service protocol.

**Methods:**

- `async create_subscription()`
- `async update_subscription()`
- `async change_plan()`

#### BillingAnalyticsProtocol

Protocol for billing analytics and reporting.

**Methods:**

- `async get_revenue_metrics()`
- `async get_customer_metrics()`
- `async get_subscription_metrics()`
- `async get_churn_analysis()`

*Source: /home/dotmac_framework/src/dotmac_shared/billing/services/protocols.py*

## dotmac_shared.cache.__init__

Shared cache service for the dotmac framework.

Provides high-performance, multi-tier caching with tenant isolation,
Redis backend support, and service registry integration.

## Quick Start

```python
from dotmac_shared.cache import create_cache_service, CacheConfig

# Create cache service with default configuration
cache_service = create_cache_service()

# Initialize the service
await cache_service.initialize()

# Use cache operations
await cache_service.set("key", "value", tenant_id=tenant_uuid)
value = await cache_service.get("key", tenant_id=tenant_uuid)
```

## Features

- __Multi-tier Caching__: Redis primary with memory fallback
- __Tenant Isolation__: Secure key namespacing and quota enforcement
- __Service Integration__: Built-in service registry support
- __Performance Monitoring__: Real-time metrics and health checks
- __Configurable Backends__: Redis, memory, or hybrid configurations
- __Production Ready__: Connection pooling, retry logic, and error handling

*Source: /home/dotmac_framework/src/dotmac_shared/cache/__init__.py*

## dotmac_shared.cache.base_service

Minimal service base classes for cache service integration.

This module provides a standalone implementation to avoid circular imports
with the main services package.

### Classes

#### ServiceStatus

Service status enumeration.

#### ServiceHealth

Service health information.

**Methods:**

- `__post_init__()`

#### BaseService

Base class for cache service.

**Methods:**

- `__init__()`
- `async initialize()`
- `async shutdown()`
- `async health_check()`
- `async get_service_info()`

#### ConfigurableService

Base service with configuration support.

**Methods:**

- `__init__()`
- `get_config_value()`
- `update_config()`

*Source: /home/dotmac_framework/src/dotmac_shared/cache/base_service.py*

## dotmac_shared.cache.core.__init__

Core caching components.

This module contains the fundamental cache manager implementations,
protocols, and backend abstractions.

*Source: /home/dotmac_framework/src/dotmac_shared/cache/core/__init__.py*

## dotmac_shared.cache.core.backends

Cache backend implementations.

Provides concrete implementations for different cache storage backends.

### Classes

#### CacheEntry

Memory cache entry with TTL.

**Methods:**

- `is_expired()`
- `touch()`

#### RedisBackend

Redis backend for cache storage.

**Methods:**

- `__init__()`
- `async connect()`
- `async disconnect()`
- `async is_connected()`
- `async get_raw()`
- `async set_raw()`
- `async delete_raw()`
- `async exists_raw()`
- `async keys_raw()`
- `async ping_raw()`
- `async ttl_raw()`
- `async expire_raw()`

#### MemoryBackend

In-memory cache backend with configurable eviction policies.

**Methods:**

- `__init__()`
- `async connect()`
- `async disconnect()`
- `async is_connected()`
- `async _cleanup_expired()`
- `async get_raw()`
- `async set_raw()`
- `async delete_raw()`
- `async exists_raw()`
- `async keys_raw()`
- `async ping_raw()`
- `get_stats()`

*Source: /home/dotmac_framework/src/dotmac_shared/cache/core/backends.py*

## dotmac_shared.cache.core.config

Cache configuration management.

### Classes

#### CacheConfig

Configuration for cache managers.

**Methods:**

- `from_env()`
- `get_redis_connection_kwargs()`
- `validate()`
- `__post_init__()`

*Source: /home/dotmac_framework/src/dotmac_shared/cache/core/config.py*

## dotmac_shared.cache.core.exceptions

Cache service exceptions.

### Classes

#### CacheError

Base exception for cache operations.

#### CacheConnectionError

Exception raised when cache backend connection fails.

#### CacheMissError

Exception raised when a required cache key is missing.

#### CacheSerializationError

Exception raised when serialization/deserialization fails.

#### CacheTimeoutError

Exception raised when cache operation times out.

#### CacheTenantError

Exception raised for tenant-related cache issues.

*Source: /home/dotmac_framework/src/dotmac_shared/cache/core/exceptions.py*

## dotmac_shared.cache.core.managers

Cache manager implementations.

Provides concrete implementations of the cache manager protocol
for different backends and use cases.

### Classes

#### CacheMetrics

Cache performance metrics.

**Methods:**

- `hit_rate()`

#### RedisCacheManager

Redis-based cache manager with tenant isolation.

**Methods:**

- `__init__()`
- `async connect()`
- `async disconnect()`
- `async get()`
- `async set()`
- `async delete()`
- `async exists()`
- `async clear()`
- `async expire()`
- `async ttl()`
- `async mget()`
- `async mset()`
- `async increment()`
- `async decrement()`
- `async ping()`
- `async health_check()`
- `async get_stats()`
- `async flush_all()`

#### MemoryCacheManager

In-memory cache manager with LRU eviction.

**Methods:**

- `__init__()`
- `async connect()`
- `async disconnect()`
- `async get()`
- `async set()`
- `async delete()`
- `async exists()`
- `async clear()`
- `async expire()`
- `async ttl()`
- `async mget()`
- `async mset()`
- `async increment()`
- `async decrement()`
- `async ping()`
- `async health_check()`
- `async get_stats()`
- `async flush_all()`

#### HybridCacheManager

Multi-tier cache manager with Redis primary and Memory fallback.

**Methods:**

- `__init__()`
- `async connect()`
- `async get()`
- `async set()`
- `async _promote_to_primary()`
- `async delete()`
- `async exists()`
- `async clear()`
- `async health_check()`

*Source: /home/dotmac_framework/src/dotmac_shared/cache/core/managers.py*

## dotmac_shared.cache.core.protocols

Cache manager protocols and interfaces.

Defines the contracts that all cache managers and backends must implement.

### Classes

#### CacheManagerProtocol

Protocol defining the interface for cache managers.

**Methods:**

- `async get()`
- `async set()`
- `async delete()`
- `async exists()`
- `async clear()`
- `async expire()`
- `async ttl()`
- `async mget()`
- `async mset()`
- `async increment()`
- `async decrement()`
- `async ping()`
- `async health_check()`
- `async get_stats()`
- `async flush_all()`

#### CacheBackendProtocol

Protocol for cache backend implementations.

**Methods:**

- `async connect()`
- `async disconnect()`
- `async is_connected()`
- `async get_raw()`
- `async set_raw()`
- `async delete_raw()`
- `async exists_raw()`
- `async keys_raw()`
- `async ping_raw()`

#### CacheSerializerProtocol

Protocol for cache value serialization.

**Methods:**

- `serialize()`
- `deserialize()`

*Source: /home/dotmac_framework/src/dotmac_shared/cache/core/protocols.py*

## dotmac_shared.cache.core.serialization

Serialization utilities for cache values.

### Classes

#### JSONSerializer

JSON-based serializer for cache values.

**Methods:**

- `serialize()`
- `deserialize()`

#### PickleSerializer

Pickle-based serializer for cache values.

**Methods:**

- `__init__()`
- `serialize()`
- `deserialize()`

#### CompressedSerializer

Wrapper that adds compression to any serializer.

**Methods:**

- `__init__()`
- `serialize()`
- `deserialize()`

*Source: /home/dotmac_framework/src/dotmac_shared/cache/core/serialization.py*

## dotmac_shared.captive_portal.dotmac_captive_portal.__init__

Unified Captive Portal Package for DotMac Framework.

Provides comprehensive WiFi captive portal functionality including:

- Guest network management and access control
- Multi-authentication methods (social, vouchers, RADIUS)
- Billing integration with usage tracking and payments
- Portal customization with themes and branding
- Session management and monitoring
- RADIUS integration for network enforcement
- Analytics and reporting

This package consolidates captive portal functionality across the DotMac ecosystem,
replacing scattered implementations with a unified, production-ready solution.

*Source: /home/dotmac_framework/src/dotmac_shared/captive_portal/dotmac_captive_portal/__init__.py*

## dotmac_shared.captive_portal.dotmac_captive_portal.auth

Authentication components for captive portal systems.

Provides multiple authentication methods including email, SMS, social,
vouchers, and RADIUS integration with comprehensive validation and security.

### Classes

#### AuthenticationResult

Result of authentication attempt.

#### SocialAuthConfig

Configuration for social authentication providers.

#### BaseAuthMethod

Base class for authentication methods.

**Methods:**

- `__init__()`
- `async authenticate()`
- `async prepare_authentication()`
- `validate_credentials()`
- `generate_verification_code()`

#### SocialAuth

Social media authentication (OAuth).

**Methods:**

- `__init__()`
- `async prepare_authentication()`
- `async authenticate()`
- `async _exchange_oauth_code()`
- `async _get_user_info()`

#### VoucherAuth

Voucher-based authentication.

**Methods:**

- `__init__()`
- `set_database_session()`
- `validate_credentials()`
- `async prepare_authentication()`
- `async authenticate()`
- `async _find_voucher()`
- `async _process_voucher_success()`

#### RADIUSAuth

RADIUS authentication integration.

**Methods:**

- `__init__()`
- `validate_credentials()`
- `async prepare_authentication()`
- `async authenticate()`
- `async _radius_authenticate()`

#### AuthenticationManager

Manages multiple authentication methods for captive portals.

**Methods:**

- `__init__()`
- `register_auth_method()`
- `get_auth_method()`
- `list_auth_methods()`
- `async prepare_authentication()`
- `async authenticate()`
- `set_default_method()`
- `get_default_method()`

*Source: /home/dotmac_framework/src/dotmac_shared/captive_portal/dotmac_captive_portal/auth.py*

## dotmac_shared.captive_portal.dotmac_captive_portal.billing

Billing integration and usage tracking for captive portal systems.

Provides comprehensive billing functionality including usage tracking,
payment processing, subscription management, and integration with
external payment providers.

### Classes

#### BillingType

Billing types for captive portal access.

#### PaymentStatus

Payment transaction status.

#### UsageMetrics

Usage tracking metrics.

#### BillingTransaction

Billing transaction record.

#### UsageTracker

Tracks user usage for billing purposes.

**Methods:**

- `__init__()`
- `async start_usage_tracking()`
- `async update_usage_metrics()`
- `async stop_usage_tracking()`
- `async get_user_usage_summary()`
- `async _log_usage_sample()`
- `async _log_final_usage()`

#### PaymentProcessor

Handles payment processing for captive portal billing.

**Methods:**

- `__init__()`
- `async create_payment_intent()`
- `async confirm_payment()`
- `async refund_payment()`
- `get_transaction()`
- `async _create_stripe_payment_intent()`
- `async _create_paypal_payment()`
- `async _verify_stripe_payment()`
- `async _verify_paypal_payment()`
- `async _create_stripe_refund()`
- `async _create_paypal_refund()`

#### BillingIntegration

Main billing integration class for captive portals.

**Methods:**

- `__init__()`
- `async create_billing_plan()`
- `async initiate_billing_session()`
- `async confirm_billing_payment()`
- `async check_usage_limits()`
- `async finalize_billing_session()`
- `async _calculate_final_charges()`

*Source: /home/dotmac_framework/src/dotmac_shared/captive_portal/dotmac_captive_portal/billing.py*

## dotmac_shared.captive_portal.dotmac_captive_portal.core

Core captive portal functionality and configuration.

Provides the main CaptivePortal class and configuration management
for unified captive portal operations.

### Classes

#### CaptivePortalConfig

Configuration for captive portal operations.

#### CaptivePortalService

Core service for captive portal operations.

**Methods:**

- `__init__()`
- `async create_portal()`
- `async get_portal()`
- `async update_portal()`
- `async delete_portal()`
- `async register_guest_user()`
- `async authenticate_user()`
- `async _create_session()`
- `async terminate_session()`
- `async get_active_sessions()`
- `async validate_session()`
- `async cleanup_expired_sessions()`
- `async _find_user()`
- `async _validate_authentication()`
- `async _check_rate_limit()`
- `async _record_failed_attempt()`
- `async _get_user_active_sessions()`
- `async _send_verification()`

#### CaptivePortal

Main captive portal management class.

**Methods:**

- `__init__()`
- `set_database_session()`
- `service()`
- `async create_portal()`
- `async authenticate_user()`
- `async terminate_session()`
- `async validate_session()`
- `async cleanup_expired_sessions()`

*Source: /home/dotmac_framework/src/dotmac_shared/captive_portal/dotmac_captive_portal/core.py*

## dotmac_shared.captive_portal.dotmac_captive_portal.customization

Portal customization and theming system for captive portals.

Provides comprehensive customization capabilities including themes, branding,
custom HTML/CSS, multi-language support, and dynamic content management.

### Classes

#### ThemeType

Portal theme types.

#### ContentType

Content types for portal pages.

#### ColorScheme

Color scheme configuration.

**Methods:**

- `to_dict()`

#### Typography

Typography configuration.

**Methods:**

- `to_dict()`

#### BrandingConfig

Branding configuration for portals.

**Methods:**

- `to_dict()`

#### LayoutConfig

Layout configuration for portal pages.

**Methods:**

- `to_dict()`

#### Theme

Portal theme configuration.

**Methods:**

- `__init__()`
- `generate_css()`
- `to_dict()`

#### ContentManager

Manages portal content and templates.

**Methods:**

- `__init__()`
- `set_content()`
- `get_content()`
- `render_template()`
- `set_translation()`
- `get_translation()`
- `load_translations_from_file()`

#### AssetManager

Manages portal assets like images, videos, and files.

**Methods:**

- `__init__()`
- `async upload_image()`
- `async upload_document()`
- `get_asset_url()`
- `delete_asset()`

#### PortalCustomizer

Main portal customization manager.

**Methods:**

- `__init__()`
- `create_theme()`
- `get_theme()`
- `list_themes()`
- `generate_portal_html()`
- `update_portal_branding()`

*Source: /home/dotmac_framework/src/dotmac_shared/captive_portal/dotmac_captive_portal/customization.py*

## dotmac_shared.captive_portal.dotmac_captive_portal.guest_manager

Guest network management for captive portal systems.

Provides comprehensive guest network configuration, access control,
VLAN management, and network isolation capabilities.

### Classes

#### NetworkRange

Network range configuration.

#### VLANConfig

VLAN configuration for guest network isolation.

#### AccessPointConfig

Access point configuration.

#### GuestNetwork

Represents a guest network configuration.

**Methods:**

- `__init__()`
- `is_ip_in_range()`
- `get_available_ips()`
- `validate_configuration()`
- `to_dict()`

#### NetworkDeviceManager

Manages network devices and their access control.

**Methods:**

- `__init__()`
- `register_device()`
- `update_device_activity()`
- `get_device_info()`
- `get_device_bandwidth_usage()`
- `list_online_devices()`
- `associate_device_session()`
- `get_device_session()`

#### GuestNetworkManager

Manages guest networks and their configurations.

**Methods:**

- `__init__()`
- `async create_guest_network()`
- `get_guest_network()`
- `list_guest_networks()`
- `async update_guest_network()`
- `delete_guest_network()`
- `async assign_ip_address()`
- `async apply_bandwidth_policies()`
- `async apply_firewall_rules()`
- `configure_access_point()`
- `get_network_statistics()`
- `async _get_assigned_ips()`

*Source: /home/dotmac_framework/src/dotmac_shared/captive_portal/dotmac_captive_portal/guest_manager.py*

## dotmac_shared.captive_portal.dotmac_captive_portal.models

Database models for captive portal functionality.

Provides SQLAlchemy models for all captive portal entities including
portals, users, sessions, vouchers, billing plans, and analytics.

### Classes

#### AuthMethodType

Authentication method types.

#### SessionStatus

User session status.

#### PortalStatus

Portal status.

#### BillingStatus

Billing status.

#### Portal

Captive portal configuration model.

**Methods:**

- `__repr__()`

#### GuestUser

Guest user model for captive portal access.

**Methods:**

- `__repr__()`

#### Session

User session model for tracking captive portal access.

**Methods:**

- `duration_minutes()`
- `total_bytes()`
- `__repr__()`

#### Voucher

Access voucher model for pre-paid captive portal access.

**Methods:**

- `is_expired()`
- `is_valid()`
- `__repr__()`

#### BillingPlan

Billing plan model for captive portal access pricing.

**Methods:**

- `__repr__()`

#### AuthMethod

Authentication method configuration model.

**Methods:**

- `__repr__()`

#### UsageLog

Usage tracking and analytics model.

**Methods:**

- `__repr__()`

*Source: /home/dotmac_framework/src/dotmac_shared/captive_portal/dotmac_captive_portal/models.py*

## dotmac_shared.container.__init__

Container and Kubernetes integration for DotMac services.

*Source: /home/dotmac_framework/src/dotmac_shared/container/__init__.py*

## dotmac_shared.container_config.__init__

DotMac Container Configuration Service

A comprehensive configuration management service for multi-tenant ISP container deployments.
Handles per-container configuration injection, environment-specific settings, and secure secret management.

*Source: /home/dotmac_framework/src/dotmac_shared/container_config/__init__.py*

## dotmac_shared.container_config.core.__init__

Core configuration management components.

*Source: /home/dotmac_framework/src/dotmac_shared/container_config/core/__init__.py*

## dotmac_shared.container_config.core.feature_flags

Feature flag management for premium feature control.

### Classes

#### FeatureRegistry

Registry for feature definitions and plan configurations.

**Methods:**

- `__init__()`
- `register_feature()`
- `get_feature()`
- `list_features()`
- `get_plan_features()`

#### FeatureFlagEvaluator

Evaluates feature flags based on conditions and rollout strategies.

**Methods:**

- `__init__()`
- `evaluate_flag()`
- `batch_evaluate()`

#### FeatureFlagManager

Manages feature flags and applies them to configurations.

Handles feature flag evaluation, configuration injection,
and integration with subscription plans.

**Methods:**

- `__init__()`
- `async apply_feature_flags()`
- `async _get_tenant_flags()`
- `async _apply_feature_configurations()`
- `async generate_plan_features()`
- `async create_feature_flag()`
- `async update_feature_flag()`
- `async delete_feature_flag()`
- `async list_tenant_flags()`
- `async get_feature_usage_stats()`
- `register_custom_feature()`

*Source: /home/dotmac_framework/src/dotmac_shared/container_config/core/feature_flags.py*

## dotmac_shared.container_config.core.secret_manager

Secret management service for secure configuration injection.

### Classes

#### SecretEncryption

Handles encryption and decryption of secrets.

**Methods:**

- `__init__()`
- `encrypt()`
- `decrypt()`
- `is_encrypted()`

#### SecretStore

Abstract secret storage interface.

**Methods:**

- `async store_secret()`
- `async get_secret()`
- `async delete_secret()`
- `async list_secrets()`
- `async rotate_secret()`

#### InMemorySecretStore

In-memory secret store for development/testing.

**Methods:**

- `__init__()`
- `async store_secret()`
- `async get_secret()`
- `async delete_secret()`
- `async list_secrets()`
- `async rotate_secret()`

#### DatabaseSecretStore

Database-backed secret store (placeholder implementation).

**Methods:**

- `__init__()`
- `async store_secret()`
- `async get_secret()`
- `async delete_secret()`
- `async list_secrets()`
- `async rotate_secret()`

#### SecretManager

Secure secret management for configuration injection.

Handles encryption, storage, rotation, and injection of secrets
into configuration templates and objects.

**Methods:**

- `__init__()`
- `async store_secret()`
- `async get_secret()`
- `async inject_secrets()`
- `async _inject_secrets_recursive()`
- `async _replace_secret_placeholders()`
- `async _auto_generate_secret()`
- `async rotate_secret()`
- `async rotate_expired_secrets()`
- `async validate_secret_access()`
- `async list_tenant_secrets()`
- `async backup_secrets()`
- `create_secret_placeholder()`
- `extract_secret_keys()`

*Source: /home/dotmac_framework/src/dotmac_shared/container_config/core/secret_manager.py*

## dotmac_shared.container_config.schemas.__init__

Configuration schemas and data models.

*Source: /home/dotmac_framework/src/dotmac_shared/container_config/schemas/__init__.py*

## dotmac_shared.container_config.schemas.config_schemas

Configuration schemas for ISP container deployments.

### Classes

#### LogLevel

Logging levels.

#### DatabaseType

Supported database types.

#### ServiceStatus

Service status options.

#### DatabaseConfig

Database configuration schema.

**Methods:**

- `validate_port()`
- `validate_password()`

#### RedisConfig

Redis configuration schema.

#### SecurityConfig

Security configuration schema.

**Methods:**

- `validate_jwt_secret()`
- `validate_encryption_key()`

#### MonitoringConfig

Monitoring and observability configuration.

#### LoggingConfig

Logging configuration schema.

#### NetworkConfig

Network configuration schema.

#### ServiceConfig

Individual service configuration.

#### ExternalServiceConfig

External service integration configuration.

#### FeatureFlagConfig

Feature flag configuration.

#### ISPConfiguration

Complete ISP container configuration.

**Methods:**

- `validate_configuration()`
- `get_feature_flag()`
- `get_service()`
- `get_external_service()`
- `is_feature_enabled()`
- `get_enabled_services()`
- `to_dict()`
- `from_dict()`

*Source: /home/dotmac_framework/src/dotmac_shared/container_config/schemas/config_schemas.py*

## dotmac_shared.container_config.schemas.feature_schemas

Feature flag and capability schemas.

### Classes

#### FeatureStatus

Feature status options.

#### FeatureCategory

Feature categories for organization.

#### RolloutStrategy

Feature rollout strategies.

#### FeatureDefinition

Feature definition and metadata.

**Methods:**

- `validate_feature_name()`
- `validate_available_plans()`
- `is_available_for_plan()`
- `get_config_for_plan()`

#### FeatureFlag

Individual feature flag instance for a tenant.

**Methods:**

- `is_enabled_for_user()`
- `evaluate_conditions()`

#### PlanFeatures

Feature configuration for a subscription plan.

**Methods:**

- `get_feature_config()`
- `is_feature_available()`
- `get_feature_limit()`

#### FeatureConfiguration

Configuration for a feature within a plan.

*Source: /home/dotmac_framework/src/dotmac_shared/container_config/schemas/feature_schemas.py*

## dotmac_shared.container_config.schemas.tenant_schemas

Tenant-specific schemas and data models.

### Classes

#### SubscriptionPlan

Available subscription plans.

#### EnvironmentType

Environment types.

#### TenantStatus

Tenant status options.

#### TenantLimits

Resource limits for a tenant.

**Methods:**

- `validate_positive_float()`

#### TenantMetadata

Additional metadata for a tenant.

#### TenantSettings

Tenant-specific settings and preferences.

**Methods:**

- `validate_session_timeout()`

#### TenantInfo

Complete tenant information model.

**Methods:**

- `validate_slug()`
- `validate_email()`
- `validate_domains()`
- `is_active()`
- `is_subscription_active()`
- `get_plan_features()`
- `can_access_feature()`
- `get_resource_usage_percentage()`
- `to_config_context()`

*Source: /home/dotmac_framework/src/dotmac_shared/container_config/schemas/tenant_schemas.py*

## dotmac_shared.container_monitoring.__init__

DotMac Container Monitoring & Health Service

Provides comprehensive health monitoring and lifecycle management for
ISP containers post-provisioning.

*Source: /home/dotmac_framework/src/dotmac_shared/container_monitoring/__init__.py*

## dotmac_shared.container_monitoring.collectors.__init__

Metrics Collectors

Specialized collectors for different types of metrics:

- System metrics (CPU, memory, disk, network)
- Application metrics (requests, responses, errors)
- Database metrics (connections, queries, performance)

*Source: /home/dotmac_framework/src/dotmac_shared/container_monitoring/collectors/__init__.py*

## dotmac_shared.container_monitoring.collectors.app_metrics

Application Metrics Collector

Collects application-specific metrics from ISP framework containers including:

- HTTP request/response metrics
- API endpoint performance
- Error rates and types
- Custom business metrics

### Classes

#### EndpointMetrics

Metrics for a specific API endpoint

#### ApplicationMetricsSnapshot

Comprehensive application metrics snapshot

**Methods:**

- `to_dict()`

#### AppMetricsCollector

Application metrics collector for ISP framework containers

Collects comprehensive application-level metrics including:

- HTTP/API request and response metrics
- Application resource usage
- Business-specific metrics (tenants, customers, billing)
- Health check results
- Custom application metrics

**Methods:**

- `__init__()`
- `async collect_application_metrics()`
- `async _collect_prometheus_metrics()`
- `async _collect_health_metrics()`
- `async _collect_api_metrics()`
- `async _collect_business_metrics()`
- `async _collect_custom_metrics()`
- `async _fetch_prometheus_data()`
- `async _extract_endpoints_from_openapi()`
- `async _parse_api_metrics_response()`
- `clear_cache()`

*Source: /home/dotmac_framework/src/dotmac_shared/container_monitoring/collectors/app_metrics.py*

## dotmac_shared.container_monitoring.collectors.database_metrics

Database Metrics Collector

Collects comprehensive database performance metrics from containers including:

- Connection pool status and utilization
- Query performance and execution statistics
- Cache hit ratios and memory usage
- Replication lag and consistency metrics

### Classes

#### ConnectionPoolMetrics

Database connection pool metrics

#### QueryPerformanceMetrics

Database query performance metrics

#### CacheMetrics

Database cache and memory metrics

#### ReplicationMetrics

Database replication metrics

#### DatabaseMetricsSnapshot

Comprehensive database metrics snapshot

**Methods:**

- `to_dict()`

#### DatabaseMetricsCollector

Database metrics collector for various database types

Supports comprehensive metrics collection for:

- PostgreSQL
- Redis
- MySQL/MariaDB
- MongoDB
- SQLite

**Methods:**

- `__init__()`
- `async collect_database_metrics()`
- `async _collect_single_database_metrics()`
- `async _collect_postgresql_metrics()`
- `async _collect_redis_metrics()`
- `async _collect_mysql_metrics()`
- `async _collect_mongodb_metrics()`
- `async _collect_sqlite_metrics()`
- `async _collect_generic_database_metrics()`
- `clear_cache()`

*Source: /home/dotmac_framework/src/dotmac_shared/container_monitoring/collectors/database_metrics.py*

## dotmac_shared.container_monitoring.collectors.system_metrics

System Metrics Collector

Collects detailed system-level metrics from containers including:

- CPU utilization and load
- Memory usage and limits
- Disk I/O and storage
- Network traffic and connections

### Classes

#### SystemMetricsSnapshot

Detailed system metrics snapshot

**Methods:**

- `to_dict()`

#### SystemMetricsCollector

System metrics collector for containers

Provides detailed system-level monitoring including:

- Comprehensive CPU metrics and per-core usage
- Detailed memory utilization including cache and swap
- Disk I/O operations and storage usage
- Network traffic analysis and error tracking
- Process and thread monitoring

**Methods:**

- `__init__()`
- `async collect_system_metrics()`
- `async _collect_cpu_metrics()`
- `async _collect_memory_metrics()`
- `async _collect_disk_metrics()`
- `async _collect_network_metrics()`
- `async _collect_process_metrics()`
- `async start_continuous_collection()`
- `clear_cache()`

*Source: /home/dotmac_framework/src/dotmac_shared/container_monitoring/collectors/system_metrics.py*

## dotmac_shared.container_monitoring.core.health_monitor

Container Health Monitor

Provides comprehensive health monitoring for ISP containers including
system metrics, application endpoints, and database connectivity.

### Classes

#### HealthStatus

Container health status levels

#### HealthCheck

Individual health check result

#### HealthReport

Complete health report for a container

**Methods:**

- `add_check()`

#### ContainerHealthMonitor

Container health monitoring service

Monitors container health including:

- Container runtime status
- System resource usage
- Application endpoint health
- Database connectivity

**Methods:**

- `__init__()`
- `async monitor_container_health()`
- `async _check_container_status()`
- `async _check_system_resources()`
- `async _check_application_endpoints()`
- `async _check_database_connectivity()`
- `async _test_db_connection()`

#### BaseModel

*Source: /home/dotmac_framework/src/dotmac_shared/container_monitoring/core/health_monitor.py*

## dotmac_shared.container_monitoring.core.lifecycle_manager

Container Lifecycle Manager

Manages container lifecycle operations including start, stop, restart,
and scale operations with proper event tracking and error handling.

### Classes

#### LifecycleAction

Container lifecycle actions

#### LifecycleEventType

Lifecycle event types

#### LifecycleEvent

Container lifecycle event

#### LifecycleResult

Result of lifecycle operation

#### ContainerLifecycleManager

Container lifecycle management service

Manages container operations including:

- Basic lifecycle (start, stop, restart)
- Advanced operations (pause, scale)
- Event tracking and auditing
- Error handling and recovery

**Methods:**

- `__init__()`
- `async manage_container_lifecycle()`
- `async _execute_action()`
- `async _start_container()`
- `async _stop_container()`
- `async _restart_container()`
- `async _pause_container()`
- `async _unpause_container()`
- `async _scale_up_container()`
- `async _scale_down_container()`
- `async _kill_container()`
- `async _remove_container()`
- `async _wait_for_status()`
- `async _emit_event()`
- `async _emit_state_change_event()`
- `async _emit_error_event()`

*Source: /home/dotmac_framework/src/dotmac_shared/container_monitoring/core/lifecycle_manager.py*

## dotmac_shared.container_monitoring.core.scaling_advisor

Scaling Advisor

Analyzes performance metrics and provides intelligent auto-scaling
recommendations based on customer growth patterns and resource utilization.

### Classes

#### ScalingAction

Scaling recommendations

#### ScalingReason

Reasons for scaling recommendations

#### ScalingUrgency

Urgency levels for scaling actions

#### ScalingRecommendation

Scaling recommendation with detailed analysis

**Methods:**

- `to_dict()`

#### ScalingThresholds

Configurable thresholds for scaling decisions

#### ScalingAdvisor

Intelligent scaling advisor for container resources

Analyzes metrics trends and provides scaling recommendations based on:

- Resource utilization patterns
- Application performance metrics
- Customer growth trends
- Cost optimization opportunities
- Performance degradation indicators

**Methods:**

- `__init__()`
- `async recommend_scaling()`
- `async _analyze_resource_utilization()`
- `async _analyze_application_performance()`
- `async _analyze_growth_trends()`
- `async _analyze_cost_optimization()`
- `async _determine_final_recommendation()`
- `async _generate_implementation_guidance()`
- `async _store_recommendation()`
- `get_recommendation_history()`

*Source: /home/dotmac_framework/src/dotmac_shared/container_monitoring/core/scaling_advisor.py*

## dotmac_shared.core.__init__

Core shared utilities for DotMac Framework.
Provides common functionality across all platforms.

*Source: /home/dotmac_framework/src/dotmac_shared/core/__init__.py*

## dotmac_shared.core.exceptions

Core exceptions for DotMac Framework.
Provides consistent exception handling across all platforms.

### Classes

#### DotMacException

Base exception for DotMac Framework.

**Methods:**

- `__init__()`
- `to_dict()`
- `to_http_exception()`

#### ValidationError

Exception raised for validation errors.

**Methods:**

- `__init__()`

#### AuthenticationError

Exception raised for authentication failures.

**Methods:**

- `__init__()`

#### AuthorizationError

Exception raised for authorization failures.

**Methods:**

- `__init__()`

#### EntityNotFoundError

Exception raised when an entity is not found.

**Methods:**

- `__init__()`

#### BusinessRuleError

Exception raised for business rule violations.

**Methods:**

- `__init__()`

#### ServiceError

Exception raised for service-level errors.

**Methods:**

- `__init__()`

#### RateLimitError

Exception raised when rate limit is exceeded.

**Methods:**

- `__init__()`

#### TenantNotFoundError

Exception raised when tenant is not found.

**Methods:**

- `__init__()`

#### ConfigurationError

Exception raised for configuration errors.

**Methods:**

- `__init__()`

#### ExternalServiceError

Exception raised for external service errors.

**Methods:**

- `__init__()`

*Source: /home/dotmac_framework/src/dotmac_shared/core/exceptions.py*

## dotmac_shared.core.pagination

Pagination utilities for DotMac Framework APIs.
Provides consistent pagination across all platforms.

### Classes

#### PaginationParams

Pagination parameters for API requests.

**Methods:**

- `offset()`
- `limit()`
- `to_dict()`

#### PaginationMeta

Pagination metadata for API responses.

**Methods:**

- `create()`

#### PaginatedResponse

Generic paginated response.

*Source: /home/dotmac_framework/src/dotmac_shared/core/pagination.py*

## dotmac_shared.customer_portal.__init__

Shared Customer Portal Service

Unified customer portal functionality shared between ISP Framework and Management Platform.
Implements DRY principles by consolidating common portal operations.

*Source: /home/dotmac_framework/src/dotmac_shared/customer_portal/__init__.py*

## dotmac_shared.customer_portal.adapters.__init__

Customer portal adapters.

Platform-specific adapters for integrating with ISP Framework and Management Platform.

*Source: /home/dotmac_framework/src/dotmac_shared/customer_portal/adapters/__init__.py*

## dotmac_shared.customer_portal.adapters.base

Base adapter interface for customer portals.

Defines the contract that platform-specific adapters must implement.

### Classes

#### CustomerPortalAdapter

Abstract base class for platform-specific customer portal adapters.

This defines the interface that ISP and Management platform adapters
must implement to integrate with the unified portal service.

**Methods:**

- `__init__()`
- `async get_customer_info()`
- `async get_customer_services()`
- `async get_platform_data()`
- `async update_customer_custom_fields()`
- `async get_service_usage()`
- `async get_usage_summary()`
- `async validate_customer_access()`
- `async get_available_actions()`
- `async can_perform_action()`

*Source: /home/dotmac_framework/src/dotmac_shared/customer_portal/adapters/base.py*

## dotmac_shared.customer_portal.adapters.isp_adapter

ISP Framework adapter for customer portal.

Integrates the unified customer portal service with ISP-specific functionality.

### Classes

#### ISPPortalAdapter

ISP Framework-specific adapter for customer portal operations.

This adapter integrates with ISP Framework services to provide
customer portal functionality specific to ISP operations.

**Methods:**

- `__init__()`
- `async get_customer_info()`
- `async get_customer_services()`
- `async get_usage_summary()`
- `async get_platform_data()`
- `async update_customer_custom_fields()`
- `async get_service_usage()`
- `async get_available_actions()`
- `async _get_current_usage()`

*Source: /home/dotmac_framework/src/dotmac_shared/customer_portal/adapters/isp_adapter.py*

## dotmac_shared.customer_portal.adapters.management_adapter

Management Platform adapter for customer portal.

Integrates the unified customer portal service with Management Platform functionality.

### Classes

#### ManagementPortalAdapter

Management Platform-specific adapter for customer portal operations.

This adapter provides customer portal functionality for Management Platform
customers (partners, resellers, etc.) with different business logic than ISP customers.

**Methods:**

- `__init__()`
- `async get_customer_info()`
- `async get_customer_services()`
- `async get_usage_summary()`
- `async get_platform_data()`
- `async update_customer_custom_fields()`
- `async get_service_usage()`
- `async get_available_actions()`
- `async validate_customer_access()`

*Source: /home/dotmac_framework/src/dotmac_shared/customer_portal/adapters/management_adapter.py*

## dotmac_shared.customer_portal.core.__init__

Core customer portal functionality.

*Source: /home/dotmac_framework/src/dotmac_shared/customer_portal/core/__init__.py*

## dotmac_shared.customer_portal.core.auth

Portal Authentication Manager

Handles authentication for customer portals using existing auth services.

### Classes

#### PortalAuthenticationManager

Authentication manager for customer portals.

Leverages existing auth service while providing portal-specific functionality.

**Methods:**

- `__init__()`
- `async authenticate_customer()`
- `async validate_session()`
- `async refresh_session()`
- `async logout()`

*Source: /home/dotmac_framework/src/dotmac_shared/customer_portal/core/auth.py*

## dotmac_shared.customer_portal.core.schemas

Shared customer portal schemas.

Unified data models for customer portal functionality across platforms.

### Classes

#### PortalType

Portal deployment types.

#### CustomerStatus

Customer account status.

#### ServiceStatus

Service instance status.

#### CustomerDashboardData

Unified customer dashboard data structure.

#### ServiceSummary

Service summary for dashboard.

#### TicketSummary

Support ticket summary.

#### UsageSummary

Usage summary for ISP services.

#### UsageCharge

Additional usage charges.

#### CustomerPortalConfig

Portal configuration per platform.

#### PortalSessionData

Portal session information.

#### CustomerProfileUpdate

Customer profile update request.

#### ServiceUsageData

Service usage data.

#### BillingSummary

Billing summary information.

#### InvoiceSummary

Invoice summary.

#### PaymentSummary

Payment summary.

#### PaymentMethodSummary

Payment method summary.

*Source: /home/dotmac_framework/src/dotmac_shared/customer_portal/core/schemas.py*

## dotmac_shared.database.coordination

Database Coordination for DotMac Framework

### Classes

#### DatabaseCoordinator

Main database coordinator for connection and transaction management.

**Methods:**

- `__init__()`
- `async initialize()`
- `async _init_database_pool()`
- `async _init_redis_client()`
- `async get_connection()`
- `async execute_query()`
- `async execute_transaction()`
- `async check_health()`
- `async get_pool_stats()`
- `async _get_connection()`
- `async cleanup()`

#### ConnectionPool

Connection pool management.

**Methods:**

- `__init__()`
- `async initialize()`
- `async acquire()`
- `async release()`
- `async __aenter__()`
- `async __aexit__()`

#### TransactionManager

Transaction management utilities.

**Methods:**

- `async begin()`
- `async commit()`
- `async rollback()`
- `async transaction()`

#### DatabaseMigration

Database migration utilities.

**Methods:**

- `__init__()`
- `async _create_migration_table()`
- `async get_applied_migrations()`
- `async apply_migration()`
- `async _get_connection()`

#### TenantCoordinator

Multi-tenant database coordination.

**Methods:**

- `__init__()`
- `async get_tenant_database_url()`
- `async register_tenant_database()`
- `async get_tenant_connection()`
- `async execute_tenant_query()`
- `async list_active_tenants()`
- `async coordinate_tenant_migration()`
- `async _create_tenant_backup()`
- `async _apply_tenant_migration()`
- `async rollback_tenant_migration()`
- `async _get_tenant_backup_info()`
- `async _perform_tenant_rollback()`
- `async get_tenant_migration_status()`

#### MigrationCoordinator

Cross-platform migration coordination system.

**Methods:**

- `__init__()`
- `async initialize()`
- `async acquire_migration_lock()`
- `async release_migration_lock()`
- `async register_platform_schema_version()`
- `async get_platform_schema_version()`
- `async get_all_platform_versions()`
- `async check_cross_platform_consistency()`
- `async coordinate_multi_platform_migration()`
- `async _store_migration_coordination()`
- `async finalize_coordinated_migration()`
- `async get_migration_status()`
- `async cleanup_expired_locks()`

*Source: /home/dotmac_framework/src/dotmac_shared/database/coordination.py*

## dotmac_shared.database.session

Database session management for DotMac Framework.
Provides async database session dependency injection.

*Source: /home/dotmac_framework/src/dotmac_shared/database/session.py*

## dotmac_shared.database_init.__init__

Database Initialization Service for DotMac Framework

This package provides automated database setup for each ISP container, including:

- Per-container database creation (PostgreSQL instances)
- Schema migration execution for new databases
- Initial data seeding (admin users, default configs)
- Database health monitoring integration
- Backup configuration setup per database

Key Components:

- DatabaseCreator: Handles database and user creation
- SchemaManager: Manages schema migrations and updates
- SeedManager: Handles initial data seeding
- ConnectionValidator: Validates database connectivity and health

*Source: /home/dotmac_framework/src/dotmac_shared/database_init/__init__.py*

## dotmac_shared.database_init.core.connection_validator

Connection Validator - Validates database connectivity and health.

### Classes

#### HealthStatus

Health status enumeration.

#### HealthCheckResult

Result of a health check.

**Methods:**

- `__post_init__()`

#### ConnectionMetrics

Database connection metrics.

#### ConnectionValidator

Validates database connectivity and monitors health.

**Methods:**

- `__init__()`
- `async _get_connection_pool()`
- `async validate_database_health()`
- `async _check_basic_connectivity()`
- `async _check_schema_integrity()`
- `async _check_performance_metrics()`
- `async _check_disk_space()`
- `async get_connection_metrics()`
- `async test_query_performance()`
- `async cleanup()`

*Source: /home/dotmac_framework/src/dotmac_shared/database_init/core/connection_validator.py*

## dotmac_shared.database_init.core.database_creator

Database Creator - Handles database and user creation for ISP containers.

### Classes

#### DatabaseConfig

Configuration for database creation.

#### DatabaseInstance

Represents a created database instance.

**Methods:**

- `get_connection_params()`

#### DatabaseCreator

Creates and manages ISP databases.

**Methods:**

- `__init__()`
- `async _get_admin_connection()`
- `async create_isp_database()`
- `async _create_database_user()`
- `async _create_database()`
- `async _configure_database()`
- `async _get_existing_database_instance()`
- `async delete_isp_database()`
- `async list_isp_databases()`
- `async validate_database_connection()`

*Source: /home/dotmac_framework/src/dotmac_shared/database_init/core/database_creator.py*

## dotmac_shared.database_init.core.schema_manager

Schema Manager - Handles database schema migrations and management.

### Classes

#### SchemaManager

Manages database schema migrations and initialization.

**Methods:**

- `__init__()`
- `async initialize_schema()`
- `async _validate_database_connection()`
- `async _setup_migration_environment()`
- `async _create_env_py()`
- `async _create_script_mako()`
- `async _initialize_alembic()`
- `async _run_migrations()`
- `async _load_base_schema()`
- `async _get_current_revision()`
- `async _get_available_migrations()`
- `async _apply_migration()`
- `async _create_pre_migration_backup()`
- `async _store_backup_metadata()`
- `async _execute_migration_file()`
- `async rollback_to_revision()`
- `async _get_rollback_path()`
- `async _apply_rollback_migration()`
- `async _execute_rollback_file()`
- `async _get_previous_revision()`
- `async get_rollback_info()`
- `async _get_backup_info()`
- `async _verify_schema_integrity()`
- `async get_schema_info()`

*Source: /home/dotmac_framework/src/dotmac_shared/database_init/core/schema_manager.py*

## dotmac_shared.database_init.core.seed_manager

Seed Manager - Handles initial data seeding for ISP databases.

### Classes

#### SeedManager

Manages initial data seeding for ISP databases.

**Methods:**

- `__init__()`
- `async seed_initial_data()`
- `async _validate_database_connection()`
- `async _generate_seed_context()`
- `async _seed_system_data()`
- `async _seed_admin_users()`
- `async _create_default_admin_user()`
- `async _seed_default_configurations()`
- `async _create_default_configurations()`
- `async _seed_sample_data()`
- `async _create_sample_service_plans()`
- `async _load_template()`
- `async _execute_sql()`
- `async _verify_seeded_data()`
- `async get_seed_status()`
- `async reset_seed_data()`

*Source: /home/dotmac_framework/src/dotmac_shared/database_init/core/seed_manager.py*

## dotmac_shared.deployment.__init__

Deployment utilities for DotMac platforms.

This module provides tools for managing tenant container provisioning,
Kubernetes integration, and deployment automation.

*Source: /home/dotmac_framework/src/dotmac_shared/deployment/__init__.py*

## dotmac_shared.deployment.tenant_provisioning

Tenant container provisioning logic for multi-tenant deployments.

This module provides the infrastructure for creating and managing
isolated tenant containers in Kubernetes.

### Classes

#### TenantProvisioningRequest

Request for provisioning a new tenant container.

#### TenantProvisioningResult

Result of tenant provisioning operation.

#### TenantResourceCalculator

Calculate resource requirements for tenant containers.

**Methods:**

- `calculate_resources()`

#### TenantNamespaceGenerator

Generate Kubernetes namespaces and resource names for tenants.

**Methods:**

- `generate_namespace()`
- `generate_container_name()`
- `generate_database_name()`
- `generate_redis_name()`
- `generate_urls()`

#### TenantConfigurationBuilder

Build tenant configuration from provisioning request.

**Methods:**

- `build_tenant_config()`

#### TenantProvisioningEngine

Main engine for provisioning tenant containers.

**Methods:**

- `__init__()`
- `async provision_tenant()`
- `async _provision_infrastructure()`
- `async _deploy_tenant_container()`
- `async _configure_ssl()`
- `async _verify_deployment()`
- `async get_tenant_status()`
- `async list_provisioned_tenants()`
- `async deprovision_tenant()`

*Source: /home/dotmac_framework/src/dotmac_shared/deployment/tenant_provisioning.py*

## dotmac_shared.device_management.__init__

DotMac Device Management Framework

Comprehensive device management system providing:

- Device inventory and asset tracking
- SNMP monitoring and telemetry collection
- Network topology discovery and management
- Hardware lifecycle management
- MAC address registry and tracking

This is the main package entry point.

*Source: /home/dotmac_framework/src/dotmac_shared/device_management/__init__.py*

## dotmac_shared.device_management.dotmac_device_management.__init__

DotMac Device Management Framework

Comprehensive device management system providing:

- Device inventory and asset tracking
- SNMP monitoring and telemetry collection
- Network topology discovery and management
- Hardware lifecycle management
- MAC address registry and tracking
- Configuration management and templates
- Device health monitoring and alerting

This framework standardizes device management across all DotMac modules.

*Source: /home/dotmac_framework/src/dotmac_shared/device_management/dotmac_device_management/__init__.py*

## dotmac_shared.device_management.dotmac_device_management.adapters.__init__

Device Management Platform Adapters.

*Source: /home/dotmac_framework/src/dotmac_shared/device_management/dotmac_device_management/adapters/__init__.py*

## dotmac_shared.device_management.dotmac_device_management.adapters.platform_adapter

Platform Adapters for Device Management.

Provides adapters to integrate device management with different DotMac platform modules.

### Classes

#### BaseDeviceAdapter

Base adapter for platform integration.

**Methods:**

- `__init__()`
- `async adapt_device_data()`
- `async export_device_data()`
- `async create_device_from_platform()`
- `async sync_device_to_platform()`

#### ISPDeviceAdapter

Adapter for ISP Framework integration.

**Methods:**

- `async adapt_device_data()`
- `async export_device_data()`

#### ManagementDeviceAdapter

Adapter for Management Platform integration.

**Methods:**

- `async adapt_device_data()`
- `async export_device_data()`

*Source: /home/dotmac_framework/src/dotmac_shared/device_management/dotmac_device_management/adapters/platform_adapter.py*

## dotmac_shared.device_management.dotmac_device_management.core.__init__

Core device management components.

*Source: /home/dotmac_framework/src/dotmac_shared/device_management/dotmac_device_management/core/__init__.py*

## dotmac_shared.device_management.dotmac_device_management.core.device_inventory

Device Inventory Management for DotMac Device Management Framework.

Provides comprehensive device inventory tracking with modules, interfaces,
and hardware lifecycle management.

### Classes

#### DeviceInventoryManager

Device inventory manager for database operations.

**Methods:**

- `__init__()`
- `async create_device()`
- `async get_device()`
- `async update_device()`
- `async delete_device()`
- `async list_devices()`
- `async add_device_module()`
- `async add_device_interface()`
- `async get_device_interfaces()`
- `async get_device_modules()`
- `async update_interface_status()`
- `async search_devices()`
- `async get_device_count_by_type()`
- `async get_devices_by_site()`

#### DeviceInventoryService

High-level service for device inventory operations.

**Methods:**

- `__init__()`
- `async provision_device()`
- `async decommission_device()`
- `async get_device_health_summary()`

*Source: /home/dotmac_framework/src/dotmac_shared/device_management/dotmac_device_management/core/device_inventory.py*

## dotmac_shared.device_management.dotmac_device_management.core.device_monitoring

Device Monitoring Management for DotMac Device Management Framework.

Provides SNMP monitoring, telemetry collection, and device health tracking.

### Classes

#### DeviceMonitoringManager

Device monitoring manager for database operations.

**Methods:**

- `__init__()`
- `async create_monitoring_record()`
- `async get_latest_metrics()`
- `async get_metrics_history()`
- `async get_device_health_status()`
- `async get_monitoring_statistics()`
- `async cleanup_old_records()`

#### DeviceMonitoringService

High-level service for device monitoring operations.

**Methods:**

- `__init__()`
- `async create_snmp_monitor()`
- `async collect_snmp_metrics()`
- `async create_telemetry_monitor()`
- `async get_device_monitoring_overview()`
- `async create_health_check()`
- `async get_trending_metrics()`

*Source: /home/dotmac_framework/src/dotmac_shared/device_management/dotmac_device_management/core/device_monitoring.py*

## dotmac_shared.device_management.dotmac_device_management.core.mac_registry

MAC Address Registry Management for DotMac Device Management Framework.

Provides MAC address tracking, OUI vendor identification, and device association.

### Classes

#### MacRegistryManager

MAC address registry manager for database operations.

**Methods:**

- `__init__()`
- `async register_mac_address()`
- `async get_mac_address()`
- `async update_mac_address()`
- `async delete_mac_address()`
- `async search_mac_addresses()`
- `async get_device_mac_addresses()`
- `async get_vendor_statistics()`
- `async get_recent_mac_addresses()`
- `async cleanup_stale_records()`

#### MacRegistryService

High-level service for MAC address registry operations.

**Methods:**

- `__init__()`
- `async discover_device_macs()`
- `async track_mac_movement()`
- `async get_mac_address_details()`
- `async generate_mac_report()`
- `async bulk_register_macs()`

*Source: /home/dotmac_framework/src/dotmac_shared/device_management/dotmac_device_management/core/mac_registry.py*

## dotmac_shared.device_management.dotmac_device_management.core.models

Device management models for DotMac Device Management Framework.

### Classes

#### DeviceStatus

Device status enumeration.

#### DeviceType

Device type enumeration.

#### InterfaceType

Interface type enumeration.

#### InterfaceStatus

Interface status enumeration.

#### MonitorType

Monitoring type enumeration.

#### NodeType

Network node type enumeration.

#### LinkType

Network link type enumeration.

#### Device

Device model for network equipment tracking.

#### DeviceModule

Device module/card model.

#### DeviceInterface

Device interface/port model.

#### MacAddress

MAC address registry model.

#### MonitoringRecord

Device monitoring record model.

#### NetworkNode

Network topology node model.

#### NetworkLink

Network topology link model.

#### ConfigTemplate

Device configuration template model.

#### ConfigIntent

Device configuration intent model.

*Source: /home/dotmac_framework/src/dotmac_shared/device_management/dotmac_device_management/core/models.py*

## dotmac_shared.device_management.dotmac_device_management.core.network_topology

Network Topology Management for DotMac Device Management Framework.

Provides network graph management with nodes, links, and path finding capabilities.

### Classes

#### NetworkTopologyManager

Network topology manager for database operations.

**Methods:**

- `__init__()`
- `async create_node()`
- `async get_node()`
- `async update_node()`
- `async delete_node()`
- `async create_link()`
- `async get_link()`
- `async get_node_links()`
- `async get_node_neighbors()`
- `async find_shortest_path()`
- `async get_site_topology()`
- `async get_topology_statistics()`
- `async list_nodes()`
- `async list_links()`

#### NetworkTopologyService

High-level service for network topology operations.

**Methods:**

- `__init__()`
- `async build_device_topology()`
- `async discover_network_paths()`
- `async get_device_connectivity()`
- `async analyze_network_redundancy()`

*Source: /home/dotmac_framework/src/dotmac_shared/device_management/dotmac_device_management/core/network_topology.py*

## dotmac_shared.device_management.dotmac_device_management.core.schemas

Device Management Framework Schemas.

Pydantic schemas for API serialization and validation.

### Classes

#### DeviceCreateRequest

Schema for device creation request.

**Methods:**

- `validate_device_id()`
- `validate_management_ip()`

#### DeviceResponse

Schema for device response.

#### DeviceModuleResponse

Schema for device module response.

#### DeviceInterfaceResponse

Schema for device interface response.

#### MacAddressResponse

Schema for MAC address response.

#### MonitoringRecordResponse

Schema for monitoring record response.

#### NetworkNodeResponse

Schema for network node response.

#### NetworkLinkResponse

Schema for network link response.

#### ConfigTemplateResponse

Schema for configuration template response.

#### ConfigIntentResponse

Schema for configuration intent response.

#### TopologyResponse

Schema for topology response.

#### DeviceHealthSummary

Schema for device health summary.

#### MonitoringOverview

Schema for monitoring overview.

#### NetworkPathResponse

Schema for network path response.

#### DeviceConnectivityResponse

Schema for device connectivity response.

#### MacAddressCreateRequest

Schema for MAC address registration request.

**Methods:**

- `validate_mac_address()`

#### NetworkNodeCreateRequest

Schema for network node creation request.

#### NetworkLinkCreateRequest

Schema for network link creation request.

#### Config

#### Config

#### Config

#### Config

#### Config

#### Config

#### Config

#### Config

#### Config

#### Config

*Source: /home/dotmac_framework/src/dotmac_shared/device_management/dotmac_device_management/core/schemas.py*

## dotmac_shared.device_management.dotmac_device_management.exceptions

Device Management Framework Exceptions.

### Classes

#### DeviceManagementError

Base exception for device management operations.

#### DeviceInventoryError

Exception for device inventory operations.

#### DeviceMonitoringError

Exception for device monitoring operations.

#### MacRegistryError

Exception for MAC address registry operations.

#### NetworkTopologyError

Exception for network topology operations.

#### DeviceConfigError

Exception for device configuration operations.

#### DeviceLifecycleError

Exception for device lifecycle operations.

#### SNMPError

Exception for SNMP operations.

#### TopologyAnalysisError

Exception for topology analysis operations.

*Source: /home/dotmac_framework/src/dotmac_shared/device_management/dotmac_device_management/exceptions.py*

## dotmac_shared.device_management.dotmac_device_management.services.__init__

Device Management Services.

*Source: /home/dotmac_framework/src/dotmac_shared/device_management/dotmac_device_management/services/__init__.py*

## dotmac_shared.device_management.dotmac_device_management.services.device_service

Unified Device Service.

High-level service that orchestrates all device management operations.

### Classes

#### DeviceService

Unified service for all device management operations.

**Methods:**

- `__init__()`
- `async create_device()`
- `async get_device()`
- `async update_device()`
- `async delete_device()`
- `async list_devices()`
- `async setup_device_monitoring()`
- `async get_device_health()`
- `async collect_device_metrics()`
- `async register_device_macs()`
- `async lookup_mac_address()`
- `async add_device_to_topology()`
- `async create_device_connection()`
- `async find_device_path()`
- `async analyze_network_topology()`
- `async provision_device()`
- `async deploy_device()`
- `async decommission_device()`
- `async get_device_overview()`
- `async bulk_device_operation()`

*Source: /home/dotmac_framework/src/dotmac_shared/device_management/dotmac_device_management/services/device_service.py*

## dotmac_shared.device_management.dotmac_device_management.utils.__init__

Device Management Utilities.

*Source: /home/dotmac_framework/src/dotmac_shared/device_management/dotmac_device_management/utils/__init__.py*

## dotmac_shared.device_management.dotmac_device_management.utils.snmp_client

SNMP Client and Collector utilities for device monitoring.

Provides SNMP query capabilities and metric collection functionality.

### Classes

#### SNMPConfig

SNMP configuration parameters.

#### SNMPClient

SNMP client for querying network devices.

**Methods:**

- `__init__()`
- `async get()`
- `async walk()`
- `async get_bulk()`
- `async test_connectivity()`

#### SNMPCollector

High-level SNMP metrics collector.

**Methods:**

- `__init__()`
- `async collect_system_info()`
- `async collect_interface_stats()`
- `async collect_cpu_memory_stats()`
- `async collect_comprehensive_metrics()`
- `async test_device_reachability()`

*Source: /home/dotmac_framework/src/dotmac_shared/device_management/dotmac_device_management/utils/snmp_client.py*

## dotmac_shared.device_management.dotmac_device_management.workflows.__init__

Device Management Workflows.

*Source: /home/dotmac_framework/src/dotmac_shared/device_management/dotmac_device_management/workflows/__init__.py*

## dotmac_shared.device_management.dotmac_device_management.workflows.lifecycle_manager

Device Lifecycle Management workflows.

Handles complete device lifecycle from provisioning to decommissioning.

### Classes

#### LifecycleStage

Device lifecycle stages.

#### LifecycleAction

Lifecycle actions.

#### DeviceLifecycleManager

Manages complete device lifecycle workflows.

**Methods:**

- `__init__()`
- `async execute_lifecycle_action()`
- `async _execute_provision()`
- `async _execute_deploy()`
- `async _execute_activate()`
- `async _execute_maintenance()`
- `async _execute_decommission()`
- `async _execute_upgrade()`
- `async _execute_migrate()`
- `async _execute_retire()`
- `async _validate_deployment()`
- `async _test_device_connectivity()`
- `async _validate_device_health()`
- `async _execute_maintenance_task()`
- `async _handle_planning()`
- `async _handle_provisioning()`
- `async _handle_deployment()`
- `async _handle_active()`
- `async _handle_maintenance()`
- `async _handle_upgrade()`
- `async _handle_migration()`
- `async _handle_decommissioning()`
- `async _handle_retired()`

*Source: /home/dotmac_framework/src/dotmac_shared/device_management/dotmac_device_management/workflows/lifecycle_manager.py*

## dotmac_shared.events.__init__

DotMac Events - Event-Driven Architecture Toolkit

This package provides comprehensive event streaming and processing capabilities:

- Event Bus with Redis and Kafka adapters
- Transactional Outbox pattern implementation
- Schema Registry for event validation
- Consumer groups and partition management
- Dead letter queue support
- Multi-tenant event isolation

*Source: /home/dotmac_framework/src/dotmac_shared/events/__init__.py*

## dotmac_shared.events.adapters.__init__

Event streaming adapters for different backends.

Provides concrete implementations of the EventAdapter interface:

- MemoryEventAdapter: In-memory adapter for testing
- RedisEventAdapter: Redis Streams adapter for production
- KafkaEventAdapter: Apache Kafka adapter for high-throughput scenarios

*Source: /home/dotmac_framework/src/dotmac_shared/events/adapters/__init__.py*

## dotmac_shared.events.adapters.kafka_adapter

Apache Kafka Event Adapter.

Provides Kafka implementation of the EventAdapter interface.
Uses aiokafka for high-throughput, distributed event streaming.

### Classes

#### KafkaConfig

Configuration for Kafka event adapter.

**Methods:**

- `producer_config()`
- `consumer_config()`

#### KafkaEventAdapter

Apache Kafka event adapter.

Provides high-throughput, distributed event streaming using Kafka with:

- Partitioned topics for scalability
- Consumer groups for load balancing
- Configurable acknowledgment levels
- Exactly-once semantics (when configured)

**Methods:**

- `__init__()`
- `async connect()`
- `async disconnect()`
- `async publish()`
- `async publish_batch()`
- `async subscribe()`
- `async consume()`
- `async create_topic()`
- `async delete_topic()`
- `async list_topics()`
- `async commit_offset()`
- `async _kafka_consumer_loop()`

*Source: /home/dotmac_framework/src/dotmac_shared/events/adapters/kafka_adapter.py*

## dotmac_shared.events.adapters.memory_adapter

In-Memory Event Adapter for Testing.

Provides an in-memory implementation of the EventAdapter interface.
Useful for testing and development scenarios where external dependencies
are not available or desired.

### Classes

#### MemoryConfig

Configuration for memory event adapter.

#### MemoryTopic

In-memory topic implementation.

**Methods:**

- `__init__()`
- `async append()`
- `async consume()`

#### MemoryEventAdapter

In-memory event adapter for testing and development.

Provides a simple, fast event streaming implementation without
external dependencies. Events are stored in memory and will be
lost when the adapter is destroyed.

**Methods:**

- `__init__()`
- `async connect()`
- `async disconnect()`
- `async publish()`
- `async publish_batch()`
- `async subscribe()`
- `async consume()`
- `async create_topic()`
- `async delete_topic()`
- `async list_topics()`
- `async commit_offset()`
- `async _create_memory_topic()`
- `async _notify_subscribers()`
- `async _consumer_loop()`

*Source: /home/dotmac_framework/src/dotmac_shared/events/adapters/memory_adapter.py*

## dotmac_shared.events.adapters.redis_adapter

Redis Streams Event Adapter.

Provides Redis Streams implementation of the EventAdapter interface.
Uses Redis Streams for durable, ordered event streaming with consumer groups.

### Classes

#### RedisConfig

Configuration for Redis event adapter.

**Methods:**

- `redis_url()`

#### RedisEventAdapter

Redis Streams event adapter.

Provides durable event streaming using Redis Streams with:

- Consumer groups for load balancing
- Message acknowledgment
- Dead letter handling for failed messages
- Automatic stream trimming

**Methods:**

- `__init__()`
- `async connect()`
- `async disconnect()`
- `async publish()`
- `async publish_batch()`
- `async subscribe()`
- `async consume()`
- `async create_topic()`
- `async delete_topic()`
- `async list_topics()`
- `async commit_offset()`
- `async _redis_consumer_loop()`

*Source: /home/dotmac_framework/src/dotmac_shared/events/adapters/redis_adapter.py*

## dotmac_shared.events.core.__init__

Core event system components.

Provides the fundamental building blocks for event-driven architecture:

- Event models and metadata
- Event bus interface
- Outbox pattern implementation
- Schema registry for validation

*Source: /home/dotmac_framework/src/dotmac_shared/events/core/__init__.py*

## dotmac_shared.events.core.event_bus

Core Event Bus implementation.

Provides the main event bus interface with pluggable adapters for different backends.
Supports async/await patterns, error handling, and multi-tenant event routing.

### Classes

#### EventAdapter

Abstract base class for event streaming adapters.

All event adapters (Redis, Kafka, etc.) must implement this interface.

**Methods:**

- `__init__()`
- `async connect()`
- `async disconnect()`
- `async publish()`
- `async publish_batch()`
- `async subscribe()`
- `async consume()`
- `async create_topic()`
- `async delete_topic()`
- `async list_topics()`
- `async commit_offset()`
- `connected()`
- `adapter_type()`

#### EventBus

Main Event Bus implementation.

Provides high-level event publishing and consumption with support for:

- Multiple backend adapters (Redis, Kafka, Memory)
- Async/await event processing
- Error handling and retries
- Multi-tenant event isolation
- Dead letter queues
- Event filtering and transformation

**Methods:**

- `__init__()`
- `async start()`
- `async stop()`
- `async publish()`
- `async publish_batch()`
- `async subscribe()`
- `async consume()`
- `async create_topic()`
- `async _send_to_dead_letter()`
- `async health_check()`

*Source: /home/dotmac_framework/src/dotmac_shared/events/core/event_bus.py*

## dotmac_shared.events.core.models

Core event models and data structures.

Pydantic v2 compatible models for event streaming, metadata, and configuration.

### Classes

#### EventBusError

Base exception for Event Bus operations.

#### PublishError

Exception raised when event publishing fails.

#### SubscriptionError

Exception raised when subscription operations fail.

#### ValidationError

Exception raised when event validation fails.

#### EventMetadata

Event metadata for tracing, correlation, and routing.

Supports distributed tracing, multi-tenancy, and event correlation.

**Methods:**

- `validate_ids()`
- `validate_context_ids()`

#### EventRecord

Core event record model.

Represents a single event with its data, metadata, and routing information.

**Methods:**

- `validate_event_type()`
- `validate_data()`
- `event_id()`
- `tenant_id()`

#### PublishResult

Result of publishing an event to the event bus.

#### ConsumerRecord

Event record as received by a consumer.

Includes additional consumer-specific metadata.

#### AdapterConfig

Base configuration for event adapters.

**Methods:**

- `validate_connection_string()`

#### TopicConfig

Configuration for event topics/streams.

**Methods:**

- `validate_topic_name()`

#### ConsumerConfig

Configuration for event consumers.

**Methods:**

- `validate_consumer_group()`
- `validate_topics()`

*Source: /home/dotmac_framework/src/dotmac_shared/events/core/models.py*

## dotmac_shared.events.core.outbox

Transactional Outbox Pattern Implementation.

Provides reliable event publishing with database transaction guarantees:

- Store events in database table within same transaction
- Background processor publishes events to event bus
- Handles failures with retry logic and dead letter queue
- Supports multi-tenant isolation

### Classes

#### OutboxEventStatus

Status enumeration for outbox events.

#### OutboxEvent

Database model for outbox events.

Stores events that need to be published reliably with transaction guarantees.

**Methods:**

- `to_event_record()`
- `from_event_record()`

#### OutboxManager

Manages transactional outbox operations.

Provides methods to store events in database and process them reliably.

**Methods:**

- `__init__()`
- `async store_event()`
- `async store_events_batch()`
- `async get_pending_events()`
- `async mark_processing()`
- `async mark_published()`
- `async mark_failed()`
- `async reset_stuck_events()`
- `async cleanup_old_events()`
- `async get_stats()`

*Source: /home/dotmac_framework/src/dotmac_shared/events/core/outbox.py*

## dotmac_shared.events.core.schema_registry

Schema Registry for Event Validation.

Provides event schema management and validation using JSON Schema:

- Register and version event schemas
- Validate events against schemas
- Schema evolution with compatibility checks
- Multi-tenant schema isolation

### Classes

#### CompatibilityLevel

Schema compatibility levels for evolution.

#### SchemaVersionInfo

Schema version information.

**Methods:**

- `create()`

#### SubjectSchema

Complete schema information for a subject.

**Methods:**

- `add_version()`
- `get_version()`
- `get_latest_version()`

#### ValidationResult

Result of schema validation.

#### RegistrationResult

Result of schema registration.

#### SchemaRegistry

In-memory schema registry with validation capabilities.

Manages event schemas with versioning and compatibility checking.
For production use, this should be backed by a database or external registry.

**Methods:**

- `__init__()`
- `async register_schema()`
- `async validate_event()`
- `async get_schema()`
- `async list_subjects()`
- `async list_versions()`
- `async _check_compatibility()`
- `async get_registry_stats()`

*Source: /home/dotmac_framework/src/dotmac_shared/events/core/schema_registry.py*

## dotmac_shared.events.sdk.__init__

Event SDK - High-level convenience APIs.

Provides simplified SDKs for common event-driven architecture patterns:

- EventBusSDK: High-level event bus operations
- OutboxSDK: Transactional outbox pattern
- SchemaRegistrySDK: Schema management and validation

*Source: /home/dotmac_framework/src/dotmac_shared/events/sdk/__init__.py*

## dotmac_shared.events.sdk.event_bus_sdk

Event Bus SDK - Simplified high-level API.

Provides a simplified interface for event publishing and consumption
with automatic adapter selection and sensible defaults.

### Classes

#### EventBusSDK

High-level Event Bus SDK.

Provides a simplified interface for event-driven applications with:

- Automatic adapter selection based on configuration
- Sensible defaults for common use cases
- Simplified publishing and subscription APIs
- Built-in error handling and retries

**Methods:**

- `__init__()`
- `async start()`
- `async stop()`
- `async publish()`
- `async publish_batch()`
- `async subscribe()`
- `async create_topic()`
- `async health_check()`
- `create_memory_bus()`
- `create_redis_bus()`
- `create_kafka_bus()`
- `async __aenter__()`
- `async __aexit__()`

*Source: /home/dotmac_framework/src/dotmac_shared/events/sdk/event_bus_sdk.py*

## dotmac_shared.events.sdk.outbox_sdk

Outbox SDK - Simplified transactional outbox API.

Provides a high-level interface for the transactional outbox pattern
with automatic background processing and simplified usage patterns.

### Classes

#### OutboxSDK

High-level Outbox SDK.

Provides simplified transactional outbox operations with:

- Automatic event processing and publishing
- Background worker for reliable event delivery
- Simple APIs for common patterns
- Built-in retry logic and error handling

**Methods:**

- `__init__()`
- `async start_processing()`
- `async stop_processing()`
- `async store_event()`
- `async store_events_batch()`
- `async process_pending_events()`
- `async get_stats()`
- `async cleanup_old_events()`
- `async reset_stuck_events()`
- `async _processing_loop()`
- `async __aenter__()`
- `async __aexit__()`

*Source: /home/dotmac_framework/src/dotmac_shared/events/sdk/outbox_sdk.py*

## dotmac_shared.events.sdk.schema_registry_sdk

Schema Registry SDK - Simplified schema management API.

Provides a high-level interface for event schema management
with automatic validation and simplified usage patterns.

### Classes

#### SchemaRegistrySDK

High-level Schema Registry SDK.

Provides simplified schema management operations with:

- Automatic schema validation
- Simplified registration APIs
- Built-in compatibility checking
- Multi-tenant schema isolation

**Methods:**

- `__init__()`
- `async register_event_schema()`
- `async validate_event_data()`
- `async get_event_schema()`
- `async list_event_types()`
- `async list_schema_versions()`
- `async register_common_schemas()`
- `async get_registry_stats()`
- `create_basic_schema()`
- `create_in_memory_registry()`

*Source: /home/dotmac_framework/src/dotmac_shared/events/sdk/schema_registry_sdk.py*

## dotmac_shared.files.__init__

DotMac File Service - Document Generation Hub.

This package provides comprehensive file generation capabilities including:

- PDF document generation with ReportLab
- Excel and CSV export functionality
- Template-based content generation with Jinja2
- Image processing and chart generation
- Multi-tenant file storage abstraction
- Async background processing for large files

*Source: /home/dotmac_framework/src/dotmac_shared/files/__init__.py*

## dotmac_shared.files.adapters.__init__

Platform adapters for integrating file service with different platforms.

*Source: /home/dotmac_framework/src/dotmac_shared/files/adapters/__init__.py*

## dotmac_shared.files.adapters.isp_adapter

ISP Framework adapter for file service integration.

This module provides specialized file operations tailored for the ISP Framework
including customer invoices, usage reports, and network documentation.

### Classes

#### ISPCustomerInfo

ISP Customer information for document generation.

**Methods:**

- `to_dict()`

#### ISPServiceUsage

ISP Service usage data for reports.

**Methods:**

- `to_dict()`

#### ISPFileAdapter

File service adapter for ISP Framework integration.

**Methods:**

- `__init__()`
- `async generate_customer_invoice()`
- `async generate_usage_report()`
- `async generate_network_diagram()`
- `async export_customer_data()`
- `async generate_service_certificate()`

*Source: /home/dotmac_framework/src/dotmac_shared/files/adapters/isp_adapter.py*

## dotmac_shared.files.adapters.management_adapter

Management Platform adapter for file service integration.

This module provides specialized file operations for the Management Platform
including analytics reports, tenant management documents, and system exports.

### Classes

#### TenantInfo

Tenant information for management reports.

**Methods:**

- `to_dict()`

#### SystemMetrics

System performance metrics.

**Methods:**

- `to_dict()`

#### ManagementPlatformAdapter

File service adapter for Management Platform integration.

**Methods:**

- `__init__()`
- `async generate_tenant_report()`
- `async generate_analytics_dashboard_export()`
- `async generate_system_status_report()`
- `async generate_tenant_onboarding_package()`
- `async _create_analytics_excel()`

*Source: /home/dotmac_framework/src/dotmac_shared/files/adapters/management_adapter.py*

## dotmac_shared.files.cache_integration

File Service Cache Integration

Integrates file generation and template processing with Developer A's cache service
for high-performance template caching, rendered content caching, and metadata storage.

### Classes

#### CacheServiceTemplateStore

Template caching implementation using Developer A's cache service.

Provides distributed template caching with tenant isolation,
version control, and performance optimization.

**Methods:**

- `__init__()`
- `async store_template()`
- `async get_template()`
- `async store_rendered_content()`
- `async get_rendered_content()`
- `async invalidate_template()`
- `async get_template_metadata()`
- `async health_check()`
- `async get_stats()`

#### CacheServiceFileStorage

File metadata and reference caching using Developer A's cache service.

Provides caching for file metadata, storage locations, and access patterns
to optimize file operations and reduce storage backend calls.

**Methods:**

- `__init__()`
- `async store_file_metadata()`
- `async get_file_metadata()`
- `async track_file_access()`

#### FileServiceCacheIntegrationFactory

Factory for creating file service cache integration components.

**Methods:**

- `async create_template_store()`
- `async create_file_storage()`
- `async create_integrated_components()`

*Source: /home/dotmac_framework/src/dotmac_shared/files/cache_integration.py*

## dotmac_shared.files.core.__init__

Core file generation components.

*Source: /home/dotmac_framework/src/dotmac_shared/files/core/__init__.py*

## dotmac_shared.files.core.generators

File generation utilities for PDF, Excel, and CSV documents.

This module provides enhanced generators that build upon the existing
implementations in the ISP Framework while adding additional features like
template integration, better styling, and multi-tenant support.

### Classes

#### DocumentMetadata

Metadata for generated documents.

**Methods:**

- `__post_init__()`

#### PDFGenerator

Enhanced PDF generation with template support and advanced styling.

**Methods:**

- `__init__()`
- `generate_invoice()`
- `generate_report()`

#### ExcelGenerator

Enhanced Excel generation with advanced styling and chart support.

**Methods:**

- `__init__()`
- `generate_report()`

#### CSVGenerator

Enhanced CSV generation with proper encoding and streaming support.

**Methods:**

- `__init__()`
- `export_to_csv()`

*Source: /home/dotmac_framework/src/dotmac_shared/files/core/generators.py*

## dotmac_shared.files.core.processors

Image processing and chart generation utilities.

This module provides comprehensive image processing capabilities including
chart generation, QR codes, thumbnails, watermarking, and image optimization.

### Classes

#### ImageMetadata

Metadata for processed images.

**Methods:**

- `__post_init__()`

#### ImageProcessor

Comprehensive image processing with chart generation and optimization.

**Methods:**

- `__init__()`
- `generate_chart()`
- `generate_qr_code()`
- `create_thumbnail()`
- `add_watermark()`
- `optimize_image()`

*Source: /home/dotmac_framework/src/dotmac_shared/files/core/processors.py*

## dotmac_shared.files.storage.__init__

Storage abstraction layer for file management.

*Source: /home/dotmac_framework/src/dotmac_shared/files/storage/__init__.py*

## dotmac_shared.files.storage.tenant_storage

Tenant-aware storage management for multi-tenant file operations.

This module provides enhanced storage capabilities with tenant isolation,
access control, and quota management.

### Classes

#### TenantQuota

Tenant storage quota configuration.

**Methods:**

- `__post_init__()`

#### TenantUsage

Current tenant storage usage.

#### TenantStorageManager

Multi-tenant storage manager with quotas and access control.

**Methods:**

- `__init__()`
- `set_tenant_quota()`
- `get_tenant_quota()`
- `async get_tenant_usage()`
- `async _calculate_tenant_usage()`
- `async check_upload_allowed()`
- `async save_file()`
- `async get_file()`
- `async delete_file()`
- `async list_files()`
- `async get_file_info()`
- `async file_exists()`
- `async copy_file()`
- `async move_file()`
- `async cleanup_tenant_files()`
- `async get_tenant_stats()`

*Source: /home/dotmac_framework/src/dotmac_shared/files/storage/tenant_storage.py*

## dotmac_shared.files.templates.__init__

Template files for document generation.

*Source: /home/dotmac_framework/src/dotmac_shared/files/templates/__init__.py*

## dotmac_shared.files.validate_cache_integration

Simple validation script for file service cache integration.

Validates that the cache integration components can be imported
and basic functionality works without external dependencies.

*Source: /home/dotmac_framework/src/dotmac_shared/files/validate_cache_integration.py*

## dotmac_shared.health.__init__

Health check module for DotMac Framework.
Provides health endpoints and monitoring.

*Source: /home/dotmac_framework/src/dotmac_shared/health/__init__.py*

## dotmac_shared.health.comprehensive_checks

Comprehensive Health Check System for DotMac Framework

### Classes

#### HealthChecker

Main health checker for all system components.

**Methods:**

- `__init__()`
- `async check_all()`
- `async check_database()`
- `async check_redis()`
- `async check_external_services()`
- `async check_external_service()`
- `async _get_db_pool()`
- `async _get_redis_client()`

#### DatabaseHealthCheck

Detailed database health checks.

**Methods:**

- `__init__()`
- `async check_pool_health()`
- `async check_query_performance()`
- `async check_disk_space()`
- `async _get_connection()`

#### RedisHealthCheck

Detailed Redis health checks.

**Methods:**

- `__init__()`
- `async check_memory_usage()`
- `async check_connected_clients()`
- `async check_key_statistics()`
- `async check_performance_metrics()`

#### ExternalServiceHealthCheck

Health checks for external services.

**Methods:**

- `__init__()`
- `async check_all_services()`
- `async check_service()`

#### MockConnection

**Methods:**

- `async fetchval()`
- `async fetchrow()`

*Source: /home/dotmac_framework/src/dotmac_shared/health/comprehensive_checks.py*

## dotmac_shared.inventory_management.__init__

DotMac Shared Inventory Management System

Comprehensive inventory management for equipment, assets, stock control,
and warehouse operations across ISP and Management Platform systems.

*Source: /home/dotmac_framework/src/dotmac_shared/inventory_management/__init__.py*

## dotmac_shared.inventory_management.adapters.__init__

Platform adapters for inventory management.

*Source: /home/dotmac_framework/src/dotmac_shared/inventory_management/adapters/__init__.py*

## dotmac_shared.inventory_management.adapters.platform_adapter

Platform adapters for integrating inventory management with ISP Framework and Management Platform.

### Classes

#### BaseInventoryAdapter

Base adapter for platform-specific inventory integration.

**Methods:**

- `__init__()`
- `async get_vendor_info()`
- `async send_inventory_notification()`
- `async create_inventory_event()`

#### ISPInventoryAdapter

Adapter for ISP Framework inventory operations.

**Methods:**

- `__init__()`
- `async get_vendor_info()`
- `async send_inventory_notification()`
- `async create_inventory_event()`
- `async setup_isp_equipment_catalog()`
- `async setup_isp_warehouses()`
- `async process_customer_installation()`
- `async process_equipment_return()`

#### ManagementInventoryAdapter

Adapter for Management Platform inventory operations.

**Methods:**

- `__init__()`
- `async get_vendor_info()`
- `async send_inventory_notification()`
- `async create_inventory_event()`
- `async setup_datacenter_inventory()`
- `async process_tenant_deployment_equipment()`

#### InventoryPlatformAdapter

Main adapter that routes to appropriate platform adapters.

**Methods:**

- `__init__()`
- `get_adapter()`
- `async setup_platform_inventory()`
- `async send_platform_notification()`

*Source: /home/dotmac_framework/src/dotmac_shared/inventory_management/adapters/platform_adapter.py*

## dotmac_shared.inventory_management.core.__init__

Core inventory management components.

*Source: /home/dotmac_framework/src/dotmac_shared/inventory_management/core/__init__.py*

## dotmac_shared.inventory_management.core.inventory_manager

Core inventory management operations and business logic.

Handles CRUD operations, stock movements, purchase orders, and warehouse management
with full audit trail and business rule validation.

### Classes

#### InventoryManager

Core inventory management system.

**Methods:**

- `__init__()`
- `async create_item()`
- `async get_item()`
- `async get_item_by_code()`
- `async list_items()`
- `async update_item()`
- `async create_warehouse()`
- `async get_warehouse()`
- `async list_warehouses()`
- `async get_stock_item()`
- `async get_item_stock_summary()`
- `async create_stock_movement()`
- `async get_stock_movements()`
- `async create_purchase_order()`
- `async get_purchase_order()`
- `async get_inventory_analytics()`
- `async _generate_item_code()`
- `async _generate_po_number()`
- `async _update_stock_levels()`

*Source: /home/dotmac_framework/src/dotmac_shared/inventory_management/core/inventory_manager.py*

## dotmac_shared.inventory_management.core.models

Inventory management models for equipment, assets, and stock management.

Platform-agnostic models that work across ISP Framework and Management Platform.

### Classes

#### ItemType

Inventory item types.

#### ItemCondition

Item condition status.

#### ItemStatus

Item availability status.

#### MovementType

Stock movement types.

#### WarehouseType

Warehouse types.

#### PurchaseOrderStatus

Purchase order status.

#### Item

Inventory items and products.

**Methods:**

- `is_end_of_life()`
- `total_stock_quantity()`
- `available_stock_quantity()`
- `__repr__()`

#### Warehouse

Warehouses and storage locations.

**Methods:**

- `__repr__()`

#### StockItem

Stock quantities per item per warehouse.

**Methods:**

- `is_below_minimum()`
- `turnover_days()`
- `__repr__()`

#### StockMovement

Stock movement transactions.

**Methods:**

- `is_inbound()`
- `__repr__()`

#### PurchaseOrder

Purchase orders for inventory replenishment.

**Methods:**

- `is_overdue()`
- `__repr__()`

#### PurchaseOrderLine

Individual line items in purchase orders.

**Methods:**

- `is_fully_received()`
- `__repr__()`

#### StockCount

Physical stock counts and cycle counts.

**Methods:**

- `accuracy_percentage()`
- `__repr__()`

#### StockCountLine

Individual item counts within a stock count.

**Methods:**

- `has_variance()`
- `__repr__()`

*Source: /home/dotmac_framework/src/dotmac_shared/inventory_management/core/models.py*

## dotmac_shared.inventory_management.core.schemas

Pydantic schemas for inventory management API validation.

### Classes

#### InventoryBase

Base schema with common configuration.

#### ItemBase

Base item schema.

#### ItemCreate

Schema for creating items.

#### ItemUpdate

Schema for updating items.

#### ItemResponse

Schema for item responses.

#### WarehouseBase

Base warehouse schema.

#### WarehouseCreate

Schema for creating warehouses.

#### WarehouseUpdate

Schema for updating warehouses.

#### WarehouseResponse

Schema for warehouse responses.

#### StockItemResponse

Schema for stock item responses.

#### StockMovementCreate

Schema for creating stock movements.

#### StockMovementResponse

Schema for stock movement responses.

#### PurchaseOrderCreate

Schema for creating purchase orders.

#### PurchaseOrderUpdate

Schema for updating purchase orders.

#### PurchaseOrderResponse

Schema for purchase order responses.

#### PurchaseOrderLineCreate

Schema for creating purchase order lines.

#### PurchaseOrderLineResponse

Schema for purchase order line responses.

#### StockCountCreate

Schema for creating stock counts.

#### StockCountResponse

Schema for stock count responses.

#### StockCountLineResponse

Schema for stock count line responses.

*Source: /home/dotmac_framework/src/dotmac_shared/inventory_management/core/schemas.py*

## dotmac_shared.inventory_management.services.__init__

Inventory management services.

*Source: /home/dotmac_framework/src/dotmac_shared/inventory_management/services/__init__.py*

## dotmac_shared.inventory_management.services.inventory_service

High-level inventory management service with business logic.

Orchestrates inventory operations, workflows, and cross-platform integrations.

### Classes

#### InventoryService

High-level inventory management service with business logic.

**Methods:**

- `__init__()`
- `async create_equipment_item()`
- `async create_consumable_item()`
- `async get_item_with_stock_summary()`
- `async get_low_stock_items()`
- `async setup_standard_warehouses()`
- `async receive_equipment()`
- `async issue_equipment_for_installation()`
- `async transfer_equipment()`
- `async create_reorder_purchase_orders()`
- `async get_inventory_dashboard()`
- `async get_equipment_utilization_report()`

*Source: /home/dotmac_framework/src/dotmac_shared/inventory_management/services/inventory_service.py*

## dotmac_shared.ipam.__init__

DotMac IPAM - IP Address Management Package

This package provides comprehensive IP address management capabilities:

- Network/subnet management with CIDR validation
- Dynamic and static IP allocation
- IP reservation system with expiration
- Conflict detection and validation
- Network utilization statistics and analytics
- Multi-tenant support with isolation
- Database persistence with SQLAlchemy integration
- RESTful API schemas with Pydantic

*Source: /home/dotmac_framework/src/dotmac_shared/ipam/__init__.py*

## dotmac_shared.ipam.config_example

IPAM Configuration Examples and Production Setup Guide.

*Source: /home/dotmac_framework/src/dotmac_shared/ipam/config_example.py*

## dotmac_shared.ipam.core.__init__

IPAM core components.

*Source: /home/dotmac_framework/src/dotmac_shared/ipam/core/__init__.py*

## dotmac_shared.ipam.core.exceptions

IPAM-specific exceptions.

### Classes

#### IPAMError

Base IPAM exception.

#### IPAddressConflictError

IP address already allocated or reserved.

**Methods:**

- `__init__()`

#### NetworkNotFoundError

Network not found in IPAM database.

**Methods:**

- `__init__()`

#### InvalidNetworkError

Invalid network configuration or CIDR.

**Methods:**

- `__init__()`

#### AllocationNotFoundError

IP allocation not found.

**Methods:**

- `__init__()`

#### ReservationNotFoundError

IP reservation not found.

**Methods:**

- `__init__()`

#### InsufficientAddressSpaceError

No available IP addresses in network.

**Methods:**

- `__init__()`

#### NetworkOverlapError

Network overlaps with existing network.

**Methods:**

- `__init__()`

#### ExpiredAllocationError

IP allocation has expired.

**Methods:**

- `__init__()`

#### TenantIsolationError

Tenant isolation violation.

**Methods:**

- `__init__()`

*Source: /home/dotmac_framework/src/dotmac_shared/ipam/core/exceptions.py*

## dotmac_shared.ipam.core.models

IPAM database models for network management.

### Classes

#### NetworkType

Network type enumeration.

#### AllocationStatus

IP allocation status.

#### ReservationStatus

IP reservation status.

#### IPNetwork

IP network/subnet definition.

**Methods:**

- `network_address()`
- `total_addresses()`
- `usable_addresses()`
- `__repr__()`

#### IPAllocation

IP address allocations.

**Methods:**

- `normalized_mac_address()`
- `is_expired()`
- `is_active()`
- `days_until_expiry()`
- `__repr__()`

#### IPReservation

IP address reservations for future allocation.

**Methods:**

- `is_expired()`
- `is_active()`
- `minutes_until_expiry()`
- `__repr__()`

#### IPNetwork

IPNetwork model stub.

#### IPAllocation

IPAllocation model stub.

#### IPReservation

IPReservation model stub.

#### TenantModel

#### StatusMixin

#### AuditMixin

*Source: /home/dotmac_framework/src/dotmac_shared/ipam/core/models.py*

## dotmac_shared.ipam.core.schemas

IPAM API schemas for requests and responses.

### Classes

#### NetworkBase

Base network schema.

**Methods:**

- `validate_cidr()`
- `validate_gateway()`
- `validate_dns_servers()`

#### NetworkCreate

Schema for creating networks.

#### NetworkUpdate

Schema for updating networks.

#### NetworkResponse

Schema for network responses.

#### AllocationBase

Base allocation schema.

**Methods:**

- `validate_ip_address()`

#### AllocationCreate

Schema for creating allocations.

#### AllocationUpdate

Schema for updating allocations.

#### AllocationResponse

Schema for allocation responses.

#### ReservationBase

Base reservation schema.

**Methods:**

- `validate_ip_address()`

#### ReservationCreate

Schema for creating reservations.

#### ReservationResponse

Schema for reservation responses.

#### NetworkUtilization

Network utilization statistics.

#### IPAvailability

IP address availability check.

#### AllocationSummary

Allocation summary statistics.

#### ReservationSummary

Reservation summary statistics.

#### NetworkListResponse

Network list response.

#### AllocationListResponse

Allocation list response.

#### ReservationListResponse

Reservation list response.

#### NetworkFilters

Network filtering options.

#### AllocationFilters

Allocation filtering options.

#### ReservationFilters

Reservation filtering options.

#### BaseModel

#### TenantModelSchema

*Source: /home/dotmac_framework/src/dotmac_shared/ipam/core/schemas.py*

## dotmac_shared.ipam.middleware.__init__

IPAM middleware components.

*Source: /home/dotmac_framework/src/dotmac_shared/ipam/middleware/__init__.py*

## dotmac_shared.ipam.planning.__init__

IPAM network planning and management components.

*Source: /home/dotmac_framework/src/dotmac_shared/ipam/planning/__init__.py*

## dotmac_shared.ipam.planning.network_planner

IPAM Network Planning - Advanced network planning and subnet management.

### Classes

#### SubnetPurpose

Subnet allocation purposes.

#### IPPoolType

IP pool types for different services.

#### SubnetRequirement

Subnet allocation requirement.

#### IPPool

IP address pool definition.

**Methods:**

- `total_addresses()`
- `available_addresses()`

#### NetworkHierarchy

Network hierarchy node.

**Methods:**

- `network()`
- `available_space()`

#### NetworkPlanner

Advanced network planner for automated subnet allocation and management.

Features:

- Hierarchical subnet planning
- IP pool management
- Automatic subnet provisioning
- Growth planning and forecasting
- Conflict detection and resolution

**Methods:**

- `__init__()`
- `create_network_hierarchy()`
- `calculate_optimal_subnet_size()`
- `plan_subnets()`
- `create_ip_pools()`
- `suggest_network_expansion()`
- `detect_subnet_conflicts()`
- `optimize_subnet_allocation()`

*Source: /home/dotmac_framework/src/dotmac_shared/ipam/planning/network_planner.py*

## dotmac_shared.ipam.repositories.__init__

IPAM repositories package.

*Source: /home/dotmac_framework/src/dotmac_shared/ipam/repositories/__init__.py*

## dotmac_shared.ipam.repositories.ipam_repository

IPAM Repository - Database access layer for IPAM operations.

### Classes

#### IPAMRepository

Repository pattern for IPAM database operations.

Provides data access methods for networks, allocations, and reservations
with proper error handling and tenant isolation.

**Methods:**

- `__init__()`
- `create_network()`
- `get_network_by_id()`
- `get_networks_by_tenant()`
- `update_network()`
- `delete_network()`
- `get_overlapping_networks()`
- `create_allocation()`
- `get_allocation_by_id()`
- `get_allocations_by_network()`
- `get_allocation_by_ip()`
- `update_allocation()`
- `get_expired_allocations()`
- `create_reservation()`
- `get_reservation_by_id()`
- `get_reservations_by_network()`
- `get_reservation_by_ip()`
- `update_reservation()`
- `get_expired_reservations()`
- `get_network_utilization_stats()`
- `get_tenant_summary()`
- `check_ip_conflict()`
- `cleanup_expired_resources()`

*Source: /home/dotmac_framework/src/dotmac_shared/ipam/repositories/ipam_repository.py*

## dotmac_shared.ipam.sdk.__init__

IPAM SDK package.

*Source: /home/dotmac_framework/src/dotmac_shared/ipam/sdk/__init__.py*

## dotmac_shared.ipam.sdk.ipam_sdk

IPAM SDK - Public interface for IP Address Management operations.

### Classes

#### IPAMSDK

Public SDK interface for IPAM operations.

Provides a clean, tenant-aware API for IP address management including:

- Network/subnet management
- Dynamic and static IP allocation
- IP reservation system
- Network utilization analytics
- Conflict detection and validation

**Methods:**

- `__init__()`
- `async create_network()`
- `async get_network()`
- `async get_network_utilization()`
- `async allocate_ip()`
- `async release_ip()`
- `async renew_allocation()`
- `async reserve_ip()`
- `async cancel_reservation()`
- `async check_ip_availability()`
- `async get_allocations_by_network()`
- `async get_reservations_by_network()`
- `get_configuration()`
- `get_tenant_id()`
- `async validate_network_configuration()`
- `async cleanup_expired()`

*Source: /home/dotmac_framework/src/dotmac_shared/ipam/sdk/ipam_sdk.py*

## dotmac_shared.ipam.services.__init__

IPAM services package.

*Source: /home/dotmac_framework/src/dotmac_shared/ipam/services/__init__.py*

## dotmac_shared.ipam.services.ipam_service

IPAM Service - Core business logic for IP address management.

### Classes

#### IPAMService

Core IPAM service with database persistence.

**Methods:**

- `__init__()`
- `async create_network()`
- `async allocate_ip()`
- `async reserve_ip()`
- `async release_allocation()`
- `async get_network_utilization()`
- `async _get_network()`
- `async _check_network_overlap()`
- `async _check_ip_conflict()`
- `async _find_next_available_ip()`
- `async _find_next_available_ip_batch()`
- `async _find_next_available_ip_large_network()`
- `async _find_next_available_ip_sequential()`

*Source: /home/dotmac_framework/src/dotmac_shared/ipam/services/ipam_service.py*

## dotmac_shared.ipam.tasks.__init__

IPAM Celery tasks for background processing.

*Source: /home/dotmac_framework/src/dotmac_shared/ipam/tasks/__init__.py*

## dotmac_shared.ipam.tasks.cleanup_tasks

IPAM Cleanup Tasks - Automated background jobs for IPAM maintenance.

*Source: /home/dotmac_framework/src/dotmac_shared/ipam/tasks/cleanup_tasks.py*

## dotmac_shared.ipam.utils.__init__

IPAM utilities package.

*Source: /home/dotmac_framework/src/dotmac_shared/ipam/utils/__init__.py*

## dotmac_shared.middleware.__init__

DotMac Middleware Suite - Unified Request Processing and Security Middleware

This package consolidates 15+ middleware implementations across the DotMac Framework,
providing consistent security posture and reusable middleware plugins.

Key Components:

- Core middleware stack for FastAPI applications
- Security middleware (CSRF, headers, input validation)
- Tenant isolation and multi-tenant database context
- Request processing (logging, metrics, tracing)
- Authentication integration middleware
- Pluggable middleware system for extensions

Usage:
    from dotmac_middleware import MiddlewareStack, SecurityConfig

    app = FastAPI()

    # Apply unified middleware stack
    middleware_stack = MiddlewareStack(
        security=SecurityConfig(
            csrf_enabled=True,
            rate_limiting=True,
            tenant_isolation=True
        )
    )
    middleware_stack.apply(app)

*Source: /home/dotmac_framework/src/dotmac_shared/middleware/__init__.py*

## dotmac_shared.middleware.dotmac_middleware.__init__

DotMac Middleware Suite Package

*Source: /home/dotmac_framework/src/dotmac_shared/middleware/dotmac_middleware/__init__.py*

## dotmac_shared.middleware.dotmac_middleware.core

Core middleware stack management and configuration.

This module provides the central MiddlewareStack that orchestrates all middleware
components with proper ordering and dependency management.

### Classes

#### MiddlewareType

Middleware categories for proper ordering.

#### MiddlewareConfig

Configuration for middleware components.

#### MiddlewareManager

Manages middleware lifecycle and dependencies.

**Methods:**

- `__init__()`
- `register_middleware()`
- `get_middleware_order()`
- `initialize()`
- `get_ordered_middlewares()`

#### MiddlewareStack

Unified middleware stack that consolidates all DotMac Framework middleware.

This class replaces 15+ scattered middleware implementations with a single,
configurable, and consistent middleware stack.

**Methods:**

- `__init__()`
- `register_security_middlewares()`
- `register_auth_middlewares()`
- `register_tenant_middlewares()`
- `register_processing_middlewares()`
- `register_custom_middlewares()`
- `apply()`
- `async lifespan_context()`

*Source: /home/dotmac_framework/src/dotmac_shared/middleware/dotmac_middleware/core.py*

## dotmac_shared.middleware.dotmac_middleware.plugins

Middleware plugin system for extensible middleware functionality.

This module provides a plugin architecture for middleware components,
allowing third-party and custom middleware to be integrated seamlessly.

### Classes

#### MiddlewarePhase

Middleware execution phases.

#### PluginMetadata

Metadata for middleware plugins.

#### MiddlewarePlugin

Base class for middleware plugins.

All middleware plugins must inherit from this class and implement
the required methods.

**Methods:**

- `__init__()`
- `get_metadata()`
- `async process_request()`
- `initialize()`
- `cleanup()`
- `validate_config()`
- `is_initialized()`

#### PluginWrapper

Wrapper that adapts MiddlewarePlugin to FastAPI middleware.

**Methods:**

- `__init__()`
- `async dispatch()`

#### PluginRegistry

Registry for managing middleware plugins.

**Methods:**

- `__init__()`
- `register_plugin()`
- `unregister_plugin()`
- `enable_plugin()`
- `disable_plugin()`
- `get_plugin()`
- `get_enabled_plugins()`
- `get_plugins_by_phase()`
- `validate_dependencies()`
- `get_registry_stats()`

#### PluginManager

Manager for loading and orchestrating middleware plugins.

Handles plugin discovery, loading, dependency resolution, and lifecycle.

**Methods:**

- `__init__()`
- `add_plugin_directory()`
- `discover_plugins()`
- `load_plugin()`
- `load_all_plugins()`
- `get_middleware_stack()`
- `reload_plugins()`

#### MiddlewareRegistry

Global registry for middleware components and plugins.

Provides a unified interface to manage both built-in and plugin middleware.

**Methods:**

- `__init__()`
- `register_builtin_middleware()`
- `get_all_middlewares()`
- `configure_plugins()`

#### LoggingPlugin

Example logging plugin.

**Methods:**

- `get_metadata()`
- `async process_request()`

#### SecurityPlugin

Example security plugin.

**Methods:**

- `get_metadata()`
- `async process_request()`

*Source: /home/dotmac_framework/src/dotmac_shared/middleware/dotmac_middleware/plugins.py*

## dotmac_shared.middleware.dotmac_middleware.security

Unified security middleware components for DotMac Framework.

This module consolidates security middleware implementations from:

- ISP Framework security middleware
- Management Platform security middleware
- Shared security components

Provides consistent security posture across all applications.

### Classes

#### SecurityConfig

Configuration for security middleware components.

#### SecurityHeadersMiddleware

Unified security headers middleware.

Consolidates security header implementations from ISP and Management frameworks.

**Methods:**

- `__init__()`
- `async dispatch()`

#### CSRFMiddleware

Cross-Site Request Forgery protection middleware.

Provides token-based CSRF protection with proper validation.

**Methods:**

- `__init__()`
- `async dispatch()`

#### RateLimitingMiddleware

Rate limiting middleware with sliding window implementation.

Provides protection against API abuse and DoS attacks.

**Methods:**

- `__init__()`
- `async dispatch()`

#### InputValidationMiddleware

Input validation and sanitization middleware.

Provides protection against various injection attacks.

**Methods:**

- `__init__()`
- `async _validate_form_data()`
- `async dispatch()`

#### SecurityMiddleware

Unified security middleware that combines all security components.

This is a convenience middleware that applies multiple security measures.

**Methods:**

- `__init__()`
- `async dispatch()`

*Source: /home/dotmac_framework/src/dotmac_shared/middleware/dotmac_middleware/security.py*

## dotmac_shared.monitoring.__init__

DotMac Unified Monitoring System

This package provides a consolidated monitoring interface that eliminates
duplication across services while providing comprehensive observability.

Main Components:

- BaseMonitoringService: Abstract base class for all monitoring implementations
- SignOzMonitoringService: Native SignOz monitoring with OpenTelemetry
- NoOpMonitoringService: No-operation monitoring for testing/disabled environments
- ContainerHealthMonitor: Comprehensive container health monitoring

*Source: /home/dotmac_framework/src/dotmac_shared/monitoring/__init__.py*

## dotmac_shared.monitoring.base

Base monitoring classes for DotMac unified monitoring system.

This module provides the core monitoring interface using OpenTelemetry and SignOz
for unified observability without Prometheus dependencies.

### Classes

#### MetricType

OpenTelemetry metric types for SignOz.

#### MetricConfig

Configuration for an OpenTelemetry metric.

**Methods:**

- `__post_init__()`

#### HealthStatus

Health check status levels.

#### HealthCheck

Health check result.

**Methods:**

- `__post_init__()`

#### BaseMonitoringService

Abstract base class for monitoring services using OpenTelemetry/SignOz.

This replaces Prometheus-based monitoring with native SignOz integration.

**Methods:**

- `__init__()`
- `record_http_request()`
- `record_database_query()`
- `record_cache_operation()`
- `record_error()`
- `perform_health_check()`
- `get_metrics_endpoint()`

#### SignOzMonitoringService

SignOz-native monitoring service implementation using OpenTelemetry.

**Methods:**

- `record_http_request()`
- `record_database_query()`
- `record_cache_operation()`
- `record_error()`
- `perform_health_check()`
- `get_metrics_endpoint()`

#### NoOpMonitoringService

No-operation monitoring service for testing/disabled environments.

**Methods:**

- `record_http_request()`
- `record_database_query()`
- `record_cache_operation()`
- `record_error()`
- `perform_health_check()`
- `get_metrics_endpoint()`

*Source: /home/dotmac_framework/src/dotmac_shared/monitoring/base.py*

## dotmac_shared.notifications.__init__

DotMac Unified Notification Service - DRY Implementation

This is a thin orchestration layer that leverages existing DotMac infrastructure:

- Plugin system for channel providers
- Secrets management for credentials
- Cache system for templates and rate limiting
- Event system for delivery tracking
- Omnichannel service for actual message delivery

No duplicate implementations - pure orchestration using existing services.

*Source: /home/dotmac_framework/src/dotmac_shared/notifications/__init__.py*

## dotmac_shared.notifications.models

Notification Service Models

Simple models that map to existing omnichannel service structures.

### Classes

#### NotificationStatus

Notification delivery status

#### NotificationPriority

Notification priority levels

#### NotificationType

Types of notifications

#### NotificationRequest

Unified notification request

#### NotificationResponse

Unified notification response

#### BulkNotificationRequest

Bulk notification request

#### BulkNotificationResponse

Bulk notification response

#### NotificationTemplate

Simple template model for caching

*Source: /home/dotmac_framework/src/dotmac_shared/notifications/models.py*

## dotmac_shared.observability.adapters.__init__

Platform adapters for observability integration.

*Source: /home/dotmac_framework/src/dotmac_shared/observability/adapters/__init__.py*

## dotmac_shared.observability.adapters.isp_adapter

ISP Platform Adapter for Observability

Integrates the observability package with ISP framework services
and provides ISP-specific metrics and monitoring capabilities.

### Classes

#### ISPObservabilityAdapter

Adapter for integrating observability with ISP platform services.

**Methods:**

- `__init__()`
- `record_customer_event()`
- `record_billing_event()`
- `record_network_operation()`
- `record_service_provisioning()`
- `record_support_ticket()`
- `record_authentication_event()`
- `record_api_usage()`
- `get_tenant_health_summary()`
- `create_tenant_dashboard_config()`
- `setup_tenant_monitoring()`
- `get_isp_business_metrics()`

*Source: /home/dotmac_framework/src/dotmac_shared/observability/adapters/isp_adapter.py*

## dotmac_shared.observability.adapters.management_adapter

Management Platform Adapter for Observability

Integrates the observability package with management platform services
and provides management-specific metrics and monitoring capabilities.

### Classes

#### ManagementPlatformAdapter

Adapter for integrating observability with management platform services.

**Methods:**

- `__init__()`
- `record_tenant_operation()`
- `record_deployment_event()`
- `record_billing_operation()`
- `record_monitoring_event()`
- `record_plugin_operation()`
- `record_user_management_event()`
- `record_analytics_event()`
- `get_platform_health_summary()`
- `create_platform_dashboard_config()`
- `setup_platform_monitoring()`
- `get_platform_business_metrics()`
- `get_multi_tenant_summary()`

*Source: /home/dotmac_framework/src/dotmac_shared/observability/adapters/management_adapter.py*

## dotmac_shared.observability.core.__init__

Core observability components for DotMac services.

*Source: /home/dotmac_framework/src/dotmac_shared/observability/core/__init__.py*

## dotmac_shared.observability.core.signoz_integration

SignOz-native observability for DotMac services.
Unified metrics, traces, and logs using OpenTelemetry with SignOz as the sole backend.

Enhanced version of the ISP framework implementation for shared service usage.

### Classes

#### SignOzTelemetry

Unified SignOz telemetry configuration for DotMac services.
Replaces Prometheus/Grafana with SignOz-native observability.

**Methods:**

- `__init__()`
- `instrument_fastapi()`
- `record_http_metrics()`
- `record_business_event()`
- `record_revenue()`
- `record_cache_operation()`
- `trace_operation()`
- `create_signoz_dashboard()`
- `shutdown()`

*Source: /home/dotmac_framework/src/dotmac_shared/observability/core/signoz_integration.py*

## dotmac_shared.observability.core.signoz_metrics

SignOz metrics integration for DotMac Platform.

This module provides SignOz-native monitoring using OpenTelemetry.
Migrated from Prometheus to provide unified observability.

DEPRECATED: This file has been replaced by the unified monitoring system.
Please use dotmac_shared.monitoring instead.

*Source: /home/dotmac_framework/src/dotmac_shared/observability/core/signoz_metrics.py*

## dotmac_shared.omnichannel.__init__

DotMac Omnichannel Communication Service

A comprehensive, multi-tenant omnichannel communication platform for the DotMac framework,
providing unified customer interaction management across multiple communication channels
with intelligent routing, agent management, and real-time analytics.

Properly integrated with the DotMac plugin system for extensible communication channels.

Author: DotMac Framework Team
License: MIT

*Source: /home/dotmac_framework/src/dotmac_shared/omnichannel/__init__.py*

## dotmac_shared.omnichannel.core.agent_manager

Agent Management System for Omnichannel Service

Provides comprehensive agent workforce management including:

- Agent status and availability tracking
- Team and hierarchy management
- Performance analytics and KPI tracking
- Workload distribution and capacity planning
- Skill-based matching and routing
- Shift management and scheduling

Author: DotMac Framework Team
License: MIT

### Classes

#### AgentStatus

Agent availability status

#### SkillLevel

Agent skill proficiency levels

#### AgentSkill

Agent skill with proficiency level

#### AgentMetrics

Agent performance metrics

#### TeamConfiguration

Team configuration and settings

#### AgentModel

Agent data model

#### TeamModel

Team data model

#### AgentManager

Comprehensive agent management system for omnichannel operations

Handles agent lifecycle, team management, performance tracking,
and intelligent workload distribution across the organization.

**Methods:**

- `__init__()`
- `async create_agent()`
- `async update_agent_status()`
- `async get_agent()`
- `async get_available_agents()`
- `async assign_interaction()`
- `async complete_interaction()`
- `async create_team()`
- `async assign_agent_to_team()`
- `async get_team_performance()`
- `async find_best_agent_for_interaction()`
- `async get_agent_performance()`
- `async _calculate_agent_score()`
- `async _track_status_change()`

#### Config

*Source: /home/dotmac_framework/src/dotmac_shared/omnichannel/core/agent_manager.py*

## dotmac_shared.omnichannel.core.channel_orchestrator

Channel Orchestrator for Omnichannel Service

Provides unified channel management and message orchestration across:

- Email, SMS, WhatsApp, social media, voice, chat
- Template-based messaging with personalization
- Channel-specific formatting and delivery
- Message tracking and delivery confirmation
- Cross-channel conversation continuity
- Channel preference management

Author: DotMac Framework Team
License: MIT

### Classes

#### MessageType

Message content types

#### DeliveryPriority

Message delivery priority

#### ChannelConfig

Channel configuration settings

#### MessageTemplate

Message template definition

#### MessageAttachment

Message attachment definition

#### OutboundMessage

Outbound message model

#### InboundMessage

Inbound message model

#### ChannelOrchestrator

Central orchestrator for multi-channel communication

Manages message routing, template rendering, delivery tracking,
and channel-specific adaptations across all communication channels.

**Methods:**

- `__init__()`
- `async configure_channel()`
- `async initialize()`
- `async register_template()`
- `async send_message()`
- `async handle_incoming_message()`
- `async get_message_status()`
- `async update_message_status()`
- `async retry_failed_messages()`
- `async get_available_channels()`
- `async get_plugin_status()`
- `async get_channel_statistics()`
- `async _validate_channel()`
- `async _check_rate_limit()`
- `async _deliver_message()`
- `async _render_template()`
- `async _render_text()`
- `async _identify_customer_and_interaction()`
- `async _process_incoming_message()`
- `async _trigger_delivery_callbacks()`
- `async _calculate_avg_delivery_time()`
- `async _calculate_success_rate()`
- `register_delivery_callback()`

#### Config

#### Config

*Source: /home/dotmac_framework/src/dotmac_shared/omnichannel/core/channel_orchestrator.py*

## dotmac_shared.omnichannel.core.interaction_manager

Interaction Manager for DotMac Omnichannel Service.

Central orchestrator for all customer interactions across multiple channels.
Manages the complete interaction lifecycle from creation to resolution.

### Classes

#### InteractionStatus

Interaction status values.

#### InteractionPriority

Interaction priority levels.

#### InteractionContext

Context information for an interaction.

#### InteractionSLA

SLA configuration for interactions.

#### InteractionModel

Core interaction data model.

**Methods:**

- `validate_priority()`
- `validate_status()`
- `is_active()`
- `is_closed()`
- `time_to_first_response()`
- `time_to_resolution()`
- `get_age()`

#### InteractionResponse

Response to an interaction.

#### InteractionManager

Central interaction management service.

Orchestrates the complete lifecycle of customer interactions including:

- Interaction creation and routing
- Status management and updates
- SLA tracking and monitoring
- Response handling and delivery
- Analytics and reporting

**Methods:**

- `__init__()`
- `async create_interaction()`
- `async update_interaction()`
- `async add_response()`
- `async close_interaction()`
- `async get_interaction()`
- `async get_customer_interactions()`
- `async get_agent_interactions()`
- `async check_sla_breaches()`
- `async _calculate_sla_deadlines()`
- `async _notify_interaction_created()`
- `configure_tenant_sla()`
- `async get_interaction_stats()`

#### Config

*Source: /home/dotmac_framework/src/dotmac_shared/omnichannel/core/interaction_manager.py*

## dotmac_shared.omnichannel.core.routing_engine

Routing Engine for DotMac Omnichannel Service.

Intelligent routing system that directs customer interactions to the most
appropriate agents based on skills, availability, workload, and business rules.

### Classes

#### RoutingStrategy

Routing strategy types.

#### ConditionOperator

Condition operators for routing rules.

#### AgentSkill

Agent skill definition.

#### AgentStatus

Current agent status and availability.

**Methods:**

- `is_available()`
- `get_workload_ratio()`
- `has_skill()`

#### RoutingCondition

Routing rule condition.

**Methods:**

- `evaluate()`

#### RoutingAction

Routing rule action.

#### RoutingRule

Complete routing rule definition.

**Methods:**

- `evaluate()`

#### RoutingResult

Result of routing operation.

#### RoutingStrategy_ABC

Abstract base class for routing strategies.

**Methods:**

- `async route()`

#### RoundRobinStrategy

Round-robin routing strategy.

**Methods:**

- `__init__()`
- `async route()`

#### LeastBusyStrategy

Least busy routing strategy.

**Methods:**

- `async route()`

#### SkillBasedStrategy

Skill-based routing strategy.

**Methods:**

- `async route()`

#### RoutingEngine

Intelligent routing engine for customer interactions.

Provides sophisticated routing capabilities including:

- Rule-based routing with complex conditions
- Multiple routing strategies (round-robin, skill-based, least-busy)
- Agent availability and workload management
- Queue management and escalation
- Analytics and performance tracking

**Methods:**

- `__init__()`
- `async route_interaction()`
- `async add_routing_rule()`
- `async remove_routing_rule()`
- `async update_routing_rule()`
- `register_custom_strategy()`
- `async _get_routing_rules()`
- `async _default_routing()`
- `async _execute_routing_action()`
- `async _route_to_team()`
- `async _escalate_interaction()`
- `async _queue_interaction()`
- `async _estimate_queue_wait_time()`
- `async get_routing_stats()`

*Source: /home/dotmac_framework/src/dotmac_shared/omnichannel/core/routing_engine.py*

## dotmac_shared.omnichannel.examples.usage_example

Omnichannel Service Usage Example

Demonstrates how to use the omnichannel service with the DotMac plugin system
for managing customer interactions across multiple communication channels.

Author: DotMac Framework Team
License: MIT

*Source: /home/dotmac_framework/src/dotmac_shared/omnichannel/examples/usage_example.py*

## dotmac_shared.omnichannel.integrations.__init__

Integration modules for omnichannel service

Provides bridges to external systems and DotMac framework components:

- plugin_system_integration: Integration with DotMac plugin system

Author: DotMac Framework Team
License: MIT

*Source: /home/dotmac_framework/src/dotmac_shared/omnichannel/integrations/__init__.py*

## dotmac_shared.omnichannel.models.__init__

Omnichannel service data models.

*Source: /home/dotmac_framework/src/dotmac_shared/omnichannel/models/__init__.py*

## dotmac_shared.omnichannel.models.agent

Agent management models.

### Classes

#### AgentStatus

Agent availability status.

#### AgentSkill

Agent skill definition.

#### AgentAvailability

Agent availability schedule.

#### AgentPerformanceMetrics

Agent performance metrics.

**Methods:**

- `resolution_rate()`

#### AgentModel

Core agent model.

**Methods:**

- `validate_interaction_count()`

#### CreateAgentRequest

Request to create a new agent.

#### UpdateAgentRequest

Request to update agent information.

#### Config

#### Config

#### Config

*Source: /home/dotmac_framework/src/dotmac_shared/omnichannel/models/agent.py*

## dotmac_shared.omnichannel.models.channel

Channel configuration and status models.

### Classes

#### ChannelStatus

Channel operational status.

#### ChannelConfig

Channel configuration model.

#### ChannelStatusInfo

Channel status information.

#### ChannelCapabilities

Channel capabilities and features.

#### ChannelMetrics

Channel performance metrics.

**Methods:**

- `success_rate()`

#### ChannelAlert

Channel alert configuration.

#### Config

#### Config

#### Config

#### Config

*Source: /home/dotmac_framework/src/dotmac_shared/omnichannel/models/channel.py*

## dotmac_shared.omnichannel.models.enums

Common enumerations for the omnichannel service.

### Classes

#### ChannelType

Communication channel types.

#### MessageStatus

Message delivery status enumeration.

*Source: /home/dotmac_framework/src/dotmac_shared/omnichannel/models/enums.py*

## dotmac_shared.omnichannel.models.interaction

Interaction management models.

### Classes

#### InteractionPriority

Interaction priority levels.

#### InteractionStatus

Interaction status states.

#### InteractionMessage

Message within an interaction.

#### InteractionModel

Core interaction model.

#### CreateInteractionRequest

Request to create a new interaction.

#### UpdateInteractionRequest

Request to update an interaction.

#### Config

#### Config

#### Config

#### Config

*Source: /home/dotmac_framework/src/dotmac_shared/omnichannel/models/interaction.py*

## dotmac_shared.omnichannel.models.message

Message and communication models.

### Classes

#### MessageStatus

Message delivery status.

#### Message

Core message model for omnichannel communication.

#### MessageResult

Result of message sending operation.

#### BulkMessageRequest

Request for sending bulk messages.

#### BulkMessageResult

Result of bulk message operation.

**Methods:**

- `success_rate()`

#### MessageTemplate

Message template for consistent messaging.

#### Config

#### Config

#### Config

#### Config

*Source: /home/dotmac_framework/src/dotmac_shared/omnichannel/models/message.py*

## dotmac_shared.omnichannel.models.routing

Routing and assignment models.

### Classes

#### RoutingStrategy

Available routing strategies.

#### RoutingResult

Result of routing operation.

#### RoutingRule

Rule-based routing configuration.

#### RoutingAction

Action to take when routing rule matches.

#### RoutingConfiguration

Tenant routing configuration.

#### SkillRequirement

Skill requirement for routing.

#### RoutingContext

Context information for routing decisions.

#### RoutingMetrics

Routing performance metrics.

**Methods:**

- `success_rate()`

#### Config

#### Config

#### Config

#### Config

*Source: /home/dotmac_framework/src/dotmac_shared/omnichannel/models/routing.py*

## dotmac_shared.omnichannel.plugins.__init__

Omnichannel Communication Plugins

Contains reference implementations of communication plugins
using the DotMac plugin system architecture.

Author: DotMac Framework Team
License: MIT

*Source: /home/dotmac_framework/src/dotmac_shared/omnichannel/plugins/__init__.py*

## dotmac_shared.plugins.__init__

DotMac Plugins - Universal Plugin System

A comprehensive, reusable plugin system for any application domain.
Supports dynamic loading, dependency management, and domain-specific adapters.

Example Usage:
    ```python
    from dotmac_shared.plugins import PluginRegistry, PluginManager

    # Initialize plugin system
    registry = PluginRegistry()
    manager = PluginManager(registry)

    # Load plugins from configuration
    await manager.load_plugins_from_config("plugins.yaml")

    # Execute plugin methods
    result = await manager.execute_plugin(
        domain="communication",
        plugin_name="email_sender",
        method="send_message",
        recipient="user@example.com",
        message="Hello World"
    )
    ```

Architecture:
    - Core: Base plugin interfaces and lifecycle management
    - Registry: Plugin discovery, loading, and dependency resolution
    - Middleware: Validation, rate limiting, metrics collection
    - Adapters: Domain-specific plugin implementations
    - Loaders: Multiple plugin source support (YAML, Python, remote)

*Source: /home/dotmac_framework/src/dotmac_shared/plugins/__init__.py*

## dotmac_shared.plugins.adapters.__init__

Domain-specific plugin adapters.

Provides specialized interfaces and utilities for different plugin domains
like communication, storage, authentication, and networking.

*Source: /home/dotmac_framework/src/dotmac_shared/plugins/adapters/__init__.py*

## dotmac_shared.plugins.adapters.authentication

Authentication domain adapter for the plugin system.

Provides specialized interfaces for authentication plugins like OAuth, LDAP, JWT, and MFA.

### Classes

#### AuthMethod

Authentication methods.

#### AuthRequest

Authentication request.

**Methods:**

- `__post_init__()`

#### AuthResult

Authentication result.

**Methods:**

- `__post_init__()`

#### AuthenticationPlugin

Base class for authentication plugins.

**Methods:**

- `async authenticate()`
- `async validate_token()`
- `get_supported_methods()`

#### AuthenticationAdapter

Domain adapter for authentication plugins.

**Methods:**

- `__init__()`
- `register_plugin()`
- `async authenticate()`
- `async validate_token()`

*Source: /home/dotmac_framework/src/dotmac_shared/plugins/adapters/authentication.py*

## dotmac_shared.plugins.adapters.communication

Communication domain adapter for the plugin system.

Provides specialized interfaces and utilities for communication plugins
like email, SMS, push notifications, and webhooks.

### Classes

#### MessagePriority

Message priority levels.

#### MessageStatus

Message delivery status.

#### Message

Universal message structure.

**Methods:**

- `__post_init__()`

#### MessageResult

Message sending result.

**Methods:**

- `__post_init__()`

#### BulkMessageResult

Bulk message sending result.

**Methods:**

- `__post_init__()`

#### CommunicationPlugin

Base class for communication plugins.

Provides common interface for all communication channels.

**Methods:**

- `async send_message()`
- `async send_bulk_messages()`
- `async get_message_status()`
- `async validate_recipient()`
- `get_supported_message_types()`
- `get_rate_limits()`

#### CommunicationAdapter

Domain adapter for communication plugins.

Provides high-level interface for managing communication plugins
and routing messages to appropriate providers.

**Methods:**

- `__init__()`
- `register_plugin()`
- `unregister_plugin()`
- `set_default_provider()`
- `add_fallback_provider()`
- `async send_message()`
- `async send_bulk_messages()`
- `async broadcast_message()`
- `get_available_providers()`
- `get_provider_info()`
- `get_routing_config()`
- `async health_check()`
- `create_email_message()`
- `create_sms_message()`
- `create_push_notification()`

*Source: /home/dotmac_framework/src/dotmac_shared/plugins/adapters/communication.py*

## dotmac_shared.plugins.adapters.networking

Networking domain adapter for the plugin system.

Provides specialized interfaces for networking plugins like HTTP clients, DNS, and monitoring.

### Classes

#### NetworkProtocol

Network protocols.

#### NetworkRequest

Network request.

**Methods:**

- `__post_init__()`

#### NetworkResponse

Network response.

**Methods:**

- `__post_init__()`

#### NetworkingPlugin

Base class for networking plugins.

**Methods:**

- `async make_request()`
- `get_supported_protocols()`

#### NetworkingAdapter

Domain adapter for networking plugins.

**Methods:**

- `__init__()`
- `register_plugin()`
- `async make_request()`

*Source: /home/dotmac_framework/src/dotmac_shared/plugins/adapters/networking.py*

## dotmac_shared.plugins.adapters.storage

Storage domain adapter for the plugin system.

Provides specialized interfaces and utilities for storage plugins
like file storage, databases, caching, and cloud storage.

### Classes

#### StorageType

Storage types.

#### AccessMode

File access modes.

#### StorageObject

Universal storage object representation.

**Methods:**

- `__post_init__()`

#### StorageInfo

Storage information and metadata.

**Methods:**

- `__post_init__()`

#### StorageResult

Storage operation result.

**Methods:**

- `__post_init__()`

#### ListResult

Storage listing result.

#### StoragePlugin

Base class for storage plugins.

Provides common interface for all storage backends.

**Methods:**

- `async put()`
- `async get()`
- `async delete()`
- `async exists()`
- `async list()`
- `async get_info()`
- `async copy()`
- `async move()`
- `get_storage_type()`
- `get_supported_operations()`
- `get_storage_limits()`

#### StorageAdapter

Domain adapter for storage plugins.

Provides high-level interface for managing storage plugins
and routing operations to appropriate backends.

**Methods:**

- `__init__()`
- `register_plugin()`
- `unregister_plugin()`
- `set_default_backend()`
- `add_routing_rule()`
- `async put()`
- `async get()`
- `async delete()`
- `async exists()`
- `async list()`
- `async get_info()`
- `async copy()`
- `async move()`
- `get_available_backends()`
- `get_backend_info()`
- `get_routing_config()`
- `async health_check()`
- `create_file_routing_rule()`
- `create_size_routing_rule()`
- `create_prefix_routing_rule()`

*Source: /home/dotmac_framework/src/dotmac_shared/plugins/adapters/storage.py*

## dotmac_shared.plugins.core.__init__

Core plugin system components.

Contains base classes, interfaces, and fundamental plugin infrastructure.

*Source: /home/dotmac_framework/src/dotmac_shared/plugins/core/__init__.py*

## dotmac_shared.plugins.core.exceptions

Plugin system exceptions.

Comprehensive error handling for all plugin operations.

### Classes

#### PluginError

Base exception for all plugin-related errors.

**Methods:**

- `__init__()`
- `__str__()`

#### PluginNotFoundError

Raised when a requested plugin cannot be found.

**Methods:**

- `__init__()`

#### PluginDependencyError

Raised when plugin dependencies cannot be resolved.

**Methods:**

- `__init__()`

#### PluginValidationError

Raised when plugin validation fails.

**Methods:**

- `__init__()`

#### PluginConfigError

Raised when plugin configuration is invalid.

**Methods:**

- `__init__()`

#### PluginLoadError

Raised when plugin cannot be loaded.

**Methods:**

- `__init__()`

#### PluginExecutionError

Raised when plugin execution fails.

**Methods:**

- `__init__()`

#### PluginTimeoutError

Raised when plugin operation times out.

**Methods:**

- `__init__()`

#### PluginVersionError

Raised when plugin version compatibility issues occur.

**Methods:**

- `__init__()`

*Source: /home/dotmac_framework/src/dotmac_shared/plugins/core/exceptions.py*

## dotmac_shared.plugins.core.lifecycle_manager

Plugin lifecycle management system.

Manages plugin initialization, shutdown, health monitoring, and state transitions.

### Classes

#### LifecycleEvent

Plugin lifecycle events.

#### LifecycleMetrics

Metrics for plugin lifecycle operations.

**Methods:**

- `record_initialization()`
- `record_shutdown()`
- `record_health_check()`
- `record_error()`

#### LifecycleManager

Comprehensive plugin lifecycle management.

Handles initialization, shutdown, health monitoring, and state management
for all plugins in the system.

**Methods:**

- `__init__()`
- `async initialize_plugin()`
- `async initialize_plugins()`
- `async _initialize_plugin_group()`
- `async _initialize_plugin_with_semaphore()`
- `async _initialize_single_plugin()`
- `async shutdown_plugin()`
- `async shutdown_all_plugins()`
- `async _shutdown_single_plugin()`
- `async start_health_monitoring()`
- `async stop_health_monitoring()`
- `async perform_health_check()`
- `async _health_monitoring_loop()`
- `async _perform_plugin_health_check()`
- `add_event_handler()`
- `remove_event_handler()`
- `async _emit_event()`
- `get_plugin_metrics()`
- `get_all_metrics()`
- `get_system_metrics()`
- `async cleanup()`

*Source: /home/dotmac_framework/src/dotmac_shared/plugins/core/lifecycle_manager.py*

## dotmac_shared.plugins.core.manager

Main plugin manager orchestrating all plugin system components.

Provides high-level interface for plugin management, loading, and execution.

### Classes

#### PluginManager

Central plugin management system.

Orchestrates plugin loading, dependency resolution, lifecycle management,
and provides a unified interface for plugin operations.

**Methods:**

- `__init__()`
- `async initialize()`
- `async shutdown()`
- `async register_plugin()`
- `async unregister_plugin()`
- `async load_plugins_from_config()`
- `async load_plugin_from_module()`
- `async get_plugin()`
- `async find_plugins()`
- `async list_plugins()`
- `async get_available_domains()`
- `async execute_plugin()`
- `async initialize_plugins_by_domain()`
- `async shutdown_plugins_by_domain()`
- `async get_system_health()`
- `async get_plugin_health()`
- `add_middleware()`
- `remove_middleware()`
- `add_lifecycle_event_handler()`
- `remove_lifecycle_event_handler()`
- `async __aenter__()`
- `async __aexit__()`
- `__repr__()`

*Source: /home/dotmac_framework/src/dotmac_shared/plugins/core/manager.py*

## dotmac_shared.plugins.core.plugin_base

Base plugin classes and interfaces.

Defines the core plugin architecture and contracts that all plugins must implement.

### Classes

#### PluginStatus

Plugin lifecycle states.

#### PluginMetadata

Plugin metadata and configuration.

**Methods:**

- `__post_init__()`
- `to_dict()`

#### BasePlugin

Base plugin class that all plugins must inherit from.

Provides lifecycle management, configuration handling, and standardized interfaces.

**Methods:**

- `__init__()`
- `name()`
- `version()`
- `domain()`
- `is_active()`
- `is_healthy()`
- `uptime()`
- `async initialize()`
- `async shutdown()`
- `async health_check()`
- `async reload_config()`
- `get_state()`
- `set_state()`
- `clear_state()`
- `async _initialize_plugin()`
- `async _shutdown_plugin()`
- `async _validate_config()`
- `async _plugin_health_check()`
- `async _apply_config_changes()`
- `__repr__()`
- `__str__()`

*Source: /home/dotmac_framework/src/dotmac_shared/plugins/core/plugin_base.py*

## dotmac_shared.plugins.core.registry

Plugin registry for discovery and management.

Centralized registry for all loaded plugins with support for domain-based organization,
dependency tracking, and query capabilities.

### Classes

#### PluginRegistry

Central registry for managing loaded plugins.

Provides plugin discovery, dependency resolution, and lifecycle management.

**Methods:**

- `__init__()`
- `async register_plugin()`
- `async unregister_plugin()`
- `async get_plugin()`
- `async get_plugin_by_key()`
- `async find_plugins()`
- `async list_plugins_by_domain()`
- `async list_all_plugins()`
- `async get_domains()`
- `async get_plugin_metadata()`
- `async plugin_exists()`
- `async get_plugin_count()`
- `async get_plugin_count_by_domain()`
- `async get_plugin_dependencies()`
- `async get_plugin_dependents()`
- `async validate_dependencies()`
- `async get_registry_status()`
- `add_registration_callback()`
- `add_unregistration_callback()`
- `remove_registration_callback()`
- `remove_unregistration_callback()`
- `async _notify_plugin_registered()`
- `async _notify_plugin_unregistered()`
- `async __aenter__()`
- `async __aexit__()`
- `__repr__()`

*Source: /home/dotmac_framework/src/dotmac_shared/plugins/core/registry.py*

## dotmac_shared.plugins.examples.__init__

Example plugins and usage for the DotMac Plugin System.

*Source: /home/dotmac_framework/src/dotmac_shared/plugins/examples/__init__.py*

## dotmac_shared.plugins.examples.usage_example

Example usage of the DotMac Plugin System.

Demonstrates how to create plugins, configure the system, and use domain adapters.

### Classes

#### EmailPlugin

Example email plugin implementation.

**Methods:**

- `async _initialize_plugin()`
- `async _shutdown_plugin()`
- `async send_message()`
- `async validate_recipient()`
- `get_supported_message_types()`

#### SMSPlugin

Example SMS plugin implementation.

**Methods:**

- `async _initialize_plugin()`
- `async _shutdown_plugin()`
- `async send_message()`
- `async validate_recipient()`
- `get_supported_message_types()`

#### UtilityPlugin

Example utility plugin.

**Methods:**

- `async _initialize_plugin()`
- `async _shutdown_plugin()`
- `async process_text()`
- `async count_words()`

*Source: /home/dotmac_framework/src/dotmac_shared/plugins/examples/usage_example.py*

## dotmac_shared.plugins.loaders.__init__

Plugin loaders for different sources and formats.

Supports loading plugins from YAML configurations, Python modules, and remote sources.

*Source: /home/dotmac_framework/src/dotmac_shared/plugins/loaders/__init__.py*

## dotmac_shared.plugins.loaders.remote_loader

Remote plugin loader.

Loads plugins from remote sources like Git repositories, HTTP URLs, and plugin registries.

### Classes

#### RemotePluginLoader

Load plugins from remote sources.

Supports Git repositories, HTTP downloads, and plugin registries.

**Methods:**

- `__init__()`
- `async __aenter__()`
- `async __aexit__()`
- `async load_plugin_from_url()`
- `async load_plugins_from_repository()`
- `async load_plugin_from_registry()`
- `async _download_and_extract()`
- `async _clone_repository()`
- `async _query_registry()`
- `async _load_plugin_from_path()`
- `clear_cache()`
- `async cleanup()`
- `create_sample_registry_response()`

*Source: /home/dotmac_framework/src/dotmac_shared/plugins/loaders/remote_loader.py*

## dotmac_shared.plugins.loaders.yaml_loader

YAML-based plugin loader.

Loads plugin configurations from YAML files and instantiates plugins.

### Classes

#### YamlPluginLoader

Load plugins from YAML configuration files.

Supports both single plugin definitions and multi-plugin manifests.

**Methods:**

- `__init__()`
- `async load_plugins_from_file()`
- `async load_plugins_from_string()`
- `async _parse_and_load_plugins()`
- `async _load_single_plugin()`
- `create_sample_config()`
- `create_single_plugin_config()`

*Source: /home/dotmac_framework/src/dotmac_shared/plugins/loaders/yaml_loader.py*

## dotmac_shared.plugins.loadersthon_loader

Python module-based plugin loader.

Loads plugins directly from Python modules and classes.

### Classes

#### PythonPluginLoader

Load plugins from Python modules.

Supports loading from installed packages, file paths, and dynamic plugin discovery.

**Methods:**

- `__init__()`
- `async load_plugin_from_module()`
- `async load_plugin_from_file()`
- `async discover_plugins_in_module()`
- `async discover_plugins_in_directory()`
- `async _discover_plugins_in_file()`
- `async _create_metadata_from_class()`
- `create_sample_plugin()`

*Source: /home/dotmac_framework/src/dotmac_shared/plugins/loaders/python_loader.py*

## dotmac_shared.plugins.middleware.__init__

Plugin middleware components.

Provides validation, rate limiting, metrics collection, and other cross-cutting concerns
for plugin execution.

*Source: /home/dotmac_framework/src/dotmac_shared/plugins/middleware/__init__.py*

## dotmac_shared.plugins.middleware.metrics

Metrics collection middleware for plugin execution.

Collects performance metrics, usage statistics, and operational data for plugin analysis.

### Classes

#### MetricType

Types of metrics that can be collected.

#### MetricPoint

Single metric data point.

#### MetricSeries

Time series of metric points.

**Methods:**

- `add_point()`
- `get_latest_value()`
- `get_average()`
- `get_percentile()`

#### PerformanceTimer

Context manager for timing plugin operations.

**Methods:**

- `__init__()`
- `__enter__()`
- `__exit__()`
- `get_duration()`

#### MetricsMiddleware

Plugin metrics collection middleware.

Collects performance, usage, and operational metrics for plugin analysis and monitoring.

**Methods:**

- `__init__()`
- `create_metric()`
- `record_metric()`
- `increment_counter()`
- `set_gauge()`
- `record_timer()`
- `record_histogram()`
- `record_plugin_execution()`
- `record_plugin_lifecycle()`
- `update_plugin_counts()`
- `record_active_request_start()`
- `record_active_request_end()`
- `timer()`
- `plugin_timer()`
- `get_metric()`
- `get_metric_value()`
- `get_metric_stats()`
- `get_plugin_metrics()`
- `get_top_plugins_by_metric()`
- `add_metric_callback()`
- `remove_metric_callback()`
- `cleanup_old_metrics()`
- `get_system_stats()`
- `export_metrics()`

*Source: /home/dotmac_framework/src/dotmac_shared/plugins/middleware/metrics.py*

## dotmac_shared.plugins.middleware.rate_limiting

Rate limiting middleware for plugin execution.

Implements various rate limiting strategies to prevent plugin abuse and ensure fair resource usage.

### Classes

#### RateLimitStrategy

Rate limiting strategies.

#### RateLimit

Rate limit configuration.

#### RateLimiter

Abstract base class for rate limiters.

**Methods:**

- `__init__()`
- `async is_allowed()`
- `get_stats()`
- `reset()`

#### TokenBucketLimiter

Token bucket rate limiter.

Allows burst traffic up to bucket capacity, then limits to refill rate.

**Methods:**

- `__init__()`
- `async is_allowed()`
- `get_stats()`
- `reset()`

#### SlidingWindowLimiter

Sliding window rate limiter.

Tracks requests in a sliding time window for precise rate limiting.

**Methods:**

- `__init__()`
- `async is_allowed()`
- `get_stats()`
- `reset()`

#### FixedWindowLimiter

Fixed window rate limiter.

Divides time into fixed windows and limits requests per window.

**Methods:**

- `__init__()`
- `async is_allowed()`
- `get_stats()`
- `reset()`

#### RateLimitingMiddleware

Plugin rate limiting middleware.

Applies rate limits to plugin method executions to prevent abuse and ensure fair resource usage.

**Methods:**

- `__init__()`
- `add_plugin_rate_limit()`
- `add_method_rate_limit()`
- `remove_plugin_rate_limit()`
- `remove_method_rate_limit()`
- `async check_rate_limit()`
- `get_rate_limit_status()`
- `get_global_rate_limit_status()`
- `reset_rate_limits()`
- `get_middleware_stats()`
- `create_conservative_rate_limit()`
- `create_moderate_rate_limit()`
- `create_permissive_rate_limit()`
- `create_per_user_rate_limit()`

*Source: /home/dotmac_framework/src/dotmac_shared/plugins/middleware/rate_limiting.py*

## dotmac_shared.plugins.middleware.validation

Input/output validation middleware for plugin execution.

Validates plugin method arguments and return values against schemas.

### Classes

#### ValidationRule

Single validation rule configuration.

#### ValidationSchema

Validation schema for plugin method.

#### BaseValidator

Base class for value validators.

**Methods:**

- `validate()`
- `get_error_message()`

#### TypeValidator

Validates value types.

**Methods:**

- `validate()`
- `get_error_message()`

#### RangeValidator

Validates numeric ranges.

**Methods:**

- `validate()`
- `get_error_message()`

#### LengthValidator

Validates string/collection lengths.

**Methods:**

- `validate()`
- `get_error_message()`

#### PatternValidator

Validates string patterns using regex.

**Methods:**

- `validate()`
- `get_error_message()`

#### CustomValidator

Uses custom validation functions.

**Methods:**

- `validate()`
- `get_error_message()`

#### ValidationMiddleware

Plugin method validation middleware.

Validates input arguments and optionally output values for plugin methods.

**Methods:**

- `__init__()`
- `add_validation_schema()`
- `remove_validation_schema()`
- `validate_input()`
- `validate_output()`
- `get_validation_stats()`
- `create_email_validation_schema()`
- `create_file_storage_validation_schema()`

*Source: /home/dotmac_framework/src/dotmac_shared/plugins/middleware/validation.py*

## dotmac_shared.portal_id.__init__

Unified Portal ID Generation Service.

This package consolidates all portal ID generation logic across platforms,
eliminating duplication and providing consistent, configurable ID generation.

Replaces:

- dotmac_isp.modules.identity.portal_id_generator
- dotmac_isp.modules.portal_management.service._generate_portal_id
- dotmac_isp.modules.portal_management.models._generate_portal_id
- dotmac_isp.modules.identity.repository._generate_portal_id

Usage:
    # Simple usage with defaults
    portal_id = generate_portal_id()

    # Async with collision checking
    from dotmac_shared.portal_id.adapters import ISPPortalIdCollisionChecker
    collision_checker = ISPPortalIdCollisionChecker(db_session, tenant_id)
    portal_id = await generate_portal_id_async(collision_checker=collision_checker)

    # Custom configuration
    service = PortalIdServiceFactory.create_custom_service(
        pattern=PortalIdPattern.ALPHANUMERIC_CLEAN,
        length=10,
        prefix="ISP-"
    )
    portal_id = service.generate_portal_id_sync()

*Source: /home/dotmac_framework/src/dotmac_shared/portal_id/__init__.py*

## dotmac_shared.portal_id.adapters.__init__

Platform adapters for portal ID collision checking.

*Source: /home/dotmac_framework/src/dotmac_shared/portal_id/adapters/__init__.py*

## dotmac_shared.portal_id.adapters.isp_adapter

ISP Framework adapter for portal ID collision checking.

### Classes

#### ISPPortalIdCollisionChecker

Collision checker for ISP Framework portal IDs.

**Methods:**

- `__init__()`
- `async check_collision()`

#### ISPLegacyCollisionChecker

Legacy collision checker for backward compatibility.

**Methods:**

- `__init__()`
- `async check_collision()`

*Source: /home/dotmac_framework/src/dotmac_shared/portal_id/adapters/isp_adapter.py*

## dotmac_shared.portal_id.adapters.management_adapter

Management Platform adapter for portal ID collision checking.

### Classes

#### ManagementPortalIdCollisionChecker

Collision checker for Management Platform portal IDs.

**Methods:**

- `__init__()`
- `async check_collision()`

*Source: /home/dotmac_framework/src/dotmac_shared/portal_id/adapters/management_adapter.py*

## dotmac_shared.portal_id.core.service

Unified Portal ID Generation Service.

This service consolidates all portal ID generation logic across platforms,
eliminating duplication and providing consistent, configurable ID generation.

### Classes

#### PortalIdPattern

Available Portal ID generation patterns.

#### PortalIdConfig

Configuration for portal ID generation.

**Methods:**

- `__init__()`

#### PortalIdCollisionChecker

Abstract base class for checking portal ID collisions.

**Methods:**

- `async check_collision()`

#### UnifiedPortalIdService

Unified Portal ID generation service that consolidates all platform implementations.

This service replaces:

- dotmac_isp.modules.identity.portal_id_generator
- dotmac_isp.modules.portal_management.service._generate_portal_id
- dotmac_isp.modules.portal_management.models._generate_portal_id
- dotmac_isp.modules.identity.repository._generate_portal_id

**Methods:**

- `__init__()`
- `async generate_portal_id()`
- `generate_portal_id_sync()`
- `get_configuration_summary()`

#### PortalIdServiceFactory

Factory for creating pre-configured Portal ID services.

**Methods:**

- `create_isp_service()`
- `create_legacy_service()`
- `create_management_service()`
- `create_custom_service()`

*Source: /home/dotmac_framework/src/dotmac_shared/portal_id/core/service.py*

## dotmac_shared.project_management.__init__

DotMac Shared Project Management Package

Universal project management system for installation projects, service deployments,
infrastructure projects, and general project lifecycle management.

Key Features:

- Multi-phase project tracking with dependencies
- Milestone management and deadline tracking
- Resource allocation and team assignment
- Customer communication and visibility
- Cost tracking and budget management
- Document and photo management
- Real-time progress updates
- SLA compliance monitoring

Use Cases:

- ISP Framework: Customer installation projects, network expansions
- Management Platform: Infrastructure deployments, system upgrades
- General: Any multi-phase project with stakeholders and deadlines

*Source: /home/dotmac_framework/src/dotmac_shared/project_management/__init__.py*

## dotmac_shared.project_management.adapters.platform_adapter

Platform adapters for integrating project management with Management Platform and ISP Framework.

### Classes

#### BasePlatformAdapter

Base adapter for platform-specific project integration.

**Methods:**

- `__init__()`
- `async get_customer_info()`
- `async get_user_info()`
- `async send_notification()`
- `async create_calendar_event()`

#### ISPProjectAdapter

Adapter for ISP Framework project integration.

**Methods:**

- `__init__()`
- `async get_customer_info()`
- `async get_user_info()`
- `async send_notification()`
- `async create_calendar_event()`
- `async create_installation_project()`
- `async create_network_expansion_project()`
- `async create_equipment_replacement_project()`

#### ManagementProjectAdapter

Adapter for Management Platform project integration.

**Methods:**

- `__init__()`
- `async get_customer_info()`
- `async get_user_info()`
- `async send_notification()`
- `async create_calendar_event()`
- `async create_tenant_deployment_project()`
- `async create_infrastructure_upgrade_project()`
- `async create_data_migration_project()`

#### ProjectPlatformAdapter

Main adapter that routes to appropriate platform adapters.

**Methods:**

- `__init__()`
- `get_adapter()`
- `async create_platform_project()`
- `async send_project_notification()`
- `async create_project_calendar_event()`

*Source: /home/dotmac_framework/src/dotmac_shared/project_management/adapters/platform_adapter.py*

## dotmac_shared.project_management.core.models

Universal Project Management Models

Platform-agnostic models for project lifecycle management, suitable for:

- ISP customer installations
- Infrastructure deployments
- Software projects
- Service implementations
- General project tracking

### Classes

#### ProjectType

Universal project types.

#### ProjectStatus

Project lifecycle status.

#### PhaseStatus

Individual phase status.

#### MilestoneType

Standard milestone types.

#### ProjectPriority

Project priority levels.

#### ResourceType

Resource types for project tracking.

#### Project

Universal project model for any type of project management.

**Methods:**

- `is_overdue()`
- `days_remaining()`
- `calculate_completion_percentage()`

#### ProjectPhase

Project phases for detailed progress tracking.

**Methods:**

- `is_overdue()`

#### ProjectMilestone

Project milestones for key checkpoint tracking.

**Methods:**

- `is_overdue()`

#### ProjectUpdate

Project updates and communication log.

#### ProjectResource

Project resource allocation and tracking.

#### ProjectDocument

Project document management.

#### ProjectCreate

Schema for creating projects.

#### ProjectUpdate

Schema for updating projects.

#### ProjectResponse

Schema for project responses.

#### PhaseCreate

Schema for creating project phases.

#### PhaseUpdate

Schema for updating project phases.

#### PhaseResponse

Schema for project phase responses.

#### MilestoneCreate

Schema for creating milestones.

#### MilestoneResponse

Schema for milestone responses.

#### UpdateCreate

Schema for creating project updates.

#### UpdateResponse

Schema for update responses.

*Source: /home/dotmac_framework/src/dotmac_shared/project_management/core/models.py*

## dotmac_shared.project_management.core.project_manager

Core Project Management System

Universal project manager providing CRUD operations, lifecycle management,
and business logic for any type of project.

### Classes

#### ProjectManager

Core project management system.

**Methods:**

- `__init__()`
- `generate_project_number()`
- `async create_project()`
- `async get_project()`
- `async get_project_by_number()`
- `async update_project()`
- `async list_projects()`
- `async create_project_phase()`
- `async update_project_phase()`
- `async create_project_milestone()`
- `async add_project_update()`
- `async get_project_analytics()`
- `async _create_default_phases()`
- `async _handle_status_change()`
- `async _trigger_project_created_events()`
- `async _trigger_project_updated_events()`
- `async _trigger_update_events()`

#### GlobalProjectManager

Global singleton project manager.

**Methods:**

- `__init__()`
- `initialize()`
- `get_instance()`

*Source: /home/dotmac_framework/src/dotmac_shared/project_management/core/project_manager.py*

## dotmac_shared.project_management.services.project_service

High-level Project Management Service

Business logic layer that orchestrates project operations, workflows,
and cross-platform integrations.

### Classes

#### ProjectService

High-level project management service with business logic.

**Methods:**

- `__init__()`
- `async create_customer_project()`
- `async assign_project_manager()`
- `async start_project()`
- `async complete_project()`
- `async start_project_phase()`
- `async complete_project_phase()`
- `async escalate_project()`
- `async get_customer_projects()`
- `async get_team_projects()`
- `async get_overdue_projects()`
- `async get_project_dashboard()`
- `async _apply_project_creation_rules()`
- `async _create_installation_milestones()`
- `async _create_deployment_milestones()`
- `async _check_next_phase_start()`

*Source: /home/dotmac_framework/src/dotmac_shared/project_management/services/project_service.py*

## dotmac_shared.project_management.workflows.project_workflows

Project Workflow Management

Automated workflows for project lifecycle management, notifications,
and cross-system integrations.

### Classes

#### WorkflowTrigger

Workflow trigger events.

#### WorkflowAction

Available workflow actions.

#### WorkflowRule

A workflow rule that defines trigger conditions and actions.

**Methods:**

- `__init__()`
- `matches()`

#### ProjectWorkflowManager

Manages automated project workflows and business rules.

**Methods:**

- `__init__()`
- `add_workflow_rule()`
- `register_action_handler()`
- `async trigger_workflow()`
- `async process_project_created()`
- `async process_project_status_change()`
- `async process_phase_completion()`
- `async process_milestone_reached()`
- `async check_overdue_items()`
- `async _execute_rule_actions()`
- `async _handle_send_notification()`
- `async _handle_create_calendar_event()`
- `async _handle_assign_team()`
- `async _handle_update_status()`
- `async _handle_escalate_priority()`
- `async _handle_send_client_update()`

*Source: /home/dotmac_framework/src/dotmac_shared/project_management/workflows/project_workflows.py*

## dotmac_shared.provisioning.__init__

DotMac Shared Provisioning Services

Container provisioning system supporting automated ISP Framework deployment
with 4-minute deployment business requirement.

Key Features:

- Automated container creation from ISP Framework template
- Environment variable injection (database URLs, tenant configs)
- Resource allocation based on customer count (50-10,000 customers)
- Container health validation during provisioning
- Rollback capability if provisioning fails

Usage:
    from dotmac_shared.provisioning import provision_isp_container

    result = await provision_isp_container(
        isp_id=UUID("..."),
        customer_count=500,
        config=ISPConfig(...)
    )

*Source: /home/dotmac_framework/src/dotmac_shared/provisioning/__init__.py*

## dotmac_shared.provisioning.adapters.__init__

Infrastructure adapters for the DotMac Container Provisioning Service.

*Source: /home/dotmac_framework/src/dotmac_shared/provisioning/adapters/__init__.py*

## dotmac_shared.provisioning.adapters.docker_adapter

Docker deployment adapter for the DotMac Container Provisioning Service.

### Classes

#### DockerAdapter

Handles Docker-specific deployment operations.

**Methods:**

- `__init__()`
- `async _initialize_client()`
- `async provision_infrastructure()`
- `async _create_docker_network()`
- `async _create_volumes()`
- `async _prepare_environment_config()`
- `async deploy_container()`
- `async _create_compose_file()`
- `async _deploy_with_compose()`
- `async _wait_for_containers_healthy()`
- `async configure_networking()`
- `async configure_ssl()`
- `async configure_monitoring()`
- `async rollback_deployment()`
- `async _cleanup_infrastructure()`

*Source: /home/dotmac_framework/src/dotmac_shared/provisioning/adapters/docker_adapter.py*

## dotmac_shared.provisioning.adapters.kubernetes_adapter

Kubernetes deployment adapter for the DotMac Container Provisioning Service.

### Classes

#### KubernetesAdapter

Handles Kubernetes-specific deployment operations.

**Methods:**

- `__init__()`
- `async _initialize_client()`
- `async provision_infrastructure()`
- `async _create_namespace()`
- `async _create_configmaps()`
- `async _create_secrets()`
- `async _create_persistent_volumes()`
- `async _create_network_policies()`
- `async deploy_container()`
- `async _create_deployment()`
- `async _create_service()`
- `async _wait_for_deployment_ready()`
- `async configure_networking()`
- `async configure_ssl()`
- `async configure_monitoring()`
- `async rollback_deployment()`
- `async _cleanup_infrastructure()`

*Source: /home/dotmac_framework/src/dotmac_shared/provisioning/adapters/kubernetes_adapter.py*

## dotmac_shared.provisioning.adapters.resource_calculator

Resource calculation adapter for optimal container resource allocation.

### Classes

#### ResourceCalculator

Calculates optimal resource allocation based on customer count and requirements.

**Methods:**

- `async calculate_optimal_resources()`
- `async estimate_cost()`
- `async recommend_plan_type()`
- `async validate_resource_limits()`

*Source: /home/dotmac_framework/src/dotmac_shared/provisioning/adapters/resource_calculator.py*

## dotmac_shared.provisioning.core.__init__

Core provisioning components for the DotMac Container Provisioning Service.

*Source: /home/dotmac_framework/src/dotmac_shared/provisioning/core/__init__.py*

## dotmac_shared.provisioning.core.exceptions

Exception classes for the DotMac Container Provisioning Service.

### Classes

#### ProvisioningError

Base exception for container provisioning errors.

**Methods:**

- `__init__()`
- `__str__()`

#### ValidationError

Exception raised when container validation fails.

**Methods:**

- `__init__()`

#### RollbackError

Exception raised when rollback operations fail.

**Methods:**

- `__init__()`

#### ResourceCalculationError

Exception raised when resource calculation fails.

**Methods:**

- `__init__()`

#### TemplateError

Exception raised when container template operations fail.

**Methods:**

- `__init__()`

#### InfrastructureError

Exception raised when infrastructure provisioning fails.

**Methods:**

- `__init__()`

#### TimeoutError

Exception raised when provisioning operations timeout.

**Methods:**

- `__init__()`

#### ConfigurationError

Exception raised when configuration is invalid or missing.

**Methods:**

- `__init__()`

#### DeploymentError

Exception raised during container deployment phase.

**Methods:**

- `__init__()`

#### HealthCheckError

Exception raised when health checks fail during provisioning.

**Methods:**

- `__init__()`

*Source: /home/dotmac_framework/src/dotmac_shared/provisioning/core/exceptions.py*

## dotmac_shared.provisioning.core.models

Data models for the DotMac Container Provisioning Service.

### Classes

#### PlanType

ISP Framework service plan types.

#### DeploymentStatus

Container deployment status.

#### HealthStatus

Container health status.

#### InfrastructureType

Infrastructure deployment type.

#### ResourceRequirements

Container resource requirements specification.

**Methods:**

- `validate_cpu()`
- `validate_memory()`
- `to_kubernetes_limits()`
- `to_docker_limits()`

#### NetworkConfig

Network configuration for container deployment.

**Methods:**

- `validate_domain()`

#### DatabaseConfig

Database configuration for ISP instance.

#### FeatureFlags

Feature flags for ISP Framework instance.

**Methods:**

- `from_plan_type()`

#### ISPConfig

Complete ISP Framework configuration.

**Methods:**

- `set_defaults()`

#### ProvisioningRequest

Request to provision a new ISP Framework container.

#### ContainerHealth

Container health check results.

#### DeploymentArtifacts

Artifacts created during deployment.

#### ProvisioningResult

Result of container provisioning operation.

**Methods:**

- `add_log()`
- `mark_completed()`

#### ProvisioningSettings

Settings for the provisioning service.

#### Config

#### Config

#### Config

*Source: /home/dotmac_framework/src/dotmac_shared/provisioning/core/models.py*

## dotmac_shared.provisioning.core.provisioner

Main provisioning orchestrator for the DotMac Container Provisioning Service.

Implements the core provision_isp_container function supporting the 4-minute deployment
business requirement with comprehensive health validation and rollback capability.

### Classes

#### ContainerProvisioner

Main orchestrator for container provisioning operations.

**Methods:**

- `__init__()`
- `async provision_container()`
- `async _validate_provisioning_request()`
- `async _calculate_resources()`
- `async _provision_infrastructure()`
- `async _deploy_container()`
- `async _configure_services()`
- `async _validate_deployment_health()`
- `async _handle_rollback()`
- `async get_provisioning_status()`
- `async list_active_operations()`

*Source: /home/dotmac_framework/src/dotmac_shared/provisioning/core/provisioner.py*

## dotmac_shared.provisioning.core.templates

Container template management for the DotMac Provisioning Service.

### Classes

#### ContainerTemplate

Container deployment template.

**Methods:**

- `render()`

#### TemplateManager

Manages container deployment templates.

**Methods:**

- `__init__()`
- `async load_templates()`
- `async _load_template_file()`
- `async get_template()`
- `async render_template()`
- `async _create_default_templates()`
- `async _create_kubernetes_template()`
- `async _create_docker_template()`
- `async _save_template()`
- `async list_templates()`
- `async validate_template()`

*Source: /home/dotmac_framework/src/dotmac_shared/provisioning/core/templates.py*

## dotmac_shared.provisioning.core.validators

Container health validation for the DotMac Provisioning Service.

### Classes

#### HealthValidator

Validates container health during and after provisioning.

**Methods:**

- `__init__()`
- `async __aenter__()`
- `async __aexit__()`
- `async validate_container_health()`
- `async _check_api_health()`
- `async _check_database_health()`
- `async _check_cache_health()`
- `async _check_ssl_health()`
- `async _check_custom_endpoints()`
- `async wait_for_healthy()`
- `async get_container_metrics()`

#### ProvisioningValidator

Validates provisioning process and requirements.

**Methods:**

- `async validate_provisioning_request()`
- `async validate_infrastructure_readiness()`

*Source: /home/dotmac_framework/src/dotmac_shared/provisioning/core/validators.py*

## dotmac_shared.sales.__init__

DotMac Sales - Customer Relationship Management Toolkit

This package provides comprehensive CRM and sales management capabilities:

- Lead management and scoring
- Opportunity pipeline tracking
- Sales activity management
- Quote and proposal generation
- Sales forecasting and analytics
- Territory management
- Multi-tenant sales operations

*Source: /home/dotmac_framework/src/dotmac_shared/sales/__init__.py*

## dotmac_shared.sales.adapters.__init__

Sales platform adapters.

*Source: /home/dotmac_framework/src/dotmac_shared/sales/adapters/__init__.py*

## dotmac_shared.sales.adapters.isp_adapter

ISP Framework adapter for sales package integration.

### Classes

#### ISPSalesAdapter

Adapter for integrating sales package with ISP Framework.

This adapter provides ISP-specific sales functionality including:

- Customer prospect management
- Service opportunity tracking
- Sales activity integration with customer portal
- Territory-based sales management

**Methods:**

- `__init__()`
- `async create_customer_prospect()`
- `async create_service_opportunity()`
- `async track_customer_interaction()`
- `async get_territory_prospects()`
- `async get_sales_dashboard_data()`

*Source: /home/dotmac_framework/src/dotmac_shared/sales/adapters/isp_adapter.py*

## dotmac_shared.sales.core.__init__

Core sales components.

*Source: /home/dotmac_framework/src/dotmac_shared/sales/core/__init__.py*

## dotmac_shared.sales.core.models

Sales models for pipeline management, lead tracking, and sales performance.

### Classes

#### LeadSource

Lead source types.

#### LeadStatus

Lead status.

#### OpportunityStage

Opportunity sales stages.

#### OpportunityStatus

Opportunity status.

#### ActivityType

Sales activity types.

#### ActivityStatus

Activity status.

#### QuoteStatus

Quote status.

#### CustomerType

Customer types.

#### Lead

Sales leads and prospects.

**Methods:**

- `full_name()`
- `days_since_creation()`
- `is_overdue_follow_up()`
- `__repr__()`

#### Opportunity

Sales opportunities and deals.

**Methods:**

- `is_won()`
- `is_overdue()`
- `age_days()`
- `__repr__()`

#### SalesActivity

Sales activities and interactions.

**Methods:**

- `is_overdue()`
- `days_until_scheduled()`
- `__repr__()`

#### Quote

Sales quotes and proposals.

**Methods:**

- `is_expired()`
- `days_to_expiry()`
- `response_time_days()`
- `__repr__()`

#### QuoteLineItem

Individual line items in quotes.

**Methods:**

- `effective_unit_price()`
- `margin_percentage()`
- `__repr__()`

#### SalesForecast

Sales forecasting and pipeline analysis.

**Methods:**

- `quota_achievement()`
- `pipeline_coverage()`
- `__repr__()`

#### Territory

Sales territories and coverage areas.

**Methods:**

- `__repr__()`

#### Lead

Lead model stub.

#### Opportunity

Opportunity model stub.

#### SalesActivity

SalesActivity model stub.

#### Quote

Quote model stub.

#### QuoteLineItem

QuoteLineItem model stub.

#### SalesForecast

SalesForecast model stub.

#### Territory

Territory model stub.

#### TenantModel

#### StatusMixin

#### AuditMixin

#### ContactMixin

#### AddressMixin

*Source: /home/dotmac_framework/src/dotmac_shared/sales/core/models.py*

## dotmac_shared.sales.core.reseller_models

Reseller-specific models extending the shared sales service.
Supports both ISP Framework and Management Platform reseller operations.

### Classes

#### ResellerType

Reseller types.

#### ResellerStatus

Reseller status.

#### ResellerTier

Reseller tier levels.

#### CommissionStructure

Commission structure types.

#### ResellerCertificationStatus

Certification status.

#### Reseller

Reseller partner management.

**Methods:**

- `quota_achievement_percentage()`
- `is_certification_expired()`
- `days_until_agreement_expiry()`
- `__repr__()`

#### ResellerOpportunity

Opportunities managed by resellers.

**Methods:**

- `__repr__()`

#### ResellerCustomer

Customers managed by resellers.

**Methods:**

- `__repr__()`

#### ResellerCommission

Commission payments to resellers.

**Methods:**

- `is_overdue()`
- `__repr__()`

#### ResellerTraining

Training and certification tracking for resellers.

**Methods:**

- `is_expired()`
- `__repr__()`

#### Reseller

Reseller model stub.

#### ResellerOpportunity

ResellerOpportunity model stub.

#### ResellerCustomer

ResellerCustomer model stub.

#### ResellerCommission

ResellerCommission model stub.

#### ResellerTraining

ResellerTraining model stub.

*Source: /home/dotmac_framework/src/dotmac_shared/sales/core/reseller_models.py*

## dotmac_shared.sales.core.schemas

Sales API schemas for requests and responses.

### Classes

#### LeadBase

Base lead schema.

#### LeadCreate

Schema for creating leads.

#### LeadUpdate

Schema for updating leads.

#### LeadQualification

Schema for lead qualification.

#### LeadResponse

Schema for lead responses.

#### OpportunityBase

Base opportunity schema.

#### OpportunityCreate

Schema for creating opportunities.

#### OpportunityUpdate

Schema for updating opportunities.

#### OpportunityStageUpdate

Schema for updating opportunity stage.

#### OpportunityClose

Schema for closing opportunities.

#### OpportunityResponse

Schema for opportunity responses.

#### SalesActivityBase

Base sales activity schema.

#### SalesActivityCreate

Schema for creating sales activities.

#### SalesActivityUpdate

Schema for updating sales activities.

#### SalesActivityComplete

Schema for completing activities.

#### SalesActivityResponse

Schema for sales activity responses.

#### SalesDashboard

Sales dashboard data.

#### SalesMetrics

Sales performance metrics.

#### LeadConversionFunnel

Lead conversion funnel analysis.

#### PipelineSummary

Sales pipeline summary.

#### SalesForecast

Sales forecast data.

#### LeadListResponse

Lead list response.

#### OpportunityListResponse

Opportunity list response.

#### SalesActivityListResponse

Sales activity list response.

#### LeadFilters

Lead filtering options.

#### OpportunityFilters

Opportunity filtering options.

#### ActivityFilters

Activity filtering options.

#### BaseModel

#### TenantModelSchema

*Source: /home/dotmac_framework/src/dotmac_shared/sales/core/schemas.py*

## dotmac_shared.sales.repositories.__init__

Sales repository components.

*Source: /home/dotmac_framework/src/dotmac_shared/sales/repositories/__init__.py*

## dotmac_shared.sales.repositories.lead_repository

Lead repository for database operations.

### Classes

#### LeadRepository

Repository for lead database operations.

**Methods:**

- `__init__()`
- `async create_lead()`
- `async get_lead_by_id()`
- `async update_lead()`
- `async update_lead_score()`
- `async update_lead_status()`
- `async list_leads()`
- `async qualify_lead()`
- `async convert_lead()`
- `async get_overdue_leads()`
- `async get_all_leads_for_scoring()`
- `async get_lead_statistics()`
- `async delete_lead()`

*Source: /home/dotmac_framework/src/dotmac_shared/sales/repositories/lead_repository.py*

## dotmac_shared.sales.scoring.__init__

Sales scoring components.

*Source: /home/dotmac_framework/src/dotmac_shared/sales/scoring/__init__.py*

## dotmac_shared.sales.scoring.engine

Lead scoring engine using Strategy pattern.

### Classes

#### LeadScoringEngine

Lead scoring engine using Strategy pattern.

REFACTORED: Replaces 14-complexity _calculate_lead_score method with
focused, configurable scoring strategies (Complexity: 3).

**Methods:**

- `__init__()`
- `calculate_lead_score()`
- `get_scoring_breakdown()`
- `add_scoring_strategy()`
- `remove_scoring_strategy()`
- `get_active_strategies()`

#### WeightedLeadScoringEngine

Advanced lead scoring engine with weighted strategies.
Allows different importance weights for different scoring criteria.

**Methods:**

- `__init__()`
- `calculate_lead_score()`

*Source: /home/dotmac_framework/src/dotmac_shared/sales/scoring/engine.py*

## dotmac_shared.sales.scoring.strategies

Lead scoring strategies using Strategy pattern.
Replaces the 14-complexity _calculate_lead_score method with focused scoring strategies.

### Classes

#### LeadScoringStrategy

Base strategy for lead scoring criteria.

**Methods:**

- `calculate_score()`
- `get_strategy_name()`

#### BudgetScoringStrategy

Strategy for scoring based on budget capacity.

**Methods:**

- `calculate_score()`
- `get_strategy_name()`

#### CustomerTypeScoringStrategy

Strategy for scoring based on customer type.

**Methods:**

- `__init__()`
- `calculate_score()`
- `get_strategy_name()`

#### LeadSourceScoringStrategy

Strategy for scoring based on lead source quality.

**Methods:**

- `__init__()`
- `calculate_score()`
- `get_strategy_name()`

#### BANTScoringStrategy

Strategy for scoring based on BANT (Budget, Authority, Need, Timeline) criteria.

**Methods:**

- `calculate_score()`
- `get_strategy_name()`

#### CompanySizeScoringStrategy

Strategy for scoring based on company size indicators.

**Methods:**

- `calculate_score()`
- `get_strategy_name()`

#### EngagementScoringStrategy

Strategy for scoring based on engagement indicators.

**Methods:**

- `calculate_score()`
- `get_strategy_name()`

*Source: /home/dotmac_framework/src/dotmac_shared/sales/scoring/strategies.py*

## dotmac_shared.sales.services.__init__

Sales service components.

*Source: /home/dotmac_framework/src/dotmac_shared/sales/services/__init__.py*

## dotmac_shared.schemas.base_schemas

Production-ready schema base classes with strict validation enforcement.
Mandatory inheritance for all schemas - no custom BaseModel usage allowed.

### Classes

#### SchemaValidationError

Raised when schemas don't follow DRY patterns.

#### BaseSchema

Production-ready root base schema with strict validation.

**Methods:**

- `__init_subclass__()`

#### TimestampMixin

Mixin for entities with timestamps - used in 80% of schemas.

**Methods:**

- `parse_datetime()`

#### IdentifiedMixin

Mixin for entities with UUID identification.

#### NamedMixin

Mixin for entities with name fields.

**Methods:**

- `validate_name()`

#### DescriptionMixin

Mixin for entities with description fields.

#### StatusMixin

Mixin for entities with status tracking.

#### TenantMixin

Mixin for multi-tenant entities.

#### EmailMixin

Mixin for entities with email fields.

**Methods:**

- `validate_email()`

#### PhoneMixin

Mixin for entities with phone fields.

**Methods:**

- `validate_phone()`

#### AddressMixin

Mixin for entities with address fields.

**Methods:**

- `validate_address()`

#### BaseEntity

Base class for all entities with ID and timestamps.

#### NamedEntity

Base class for named entities with descriptions.

#### ActiveEntity

Base class for entities with status tracking.

#### TenantEntity

Base class for multi-tenant entities.

#### PersonEntity

Base class for person-related entities.

**Methods:**

- `full_name()`

#### CompanyEntity

Base class for company/organization entities.

#### BaseCreateSchema

Base schema for create operations.

#### BaseUpdateSchema

Base schema for update operations - all fields optional.

#### BaseResponseSchema

Base schema for API responses.

#### PaginationSchema

Standard pagination parameters.

**Methods:**

- `offset()`

#### PaginatedResponseSchema

Standard paginated response format.

**Methods:**

- `calculate_pages()`

#### SearchSchema

Standard search parameters.

#### CurrencyMixin

Mixin for entities with currency fields.

#### DateRangeMixin

Mixin for entities with date ranges.

**Methods:**

- `validate_date_range()`

#### GeoLocationMixin

Mixin for entities with geographic coordinates.

#### Config

#### Config

#### Config

*Source: /home/dotmac_framework/src/dotmac_shared/schemas/base_schemas.py*

## dotmac_shared.scripts.dev-setup

Developer Environment Setup Script for DotMac Framework

This script automates the setup of a complete development environment
including all dependencies, tools, and configurations.

### Classes

#### Colors

Terminal color constants.

#### DevSetup

Development environment setup manager.

**Methods:**

- `__init__()`
- `print_banner()`
- `run_setup()`
- `log_step()`
- `log_success()`
- `log_warning()`
- `log_error()`
- `run_command()`
- `check_tool_version()`
- `check_system_requirements()`
- `print_installation_instructions()`
- `setup_python_environment()`
- `install_dependencies()`
- `setup_git_hooks()`
- `setup_docker_environment()`
- `initialize_databases()`
- `setup_frontend()`
- `configure_dev_tools()`
- `run_initial_tests()`
- `generate_documentation()`
- `generate_quickstart_guide()`
- `generate_testing_guide()`
- `print_success_message()`

*Source: /home/dotmac_framework/src/dotmac_shared/scripts/dev-setup.py*

## dotmac_shared.secrets.__init__

DotMac Secrets - Enterprise Secrets Management Package

This package provides comprehensive secrets management capabilities including:

- Enterprise-grade secrets management with compliance support
- OpenBao/Vault integration for secure secret storage
- Field-level encryption for sensitive data protection
- Role-Based Access Control (RBAC) for secrets access
- Multi-tenant secrets isolation
- Secrets rotation and lifecycle management
- Audit logging for security compliance

Features:

- SOC2, PCI DSS, ISO27001, GDPR compliant secret handling
- Multiple authentication methods (Token, AppRole, Kubernetes, AWS)
- Secret caching with TTL for performance
- Encryption as a Service capabilities
- Dynamic secret generation
- Hierarchical permission system

*Source: /home/dotmac_framework/src/dotmac_shared/secrets/__init__.py*

## dotmac_shared.secrets.adapters.__init__

Platform adapters for secrets integration.

*Source: /home/dotmac_framework/src/dotmac_shared/secrets/adapters/__init__.py*

## dotmac_shared.secrets.adapters.isp_adapter

ISP Framework Secrets Adapter

Provides integration between the ISP Framework and the shared secrets management system.

### Classes

#### ISPSecretsAdapter

Adapter for ISP Framework secrets integration.

Provides:

- ISP-specific secret management
- Tenant-based secret isolation
- Customer data encryption
- Network device credentials

**Methods:**

- `__init__()`
- `async get_database_credentials()`
- `async get_radius_secret()`
- `async get_jwt_secret()`
- `async get_customer_encryption_key()`
- `async store_device_credentials()`
- `async get_device_credentials()`
- `async rotate_tenant_secrets()`
- `async setup_tenant_rbac()`
- `async health_check()`

*Source: /home/dotmac_framework/src/dotmac_shared/secrets/adapters/isp_adapter.py*

## dotmac_shared.secrets.adapters.management_adapter

Management Platform Secrets Adapter

Provides integration between the Management Platform and the shared secrets management system.

### Classes

#### ManagementPlatformSecretsAdapter

Adapter for Management Platform secrets integration.

Provides:

- Multi-tenant secret management
- Organization-based access control
- API key management
- Webhook secret handling

**Methods:**

- `__init__()`
- `async get_platform_api_key()`
- `async get_database_encryption_key()`
- `async get_webhook_signing_secret()`
- `async get_jwt_secret()`
- `async get_oauth_credentials()`
- `async store_organization_secrets()`
- `async get_organization_secrets()`
- `async generate_api_key()`
- `async revoke_api_key()`
- `async setup_organization_rbac()`
- `async health_check()`

*Source: /home/dotmac_framework/src/dotmac_shared/secrets/adapters/management_adapter.py*

## dotmac_shared.secrets.core.__init__

Core secrets management components.

*Source: /home/dotmac_framework/src/dotmac_shared/secrets/core/__init__.py*

## dotmac_shared.secrets.core.enterprise_secrets_manager

Enterprise Secrets Management System

SECURITY ENHANCEMENT: Addresses critical issues identified in quality analysis:

1. Replaces hardcoded secrets with secure environment variable management
2. Implements proper secrets rotation and lifecycle management
3. Provides enterprise-grade secret validation and compliance
4. Integrates with Vault for production environments

COMPLIANCE: SOC2, PCI DSS, ISO27001, GDPR compliant secret handling.

### Classes

#### SecretType

Types of secrets managed by the system.

#### SecretSource

Sources from which secrets can be retrieved.

#### SecretValidationResult

Result of secret validation.

#### EnterpriseSecretsManager

Enterprise-grade secrets management system.

SECURITY FEATURES:

- Secure secret retrieval from multiple sources
- Validation and compliance checking
- Automatic secret rotation
- Audit logging and monitoring
- Integration with Vault and cloud secret managers

**Methods:**

- `__init__()`
- `register_secret()`
- `async get_secret()`
- `async _retrieve_from_source()`
- `async _read_file_secret()`
- `async validate_secret()`
- `async _validate_secret_access()`
- `async rotate_secret()`
- `async list_secrets()`
- `async health_check()`

#### SecretValidationRule

Validation rules for secrets.

#### SecretMetadata

Metadata associated with a secret.

#### SecretValidationRule

#### SecretMetadata

*Source: /home/dotmac_framework/src/dotmac_shared/secrets/core/enterprise_secrets_manager.py*

## dotmac_shared.security.api_auth_middleware

API Authentication Middleware for DotMac Framework

### Classes

#### APIAuthMiddleware

JWT-based API authentication middleware.

**Methods:**

- `__init__()`
- `async authenticate_request()`
- `generate_token()`

#### RateLimiter

Rate limiting middleware.

**Methods:**

- `__init__()`
- `async check_rate_limit()`
- `async get_rate_limit_status()`
- `async reset_rate_limit()`

#### SecurityHeaders

Security headers middleware.

**Methods:**

- `__init__()`
- `add_security_headers()`

#### InputSanitizer

Input sanitization utilities.

**Methods:**

- `__init__()`
- `sanitize_html()`
- `sanitize_sql_input()`
- `validate_email()`
- `sanitize_filename()`
- `sanitize_url()`
- `escape_html_entities()`

*Source: /home/dotmac_framework/src/dotmac_shared/security/api_auth_middleware.py*

## dotmac_shared.security.api_security_integration

API Security Integration and Validation Suite
Integrates all API security components and provides comprehensive security validation

SECURITY: This module coordinates all security middleware and provides validation
tools to ensure complete API security coverage across the platform

### Classes

#### APISecuritySuite

Comprehensive API security suite that orchestrates all security components

**Methods:**

- `__init__()`
- `async initialize_security_components()`
- `configure_app_security()`
- `async validate_security_implementation()`
- `async _validate_rate_limiting()`
- `async _validate_threat_detection()`
- `async get_security_health_report()`

*Source: /home/dotmac_framework/src/dotmac_shared/security/api_security_integration.py*

## dotmac_shared.security.connection_pool

Tenant-Aware Database Connection Pooling
Provides secure database connections with automatic tenant context management

SECURITY: This module ensures tenant context is properly maintained
across all database connections and operations

### Classes

#### TenantAwareConnectionPool

Connection pool that automatically manages tenant context

**Methods:**

- `__init__()`
- `async get_tenant_session()`
- `async get_admin_session()`
- `async get_connection_stats()`
- `async validate_tenant_isolation()`

*Source: /home/dotmac_framework/src/dotmac_shared/security/connection_pool.py*

## dotmac_shared.security.input_middleware

Input Sanitization Middleware for FastAPI
Automatically sanitizes all incoming request data to prevent security vulnerabilities

### Classes

#### InputSanitizationMiddleware

FastAPI middleware for automatic input sanitization

Features:

- Sanitizes JSON request bodies
- Sanitizes query parameters
- Sanitizes path parameters
- Configurable sanitization rules per endpoint
- Logging of suspicious input patterns

**Methods:**

- `__init__()`
- `is_exempt()`
- `async sanitize_query_params()`
- `async sanitize_json_body()`
- `async sanitize_form_data()`
- `async __call__()`

*Source: /home/dotmac_framework/src/dotmac_shared/security/input_middleware.py*

## dotmac_shared.security.row_level_security

Row Level Security (RLS) Implementation for Multi-Tenant Database Isolation
Provides database-level security policies to prevent cross-tenant data access

SECURITY: This module implements PostgreSQL Row Level Security policies
to ensure complete tenant data isolation at the database level

### Classes

#### RLSPolicyManager

Manager for PostgreSQL Row Level Security policies

Features:

- Automatic RLS policy creation for tenant-aware tables
- Policy validation and testing
- Tenant context management
- Security audit logging

**Methods:**

- `__init__()`
- `async enable_rls_for_table()`
- `async enable_rls_for_all_tenant_tables()`
- `async _find_tenant_tables()`
- `async set_tenant_context()`
- `async clear_tenant_context()`
- `async create_tenant_isolation_function()`
- `async create_audit_trigger_function()`
- `async create_audit_log_table()`
- `async add_audit_triggers_to_table()`
- `async validate_tenant_isolation()`
- `async get_rls_status()`

*Source: /home/dotmac_framework/src/dotmac_shared/security/row_level_security.py*

## dotmac_shared.service_assurance.core.enums

Service Assurance enumeration types.

### Classes

#### ProbeType

Service probe type enumeration.

#### ProbeStatus

Service probe status.

#### AlarmSeverity

Alarm severity levels.

#### AlarmStatus

Alarm status enumeration.

#### AlarmType

Alarm type classification.

#### EventType

Event type enumeration.

#### FlowType

Flow data type enumeration.

#### CollectorStatus

Flow collector status.

#### SLAComplianceStatus

SLA compliance status.

#### SuppressionStatus

Alarm suppression status.

#### ViolationType

SLA violation type.

*Source: /home/dotmac_framework/src/dotmac_shared/service_assurance/core/enums.py*

## dotmac_shared.service_assurance.core.models

Service Assurance database models and schemas.

### Classes

#### ProbeCreate

Schema for creating a service probe.

#### ProbeResponse

Schema for probe response.

#### ProbeResultCreate

Schema for creating a probe result.

#### ProbeResultResponse

Schema for probe result response.

#### AlarmRuleCreate

Schema for creating an alarm rule.

#### AlarmResponse

Schema for alarm response.

#### FlowRecordCreate

Schema for creating a flow record.

#### FlowCollectorCreate

Schema for creating a flow collector.

#### SLAPolicyCreate

Schema for creating an SLA policy.

#### ProbeCreate

ProbeCreate schema stub.

#### ProbeResponse

ProbeResponse schema stub.

#### ProbeResultCreate

ProbeResultCreate schema stub.

#### ProbeResultResponse

ProbeResultResponse schema stub.

#### AlarmRuleCreate

AlarmRuleCreate schema stub.

#### AlarmResponse

AlarmResponse schema stub.

#### FlowRecordCreate

FlowRecordCreate schema stub.

#### FlowCollectorCreate

FlowCollectorCreate schema stub.

#### SLAPolicyCreate

SLAPolicyCreate schema stub.

#### ServiceProbe

Service assurance probe definition.

#### ProbeResult

Service probe execution result.

#### AlarmRule

Alarm generation rule.

#### Alarm

Network/service alarm.

#### FlowCollector

Network flow data collector.

#### FlowRecord

Network flow record.

#### SLAPolicy

Service Level Agreement policy.

#### SLAViolation

SLA policy violation record.

#### ServiceProbe

ServiceProbe model stub.

#### ProbeResult

ProbeResult model stub.

#### AlarmRule

AlarmRule model stub.

#### Alarm

Alarm model stub.

#### FlowCollector

FlowCollector model stub.

#### FlowRecord

FlowRecord model stub.

#### SLAPolicy

SLAPolicy model stub.

#### SLAViolation

SLAViolation model stub.

#### TenantModel

#### StatusMixin

#### AuditMixin

*Source: /home/dotmac_framework/src/dotmac_shared/service_assurance/core/models.py*

## dotmac_shared.service_assurance.sdk.service_assurance_sdk

Service Assurance unified SDK interface.

### Classes

#### ServiceAssuranceError

Service Assurance SDK error.

#### ServiceAssuranceSDK

Unified SDK for Service Assurance operations.

**Methods:**

- `__init__()`
- `async create_icmp_probe()`
- `async create_dns_probe()`
- `async create_http_probe()`
- `async create_tcp_probe()`
- `async execute_probe()`
- `async get_probe_statistics()`
- `async list_probes()`
- `async create_sla_policy()`
- `async check_sla_compliance()`
- `async get_sla_violations()`
- `async create_snmp_alarm_rule()`
- `async create_syslog_alarm_rule()`
- `async process_snmp_trap()`
- `async process_syslog_message()`
- `async acknowledge_alarm()`
- `async clear_alarm()`
- `async suppress_alarms()`
- `async get_active_alarms()`
- `async get_alarm_statistics()`
- `async create_netflow_collector()`
- `async create_sflow_collector()`
- `async ingest_flow_data()`
- `async get_traffic_summary()`
- `async get_top_talkers()`
- `async aggregate_flows()`
- `async aggregate_traffic_by_subnet()`
- `async get_protocol_statistics()`
- `async list_collectors()`
- `async get_collector_statistics()`
- `async get_service_health_dashboard()`
- `async get_network_performance_report()`
- `async health_check()`

*Source: /home/dotmac_framework/src/dotmac_shared/service_assurance/sdk/service_assurance_sdk.py*

## dotmac_shared.service_assurance.utils.event_parsers

Event parsing utilities for SNMP traps and syslog messages.

### Classes

#### SNMPTrapParser

Parser for SNMP trap messages.

**Methods:**

- `__init__()`
- `parse_trap_data()`
- `parse_varbind()`
- `get_trap_name()`
- `get_enterprise_name()`
- `analyze_trap_severity()`

#### SyslogParser

Parser for syslog messages.

**Methods:**

- `__init__()`
- `parse_syslog_message()`
- `parse_structured_data()`
- `is_valid_hostname_or_ip()`
- `analyze_message_content()`

#### EventNormalizer

Normalize events from different sources to common format.

**Methods:**

- `__init__()`
- `normalize_snmp_trap()`
- `normalize_syslog_message()`
- `extract_event_patterns()`

*Source: /home/dotmac_framework/src/dotmac_shared/service_assurance/utils/event_parsers.py*

## dotmac_shared.service_assurance.utils.metrics_calculators

Metrics calculation and aggregation utilities.

### Classes

#### PerformanceMetrics

Calculate performance metrics from time series data.

**Methods:**

- `__init__()`
- `calculate_availability()`
- `calculate_latency_statistics()`
- `calculate_throughput_metrics()`
- `calculate_error_rate()`

#### SLACalculator

Calculate SLA compliance metrics.

**Methods:**

- `__init__()`
- `calculate_sla_compliance()`
- `calculate_sla_credits()`

#### TrafficAnalyzer

Analyze network traffic patterns and metrics.

**Methods:**

- `__init__()`
- `analyze_flow_patterns()`
- `detect_traffic_anomalies()`

#### AlertingThresholds

Calculate dynamic alerting thresholds based on historical data.

**Methods:**

- `__init__()`
- `calculate_dynamic_thresholds()`

*Source: /home/dotmac_framework/src/dotmac_shared/service_assurance/utils/metrics_calculators.py*

## dotmac_shared.services.__init__

Shared services module for DotMac framework.

*Source: /home/dotmac_framework/src/dotmac_shared/services/__init__.py*

## dotmac_shared.services.service_factory

Deployment-aware service factory for DotMac platforms.

### Classes

#### DeploymentAwareServiceFactory

Factory for creating services based on deployment context.

**Methods:**

- `__init__()`
- `register_service()`
- `get_service()`
- `list_services()`
- `async create_service_registry()`

*Source: /home/dotmac_framework/src/dotmac_shared/services/service_factory.py*

## dotmac_shared.services.service_registry

Service registry for DotMac platforms.

### Classes

#### ServiceInfo

Information about a registered service.

#### ServiceRegistry

Registry for managing services across the platform.

**Methods:**

- `__init__()`
- `register()`
- `get()`
- `get_by_type()`
- `list_all()`
- `unregister()`
- `get_ready_services()`

*Source: /home/dotmac_framework/src/dotmac_shared/services/service_registry.py*

## dotmac_shared.services_framework.__init__

DotMac Services Framework

Universal service lifecycle management system providing:

- Service registration and discovery
- Health monitoring and status management
- Configuration management and validation
- Dependency injection and initialization ordering
- Deployment-aware service creation
- Platform-agnostic business service architecture

This framework standardizes service architecture across all DotMac modules.

*Source: /home/dotmac_framework/src/dotmac_shared/services_framework/__init__.py*

## dotmac_shared.services_framework.core.__init__

Core service framework components.

*Source: /home/dotmac_framework/src/dotmac_shared/services_framework/core/__init__.py*

## dotmac_shared.services_framework.core.base

Base service classes and interfaces for service lifecycle management.

### Classes

#### ServiceStatus

Service status enumeration.

#### ServiceHealth

Service health information.

**Methods:**

- `__post_init__()`

#### BaseService

Base class for all business services.

**Methods:**

- `__init__()`
- `async initialize()`
- `async shutdown()`
- `async health_check()`
- `get_status()`
- `get_health()`
- `is_ready()`
- `is_healthy()`
- `get_config_value()`
- `has_config()`
- `async _set_status()`
- `get_service_info()`

#### ConfigurableService

Base service with configuration validation.

**Methods:**

- `__init__()`
- `validate_config()`
- `get_required_config_status()`
- `async initialize()`
- `async _initialize_service()`
- `async health_check()`
- `async _health_check_service()`

#### StatefulService

Base service with state management capabilities.

**Methods:**

- `__init__()`
- `set_state()`
- `get_state()`
- `has_state()`
- `clear_state()`
- `get_state_info()`
- `async _initialize_service()`
- `async _initialize_stateful_service()`
- `async _health_check_service()`
- `async _health_check_stateful_service()`

*Source: /home/dotmac_framework/src/dotmac_shared/services_framework/core/base.py*

## dotmac_shared.services_framework.core.factory

Service factory for creating deployment-aware business services.

### Classes

#### ServiceCreationResult

Result of service creation.

#### ServiceFactory

Factory for creating business services with configuration.

**Methods:**

- `create_service_config()`
- `async create_auth_service()`
- `async create_payment_service()`
- `async create_notification_service()`
- `async create_analytics_service()`

#### DeploymentAwareServiceFactory

Enhanced service factory with full deployment awareness.

**Methods:**

- `__init__()`
- `async create_service_registry()`
- `async _register_standard_services()`
- `async _register_custom_services()`
- `get_deployment_info()`

*Source: /home/dotmac_framework/src/dotmac_shared/services_framework/core/factory.py*

## dotmac_shared.services_framework.examples.__init__

Examples for the DotMac Services Framework.

*Source: /home/dotmac_framework/src/dotmac_shared/services_framework/examples/__init__.py*

## dotmac_shared.services_framework.services.__init__

Business service implementations.

*Source: /home/dotmac_framework/src/dotmac_shared/services_framework/services/__init__.py*

## dotmac_shared.services_framework.services.analytics_service

Analytics service implementation for DotMac Services Framework.

### Classes

#### AnalyticsServiceConfig

Analytics service configuration.

**Methods:**

- `__post_init__()`

#### AnalyticsService

Service layer - exceptions bubble up to router @standard_exception_handler.

**Methods:**

- `__init__()`
- `async _initialize_stateful_service()`
- `async _initialize_prometheus()`
- `async _initialize_datadog()`
- `async _initialize_newrelic()`
- `async _initialize_custom()`
- `async shutdown()`
- `async _health_check_stateful_service()`
- `async _test_provider_connectivity()`
- `async record_metric()`
- `async record_event()`
- `async record_batch_metrics()`
- `async _flush_metrics()`
- `async _flush_oldest_metrics()`
- `async _send_to_prometheus()`
- `async _send_to_datadog()`
- `async _send_to_newrelic()`
- `async _send_to_custom()`
- `async _send_metrics_batch()`
- `get_analytics_stats()`

*Source: /home/dotmac_framework/src/dotmac_shared/services_framework/services/analytics_service.py*

## dotmac_shared.services_framework.services.auth_service

Authentication service implementation for DotMac Services Framework.

### Classes

#### AuthServiceConfig

Authentication service configuration.

**Methods:**

- `__post_init__()`

#### AuthService

Service layer - exceptions bubble up to router @standard_exception_handler.

**Methods:**

- `__init__()`
- `async _initialize_stateful_service()`
- `async shutdown()`
- `async _health_check_stateful_service()`
- `create_token()`
- `verify_token()`
- `revoke_token()`
- `revoke_all_tokens()`
- `get_active_token_count()`
- `get_issuer()`
- `get_auth_stats()`

*Source: /home/dotmac_framework/src/dotmac_shared/services_framework/services/auth_service.py*

## dotmac_shared.services_framework.utils.__init__

Service framework utilities.

*Source: /home/dotmac_framework/src/dotmac_shared/services_framework/utils/__init__.py*

## dotmac_shared.services_framework.utils.health_monitor

Health monitoring utilities for the DotMac Services Framework.

### Classes

#### HealthAlert

Health alert information.

#### HealthMonitorConfig

Health monitor configuration.

#### HealthMonitor

Health monitoring utility for service registry.

**Methods:**

- `__init__()`
- `async start_monitoring()`
- `async stop_monitoring()`
- `async _monitoring_loop()`
- `async _perform_health_checks()`
- `async _check_service_health()`
- `async _check_status_changes()`
- `async _check_health_degradation()`
- `async _check_service_recovery()`
- `async _send_alert()`
- `get_service_health_history()`
- `get_recent_alerts()`
- `get_service_health_summary()`
- `get_overall_health_status()`
- `get_monitoring_stats()`

*Source: /home/dotmac_framework/src/dotmac_shared/services_framework/utils/health_monitor.py*

## dotmac_shared.testing.frontend_flows

DRY-Compliant Frontend Flow Testing Module

Integrates with existing DRY test orchestration system and follows established patterns.
Uses Poetry environment and pytest framework for consistency.

### Classes

#### UITestResult

Result of a UI test following DRY patterns.

**Methods:**

- `__post_init__()`

#### FrontendFlowResult

Complete frontend flow test result.

**Methods:**

- `total_tests()`
- `passed_tests()`
- `failed_tests()`
- `success_rate()`

#### DRYFrontendFlowTester

DRY-compliant frontend flow tester that integrates with existing architecture.

Features:

- Follows existing DRY patterns and conventions
- Integrates with Poetry environment
- Uses pytest framework consistency
- Leverages existing monitoring system
- Provides structured results for orchestration

**Methods:**

- `__init__()`
- `async setup_browser_context()`
- `log_test_result()`
- `async test_application_connectivity()`
- `async test_login_form_presence()`
- `async test_responsive_behavior()`
- `async run_comprehensive_tests()`

*Source: /home/dotmac_framework/src/dotmac_shared/testing/frontend_flows.py*

## dotmac_shared.ticketing.__init__

DotMac Ticketing System

Universal ticketing system for customer support, technical issues, and service requests.
Provides unified ticket management across Management Platform and ISP Framework.

*Source: /home/dotmac_framework/src/dotmac_shared/ticketing/__init__.py*

## dotmac_shared.ticketing.adapters.platform_adapter

Platform adapters for integrating ticketing with Management Platform and ISP Framework.

### Classes

#### BasePlatformAdapter

Base adapter for platform-specific ticketing integration.

**Methods:**

- `__init__()`
- `async get_customer_info()`
- `async get_user_info()`
- `async send_notification()`

#### ManagementPlatformAdapter

Adapter for Management Platform integration.

**Methods:**

- `__init__()`
- `async get_customer_info()`
- `async get_user_info()`
- `async send_notification()`
- `async create_billing_ticket()`

#### ISPPlatformAdapter

Adapter for ISP Framework integration.

**Methods:**

- `__init__()`
- `async get_customer_info()`
- `async get_user_info()`
- `async send_notification()`
- `async create_network_issue_ticket()`
- `async create_service_request_ticket()`

#### TicketingPlatformAdapter

Main adapter that routes to appropriate platform adapters.

**Methods:**

- `__init__()`
- `get_adapter()`
- `async create_platform_ticket()`

*Source: /home/dotmac_framework/src/dotmac_shared/ticketing/adapters/platform_adapter.py*

## dotmac_shared.ticketing.core.models

Core ticketing models for universal ticket management.

### Classes

#### TicketStatus

Ticket status enumeration.

#### TicketPriority

Ticket priority levels.

#### TicketCategory

Ticket categories.

#### TicketSource

How the ticket was created.

#### Ticket

Core ticket model.

#### TicketComment

Ticket comment/note model.

#### TicketAttachment

Ticket attachment model.

#### TicketEscalation

Ticket escalation tracking.

#### TicketCreate

Create ticket request.

#### TicketUpdate

Update ticket request.

#### TicketResponse

Ticket API response.

#### CommentCreate

Create comment request.

#### CommentResponse

Comment API response.

#### Config

#### Config

*Source: /home/dotmac_framework/src/dotmac_shared/ticketing/core/models.py*

## dotmac_shared.ticketing.core.ticket_manager

Core ticket management system.

### Classes

#### TicketManager

Core ticket management system.

**Methods:**

- `__init__()`
- `generate_ticket_number()`
- `async create_ticket()`
- `async get_ticket()`
- `async get_ticket_by_number()`
- `async update_ticket()`
- `async add_comment()`
- `async list_tickets()`
- `async get_ticket_metrics()`
- `async _handle_status_change()`
- `async _trigger_ticket_created_events()`
- `async _trigger_ticket_updated_events()`
- `async _trigger_comment_added_events()`

#### GlobalTicketManager

Global singleton ticket manager.

**Methods:**

- `__init__()`
- `initialize()`
- `get_instance()`

*Source: /home/dotmac_framework/src/dotmac_shared/ticketing/core/ticket_manager.py*

## dotmac_shared.ticketing.services.ticket_service

High-level ticket service with business logic.

### Classes

#### TicketService

High-level ticket service with business logic.

**Methods:**

- `__init__()`
- `async create_customer_ticket()`
- `async assign_ticket()`
- `async escalate_ticket()`
- `async resolve_ticket()`
- `async close_ticket()`
- `async get_customer_tickets()`
- `async get_team_tickets()`
- `async get_overdue_tickets()`
- `async get_ticket_analytics()`

*Source: /home/dotmac_framework/src/dotmac_shared/ticketing/services/ticket_service.py*

## dotmac_shared.user_management.__init__

DotMac Unified User Management Service

Consolidates user lifecycle management across ISP Framework and Management Platform,
eliminating 8-10 duplicate user service implementations.

Key Components:

- UserLifecycleService: Core user operations (register, activate, update, deactivate)
- Platform Adapters: ISP and Management platform integration
- Profile Manager: User profile and preference management
- Permission Manager: User role and permission assignment
- Auth Integration: Seamless integration with dotmac_shared/auth/

Usage:
    from dotmac_shared.user_management import UserLifecycleService
    from dotmac_shared.user_management.adapters import ISPUserAdapter

    user_service = UserLifecycleService()
    isp_adapter = ISPUserAdapter(db_session, tenant_id)

    # Register new user
    user = await isp_adapter.register_user({
        "email": "user@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "user_type": "customer"
    })

*Source: /home/dotmac_framework/src/dotmac_shared/user_management/__init__.py*

## dotmac_shared.user_management.adapters.__init__

User Management Platform Adapters.

Provides platform-specific adapters for integrating the unified user management
service with ISP Framework and Management Platform.

*Source: /home/dotmac_framework/src/dotmac_shared/user_management/adapters/__init__.py*

## dotmac_shared.user_management.adapters.base_adapter

Base User Management Adapter.

Provides common functionality for platform-specific user management adapters.
Defines the interface and shared operations for ISP and Management Platform adapters.

### Classes

#### BaseUserAdapter

Abstract base class for platform-specific user management adapters.

Provides common functionality and defines the interface that platform
adapters must implement for consistent user management operations.

**Methods:**

- `__init__()`
- `async register_user()`
- `async activate_user()`
- `async deactivate_user()`
- `async get_user()`
- `async get_user_by_email()`
- `async get_user_by_username()`
- `async update_user()`
- `async search_users()`
- `async get_user_profile()`
- `async update_user_profile()`
- `async upload_user_avatar()`
- `async assign_user_roles()`
- `async check_user_permission()`
- `async get_user_permissions()`
- `async get_user_roles()`
- `async authenticate_user()`
- `async logout_user()`
- `async _record_platform_event()`
- `async _create_platform_specific_record()`
- `async _update_platform_specific_record()`
- `async _delete_platform_specific_record()`
- `async _get_platform_specific_data()`
- `async __aenter__()`
- `async __aexit__()`
- `get_config()`
- `set_config()`
- `async bulk_create_users()`

*Source: /home/dotmac_framework/src/dotmac_shared/user_management/adapters/base_adapter.py*

## dotmac_shared.user_management.core.profile_manager

Profile Manager for Unified User Management.

Handles user profile data, preferences, and extended information across platforms.
Provides consistent profile management while supporting platform-specific customizations.

### Classes

#### ProfileManager

Manager for user profile operations.

Handles profile data, preferences, contact information, and avatar management
across both ISP Framework and Management Platform.

**Methods:**

- `__init__()`
- `async get_user_profile()`
- `async update_user_profile()`
- `async update_user_preferences()`
- `async upload_user_avatar()`
- `async remove_user_avatar()`
- `async update_contact_information()`
- `async search_profiles_by_criteria()`
- `async get_profile_completion_status()`
- `async _validate_profile_updates()`
- `async _validate_contact_info()`
- `async _validate_avatar()`
- `async _store_avatar()`
- `async _delete_avatar_file()`
- `async _record_profile_event()`
- `async _trigger_contact_verification()`

*Source: /home/dotmac_framework/src/dotmac_shared/user_management/core/profile_manager.py*

## dotmac_shared.user_management.core.user_lifecycle_service

Core User Lifecycle Management Service.

Provides comprehensive user lifecycle operations including registration, activation,
profile management, and deactivation. Works with platform adapters to provide
consistent user management across ISP Framework and Management Platform.

### Classes

#### UserLifecycleService

Core service for managing user lifecycle operations.

Provides unified user operations that work across all platforms through
adapter patterns while maintaining consistent behavior and security.

**Methods:**

- `__init__()`
- `async register_user()`
- `async activate_user()`
- `async update_user()`
- `async update_user_profile()`
- `async deactivate_user()`
- `async reactivate_user()`
- `async delete_user()`
- `async get_user()`
- `async get_user_by_username()`
- `async get_user_by_email()`
- `async search_users()`
- `async get_user_audit_trail()`
- `async _validate_user_registration()`
- `async _validate_email_uniqueness()`
- `async _user_to_response()`
- `async _log_lifecycle_event()`

*Source: /home/dotmac_framework/src/dotmac_shared/user_management/core/user_lifecycle_service.py*

## dotmac_shared.user_management.core.user_repository

User Repository for Unified User Management.

Provides database operations for user lifecycle management across platforms.
Implements the repository pattern for clean separation of data access logic.

### Classes

#### UserModel

Database model for unified user management.

**Methods:**

- `to_dict()`

#### UserLifecycleEventModel

Database model for user lifecycle events.

#### UserPasswordModel

Database model for user password management.

#### UserRepository

Repository for user database operations.

**Methods:**

- `__init__()`
- `async create_user()`
- `async get_user_by_id()`
- `async get_user_by_email()`
- `async get_user_by_username()`
- `async get_user_by_identifier()`
- `async update_user()`
- `async delete_user()`
- `async search_users()`
- `async activate_user()`
- `async deactivate_user()`
- `async create_lifecycle_event()`
- `async get_user_lifecycle_events()`
- `async store_user_password()`
- `async get_user_password_hash()`

*Source: /home/dotmac_framework/src/dotmac_shared/user_management/core/user_repository.py*

## dotmac_shared.user_management.integrations.__init__

Integration modules for unified user management service.

Provides seamless integration with authentication systems, external services,
and platform-specific components.

*Source: /home/dotmac_framework/src/dotmac_shared/user_management/integrations/__init__.py*

## dotmac_shared.user_management.schemas.lifecycle_schemas

User lifecycle schemas for registration, activation, and deactivation workflows.

Provides consistent data models for user lifecycle events across platforms.

### Classes

#### RegistrationSource

Sources of user registration.

#### VerificationType

Types of user verification.

#### DeactivationReason

Reasons for user deactivation.

#### UserRegistration

Schema for user registration requests.

**Methods:**

- `validate_username()`
- `validate_password()`

#### UserActivation

Schema for user activation requests.

#### UserDeactivation

Schema for user deactivation requests.

#### UserDeletion

Schema for user deletion requests.

#### UserLifecycleEvent

Schema for user lifecycle event tracking.

#### UserVerificationRequest

Schema for user verification requests.

#### UserApprovalRequest

Schema for user approval workflow.

#### UserApprovalResponse

Schema for user approval responses.

#### BulkUserOperation

Schema for bulk user operations.

#### BulkUserOperationResult

Schema for bulk user operation results.

#### Config

Pydantic configuration.

*Source: /home/dotmac_framework/src/dotmac_shared/user_management/schemas/lifecycle_schemas.py*

## dotmac_shared.user_management.schemas.user_schemas

Unified user schemas for cross-platform user management.

These schemas provide consistent data models across ISP Framework and
Management Platform while allowing for platform-specific extensions.

### Classes

#### UserType

Universal user types across all platforms.

#### UserStatus

User account status.

#### NotificationPreferences

User notification preferences.

#### UserPreferences

User preferences and settings.

#### ContactInformation

User contact information.

#### UserProfile

Extended user profile information.

#### UserBase

Base user model with common fields.

**Methods:**

- `validate_username()`
- `validate_names()`

#### UserCreate

Schema for creating new users.

**Methods:**

- `validate_password()`
- `validate_password_confirm()`

#### UserUpdate

Schema for updating existing users.

**Methods:**

- `validate_names()`

#### UserResponse

Schema for user response data.

#### UserSummary

Lightweight user summary for lists and references.

**Methods:**

- `full_name()`
- `display_name()`

#### UserSearchQuery

Schema for user search queries.

#### UserSearchResult

Schema for user search results.

**Methods:**

- `has_next_page()`
- `has_previous_page()`

#### Config

Pydantic configuration.

#### Config

Pydantic configuration.

*Source: /home/dotmac_framework/src/dotmac_shared/user_management/schemas/user_schemas.py*

## dotmac_shared.websockets.__init__

DotMac WebSocket Service Package

A comprehensive, production-ready WebSocket service for real-time communication
with multi-tenant support, horizontal scaling, and service integration.

Key Features:

- Multi-tenant WebSocket connection management
- Real-time event broadcasting and routing
- Horizontal scaling with Redis backend
- Service registry integration
- Cross-package integration support

*Source: /home/dotmac_framework/src/dotmac_shared/websockets/__init__.py*

## dotmac_shared.websockets.adapters.__init__

Platform adapters for WebSocket service.

*Source: /home/dotmac_framework/src/dotmac_shared/websockets/adapters/__init__.py*

## dotmac_shared.websockets.auth_integration

WebSocket Authentication Integration

Integrates WebSocket service with Developer B's authentication service
for secure WebSocket connections, session validation, and real-time permissions.

### Classes

#### TokenValidationResult

Token validation result structure.

#### WebSocketAuthContext

Authentication context for WebSocket connections.

**Methods:**

- `__post_init__()`

#### WebSocketAuthManager

WebSocket authentication manager integrating with Developer B's auth service.

Provides secure WebSocket authentication, session validation,
and real-time permission checking.

**Methods:**

- `__init__()`
- `async authenticate_websocket_connection()`
- `async check_message_permission()`
- `async disconnect_websocket()`
- `async get_user_connections()`
- `async disconnect_user_connections()`
- `async get_connection_context()`
- `async get_active_connections_stats()`
- `async _log_security_event()`

#### WebSocketAuthIntegrationFactory

Factory for creating WebSocket auth integration components.

**Methods:**

- `async create_websocket_auth_manager()`
- `async create_integrated_websocket_system()`

*Source: /home/dotmac_framework/src/dotmac_shared/websockets/auth_integration.py*

## dotmac_shared.websockets.cache_integration

WebSocket Cache Integration

Integrates WebSocket service with Developer A's cache service for
message persistence, connection state management, and real-time coordination.

### Classes

#### CachedMessage

Cached WebSocket message structure.

**Methods:**

- `__post_init__()`

#### ConnectionState

Cached WebSocket connection state.

**Methods:**

- `__post_init__()`

#### CacheServiceWebSocketStore

WebSocket message and connection state caching using Developer A's cache service.

Provides distributed message persistence, connection state management,
and real-time coordination across multiple WebSocket server instances.

**Methods:**

- `__init__()`
- `async store_message()`
- `async get_message()`
- `async update_message_status()`
- `async store_connection_state()`
- `async get_connection_state()`
- `async remove_connection_state()`
- `async get_user_connections()`
- `async join_room()`
- `async leave_room()`
- `async get_room_members()`
- `async get_server_connections()`
- `async get_pending_messages()`
- `async health_check()`
- `async get_stats()`
- `async _add_to_user_message_queue()`
- `async _update_user_connections_index()`
- `async _remove_from_user_connections_index()`
- `async _update_server_connections_index()`
- `async _remove_from_server_connections_index()`

#### WebSocketCacheIntegrationFactory

Factory for creating WebSocket cache integration components.

**Methods:**

- `async create_websocket_cache_store()`
- `async create_integrated_websocket_components()`

*Source: /home/dotmac_framework/src/dotmac_shared/websockets/cache_integration.py*

## dotmac_shared.websockets.core.__init__

Core WebSocket components.

*Source: /home/dotmac_framework/src/dotmac_shared/websockets/core/__init__.py*

## dotmac_shared.websockets.core.config

WebSocket Service Configuration Management

Environment-based configuration with validation and defaults for production deployments.

### Classes

#### LogLevel

Logging levels.

#### WebSocketConfig

WebSocket service configuration with environment variable support.

All settings can be overridden via environment variables with WEBSOCKET_ prefix.

**Methods:**

- `validate_max_connections()`
- `validate_heartbeat_interval()`
- `validate_redis_url()`
- `validate_cors_origins()`
- `is_production()`
- `is_development()`
- `to_dict()`
- `from_env()`
- `for_testing()`
- `for_production()`

*Source: /home/dotmac_framework/src/dotmac_shared/websockets/core/config.py*

## dotmac_shared.websockets.core.events

Real-time Event System

Advanced event management for WebSocket connections with filtering,
transformation, persistence, and replay capabilities.

### Classes

#### EventPriority

Event priority levels.

#### EventType

Common WebSocket event types.

#### EventFilter

Event filtering criteria.

**Methods:**

- `matches()`

#### WebSocketEvent

WebSocket event with comprehensive metadata and routing information.

**Methods:**

- `validate_event_type()`
- `validate_data()`
- `is_expired()`
- `can_retry()`
- `should_persist()`
- `to_message()`

#### EventSubscription

Event subscription for connections.

#### EventManager

Advanced event management system for WebSocket connections.

Features:

- Event filtering and routing
- Subscription management
- Event persistence and replay
- Delivery guarantees
- Event transformation
- Performance metrics

**Methods:**

- `__init__()`
- `async start()`
- `async stop()`
- `async subscribe()`
- `async unsubscribe()`
- `async publish_event()`
- `async replay_events()`
- `async add_event_handler()`
- `async remove_event_handler()`
- `get_metrics()`
- `async _find_matching_connections()`
- `async _deliver_event()`
- `async _persist_event()`
- `async _call_event_handlers()`
- `async _cleanup_expired_events()`

#### Config

*Source: /home/dotmac_framework/src/dotmac_shared/websockets/core/events.py*

## dotmac_shared.websockets.core.manager

WebSocket Connection Manager

High-performance WebSocket connection management with multi-tenant support,
heartbeat monitoring, and graceful connection lifecycle handling.

### Classes

#### ConnectionInfo

Information about a WebSocket connection.

#### MessageEnvelope

WebSocket message envelope for structured communication.

#### WebSocketManager

Production-ready WebSocket connection manager with advanced features.

Features:

- Multi-tenant connection isolation
- Heartbeat monitoring and auto-cleanup
- Room-based message routing
- Connection metadata and state management
- Graceful shutdown and connection migration
- Comprehensive metrics and monitoring

**Methods:**

- `__init__()`
- `async start()`
- `async stop()`
- `async connect()`
- `async disconnect()`
- `async send_message()`
- `async broadcast_to_room()`
- `async broadcast_to_tenant()`
- `async join_room()`
- `async leave_room()`
- `async get_room_connections()`
- `async update_heartbeat()`
- `get_connection_info()`
- `get_metrics()`
- `add_connection_hook()`
- `add_disconnection_hook()`
- `add_message_hook()`
- `async _send_system_message()`
- `async _heartbeat_monitor()`
- `async _connection_cleanup()`
- `async _close_all_connections()`

*Source: /home/dotmac_framework/src/dotmac_shared/websockets/core/manager.py*

## dotmac_shared.websockets.integration.__init__

Service integration components.

*Source: /home/dotmac_framework/src/dotmac_shared/websockets/integration/__init__.py*

## dotmac_shared.websockets.integration.service_factory

Unified Service Factory for All Shared Services

This is the master integration point that creates and coordinates all 4 shared service packages
with proper dependency injection, service registry integration, and production deployment support.

### Classes

#### ServiceType

Available shared service types.

#### ServiceConfig

Configuration for a specific service.

#### UnifiedServiceFactory

Master factory for creating and managing all 4 shared service packages.

This factory handles:

- Service dependency resolution and injection
- Service registry integration
- Health monitoring across all services
- Configuration management
- Graceful startup and shutdown
- Cross-service communication

**Methods:**

- `__init__()`
- `async initialize_all_services()`
- `async shutdown_all_services()`
- `async get_service()`
- `async get_cache_service()`
- `async get_auth_service()`
- `async get_file_service()`
- `async get_websocket_service()`
- `async get_unified_health()`
- `async get_unified_metrics()`
- `async _parse_service_configs()`
- `async _initialize_cache_service()`
- `async _initialize_auth_service()`
- `async _initialize_file_service()`
- `async _initialize_websocket_service()`
- `async _setup_cross_service_integrations()`
- `async _register_with_service_registry()`
- `async _start_health_monitoring()`
- `async _health_check_loop()`
- `async _create_mock_cache_service()`
- `async _create_mock_auth_service()`
- `async _create_mock_file_service()`

#### WebSocketServiceFactory

Factory for creating WebSocket service instances.

**Methods:**

- `async create_websocket_service()`

#### MockCacheService

**Methods:**

- `async start()`
- `async stop()`
- `async get()`
- `async set()`
- `async delete()`
- `async health_check()`
- `get_metrics()`

#### MockAuthService

**Methods:**

- `async start()`
- `async stop()`
- `async validate_token()`
- `async health_check()`
- `get_metrics()`

#### MockFileService

**Methods:**

- `async start()`
- `async stop()`
- `async generate_file()`
- `async health_check()`
- `get_metrics()`

*Source: /home/dotmac_framework/src/dotmac_shared/websockets/integration/service_factory.py*

## dotmac_shared.websockets.patterns.__init__

WebSocket pattern implementations.

*Source: /home/dotmac_framework/src/dotmac_shared/websockets/patterns/__init__.py*

## dotmac_shared.websockets.patterns.broadcasting

Advanced Broadcasting Management

High-performance message broadcasting with intelligent routing, filtering,
and delivery optimization for WebSocket connections.

### Classes

#### BroadcastType

Types of broadcast operations.

#### DeliveryMode

Message delivery modes.

#### BroadcastFilter

Filters for selective broadcasting.

#### BroadcastResult

Result of a broadcast operation.

#### BroadcastManager

Advanced broadcasting system for WebSocket connections.

Features:

- Intelligent message routing and filtering
- Delivery mode selection (best effort, reliable, guaranteed)
- Performance optimization with batching
- Broadcast analytics and monitoring
- Custom broadcast patterns
- Rate limiting and throttling

**Methods:**

- `__init__()`
- `async broadcast_to_all()`
- `async broadcast_to_tenant()`
- `async broadcast_to_users()`
- `async broadcast_to_rooms()`
- `async broadcast_filtered()`
- `async broadcast_priority()`
- `async schedule_broadcast()`
- `async add_broadcast_handler()`
- `async remove_broadcast_handler()`
- `get_broadcast_stats()`
- `async _execute_broadcast()`
- `async _get_target_connections()`
- `async _apply_filters()`
- `async _deliver_to_connections()`
- `async _reliable_delivery()`
- `async _guaranteed_delivery()`
- `async _check_rate_limit()`
- `async _call_broadcast_handlers()`

*Source: /home/dotmac_framework/src/dotmac_shared/websockets/patterns/broadcasting.py*

## dotmac_shared.websockets.patterns.rooms

Advanced Room Management System

Sophisticated room-based messaging with hierarchical rooms, permissions,
moderation capabilities, and advanced routing patterns.

### Classes

#### RoomType

Room types with different behavior.

#### MemberRole

Member roles within rooms.

#### RoomMember

Room member information.

#### Room

Room configuration and state.

**Methods:**

- `__post_init__()`

#### RoomManager

Advanced room management system for WebSocket connections.

Features:

- Hierarchical room structure
- Role-based permissions
- Room moderation and security
- Temporary and persistent rooms
- Room statistics and analytics
- Custom room events and hooks

**Methods:**

- `__init__()`
- `async start()`
- `async stop()`
- `async create_room()`
- `async delete_room()`
- `async join_room()`
- `async leave_room()`
- `async send_room_message()`
- `async change_member_role()`
- `get_room()`
- `get_user_rooms()`
- `get_tenant_rooms()`
- `get_room_stats()`
- `get_metrics()`
- `add_room_hook()`
- `remove_room_hook()`
- `async _call_room_hooks()`
- `async _cleanup_inactive_rooms()`

*Source: /home/dotmac_framework/src/dotmac_shared/websockets/patterns/rooms.py*

## dotmac_shared.websockets.scaling.__init__

WebSocket scaling components.

*Source: /home/dotmac_framework/src/dotmac_shared/websockets/scaling/__init__.py*

## dotmac_shared.websockets.scaling.redis_backend

Redis WebSocket Backend for Horizontal Scaling

Production-ready Redis backend for WebSocket scaling across multiple instances
with message broadcasting, connection state sharing, and cluster coordination.

### Classes

#### RedisWebSocketBackend

Redis-based WebSocket backend for horizontal scaling.

Features:

- Cross-instance message broadcasting
- Distributed connection state management
- Cluster coordination and health monitoring
- Message persistence and replay
- Connection migration support
- Comprehensive metrics and monitoring

**Methods:**

- `__init__()`
- `async start()`
- `async stop()`
- `async publish_message()`
- `async broadcast_event()`
- `async notify_connection_event()`
- `async store_message()`
- `async get_message()`
- `async get_connection_count()`
- `async get_instance_info()`
- `async add_message_handler()`
- `async remove_message_handler()`
- `get_metrics()`
- `async _subscribe_to_channels()`
- `async _register_instance()`
- `async _unregister_instance()`
- `async _heartbeat_loop()`
- `async _message_listener()`
- `async _handle_redis_message()`
- `async _cleanup_loop()`

*Source: /home/dotmac_framework/src/dotmac_shared/websockets/scaling/redis_backend.py*

## dotmac_shared.websockets.validate_integration

Simple validation for WebSocket service integration.

Validates that WebSocket integration components can be imported
and basic functionality works.

*Source: /home/dotmac_framework/src/dotmac_shared/websockets/validate_integration.py*
