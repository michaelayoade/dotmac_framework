"""
Unit tests for dotmac_shared_core.common module.
"""

from dotmac_shared_core.common import ids, paths, time


class TestCommonModuleImports:
    """Test that common module imports are working correctly."""

    def test_ids_module_available(self):
        """Test that ids module is available."""
        assert hasattr(ids, 'new_uuid')
        assert hasattr(ids, 'new_ulid')
        assert callable(ids.new_uuid)
        assert callable(ids.new_ulid)

    def test_paths_module_available(self):
        """Test that paths module is available."""
        assert hasattr(paths, 'safe_join')
        assert callable(paths.safe_join)

    def test_time_module_available(self):
        """Test that time module is available."""
        assert hasattr(time, 'utcnow')
        assert hasattr(time, 'to_utc')
        assert hasattr(time, 'isoformat')
        assert callable(time.utcnow)
        assert callable(time.to_utc)
        assert callable(time.isoformat)

    def test_module_functionality_integration(self):
        """Test basic functionality integration across common modules."""
        # Generate a UUID using ids module
        new_id = ids.new_uuid()
        assert new_id is not None

        # Get current time using time module
        now = time.utcnow()
        assert now is not None

        # Use safe_join from paths module
        from pathlib import Path
        safe_path = paths.safe_join(Path("/tmp"), "test")
        assert safe_path is not None


class TestCommonModuleAll:
    """Test __all__ exports from common module."""

    def test_all_exports_available(self):
        """Test that all declared exports are available."""
        from dotmac_shared_core.common import __all__

        expected_exports = ["ids", "paths", "time"]
        assert __all__ == expected_exports

        # Verify each export is actually available
        import dotmac_shared_core.common as common_module
        for export_name in expected_exports:
            assert hasattr(common_module, export_name)
