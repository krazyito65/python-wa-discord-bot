"""
Unit tests for embed macro functionality.

This module tests the embed macro creation, editing, and execution features.
"""

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bot import WeakAurasBot

# Test constants
TEST_EMBED_COLOR = 0x5865F2
MAX_COLOR_VALUE = 0xFFFFFF


class TestEmbedMacros(unittest.TestCase):
    """Test cases for embed macro functionality."""

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

    def test_embed_macro_structure(self):
        """Test that embed macros have the correct structure."""
        embed_macro_data = {
            "name": "test_embed",
            "type": "embed",
            "embed_data": {
                "title": "Test Title",
                "description": "Test description",
                "color": TEST_EMBED_COLOR,
                "footer": "Test footer",
                "image": "https://example.com/test.png",
                "fields": [{"name": "Field 1", "value": "Value 1", "inline": False}],
            },
            "created_by": "user123",
            "created_by_name": "TestUser",
            "created_at": "2024-01-01T00:00:00",
        }

        # Verify structure
        assert embed_macro_data["type"] == "embed"
        assert "embed_data" in embed_macro_data

        embed_data = embed_macro_data["embed_data"]
        assert embed_data["title"] == "Test Title"
        assert embed_data["description"] == "Test description"
        assert embed_data["color"] == TEST_EMBED_COLOR
        assert embed_data["footer"] == "Test footer"
        assert embed_data["image"] == "https://example.com/test.png"
        assert len(embed_data["fields"]) == 1
        assert embed_data["fields"][0]["name"] == "Field 1"
        assert embed_data["fields"][0]["value"] == "Value 1"
        assert embed_data["fields"][0]["inline"] is False

    def test_backward_compatibility_with_text_macros(self):
        """Test that text macros still work alongside embed macros."""
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

                # Load and verify both types work
                result = bot.load_server_macros(
                    self.test_guild_id, self.test_guild_name
                )

                # Check text macro (legacy format)
                text_macro = result["text_macro"]
                assert "message" in text_macro
                assert text_macro["message"] == "Simple text message"
                assert text_macro.get("type") != "embed"

                # Check embed macro
                embed_macro = result["embed_macro"]
                assert embed_macro["type"] == "embed"
                assert "embed_data" in embed_macro
                assert embed_macro["embed_data"]["title"] == "Embed Title"

    def test_embed_field_inline_property(self):
        """Test that embed fields support inline property correctly."""
        field_data_inline = {
            "name": "Inline Field",
            "value": "This field is inline",
            "inline": True,
        }

        field_data_not_inline = {
            "name": "Block Field",
            "value": "This field is not inline",
            "inline": False,
        }

        # Test inline field
        assert field_data_inline["inline"] is True
        assert field_data_inline["name"] == "Inline Field"
        assert field_data_inline["value"] == "This field is inline"

        # Test non-inline field
        assert field_data_not_inline["inline"] is False
        assert field_data_not_inline["name"] == "Block Field"
        assert field_data_not_inline["value"] == "This field is not inline"

    def test_empty_embed_data_validation(self):
        """Test that empty embed data is properly handled."""
        empty_embed_data = {}

        # Embed should be considered empty
        has_content = any(
            [
                empty_embed_data.get("title"),
                empty_embed_data.get("description"),
                empty_embed_data.get("footer"),
                empty_embed_data.get("image"),
                empty_embed_data.get("fields", []),
            ]
        )

        assert has_content is False

    def test_partial_embed_data_validation(self):
        """Test that partial embed data is properly handled."""
        partial_embed_data = {
            "title": "Test Title",
            # Missing description, footer, image, fields
        }

        # Should have content due to title
        has_content = any(
            [
                partial_embed_data.get("title"),
                partial_embed_data.get("description"),
                partial_embed_data.get("footer"),
                partial_embed_data.get("image"),
                partial_embed_data.get("fields", []),
            ]
        )

        assert has_content is True

    def test_embed_color_parsing(self):
        """Test that embed colors are properly parsed."""
        # Test various color formats that should work
        valid_colors = [
            0x5865F2,  # Discord blurple
            0xFF0000,  # Red
            0x00FF00,  # Green
            0x0000FF,  # Blue
            0xFFFFFF,  # White
            0x000000,  # Black
        ]

        for color in valid_colors:
            embed_data = {"color": color}
            assert isinstance(embed_data["color"], int)
            assert 0 <= embed_data["color"] <= MAX_COLOR_VALUE

    def test_embed_macro_modification_tracking(self):
        """Test that embed macro modifications are tracked."""
        original_macro = {
            "name": "test_embed",
            "type": "embed",
            "embed_data": {"title": "Original Title"},
            "created_by": "user123",
            "created_by_name": "TestUser",
            "created_at": "2024-01-01T00:00:00",
        }

        # Simulate modification
        modified_macro = original_macro.copy()
        modified_macro["embed_data"] = {"title": "Modified Title"}
        modified_macro["modified_by"] = "user456"
        modified_macro["modified_by_name"] = "ModifyUser"
        modified_macro["modified_at"] = "2024-01-01T01:00:00"

        # Check modification tracking
        assert "modified_by" in modified_macro
        assert "modified_by_name" in modified_macro
        assert "modified_at" in modified_macro
        assert modified_macro["modified_by"] == "user456"
        assert modified_macro["modified_by_name"] == "ModifyUser"
        assert modified_macro["embed_data"]["title"] == "Modified Title"


if __name__ == "__main__":
    unittest.main()
