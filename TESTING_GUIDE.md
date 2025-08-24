# Testing Guide

**AI-first testing methodology for the DotMac Platform**

## 🎯 Testing Philosophy

This platform uses **AI-first testing** - focusing on business outcomes rather than traditional code coverage metrics.

## 🚀 Quick Start

```bash
# Setup test environment
make install-dev
docker-compose -f docker-compose.test.yml up -d

# Run all tests
make test

# AI-first testing (recommended)
make test-ai-first
```

## 📊 Test Types

### Primary (AI-Generated)
- **Property-based tests** (40%) - AI generates thousands of test cases
- **Behavior tests** (30%) - Tests business outcomes
- **Contract tests** (20%) - API schema validation
- **Smoke tests** (10%) - Revenue-critical paths only

### Traditional (Optional)
- Unit tests - Use only for critical business logic
- Integration tests - AI can generate better versions

## 🔧 Commands

```bash
# AI-first testing
make test-ai-first           # Primary test suite
make test-property-based     # Property-based testing
make test-contracts          # API contract validation
make test-behaviors          # Business outcome testing

# Traditional testing
make test-unit               # Unit tests
make test-integration        # Integration tests
make test-e2e               # End-to-end tests

# Platform-specific
cd isp-framework && make test
cd management-platform && make test
cd frontend && pnpm test
```

## ✅ Test Markers

Use pytest markers to categorize tests:

```python
@pytest.mark.property_based   # AI-generated test cases
@pytest.mark.behavior        # Business outcome tests
@pytest.mark.contract        # API/Service contracts
@pytest.mark.smoke_critical  # Revenue-critical only
@pytest.mark.e2e            # Full workflow tests
```

## 🎯 Business-Critical Gates

**Always enforced:**
- Business logic correctness (billing/revenue)
- Security patterns validation
- API contract compliance
- Performance baselines

**Optional (human convenience):**
- Code formatting
- Complexity limits
- Traditional coverage metrics

## 🔍 Test Structure

```
tests/
├── property_based/     # AI-generated test cases
├── behaviors/          # Business outcome tests
├── contracts/          # API schema validation
├── smoke/             # Critical path tests
└── unit/              # Traditional unit tests (minimal)
```

## 📈 Quality Metrics

Focus on:
- ✅ Business outcome coverage
- ✅ Property-based test coverage
- ✅ Contract compliance rate
- ✅ Critical path success rate

Ignore:
- ❌ Line coverage percentages
- ❌ Code complexity metrics
- ❌ Style/formatting scores

## 🚨 Running Tests in CI

```bash
# Fast feedback (primary)
make ai-safety-check         # Security validation
make test-ai-first          # AI-generated tests

# Optional traditional checks
make lint-optional          # Code formatting
make type-check-optional    # Type validation
```

## 💡 Writing Tests

### Property-Based Test Example
```python
@pytest.mark.property_based
@given(amount=st.decimals(min_value=0, max_value=10000))
def test_billing_calculation_properties(amount):
    """AI-generated property: billing calculations are always positive"""
    result = calculate_bill(amount)
    assert result >= 0
    assert result.is_finite()
```

### Behavior Test Example
```python
@pytest.mark.behavior
def test_customer_can_pay_bill():
    """Business outcome: customers can successfully pay their bills"""
    customer = create_test_customer()
    bill = generate_bill(customer)
    
    result = process_payment(customer, bill.amount)
    
    assert result.status == PaymentStatus.SUCCESS
    assert customer.balance == 0
```

## 🔧 Troubleshooting

**Tests failing?**
```bash
make test-debug          # Run with detailed output
make db-reset-test       # Reset test database
```

**Database issues?**
```bash
docker-compose -f docker-compose.test.yml restart postgres-test
```

**Need more info?** Check the [Developer Guide](DEVELOPER_GUIDE.md) for detailed setup instructions.

---

**Philosophy**: Focus on business outcomes, not code aesthetics. AI handles complexity better than traditional testing approaches.