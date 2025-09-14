"""
Models for server-specific administrative settings and permissions.

This module defines models for configuring per-server permissions for macro
management and other administrative functions, including who can access
the admin panel itself.
"""

from django.db import models
from django.utils import timezone

# Discord permission constants
DISCORD_ADMINISTRATOR_PERMISSION = 0x8
DISCORD_MANAGE_SERVER_PERMISSION = 0x20


class ServerPermissionConfig(models.Model):
    """Configuration for server-specific permissions and settings."""

    # Server identification
    guild_id = models.CharField(
        max_length=20, unique=True, help_text="Discord guild/server ID"
    )
    guild_name = models.CharField(
        max_length=100, help_text="Discord guild/server name (cached for display)"
    )

    # Permission level choices
    PERMISSION_CHOICES = [
        ("admin_only", "Administrators Only"),
        ("moderators", "Moderators and Administrators"),
        ("trusted_users", "Trusted Users and Above"),
        ("everyone", "Everyone"),
        ("custom_roles", "Custom Roles Only"),
        ("server_owner", "Server Owner Only"),
    ]

    # Admin panel access control
    admin_panel_access = models.CharField(
        max_length=20,
        choices=PERMISSION_CHOICES,
        default="admin_only",
        help_text="Who can access the admin panel for this server",
    )

    # Macro management permissions
    create_macros = models.CharField(
        max_length=20,
        choices=PERMISSION_CHOICES,
        default="admin_only",
        help_text="Who can create new macros",
    )
    edit_macros = models.CharField(
        max_length=20,
        choices=PERMISSION_CHOICES,
        default="admin_only",
        help_text="Who can edit existing macros",
    )
    delete_macros = models.CharField(
        max_length=20,
        choices=PERMISSION_CHOICES,
        default="admin_only",
        help_text="Who can delete macros",
    )
    use_macros = models.CharField(
        max_length=20,
        choices=PERMISSION_CHOICES,
        default="everyone",
        help_text="Who can use/execute macros",
    )

    # Custom role-based permissions (JSON field for flexibility)
    custom_admin_panel_roles = models.JSONField(
        default=list,
        blank=True,
        help_text="Custom role names that can access admin panel (case-insensitive)",
    )
    custom_create_roles = models.JSONField(
        default=list,
        blank=True,
        help_text="Custom role names that can create macros (case-insensitive)",
    )
    custom_edit_roles = models.JSONField(
        default=list,
        blank=True,
        help_text="Custom role names that can edit macros (case-insensitive)",
    )
    custom_delete_roles = models.JSONField(
        default=list,
        blank=True,
        help_text="Custom role names that can delete macros (case-insensitive)",
    )
    custom_use_roles = models.JSONField(
        default=list,
        blank=True,
        help_text="Custom role names that can use macros (case-insensitive)",
    )

    # Discord permission-based settings
    require_discord_permissions = models.BooleanField(
        default=True,
        help_text="Also check Discord permissions (Administrator, Manage Server, etc.)",
    )

    # Role hierarchy settings
    trusted_user_roles = models.JSONField(
        default=list,
        blank=True,
        help_text="Role names considered 'trusted users' (case-insensitive)",
    )

    moderator_roles = models.JSONField(
        default=list, help_text="Role names considered 'moderators' (case-insensitive)"
    )

    admin_roles = models.JSONField(
        default=list,
        help_text="Role names considered 'administrators' (case-insensitive)",
    )

    # Metadata
    created_at = models.DateTimeField(
        default=timezone.now, help_text="When this configuration was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True, help_text="When this configuration was last updated"
    )
    updated_by = models.CharField(
        max_length=20, help_text="Discord user ID who last updated this config"
    )
    updated_by_name = models.CharField(
        max_length=100,
        default="",
        help_text="Discord username who last updated this config",
    )

    class Meta:
        verbose_name = "Server Permission Configuration"
        verbose_name_plural = "Server Permission Configurations"
        ordering = ["guild_name"]

    def save(self, *args, **kwargs):
        """Override save to set default role values if not already set."""
        # Set default moderator roles if empty
        if not self.moderator_roles:
            self.moderator_roles = ["moderator", "mod"]

        # Set default admin roles if empty
        if not self.admin_roles:
            self.admin_roles = ["administrator", "admin"]

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.guild_name} ({self.guild_id}) - Permission Config"

    def get_permission_level_display(self, permission_type: str) -> str:
        """Get human-readable display for a permission level."""
        permission_value = getattr(self, permission_type, "admin_only")
        return dict(self.PERMISSION_CHOICES).get(permission_value, permission_value)

    def has_permission(
        self,
        user_roles: list[str],
        permission_type: str,
        guild_permissions: int = 0,
        is_server_owner: bool = False,
    ) -> bool:
        """
        Check if a user has the specified permission based on their roles and Discord permissions.

        Args:
            user_roles: List of role names the user has in the server (case-insensitive)
            permission_type: Type of permission to check ('create_macros', 'edit_macros', etc.)
            guild_permissions: User's Discord permissions in the server (as integer)
            is_server_owner: Whether the user is the server owner

        Returns:
            bool: True if user has the specified permission, False otherwise
        """
        permission_level = getattr(self, permission_type, "admin_only")
        user_roles_lower = [role.lower() for role in user_roles]

        # Server owner always has access (unless permission is set to a restrictive custom role)
        if is_server_owner and permission_level != "custom_roles":
            return True

        # Check for server_owner permission level
        if permission_level == "server_owner":
            return is_server_owner

        # Check Discord permissions if enabled
        if self.require_discord_permissions:
            # Administrator permission always grants access
            if (
                guild_permissions & DISCORD_ADMINISTRATOR_PERMISSION
            ) == DISCORD_ADMINISTRATOR_PERMISSION:
                return True

            # Manage Server permission grants admin-level access
            if (
                permission_level in ["admin_only", "moderators", "trusted_users"]
                and (guild_permissions & DISCORD_MANAGE_SERVER_PERMISSION)
                == DISCORD_MANAGE_SERVER_PERMISSION
            ):
                return True

        if permission_level == "everyone":
            return True
        if permission_level == "custom_roles":
            # Get the appropriate custom roles field
            if permission_type == "admin_panel_access":
                custom_roles = [role.lower() for role in self.custom_admin_panel_roles]
            else:
                custom_roles_attr = (
                    f"custom_{permission_type.replace('_macros', '')}_roles"
                )
                custom_roles = [
                    role.lower() for role in getattr(self, custom_roles_attr, [])
                ]
            return any(role in custom_roles for role in user_roles_lower)
        if permission_level == "trusted_users":
            # Check trusted user roles
            trusted_roles = [role.lower() for role in self.trusted_user_roles]
            if any(role in trusted_roles for role in user_roles_lower):
                return True
            # Fall through to check moderators and admins
            return self._check_moderator_or_admin_roles(user_roles_lower)
        if permission_level == "moderators":
            # Check moderators and admins
            return self._check_moderator_or_admin_roles(user_roles_lower)
        if permission_level == "admin_only":
            # Check admin roles only
            admin_roles = [role.lower() for role in self.admin_roles]
            return any(role in admin_roles for role in user_roles_lower)

        return False

    def _check_moderator_or_admin_roles(self, user_roles_lower: list[str]) -> bool:
        """Check if user has moderator or admin roles."""
        moderator_roles = [role.lower() for role in self.moderator_roles]
        admin_roles = [role.lower() for role in self.admin_roles]

        return any(
            role in moderator_roles or role in admin_roles for role in user_roles_lower
        )


class ServerPermissionLog(models.Model):
    """Log of permission configuration changes for auditing purposes."""

    server_config = models.ForeignKey(
        ServerPermissionConfig,
        on_delete=models.CASCADE,
        related_name="permission_logs",
        help_text="The server configuration that was changed",
    )

    ACTION_CHOICES = [
        ("created", "Configuration Created"),
        ("updated", "Configuration Updated"),
        ("permission_changed", "Permission Level Changed"),
        ("roles_updated", "Role Lists Updated"),
        ("admin_access_changed", "Admin Panel Access Changed"),
    ]

    action = models.CharField(
        max_length=25, choices=ACTION_CHOICES, help_text="Type of action performed"
    )

    field_changed = models.CharField(
        max_length=50,
        blank=True,
        help_text="Specific field that was changed (if applicable)",
    )

    old_value = models.TextField(blank=True, help_text="Previous value (JSON format)")

    new_value = models.TextField(blank=True, help_text="New value (JSON format)")

    changed_by = models.CharField(
        max_length=20, help_text="Discord user ID who made the change"
    )

    changed_by_name = models.CharField(
        max_length=100, help_text="Discord username who made the change"
    )

    timestamp = models.DateTimeField(
        default=timezone.now, help_text="When the change was made"
    )

    user_agent = models.CharField(
        max_length=200, blank=True, help_text="User agent of the request"
    )

    ip_address = models.GenericIPAddressField(
        null=True, blank=True, help_text="IP address of the user who made the change"
    )

    class Meta:
        verbose_name = "Server Permission Log"
        verbose_name_plural = "Server Permission Logs"
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.server_config.guild_name} - {self.get_action_display()} by {self.changed_by_name}"
