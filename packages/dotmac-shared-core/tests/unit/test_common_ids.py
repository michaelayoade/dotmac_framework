"""
Unit tests for dotmac_shared_core.common.ids module.
"""

import uuid

from dotmac_shared_core.common.ids import new_ulid, new_uuid


class TestNewUuid:
    """Test the new_uuid function."""

    def test_returns_uuid_object(self):
        """Test that new_uuid returns a UUID object."""
        result = new_uuid()
        assert isinstance(result, uuid.UUID)

    def test_returns_version_4_uuid(self):
        """Test that new_uuid returns a version 4 (random) UUID."""
        result = new_uuid()
        assert result.version == 4

    def test_generates_unique_ids(self):
        """Test that new_uuid generates unique IDs."""
        # Generate multiple UUIDs and ensure they're all unique
        uuids = [new_uuid() for _ in range(100)]

        # Convert to set to remove duplicates, should be same length
        unique_uuids = set(uuids)
        assert len(unique_uuids) == len(uuids)

    def test_string_representation(self):
        """Test UUID string representation format."""
        result = new_uuid()
        uuid_str = str(result)

        # UUID string should be 36 characters (32 hex + 4 hyphens)
        assert len(uuid_str) == 36

        # Should have hyphens in the right places
        assert uuid_str[8] == "-"
        assert uuid_str[13] == "-"
        assert uuid_str[18] == "-"
        assert uuid_str[23] == "-"

    def test_hex_format(self):
        """Test UUID hex representation."""
        result = new_uuid()
        hex_str = result.hex

        # Hex representation should be 32 characters
        assert len(hex_str) == 32

        # Should be valid hex
        int(hex_str, 16)  # Will raise ValueError if not valid hex

    def test_multiple_calls_different_results(self):
        """Test that multiple calls return different UUIDs."""
        uuid1 = new_uuid()
        uuid2 = new_uuid()
        uuid3 = new_uuid()

        assert uuid1 != uuid2
        assert uuid2 != uuid3
        assert uuid1 != uuid3


class TestNewUlid:
    """Test the new_ulid function (stub implementation)."""

    def test_returns_string(self):
        """Test that new_ulid returns a string."""
        result = new_ulid()
        assert isinstance(result, str)

    def test_returns_uuid_format(self):
        """Test that new_ulid returns UUID format (stub implementation)."""
        result = new_ulid()

        # Current stub implementation returns UUID string format
        assert len(result) == 36

        # Should have hyphens in UUID positions
        assert result[8] == "-"
        assert result[13] == "-"
        assert result[18] == "-"
        assert result[23] == "-"

    def test_generates_unique_ids(self):
        """Test that new_ulid generates unique IDs."""
        # Generate multiple ULIDs and ensure they're all unique
        ulids = [new_ulid() for _ in range(100)]

        # Convert to set to remove duplicates, should be same length
        unique_ulids = set(ulids)
        assert len(unique_ulids) == len(ulids)

    def test_valid_uuid_format(self):
        """Test that returned string is valid UUID format."""
        result = new_ulid()

        # Should be parseable as UUID (since it's a UUID stub)
        parsed_uuid = uuid.UUID(result)
        assert str(parsed_uuid) == result

    def test_multiple_calls_different_results(self):
        """Test that multiple calls return different ULIDs."""
        ulid1 = new_ulid()
        ulid2 = new_ulid()
        ulid3 = new_ulid()

        assert ulid1 != ulid2
        assert ulid2 != ulid3
        assert ulid1 != ulid3

    def test_stub_implementation_note(self):
        """Test to document the stub implementation."""
        # This test documents that new_ulid is currently a stub
        # In a real ULID implementation, this would be 26 characters
        # and would have lexicographic sorting properties
        result = new_ulid()

        # Current implementation returns UUID format
        assert len(result) == 36  # UUID format, not 26-char ULID

        # Would be sortable in a real implementation
        # For now, just verify it's a string
        assert isinstance(result, str)


class TestIdFunctionIntegration:
    """Integration tests for ID generation functions."""

    def test_uuid_and_ulid_different(self):
        """Test that UUID and ULID functions return different formats."""
        uuid_result = new_uuid()
        ulid_result = new_ulid()

        # UUID is UUID object, ULID is string
        assert isinstance(uuid_result, uuid.UUID)
        assert isinstance(ulid_result, str)

        # They should not be equal when converted to string
        assert str(uuid_result) != ulid_result

    def test_id_generation_performance(self):
        """Test that ID generation is reasonably fast."""
        import time

        # Generate 1000 UUIDs and measure time
        start_time = time.time()
        for _ in range(1000):
            new_uuid()
        uuid_time = time.time() - start_time

        # Generate 1000 ULIDs and measure time
        start_time = time.time()
        for _ in range(1000):
            new_ulid()
        ulid_time = time.time() - start_time

        # Both should complete in reasonable time (< 1 second)
        assert uuid_time < 1.0
        assert ulid_time < 1.0

    def test_concurrent_id_generation(self):
        """Test ID generation works correctly with concurrent access."""
        import threading

        results = []

        def generate_ids():
            thread_ids = []
            for _ in range(50):
                thread_ids.append(str(new_uuid()))
                thread_ids.append(new_ulid())
            results.extend(thread_ids)

        # Create multiple threads generating IDs
        threads = []
        for _ in range(4):
            thread = threading.Thread(target=generate_ids)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # All IDs should be unique
        unique_results = set(results)
        assert len(unique_results) == len(results)

        # Should have generated correct number of IDs
        assert len(results) == 4 * 50 * 2  # 4 threads * 50 iterations * 2 IDs
