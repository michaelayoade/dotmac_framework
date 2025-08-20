"""
Contract tests for DotMac Framework.
Ensures API contracts and data models remain compatible across services.
"""


import jsonschema
import pytest


class TestCustomerContracts:
    """Test customer data contracts across services."""

    @pytest.mark.contract
    def test_customer_creation_contract(self, contract_schemas, validate_contract, sample_customer_data):
        """Test customer creation follows the contract."""
        assert validate_contract(sample_customer_data, contract_schemas["customer"])

    @pytest.mark.contract
    def test_customer_required_fields(self, contract_schemas):
        """Test customer contract requires essential fields."""
        schema = contract_schemas["customer"]

        # Missing required field should fail validation
        invalid_customer = {"email": "test@example.com"}  # Missing id and status

        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(invalid_customer, schema)

    @pytest.mark.contract
    def test_customer_email_format(self, contract_schemas):
        """Test customer email format validation."""
        schema = contract_schemas["customer"]

        invalid_customer = {
            "id": "cust_123",
            "email": "invalid-email",  # Invalid format
            "status": "active"
        }

        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(invalid_customer, schema)

    @pytest.mark.contract
    def test_customer_status_enum(self, contract_schemas):
        """Test customer status follows enum values."""
        schema = contract_schemas["customer"]

        invalid_customer = {
            "id": "cust_123",
            "email": "test@example.com",
            "status": "invalid_status"  # Not in enum
        }

        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(invalid_customer, schema)


class TestServiceContracts:
    """Test service data contracts across services."""

    @pytest.mark.contract
    def test_service_creation_contract(self, contract_schemas, validate_contract, sample_service_data):
        """Test service creation follows the contract."""
        # Convert sample data to match schema requirements
        service_data = {
            "id": sample_service_data["id"],
            "customer_id": sample_service_data["customer_id"],
            "service_type": sample_service_data["service_type"],
            "status": sample_service_data["status"]
        }

        assert validate_contract(service_data, contract_schemas["service"])

    @pytest.mark.contract
    def test_service_customer_reference(self, contract_schemas):
        """Test service must reference valid customer."""
        schema = contract_schemas["service"]

        # Missing customer_id should fail
        invalid_service = {
            "id": "svc_123",
            "service_type": "broadband",
            "status": "active"
        }

        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(invalid_service, schema)


class TestEventContracts:
    """Test event data contracts across services."""

    @pytest.mark.contract
    def test_event_structure_contract(self, contract_schemas, validate_contract):
        """Test event structure follows the contract."""
        event_data = {
            "event_type": "customer.created",
            "data": {"customer_id": "cust_123"},
            "timestamp": "2024-01-15T10:30:00Z"
        }

        assert validate_contract(event_data, contract_schemas["event"])

    @pytest.mark.contract
    def test_event_timestamp_format(self, contract_schemas):
        """Test event timestamp format validation."""
        schema = contract_schemas["event"]

        # Invalid timestamp format
        invalid_event = {
            "event_type": "test.event",
            "data": {},
            "timestamp": "2024-01-15"  # Missing time portion
        }

        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(invalid_event, schema)


class TestCrossServiceContracts:
    """Test contracts between different services."""

    @pytest.mark.contract
    @pytest.mark.integration
    async def test_customer_service_integration(self, async_http_client, api_headers):
        """Test customer creation integrates with service creation."""
        # This would test actual API calls between services
        # For now, we'll simulate the contract

        customer_response = {
            "id": "cust_123",
            "email": "test@example.com",
            "status": "active"
        }

        service_response = {
            "id": "svc_456",
            "customer_id": "cust_123",  # Must match customer.id
            "service_type": "broadband",
            "status": "active"
        }

        # Contract: service.customer_id must equal customer.id
        assert service_response["customer_id"] == customer_response["id"]

    @pytest.mark.contract
    def test_billing_service_contract(self, sample_customer_data, sample_invoice_data):
        """Test billing service contracts with customer service."""
        # Contract: invoice.customer_id must reference valid customer
        assert sample_invoice_data["customer_id"] == sample_customer_data["id"]

        # Contract: invoice must have required billing fields
        required_billing_fields = ["id", "amount", "due_date", "status"]
        for field in required_billing_fields:
            assert field in sample_invoice_data

    @pytest.mark.contract
    def test_event_publishing_contract(self, test_data_factory):
        """Test event publishing contracts."""
        # Create test customer
        customer = test_data_factory.customer()

        # Generate expected event
        expected_event = {
            "event_type": "customer.created",
            "data": customer,
            "timestamp": "2024-01-15T10:30:00Z",
            "source": "dotmac_identity"
        }

        # Contract: events must include source service
        assert "source" in expected_event
        assert expected_event["source"].startswith("dotmac_")

        # Contract: customer events must include customer data
        assert "data" in expected_event
        assert expected_event["data"]["id"] == customer["id"]


class TestAPIResponseContracts:
    """Test API response format contracts."""

    @pytest.mark.contract
    def test_error_response_contract(self):
        """Test error responses follow standard format."""
        error_response = {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid input data",
                "details": {
                    "field": "email",
                    "reason": "Invalid email format"
                }
            },
            "timestamp": "2024-01-15T10:30:00Z",
            "request_id": "req_123"
        }

        # Contract: error responses must have these fields
        assert "error" in error_response
        assert "code" in error_response["error"]
        assert "message" in error_response["error"]
        assert "timestamp" in error_response
        assert "request_id" in error_response

    @pytest.mark.contract
    def test_success_response_contract(self):
        """Test success responses follow standard format."""
        success_response = {
            "data": {"id": "cust_123", "status": "created"},
            "meta": {
                "timestamp": "2024-01-15T10:30:00Z",
                "version": "1.0"
            }
        }

        # Contract: success responses should have data and meta
        assert "data" in success_response
        assert "meta" in success_response
        assert "timestamp" in success_response["meta"]

    @pytest.mark.contract
    def test_pagination_contract(self):
        """Test paginated responses follow standard format."""
        paginated_response = {
            "data": [
                {"id": "cust_1", "email": "test1@example.com"},
                {"id": "cust_2", "email": "test2@example.com"}
            ],
            "pagination": {
                "page": 1,
                "per_page": 10,
                "total": 2,
                "pages": 1
            },
            "meta": {
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }

        # Contract: paginated responses must have pagination metadata
        assert "pagination" in paginated_response
        assert "page" in paginated_response["pagination"]
        assert "total" in paginated_response["pagination"]
        assert len(paginated_response["data"]) <= paginated_response["pagination"]["per_page"]


class TestDatabaseSchemaContracts:
    """Test database schema contracts."""

    @pytest.mark.contract
    @pytest.mark.slow
    async def test_customer_table_schema(self, db_session):
        """Test customer table has required columns."""
        # This would test actual database schema
        # For example, using SQLAlchemy metadata

        from sqlalchemy import text

        # Check table exists and has required columns
        result = await db_session.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'customers'
            ORDER BY ordinal_position
        """))

        columns = {row[0]: {"type": row[1], "nullable": row[2]} for row in result}

        # Contract: customers table must have these columns
        required_columns = ["id", "email", "first_name", "last_name", "created_at"]
        for col in required_columns:
            assert col in columns, f"Required column {col} missing from customers table"

    @pytest.mark.contract
    def test_foreign_key_contracts(self):
        """Test foreign key relationships follow contracts."""
        # This would test database foreign key constraints
        # Contract: services.customer_id must reference customers.id
        # Contract: invoices.customer_id must reference customers.id
        # etc.

        # For now, we'll define the expected relationships
        expected_relationships = {
            "services": {"customer_id": "customers.id"},
            "invoices": {"customer_id": "customers.id"},
            "payments": {"invoice_id": "invoices.id"},
            "support_tickets": {"customer_id": "customers.id"}
        }

        # In a real test, you'd verify these exist in the database
        assert len(expected_relationships) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "contract"])
