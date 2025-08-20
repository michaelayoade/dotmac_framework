"""
Unit tests for SchemaRegistrySDK.
"""


import pytest

from dotmac_core_events.sdks import CompatibilityLevel, SchemaRegistrySDK


class TestSchemaRegistrySDK:
    """Test cases for SchemaRegistrySDK."""

    @pytest.mark.asyncio
    async def test_register_schema(self, schema_registry: SchemaRegistrySDK, sample_schema, tenant_id):
        """Test registering a schema."""
        result = await schema_registry.register_schema(
            event_type="user.created",
            version="1.0",
            schema=sample_schema,
            compatibility_level=CompatibilityLevel.BACKWARD,
            tenant_id=tenant_id
        )

        assert result.success is True
        assert result.schema_id is not None
        assert result.version == "1.0"

    @pytest.mark.asyncio
    async def test_get_schema(self, schema_registry: SchemaRegistrySDK, sample_schema, tenant_id):
        """Test getting a schema."""
        # Register schema first
        await schema_registry.register_schema(
            event_type="user.created",
            version="1.0",
            schema=sample_schema,
            compatibility_level=CompatibilityLevel.BACKWARD,
            tenant_id=tenant_id
        )

        # Get schema
        result = await schema_registry.get_schema(
            event_type="user.created",
            version="1.0",
            tenant_id=tenant_id
        )

        assert result is not None
        assert result["schema"] == sample_schema
        assert result["version"] == "1.0"

    @pytest.mark.asyncio
    async def test_get_latest_schema(self, schema_registry: SchemaRegistrySDK, sample_schema, tenant_id):
        """Test getting the latest schema version."""
        # Register multiple versions
        await schema_registry.register_schema(
            event_type="user.created",
            version="1.0",
            schema=sample_schema,
            compatibility_level=CompatibilityLevel.BACKWARD,
            tenant_id=tenant_id
        )

        updated_schema = {**sample_schema, "properties": {**sample_schema["properties"], "age": {"type": "integer"}}}
        await schema_registry.register_schema(
            event_type="user.created",
            version="2.0",
            schema=updated_schema,
            compatibility_level=CompatibilityLevel.BACKWARD,
            tenant_id=tenant_id
        )

        # Get latest version
        result = await schema_registry.get_schema(
            event_type="user.created",
            tenant_id=tenant_id
        )

        assert result["version"] == "2.0"
        assert "age" in result["schema"]["properties"]

    @pytest.mark.asyncio
    async def test_validate_event(self, schema_registry: SchemaRegistrySDK, sample_schema, sample_event_data, tenant_id):
        """Test event validation."""
        # Register schema
        await schema_registry.register_schema(
            event_type="user.created",
            version="1.0",
            schema=sample_schema,
            compatibility_level=CompatibilityLevel.BACKWARD,
            tenant_id=tenant_id
        )

        # Validate valid data
        result = await schema_registry.validate_event(
            event_type="user.created",
            data=sample_event_data,
            tenant_id=tenant_id
        )

        assert result.valid is True
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_validate_invalid_event(self, schema_registry: SchemaRegistrySDK, sample_schema, tenant_id):
        """Test validation of invalid event data."""
        # Register schema
        await schema_registry.register_schema(
            event_type="user.created",
            version="1.0",
            schema=sample_schema,
            compatibility_level=CompatibilityLevel.BACKWARD,
            tenant_id=tenant_id
        )

        # Validate invalid data (missing required field)
        invalid_data = {"user_id": "123"}  # Missing email
        result = await schema_registry.validate_event(
            event_type="user.created",
            data=invalid_data,
            tenant_id=tenant_id
        )

        assert result.valid is False
        assert len(result.errors) > 0
        assert any("email" in error for error in result.errors)

    @pytest.mark.asyncio
    async def test_check_compatibility_backward(self, schema_registry: SchemaRegistrySDK, sample_schema, tenant_id):
        """Test backward compatibility checking."""
        # Register initial schema
        await schema_registry.register_schema(
            event_type="user.created",
            version="1.0",
            schema=sample_schema,
            compatibility_level=CompatibilityLevel.BACKWARD,
            tenant_id=tenant_id
        )

        # New schema with additional optional field (backward compatible)
        new_schema = {
            **sample_schema,
            "properties": {
                **sample_schema["properties"],
                "age": {"type": "integer"}  # Optional field
            }
        }

        result = await schema_registry.check_compatibility(
            event_type="user.created",
            new_schema=new_schema,
            tenant_id=tenant_id
        )

        assert result.compatible is True

    @pytest.mark.asyncio
    async def test_check_compatibility_incompatible(self, schema_registry: SchemaRegistrySDK, sample_schema, tenant_id):
        """Test incompatible schema detection."""
        # Register initial schema
        await schema_registry.register_schema(
            event_type="user.created",
            version="1.0",
            schema=sample_schema,
            compatibility_level=CompatibilityLevel.BACKWARD,
            tenant_id=tenant_id
        )

        # New schema with additional required field (not backward compatible)
        new_schema = {
            **sample_schema,
            "properties": {
                **sample_schema["properties"],
                "age": {"type": "integer"}
            },
            "required": sample_schema["required"] + ["age"]
        }

        result = await schema_registry.check_compatibility(
            event_type="user.created",
            new_schema=new_schema,
            tenant_id=tenant_id
        )

        assert result.compatible is False
        assert len(result.issues) > 0

    @pytest.mark.asyncio
    async def test_list_schemas(self, schema_registry: SchemaRegistrySDK, sample_schema, tenant_id):
        """Test listing schemas for an event type."""
        # Register multiple versions
        await schema_registry.register_schema(
            event_type="user.created",
            version="1.0",
            schema=sample_schema,
            compatibility_level=CompatibilityLevel.BACKWARD,
            tenant_id=tenant_id
        )

        await schema_registry.register_schema(
            event_type="user.created",
            version="2.0",
            schema=sample_schema,
            compatibility_level=CompatibilityLevel.BACKWARD,
            tenant_id=tenant_id
        )

        # List schemas
        schemas = await schema_registry.list_schemas(
            event_type="user.created",
            tenant_id=tenant_id
        )

        assert len(schemas) == 2
        versions = [s["version"] for s in schemas]
        assert "1.0" in versions
        assert "2.0" in versions

    @pytest.mark.asyncio
    async def test_delete_schema(self, schema_registry: SchemaRegistrySDK, sample_schema, tenant_id):
        """Test deleting a schema."""
        # Register schema
        await schema_registry.register_schema(
            event_type="user.created",
            version="1.0",
            schema=sample_schema,
            compatibility_level=CompatibilityLevel.BACKWARD,
            tenant_id=tenant_id
        )

        # Delete schema
        await schema_registry.delete_schema(
            event_type="user.created",
            version="1.0",
            tenant_id=tenant_id
        )

        # Verify deletion
        with pytest.raises(Exception):  # Should raise error when schema not found
            await schema_registry.get_schema(
                event_type="user.created",
                version="1.0",
                tenant_id=tenant_id
            )

    @pytest.mark.asyncio
    async def test_tenant_isolation(self, schema_registry: SchemaRegistrySDK, sample_schema):
        """Test that schemas are isolated by tenant."""
        tenant1 = "tenant-1"
        tenant2 = "tenant-2"

        # Register schema for tenant 1
        await schema_registry.register_schema(
            event_type="user.created",
            version="1.0",
            schema=sample_schema,
            compatibility_level=CompatibilityLevel.BACKWARD,
            tenant_id=tenant1
        )

        # Try to get schema as tenant 2 - should not find it
        with pytest.raises(Exception):
            await schema_registry.get_schema(
                event_type="user.created",
                version="1.0",
                tenant_id=tenant2
            )

    @pytest.mark.asyncio
    async def test_cache_functionality(self, schema_registry: SchemaRegistrySDK, sample_schema, tenant_id):
        """Test that schema caching works."""
        # Register schema
        await schema_registry.register_schema(
            event_type="user.created",
            version="1.0",
            schema=sample_schema,
            compatibility_level=CompatibilityLevel.BACKWARD,
            tenant_id=tenant_id
        )

        # Get schema twice - second call should use cache
        result1 = await schema_registry.get_schema(
            event_type="user.created",
            version="1.0",
            tenant_id=tenant_id
        )

        result2 = await schema_registry.get_schema(
            event_type="user.created",
            version="1.0",
            tenant_id=tenant_id
        )

        assert result1 == result2
