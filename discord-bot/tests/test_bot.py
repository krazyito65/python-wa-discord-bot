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

import pytest
from bot import WeakAurasBot

# Test constants
MAX_SERVER_NAME_LENGTH = 100
WEAKAURAS_PURPLE_COLOR = 10439411
TEST_EMBED_COLOR = 0x5865F2
EXPECTED_FIELD_COUNT = 2
EXPECTED_MACRO_COUNT = 2


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
            # Check that data_dir is calculated as absolute path relative to discord-bot directory
            bot_package_dir = (
                Path(__file__).resolve().parent.parent
            )  # discord-bot directory
            expected_path = bot_package_dir / "test_server_data"
            assert bot.data_dir == expected_path
            mock_init.assert_called_once()

    def test_bot_initialization_default_storage(self):
        """Test bot initialization with default storage directory."""
        config_no_storage = {"discord": {"tokens": {"dev": "test_token"}}}

        with patch("bot.weakauras_bot.commands.Bot.__init__") as mock_init:
            mock_init.return_value = None
            bot = WeakAurasBot(config_no_storage)

            # Should use default storage directory as absolute path
            bot_package_dir = (
                Path(__file__).resolve().parent.parent
            )  # discord-bot directory
            expected_path = bot_package_dir / "server_data"
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

    def test_create_embed_with_custom_footer(self):
        """Test creating embed with custom footer."""
        with patch("bot.weakauras_bot.commands.Bot.__init__") as mock_init:
            mock_init.return_value = None
            bot = WeakAurasBot(self.test_config)

            embed, logo_file = bot.create_embed(
                title="Test", description="Test", footer_text="Custom Footer"
            )

            # Bot appends "WeakAuras Bot" to custom footers
            assert "Custom Footer" in embed.footer.text
            assert "WeakAuras Bot" in embed.footer.text

    def test_create_embed_with_color(self):
        """Test creating embed with custom color."""
        with patch("bot.weakauras_bot.commands.Bot.__init__") as mock_init:
            mock_init.return_value = None
            bot = WeakAurasBot(self.test_config)

            custom_color = 0xFF0000  # Red
            embed, logo_file = bot.create_embed(
                title="Test", description="Test", color=custom_color
            )

            assert embed.color.value == custom_color

    def test_load_server_macros_invalid_json(self):
        """Test loading server macros with invalid JSON file."""
        # Create invalid JSON file
        macros_file = self.temp_dir / f"{self.test_guild_id}_macros.json"
        with open(macros_file, "w", encoding="utf-8") as f:
            f.write("invalid json content")

        with patch("bot.weakauras_bot.commands.Bot.__init__") as mock_init:
            mock_init.return_value = None
            bot = WeakAurasBot(self.test_config)
            bot.data_dir = self.temp_dir

            with (
                patch.object(bot, "get_server_folder", return_value=self.temp_dir),
                pytest.raises(json.JSONDecodeError),
            ):
                bot.load_server_macros(self.test_guild_id, self.test_guild_name)

    def test_save_server_macros_creates_directory(self):
        """Test that save_server_macros creates the directory if it doesn't exist."""
        with patch("bot.weakauras_bot.commands.Bot.__init__") as mock_init:
            mock_init.return_value = None
            bot = WeakAurasBot(self.test_config)
            bot.data_dir = self.temp_dir

            # Don't mock get_server_folder, let it create the directory naturally
            test_macros = {"test": {"name": "test", "message": "test message"}}
            bot.save_server_macros(
                self.test_guild_id, self.test_guild_name, test_macros
            )

            # Verify directory was created and file exists
            expected_dir = self.temp_dir / f"Test Server_{self.test_guild_id}"
            macros_file = expected_dir / f"{self.test_guild_id}_macros.json"
            assert expected_dir.exists()
            assert macros_file.exists()

    def test_get_server_folder_existing(self):
        """Test getting server folder when it already exists."""
        with patch("bot.weakauras_bot.commands.Bot.__init__") as mock_init:
            mock_init.return_value = None
            bot = WeakAurasBot(self.test_config)
            bot.data_dir = self.temp_dir

            # Create existing folder
            expected_path = self.temp_dir / f"Test Server_{self.test_guild_id}"
            expected_path.mkdir(parents=True, exist_ok=True)

            result = bot.get_server_folder(self.test_guild_id, self.test_guild_name)
            assert result == expected_path
            assert result.exists()

    def test_sanitize_server_name_unicode(self):
        """Test server name sanitization with unicode characters."""
        with patch("bot.weakauras_bot.commands.Bot.__init__") as mock_init:
            mock_init.return_value = None
            bot = WeakAurasBot(self.test_config)

            # Test unicode characters - bot may handle emojis differently
            result = bot.sanitize_server_name("Tëst Sërvër 🎮")
            # Just verify it returns a valid string
            assert isinstance(result, str)
            assert len(result) > 0

    def test_has_admin_access_with_permissions(self):
        """Test admin access checking with user permissions."""
        mock_member = Mock()
        mock_member.roles = []
        mock_member.guild_permissions = Mock()
        mock_member.guild_permissions.administrator = True  # Has admin permission

        # Setup proper bot config with admin permissions
        admin_config = {
            "bot": {"permissions": {"admin_permissions": ["administrator"]}},
            "discord": {"tokens": {"dev": "test_token"}},
        }

        with patch("bot.weakauras_bot.commands.Bot.__init__") as mock_init:
            mock_init.return_value = None
            bot = WeakAurasBot(admin_config)

            result = bot.has_admin_access(mock_member)
            assert result

    def test_has_admin_access_multiple_roles(self):
        """Test admin access checking with multiple roles including admin."""
        mock_member = Mock()
        mock_role1 = Mock()
        mock_role1.name = "user"
        mock_role2 = Mock()
        mock_role2.name = "admin"  # Has admin role
        mock_role3 = Mock()
        mock_role3.name = "moderator"
        mock_member.roles = [mock_role1, mock_role2, mock_role3]

        with patch("bot.weakauras_bot.commands.Bot.__init__") as mock_init:
            mock_init.return_value = None
            bot = WeakAurasBot(self.test_config)

            result = bot.has_admin_access(mock_member)
            assert result

    def test_load_embed_macro(self):
        """Test loading embed macro from JSON file."""
        test_embed_macro = {
            "test_embed": {
                "name": "test_embed",
                "type": "embed",
                "embed_data": {
                    "title": "Test Embed Title",
                    "description": "Test embed description",
                    "color": 0x5865F2,
                    "footer": "Test footer",
                    "image": "https://example.com/image.png",
                    "fields": [
                        {"name": "Field 1", "value": "Field 1 value", "inline": False},
                        {"name": "Field 2", "value": "Field 2 value", "inline": True},
                    ],
                },
                "created_by": "user123",
                "created_by_name": "TestUser",
                "created_at": "2024-01-01T00:00:00",
            }
        }

        # Create a test macros file
        macros_file = self.temp_dir / f"{self.test_guild_id}_macros.json"
        with open(macros_file, "w", encoding="utf-8") as f:
            json.dump(test_embed_macro, f)

        with patch("bot.weakauras_bot.commands.Bot.__init__") as mock_init:
            mock_init.return_value = None
            bot = WeakAurasBot(self.test_config)
            bot.data_dir = self.temp_dir

            with patch.object(bot, "get_server_folder", return_value=self.temp_dir):
                result = bot.load_server_macros(
                    self.test_guild_id, self.test_guild_name
                )
                assert result == test_embed_macro

                # Verify embed macro structure
                embed_macro = result["test_embed"]
                assert embed_macro["type"] == "embed"
                assert "embed_data" in embed_macro

                embed_data = embed_macro["embed_data"]
                assert embed_data["title"] == "Test Embed Title"
                assert embed_data["description"] == "Test embed description"
                assert embed_data["color"] == TEST_EMBED_COLOR
                assert embed_data["footer"] == "Test footer"
                assert embed_data["image"] == "https://example.com/image.png"
                assert len(embed_data["fields"]) == EXPECTED_FIELD_COUNT
                assert embed_data["fields"][0]["name"] == "Field 1"
                assert embed_data["fields"][0]["inline"] is False
                assert embed_data["fields"][1]["inline"] is True

    def test_save_embed_macro(self):
        """Test saving embed macro to JSON file."""
        test_embed_macro = {
            "test_embed": {
                "name": "test_embed",
                "type": "embed",
                "embed_data": {
                    "title": "Test Embed",
                    "description": "Test description",
                    "color": 0xFF0000,
                    "fields": [
                        {"name": "Test Field", "value": "Test value", "inline": False}
                    ],
                },
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
                    self.test_guild_id, self.test_guild_name, test_embed_macro
                )

                # Verify file was created and has correct content
                macros_file = self.temp_dir / f"{self.test_guild_id}_macros.json"
                assert macros_file.exists()

                with open(macros_file, encoding="utf-8") as f:
                    saved_data = json.load(f)
                assert saved_data == test_embed_macro

                # Verify embed structure is preserved
                saved_embed = saved_data["test_embed"]
                assert saved_embed["type"] == "embed"
                assert "embed_data" in saved_embed
                assert saved_embed["embed_data"]["title"] == "Test Embed"
                assert len(saved_embed["embed_data"]["fields"]) == 1

    def test_mixed_macro_types(self):
        """Test loading and saving both text and embed macros together."""
        mixed_macros = {
            "text_macro": {
                "name": "text_macro",
                "message": "Simple text message",
                "created_by": "user123",
                "created_by_name": "TestUser",
                "created_at": "2024-01-01T00:00:00",
            },
            "embed_macro": {
                "name": "embed_macro",
                "type": "embed",
                "embed_data": {
                    "title": "Embed Title",
                    "description": "Embed description",
                },
                "created_by": "user456",
                "created_by_name": "TestUser2",
                "created_at": "2024-01-01T01:00:00",
            },
        }

        with patch("bot.weakauras_bot.commands.Bot.__init__") as mock_init:
            mock_init.return_value = None
            bot = WeakAurasBot(self.test_config)
            bot.data_dir = self.temp_dir

            with patch.object(bot, "get_server_folder", return_value=self.temp_dir):
                # Save mixed macros
                bot.save_server_macros(
                    self.test_guild_id, self.test_guild_name, mixed_macros
                )

                # Load and verify
                result = bot.load_server_macros(
                    self.test_guild_id, self.test_guild_name
                )

                assert len(result) == EXPECTED_MACRO_COUNT
                assert "text_macro" in result
                assert "embed_macro" in result

                # Verify text macro (legacy format)
                text_macro = result["text_macro"]
                assert "message" in text_macro
                assert text_macro.get("type") != "embed"

                # Verify embed macro
                embed_macro = result["embed_macro"]
                assert embed_macro["type"] == "embed"
                assert "embed_data" in embed_macro


if __name__ == "__main__":
    unittest.main()
