"""
Tests for server views including macro search functionality.
"""

from unittest.mock import patch

from allauth.socialaccount.models import SocialAccount, SocialApp
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from django.urls import reverse
from servers.views import _check_macro_permission, _get_user_permission_status
from shared.test_utils import skip_complex_integration, skip_discord_api_dependent


class ServerViewTests(TestCase):
    """Test server views including search functionality."""

    def setUp(self):
        """Set up test data."""
        # Create a test user with Discord social account
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        # Create a social app for Discord
        self.social_app = SocialApp.objects.create(
            provider="discord",
            name="Discord",
            client_id="test_client_id",
            secret="test_secret",
        )

        # Create a social account for the user
        self.social_account = SocialAccount.objects.create(
            user=self.user,
            provider="discord",
            uid="123456789012345678",
            extra_data={"username": "testuser"},
        )

        self.guild_id = 123456789012345678

        # Test macros data
        self.test_macros = {
            "heal": {
                "message": "/cast Heal",
                "created_by": "123456789012345678",
                "created_by_name": "testuser",
                "created_at": "2023-01-01T00:00:00Z",
            },
            "weakaura": {
                "message": "This is a WeakAura configuration string",
                "created_by": "123456789012345678",
                "created_by_name": "testuser",
                "created_at": "2023-01-01T00:00:00Z",
            },
            "dps": {
                "message": "/cast Fireball",
                "created_by": "123456789012345678",
                "created_by_name": "testuser",
                "created_at": "2023-01-01T00:00:00Z",
            },
        }

    @skip_complex_integration
    @patch("servers.views.get_user_guilds")
    @patch("servers.views.bot_interface.get_available_servers")
    @patch("servers.views.bot_interface.load_server_macros")
    def test_search_by_macro_name(
        self, mock_load_macros, mock_get_servers, mock_get_guilds
    ):
        """Test searching macros by name."""
        # Mock the API responses
        mock_get_guilds.return_value = [
            {"id": str(self.guild_id), "name": "Test Server"}
        ]
        mock_get_servers.return_value = [
            {"guild_id": self.guild_id, "guild_name": "Test Server", "macro_count": 3}
        ]
        mock_load_macros.return_value = self.test_macros

        # Log in the user
        self.client.force_login(self.user)

        # Test search for "heal" - should find "heal" macro
        response = self.client.get(
            reverse("servers:server_detail", args=[self.guild_id]), {"search": "heal"}
        )

        assert response.status_code == 200
        assert "heal" in response.content.decode()
        assert "dps" not in response.content.decode()
        assert "weakaura" not in response.content.decode()

        # Verify search context variables
        assert response.context["search_query"] == "heal"
        assert response.context["macro_count"] == 1
        assert response.context["total_macros"] == 3

    @skip_complex_integration
    @patch("servers.views.get_user_guilds")
    @patch("servers.views.bot_interface.get_available_servers")
    @patch("servers.views.bot_interface.load_server_macros")
    def test_search_by_macro_content(
        self, mock_load_macros, mock_get_servers, mock_get_guilds
    ):
        """Test searching macros by content."""
        # Mock the API responses
        mock_get_guilds.return_value = [
            {"id": str(self.guild_id), "name": "Test Server"}
        ]
        mock_get_servers.return_value = [
            {"guild_id": self.guild_id, "guild_name": "Test Server", "macro_count": 3}
        ]
        mock_load_macros.return_value = self.test_macros

        # Log in the user
        self.client.force_login(self.user)

        # Test search for "cast" - should find both "heal" and "dps" macros
        response = self.client.get(
            reverse("servers:server_detail", args=[self.guild_id]), {"search": "cast"}
        )

        assert response.status_code == 200
        assert "heal" in response.content.decode()
        assert "dps" in response.content.decode()
        assert "weakaura" not in response.content.decode()

        # Verify search context variables
        assert response.context["search_query"] == "cast"
        assert response.context["macro_count"] == 2
        assert response.context["total_macros"] == 3

    @skip_complex_integration
    @patch("servers.views.get_user_guilds")
    @patch("servers.views.bot_interface.get_available_servers")
    @patch("servers.views.bot_interface.load_server_macros")
    def test_search_case_insensitive(
        self, mock_load_macros, mock_get_servers, mock_get_guilds
    ):
        """Test that search is case insensitive."""
        # Mock the API responses
        mock_get_guilds.return_value = [
            {"id": str(self.guild_id), "name": "Test Server"}
        ]
        mock_get_servers.return_value = [
            {"guild_id": self.guild_id, "guild_name": "Test Server", "macro_count": 3}
        ]
        mock_load_macros.return_value = self.test_macros

        # Log in the user
        self.client.force_login(self.user)

        # Test search for "WEAKAURA" (uppercase) - should find "weakaura" macro
        response = self.client.get(
            reverse("servers:server_detail", args=[self.guild_id]),
            {"search": "WEAKAURA"},
        )

        assert response.status_code == 200
        assert "weakaura" in response.content.decode()
        assert "heal" not in response.content.decode()
        assert "dps" not in response.content.decode()

        # Verify search context variables
        assert response.context["search_query"] == "WEAKAURA"
        assert response.context["macro_count"] == 1

    @skip_complex_integration
    @patch("servers.views.get_user_guilds")
    @patch("servers.views.bot_interface.get_available_servers")
    @patch("servers.views.bot_interface.load_server_macros")
    def test_search_no_results(
        self, mock_load_macros, mock_get_servers, mock_get_guilds
    ):
        """Test search with no results."""
        # Mock the API responses
        mock_get_guilds.return_value = [
            {"id": str(self.guild_id), "name": "Test Server"}
        ]
        mock_get_servers.return_value = [
            {"guild_id": self.guild_id, "guild_name": "Test Server", "macro_count": 3}
        ]
        mock_load_macros.return_value = self.test_macros

        # Log in the user
        self.client.force_login(self.user)

        # Test search for non-existent term
        response = self.client.get(
            reverse("servers:server_detail", args=[self.guild_id]),
            {"search": "nonexistent"},
        )

        assert response.status_code == 200
        assert "No search results" in response.content.decode()
        assert 'No macros found matching "nonexistent"' in response.content.decode()

        # Verify search context variables
        assert response.context["search_query"] == "nonexistent"
        assert response.context["macro_count"] == 0
        assert response.context["total_macros"] == 3

    @skip_complex_integration
    @patch("servers.views.get_user_guilds")
    @patch("servers.views.bot_interface.get_available_servers")
    @patch("servers.views.bot_interface.load_server_macros")
    def test_no_search_shows_all(
        self, mock_load_macros, mock_get_servers, mock_get_guilds
    ):
        """Test that no search parameter shows all macros."""
        # Mock the API responses
        mock_get_guilds.return_value = [
            {"id": str(self.guild_id), "name": "Test Server"}
        ]
        mock_get_servers.return_value = [
            {"guild_id": self.guild_id, "guild_name": "Test Server", "macro_count": 3}
        ]
        mock_load_macros.return_value = self.test_macros

        # Log in the user
        self.client.force_login(self.user)

        # Test with no search parameter
        response = self.client.get(
            reverse("servers:server_detail", args=[self.guild_id])
        )

        assert response.status_code == 200
        assert "heal" in response.content.decode()
        assert "weakaura" in response.content.decode()
        assert "dps" in response.content.decode()

        # Verify context variables
        assert response.context["search_query"] == ""
        assert response.context["macro_count"] == 3
        assert response.context["total_macros"] == 3

    @skip_discord_api_dependent
    @patch("servers.views.get_user_guilds")
    def test_server_hub_success(self, mock_get_guilds):
        """Test server hub view with valid access."""
        self.client.force_login(self.user)

        guild_id = 123456789012345678
        mock_get_guilds.return_value = [
            {"id": str(guild_id), "name": "Test Server", "permissions": str(0x8)}
        ]

        response = self.client.get(reverse("servers:server_hub", args=[guild_id]))
        assert response.status_code == 200
        assert "Test Server" in response.content.decode()

    @skip_discord_api_dependent
    @patch("servers.views.get_user_guilds")
    def test_server_hub_no_access(self, mock_get_guilds):
        """Test server hub when user has no access."""
        self.client.force_login(self.user)

        guild_id = 123456789012345678
        mock_get_guilds.return_value = []  # No guilds

        response = self.client.get(reverse("servers:server_hub", args=[guild_id]))
        assert response.status_code == 302  # Redirect to servers:dashboard

    @skip_complex_integration
    @patch("servers.views.get_user_guilds")
    def test_permission_status_checking(self, mock_get_guilds):
        """Test user permission status checking utility."""

        factory = RequestFactory()
        request = factory.get("/dummy")
        request.user = self.user

        guild_id = 123456789012345678
        mock_get_guilds.return_value = [
            {
                "id": str(guild_id),
                "name": "Test Server",
                "permissions": str(0x8),  # Administrator permission
                "owner": False,
            }
        ]

        # Test permission status calculation
        user_guilds = mock_get_guilds.return_value
        permission_status = _get_user_permission_status(request, guild_id, user_guilds)

        # Should have various permission flags
        assert "can_admin_panel" in permission_status
        assert "can_create_macros" in permission_status

    @skip_complex_integration
    @patch("servers.views.get_user_guilds")
    def test_macro_permission_checking(self, mock_get_guilds):
        """Test macro permission checking function."""

        factory = RequestFactory()
        request = factory.get("/dummy")
        request.user = self.user

        guild_id = 123456789012345678
        mock_get_guilds.return_value = [
            {
                "id": str(guild_id),
                "name": "Test Server",
                "permissions": str(0x8),
                "owner": True,
            }
        ]

        # Test permission checking
        user_guilds = mock_get_guilds.return_value
        has_permission = _check_macro_permission(
            request, guild_id, user_guilds, "create_macros"
        )

        # Server owner should have all permissions
        assert has_permission
