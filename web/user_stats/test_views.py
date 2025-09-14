"""
Comprehensive tests for user stats views.

This module provides thorough test coverage for user statistics view functions
including dashboards, detailed stats, and API endpoints.
"""

import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from shared.test_utils import skip_complex_integration, skip_discord_api_dependent

from .models import DailyMessageStatistics, MessageStatistics

User = get_user_model()


class UserStatsViewsTestCase(TestCase):
    """Test cases for user stats views."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        self.guild_id = 123456789012345678
        self.user_id = 987654321012345678
        self.channel_id = 555666777012345678

        # Create Discord entities with proper relationships
        from user_stats.models import DiscordChannel, DiscordGuild, DiscordUser

        # Create Discord user
        self.discord_user = DiscordUser.objects.create(
            user_id=str(self.user_id),
            username='testdiscorduser',
            display_name='Test Discord User'
        )

        # Create Discord guild
        self.discord_guild = DiscordGuild.objects.create(
            guild_id=str(self.guild_id),
            name='Test Server'
        )

        # Create Discord channel
        self.discord_channel = DiscordChannel.objects.create(
            channel_id=str(self.channel_id),
            guild=self.discord_guild,
            name='test-channel'
        )

        # Create test message statistics
        self.message_stats = MessageStatistics.objects.create(
            user=self.discord_user,
            channel=self.discord_channel,
            total_messages=100,
            messages_last_7_days=15,
            messages_last_30_days=45,
            messages_last_90_days=85
        )

    @skip_discord_api_dependent
    @patch('user_stats.views.get_user_guilds')
    def test_user_stats_dashboard_success(self, mock_get_guilds):
        """Test successful user stats dashboard access."""
        self.client.login(username='testuser', password='testpassword')

        mock_get_guilds.return_value = [
            {
                'id': str(self.guild_id),
                'name': 'Test Server',
                'permissions': str(0x8)
            }
        ]

        response = self.client.get(reverse('user_stats:dashboard'))
        assert response.status_code == 200
        self.assertContains(response, 'User Statistics Dashboard')

    @skip_discord_api_dependent
    @patch('user_stats.views.get_user_guilds')
    def test_user_stats_dashboard_no_guilds(self, mock_get_guilds):
        """Test user stats dashboard when user has no guilds."""
        self.client.login(username='testuser', password='testpassword')

        mock_get_guilds.return_value = []  # No guilds

        response = self.client.get(reverse('user_stats:dashboard'))
        assert response.status_code == 200
        self.assertContains(response, 'No servers')

    @skip_discord_api_dependent
    @patch('user_stats.views.get_user_guilds')
    def test_guild_user_stats_success(self, mock_get_guilds):
        """Test guild user stats view with valid access."""
        self.client.login(username='testuser', password='testpassword')

        mock_get_guilds.return_value = [
            {
                'id': str(self.guild_id),
                'name': 'Test Server',
                'permissions': str(0x8)
            }
        ]

        response = self.client.get(reverse('user_stats:guild_stats', args=[self.guild_id]))
        assert response.status_code == 200
        self.assertContains(response, 'Test Server')

    @skip_discord_api_dependent
    @patch('user_stats.views.get_user_guilds')
    def test_guild_user_stats_no_access(self, mock_get_guilds):
        """Test guild user stats when user has no access to server."""
        self.client.login(username='testuser', password='testpassword')

        mock_get_guilds.return_value = []  # No guilds

        response = self.client.get(reverse('user_stats:guild_stats', args=[self.guild_id]))
        assert response.status_code == 404

    @skip_discord_api_dependent
    @patch('user_stats.views.get_user_guilds')
    def test_guild_user_stats_time_range_filter(self, mock_get_guilds):
        """Test guild user stats with time range filtering."""
        self.client.login(username='testuser', password='testpassword')

        mock_get_guilds.return_value = [
            {
                'id': str(self.guild_id),
                'name': 'Test Server',
                'permissions': str(0x8)
            }
        ]

        # Test different time ranges
        time_ranges = ['7days', '30days', '90days', 'all_time']
        for time_range in time_ranges:
            response = self.client.get(
                reverse('user_stats:guild_stats', args=[self.guild_id]),
                {'time_range': time_range}
            )
            assert response.status_code == 200

    @skip_discord_api_dependent
    @patch('user_stats.views.get_user_guilds')
    def test_user_detail_stats_success(self, mock_get_guilds):
        """Test user detail stats view."""
        self.client.login(username='testuser', password='testpassword')

        mock_get_guilds.return_value = [
            {
                'id': str(self.guild_id),
                'name': 'Test Server',
                'permissions': str(0x8)
            }
        ]

        response = self.client.get(
            reverse('user_stats:user_detail', args=[self.guild_id, self.user_id])
        )
        assert response.status_code == 200
        self.assertContains(response, 'User Statistics')

    @skip_discord_api_dependent
    @patch('user_stats.views.get_user_guilds')
    def test_multi_user_channel_stats_success(self, mock_get_guilds):
        """Test multi-user channel stats view."""
        self.client.login(username='testuser', password='testpassword')

        mock_get_guilds.return_value = [
            {
                'id': str(self.guild_id),
                'name': 'Test Server',
                'permissions': str(0x8)
            }
        ]

        response = self.client.get(reverse('user_stats:multi_user_channel', args=[self.guild_id]))
        assert response.status_code == 200
        self.assertContains(response, 'Multi-User Channel Analysis')

    @skip_discord_api_dependent
    @patch('user_stats.views.get_user_guilds')
    def test_api_guild_stats_json(self, mock_get_guilds):
        """Test API endpoint for guild stats JSON data."""
        self.client.login(username='testuser', password='testpassword')

        mock_get_guilds.return_value = [
            {
                'id': str(self.guild_id),
                'name': 'Test Server',
                'permissions': str(0x8)
            }
        ]

        response = self.client.get(reverse('user_stats:api_guild_stats', args=[self.guild_id]))
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/json'

        data = json.loads(response.content)
        assert 'users' in data
        assert 'channels' in data

    @skip_discord_api_dependent
    @patch('user_stats.views.get_user_guilds')
    def test_api_guild_stats_with_filters(self, mock_get_guilds):
        """Test API endpoint with various filters."""
        self.client.login(username='testuser', password='testpassword')

        mock_get_guilds.return_value = [
            {
                'id': str(self.guild_id),
                'name': 'Test Server',
                'permissions': str(0x8)
            }
        ]

        # Test with time range filter
        response = self.client.get(
            reverse('user_stats:api_guild_stats', args=[self.guild_id]),
            {'time_range': '7days', 'sort': 'activity'}
        )
        assert response.status_code == 200

        data = json.loads(response.content)
        assert 'users' in data

    @skip_discord_api_dependent
    @patch('user_stats.views.get_user_guilds')
    def test_live_stats_update_success(self, mock_get_guilds):
        """Test live stats update view."""
        self.client.login(username='testuser', password='testpassword')

        mock_get_guilds.return_value = [
            {
                'id': str(self.guild_id),
                'name': 'Test Server',
                'permissions': str(0x8)
            }
        ]

        response = self.client.get(reverse('user_stats:live_stats', args=[self.guild_id]))
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/json'

    @skip_complex_integration
    def test_unauthenticated_access_denied(self):
        """Test that unauthenticated users cannot access user stats views."""
        response = self.client.get(reverse('user_stats:dashboard'))
        assert response.status_code == 302  # Redirect to login

    @skip_discord_api_dependent
    @patch('user_stats.views.get_user_guilds')
    def test_discord_api_error_handling(self, mock_get_guilds):
        """Test handling of Discord API errors in user stats views."""
        self.client.login(username='testuser', password='testpassword')

        from shared.discord_api import DiscordAPIError
        mock_get_guilds.side_effect = DiscordAPIError("API Error")

        response = self.client.get(reverse('user_stats:dashboard'))
        assert response.status_code == 200  # Should handle error gracefully

    @skip_complex_integration
    def test_message_field_for_time_range(self):
        """Test utility function for getting message field for time range."""
        from user_stats.views import _get_message_field_for_time_range

        assert _get_message_field_for_time_range('7days') == 'messages_last_7_days'
        assert _get_message_field_for_time_range('30days') == 'messages_last_30_days'
        assert _get_message_field_for_time_range('90days') == 'messages_last_90_days'
        assert _get_message_field_for_time_range('all_time') == 'total_messages'
        assert _get_message_field_for_time_range('invalid') == 'total_messages'

    @skip_complex_integration
    def test_get_period_field(self):
        """Test utility function for getting period field."""
        from user_stats.views import _get_period_field

        assert _get_period_field('day') == '__date'
        assert _get_period_field('week') == '__week'
        assert _get_period_field('month') == '__month'

    @skip_complex_integration
    def test_determine_activity_level(self):
        """Test utility function for determining activity level."""
        from user_stats.views import _determine_activity_level

        # Test with high activity user
        high_activity_stats = {'messages_last_7_days': 100}
        activity_level = _determine_activity_level(high_activity_stats, '7days')
        assert activity_level == 'high'

        # Test with low activity user
        low_activity_stats = {'messages_last_7_days': 1}
        activity_level = _determine_activity_level(low_activity_stats, '7days')
        assert activity_level == 'low'

    @skip_complex_integration
    def test_sort_users_by_activity(self):
        """Test utility function for sorting users by activity."""
        from user_stats.views import _sort_users_by_activity

        users_data = [
            {'messages_last_7_days': 50, 'username': 'user1'},
            {'messages_last_7_days': 100, 'username': 'user2'},
            {'messages_last_7_days': 25, 'username': 'user3'},
        ]

        sorted_users = _sort_users_by_activity(users_data, '7days')

        # Should be sorted by activity (descending)
        assert sorted_users[0]['username'] == 'user2'  # 100 messages
        assert sorted_users[1]['username'] == 'user1'  # 50 messages
        assert sorted_users[2]['username'] == 'user3'  # 25 messages

    @skip_discord_api_dependent
    @patch('user_stats.views.get_user_guilds')
    def test_guild_stats_invalid_time_range(self, mock_get_guilds):
        """Test guild stats with invalid time range parameter."""
        self.client.login(username='testuser', password='testpassword')

        mock_get_guilds.return_value = [
            {
                'id': str(self.guild_id),
                'name': 'Test Server',
                'permissions': str(0x8)
            }
        ]

        response = self.client.get(
            reverse('user_stats:guild_stats', args=[self.guild_id]),
            {'time_range': 'invalid_range'}
        )
        assert response.status_code == 200  # Should handle gracefully

    @skip_discord_api_dependent
    @patch('user_stats.views.get_user_guilds')
    def test_user_detail_stats_with_daily_data(self, mock_get_guilds):
        """Test user detail stats when daily message data exists."""
        self.client.login(username='testuser', password='testpassword')

        # Create daily message statistics
        DailyMessageStatistics.objects.create(
            user=self.discord_user,
            channel=self.discord_channel,
            date='2024-01-01',
            message_count=10
        )

        mock_get_guilds.return_value = [
            {
                'id': str(self.guild_id),
                'name': 'Test Server',
                'permissions': str(0x8)
            }
        ]

        response = self.client.get(
            reverse('user_stats:user_detail', args=[self.guild_id, self.user_id])
        )
        assert response.status_code == 200

    @skip_complex_integration
    def test_clear_user_stats_cache(self):
        """Test cache clearing utility function."""
        from user_stats.views import clear_user_stats_cache

        # Test cache clearing (should not raise exceptions)
        clear_user_stats_cache(self.user)
        clear_user_stats_cache(self.user, guild_id=self.guild_id)

    @skip_discord_api_dependent
    @patch('user_stats.views.get_user_guilds')
    def test_build_base_queryset(self, mock_get_guilds):
        """Test base queryset building utility function."""
        mock_get_guilds.return_value = [
            {'id': str(self.guild_id), 'name': 'Test Server'}
        ]

        from user_stats.views import _build_base_queryset

        # Test with valid guild
        queryset = _build_base_queryset(self.guild_id, self.user_id)
        assert queryset is not None

        # Test with all guilds (None)
        queryset = _build_base_queryset(None, self.user_id)
        assert queryset is not None

    @skip_complex_integration
    def test_get_user_statistics(self):
        """Test user statistics gathering utility function."""
        from user_stats.models import MessageStatistics
        from user_stats.views import _get_user_statistics

        # Create a queryset
        queryset = MessageStatistics.objects.filter(user=self.discord_user)

        # Test statistics calculation
        stats = _get_user_statistics(queryset, 'total_messages')

        # Should return dictionary with user statistics
        assert isinstance(stats, dict)

    @skip_complex_integration
    def test_get_channel_statistics(self):
        """Test channel statistics gathering utility function."""
        from user_stats.models import MessageStatistics
        from user_stats.views import _get_channel_statistics

        # Create a queryset
        queryset = MessageStatistics.objects.filter(channel=self.discord_channel)

        # Test channel statistics calculation
        stats = _get_channel_statistics(queryset, 'total_messages')

        # Should return dictionary with channel statistics
        assert isinstance(stats, dict)

    @skip_complex_integration
    def test_get_available_users(self):
        """Test available users utility function."""
        from user_stats.views import _get_available_users

        # Test getting available users for guild
        users = _get_available_users(self.discord_guild)

        # Should return queryset of users
        assert len(users) == 1
        assert users[0] == self.discord_user

    @skip_complex_integration
    def test_get_available_channels(self):
        """Test available channels utility function."""
        from user_stats.views import _get_available_channels

        # Test getting available channels for guild
        channels = _get_available_channels(self.discord_guild)

        # Should return queryset of channels
        assert len(channels) == 1
        assert channels[0] == self.discord_channel

    @skip_complex_integration
    def test_sort_users_by_activity_edge_cases(self):
        """Test activity sorting with edge cases."""
        from user_stats.views import _sort_users_by_activity

        # Test with empty data
        empty_result = _sort_users_by_activity([], '7days')
        assert empty_result == []

        # Test with single user
        single_user = [{'messages_last_7_days': 50, 'username': 'user1'}]
        result = _sort_users_by_activity(single_user, '7days')
        assert len(result) == 1

    @skip_complex_integration
    def test_determine_activity_level_edge_cases(self):
        """Test activity level determination with edge cases."""
        from user_stats.views import _determine_activity_level

        # Test with zero messages
        zero_stats = {'messages_last_7_days': 0}
        level = _determine_activity_level(zero_stats, '7days')
        assert level == 'low'

        # Test with missing field
        empty_stats = {}
        level = _determine_activity_level(empty_stats, '7days')
        assert level == 'low'

        # Test with very high activity
        high_stats = {'total_messages': 10000}
        level = _determine_activity_level(high_stats, 'all_time')
        assert level == 'high'

    @skip_discord_api_dependent
    @patch('user_stats.views.get_user_guilds')
    def test_multi_user_channel_data(self, mock_get_guilds):
        """Test multi-user channel data utility function."""
        mock_get_guilds.return_value = [
            {'id': str(self.guild_id), 'name': 'Test Server'}
        ]

        from user_stats.views import _get_multi_user_channel_data

        # Test getting multi-user channel data
        data = _get_multi_user_channel_data(self.guild_id, '7days')

        # Should return dictionary with channel analysis data
        assert isinstance(data, dict)
        assert 'channels' in data
        assert 'users' in data

    @skip_discord_api_dependent
    @patch('user_stats.views.get_user_guilds')
    def test_api_guild_stats_invalid_sort(self, mock_get_guilds):
        """Test API guild stats with invalid sort parameter."""
        self.client.login(username='testuser', password='testpassword')

        mock_get_guilds.return_value = [
            {
                'id': str(self.guild_id),
                'name': 'Test Server',
                'permissions': str(0x8)
            }
        ]

        response = self.client.get(
            reverse('user_stats:api_guild_stats', args=[self.guild_id]),
            {'sort': 'invalid_sort_option'}
        )
        assert response.status_code == 200

        data = json.loads(response.content)
        # Should handle invalid sort gracefully
        assert 'users' in data
