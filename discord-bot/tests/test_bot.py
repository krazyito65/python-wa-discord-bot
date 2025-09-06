"""
Unit tests for WeakAuras Discord Bot core functionality.

This module tests the main bot class, configuration loading,
and core bot operations.
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from bot import WeakAurasBot

# Test constants
MAX_SERVER_NAME_LENGTH = 100
WEAKAURAS_PURPLE_COLOR = 10439411


class TestWeakAurasBot(unittest.TestCase):
    """Test cases for the WeakAurasBot class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.test_config = {
            "storage": {"data_directory": "test_server_data"},
            "bot": {"permissions": {"admin_roles": ["admin"]}},
            "discord": {"tokens": {"dev": "test_token"}},
        }
        self.temp_dir = Path(tempfile.mkdtemp())
        self.test_guild_id = 123456789
        self.test_guild_name = "Test Server"

    def tearDown(self):
        """Clean up after each test method."""
        # Clean up temp directory
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_bot_initialization(self):
        """Test bot initialization with valid config."""
        with patch("bot.weakauras_bot.commands.Bot.__init__") as mock_init:
            mock_init.return_value = None
            bot = WeakAurasBot(self.test_config)

            assert bot.config == self.test_config
            # Check that data_dir is set from config
            expected_path = Path("test_server_data")
            assert bot.data_dir == expected_path
            mock_init.assert_called_once()

    def test_bot_initialization_default_storage(self):
        """Test bot initialization with default storage directory."""
        config_no_storage = {"discord": {"tokens": {"dev": "test_token"}}}

        with patch("bot.weakauras_bot.commands.Bot.__init__") as mock_init:
            mock_init.return_value = None
            bot = WeakAurasBot(config_no_storage)

            # Should use default storage directory
            expected_path = Path("server_data")
            assert bot.data_dir == expected_path

    def test_sanitize_server_name(self):
        """Test server name sanitization for filesystem usage."""
        with patch("bot.weakauras_bot.commands.Bot.__init__") as mock_init:
            mock_init.return_value = None
            bot = WeakAurasBot(self.test_config)

            # Test normal name (spaces should be preserved in actual implementation)
            result = bot.sanitize_server_name("Test Server")
            assert result == "Test Server"

            # Test name with invalid characters
            result = bot.sanitize_server_name("Test<>Server:|?*")
            assert result == "Test_Server_"

            # Test empty name
            result = bot.sanitize_server_name("")
            assert result == "unknown_server"

            # Test very long name (should be truncated to max length)
            long_name = "a" * 150
            result = bot.sanitize_server_name(long_name)
            assert len(result) == MAX_SERVER_NAME_LENGTH

    def test_get_server_folder_new(self):
        """Test getting server folder when none exists."""
        with patch("bot.weakauras_bot.commands.Bot.__init__") as mock_init:
            mock_init.return_value = None
            bot = WeakAurasBot(self.test_config)

            # Use a fresh temporary directory
            test_data_dir = Path(tempfile.mkdtemp())
            bot.data_dir = test_data_dir

            try:
                result = bot.get_server_folder(self.test_guild_id, self.test_guild_name)

                expected_path = test_data_dir / f"Test Server_{self.test_guild_id}"
                assert result == expected_path
                assert result.exists()
            finally:
                # Clean up the test directory
                shutil.rmtree(test_data_dir, ignore_errors=True)

    def test_load_server_macros_no_file(self):
        """Test loading server macros when no file exists."""
        with patch("bot.weakauras_bot.commands.Bot.__init__") as mock_init:
            mock_init.return_value = None
            bot = WeakAurasBot(self.test_config)
            bot.data_dir = self.temp_dir

            with patch.object(bot, "get_server_folder", return_value=self.temp_dir):
                result = bot.load_server_macros(
                    self.test_guild_id, self.test_guild_name
                )
                assert result == {}

    def test_load_server_macros_with_file(self):
        """Test loading server macros when file exists."""
        test_macros = {
            "test_macro": {
                "name": "test_macro",
                "message": "Test message",
                "created_by": "user123",
                "created_by_name": "TestUser",
                "created_at": "2024-01-01T00:00:00",
            }
        }

        # Create a test macros file
        macros_file = self.temp_dir / f"{self.test_guild_id}_macros.json"
        with open(macros_file, "w", encoding="utf-8") as f:
            json.dump(test_macros, f)

        with patch("bot.weakauras_bot.commands.Bot.__init__") as mock_init:
            mock_init.return_value = None
            bot = WeakAurasBot(self.test_config)
            bot.data_dir = self.temp_dir

            with patch.object(bot, "get_server_folder", return_value=self.temp_dir):
                result = bot.load_server_macros(
                    self.test_guild_id, self.test_guild_name
                )
                assert result == test_macros

    def test_save_server_macros(self):
        """Test saving server macros to JSON file."""
        test_macros = {
            "test_macro": {
                "name": "test_macro",
                "message": "Test message",
                "created_by": "user123",
                "created_by_name": "TestUser",
                "created_at": "2024-01-01T00:00:00",
            }
        }

        with patch("bot.weakauras_bot.commands.Bot.__init__") as mock_init:
            mock_init.return_value = None
            bot = WeakAurasBot(self.test_config)
            bot.data_dir = self.temp_dir

            with patch.object(bot, "get_server_folder", return_value=self.temp_dir):
                bot.save_server_macros(
                    self.test_guild_id, self.test_guild_name, test_macros
                )

                # Verify file was created and has correct content
                macros_file = self.temp_dir / f"{self.test_guild_id}_macros.json"
                assert macros_file.exists()

                with open(macros_file, encoding="utf-8") as f:
                    saved_data = json.load(f)
                assert saved_data == test_macros

    def test_has_admin_access_with_role(self):
        """Test admin access checking when user has admin role."""
        mock_member = Mock()
        mock_role = Mock()
        mock_role.name = "admin"
        mock_member.roles = [mock_role]

        with patch("bot.weakauras_bot.commands.Bot.__init__") as mock_init:
            mock_init.return_value = None
            bot = WeakAurasBot(self.test_config)

            result = bot.has_admin_access(mock_member)
            assert result

    def test_has_admin_access_without_role(self):
        """Test admin access checking when user doesn't have admin role."""
        mock_member = Mock()
        mock_role = Mock()
        mock_role.name = "user"
        mock_member.roles = [mock_role]
        mock_member.guild_permissions = Mock()

        with patch("bot.weakauras_bot.commands.Bot.__init__") as mock_init:
            mock_init.return_value = None
            bot = WeakAurasBot(self.test_config)

            result = bot.has_admin_access(mock_member)
            assert not result

    def test_has_admin_access_no_roles(self):
        """Test admin access checking when user has no roles."""
        mock_member = Mock()
        mock_member.roles = []
        mock_member.guild_permissions = Mock()

        with patch("bot.weakauras_bot.commands.Bot.__init__") as mock_init:
            mock_init.return_value = None
            bot = WeakAurasBot(self.test_config)

            result = bot.has_admin_access(mock_member)
            assert not result

    def test_create_embed_basic(self):
        """Test creating basic embed without logo."""
        with patch("bot.weakauras_bot.commands.Bot.__init__") as mock_init:
            mock_init.return_value = None
            bot = WeakAurasBot(self.test_config)

            embed, logo_file = bot.create_embed(
                title="Test Title", description="Test Description"
            )

            assert embed.title == "Test Title"
            assert embed.description == "Test Description"
            assert (
                embed.color.value == WEAKAURAS_PURPLE_COLOR
            )  # Default WeakAuras purple
            assert logo_file is None
            assert embed.footer.text == "WeakAuras Bot"


if __name__ == "__main__":
    unittest.main()
