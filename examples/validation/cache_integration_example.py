"""
Cache Integration Validation Example

Example script showing how to validate cache integration components.
This should be run from the project root with proper PYTHONPATH.

Usage:
    PYTHONPATH=./src:./packages/dotmac-platform-services/src python examples/validation/cache_integration_example.py
"""

import asyncio
from unittest.mock import Mock

# NOTE: These imports require proper PYTHONPATH setup
try:
    from dotmac_shared.files.cache_integration import (
        CacheServiceFileStorage,
        CacheServiceTemplateStore,
    )
    CACHE_INTEGRATION_AVAILABLE = True
except ImportError:
    print("❌ Cache integration components not available")
    print("   Ensure PYTHONPATH includes required source directories")
    CACHE_INTEGRATION_AVAILABLE = False
async def test_basic_functionality():
    """Test basic cache integration functionality."""

    # Create mock cache service
    cache = Mock()
    cache.set = Mock()
    cache.get = Mock()
    cache.clear = Mock()
    cache.ping = Mock()
    cache.get_stats = Mock()

    # Make async mocks
    cache.set.return_value = True
    cache.get.return_value = None
    cache.clear.return_value = 0
    cache.ping.return_value = True
    cache.get_stats.return_value = {"hit_rate": 0.95}

    # Create components

    template_store = CacheServiceTemplateStore(cache)

    file_storage = CacheServiceFileStorage(cache)

    # Test basic operations

    # Template store operations
    key = template_store._template_key("test", "1.0")
    assert "file_templates:test:1.0" == key

    content_key = template_store._content_key("test", "abc123")
    assert "rendered_content:test:abc123" == content_key

    ctx_hash = template_store._compute_context_hash({"name": "test", "value": 123})
    assert len(ctx_hash) == 16  # Should be 16-char hash

    # File storage operations
    file_key = file_storage._file_key("file-123")
    assert "file_metadata:file-123" == file_key

    access_key = file_storage._access_key("file-123")
    assert "file_access:file-123" == access_key

    return True


def test_imports():
    """Test that all required components can be imported."""

    try:
        from dotmac_shared.files.cache_integration import (
            CacheServiceFileStorage,
            CacheServiceTemplateStore,
            FileServiceCacheIntegrationFactory,
        )

        return True
    except ImportError:
        return False


def main():
    """Run validation tests."""
    success = True

    # Test imports
    if not test_imports():
        success = False

    # Test basic functionality
    try:
        result = asyncio.run(test_basic_functionality())
        if not result:
            success = False
    except Exception:
        success = False

    if success:
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
