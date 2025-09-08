"""
Tests for Request/Response Validation - Pydantic schema validation, FastAPI integration.
"""
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field, ValidationError
from tests.utilities.api_test_base import APITestBase


# Test schemas for validation testing
class UserCreateSchema(BaseModel):
    """Schema for user creation requests."""
    email: str = Field(..., min_length=3, max_length=254)
    name: str = Field(..., min_length=1, max_length=100)
    age: Optional[int] = Field(None, ge=0, le=150)
    roles: list[str] = Field(default_factory=list)


class UserUpdateSchema(BaseModel):
    """Schema for user update requests."""
    email: Optional[str] = Field(None, min_length=3, max_length=254)
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    age: Optional[int] = Field(None, ge=0, le=150)
    roles: Optional[list[str]] = None


class UserResponseSchema(BaseModel):
    """Schema for user responses."""
    id: str
    email: str
    name: str
    age: Optional[int] = None
    roles: list[str]
    created_at: str
    is_active: bool = True


class PaginatedResponseSchema(BaseModel):
    """Schema for paginated responses."""
    items: list[UserResponseSchema]
    total: int
    page: int
    size: int
    has_next: bool = False
    has_previous: bool = False


class ErrorResponseSchema(BaseModel):
    """Schema for error responses."""
    error: str
    message: str
    details: Optional[dict[str, Any]] = None
    timestamp: str


class TestPydanticSchemaValidation(APITestBase):
    """Test Pydantic schema validation patterns."""

    def test_user_create_schema_valid_data(self):
        """Test UserCreateSchema with valid data."""
        valid_data = {
            "email": "test@example.com",
            "name": "Test User",
            "age": 25,
            "roles": ["user", "admin"]
        }

        schema = UserCreateSchema(**valid_data)

        assert schema.email == "test@example.com"
        assert schema.name == "Test User"
        assert schema.age == 25
        assert schema.roles == ["user", "admin"]

    def test_user_create_schema_minimal_data(self):
        """Test UserCreateSchema with minimal required data."""
        minimal_data = {
            "email": "min@example.com",
            "name": "Min User"
        }

        schema = UserCreateSchema(**minimal_data)

        assert schema.email == "min@example.com"
        assert schema.name == "Min User"
        assert schema.age is None
        assert schema.roles == []  # default empty list

    def test_user_create_schema_validation_errors(self):
        """Test UserCreateSchema validation errors."""
        # Missing required field
        with pytest.raises(ValidationError) as exc_info:
            UserCreateSchema(name="Test User")  # Missing email

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("email",) for error in errors)

        # Invalid email format (too short)
        with pytest.raises(ValidationError) as exc_info:
            UserCreateSchema(email="ab", name="Test User")  # Too short

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("email",) for error in errors)

        # Invalid age (negative)
        with pytest.raises(ValidationError) as exc_info:
            UserCreateSchema(email="test@example.com", name="Test User", age=-1)

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("age",) for error in errors)

        # Invalid age (too high)
        with pytest.raises(ValidationError) as exc_info:
            UserCreateSchema(email="test@example.com", name="Test User", age=200)

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("age",) for error in errors)

    def test_user_update_schema_optional_fields(self):
        """Test UserUpdateSchema with optional field updates."""
        # Test with single field update
        update_data = {"name": "Updated Name"}
        schema = UserUpdateSchema(**update_data)

        assert schema.name == "Updated Name"
        assert schema.email is None
        assert schema.age is None
        assert schema.roles is None

        # Test with multiple field updates
        multi_update_data = {
            "email": "updated@example.com",
            "age": 30,
            "roles": ["admin"]
        }
        multi_schema = UserUpdateSchema(**multi_update_data)

        assert multi_schema.email == "updated@example.com"
        assert multi_schema.age == 30
        assert multi_schema.roles == ["admin"]

    def test_user_response_schema_serialization(self):
        """Test UserResponseSchema data serialization."""
        response_data = {
            "id": str(uuid4()),
            "email": "response@example.com",
            "name": "Response User",
            "age": 28,
            "roles": ["user"],
            "created_at": "2023-01-01T00:00:00Z",
            "is_active": True
        }

        schema = UserResponseSchema(**response_data)

        # Test serialization to dict
        serialized = schema.model_dump()
        assert serialized["email"] == "response@example.com"
        assert serialized["age"] == 28
        assert serialized["is_active"] is True

        # Test JSON serialization
        json_str = schema.model_dump_json()
        assert isinstance(json_str, str)
        assert "response@example.com" in json_str

    def test_paginated_response_schema(self):
        """Test PaginatedResponseSchema structure."""
        user_items = [
            UserResponseSchema(
                id=str(uuid4()),
                email=f"user{i}@example.com",
                name=f"User {i}",
                roles=["user"],
                created_at="2023-01-01T00:00:00Z"
            )
            for i in range(3)
        ]

        paginated_data = {
            "items": user_items,
            "total": 10,
            "page": 1,
            "size": 3,
            "has_next": True,
            "has_previous": False
        }

        schema = PaginatedResponseSchema(**paginated_data)

        assert len(schema.items) == 3
        assert schema.total == 10
        assert schema.has_next is True
        assert schema.has_previous is False

    def test_error_response_schema(self):
        """Test ErrorResponseSchema structure."""
        error_data = {
            "error": "ValidationError",
            "message": "Invalid input data",
            "details": {"field": "email", "issue": "invalid format"},
            "timestamp": datetime.utcnow().isoformat()
        }

        schema = ErrorResponseSchema(**error_data)

        assert schema.error == "ValidationError"
        assert schema.message == "Invalid input data"
        assert schema.details["field"] == "email"
        assert schema.timestamp is not None


class TestFastAPIValidationIntegration(APITestBase):
    """Test FastAPI request/response validation integration."""

    def create_test_validation_app(self) -> FastAPI:
        """Create test FastAPI app with validation endpoints."""
        app = FastAPI(title="Validation Test App")

        @app.post("/users/", response_model=UserResponseSchema, status_code=201)
        async def create_user(user_data: UserCreateSchema):
            """Create user endpoint with validation."""
            return UserResponseSchema(
                id=str(uuid4()),
                email=user_data.email,
                name=user_data.name,
                age=user_data.age,
                roles=user_data.roles,
                created_at=datetime.utcnow().isoformat()
            )

        @app.put("/users/{user_id}", response_model=UserResponseSchema)
        async def update_user(user_id: str, user_data: UserUpdateSchema):
            """Update user endpoint with validation."""
            return UserResponseSchema(
                id=user_id,
                email=user_data.email or "existing@example.com",
                name=user_data.name or "Existing User",
                age=user_data.age,
                roles=user_data.roles or ["user"],
                created_at="2023-01-01T00:00:00Z"
            )

        @app.get("/users/", response_model=PaginatedResponseSchema)
        async def list_users():
            """List users endpoint with pagination response."""
            return PaginatedResponseSchema(
                items=[],
                total=0,
                page=1,
                size=10
            )

        return app

    def test_fastapi_request_validation_success(self):
        """Test successful request validation in FastAPI."""
        app = self.create_test_validation_app()
        client = TestClient(app)

        # Test valid user creation
        valid_user_data = {
            "email": "fastapi@example.com",
            "name": "FastAPI User",
            "age": 30,
            "roles": ["user", "tester"]
        }

        response = client.post("/users/", json=valid_user_data)

        self.assert_response_status(response, 201)
        response_data = self.assert_response_json(response, ["id", "email", "name", "created_at"])

        assert response_data["email"] == "fastapi@example.com"
        assert response_data["name"] == "FastAPI User"
        assert response_data["age"] == 30
        assert response_data["roles"] == ["user", "tester"]

    def test_fastapi_request_validation_errors(self):
        """Test request validation errors in FastAPI."""
        app = self.create_test_validation_app()
        client = TestClient(app)

        # Test missing required field
        invalid_data = {
            "name": "Missing Email User"
            # Missing email
        }

        response = client.post("/users/", json=invalid_data)
        self.assert_validation_error(response, "email")

        # Test invalid field constraints
        constraint_violation_data = {
            "email": "ab",  # Too short
            "name": "Test User",
            "age": -5  # Negative age
        }

        response = client.post("/users/", json=constraint_violation_data)
        self.assert_validation_error(response)

        # Check validation error details
        error_data = response.json()
        assert "detail" in error_data
        assert isinstance(error_data["detail"], list)

    def test_fastapi_response_validation(self):
        """Test response schema validation in FastAPI."""
        app = self.create_test_validation_app()
        client = TestClient(app)

        # Test response structure
        response = client.get("/users/")

        self.assert_response_status(response, 200)
        response_data = self.assert_response_json(response, ["items", "total", "page", "size"])

        # Validate paginated response structure
        assert isinstance(response_data["items"], list)
        assert isinstance(response_data["total"], int)
        assert isinstance(response_data["page"], int)
        assert isinstance(response_data["size"], int)
        assert "has_next" in response_data
        assert "has_previous" in response_data

    def test_fastapi_partial_update_validation(self):
        """Test partial update validation in FastAPI."""
        app = self.create_test_validation_app()
        client = TestClient(app)

        user_id = str(uuid4())

        # Test partial update with single field
        partial_update = {
            "name": "Partially Updated User"
        }

        response = client.put(f"/users/{user_id}", json=partial_update)

        self.assert_response_status(response, 200)
        response_data = self.assert_response_json(response, ["id", "name"])

        assert response_data["id"] == user_id
        assert response_data["name"] == "Partially Updated User"
        assert response_data["email"] == "existing@example.com"  # Default value

        # Test validation on partial update
        invalid_partial_update = {
            "email": "invalid",  # Too short
            "age": 200  # Too high
        }

        response = client.put(f"/users/{user_id}", json=invalid_partial_update)
        self.assert_validation_error(response)


class TestSchemaInheritancePatterns(APITestBase):
    """Test schema inheritance and composition patterns."""

    def test_base_schema_patterns(self):
        """Test base schema inheritance patterns."""
        try:
            from dotmac_shared.schemas import (
                BaseCreateSchema,
                BaseResponseSchema,
                BaseUpdateSchema,
            )

            # Test that schemas can be imported (structure test)
            assert BaseCreateSchema is not None
            assert BaseUpdateSchema is not None
            assert BaseResponseSchema is not None

        except ImportError:
            pytest.skip("Base schemas not available")

    def test_custom_schema_inheritance(self):
        """Test custom schema inheritance from base schemas."""
        # Define base schema for testing
        class BaseTestSchema(BaseModel):
            """Base schema for testing inheritance."""
            created_at: Optional[str] = None
            updated_at: Optional[str] = None

        class InheritedCreateSchema(BaseTestSchema):
            """Schema inheriting from base."""
            name: str = Field(..., min_length=1)
            description: str = Field(..., max_length=500)

        # Test inheritance works correctly
        inherited_data = {
            "name": "Inherited Test",
            "description": "Testing inheritance",
            "created_at": "2023-01-01T00:00:00Z"
        }

        schema = InheritedCreateSchema(**inherited_data)

        assert schema.name == "Inherited Test"
        assert schema.description == "Testing inheritance"
        assert schema.created_at == "2023-01-01T00:00:00Z"
        assert schema.updated_at is None


class TestValidationUtilities(APITestBase):
    """Test validation utility functions and patterns."""

    def test_validation_error_handling_patterns(self):
        """Test validation error handling and formatting patterns."""
        def format_validation_error(validation_error: ValidationError) -> dict[str, Any]:
            """Format Pydantic validation error for API response."""
            errors = []
            for error in validation_error.errors():
                errors.append({
                    "field": ".".join(str(loc) for loc in error["loc"]),
                    "message": error["msg"],
                    "type": error["type"],
                    "input": error.get("input")
                })

            return {
                "error": "ValidationError",
                "message": "Request validation failed",
                "details": errors
            }

        # Test validation error formatting
        try:
            UserCreateSchema(email="invalid", name="")  # Multiple validation errors
        except ValidationError as e:
            formatted_error = format_validation_error(e)

            assert formatted_error["error"] == "ValidationError"
            assert "details" in formatted_error
            assert isinstance(formatted_error["details"], list)
            assert len(formatted_error["details"]) > 0

            # Check that field names are properly formatted
            field_names = [detail["field"] for detail in formatted_error["details"]]
            assert any("email" in field_name for field_name in field_names)
            assert any("name" in field_name for field_name in field_names)

    def test_custom_validator_patterns(self):
        """Test custom validation patterns with Pydantic."""
        from pydantic import validator

        class CustomValidationSchema(BaseModel):
            """Schema with custom validators."""
            email: str
            password: str
            confirm_password: str

            @validator('email')
            def email_must_contain_at(cls, v):
                if '@' not in v:
                    raise ValueError('Email must contain @ symbol')
                return v

            @validator('password')
            def password_strength(cls, v):
                if len(v) < 8:
                    raise ValueError('Password must be at least 8 characters')
                return v

            @validator('confirm_password')
            def passwords_match(cls, v, values):
                if 'password' in values and v != values['password']:
                    raise ValueError('Passwords do not match')
                return v

        # Test successful validation
        valid_data = {
            "email": "test@example.com",
            "password": "strongpassword",
            "confirm_password": "strongpassword"
        }

        schema = CustomValidationSchema(**valid_data)
        assert schema.email == "test@example.com"

        # Test custom validation failures
        with pytest.raises(ValidationError) as exc_info:
            CustomValidationSchema(
                email="invalid-email",  # No @ symbol
                password="weak",  # Too short
                confirm_password="different"  # Doesn't match
            )

        errors = exc_info.value.errors()
        assert len(errors) >= 2  # Multiple validation errors
