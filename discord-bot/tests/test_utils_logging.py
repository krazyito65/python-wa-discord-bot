"""
Unit tests for logging utility functions.

This module tests the logging configuration and utility functions
that can be tested without Discord client integration.
"""

import logging
import unittest
from unittest.mock import patch

from utils.logging import get_logger, setup_logging


class TestLoggingUtils(unittest.TestCase):
    """Test cases for logging utilities."""

    def test_get_logger_returns_logger(self):
        """Test that get_logger returns a logger instance."""
        logger = get_logger("test_module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"

    def test_get_logger_different_modules(self):
        """Test that different modules get different logger instances."""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")

        assert logger1.name != logger2.name
        assert logger1.name == "module1"
        assert logger2.name == "module2"

    @patch('utils.logging.logging.basicConfig')
    def test_setup_logging_dev_environment(self, mock_basic_config):
        """Test logging setup for development environment."""
        setup_logging("dev")

        # Should call basicConfig for dev environment
        mock_basic_config.assert_called_once()
        call_args = mock_basic_config.call_args[1]
        assert call_args['level'] == logging.DEBUG

    @patch('utils.logging.logging.basicConfig')
    def test_setup_logging_prod_environment(self, mock_basic_config):
        """Test logging setup for production environment."""
        setup_logging("prod")

        # Should call basicConfig for prod environment
        mock_basic_config.assert_called_once()
        call_args = mock_basic_config.call_args[1]
        assert call_args['level'] == logging.INFO

    @patch('utils.logging.logging.basicConfig')
    def test_setup_logging_default_environment(self, mock_basic_config):
        """Test logging setup with default environment."""
        setup_logging()

        # Should call basicConfig with default settings
        mock_basic_config.assert_called_once()

    def test_logger_hierarchy(self):
        """Test that loggers follow Python's hierarchy."""
        parent_logger = get_logger("parent")
        child_logger = get_logger("parent.child")

        assert child_logger.name.startswith(parent_logger.name)

    def test_get_logger_with_empty_name(self):
        """Test get_logger behavior with empty module name."""
        logger = get_logger("")
        assert isinstance(logger, logging.Logger)

    def test_get_logger_with_none_name(self):
        """Test get_logger behavior with None module name."""
        # This should handle the case gracefully
        try:
            logger = get_logger(None)
            assert isinstance(logger, logging.Logger)
        except (TypeError, AttributeError):
            # It's acceptable if this raises an error for None input
            pass


if __name__ == "__main__":
    unittest.main()
