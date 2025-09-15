"""Tests for color role command functionality."""

import asyncio
import unittest

import discord
from commands.color_role_commands import (
    find_existing_color_role,
    get_lowest_position,
    hex_to_discord_color,
    is_valid_hex_color,
)

# Test color constants to avoid magic numbers
RED_COLOR = 0xFF0000
GREEN_COLOR = 0x00FF00
BLUE_COLOR = 0x0000FF
TEST_COLOR = 0xABCDEF


class TestColorRoleUtilities(unittest.TestCase):
    """Test utility functions for color role commands."""

    def test_is_valid_hex_color(self):
        """Test hex color validation."""
        # Valid hex colors
        assert is_valid_hex_color("#ff0000")
        assert is_valid_hex_color("ff0000")
        assert is_valid_hex_color("#123ABC")
        assert is_valid_hex_color("123abc")
        assert is_valid_hex_color("#000000")
        assert is_valid_hex_color("ffffff")

        # Invalid hex colors
        assert not is_valid_hex_color("#ff")  # Too short
        assert not is_valid_hex_color("#ff00000")  # Too long
        assert not is_valid_hex_color("#gggggg")  # Invalid characters
        assert not is_valid_hex_color("")  # Empty string
        assert not is_valid_hex_color("#ff-000")  # Invalid character
        assert not is_valid_hex_color("ff00zz")  # Invalid character

    def test_hex_to_discord_color(self):
        """Test hex to Discord color conversion."""
        # Test with # prefix
        color1 = hex_to_discord_color("#ff0000")
        assert color1.value == RED_COLOR

        # Test without # prefix
        color2 = hex_to_discord_color("00ff00")
        assert color2.value == GREEN_COLOR

        # Test uppercase
        color3 = hex_to_discord_color("#0000FF")
        assert color3.value == BLUE_COLOR

        # Test mixed case
        color4 = hex_to_discord_color("#AbCdEf")
        assert color4.value == TEST_COLOR

    def test_get_lowest_position(self):
        """Test getting lowest position for role placement."""

        async def _test():
            # Mock guild (position doesn't depend on actual guild data)
            mock_guild = None
            position = await get_lowest_position(mock_guild)
            assert position == 1  # Should be 1 (above @everyone)

        # Run the async test
        asyncio.run(_test())


class MockRole:
    """Mock Discord role for testing."""

    def __init__(self, name: str, color: int = 0):
        self.name = name
        self.color = discord.Color(color)


class MockGuild:
    """Mock Discord guild for testing."""

    def __init__(self, roles: list[MockRole]):
        self.roles = roles


class TestFindExistingColorRole(unittest.TestCase):
    """Test finding existing color roles."""

    def test_find_existing_color_role_exact_match(self):
        """Test finding exact match for color role."""
        roles = [
            MockRole("Admin"),
            MockRole("#ff0000"),
            MockRole("Member"),
        ]
        guild = MockGuild(roles)

        # Should find exact match
        result = find_existing_color_role(guild, "#ff0000")
        assert result is not None
        assert result.name == "#ff0000"

        # Should find match without # prefix
        result = find_existing_color_role(guild, "ff0000")
        assert result is not None
        assert result.name == "#ff0000"

    def test_find_existing_color_role_case_insensitive(self):
        """Test case insensitive matching."""
        roles = [
            MockRole("Admin"),
            MockRole("#FF0000"),  # Uppercase
            MockRole("Member"),
        ]
        guild = MockGuild(roles)

        # Should find match with lowercase input
        result = find_existing_color_role(guild, "#ff0000")
        assert result is not None
        assert result.name == "#FF0000"

        # Should find match with mixed case input
        result = find_existing_color_role(guild, "Ff0000")
        assert result is not None
        assert result.name == "#FF0000"

    def test_find_existing_color_role_no_match(self):
        """Test when no matching color role exists."""
        roles = [
            MockRole("Admin"),
            MockRole("#ff0000"),
            MockRole("Member"),
        ]
        guild = MockGuild(roles)

        # Should not find non-existent color
        result = find_existing_color_role(guild, "#00ff00")
        assert result is None

    def test_find_existing_color_role_non_hex_roles_ignored(self):
        """Test that non-hex roles are ignored."""
        roles = [
            MockRole("Admin"),
            MockRole("ff0000"),  # Missing # prefix but valid hex
            MockRole("NotAColor"),
            MockRole("#invalid"),  # Too short
        ]
        guild = MockGuild(roles)

        # Should find role without # prefix (valid hex pattern)
        result = find_existing_color_role(guild, "ff0000")
        assert result is not None
        assert result.name == "ff0000"

        # Should not find invalid hex role
        result = find_existing_color_role(guild, "invalid")
        assert result is None

    def test_find_existing_color_role_multiple_formats(self):
        """Test finding roles in different valid formats."""
        roles = [
            MockRole("#ff0000"),  # With #
            MockRole("00ff00"),  # Without #
            MockRole("#0000FF"),  # Uppercase with #
        ]
        guild = MockGuild(roles)

        # Test finding each format
        result1 = find_existing_color_role(guild, "ff0000")
        assert result1.name == "#ff0000"

        result2 = find_existing_color_role(guild, "#00ff00")
        assert result2.name == "00ff00"

        result3 = find_existing_color_role(guild, "0000ff")
        assert result3.name == "#0000FF"


if __name__ == "__main__":
    unittest.main()
