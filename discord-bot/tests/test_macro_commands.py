"""
Unit tests for WeakAuras Discord Bot macro commands.

This module tests the macro command setup functionality.
"""

import unittest
from unittest.mock import Mock, patch

from bot import WeakAurasBot
from commands.macro_commands import setup_macro_commands


class TestMacroCommands(unittest.TestCase):
    """Test cases for macro commands setup."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_config = {
            "bot": {"admin_role": "admin"},
            "discord": {"tokens": {"dev": "test_token"}},
        }

    def test_setup_macro_commands(self):
        """Test that macro commands are properly set up on the bot."""
        # Create mock bot with command tree
        with patch("bot.weakauras_bot.commands.Bot.__init__") as mock_init:
            mock_init.return_value = None
            bot = WeakAurasBot(self.test_config)

            # Mock the command tree
            mock_tree = Mock()
            mock_tree.command = Mock(return_value=lambda func: func)

            # Use patch to mock the tree property
            with patch.object(type(bot), "tree", new_callable=lambda: mock_tree):
                # Call setup function
                setup_macro_commands(bot)

                # Verify that commands were registered
                expected_commands = 4
                assert mock_tree.command.call_count >= expected_commands


if __name__ == "__main__":
    unittest.main()
