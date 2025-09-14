"""
Tests for user_stats app.
"""

from unittest.mock import patch

from allauth.socialaccount.models import SocialAccount
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from shared.discord_api import DiscordAPIError
from shared.test_utils import skip_discord_api_dependent

from .models import (
    DiscordChannel,
    DiscordGuild,
    DiscordUser,
    MessageStatistics,
    StatisticsCollectionJob,
)

# Test constants
TEST_MESSAGE_COUNT_TOTAL = 100
TEST_MESSAGE_COUNT_7_DAYS = 20
TEST_PROGRESS_PERCENTAGE = 25.0
HTTP_REDIRECT_STATUS = 302


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

        assert stats.total_messages == TEST_MESSAGE_COUNT_TOTAL
        assert stats.messages_last_7_days == TEST_MESSAGE_COUNT_7_DAYS
        assert str(stats) == f"testuser in general: {TEST_MESSAGE_COUNT_TOTAL} messages"

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

        assert job.progress_percentage == TEST_PROGRESS_PERCENTAGE

    def test_collection_job_zero_total_progress(self):
        """Test collection job progress with zero total."""
        job = StatisticsCollectionJob.objects.create(
            guild=self.guild, progress_current=0, progress_total=0
        )

        assert job.progress_percentage == 0.0

    def test_discord_guild_str_method(self):
        """Test Discord guild string representation."""
        guild = DiscordGuild.objects.create(
            guild_id="999888777666555444", name="Another Server"
        )

        assert str(guild) == "Another Server (999888777666555444)"

    def test_discord_user_str_method(self):
        """Test Discord user string representation."""
        user = DiscordUser.objects.create(
            user_id="111222333444555666", username="newuser", display_name="New User"
        )

        assert str(user) == "New User (111222333444555666)"

    def test_discord_channel_str_method(self):
        """Test Discord channel string representation."""
        channel = DiscordChannel.objects.create(
            channel_id="777888999000111222",
            guild=self.guild,
            name="testing",
            channel_type="text",
        )

        assert str(channel) == "#testing (Test Server)"


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
        assert response.status_code == HTTP_REDIRECT_STATUS  # Redirect to login

    @skip_discord_api_dependent
    @patch("user_stats.views.get_user_guilds")
    def test_dashboard_access_with_login(self, mock_get_guilds):
        """Test dashboard access with authenticated user."""

        mock_get_guilds.side_effect = DiscordAPIError("No Discord token available")

        self.client.force_login(self.user)

        # When DiscordAPIError is raised, should redirect to servers dashboard
        response = self.client.get(reverse("user_stats:dashboard"))
        assert (
            response.status_code == HTTP_REDIRECT_STATUS
        )  # Redirect to servers dashboard

    def test_api_endpoint_requires_login(self):
        """Test API endpoint requires authentication."""
        response = self.client.get(
            reverse("user_stats:api_guild_stats", args=[123456789012345678])
        )
        assert response.status_code == HTTP_REDIRECT_STATUS  # Redirect to login

    def test_user_detail_requires_login(self):
        """Test user detail requires authentication."""
        response = self.client.get(
            reverse(
                "user_stats:user_detail",
                args=[123456789012345678, "987654321098765432"],
            )
        )
        assert response.status_code == HTTP_REDIRECT_STATUS  # Redirect to login
