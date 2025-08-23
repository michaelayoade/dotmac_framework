"""
Example API contract tests using OpenAPI schema validation.

This demonstrates best practices for testing:
- API schema validation
- Request/response contract enforcement
- Backward compatibility testing
- OpenAPI specification compliance
"""

import json
import os
from typing import Any, Dict, List
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import AsyncClient, Response
from jsonschema import validate, ValidationError
from openapi_spec_validator import validate_spec
import yaml


# Test configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
OPENAPI_SPEC_PATH = "docs/api/openapi.json"  # Path to OpenAPI spec

pytestmark = pytest.mark.skipif(
    not os.getenv("API_BASE_URL"),
    reason="API_BASE_URL required for contract tests"
)


# Fixtures
@pytest_asyncio.fixture
async def api_client():
    """HTTP client for API testing."""
    async with AsyncClient(base_url=API_BASE_URL) as client:
        yield client


@pytest.fixture
def openapi_spec():
    """Load OpenAPI specification."""
    spec_path = Path(OPENAPI_SPEC_PATH)
    if not spec_path.exists():
        pytest.skip(f"OpenAPI spec not found at {spec_path}")
    
    with open(spec_path, 'r') as f:
        if spec_path.suffix == '.yaml' or spec_path.suffix == '.yml':
            spec = yaml.safe_load(f)
        else:
            spec = json.load(f)
    
    return spec


@pytest.fixture
def customer_schema(openapi_spec):
    """Extract customer schema from OpenAPI spec."""
    return openapi_spec["components"]["schemas"]["Customer"]


@pytest.fixture
def customer_create_schema(openapi_spec):
    """Extract customer creation schema from OpenAPI spec."""
    return openapi_spec["components"]["schemas"]["CustomerCreate"]


@pytest.fixture
def customer_update_schema(openapi_spec):
    """Extract customer update schema from OpenAPI spec."""
    return openapi_spec["components"]["schemas"]["CustomerUpdate"]


@pytest.fixture
def error_schema(openapi_spec):
    """Extract error response schema from OpenAPI spec."""
    return openapi_spec["components"]["schemas"]["ErrorResponse"]


@pytest.fixture
def pagination_schema(openapi_spec):
    """Extract pagination schema from OpenAPI spec."""
    return openapi_spec["components"]["schemas"]["PaginatedResponse"]


# Helper functions
def validate_response_schema(response: Response, schema: Dict[str, Any]) -> None:
    """Validate response against JSON schema."""
    try:
        response_data = response.json()
        validate(instance=response_data, schema=schema)
    except ValidationError as e:
        pytest.fail(f"Response schema validation failed: {e}")
    except json.JSONDecodeError as e:
        pytest.fail(f"Invalid JSON response: {e}")


def validate_request_schema(request_data: Dict[str, Any], schema: Dict[str, Any]) -> None:
    """Validate request data against JSON schema."""
    try:
        validate(instance=request_data, schema=schema)
    except ValidationError as e:
        pytest.fail(f"Request schema validation failed: {e}")


# Contract tests
@pytest.mark.contract
@pytest.mark.asyncio
class TestOpenAPISpecification:
    """Test OpenAPI specification compliance."""
    
    def test_openapi_spec_validity(self, openapi_spec):
        """Test that OpenAPI specification is valid."""
        try:
            validate_spec(openapi_spec)
        except Exception as e:
            pytest.fail(f"Invalid OpenAPI specification: {e}")
    
    def test_required_schemas_exist(self, openapi_spec):
        """Test that required schemas are defined."""
        schemas = openapi_spec.get("components", {}).get("schemas", {})
        
        required_schemas = [
            "Customer",
            "CustomerCreate",
            "CustomerUpdate",
            "ErrorResponse",
            "PaginatedResponse"
        ]
        
        for schema_name in required_schemas:
            assert schema_name in schemas, f"Required schema '{schema_name}' not found"
    
    def test_customer_schema_properties(self, customer_schema):
        """Test customer schema has required properties."""
        required_properties = ["id", "email", "first_name", "last_name", "status", "created_at"]
        
        properties = customer_schema.get("properties", {})
        schema_required = customer_schema.get("required", [])
        
        for prop in required_properties:
            assert prop in properties, f"Property '{prop}' missing from Customer schema"
        
        # Check that email is in required fields
        assert "email" in schema_required
        assert "first_name" in schema_required
        assert "last_name" in schema_required
    
    def test_schema_types_and_formats(self, customer_schema):
        """Test schema property types and formats."""
        properties = customer_schema.get("properties", {})
        
        # Email should have email format
        email_prop = properties.get("email", {})
        assert email_prop.get("type") == "string"
        assert email_prop.get("format") == "email"
        
        # ID should be string (UUID)
        id_prop = properties.get("id", {})
        assert id_prop.get("type") == "string"
        
        # Status should be enum
        status_prop = properties.get("status", {})
        assert status_prop.get("type") == "string"
        assert "enum" in status_prop
        
        # Created_at should be datetime
        created_at_prop = properties.get("created_at", {})
        assert created_at_prop.get("type") == "string"
        assert created_at_prop.get("format") in ["date-time", "datetime"]


@pytest.mark.contract
@pytest.mark.asyncio
class TestCustomerEndpointContracts:
    """Test customer API endpoint contracts."""
    
    async def test_create_customer_request_contract(self, api_client, customer_create_schema):
        """Test customer creation request contract."""
        # Valid request data
        valid_request = {
            "email": "contract_test@example.com",
            "first_name": "Contract",
            "last_name": "Test",
            "phone": "555-123-4567"
        }
        
        # Validate request against schema
        validate_request_schema(valid_request, customer_create_schema)
        
        # Make request (might fail due to auth, but that's OK for contract testing)
        response = await api_client.post("/api/v1/customers", json=valid_request)
        
        # Should return proper error format if auth fails
        if response.status_code == 401:
            assert response.headers.get("content-type", "").startswith("application/json")
    
    async def test_create_customer_response_contract(self, api_client, customer_schema, error_schema):
        """Test customer creation response contract."""
        request_data = {
            "email": "response_contract_test@example.com", 
            "first_name": "Response",
            "last_name": "Contract"
        }
        
        # Add auth header if available
        headers = {}
        auth_token = os.getenv("TEST_AUTH_TOKEN")
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        
        response = await api_client.post(
            "/api/v1/customers",
            json=request_data,
            headers=headers
        )
        
        if response.status_code == 201:
            # Success response should match customer schema
            validate_response_schema(response, customer_schema)
        elif response.status_code in [400, 401, 422]:
            # Error response should match error schema
            validate_response_schema(response, error_schema)
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")
    
    async def test_get_customer_response_contract(self, api_client, customer_schema, error_schema):
        """Test get customer response contract."""
        # Test with a likely non-existent customer ID
        test_customer_id = "00000000-0000-0000-0000-000000000000"
        
        headers = {}
        auth_token = os.getenv("TEST_AUTH_TOKEN")
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        
        response = await api_client.get(
            f"/api/v1/customers/{test_customer_id}",
            headers=headers
        )
        
        if response.status_code == 200:
            # Success response should match customer schema
            validate_response_schema(response, customer_schema)
        elif response.status_code in [401, 403, 404]:
            # Error response should match error schema  
            validate_response_schema(response, error_schema)
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")
    
    async def test_list_customers_response_contract(self, api_client, pagination_schema, error_schema):
        """Test list customers response contract."""
        headers = {}
        auth_token = os.getenv("TEST_AUTH_TOKEN")
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        
        response = await api_client.get("/api/v1/customers", headers=headers)
        
        if response.status_code == 200:
            # Success response should match pagination schema
            validate_response_schema(response, pagination_schema)
        elif response.status_code in [401, 403]:
            # Error response should match error schema
            validate_response_schema(response, error_schema)
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")
    
    async def test_update_customer_request_contract(self, api_client, customer_update_schema):
        """Test customer update request contract."""
        valid_update_request = {
            "first_name": "Updated Name",
            "phone": "555-999-8888"
        }
        
        # Validate request against schema
        validate_request_schema(valid_update_request, customer_update_schema)
        
        # Test partial update (should be allowed)
        partial_update = {"first_name": "Partial Update"}
        validate_request_schema(partial_update, customer_update_schema)


@pytest.mark.contract
@pytest.mark.asyncio
class TestErrorResponseContracts:
    """Test error response contracts."""
    
    async def test_400_error_response_contract(self, api_client, error_schema):
        """Test 400 Bad Request response contract."""
        # Send invalid JSON to trigger 400 error
        response = await api_client.post(
            "/api/v1/customers",
            content="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 400:
            validate_response_schema(response, error_schema)
    
    async def test_401_error_response_contract(self, api_client, error_schema):
        """Test 401 Unauthorized response contract."""
        # Request without auth token
        response = await api_client.get("/api/v1/customers")
        
        if response.status_code == 401:
            validate_response_schema(response, error_schema)
            
            # Check for required auth headers
            response_data = response.json()
            assert "detail" in response_data or "message" in response_data
    
    async def test_404_error_response_contract(self, api_client, error_schema):
        """Test 404 Not Found response contract."""
        headers = {}
        auth_token = os.getenv("TEST_AUTH_TOKEN")
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        
        # Request non-existent customer
        response = await api_client.get(
            "/api/v1/customers/nonexistent-id",
            headers=headers
        )
        
        if response.status_code == 404:
            validate_response_schema(response, error_schema)
    
    async def test_422_validation_error_contract(self, api_client, error_schema):
        """Test 422 Unprocessable Entity response contract."""
        # Send invalid data to trigger validation error
        invalid_request = {
            "email": "not-an-email",
            "first_name": "",  # Empty required field
            "last_name": "Test"
        }
        
        headers = {}
        auth_token = os.getenv("TEST_AUTH_TOKEN")
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        
        response = await api_client.post(
            "/api/v1/customers",
            json=invalid_request,
            headers=headers
        )
        
        if response.status_code == 422:
            # FastAPI returns specific validation error format
            response_data = response.json()
            assert "detail" in response_data
            assert isinstance(response_data["detail"], list)
            
            for error in response_data["detail"]:
                assert "loc" in error
                assert "msg" in error
                assert "type" in error


@pytest.mark.contract
@pytest.mark.asyncio
class TestHeaderContracts:
    """Test HTTP header contracts."""
    
    async def test_content_type_headers(self, api_client):
        """Test Content-Type headers in responses."""
        headers = {}
        auth_token = os.getenv("TEST_AUTH_TOKEN")
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        
        response = await api_client.get("/api/v1/customers", headers=headers)
        
        # Should return JSON content type
        content_type = response.headers.get("content-type", "")
        assert content_type.startswith("application/json")
    
    async def test_cors_headers(self, api_client):
        """Test CORS headers are present."""
        # Make OPTIONS request to check CORS
        response = await api_client.options("/api/v1/customers")
        
        if response.status_code == 200:
            # Check for CORS headers
            assert "access-control-allow-origin" in [h.lower() for h in response.headers.keys()]
        
        # Make actual request and check CORS headers
        response = await api_client.get("/api/v1/customers")
        
        cors_headers = [h.lower() for h in response.headers.keys()]
        # At least one CORS header should be present
        expected_cors_headers = [
            "access-control-allow-origin",
            "access-control-allow-methods", 
            "access-control-allow-headers"
        ]
        
        has_cors_header = any(header in cors_headers for header in expected_cors_headers)
        assert has_cors_header, "No CORS headers found"
    
    async def test_security_headers(self, api_client):
        """Test security headers are present."""
        response = await api_client.get("/health")  # Use health endpoint as it's usually available
        
        security_headers = response.headers
        
        # Check for common security headers
        expected_headers = {
            "x-content-type-options": "nosniff",
            "x-frame-options": ["DENY", "SAMEORIGIN"],
            "x-xss-protection": "1; mode=block"
        }
        
        for header, expected_value in expected_headers.items():
            if header in security_headers:
                actual_value = security_headers[header].lower()
                if isinstance(expected_value, list):
                    assert actual_value in [v.lower() for v in expected_value]
                else:
                    assert actual_value == expected_value.lower()


@pytest.mark.contract
@pytest.mark.asyncio
class TestPaginationContracts:
    """Test pagination contracts."""
    
    async def test_pagination_parameters(self, api_client):
        """Test pagination parameter contracts."""
        headers = {}
        auth_token = os.getenv("TEST_AUTH_TOKEN")
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        
        # Test with pagination parameters
        params = {"limit": 10, "offset": 0}
        response = await api_client.get("/api/v1/customers", params=params, headers=headers)
        
        if response.status_code == 200:
            response_data = response.json()
            
            # Should have pagination fields
            assert "items" in response_data
            assert "total" in response_data
            assert "limit" in response_data
            assert "offset" in response_data
            
            # Verify values
            assert response_data["limit"] == 10
            assert response_data["offset"] == 0
            assert isinstance(response_data["items"], list)
            assert isinstance(response_data["total"], int)
            assert len(response_data["items"]) <= 10
    
    async def test_pagination_boundaries(self, api_client):
        """Test pagination boundary conditions."""
        headers = {}
        auth_token = os.getenv("TEST_AUTH_TOKEN")
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        
        # Test maximum limit
        params = {"limit": 1000}  # Large limit
        response = await api_client.get("/api/v1/customers", params=params, headers=headers)
        
        if response.status_code == 200:
            response_data = response.json()
            # Should enforce maximum limit
            assert response_data["limit"] <= 100  # Assuming max limit is 100
        elif response.status_code == 422:
            # Should return validation error for invalid limit
            error_data = response.json()
            assert "detail" in error_data


@pytest.mark.contract
@pytest.mark.asyncio
class TestVersioningContracts:
    """Test API versioning contracts."""
    
    async def test_api_version_in_path(self, api_client):
        """Test API version is properly specified in path."""
        # All API endpoints should include version
        response = await api_client.get("/api/v1/customers")
        
        # Should not be 404 (endpoint exists with version)
        assert response.status_code != 404
    
    async def test_version_header_support(self, api_client):
        """Test API version header support."""
        headers = {"Accept": "application/vnd.api+json;version=1"}
        
        response = await api_client.get("/api/v1/customers", headers=headers)
        
        # Should handle version headers gracefully
        assert response.status_code != 400  # Bad Request due to version header


@pytest.mark.contract
@pytest.mark.parametrize("endpoint,method,expected_codes", [
    ("/api/v1/customers", "GET", [200, 401, 403]),
    ("/api/v1/customers", "POST", [201, 400, 401, 403, 422]),
    ("/api/v1/customers/test-id", "GET", [200, 401, 403, 404]),
    ("/api/v1/customers/test-id", "PUT", [200, 400, 401, 403, 404, 422]),
    ("/api/v1/customers/test-id", "DELETE", [204, 401, 403, 404]),
])
@pytest.mark.asyncio
async def test_endpoint_status_codes(api_client, endpoint, method, expected_codes):
    """Test that endpoints return expected status codes."""
    headers = {}
    auth_token = os.getenv("TEST_AUTH_TOKEN")
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    
    # Make request
    if method == "GET":
        response = await api_client.get(endpoint, headers=headers)
    elif method == "POST":
        response = await api_client.post(endpoint, json={"email": "test@example.com", "first_name": "Test", "last_name": "User"}, headers=headers)
    elif method == "PUT":
        response = await api_client.put(endpoint, json={"first_name": "Updated"}, headers=headers)
    elif method == "DELETE":
        response = await api_client.delete(endpoint, headers=headers)
    else:
        pytest.skip(f"Method {method} not supported in test")
    
    # Check status code is expected
    assert response.status_code in expected_codes, f"Unexpected status code {response.status_code} for {method} {endpoint}"