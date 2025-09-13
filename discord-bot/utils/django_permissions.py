"""
Django Permission Integration for Discord Bot

This module provides integration with the Django web interface's admin panel
permission system, allowing the Discord bot to use the same server-specific
permission configuration that users set through the web interface.
"""

import json
import sqlite3
from pathlib import Path

import discord
import yaml


def get_django_database_path() -> str | None:
    """Get the Django database path from configuration.

    Returns:
        Optional[str]: Path to Django SQLite database, None if not found.
    """
    try:
        # Try multiple locations for bot configuration
        config_paths = [
            Path("~/.config/weakauras-bot/token.yml").expanduser(),
            Path("~/weakauras-bot-config/token.yml").expanduser(),
            Path("settings/token.yml"),
        ]

        for config_path in config_paths:
            if config_path.exists():
                with open(config_path, encoding="utf-8") as f:
                    config = yaml.safe_load(f)
                    database_url = (
                        config.get("django", {})
                        .get("database_url", "sqlite:///~/weakauras-bot-data/statistics.db")
                    )
                    if database_url.startswith("sqlite:///"):
                        db_path = database_url.replace("sqlite:///", "")
                        # Expand user path if it starts with ~
                        if db_path.startswith("~"):
                            return str(Path(db_path).expanduser())
                        return db_path
                break
    except Exception:
        pass

    # Default fallback to external data directory
    return str(Path("~/weakauras-bot-data/statistics.db").expanduser())


def get_server_permission_config(guild_id: int) -> dict | None:
    """Get server permission configuration from Django database.

    Args:
        guild_id: Discord guild ID to get permissions for.

    Returns:
        Optional[Dict]: Permission configuration dict, None if not found.
    """
    db_path = get_django_database_path()
    if not db_path or not Path(db_path).exists():
        return None

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Access columns by name
        cursor = conn.cursor()

        # Query the admin_panel_serverpermissionconfig table
        cursor.execute(
            """
            SELECT * FROM admin_panel_serverpermissionconfig
            WHERE guild_id = ?
            """,
            (str(guild_id),)
        )

        row = cursor.fetchone()
        conn.close()

        if row:
            # Convert row to dictionary and parse JSON fields
            config = dict(row)

            # Parse JSON fields
            json_fields = [
                'admin_roles',
                'moderator_roles',
                'trusted_user_roles',
                'custom_admin_panel_roles',
                'custom_create_roles',
                'custom_edit_roles',
                'custom_delete_roles',
                'custom_use_roles'
            ]

            for field in json_fields:
                if config.get(field):
                    try:
                        config[field] = json.loads(config[field])
                    except json.JSONDecodeError:
                        config[field] = []
                else:
                    config[field] = []

            return config

    except Exception:
        pass

    return None


def check_server_permission(
    member: discord.Member,
    guild_id: int,
    permission_type: str
) -> bool:
    """Check if a Discord member has the specified permission for a server.

    Args:
        member: Discord member to check permissions for.
        guild_id: Discord guild ID.
        permission_type: Type of permission ('create_macros', 'edit_macros', 'delete_macros', etc.).

    Returns:
        bool: True if user has the specified permission, False otherwise.
    """
    # Get server permission configuration
    config = get_server_permission_config(guild_id)

    if not config:
        # No configuration found, fall back to basic admin checking
        # Check if user is server owner
        if member.guild.owner_id == member.id:
            return True

        # Check for basic Discord admin permissions
        return (
            member.guild_permissions.administrator or
            member.guild_permissions.manage_guild
        )

    # Get permission level for this permission type
    permission_level = config.get(permission_type, 'admin_only')

    # Server owner always has access
    if member.guild.owner_id == member.id:
        return True

    # Check permission levels
    if permission_level == 'everyone':
        return True
    if permission_level == 'server_owner':
        return member.guild.owner_id == member.id
    if permission_level == 'admin_only':
        return _check_admin_access(member, config)
    if permission_level == 'moderators':
        return _check_moderator_access(member, config) or _check_admin_access(member, config)
    if permission_level == 'trusted_users':
        return (
            _check_trusted_user_access(member, config) or
            _check_moderator_access(member, config) or
            _check_admin_access(member, config)
        )
    if permission_level == 'custom_roles':
        custom_field = f'custom_{permission_type.replace("_macros", "").replace("admin_panel_access", "admin_panel")}_roles'
        custom_roles = config.get(custom_field, [])
        return _check_role_access(member, custom_roles)

    return False


def _check_admin_access(member: discord.Member, config: dict) -> bool:
    """Check if member has admin access."""
    # Check Discord permissions first if required
    if config.get('require_discord_permissions', True):
        if member.guild_permissions.administrator:
            return True

    # Check admin roles
    admin_roles = config.get('admin_roles', [])
    return _check_role_access(member, admin_roles)


def _check_moderator_access(member: discord.Member, config: dict) -> bool:
    """Check if member has moderator access."""
    # Check Discord permissions first if required
    if config.get('require_discord_permissions', True):
        if (member.guild_permissions.administrator or
            member.guild_permissions.manage_guild or
            member.guild_permissions.manage_channels):
            return True

    # Check moderator roles
    moderator_roles = config.get('moderator_roles', [])
    return _check_role_access(member, moderator_roles)


def _check_trusted_user_access(member: discord.Member, config: dict) -> bool:
    """Check if member has trusted user access."""
    # Check trusted user roles
    trusted_roles = config.get('trusted_user_roles', [])
    return _check_role_access(member, trusted_roles)


def _check_role_access(member: discord.Member, required_roles: list[str]) -> bool:
    """Check if member has any of the required roles (case-insensitive)."""
    if not required_roles:
        return False

    member_role_names = [role.name.lower() for role in member.roles]
    required_role_names = [role.lower() for role in required_roles]

    return any(role_name in member_role_names for role_name in required_role_names)


def get_permission_error_message(permission_type: str, config: dict | None = None) -> str:
    """Get a user-friendly error message for permission denial.

    Args:
        permission_type: Type of permission that was denied.
        config: Server permission configuration (optional).

    Returns:
        str: User-friendly error message explaining what's required.
    """
    if not config:
        return (
            "You need server administrator permissions or the admin role to use this command."
        )

    permission_level = config.get(permission_type, 'admin_only')

    if permission_level == 'server_owner':
        return "Only the server owner can use this command."
    if permission_level == 'admin_only':
        admin_roles = config.get('admin_roles', [])
        if admin_roles:
            roles_text = ", ".join(f"'{role}'" for role in admin_roles)
            return f"You need either Discord administrator permissions or one of these roles: {roles_text}"
        return "You need Discord administrator permissions to use this command."
    if permission_level == 'moderators':
        moderator_roles = config.get('moderator_roles', [])
        admin_roles = config.get('admin_roles', [])
        all_roles = admin_roles + moderator_roles
        if all_roles:
            roles_text = ", ".join(f"'{role}'" for role in all_roles)
            return f"You need either Discord moderator/administrator permissions or one of these roles: {roles_text}"
        return "You need Discord moderator or administrator permissions to use this command."
    if permission_level == 'trusted_users':
        return "You need to have a trusted user role or higher to use this command."
    if permission_level == 'custom_roles':
        return "You need to have one of the configured custom roles to use this command."
    return "You don't have permission to use this command."
