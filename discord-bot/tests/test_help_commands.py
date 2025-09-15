"""Tests for help command functionality."""

import unittest

import discord
from commands.help_commands import (
    COMMAND_CATEGORIES,
    create_help_embed,
    get_command_info,
    get_total_command_count,
)

# Discord limits
DISCORD_EMBED_FIELD_LIMIT = 25
DISCORD_EMBED_TOTAL_CHAR_LIMIT = 6000
MIN_EXAMPLE_LENGTH = 10


class TestHelpCommands(unittest.TestCase):
    """Test help command utilities and functionality."""

    def test_command_categories_structure(self):
        """Test that command categories have proper structure."""
        for category_data in COMMAND_CATEGORIES.values():
            # Check required keys exist
            assert "title" in category_data
            assert "description" in category_data
            assert "commands" in category_data

            # Check title format
            assert isinstance(category_data["title"], str)
            assert len(category_data["title"]) > 0

            # Check description
            assert isinstance(category_data["description"], str)
            assert len(category_data["description"]) > 0

            # Check commands list
            assert isinstance(category_data["commands"], list)
            assert len(category_data["commands"]) > 0

            # Check each command structure
            for cmd in category_data["commands"]:
                assert "name" in cmd
                assert "description" in cmd
                assert "usage" in cmd
                assert "example" in cmd

                # Verify command name starts with /
                assert cmd["name"].startswith("/")

                # Verify usage contains the command name
                assert cmd["name"].split("/")[1] in cmd["usage"]

    def test_create_help_embed_all_categories(self):
        """Test creating help embed for all categories."""
        embed = create_help_embed("all", "Test Server")

        # Check embed properties
        assert isinstance(embed, discord.Embed)
        assert "WeakAuras Bot Commands" in embed.title
        assert "Test Server" in embed.description
        assert embed.color == discord.Color.blue()

        # Check that all categories are included
        assert len(embed.fields) == len(COMMAND_CATEGORIES)

        # Verify field names contain category titles
        field_names = [field.name for field in embed.fields]
        for category_data in COMMAND_CATEGORIES.values():
            assert any(category_data["title"] in name for name in field_names)

    def test_create_help_embed_specific_category(self):
        """Test creating help embed for specific categories."""
        for category_key in COMMAND_CATEGORIES:
            embed = create_help_embed(category_key, "Test Server")

            # Check embed properties
            assert isinstance(embed, discord.Embed)
            assert embed.color == discord.Color.green()

            # Check that commands are listed
            category_data = COMMAND_CATEGORIES[category_key]
            assert category_data["title"] in embed.title
            assert category_data["description"] in embed.description

            # Verify all commands in category are included
            field_names = [field.name for field in embed.fields]
            for cmd in category_data["commands"]:
                assert any(cmd["name"] in name for name in field_names)

    def test_create_help_embed_invalid_category(self):
        """Test that invalid category falls back to all categories."""
        embed = create_help_embed("invalid_category", "Test Server")

        # Should fall back to "all" behavior
        assert "WeakAuras Bot Commands" in embed.title
        assert embed.color == discord.Color.blue()

    def test_get_command_info_valid_commands(self):
        """Test getting info for valid commands."""
        # Test with slash prefix
        info = get_command_info("/ping")
        assert info is not None
        assert info["name"] == "/ping"
        assert "description" in info
        assert "usage" in info
        assert "example" in info

        # Test without slash prefix
        info = get_command_info("ping")
        assert info is not None
        assert info["name"] == "/ping"

        # Test another command
        info = get_command_info("/help")
        assert info is not None
        assert info["name"] == "/help"

    def test_get_command_info_invalid_command(self):
        """Test getting info for invalid commands."""
        info = get_command_info("/nonexistent")
        assert info is None

        info = get_command_info("invalid_command")
        assert info is None

    def test_get_total_command_count(self):
        """Test getting total command count."""
        total = get_total_command_count()

        # Calculate expected total
        expected_total = sum(
            len(cat["commands"]) for cat in COMMAND_CATEGORIES.values()
        )

        assert total == expected_total
        assert total > 0

    def test_all_commands_have_unique_names(self):
        """Test that all command names are unique across categories."""
        all_command_names = []

        for category_data in COMMAND_CATEGORIES.values():
            for cmd in category_data["commands"]:
                command_name = cmd["name"]
                assert command_name not in all_command_names, (
                    f"Duplicate command: {command_name}"
                )
                all_command_names.append(command_name)

    def test_embed_field_limits(self):
        """Test that help embeds don't exceed Discord's field limits."""
        # Test all categories embed
        embed = create_help_embed("all", "Test Server")
        assert len(embed.fields) <= DISCORD_EMBED_FIELD_LIMIT  # Discord limit

        # Test specific category embeds
        for category_key in COMMAND_CATEGORIES:
            embed = create_help_embed(category_key, "Test Server")
            assert len(embed.fields) <= DISCORD_EMBED_FIELD_LIMIT  # Discord limit

            # Check total embed length (approximate)
            total_length = len(embed.title or "") + len(embed.description or "")
            for field in embed.fields:
                total_length += len(field.name or "") + len(field.value or "")

            # Discord embed total limit is 6000 characters
            assert total_length < DISCORD_EMBED_TOTAL_CHAR_LIMIT

    def test_command_usage_examples_format(self):
        """Test that command usage examples are properly formatted."""
        for category_data in COMMAND_CATEGORIES.values():
            for cmd in category_data["commands"]:
                usage = cmd["usage"]
                example = cmd["example"]

                # Usage should start with the command name
                assert usage.startswith(cmd["name"])

                # Example should be descriptive
                assert len(example) > MIN_EXAMPLE_LENGTH

                # Example should not start with / (it's a description, not a command)
                assert not example.startswith("/")

    def test_category_coverage(self):
        """Test that all major bot functionality is covered in help."""
        # Expected command types that should be covered
        expected_commands = [
            "/help",
            "/ping",  # utility
            "/create_macro",
            "/macro",
            "/list_macros",  # macros
            "/role",
            "/remove_role",
            "/list_roles",  # roles
        ]

        all_commands = []
        for category_data in COMMAND_CATEGORIES.values():
            all_commands.extend(cmd["name"] for cmd in category_data["commands"])

        for expected_cmd in expected_commands:
            assert expected_cmd in all_commands, (
                f"Missing command in help: {expected_cmd}"
            )


if __name__ == "__main__":
    unittest.main()
