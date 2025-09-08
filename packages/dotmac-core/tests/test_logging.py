"""
Test cases for DotMac Core logging functionality.
"""

from unittest.mock import Mock, patch

import pytest

from dotmac.core.logging import get_logger


class TestLogging:
    """Test logging functionality."""

    def test_get_logger_returns_logger(self):
        """Test get_logger returns a logger instance."""
        logger = get_logger(__name__)
        assert logger is not None
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "debug")

    def test_get_logger_with_different_names(self):
        """Test get_logger with different module names."""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")

        assert logger1 is not None
        assert logger2 is not None
        # Loggers with different names should be different instances
        assert logger1 != logger2

    def test_get_logger_same_name_returns_same_logger(self):
        """Test get_logger returns same logger for same name."""
        logger1 = get_logger("same_module")
        logger2 = get_logger("same_module")

        # Should return the same logger instance
        assert logger1 is logger2

    def test_logger_has_expected_methods(self):
        """Test logger has expected logging methods."""
        logger = get_logger(__name__)

        # Check all standard logging methods exist
        methods = ["debug", "info", "warning", "error", "critical"]
        for method in methods:
            assert hasattr(logger, method)
            assert callable(getattr(logger, method))

    @patch("dotmac.core.logging.structlog")
    def test_get_logger_uses_structlog(self, mock_structlog):
        """Test get_logger uses structlog."""
        mock_logger = Mock()
        mock_structlog.get_logger.return_value = mock_logger

        logger = get_logger("test_module")

        mock_structlog.get_logger.assert_called_once_with("test_module")
        assert logger == mock_logger

    def test_logger_basic_functionality(self):
        """Test logger basic functionality."""
        logger = get_logger(__name__)

        # These should not raise exceptions
        try:
            logger.info("Test info message")
            logger.error("Test error message")
            logger.warning("Test warning message")
            logger.debug("Test debug message")
        except Exception as e:
            pytest.fail(f"Logger should not raise exception: {e}")

    def test_logger_with_extra_data(self):
        """Test logger with extra data."""
        logger = get_logger(__name__)

        # Should be able to log with extra data (structured logging)
        try:
            logger.info("Test message with extra data", user_id="123", action="test")
        except Exception as e:
            pytest.fail(f"Logger should handle extra data: {e}")

    def test_logger_with_none_name(self):
        """Test get_logger with None name."""
        # Should handle None gracefully
        logger = get_logger(None)
        assert logger is not None

    def test_logger_with_empty_string_name(self):
        """Test get_logger with empty string name."""
        logger = get_logger("")
        assert logger is not None

    def test_logger_consistency(self):
        """Test logger consistency across calls."""
        # Multiple calls should return consistent loggers
        loggers = []
        for i in range(5):
            logger = get_logger(f"test_module_{i}")
            loggers.append(logger)

            # Each should be a valid logger
            assert logger is not None
            assert hasattr(logger, "info")

        # Same name should return same logger
        logger_a1 = get_logger("consistent_test")
        logger_a2 = get_logger("consistent_test")
        assert logger_a1 is logger_a2
