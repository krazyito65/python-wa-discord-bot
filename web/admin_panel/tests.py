"""
Tests for admin panel models.

This module provides comprehensive test coverage for admin panel model functionality
including configuration validation, permission logic, and audit logging.
"""

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from .models import ServerPermissionConfig, ServerPermissionLog


class ServerPermissionConfigTest(TestCase):
    """Test cases for ServerPermissionConfig model."""

    def setUp(self):
        """Set up test data."""
        self.guild_id = "123456789012345678"
        self.guild_name = "Test Server"

    def test_server_config_creation(self):
        """Test basic server configuration creation."""
        config = ServerPermissionConfig.objects.create(
            guild_id=self.guild_id,
            guild_name=self.guild_name,
            updated_by="987654321098765432",
            updated_by_name="Test User"
        )

        assert config.guild_id == self.guild_id
        assert config.guild_name == self.guild_name
        assert config.admin_panel_access == 'admin_only'  # Default
        assert config.create_macros == 'admin_only'  # Default
        assert config.edit_macros == 'admin_only'  # Default
        assert config.delete_macros == 'admin_only'  # Default
        assert config.use_macros == 'everyone'  # Default
        assert config.require_discord_permissions is True  # Default

    def test_server_config_str_representation(self):
        """Test string representation of server config."""
        config = ServerPermissionConfig.objects.create(
            guild_id=self.guild_id,
            guild_name=self.guild_name,
            updated_by="987654321098765432",
            updated_by_name="Test User"
        )

        assert str(config) == f"Test Server ({self.guild_id}) - Permission Config"

    def test_server_config_custom_permissions(self):
        """Test server configuration with custom permissions."""
        config = ServerPermissionConfig.objects.create(
            guild_id=self.guild_id,
            guild_name=self.guild_name,
            admin_panel_access='moderators',
            create_macros='trusted_users',
            edit_macros='everyone',
            delete_macros='server_owner',
            use_macros='everyone',
            updated_by="987654321098765432",
            updated_by_name="Test User"
        )

        assert config.admin_panel_access == 'moderators'
        assert config.create_macros == 'trusted_users'
        assert config.edit_macros == 'everyone'
        assert config.delete_macros == 'server_owner'
        assert config.use_macros == 'everyone'

    def test_server_config_custom_roles_json(self):
        """Test server configuration with custom roles JSON fields."""
        custom_admin_roles = ["admin", "owner"]
        custom_create_roles = ["creator", "moderator"]

        config = ServerPermissionConfig.objects.create(
            guild_id=self.guild_id,
            guild_name=self.guild_name,
            admin_panel_access='custom_roles',
            create_macros='custom_roles',
            custom_admin_panel_roles=custom_admin_roles,
            custom_create_roles=custom_create_roles,
            updated_by="987654321098765432",
            updated_by_name="Test User"
        )

        assert config.custom_admin_panel_roles == custom_admin_roles
        assert config.custom_create_roles == custom_create_roles

    def test_server_config_role_lists(self):
        """Test server configuration role list fields."""
        trusted_roles = ["trusted", "vip"]
        moderator_roles = ["mod", "moderator"]
        admin_roles = ["admin", "administrator"]

        config = ServerPermissionConfig.objects.create(
            guild_id=self.guild_id,
            guild_name=self.guild_name,
            trusted_user_roles=trusted_roles,
            moderator_roles=moderator_roles,
            admin_roles=admin_roles,
            updated_by="987654321098765432",
            updated_by_name="Test User"
        )

        assert config.trusted_user_roles == trusted_roles
        assert config.moderator_roles == moderator_roles
        assert config.admin_roles == admin_roles

    def test_server_config_timestamps(self):
        """Test automatic timestamp management."""
        config = ServerPermissionConfig.objects.create(
            guild_id=self.guild_id,
            guild_name=self.guild_name,
            updated_by="987654321098765432",
            updated_by_name="Test User"
        )

        assert config.created_at is not None
        assert config.updated_at is not None
        assert config.created_at <= config.updated_at

        # Test update timestamp changes
        original_updated = config.updated_at
        config.guild_name = "Updated Server Name"
        config.save()

        assert config.updated_at > original_updated

    def test_server_config_unique_guild_constraint(self):
        """Test unique constraint on guild_id."""
        ServerPermissionConfig.objects.create(
            guild_id=self.guild_id,
            guild_name=self.guild_name,
            updated_by="987654321098765432",
            updated_by_name="Test User"
        )

        # Attempting to create another config with same guild_id should fail
        with self.assertRaises(Exception):  # IntegrityError
            ServerPermissionConfig.objects.create(
                guild_id=self.guild_id,
                guild_name="Different Server Name",
                updated_by="111111111111111111",
                updated_by_name="Different User"
            )


class ServerPermissionLogTest(TestCase):
    """Test cases for ServerPermissionLog model."""

    def setUp(self):
        """Set up test data."""
        self.server_config = ServerPermissionConfig.objects.create(
            guild_id="123456789012345678",
            guild_name="Test Server",
            updated_by="987654321098765432",
            updated_by_name="Test User"
        )

    def test_permission_log_creation(self):
        """Test basic permission log creation."""
        log_entry = ServerPermissionLog.objects.create(
            server_config=self.server_config,
            action='updated',
            field_changed='create_macros',
            old_value='admin_only',
            new_value='moderators',
            changed_by="987654321098765432",
            changed_by_name="Test User",
            user_agent="TestAgent/1.0",
            ip_address="127.0.0.1"
        )

        assert log_entry.server_config == self.server_config
        assert log_entry.action == 'updated'
        assert log_entry.field_changed == 'create_macros'
        assert log_entry.old_value == 'admin_only'
        assert log_entry.new_value == 'moderators'
        assert log_entry.changed_by == "987654321098765432"
        assert log_entry.changed_by_name == "Test User"
        assert log_entry.user_agent == "TestAgent/1.0"
        assert log_entry.ip_address == "127.0.0.1"
        assert log_entry.timestamp is not None

    def test_permission_log_str_representation(self):
        """Test string representation of permission log."""
        log_entry = ServerPermissionLog.objects.create(
            server_config=self.server_config,
            action='updated',
            field_changed='create_macros',
            old_value='admin_only',
            new_value='moderators',
            changed_by="987654321098765432",
            changed_by_name="Test User",
            user_agent="TestAgent/1.0"
        )

        # Test that string representation contains expected components
        log_str = str(log_entry)
        assert "Test Server" in log_str
        assert "Test User" in log_str
        assert "Configuration Updated" in log_str

    def test_permission_log_different_actions(self):
        """Test permission log with different action types."""
        actions = ['created', 'updated', 'permission_changed', 'roles_updated']

        for action in actions:
            log_entry = ServerPermissionLog.objects.create(
                server_config=self.server_config,
                action=action,
                field_changed='admin_panel_access',
                old_value='admin_only',
                new_value='moderators',
                changed_by="987654321098765432",
                changed_by_name="Test User",
                user_agent="TestAgent/1.0"
            )

            assert log_entry.action == action

    def test_permission_log_optional_ip_address(self):
        """Test permission log without IP address."""
        log_entry = ServerPermissionLog.objects.create(
            server_config=self.server_config,
            action='updated',
            field_changed='create_macros',
            old_value='admin_only',
            new_value='moderators',
            changed_by="987654321098765432",
            changed_by_name="Test User",
            user_agent="TestAgent/1.0"
            # ip_address is optional
        )

        assert log_entry.ip_address is None

    def test_permission_log_relationship(self):
        """Test relationship between log and server config."""
        log_entry = ServerPermissionLog.objects.create(
            server_config=self.server_config,
            action='updated',
            field_changed='create_macros',
            old_value='admin_only',
            new_value='moderators',
            changed_by="987654321098765432",
            changed_by_name="Test User",
            user_agent="TestAgent/1.0"
        )

        # Test forward relationship
        assert log_entry.server_config.guild_id == "123456789012345678"

        # Test reverse relationship
        logs = self.server_config.permission_logs.all()
        assert log_entry in logs
        assert len(logs) == 1