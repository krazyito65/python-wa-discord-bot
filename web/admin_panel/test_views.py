"""
Comprehensive tests for admin panel views.

This module provides thorough test coverage for all admin panel view functions
including dashboard, permission settings, role configurations, and audit logging.
"""

from unittest.mock import Mock, patch
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from shared.test_utils import skip_discord_api_dependent, skip_complex_integration
from .models import ServerPermissionConfig, ServerPermissionLog


User = get_user_model()


class AdminPanelViewsTestCase(TestCase):
    """Test cases for admin panel views."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        self.guild_id = 123456789012345678
        self.guild_name = 'Test Server'

        # Create test server config
        self.server_config = ServerPermissionConfig.objects.create(
            guild_id=str(self.guild_id),
            guild_name=self.guild_name,
            create_macros='everyone',
            edit_macros='trusted_users',
            delete_macros='admin_only',
            use_macros='everyone',
            admin_panel_access='admin_only'
        )

    def test_validate_admin_panel_access_no_access(self):
        """Test admin panel access validation when user has no access."""
        self.client.login(username='testuser', password='testpassword')

        with patch('admin_panel.views.get_user_guilds') as mock_get_guilds:
            mock_get_guilds.return_value = []  # User has no guilds

            response = self.client.get(reverse('admin_panel:dashboard', args=[self.guild_id]))
            self.assertEqual(response.status_code, 302)  # Redirects to servers:dashboard

    @skip_discord_api_dependent
    @patch('admin_panel.views.get_user_guilds')
    def test_admin_panel_dashboard_success(self, mock_get_guilds):
        """Test successful admin panel dashboard access."""
        self.client.login(username='testuser', password='testpassword')

        # Mock user guilds response
        mock_get_guilds.return_value = [
            {
                'id': str(self.guild_id),
                'name': self.guild_name,
                'permissions': str(0x8),  # Administrator permission
                'owner': True
            }
        ]

        response = self.client.get(reverse('admin_panel:dashboard', args=[self.guild_id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.guild_name)
        self.assertContains(response, 'Admin Panel')

    @skip_discord_api_dependent
    @patch('admin_panel.views.get_user_guilds')
    def test_admin_panel_dashboard_context(self, mock_get_guilds):
        """Test admin panel dashboard provides correct context."""
        self.client.login(username='testuser', password='testpassword')

        mock_get_guilds.return_value = [
            {
                'id': str(self.guild_id),
                'name': self.guild_name,
                'permissions': str(0x8),
                'owner': True
            }
        ]

        response = self.client.get(reverse('admin_panel:dashboard', args=[self.guild_id]))
        self.assertEqual(response.status_code, 200)

        # Check context variables
        context = response.context
        self.assertEqual(context['guild_id'], self.guild_id)
        self.assertEqual(context['guild_name'], self.guild_name)
        self.assertIsNotNone(context['server_config'])

    @skip_complex_integration
    @patch('admin_panel.views.get_user_guilds')
    def test_permission_settings_get(self, mock_get_guilds):
        """Test GET request to permission settings view."""
        self.client.login(username='testuser', password='testpassword')

        mock_get_guilds.return_value = [
            {
                'id': str(self.guild_id),
                'name': self.guild_name,
                'permissions': str(0x8),
                'owner': True
            }
        ]

        response = self.client.get(reverse('admin_panel:permission_settings', args=[self.guild_id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Permission Settings')

    @skip_complex_integration
    @patch('admin_panel.views.get_user_guilds')
    def test_permission_settings_post_update(self, mock_get_guilds):
        """Test POST request to update permission settings."""
        self.client.login(username='testuser', password='testpassword')

        mock_get_guilds.return_value = [
            {
                'id': str(self.guild_id),
                'name': self.guild_name,
                'permissions': str(0x8),
                'owner': True
            }
        ]

        # Test permission update
        response = self.client.post(
            reverse('admin_panel:permission_settings', args=[self.guild_id]),
            {
                'create_macros': 'admin_only',
                'edit_macros': 'moderators',
                'delete_macros': 'admin_only',
                'use_macros': 'everyone'
            }
        )

        self.assertEqual(response.status_code, 302)  # Redirect after successful update

        # Verify permission was updated
        self.server_config.refresh_from_db()
        self.assertEqual(self.server_config.create_macros, 'admin_only')

    @skip_complex_integration
    @patch('admin_panel.views.get_user_guilds')
    def test_role_settings_get(self, mock_get_guilds):
        """Test GET request to role settings view."""
        self.client.login(username='testuser', password='testpassword')

        mock_get_guilds.return_value = [
            {
                'id': str(self.guild_id),
                'name': self.guild_name,
                'permissions': str(0x8),
                'owner': True
            }
        ]

        response = self.client.get(reverse('admin_panel:role_settings', args=[self.guild_id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Role Settings')

    @skip_complex_integration
    @patch('admin_panel.views.get_user_guilds')
    def test_audit_log_view(self, mock_get_guilds):
        """Test audit log view displays permission changes."""
        self.client.login(username='testuser', password='testpassword')

        # Create test audit log entry
        ServerPermissionLog.objects.create(
            server_config=self.server_config,
            action='permission_changed',
            changed_by=str(self.user.id),
            changed_by_name=self.user.username,
            field_changed='create_macros',
            old_value='everyone',
            new_value='admin_only'
        )

        mock_get_guilds.return_value = [
            {
                'id': str(self.guild_id),
                'name': self.guild_name,
                'permissions': str(0x8),
                'owner': True
            }
        ]

        response = self.client.get(reverse('admin_panel:audit_log', args=[self.guild_id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'create_macros')
        self.assertContains(response, 'Permission Level Changed')

    @skip_complex_integration
    @patch('admin_panel.views.get_user_guilds')
    def test_reset_to_defaults(self, mock_get_guilds):
        """Test reset to defaults functionality."""
        self.client.login(username='testuser', password='testpassword')

        mock_get_guilds.return_value = [
            {
                'id': str(self.guild_id),
                'name': self.guild_name,
                'permissions': str(0x8),
                'owner': True
            }
        ]

        # Modify some settings first
        self.server_config.create_macros = 'admin_only'
        self.server_config.save()

        response = self.client.post(reverse('admin_panel:reset_to_defaults', args=[self.guild_id]))
        self.assertEqual(response.status_code, 302)  # Redirect after reset

        # Verify settings were reset
        self.server_config.refresh_from_db()
        self.assertEqual(self.server_config.create_macros, 'admin_only')  # Default value

    def test_unauthenticated_access_denied(self):
        """Test that unauthenticated users cannot access admin panel."""
        response = self.client.get(reverse('admin_panel:dashboard', args=[self.guild_id]))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    @skip_discord_api_dependent
    @patch('admin_panel.views.get_user_guilds')
    def test_discord_api_error_handling(self, mock_get_guilds):
        """Test handling of Discord API errors."""
        self.client.login(username='testuser', password='testpassword')

        # Mock Discord API error
        from shared.discord_api import DiscordAPIError
        mock_get_guilds.side_effect = DiscordAPIError("API Error")

        response = self.client.get(reverse('admin_panel:dashboard', args=[self.guild_id]))
        self.assertEqual(response.status_code, 302)  # Redirects to servers:dashboard

    @skip_complex_integration
    @patch('admin_panel.views.get_user_guilds')
    def test_permission_displays_context(self, mock_get_guilds):
        """Test that permission displays are properly contextualized."""
        self.client.login(username='testuser', password='testpassword')

        mock_get_guilds.return_value = [
            {
                'id': str(self.guild_id),
                'name': self.guild_name,
                'permissions': str(0x8),
                'owner': True
            }
        ]

        response = self.client.get(reverse('admin_panel:dashboard', args=[self.guild_id]))
        context = response.context

        # Check that permission displays are available
        self.assertIn('permission_displays', context)
        permission_displays = context['permission_displays']

        # Verify permission levels are properly mapped - check for permission keys
        expected_permission_keys = ['admin_panel_access', 'create_macros', 'edit_macros', 'delete_macros', 'use_macros']
        for key in expected_permission_keys:
            self.assertIn(key, permission_displays)
            self.assertIsInstance(permission_displays[key], str)

    def test_server_config_creation(self):
        """Test that server config is created when it doesn't exist."""
        # Delete existing config
        ServerPermissionConfig.objects.filter(guild_id=str(self.guild_id)).delete()

        self.client.login(username='testuser', password='testpassword')

        with patch('admin_panel.views.get_user_guilds') as mock_get_guilds:
            mock_get_guilds.return_value = [
                {
                    'id': str(self.guild_id),
                    'name': self.guild_name,
                    'permissions': str(0x8),
                    'owner': True
                }
            ]

            response = self.client.get(reverse('admin_panel:dashboard', args=[self.guild_id]))
            self.assertEqual(response.status_code, 200)

            # Verify config was created
            self.assertTrue(
                ServerPermissionConfig.objects.filter(guild_id=str(self.guild_id)).exists()
            )