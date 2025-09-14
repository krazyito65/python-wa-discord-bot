"""
Unit tests for Django permissions integration utility.

This module tests the Django database integration functionality
used by the Discord bot to check permissions.
"""

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import discord
from utils.django_permissions import (
    get_django_database_path,
    get_permission_error_message,
    get_server_permission_config,
)


class TestDjangoPermissions(unittest.TestCase):
    """Test cases for Django permissions integration."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_guild_id = 123456789
        self.mock_member = Mock(spec=discord.Member)
        self.mock_member.id = 12345
        self.mock_member.roles = []
        self.mock_member.guild_permissions = Mock()
        self.mock_member.guild_permissions.administrator = False

    def test_get_django_database_path_default(self):
        """Test getting Django database path with default fallback."""
        with patch("pathlib.Path.exists", return_value=False):
            result = get_django_database_path()
            # Should return the expanded default path
            expected = str(Path("~/weakauras-bot-data/statistics.db").expanduser())
            assert result == expected

    def test_get_django_database_path_with_config(self):
        """Test getting Django database path from config file."""
        test_config = {"django": {"database_url": "sqlite:///~/test-data/test.db"}}

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("builtins.open", create=True),
            patch("yaml.safe_load", return_value=test_config),
        ):
            result = get_django_database_path()
            expected = str(Path("~/test-data/test.db").expanduser())
            assert result == expected

    def test_get_django_database_path_exception_handling(self):
        """Test that database path function handles exceptions gracefully."""
        with patch("pathlib.Path.exists", side_effect=Exception("Test error")):
            result = get_django_database_path()
            # Should still return default path
            expected = str(Path("~/weakauras-bot-data/statistics.db").expanduser())
            assert result == expected

    def test_get_server_permission_config_no_database(self):
        """Test getting server permission config when database doesn't exist."""
        with patch(
            "utils.django_permissions.get_django_database_path",
            return_value="/nonexistent/path.db",
        ):
            result = get_server_permission_config(self.test_guild_id)

            # Should return None when database is not accessible
            assert result is None

    def test_get_permission_error_message_no_config(self):
        """Test getting permission error message when no config is provided."""
        result = get_permission_error_message("create_macros", None)

        # Should return a default error message
        assert isinstance(result, str)
        assert "permission" in result.lower()

    def test_get_permission_error_message_with_config(self):
        """Test getting permission error message with config."""
        mock_config = Mock()
        mock_config.create_macros = "admin_only"

        result = get_permission_error_message("create_macros", mock_config)

        # Should return a descriptive error message
        assert isinstance(result, str)
        # Just verify it's a non-empty string with permission context
        assert len(result) > 0
        assert "permission" in result.lower()

    def test_permission_functions_exist(self):
        """Test that all required permission functions exist and are callable."""
        # Test that the main functions we need exist
        assert callable(get_django_database_path)
        assert callable(get_server_permission_config)
        assert callable(get_permission_error_message)

    def test_get_django_database_path_sqlite_prefix(self):
        """Test database path extraction from different SQLite URL formats."""
        test_configs = [
            {"django": {"database_url": "sqlite:///relative/path/db.sqlite3"}},
            {"django": {"database_url": "sqlite:///absolute/path/db.sqlite3"}},
        ]

        for config in test_configs:
            with (
                patch("pathlib.Path.exists", return_value=True),
                patch("builtins.open"),
                patch("yaml.safe_load", return_value=config),
            ):
                result = get_django_database_path()
                assert isinstance(result, str)
                # Should not contain the sqlite:/// prefix
                assert "sqlite:///" not in result

    def test_get_django_database_path_yaml_parsing(self):
        """Test that function properly parses YAML configuration."""
        test_config = {"django": {"database_url": "sqlite:///~/test-db/test.db"}}

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("builtins.open", create=True),
            patch("yaml.safe_load", return_value=test_config),
        ):
            result = get_django_database_path()
            # Should process the config and return a path
            assert isinstance(result, str)
            assert "test-db" in result

    def test_get_django_database_path_non_sqlite(self):
        """Test behavior with non-SQLite database URLs."""
        test_config = {"django": {"database_url": "postgresql://localhost/test"}}

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("builtins.open"),
            patch("yaml.safe_load", return_value=test_config),
        ):
            result = get_django_database_path()
            # Should fall back to default path for non-SQLite URLs
            expected = str(Path("~/weakauras-bot-data/statistics.db").expanduser())
            assert result == expected

    def test_get_permission_error_message_different_permissions(self):
        """Test permission error messages for different permission types."""
        mock_config = Mock()
        mock_config.create_macros = "everyone"
        mock_config.edit_macros = "trusted_users"
        mock_config.delete_macros = "admin_only"

        # Test different permission types
        permission_types = ["create_macros", "edit_macros", "delete_macros"]

        for perm_type in permission_types:
            result = get_permission_error_message(perm_type, mock_config)
            assert isinstance(result, str)
            assert len(result) > 0

    def test_get_permission_error_message_missing_attribute(self):
        """Test permission error message when config lacks the requested permission."""
        mock_config = Mock()
        # Don't set any permission attributes

        result = get_permission_error_message("nonexistent_permission", mock_config)
        assert isinstance(result, str)
        assert len(result) > 0
        assert "permission" in result.lower()


if __name__ == "__main__":
    unittest.main()
