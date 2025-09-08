"""
Test cases for DotMac Core types.
"""

import uuid
from unittest.mock import Mock

import pytest

from dotmac.core.types import GUID


class TestGUIDType:
    """Test GUID SQLAlchemy type."""

    def test_guid_initialization(self):
        """Test GUID type initialization."""
        guid_type = GUID()
        assert guid_type.cache_ok is True

    def test_load_dialect_impl_postgresql(self):
        """Test dialect implementation loading for PostgreSQL."""
        guid_type = GUID()

        # Mock PostgreSQL dialect
        mock_dialect = Mock()
        mock_dialect.name = "postgresql"
        mock_uuid_type = Mock()
        mock_dialect.type_descriptor.return_value = mock_uuid_type

        # Mock the postgresql.UUID import
        with pytest.mock.patch("dotmac.core.types.postgresql") as mock_postgresql:
            mock_postgresql.UUID.return_value = "postgresql_uuid_type"
            result = guid_type.load_dialect_impl(mock_dialect)
            assert result == mock_uuid_type
            mock_dialect.type_descriptor.assert_called_once()

    def test_load_dialect_impl_other(self):
        """Test dialect implementation loading for non-PostgreSQL."""
        guid_type = GUID()

        # Mock other dialect
        mock_dialect = Mock()
        mock_dialect.name = "sqlite"
        mock_string_type = Mock()
        mock_dialect.type_descriptor.return_value = mock_string_type

        result = guid_type.load_dialect_impl(mock_dialect)
        assert result == mock_string_type
        mock_dialect.type_descriptor.assert_called_once()

    def test_process_bind_param_none(self):
        """Test processing None bind parameter."""
        guid_type = GUID()
        mock_dialect = Mock()

        result = guid_type.process_bind_param(None, mock_dialect)
        assert result is None

    def test_process_bind_param_postgresql_uuid(self):
        """Test processing UUID bind parameter for PostgreSQL."""
        guid_type = GUID()
        test_uuid = uuid.uuid4()

        mock_dialect = Mock()
        mock_dialect.name = "postgresql"

        result = guid_type.process_bind_param(test_uuid, mock_dialect)
        assert result == str(test_uuid)

    def test_process_bind_param_postgresql_string(self):
        """Test processing string UUID bind parameter for PostgreSQL."""
        guid_type = GUID()
        test_uuid = uuid.uuid4()
        uuid_string = str(test_uuid)

        mock_dialect = Mock()
        mock_dialect.name = "postgresql"

        result = guid_type.process_bind_param(uuid_string, mock_dialect)
        assert result == uuid_string

    def test_process_bind_param_other_uuid(self):
        """Test processing UUID bind parameter for non-PostgreSQL."""
        guid_type = GUID()
        test_uuid = uuid.uuid4()

        mock_dialect = Mock()
        mock_dialect.name = "sqlite"

        result = guid_type.process_bind_param(test_uuid, mock_dialect)
        assert result == str(test_uuid)

    def test_process_bind_param_other_string(self):
        """Test processing string UUID bind parameter for non-PostgreSQL."""
        guid_type = GUID()
        test_uuid = uuid.uuid4()
        uuid_string = str(test_uuid)

        mock_dialect = Mock()
        mock_dialect.name = "sqlite"

        result = guid_type.process_bind_param(uuid_string, mock_dialect)
        assert result == uuid_string

    def test_process_bind_param_other_invalid_string(self):
        """Test processing invalid string UUID bind parameter for non-PostgreSQL."""
        guid_type = GUID()
        invalid_uuid = "not-a-uuid"

        mock_dialect = Mock()
        mock_dialect.name = "sqlite"

        with pytest.raises(ValueError):
            guid_type.process_bind_param(invalid_uuid, mock_dialect)

    def test_process_result_value_none(self):
        """Test processing None result value."""
        guid_type = GUID()
        mock_dialect = Mock()

        result = guid_type.process_result_value(None, mock_dialect)
        assert result is None

    def test_process_result_value_uuid(self):
        """Test processing UUID result value."""
        guid_type = GUID()
        test_uuid = uuid.uuid4()
        mock_dialect = Mock()

        result = guid_type.process_result_value(test_uuid, mock_dialect)
        assert result == test_uuid
        assert isinstance(result, uuid.UUID)

    def test_process_result_value_string(self):
        """Test processing string UUID result value."""
        guid_type = GUID()
        test_uuid = uuid.uuid4()
        uuid_string = str(test_uuid)
        mock_dialect = Mock()

        result = guid_type.process_result_value(uuid_string, mock_dialect)
        assert result == test_uuid
        assert isinstance(result, uuid.UUID)

    def test_process_result_value_invalid_string(self):
        """Test processing invalid string UUID result value."""
        guid_type = GUID()
        invalid_uuid = "not-a-uuid"
        mock_dialect = Mock()

        with pytest.raises(ValueError):
            guid_type.process_result_value(invalid_uuid, mock_dialect)

    def test_guid_roundtrip_postgresql(self):
        """Test GUID roundtrip for PostgreSQL."""
        guid_type = GUID()
        test_uuid = uuid.uuid4()

        # Mock PostgreSQL dialect
        mock_dialect = Mock()
        mock_dialect.name = "postgresql"

        # Process bind parameter
        bound_value = guid_type.process_bind_param(test_uuid, mock_dialect)
        assert bound_value == str(test_uuid)

        # Process result value
        result_value = guid_type.process_result_value(bound_value, mock_dialect)
        assert result_value == test_uuid
        assert isinstance(result_value, uuid.UUID)

    def test_guid_roundtrip_other(self):
        """Test GUID roundtrip for non-PostgreSQL."""
        guid_type = GUID()
        test_uuid = uuid.uuid4()

        # Mock other dialect
        mock_dialect = Mock()
        mock_dialect.name = "sqlite"

        # Process bind parameter
        bound_value = guid_type.process_bind_param(test_uuid, mock_dialect)
        assert bound_value == str(test_uuid)

        # Process result value
        result_value = guid_type.process_result_value(bound_value, mock_dialect)
        assert result_value == test_uuid
        assert isinstance(result_value, uuid.UUID)

    def test_guid_with_different_uuid_formats(self):
        """Test GUID with different UUID formats."""
        guid_type = GUID()
        mock_dialect = Mock()
        mock_dialect.name = "sqlite"

        # Test different UUID formats
        test_cases = [
            uuid.uuid4(),  # Random UUID
            uuid.uuid1(),  # Time-based UUID
            uuid.uuid5(uuid.NAMESPACE_DNS, "example.com"),  # Name-based UUID
        ]

        for test_uuid in test_cases:
            # Roundtrip test
            bound_value = guid_type.process_bind_param(test_uuid, mock_dialect)
            result_value = guid_type.process_result_value(bound_value, mock_dialect)

            assert result_value == test_uuid
            assert isinstance(result_value, uuid.UUID)

    def test_guid_string_normalization(self):
        """Test GUID string normalization."""
        guid_type = GUID()
        test_uuid = uuid.uuid4()
        mock_dialect = Mock()
        mock_dialect.name = "sqlite"

        # Test with different string formats
        formats = [
            str(test_uuid).upper(),
            str(test_uuid).lower(),
            str(test_uuid),
        ]

        for uuid_string in formats:
            result = guid_type.process_result_value(uuid_string, mock_dialect)
            assert result == test_uuid
            assert isinstance(result, uuid.UUID)
