"""
Contract Testing Framework for AI-First Development

Validates API contracts, service interfaces, and data schemas
automatically using AI-generated test cases.
"""

import pytest
import requests
import jsonschema
from typing import Dict, Any, List, Optional, Callable
from functools import wraps
import json
from pathlib import Path


class ContractValidator:
    """
    AI-powered contract validator that automatically tests API contracts,
    service interfaces, and data schemas.
    """
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.schemas_cache: Dict[str, Dict] = {}
    
    def load_schema(self, schema_name: str) -> Dict[str, Any]:
        """Load JSON schema for contract validation."""
        if schema_name in self.schemas_cache:
            return self.schemas_cache[schema_name]
        
        schema_path = Path(f"schemas/{schema_name}.json")
        if schema_path.exists():
            with open(schema_path, 'r') as f:
                schema = json.load(f)
                self.schemas_cache[schema_name] = schema
                return schema
        
        # Generate basic schema if not found
        return self._generate_basic_schema(schema_name)
    
    def _generate_basic_schema(self, schema_name: str) -> Dict[str, Any]:
        """Generate basic JSON schema for common entities."""
        schemas = {
            "customer": {
                "type": "object",
                "required": ["id", "customer_number", "display_name"],
                "properties": {
                    "id": {"type": "string", "format": "uuid"},
                    "customer_number": {"type": "string", "pattern": "^CUS-[A-Z0-9]{6}$"},
                    "display_name": {"type": "string", "minLength": 2, "maxLength": 100},
                    "email": {"type": "string", "format": "email"},
                    "phone": {"type": "string", "pattern": "^\\+1-\\d{3}-\\d{3}-\\d{4}$"},
                    "status": {"type": "string", "enum": ["active", "suspended", "cancelled"]},
                    "created_at": {"type": "string", "format": "date-time"},
                    "updated_at": {"type": "string", "format": "date-time"}
                }
            },
            "service": {
                "type": "object",
                "required": ["id", "service_type", "customer_id", "monthly_cost"],
                "properties": {
                    "id": {"type": "string", "format": "uuid"},
                    "service_type": {"type": "string", "enum": ["internet", "phone", "tv", "bundle"]},
                    "customer_id": {"type": "string", "format": "uuid"},
                    "monthly_cost": {"type": "number", "minimum": 0},
                    "bandwidth_mbps": {"type": "integer", "minimum": 1},
                    "status": {"type": "string", "enum": ["active", "suspended", "cancelled"]}
                }
            },
            "invoice": {
                "type": "object",
                "required": ["id", "customer_id", "amount", "due_date"],
                "properties": {
                    "id": {"type": "string", "format": "uuid"},
                    "customer_id": {"type": "string", "format": "uuid"},
                    "amount": {"type": "number", "minimum": 0},
                    "tax_amount": {"type": "number", "minimum": 0},
                    "total_amount": {"type": "number", "minimum": 0},
                    "due_date": {"type": "string", "format": "date"},
                    "status": {"type": "string", "enum": ["draft", "sent", "paid", "overdue", "cancelled"]}
                }
            }
        }
        
        return schemas.get(schema_name, {"type": "object"})
    
    def validate_response_schema(self, response: requests.Response, schema_name: str) -> bool:
        """Validate API response against schema."""
        try:
            data = response.json()
            schema = self.load_schema(schema_name)
            jsonschema.validate(data, schema)
            return True
        except (jsonschema.ValidationError, json.JSONDecodeError) as e:
            pytest.fail(f"Contract validation failed for {schema_name}: {e}")
    
    def validate_request_schema(self, request_data: Dict[str, Any], schema_name: str) -> bool:
        """Validate API request against schema."""
        try:
            schema = self.load_schema(f"{schema_name}_request")
            jsonschema.validate(request_data, schema)
            return True
        except jsonschema.ValidationError as e:
            pytest.fail(f"Request contract validation failed for {schema_name}: {e}")


def contract_test(
    endpoint: str,
    method: str = "GET",
    schema_name: Optional[str] = None,
    status_code: int = 200,
    auth_required: bool = True
):
    """
    Decorator for contract-based API tests.
    
    Example:
        @contract_test("/api/customers", "POST", "customer", 201)
        @pytest.mark.contract
        def test_create_customer_contract(validator, test_data):
            response = requests.post(validator.base_url + "/api/customers", json=test_data)
            validator.validate_response_schema(response, "customer")
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            validator = ContractValidator()
            return func(validator, *args, **kwargs)
        
        wrapper.pytestmark = pytest.mark.contract
        return wrapper
    return decorator


# Contract test examples

@contract_test("/api/customers", "GET", "customer")
@pytest.mark.contract
@pytest.mark.revenue_critical
def contract_test_get_customers(validator):
    """Contract test: GET /api/customers should return valid customer schema."""
    response = requests.get(f"{validator.base_url}/api/customers")
    
    # Contract: Should return 200 OK
    assert response.status_code == 200
    
    # Contract: Response should be valid JSON
    data = response.json()
    assert isinstance(data, (list, dict))
    
    # Contract: If list, each item should match customer schema
    if isinstance(data, list) and data:
        for customer in data:
            validator.validate_response_schema(
                type('MockResponse', (), {'json': lambda: customer})(),
                "customer"
            )


@contract_test("/api/customers", "POST", "customer", 201)
@pytest.mark.contract
@pytest.mark.revenue_critical
def contract_test_create_customer(validator):
    """Contract test: POST /api/customers should accept valid customer data."""
    customer_data = {
        "customer_number": "CUS-TEST01",
        "display_name": "Test Customer",
        "email": "test@example.com",
        "phone": "+1-555-123-4567"
    }
    
    # Contract: Should validate request data
    validator.validate_request_schema(customer_data, "customer")
    
    # Contract: Should return 201 Created with valid customer response
    response = requests.post(
        f"{validator.base_url}/api/customers",
        json=customer_data
    )
    
    assert response.status_code == 201
    validator.validate_response_schema(response, "customer")
    
    # Contract: Response should include generated fields
    created_customer = response.json()
    assert "id" in created_customer
    assert "created_at" in created_customer
    assert "updated_at" in created_customer


@contract_test("/api/billing/invoices", "POST", "invoice", 201)
@pytest.mark.contract
@pytest.mark.billing_core
def contract_test_create_invoice(validator):
    """Contract test: POST /api/billing/invoices should create valid invoice."""
    # First create a customer (dependency)
    customer_response = requests.post(
        f"{validator.base_url}/api/customers",
        json={
            "customer_number": "CUS-INV001",
            "display_name": "Invoice Test Customer",
            "email": "invoice@example.com"
        }
    )
    customer = customer_response.json()
    
    invoice_data = {
        "customer_id": customer["id"],
        "amount": 99.99,
        "tax_amount": 8.00,
        "total_amount": 107.99,
        "due_date": "2024-02-01"
    }
    
    # Contract: Should create invoice with proper structure
    response = requests.post(
        f"{validator.base_url}/api/billing/invoices",
        json=invoice_data
    )
    
    assert response.status_code == 201
    validator.validate_response_schema(response, "invoice")
    
    # Contract: Invoice amounts should be consistent
    invoice = response.json()
    assert invoice["total_amount"] == invoice["amount"] + invoice["tax_amount"]


@pytest.mark.contract
@pytest.mark.data_safety
def contract_test_api_error_responses():
    """Contract test: API should return consistent error response format."""
    validator = ContractValidator()
    
    # Test various error conditions
    error_tests = [
        ("/api/customers/invalid-uuid", 404),
        ("/api/nonexistent-endpoint", 404),
        ("/api/customers", 401),  # No auth
    ]
    
    for endpoint, expected_status in error_tests:
        response = requests.get(f"{validator.base_url}{endpoint}")
        assert response.status_code == expected_status
        
        # Contract: Error responses should have consistent structure
        if response.headers.get('content-type', '').startswith('application/json'):
            error_data = response.json()
            assert "error" in error_data
            assert "message" in error_data
            assert isinstance(error_data["message"], str)


@pytest.mark.contract
@pytest.mark.performance_baseline
def contract_test_api_response_times():
    """Contract test: API endpoints should meet performance contracts."""
    validator = ContractValidator()
    
    # Performance contracts for different endpoints
    performance_contracts = [
        ("/api/customers", 500),  # 500ms max
        ("/api/health", 100),     # 100ms max  
        ("/api/billing/invoices", 1000),  # 1s max
    ]
    
    for endpoint, max_response_time_ms in performance_contracts:
        import time
        
        start_time = time.time()
        response = requests.get(f"{validator.base_url}{endpoint}")
        end_time = time.time()
        
        response_time_ms = (end_time - start_time) * 1000
        
        # Performance contract: Response time within limits
        assert response_time_ms < max_response_time_ms, \
            f"{endpoint} took {response_time_ms:.2f}ms, exceeds contract of {max_response_time_ms}ms"


@pytest.mark.contract
@pytest.mark.business_logic_protection
def contract_test_business_rule_enforcement():
    """Contract test: API should enforce business rules consistently."""
    validator = ContractValidator()
    
    # Business rule: Customer numbers must be unique
    customer_data = {
        "customer_number": "CUS-UNIQUE",
        "display_name": "Unique Test",
        "email": "unique@example.com"
    }
    
    # Create first customer
    response1 = requests.post(
        f"{validator.base_url}/api/customers",
        json=customer_data
    )
    assert response1.status_code == 201
    
    # Try to create duplicate customer number
    response2 = requests.post(
        f"{validator.base_url}/api/customers",
        json=customer_data
    )
    
    # Contract: Should reject duplicate customer numbers
    assert response2.status_code == 400
    error_data = response2.json()
    assert "customer_number" in error_data["error"].lower()
    assert "unique" in error_data["error"].lower() or "duplicate" in error_data["error"].lower()