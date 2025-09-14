"""
Views for the server admin panel.

This module provides views for managing server-specific permissions and settings,
including macro permissions, role configurations, and admin panel access control.
"""

import json
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST
from shared.discord_api import DiscordAPIError, get_guild_roles, get_user_guilds

from .models import (
    DISCORD_ADMINISTRATOR_PERMISSION,
    DISCORD_MANAGE_SERVER_PERMISSION,
    ServerPermissionConfig,
    ServerPermissionLog,
)

logger = logging.getLogger(__name__)


def _validate_admin_panel_access(request, guild_id: int):
    """
    Validate that user has access to the admin panel for the specified server.

    Args:
        request: Django HTTP request with authenticated user
        guild_id: Discord guild ID to check admin panel access for

    Returns:
        tuple: (guild_name, server_config, user_guilds) if access granted

    Raises:
        Http404: If user doesn't have access to this server or admin panel
    """
    try:
        # Get user's guilds and check server access
        user_guilds = get_user_guilds(request.user)
        user_guild_ids = [int(guild["id"]) for guild in user_guilds]

        if guild_id not in user_guild_ids:
            raise Http404("You don't have access to this server")

        # Get guild info
        guild_info = next(
            (guild for guild in user_guilds if int(guild["id"]) == guild_id),
            None,
        )

        if not guild_info:
            raise Http404("Server not found")

        guild_name = guild_info["name"]
        is_server_owner = guild_info.get("owner", False)
        guild_permissions = int(guild_info.get("permissions", 0))

        # Get or create server permission configuration
        server_config, created = ServerPermissionConfig.objects.get_or_create(
            guild_id=str(guild_id),
            defaults={
                "guild_name": guild_name,
                "updated_by": str(request.user.socialaccount_set.first().uid)
                if request.user.socialaccount_set.first()
                else str(request.user.id),
                "updated_by_name": request.user.username,
            },
        )

        # Update guild name if it changed
        if server_config.guild_name != guild_name:
            server_config.guild_name = guild_name
            server_config.save()

        # Check admin panel access permission
        # For newly created configs, default to admin_only, so check basic admin permissions
        if created:
            # For new configs, use basic admin permission check (Discord administrator permission)
            if not (
                is_server_owner
                or (guild_permissions & DISCORD_ADMINISTRATOR_PERMISSION)
                == DISCORD_ADMINISTRATOR_PERMISSION
                or (guild_permissions & DISCORD_MANAGE_SERVER_PERMISSION)
                == DISCORD_MANAGE_SERVER_PERMISSION
            ):
                raise Http404(
                    "You don't have permission to access the admin panel for this server"
                )
        else:
            # Use the configured permission system
            user_roles = []  # We'll need to implement role fetching from Discord API
            if not server_config.has_permission(
                user_roles, "admin_panel_access", guild_permissions, is_server_owner
            ):
                raise Http404(
                    "You don't have permission to access the admin panel for this server"
                )

        return guild_name, server_config, user_guilds

    except DiscordAPIError as e:
        logger.exception("Discord API error in admin panel access validation")
        raise Http404(f"Error accessing server information: {e}") from e


@login_required
def admin_panel_dashboard(request, guild_id):
    """
    Main admin panel dashboard for a specific server.

    Shows overview of current permissions and quick access to settings.
    """
    try:
        guild_name, server_config, user_guilds = _validate_admin_panel_access(
            request, guild_id
        )

        # Get recent permission changes for audit log
        recent_logs = server_config.permission_logs.all()[:10]

        # Get human-readable permission displays
        permission_displays = {
            "admin_panel_access": server_config.get_permission_level_display(
                "admin_panel_access"
            ),
            "create_macros": server_config.get_permission_level_display(
                "create_macros"
            ),
            "edit_macros": server_config.get_permission_level_display("edit_macros"),
            "delete_macros": server_config.get_permission_level_display(
                "delete_macros"
            ),
            "use_macros": server_config.get_permission_level_display("use_macros"),
        }

        context = {
            "guild_id": guild_id,
            "guild_name": guild_name,
            "server_config": server_config,
            "permission_displays": permission_displays,
            "recent_logs": recent_logs,
            "user_guilds": user_guilds,
        }

        return render(request, "admin_panel/dashboard.html", context)

    except Http404:
        messages.error(
            request,
            "You don't have permission to access the admin panel for this server",
        )
        return redirect("servers:dashboard")


@login_required
def permission_settings(request, guild_id):
    """
    View and edit permission settings for macro operations.
    """
    try:
        guild_name, server_config, user_guilds = _validate_admin_panel_access(
            request, guild_id
        )

        if request.method == "POST":
            return _handle_permission_update(request, server_config, guild_id)

        context = {
            "guild_id": guild_id,
            "guild_name": guild_name,
            "server_config": server_config,
            "permission_choices": ServerPermissionConfig.PERMISSION_CHOICES,
            "user_guilds": user_guilds,
        }

        return render(request, "admin_panel/permission_settings.html", context)

    except Http404:
        messages.error(
            request,
            "You don't have permission to access the admin panel for this server",
        )
        return redirect("servers:dashboard")


@login_required
def role_settings(request, guild_id):
    """
    View and edit role-based permission settings.
    """
    try:
        guild_name, server_config, user_guilds = _validate_admin_panel_access(
            request, guild_id
        )

        if request.method == "POST":
            return _handle_role_update(request, server_config, guild_id)

        # Fetch Discord roles for dropdown
        discord_roles = []
        try:
            discord_roles = get_guild_roles(int(guild_id))
            if discord_roles is None:
                discord_roles = []
                messages.warning(
                    request,
                    "Could not fetch Discord roles. The bot may not be in this server or may lack permissions.",
                )
        except DiscordAPIError as e:
            logger.warning(f"Failed to fetch Discord roles for guild {guild_id}: {e}")
            messages.warning(
                request,
                "Could not fetch Discord roles. Some features may not work correctly.",
            )

        # Create role name to ID mapping for template selection
        role_name_to_id = {}
        if discord_roles:
            role_name_to_id = {role["name"]: role["id"] for role in discord_roles}

        context = {
            "guild_id": guild_id,
            "guild_name": guild_name,
            "server_config": server_config,
            "user_guilds": user_guilds,
            "discord_roles": discord_roles,
            "role_name_to_id": role_name_to_id,
        }

        return render(request, "admin_panel/role_settings.html", context)

    except Http404:
        messages.error(
            request,
            "You don't have permission to access the admin panel for this server",
        )
        return redirect("servers:dashboard")


def _handle_permission_update(request, server_config, guild_id):
    """Handle permission level updates from the form."""
    user_id = (
        str(request.user.socialaccount_set.first().uid)
        if request.user.socialaccount_set.first()
        else str(request.user.id)
    )
    user_name = request.user.username
    changes_made = False

    # Permission fields to check
    permission_fields = [
        "admin_panel_access",
        "create_macros",
        "edit_macros",
        "delete_macros",
        "use_macros",
    ]

    for field in permission_fields:
        new_value = request.POST.get(field)
        if new_value and hasattr(server_config, field):
            old_value = getattr(server_config, field)
            if old_value != new_value:
                # Log the change
                ServerPermissionLog.objects.create(
                    server_config=server_config,
                    action="permission_changed",
                    field_changed=field,
                    old_value=old_value,
                    new_value=new_value,
                    changed_by=user_id,
                    changed_by_name=user_name,
                    user_agent=request.META.get("HTTP_USER_AGENT", ""),
                    ip_address=request.META.get("REMOTE_ADDR"),
                )

                setattr(server_config, field, new_value)
                changes_made = True

    # Handle boolean settings
    server_config.require_discord_permissions = (
        request.POST.get("require_discord_permissions") == "on"
    )

    if changes_made or "require_discord_permissions" in request.POST:
        server_config.updated_by = user_id
        server_config.updated_by_name = user_name
        server_config.save()
        messages.success(request, "Permission settings updated successfully!")
    else:
        messages.info(request, "No changes were made to permission settings.")

    return redirect("admin_panel:permission_settings", guild_id=guild_id)


def _handle_role_update(request, server_config, guild_id):
    """Handle role list updates from the form."""
    user_id = (
        str(request.user.socialaccount_set.first().uid)
        if request.user.socialaccount_set.first()
        else str(request.user.id)
    )
    user_name = request.user.username
    changes_made = False

    # Role list fields to check
    role_fields = [
        "admin_roles",
        "moderator_roles",
        "trusted_user_roles",
        "custom_admin_panel_roles",
        "custom_create_roles",
        "custom_edit_roles",
        "custom_delete_roles",
        "custom_use_roles",
    ]

    # Get Discord roles for ID to name mapping
    try:
        discord_roles = get_guild_roles(int(guild_id))
        role_id_to_name = {}
        if discord_roles:
            role_id_to_name = {role["id"]: role["name"] for role in discord_roles}
    except (DiscordAPIError, ValueError):
        logger.warning(
            f"Failed to fetch Discord roles for guild {guild_id} during role update"
        )
        role_id_to_name = {}

    for field in role_fields:
        # Get selected role IDs from form
        new_role_ids = request.POST.getlist(field)

        # Convert role IDs to role names
        new_role_names = []
        for role_id in new_role_ids:
            if role_id in role_id_to_name:
                new_role_names.append(role_id_to_name[role_id])
            else:
                # If we can't find the role name, log a warning but continue
                logger.warning(
                    f"Role ID {role_id} not found in Discord roles for guild {guild_id}"
                )

        if hasattr(server_config, field):
            old_value = getattr(server_config, field)
            if old_value != new_role_names:
                # Log the change
                ServerPermissionLog.objects.create(
                    server_config=server_config,
                    action="roles_updated",
                    field_changed=field,
                    old_value=json.dumps(old_value),
                    new_value=json.dumps(new_role_names),
                    changed_by=user_id,
                    changed_by_name=user_name,
                    user_agent=request.META.get("HTTP_USER_AGENT", ""),
                    ip_address=request.META.get("REMOTE_ADDR"),
                )

                setattr(server_config, field, new_role_names)
                changes_made = True

    if changes_made:
        server_config.updated_by = user_id
        server_config.updated_by_name = user_name
        server_config.save()
        messages.success(request, "Role settings updated successfully!")
    else:
        messages.info(request, "No changes were made to role settings.")

    return redirect("admin_panel:role_settings", guild_id=guild_id)


@login_required
def audit_log(request, guild_id):
    """
    View audit log of permission changes for the server.
    """
    try:
        guild_name, server_config, user_guilds = _validate_admin_panel_access(
            request, guild_id
        )

        # Get all logs for this server, paginated
        logs = server_config.permission_logs.all()

        # Simple pagination - get last 50 entries
        logs = logs[:50]

        context = {
            "guild_id": guild_id,
            "guild_name": guild_name,
            "server_config": server_config,
            "logs": logs,
            "user_guilds": user_guilds,
        }

        return render(request, "admin_panel/audit_log.html", context)

    except Http404:
        messages.error(
            request,
            "You don't have permission to access the admin panel for this server",
        )
        return redirect("servers:dashboard")


@login_required
@require_POST
def reset_to_defaults(request, guild_id):
    """
    Reset server permissions to default settings.
    """
    try:
        guild_name, server_config, user_guilds = _validate_admin_panel_access(
            request, guild_id
        )

        user_id = (
            str(request.user.socialaccount_set.first().uid)
            if request.user.socialaccount_set.first()
            else str(request.user.id)
        )
        user_name = request.user.username

        # Log the reset action
        ServerPermissionLog.objects.create(
            server_config=server_config,
            action="updated",
            field_changed="all_permissions",
            old_value="Custom configuration",
            new_value="Default configuration",
            changed_by=user_id,
            changed_by_name=user_name,
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        # Reset to defaults
        server_config.admin_panel_access = "admin_only"
        server_config.create_macros = "admin_only"
        server_config.edit_macros = "admin_only"
        server_config.delete_macros = "admin_only"
        server_config.use_macros = "everyone"

        # Reset role lists
        server_config.admin_roles = ["administrator", "admin"]
        server_config.moderator_roles = ["moderator", "mod"]
        server_config.trusted_user_roles = []
        server_config.custom_admin_panel_roles = []
        server_config.custom_create_roles = []
        server_config.custom_edit_roles = []
        server_config.custom_delete_roles = []
        server_config.custom_use_roles = []

        # Reset boolean settings
        server_config.require_discord_permissions = True

        server_config.updated_by = user_id
        server_config.updated_by_name = user_name
        server_config.save()

        messages.success(
            request, "Server permissions have been reset to default settings!"
        )

    except Http404:
        messages.error(
            request,
            "You don't have permission to access the admin panel for this server",
        )

    return redirect("admin_panel:dashboard", guild_id=guild_id)
