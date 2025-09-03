# DotMac Business Logic Framework

A comprehensive business logic framework providing policy-as-code, idempotency management, and saga orchestration for the DotMac platform.

## Overview

The business logic framework implements three core patterns:

1. **Policy-as-Code**: Declarative business rules with versioning and consistent evaluation
2. **Idempotency**: Safe operation retries without side effects across distributed services  
3. **Sagas**: Distributed transaction management with compensation patterns

## Architecture

```
dotmac_shared/business_logic/
├── __init__.py                    # Main module exports
├── exceptions.py                  # Structured exception hierarchy
├── policies.py                    # Core policy framework
├── idempotency.py                # Idempotent operation management
├── sagas.py                      # Saga orchestration framework
├── policies/                     # Domain-specific policies
│   ├── __init__.py
│   ├── plan_eligibility.py       # Service plan eligibility rules
│   └── commission_rules.py       # Partner commission validation
├── operations/                   # Business operation implementations
│   ├── __init__.py
│   ├── tenant_provisioning.py    # Tenant creation with sagas
│   ├── service_provisioning.py   # Service activation workflows
│   └── billing_runs.py          # Monthly billing processing
└── tests/                        # Validation and integration tests
    ├── test_business_logic_integration.py
    └── validate_structure.py
```

## Key Features

### Policy-as-Code Framework

- **Declarative Rules**: Define business rules using operators and field paths
- **Versioning**: Track policy changes with semantic versioning
- **Weighted Evaluation**: Rules can have different priorities and weights
- **Context Aware**: Policies evaluate within tenant and operational context
- **Rule Registry**: Centralized management of business policies

### Idempotency Management

- **Operation Keys**: Deterministic keys based on operation type and data
- **State Tracking**: Database persistence of operation status and results
- **Automatic Retries**: Configurable retry logic with exponential backoff
- **Result Caching**: Return cached results for completed operations
- **TTL Management**: Automatic cleanup of expired operations

### Saga Orchestration

- **Step Definition**: Individual saga steps with execute/compensate methods
- **Sequential Execution**: Ordered step processing with context passing
- **Compensation Handling**: Automatic rollback of completed steps on failure
- **Timeout Management**: Configurable timeouts for steps and entire sagas
- **State Persistence**: Database tracking of saga execution progress

## Usage Examples

### Policy Evaluation

```python
from dotmac_shared.business_logic import PolicyEngine, PolicyContext
from dotmac_shared.business_logic.policies import PlanEligibilityEngine

# Create policy engine
engine = PlanEligibilityEngine()

# Set up evaluation context
context = PolicyContext(
    tenant_id="tenant123",
    user_id="user456", 
    operation="plan_eligibility_check"
)

# Check customer eligibility for residential plan
customer_data = {
    "id": "cust789",
    "customer_type": "residential",
    "credit_score": 650,
    "outstanding_balance": 0.0,
    "location": {"service_coverage": True}
}

result = engine.check_plan_eligibility(
    plan_type="residential_basic",
    customer_data=customer_data,
    context=context
)

print(f"Eligible: {result['eligible']}")
print(f"Policy Result: {result['policy_result']}")
```

### Idempotent Operations

```python
from dotmac_shared.business_logic import IdempotencyKey, IdempotencyManager
from dotmac_shared.business_logic.operations import TenantProvisioningOperation

# Generate idempotency key
key = IdempotencyKey.generate(
    operation_type="tenant_provisioning",
    tenant_id="tenant123",
    operation_data={
        "name": "New Tenant",
        "domain": "new-tenant", 
        "plan": "basic",
        "admin_email": "admin@newtenant.com"
    }
)

# Execute idempotent operation
operation = TenantProvisioningOperation()
manager = IdempotencyManager(db_session_factory)

result = await manager.execute_idempotent(
    idempotency_key=key,
    operation_data=operation_data,
    context={"user_id": "user123"}
)

print(f"Success: {result.success}")
print(f"Tenant ID: {result.data['tenant_id']}")
```

### Saga Orchestration

```python
from dotmac_shared.business_logic.sagas import SagaCoordinator, SagaContext
from dotmac_shared.business_logic.operations import ServiceProvisioningSaga

# Create saga coordinator
coordinator = SagaCoordinator(db_session_factory)

# Register saga definition
saga_definition = ServiceProvisioningSaga.create_definition()
coordinator.register_saga(saga_definition)

# Create saga context
context = SagaContext(
    saga_id=str(uuid4()),
    tenant_id="tenant123",
    user_id="user456"
)

# Execute saga
result = await coordinator.execute_saga(
    saga_name="service_provisioning",
    context=context,
    initial_data={
        "customer_id": "cust789",
        "service_type": "internet",
        "plan": "standard",
        "billing_period": "monthly"
    }
)

print(f"Status: {result['status']}")
print(f"Service ID: {result['step_results']['activate_service']['service_id']}")
```

## Business Rules Implemented

### Plan Eligibility Policies

- **Residential Basic**: Credit score ≥600, no outstanding debt, service coverage
- **Business Pro**: Valid business registration, 12-month commitment, $1K credit limit
- **Enterprise**: 50+ employees, $1M+ revenue, signed SLA, dedicated account manager

### Commission Rules

- **Partner Eligibility**: Active status, signed agreement, compliance, performance ≥70%
- **Rate Validation**: Commission rates 0-50%, minimum $50 payout, maximum $10K per transaction
- **Tier Advancement**: Revenue thresholds, customer count, performance scores, certifications
- **Clawback Conditions**: 90-day cancellations, quality issues, chargebacks, fraud detection

### Licensing Constraints  

- **Usage Limits**: Users, bandwidth, storage within licensed capacity
- **Feature Access**: Premium features require appropriate license tier
- **API Limits**: Rate limiting based on license tier
- **Compliance**: Active license with valid expiration date

## Operations

### Tenant Provisioning Saga

1. **Create Tenant**: Database record creation
2. **Configure Database**: Schema setup and initialization  
3. **Setup Defaults**: Default settings based on plan
4. **Activate Tenant**: Make tenant available for use

### Service Provisioning Saga

1. **Validate Request**: Customer eligibility and plan validation
2. **Allocate Resources**: Reserve resources based on service type
3. **Configure Service**: Network and billing configuration
4. **Activate Service**: Enable service and create billing account
5. **Notify Customer**: Send activation confirmation

### Billing Run Saga

1. **Validate Period**: Check billing period and prerequisites
2. **Generate Invoices**: Create invoices for all eligible customers
3. **Process Payments**: Charge payment methods and handle failures
4. **Send Notifications**: Email confirmations and failure notices
5. **Finalize Billing**: Update billing run status and prepare reports

## Error Handling

### Structured Exceptions

- **BusinessLogicError**: Base exception with context and severity
- **PolicyViolationError**: Policy rule violations with failed rule details
- **IdempotencyError**: Operation conflicts and retry failures
- **SagaError**: Orchestration failures with compensation status
- **ProvisioningError**: Service/tenant provisioning failures
- **BillingRunError**: Billing process failures with customer impact

### Error Context

All exceptions include:
- Operation type and resource identification
- Tenant and user context
- Correlation IDs for distributed tracing
- Metadata for debugging and auditing

## Integration

### Standard Exception Handler

Use the `@standard_exception_handler` decorator for consistent error handling:

```python
from dotmac_shared.standard_exception_handler import standard_exception_handler

@standard_exception_handler
async def business_operation():
    # Your business logic here
    pass
```

### Database Models

The framework includes SQLAlchemy models for:
- Idempotent operation tracking
- Saga execution state
- Step execution details
- Commission configurations

### Monitoring and Observability

- Structured logging with tenant and correlation context
- Performance metrics for policy evaluation
- Success/failure rates for idempotent operations  
- Saga completion and compensation statistics

## Testing

Run validation tests:

```bash
cd src/dotmac_shared/business_logic
python3 tests/validate_structure.py
```

The test suite validates:
- File structure and imports
- Policy rule evaluation
- Idempotency key generation
- Saga orchestration components
- Business rule implementations
- Error handling structures

## Best Practices

1. **Policy Design**:
   - Keep rules atomic and focused
   - Use descriptive rule names and error messages
   - Version policies when making breaking changes
   - Test policies with various data scenarios

2. **Idempotent Operations**:
   - Generate keys from operation type + tenant + data
   - Keep operation data immutable during execution
   - Set appropriate TTL for operation caching
   - Handle partial failures gracefully

3. **Saga Implementation**:
   - Design compensating actions for each step
   - Keep step operations idempotent
   - Use timeouts to prevent hanging sagas
   - Log step execution for debugging

4. **Error Handling**:
   - Provide actionable error messages
   - Include relevant context for debugging
   - Use appropriate error severity levels
   - Implement proper retry and backoff strategies

## Performance Considerations

- Policy evaluation is optimized for sub-millisecond response times
- Idempotency keys are indexed for fast lookup
- Saga state is persisted efficiently with minimal database calls
- Commission calculations support batch processing for large datasets

The framework is designed to handle high-throughput operations while maintaining consistency and reliability across the distributed DotMac platform.