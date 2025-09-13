"""
Tests for user_stats app.
"""

from unittest.mock import patch

from allauth.socialaccount.models import SocialAccount
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from shared.discord_api import DiscordAPIError

from .models import (
    DiscordChannel,
    DiscordGuild,
    DiscordUser,
    MessageStatistics,
    StatisticsCollectionJob,
)


class UserStatsModelsTest(TestCase):
    """Test user statistics models."""

    def setUp(self):
        """Set up test data."""
        self.guild = DiscordGuild.objects.create(
            guild_id="123456789012345678", name="Test Server"
        )

        self.user_discord = DiscordUser.objects.create(
            user_id="987654321098765432", username="testuser", display_name="Test User"
        )

        self.channel = DiscordChannel.objects.create(
            channel_id="111111111111111111",
            guild=self.guild,
            name="general",
            channel_type="text",
        )

    def test_guild_creation(self):
        """Test Discord guild creation."""
        assert self.guild.name == "Test Server"
        assert str(self.guild) == "Test Server (123456789012345678)"

    def test_user_creation(self):
        """Test Discord user creation."""
        assert self.user_discord.username == "testuser"
        assert str(self.user_discord) == "Test User (987654321098765432)"

    def test_channel_creation(self):
        """Test Discord channel creation."""
        assert self.channel.name == "general"
        assert str(self.channel) == "#general (Test Server)"

    def test_message_statistics_creation(self):
        """Test message statistics creation."""
        stats = MessageStatistics.objects.create(
            user=self.user_discord,
            channel=self.channel,
            total_messages=100,
            messages_last_7_days=20,
            messages_last_30_days=80,
            messages_last_90_days=95,
        )

        assert stats.total_messages == 100
        assert stats.messages_last_7_days == 20
        assert str(stats) == "testuser in general: 100 messages"

    def test_collection_job_creation(self):
        """Test statistics collection job creation."""
        job = StatisticsCollectionJob.objects.create(
            guild=self.guild,
            target_user=self.user_discord,
            time_range_days=30,
            status="pending",
        )

        assert job.status == "pending"
        assert job.progress_percentage == 0
        assert "testuser" in str(job)

    def test_collection_job_progress(self):
        """Test collection job progress calculation."""
        job = StatisticsCollectionJob.objects.create(
            guild=self.guild, progress_current=25, progress_total=100
        )

        assert job.progress_percentage == 25.0


class UserStatsViewsTest(TestCase):
    """Test user statistics views."""

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

        # Create test Discord data
        self.guild = DiscordGuild.objects.create(
            guild_id="123456789012345678", name="Test Server"
        )

        self.user_discord = DiscordUser.objects.create(
            user_id="987654321098765432", username="testuser", display_name="Test User"
        )

        self.channel = DiscordChannel.objects.create(
            channel_id="111111111111111111",
            guild=self.guild,
            name="general",
            channel_type="text",
        )

        self.stats = MessageStatistics.objects.create(
            user=self.user_discord,
            channel=self.channel,
            total_messages=100,
            messages_last_7_days=20,
            messages_last_30_days=80,
            messages_last_90_days=95,
        )

    def test_dashboard_requires_login(self):
        """Test that dashboard requires authentication."""
        response = self.client.get(reverse("user_stats:dashboard"))
        assert response.status_code == 302  # Redirect to login

    @patch("user_stats.views.get_user_guilds")
    def test_dashboard_access_with_login(self, mock_get_guilds):
        """Test dashboard access with authenticated user."""

        mock_get_guilds.side_effect = DiscordAPIError("No Discord token available")

        self.client.force_login(self.user)

        # This should now return a 200 but with an error message
        response = self.client.get(reverse("user_stats:dashboard"))
        assert response.status_code == 302  # Redirect to servers dashboard

    def test_api_endpoint_requires_login(self):
        """Test API endpoint requires authentication."""
        response = self.client.get(
            reverse("user_stats:api_guild_stats", args=[123456789012345678])
        )
        assert response.status_code == 302  # Redirect to login

    def test_user_detail_requires_login(self):
        """Test user detail requires authentication."""
        response = self.client.get(
            reverse(
                "user_stats:user_detail",
                args=[123456789012345678, "987654321098765432"],
            )
        )
        assert response.status_code == 302  # Redirect to login
