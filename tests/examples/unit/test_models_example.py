"""
Example unit tests for Pydantic models and data structures.

This demonstrates best practices for testing:
- Model validation
- Data serialization/deserialization  
- Edge cases and error conditions
- Pydantic v2 features
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import uuid4

import pytest
from pydantic import BaseModel, Field, ValidationError, validator, ConfigDict
from pydantic.networks import EmailStr


# Example models for testing
class CustomerStatus(str, Enum):
    """Customer status enumeration."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


class Address(BaseModel):
    """Address model with validation."""
    street: str = Field(..., min_length=1, max_length=255)
    city: str = Field(..., min_length=1, max_length=100)
    state: str = Field(..., min_length=2, max_length=2)
    zip_code: str = Field(..., pattern=r"^\d{5}(-\d{4})?$")
    country: str = Field(default="US", min_length=2, max_length=2)


class Customer(BaseModel):
    """Customer model with comprehensive validation."""
    id: Optional[str] = Field(default_factory=lambda: str(uuid4())
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    phone: Optional[str] = Field(None, pattern=r"^\+?1?[0-9]{10}$")
    address: Optional[Address] = None
    status: CustomerStatus = CustomerStatus.ACTIVE
    balance: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc)
    tenant_id: str = Field(..., min_length=1)

    @validator('email')
    def validate_email_domain(cls, v):
        """Validate email domain is not from disposable email services."""
        disposable_domains = ['10minutemail.com', 'tempmail.org']
        domain = v.split('@')[1].lower()
        if domain in disposable_domains:
            raise ValueError('Disposable email addresses are not allowed')
        return v

    @validator('phone', pre=True)
    def clean_phone(cls, v):
        """Clean phone number by removing non-numeric characters."""
        if v:
            return ''.join(filter(str.isdigit, v)[-10:]  # Last 10 digits
        return v

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        }
    )

# Test fixtures
@pytest.fixture
def valid_customer_data():
    """Valid customer data for testing."""
    return {
        "email": "john.doe@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "phone": "5551234567",
        "tenant_id": "test-tenant-1"
    }


@pytest.fixture
def valid_address_data():
    """Valid address data for testing."""
    return {
        "street": "123 Main St",
        "city": "Anytown",
        "state": "CA",
        "zip_code": "12345"
    }


@pytest.fixture
def customer_with_address(valid_customer_data, valid_address_data):
    """Customer with address for testing."""
    data = valid_customer_data.copy()
    data["address"] = valid_address_data
    return Customer(**data)


# Unit tests
@pytest.mark.unit
@pytest.mark.fast
class TestAddressModel:
    """Test cases for Address model."""
    
    def test_valid_address_creation(self, valid_address_data):
        """Test creating a valid address."""
        address = Address(**valid_address_data)
        
        assert address.street == "123 Main St"
        assert address.city == "Anytown"
        assert address.state == "CA"
        assert address.zip_code == "12345"
        assert address.country == "US"  # Default value

    def test_address_with_extended_zip(self, valid_address_data):
        """Test address with extended ZIP code."""
        valid_address_data["zip_code"] = "12345-6789"
        address = Address(**valid_address_data)
        
        assert address.zip_code == "12345-6789"

    def test_invalid_zip_code(self, valid_address_data):
        """Test address with invalid ZIP code."""
        valid_address_data["zip_code"] = "invalid"
        
        with pytest.raises(ValidationError) as exc_info:
            Address(**valid_address_data)
        
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["field"] == "zip_code"
        assert "regex" in errors[0]["type"]

    def test_empty_street_validation(self, valid_address_data):
        """Test validation of empty street."""
        valid_address_data["street"] = ""
        
        with pytest.raises(ValidationError) as exc_info:
            Address(**valid_address_data)
        
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["field"] == "street"

    def test_address_serialization(self, valid_address_data):
        """Test address JSON serialization."""
        address = Address(**valid_address_data)
        json_data = address.dict()
        
        expected_fields = {"street", "city", "state", "zip_code", "country"}
        assert set(json_data.keys() == expected_fields
        
        # Test round-trip serialization
        recreated = Address(**json_data)
        assert recreated == address


@pytest.mark.unit
@pytest.mark.fast
class TestCustomerModel:
    """Test cases for Customer model."""
    
    def test_valid_customer_creation(self, valid_customer_data):
        """Test creating a valid customer."""
        customer = Customer(**valid_customer_data)
        
        assert customer.email == "john.doe@example.com"
        assert customer.first_name == "John"
        assert customer.last_name == "Doe"
        assert customer.phone == "5551234567"
        assert customer.status == CustomerStatus.ACTIVE
        assert customer.balance == Decimal("0.00")
        assert customer.tenant_id == "test-tenant-1"
        assert customer.id is not None
        assert isinstance(customer.created_at, datetime)

    def test_customer_with_address(self, customer_with_address):
        """Test customer with address."""
        assert customer_with_address.address is not None
        assert customer_with_address.address.street == "123 Main St"

    def test_phone_number_cleaning(self, valid_customer_data):
        """Test phone number cleaning."""
        test_cases = [
            ("(555) 123-4567", "5551234567"),
            ("+1-555-123-4567", "5551234567"), 
            ("555.123.4567", "5551234567"),
            ("15551234567", "5551234567"),  # 11 digits, take last 10
        ]
        
        for input_phone, expected_phone in test_cases:
            data = valid_customer_data.copy()
            data["phone"] = input_phone
            customer = Customer(**data)
            assert customer.phone == expected_phone

    def test_invalid_email_domain(self, valid_customer_data):
        """Test rejection of disposable email domains."""
        valid_customer_data["email"] = "test@10minutemail.com"
        
        with pytest.raises(ValidationError) as exc_info:
            Customer(**valid_customer_data)
        
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "Disposable email addresses" in str(errors[0]["msg"])

    def test_invalid_phone_format(self, valid_customer_data):
        """Test invalid phone number format."""
        valid_customer_data["phone"] = "123"  # Too short
        
        with pytest.raises(ValidationError) as exc_info:
            Customer(**valid_customer_data)
        
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["field"] == "phone"

    def test_negative_balance_validation(self, valid_customer_data):
        """Test negative balance validation."""
        valid_customer_data["balance"] = Decimal("-10.00")
        
        with pytest.raises(ValidationError) as exc_info:
            Customer(**valid_customer_data)
        
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["field"] == "balance"

    def test_customer_status_enum(self, valid_customer_data):
        """Test customer status enumeration."""
        for status in CustomerStatus:
            data = valid_customer_data.copy()
            data["status"] = status
            customer = Customer(**data)
            assert customer.status == status

    def test_invalid_customer_status(self, valid_customer_data):
        """Test invalid customer status."""
        valid_customer_data["status"] = "invalid_status"
        
        with pytest.raises(ValidationError) as exc_info:
            Customer(**valid_customer_data)
        
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["field"] == "status"

    def test_json_serialization(self, customer_with_address):
        """Test JSON serialization with custom encoders."""
        json_data = customer_with_address.json()
        assert isinstance(json_data, str)
        
        # Parse back to verify structure
        import json
        parsed = json.loads(json_data)
        
        # Check datetime serialization
        assert "T" in parsed["created_at"]  # ISO format
        assert parsed["balance"] == "0.00"  # Decimal as string

    def test_model_update(self, customer_with_address):
        """Test model updates."""
        updated_data = {
            "first_name": "Jane",
            "status": CustomerStatus.SUSPENDED
        }
        
        updated_customer = customer_with_address.copy(update=updated_data)
        
        assert updated_customer.first_name == "Jane"
        assert updated_customer.status == CustomerStatus.SUSPENDED
        assert updated_customer.last_name == customer_with_address.last_name  # Unchanged
        assert updated_customer.id == customer_with_address.id  # Should be same

    def test_dict_conversion(self, customer_with_address):
        """Test conversion to dictionary."""
        customer_dict = customer_with_address.dict()
        
        # Verify all fields are present
        expected_fields = {
            "id", "email", "first_name", "last_name", "phone", 
            "address", "status", "balance", "created_at", "tenant_id"
        }
        assert set(customer_dict.keys() == expected_fields
        
        # Verify nested address is also a dict
        assert isinstance(customer_dict["address"], dict)

    def test_model_validation_error_details(self):
        """Test detailed validation error information."""
        with pytest.raises(ValidationError) as exc_info:
            Customer(
                email="invalid-email",
                first_name="",  # Too short
                last_name="Valid",
                tenant_id=""  # Too short
            )
        
        errors = exc_info.value.errors()
        assert len(errors) >= 3  # Multiple validation errors
        
        # Check specific error types
        error_fields = {error["field"] for error in errors}
        assert "email" in error_fields
        assert "first_name" in error_fields
        assert "tenant_id" in error_fields


@pytest.mark.unit
@pytest.mark.fast  
class TestModelPerformance:
    """Performance tests for model operations."""
    
    def test_model_creation_performance(self, valid_customer_data, benchmark):
        """Benchmark model creation performance."""
        def create_customer():
            return Customer(**valid_customer_data)
        
        result = benchmark(create_customer)
        assert isinstance(result, Customer)

    def test_model_serialization_performance(self, customer_with_address, benchmark):
        """Benchmark model serialization performance."""
        def serialize_customer():
            return customer_with_address.json()
        
        result = benchmark(serialize_customer)
        assert isinstance(result, str)

    def test_model_validation_performance(self, valid_customer_data, benchmark):
        """Benchmark validation performance."""
        def validate_customer():
            # Force re-validation
            return Customer.parse_obj(valid_customer_data)
        
        result = benchmark(validate_customer)
        assert isinstance(result, Customer)


# Parameterized tests
@pytest.mark.unit
@pytest.mark.parametrize("status", list(CustomerStatus)
def test_all_customer_statuses(valid_customer_data, status):
    """Test all customer status values."""
    valid_customer_data["status"] = status
    customer = Customer(**valid_customer_data)
    assert customer.status == status


@pytest.mark.unit
@pytest.mark.parametrize("zip_code,should_pass", [
    ("12345", True),
    ("12345-6789", True), 
    ("1234", False),
    ("123456", False),
    ("abcde", False),
    ("12345-", False),
    ("12345-67890", False),
])
def test_zip_code_validation(valid_address_data, zip_code, should_pass):
    """Test ZIP code validation with various inputs."""
    valid_address_data["zip_code"] = zip_code
    
    if should_pass:
        address = Address(**valid_address_data)
        assert address.zip_code == zip_code
    else:
        with pytest.raises(ValidationError):
            Address(**valid_address_data)


# Property-based testing example (requires hypothesis)
try:
    from hypothesis import given, strategies as st
    
    @pytest.mark.unit
    @pytest.mark.slow  # Property-based tests can be slower
    @given(
        email=st.emails(),
        first_name=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'),
        last_name=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'),
        tenant_id=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', '-')
    )
    def test_customer_creation_property_based(email, first_name, last_name, tenant_id):
        """Property-based test for customer creation."""
        try:
            customer = Customer(
                email=email,
                first_name=first_name,
                last_name=last_name,
                tenant_id=tenant_id
            )
            
            # Properties that should always hold
            assert customer.email == email
            assert customer.first_name == first_name
            assert customer.last_name == last_name
            assert customer.tenant_id == tenant_id
            assert customer.status == CustomerStatus.ACTIVE
            assert customer.balance >= Decimal("0.00")
            
        except ValidationError:
            # Some generated values may not pass validation - that's expected
            pass

except ImportError:
    # hypothesis not available, skip property-based tests
    pass