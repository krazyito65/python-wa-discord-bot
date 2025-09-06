"""
Unit tests for WeakAuras Web Interface authentication adapters.

This module tests custom authentication adapters that enforce Discord OAuth-only
authentication and disable traditional username/password account creation.
"""

from unittest.mock import Mock, patch

from allauth.account.models import EmailAddress
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from authentication.adapters import (
    DiscordOnlyAccountAdapter,
    DiscordOnlySocialAccountAdapter,
)

# Test constants
HTTP_REDIRECT_STATUS = 302


class TestDiscordOnlyAccountAdapter(TestCase):
    """Test cases for DiscordOnlyAccountAdapter."""

    def setUp(self):
        """Set up test fixtures."""
        self.adapter = DiscordOnlyAccountAdapter()
        self.factory = RequestFactory()

    def test_is_open_for_signup_returns_false(self):
        """Test that traditional signup is disabled."""
        request = self.factory.get("/")
        result = self.adapter.is_open_for_signup(request)
        assert not result

    def test_is_safe_url_discord_url(self):
        """Test that Discord OAuth URLs are considered safe."""
        result = self.adapter.is_safe_url("/accounts/discord/login/")
        assert result

    def test_is_safe_url_non_discord_url(self):
        """Test that non-Discord URLs use parent implementation."""
        with patch.object(
            DiscordOnlyAccountAdapter.__bases__[0], "is_safe_url", return_value=True
        ) as mock_parent:
            result = self.adapter.is_safe_url("/some/other/url/")
            mock_parent.assert_called_once_with("/some/other/url/")
            assert result

    def test_get_login_redirect_url(self):
        """Test login redirect URL points to dashboard."""
        request = self.factory.get("/")
        result = self.adapter.get_login_redirect_url(request)
        assert result == "/dashboard/"

    def test_respond_user_inactive(self):
        """Test inactive user response redirects to Discord OAuth."""
        request = self.factory.get("/")
        user = Mock()

        # Mock messages framework and redirect
        with (
            patch("authentication.adapters.messages.error") as mock_messages,
            patch("authentication.adapters.redirect") as mock_redirect,
        ):
            mock_redirect.return_value = HttpResponse(status=HTTP_REDIRECT_STATUS)
            result = self.adapter.respond_user_inactive(request, user)

            mock_messages.assert_called_once()
            mock_redirect.assert_called_once_with(
                "socialaccount_login", provider="discord"
            )
            assert isinstance(result, HttpResponse)
            assert result.status_code == HTTP_REDIRECT_STATUS


class TestDiscordOnlySocialAccountAdapter(TestCase):
    """Test cases for DiscordOnlySocialAccountAdapter."""

    def setUp(self):
        """Set up test fixtures."""
        self.adapter = DiscordOnlySocialAccountAdapter()
        self.factory = RequestFactory()

    def test_is_open_for_signup_discord_provider(self):
        """Test that signup is allowed for Discord provider."""
        request = self.factory.get("/")

        # Mock social login with Discord provider
        sociallogin = Mock()
        sociallogin.account.provider = "discord"

        result = self.adapter.is_open_for_signup(request, sociallogin)
        assert result

    def test_is_open_for_signup_non_discord_provider(self):
        """Test that signup is denied for non-Discord providers."""
        request = self.factory.get("/")

        # Mock social login with non-Discord provider
        sociallogin = Mock()
        sociallogin.account.provider = "google"

        result = self.adapter.is_open_for_signup(request, sociallogin)
        assert not result

    def test_populate_user_with_username(self):
        """Test user population with Discord username."""
        request = self.factory.get("/")
        sociallogin = Mock()
        data = {
            "username": "testuser",
            "id": "123456789",
        }

        with patch.object(
            DiscordOnlySocialAccountAdapter.__bases__[0], "populate_user"
        ) as mock_parent:
            mock_user = Mock()
            mock_parent.return_value = mock_user

            result = self.adapter.populate_user(request, sociallogin, data)

            assert result.username == "testuser"
            mock_parent.assert_called_once_with(request, sociallogin, data)

    def test_populate_user_with_global_name(self):
        """Test user population with Discord global name only."""
        request = self.factory.get("/")
        sociallogin = Mock()
        data = {
            "global_name": "Test User",
            "id": "123456789",
        }

        with patch.object(
            DiscordOnlySocialAccountAdapter.__bases__[0], "populate_user"
        ) as mock_parent:
            mock_user = Mock()
            mock_parent.return_value = mock_user

            result = self.adapter.populate_user(request, sociallogin, data)

            # Username should be global_name when username is not present
            assert result.username == "Test User"
            assert result.first_name == "Test User"

    def test_populate_user_fallback_to_id(self):
        """Test user population fallback to Discord ID."""
        request = self.factory.get("/")
        sociallogin = Mock()
        data = {"id": "123456789"}

        with patch.object(
            DiscordOnlySocialAccountAdapter.__bases__[0], "populate_user"
        ) as mock_parent:
            mock_user = Mock()
            mock_parent.return_value = mock_user

            result = self.adapter.populate_user(request, sociallogin, data)

            assert result.username == "discord_user_123456789"

    def test_populate_user_fallback_to_unknown(self):
        """Test user population fallback when no ID available."""
        request = self.factory.get("/")
        sociallogin = Mock()
        data = {}

        with patch.object(
            DiscordOnlySocialAccountAdapter.__bases__[0], "populate_user"
        ) as mock_parent:
            mock_user = Mock()
            mock_parent.return_value = mock_user

            result = self.adapter.populate_user(request, sociallogin, data)

            assert result.username == "discord_user_unknown"

    def test_save_user_with_email(self):
        """Test saving user with email verification."""
        request = self.factory.get("/")
        sociallogin = Mock()
        sociallogin.account.extra_data = {"email": "test@example.com"}

        user = User.objects.create_user("testuser")

        with patch.object(
            DiscordOnlySocialAccountAdapter.__bases__[0], "save_user", return_value=user
        ) as mock_parent:
            self.adapter.save_user(request, sociallogin)

            # Verify parent was called
            mock_parent.assert_called_once_with(request, sociallogin, None)

            # Verify email address was created and verified
            email_address = EmailAddress.objects.get(
                user=user, email="test@example.com"
            )
            assert email_address.verified
            assert email_address.primary

    def test_save_user_without_email(self):
        """Test saving user without email in extra_data."""
        request = self.factory.get("/")
        sociallogin = Mock()
        sociallogin.account.extra_data = {}

        user = User.objects.create_user("testuser")

        with patch.object(
            DiscordOnlySocialAccountAdapter.__bases__[0], "save_user", return_value=user
        ) as mock_parent:
            self.adapter.save_user(request, sociallogin)

            # Verify parent was called
            mock_parent.assert_called_once_with(request, sociallogin, None)

            # Verify no email address was created
            assert not EmailAddress.objects.filter(user=user).exists()

    def test_get_connect_redirect_url(self):
        """Test connect redirect URL points to dashboard."""
        request = self.factory.get("/")
        socialaccount = Mock()

        result = self.adapter.get_connect_redirect_url(request, socialaccount)

        assert result == "/dashboard/"
