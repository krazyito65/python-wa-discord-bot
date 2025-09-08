"""
Unit tests for WeakAuras Web Interface shared modules.

This module tests the bot interface and Discord API utilities used
by the Django web application to interact with bot data and Discord API.
"""

import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests
from allauth.socialaccount.models import SocialToken
from django.contrib.auth.models import User
from django.test import TestCase

from shared.bot_interface import BotDataInterface, MacroData, MacroUpdateData
from shared.discord_api import (
    DiscordAPIError,
    filter_available_servers,
    get_user_discord_token,
    get_user_guilds,
    get_user_info,
)

# Test constants
MAX_SERVER_NAME_LENGTH = 100
EXPECTED_AVAILABLE_SERVERS = 2
TEST_GUILD_ID_1 = 123
TEST_GUILD_ID_2 = 456
EXPECTED_GUILD_COUNT = 2


class TestBotDataInterface(TestCase):
    """Test cases for BotDataInterface."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        with patch("django.conf.settings.BOT_DATA_DIR", str(self.temp_dir)):
            self.interface = BotDataInterface()
        self.test_guild_id = 123456789
        self.test_guild_name = "Test Server"

    def tearDown(self):
        """Clean up after each test."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_sanitize_server_name(self):
        """Test server name sanitization."""
        # Test normal name (spaces are preserved)
        result = self.interface.sanitize_server_name("Test Server")
        assert result == "Test Server"

        # Test name with invalid characters
        result = self.interface.sanitize_server_name("Test<>Server:|?*")
        assert result == "Test_Server_"

        # Test empty name
        result = self.interface.sanitize_server_name("")
        assert result == "unknown_server"

        # Test long name (should be truncated)
        long_name = "a" * 150
        result = self.interface.sanitize_server_name(long_name)
        assert len(result) == MAX_SERVER_NAME_LENGTH

    def test_get_server_folder_existing(self):
        """Test getting server folder when it exists."""
        # Create test folder
        folder_name = f"Test_Server_{self.test_guild_id}"
        test_folder = self.temp_dir / folder_name
        test_folder.mkdir()

        result = self.interface.get_server_folder(
            self.test_guild_id, self.test_guild_name
        )

        assert result == test_folder
        assert result.exists()

    def test_get_server_folder_nonexistent(self):
        """Test getting server folder when it doesn't exist."""
        result = self.interface.get_server_folder(
            self.test_guild_id, self.test_guild_name
        )

        assert result is None

    def test_get_available_servers(self):
        """Test getting list of available servers."""
        # Create test server folders
        folder1 = self.temp_dir / f"Server_One_{TEST_GUILD_ID_1}"
        folder2 = self.temp_dir / f"Server_Two_{TEST_GUILD_ID_2}"
        folder1.mkdir()
        folder2.mkdir()

        # Create macro files
        (folder1 / f"{TEST_GUILD_ID_1}_macros.json").write_text('{"test": "data"}')
        (folder2 / f"{TEST_GUILD_ID_2}_macros.json").write_text('{"test": "data"}')

        result = self.interface.get_available_servers()

        assert len(result) == EXPECTED_AVAILABLE_SERVERS
        guild_ids = [server["guild_id"] for server in result]
        assert TEST_GUILD_ID_1 in guild_ids
        assert TEST_GUILD_ID_2 in guild_ids

    def test_load_server_macros_existing_file(self):
        """Test loading server macros when file exists."""
        # Create test server folder and macros file
        folder_name = f"Test_Server_{self.test_guild_id}"
        test_folder = self.temp_dir / folder_name
        test_folder.mkdir()

        test_macros = {
            "test_macro": {
                "name": "test_macro",
                "message": "Test message",
                "created_by": "user123",
                "created_by_name": "TestUser",
                "created_at": "2024-01-01T00:00:00",
            }
        }

        macros_file = test_folder / f"{self.test_guild_id}_macros.json"
        with open(macros_file, "w", encoding="utf-8") as f:
            json.dump(test_macros, f)

        result = self.interface.load_server_macros(
            self.test_guild_id, self.test_guild_name
        )

        assert result == test_macros

    def test_load_server_macros_no_file(self):
        """Test loading server macros when no file exists."""
        result = self.interface.load_server_macros(
            self.test_guild_id, self.test_guild_name
        )
        assert result == {}

    def test_save_server_macros(self):
        """Test saving server macros."""
        test_macros = {
            "test_macro": {
                "name": "test_macro",
                "message": "Test message",
                "created_by": "user123",
                "created_by_name": "TestUser",
                "created_at": "2024-01-01T00:00:00",
            }
        }

        # Create test server folder
        folder_name = f"Test_Server_{self.test_guild_id}"
        test_folder = self.temp_dir / folder_name
        test_folder.mkdir()

        result = self.interface.save_server_macros(
            self.test_guild_id, self.test_guild_name, test_macros
        )

        assert result is True

        # Verify file was created
        macros_file = test_folder / f"{self.test_guild_id}_macros.json"
        assert macros_file.exists()

        with open(macros_file, encoding="utf-8") as f:
            saved_data = json.load(f)

        assert saved_data == test_macros

    def test_add_macro_success(self):
        """Test successful macro addition."""
        # Create test server folder
        folder_name = f"Test_Server_{self.test_guild_id}"
        test_folder = self.temp_dir / folder_name
        test_folder.mkdir()

        macro_data = MacroData(
            guild_id=self.test_guild_id,
            guild_name=self.test_guild_name,
            name="test_macro",
            message="Test message",
            created_by="user123",
            created_by_name="TestUser",
        )

        result = self.interface.add_macro(macro_data)

        assert result is True

        # Verify macro was saved
        macros = self.interface.load_server_macros(
            self.test_guild_id, self.test_guild_name
        )
        assert "test_macro" in macros
        assert macros["test_macro"]["message"] == "Test message"

    def test_add_macro_duplicate(self):
        """Test adding duplicate macro."""
        # Create existing macro
        existing_macros = {"test_macro": {"name": "test_macro"}}

        folder_name = f"Test_Server_{self.test_guild_id}"
        test_folder = self.temp_dir / folder_name
        test_folder.mkdir()

        macros_file = test_folder / f"{self.test_guild_id}_macros.json"
        with open(macros_file, "w", encoding="utf-8") as f:
            json.dump(existing_macros, f)

        macro_data = MacroData(
            guild_id=self.test_guild_id,
            guild_name=self.test_guild_name,
            name="test_macro",
            message="New message",
            created_by="user123",
            created_by_name="TestUser",
        )

        result = self.interface.add_macro(macro_data)

        assert result is False

    def test_update_macro(self):
        """Test macro update."""
        # Create existing macro
        existing_macros = {
            "test_macro": {
                "name": "test_macro",
                "message": "Old message",
                "created_by": "user123",
                "created_by_name": "TestUser",
                "created_at": "2024-01-01T00:00:00",
            }
        }

        folder_name = f"Test_Server_{self.test_guild_id}"
        test_folder = self.temp_dir / folder_name
        test_folder.mkdir()

        macros_file = test_folder / f"{self.test_guild_id}_macros.json"
        with open(macros_file, "w", encoding="utf-8") as f:
            json.dump(existing_macros, f)

        update_data = MacroUpdateData(
            guild_id=self.test_guild_id,
            guild_name=self.test_guild_name,
            old_name="test_macro",
            new_name="test_macro",
            message="New message",
            edited_by="123456789",
            edited_by_name="TestUser",
        )

        success, error_message = self.interface.update_macro(update_data)

        assert success is True
        assert error_message == ""

        # Verify macro was updated
        macros = self.interface.load_server_macros(
            self.test_guild_id, self.test_guild_name
        )
        assert macros["test_macro"]["message"] == "New message"
        assert "updated_at" in macros["test_macro"]
        assert macros["test_macro"]["updated_by"] == "123456789"
        assert macros["test_macro"]["updated_by_name"] == "TestUser"

    def test_rename_macro(self):
        """Test macro renaming."""
        # Create server folder and macro first
        test_folder = (
            self.interface.data_dir / f"{self.test_guild_name}_{self.test_guild_id}"
        )
        test_folder.mkdir(exist_ok=True)

        existing_macros = {
            "old_macro": {
                "name": "old_macro",
                "message": "Original message",
                "created_by": "123456789",
                "created_by_name": "Creator",
                "created_at": "2023-01-01T00:00:00",
            }
        }

        macros_file = test_folder / f"{self.test_guild_id}_macros.json"
        with open(macros_file, "w", encoding="utf-8") as f:
            json.dump(existing_macros, f)

        # Test renaming macro
        update_data = MacroUpdateData(
            guild_id=self.test_guild_id,
            guild_name=self.test_guild_name,
            old_name="old_macro",
            new_name="new_macro",
            message="Updated message",
            edited_by="987654321",
            edited_by_name="Editor",
        )

        success, error_message = self.interface.update_macro(update_data)

        assert success is True
        assert error_message == ""

        # Verify old name is gone and new name exists
        loaded_macros = self.interface.load_server_macros(
            self.test_guild_id, self.test_guild_name
        )
        assert "old_macro" not in loaded_macros
        assert "new_macro" in loaded_macros
        assert loaded_macros["new_macro"]["message"] == "Updated message"
        assert loaded_macros["new_macro"]["updated_by"] == "987654321"
        assert loaded_macros["new_macro"]["updated_by_name"] == "Editor"

    def test_rename_conflict(self):
        """Test macro renaming with name conflict."""
        # Create server folder and macros first
        test_folder = (
            self.interface.data_dir / f"{self.test_guild_name}_{self.test_guild_id}"
        )
        test_folder.mkdir(exist_ok=True)

        existing_macros = {
            "macro1": {"name": "macro1", "message": "Message 1"},
            "macro2": {"name": "macro2", "message": "Message 2"},
        }

        macros_file = test_folder / f"{self.test_guild_id}_macros.json"
        with open(macros_file, "w", encoding="utf-8") as f:
            json.dump(existing_macros, f)

        # Try to rename macro1 to macro2 (should fail)
        update_data = MacroUpdateData(
            guild_id=self.test_guild_id,
            guild_name=self.test_guild_name,
            old_name="macro1",
            new_name="macro2",
            message="Updated message",
            edited_by="123456789",
            edited_by_name="TestUser",
        )

        success, error_message = self.interface.update_macro(update_data)

        assert success is False
        assert "already exists" in error_message

        # Verify original macros are unchanged
        loaded_macros = self.interface.load_server_macros(
            self.test_guild_id, self.test_guild_name
        )
        assert loaded_macros["macro1"]["message"] == "Message 1"
        assert loaded_macros["macro2"]["message"] == "Message 2"

    def test_delete_macro(self):
        """Test macro deletion."""
        # Create existing macro
        existing_macros = {"test_macro": {"name": "test_macro"}}

        folder_name = f"Test_Server_{self.test_guild_id}"
        test_folder = self.temp_dir / folder_name
        test_folder.mkdir()

        macros_file = test_folder / f"{self.test_guild_id}_macros.json"
        with open(macros_file, "w", encoding="utf-8") as f:
            json.dump(existing_macros, f)

        result = self.interface.delete_macro(
            self.test_guild_id, self.test_guild_name, "test_macro"
        )

        assert result is True

        # Verify macro was deleted
        macros = self.interface.load_server_macros(
            self.test_guild_id, self.test_guild_name
        )
        assert "test_macro" not in macros


class TestDiscordAPI(TestCase):
    """Test cases for Discord API utilities."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user("testuser")

    def test_get_user_discord_token_success(self):
        """Test getting Discord token when token exists."""
        # Create mock social token
        with patch("shared.discord_api.SocialToken.objects.get") as mock_get:
            mock_token = Mock()
            mock_token.token = "test_token_123"
            mock_get.return_value = mock_token

            result = get_user_discord_token(self.user)

            assert result == "test_token_123"

    def test_get_user_discord_token_not_found(self):
        """Test getting Discord token when token doesn't exist."""
        with patch(
            "shared.discord_api.SocialToken.objects.get",
            side_effect=SocialToken.DoesNotExist,
        ):
            result = get_user_discord_token(self.user)

            assert result is None

    @patch("shared.discord_api.requests.get")
    def test_get_user_guilds_success(self, mock_get):
        """Test successful guild fetching."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {"id": "123", "name": "Test Server", "icon": "icon123"},
            {"id": "456", "name": "Another Server", "icon": "icon456"},
        ]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        with patch(
            "shared.discord_api.get_user_discord_token", return_value="test_token"
        ):
            result = get_user_guilds(self.user)

            assert len(result) == EXPECTED_GUILD_COUNT
            assert result[0]["name"] == "Test Server"

    def test_get_user_guilds_no_token(self):
        """Test guild fetching when user has no token."""
        with (
            patch("shared.discord_api.get_user_discord_token", return_value=None),
            pytest.raises(DiscordAPIError),
        ):
            get_user_guilds(self.user)

    @patch("shared.discord_api.requests.get")
    def test_get_user_guilds_request_error(self, mock_get):
        """Test guild fetching when request fails."""
        mock_get.side_effect = requests.RequestException("Network error")

        with (
            patch(
                "shared.discord_api.get_user_discord_token", return_value="test_token"
            ),
            pytest.raises(DiscordAPIError),
        ):
            get_user_guilds(self.user)

    @patch("shared.discord_api.requests.get")
    def test_get_user_info_success(self, mock_get):
        """Test successful user info fetching."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "123456789",
            "username": "testuser",
            "discriminator": "1234",
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        with patch(
            "shared.discord_api.get_user_discord_token", return_value="test_token"
        ):
            result = get_user_info(self.user)

            assert result["username"] == "testuser"

    def test_get_user_info_no_token(self):
        """Test user info fetching when user has no token."""
        with patch("shared.discord_api.get_user_discord_token", return_value=None):
            result = get_user_info(self.user)

            assert result is None

    def test_filter_available_servers(self):
        """Test filtering available servers."""
        user_guilds = [
            {"id": "123", "name": "Server One"},
            {"id": "456", "name": "Server Two"},
            {"id": "789", "name": "Server Three"},
        ]

        bot_servers = [
            {
                "guild_id": 123,
                "folder_name": "Server_One_123",
                "folder_path": "/path/123",
            },
            {
                "guild_id": 456,
                "folder_name": "Server_Two_456",
                "folder_path": "/path/456",
            },
        ]

        result = filter_available_servers(user_guilds, bot_servers)

        assert len(result) == EXPECTED_GUILD_COUNT
        assert result[0]["guild_name"] == "Server One"
        assert result[1]["guild_name"] == "Server Two"

        # Server Three should not be included (no bot data)
        guild_names = [server["guild_name"] for server in result]
        assert "Server Three" not in guild_names
