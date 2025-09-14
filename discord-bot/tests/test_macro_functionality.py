"""
Unit tests for macro-related functionality and utilities.

This module tests the actual functionality that can be properly tested
without complex Discord.py mocking.
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, Mock

import discord
from commands.macro_commands import send_embed_response


class TestMacroFunctionality(unittest.TestCase):
    """Test cases for macro functionality."""

    def test_send_embed_response_with_file(self):
        """Test sending embed response with file attachment."""
        # Create mock interaction and response
        mock_interaction = Mock(spec=discord.Interaction)
        mock_interaction.response = AsyncMock()

        # Create mock embed and file
        mock_embed = Mock(spec=discord.Embed)
        mock_file = Mock(spec=discord.File)

        async def run_test():
            await send_embed_response(
                mock_interaction, mock_embed, mock_file, ephemeral=False
            )

            # Verify response was called with correct parameters
            mock_interaction.response.send_message.assert_called_once_with(
                embed=mock_embed, file=mock_file, ephemeral=False
            )

        asyncio.run(run_test())

    def test_send_embed_response_without_file(self):
        """Test sending embed response without file attachment."""
        # Create mock interaction and response
        mock_interaction = Mock(spec=discord.Interaction)
        mock_interaction.response = AsyncMock()

        # Create mock embed
        mock_embed = Mock(spec=discord.Embed)

        async def run_test():
            await send_embed_response(
                mock_interaction, mock_embed, None, ephemeral=True
            )

            # Verify response was called with correct parameters (default ephemeral=True)
            mock_interaction.response.send_message.assert_called_once_with(
                embed=mock_embed, ephemeral=True
            )

        asyncio.run(run_test())

    def test_send_embed_response_default_ephemeral(self):
        """Test that send_embed_response defaults to ephemeral=True."""
        mock_interaction = Mock(spec=discord.Interaction)
        mock_interaction.response = AsyncMock()
        mock_embed = Mock(spec=discord.Embed)

        async def run_test():
            # Don't specify ephemeral parameter
            await send_embed_response(mock_interaction, mock_embed, None)

            # Should default to ephemeral=True
            mock_interaction.response.send_message.assert_called_once_with(
                embed=mock_embed, ephemeral=True
            )

        asyncio.run(run_test())

    def test_send_embed_response_with_file_default_ephemeral(self):
        """Test send_embed_response with file using default ephemeral setting."""
        mock_interaction = Mock(spec=discord.Interaction)
        mock_interaction.response = AsyncMock()
        mock_embed = Mock(spec=discord.Embed)
        mock_file = Mock(spec=discord.File)

        async def run_test():
            # Don't specify ephemeral parameter
            await send_embed_response(mock_interaction, mock_embed, mock_file)

            # Should default to ephemeral=True and include file
            mock_interaction.response.send_message.assert_called_once_with(
                embed=mock_embed, file=mock_file, ephemeral=True
            )

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
