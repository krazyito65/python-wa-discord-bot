"""
Tests for macros app views and functionality.
"""

from unittest.mock import patch

from allauth.socialaccount.models import SocialAccount
from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse


class MacroAddFeatureFlagTest(TestCase):
    """Test macro_add view feature flag functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a test user with Discord social account
        self.user = User.objects.create_user(username="testuser")
        self.social_account = SocialAccount.objects.create(
            user=self.user,
            provider="discord",
            uid="123456789012345678",
            extra_data={"username": "testuser"},
        )
        self.guild_id = 123456789012345678

    @patch("macros.views.get_user_guilds")
    def test_preview_enabled_by_default(self, mock_get_guilds):
        """Test that preview respects current configuration."""

        mock_get_guilds.return_value = [
            {"id": str(self.guild_id), "name": "Test Server", "permissions": "8"}  # Administrator permission
        ]

        self.client.force_login(self.user)
        response = self.client.get(reverse("macros:macro_add", args=[self.guild_id]))

        assert response.status_code == 200

        # Test based on actual configuration
        feature_flags = getattr(settings, "FEATURE_FLAGS", {})
        macro_preview_enabled = feature_flags.get("macro_preview", True)

        if macro_preview_enabled:
            self.assertContains(response, "Discord Preview")
            self.assertContains(response, "macroPreview")
            self.assertContains(response, "parseDiscordMarkdown")
        else:
            self.assertNotContains(response, "Discord Preview")
            self.assertNotContains(response, "macroPreview")
            self.assertNotContains(response, "parseDiscordMarkdown")

    @override_settings(FEATURE_FLAGS={"macro_preview": False})
    @patch("macros.views.get_user_guilds")
    def test_preview_disabled_by_feature_flag(self, mock_get_guilds):
        """Test that preview is hidden when feature flag is disabled."""
        mock_get_guilds.return_value = [
            {"id": str(self.guild_id), "name": "Test Server", "permissions": "8"}  # Administrator permission
        ]

        self.client.force_login(self.user)
        response = self.client.get(reverse("macros:macro_add", args=[self.guild_id]))

        assert response.status_code == 200
        self.assertNotContains(response, "Discord Preview")
        self.assertNotContains(response, "macroPreview")
        self.assertNotContains(response, "parseDiscordMarkdown")

    @override_settings(FEATURE_FLAGS={"macro_preview": True})
    @patch("macros.views.get_user_guilds")
    def test_preview_explicitly_enabled(self, mock_get_guilds):
        """Test that preview works when explicitly enabled."""
        mock_get_guilds.return_value = [
            {"id": str(self.guild_id), "name": "Test Server", "permissions": "8"}  # Administrator permission
        ]

        self.client.force_login(self.user)
        response = self.client.get(reverse("macros:macro_add", args=[self.guild_id]))

        assert response.status_code == 200
        self.assertContains(response, "Discord Preview")
        self.assertContains(response, "macroPreview")
        self.assertContains(response, "parseDiscordMarkdown")
