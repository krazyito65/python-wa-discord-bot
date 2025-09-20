"""
Views for the server admin panel.

This module provides views for managing server-specific permissions and settings,
including macro permissions, role configurations, and admin panel access control.
"""

import json
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils.html import format_html
from django.views.decorators.http import require_POST
from shared.discord_api import DiscordAPIError, get_guild_roles, get_user_guilds

from .models import (
    DISCORD_ADMINISTRATOR_PERMISSION,
    DISCORD_MANAGE_SERVER_PERMISSION,
    AssignableRole,
    EventConfig,
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
                    format_html(
                        "Could not fetch Discord roles. The bot may not be in this server or may lack permissions. "
                        '<a href="https://discord.com/oauth2/authorize?client_id=270716626469519372&permissions=2550262784&redirect_uri=https%3A%2F%2Fbot.weakauras.wtf%2Faccounts%2Fdiscord%2Flogin%2Fcallback%2F&integration_type=0&scope=bot+applications.commands" target="_blank" rel="noopener">'
                        "Click here to invite the bot with proper permissions</a>."
                    ),
                )
        except DiscordAPIError as e:
            logger.warning(f"Failed to fetch Discord roles for guild {guild_id}: {e}")
            messages.warning(
                request,
                format_html(
                    "Could not fetch Discord roles. Some features may not work correctly. "
                    '<a href="https://discord.com/oauth2/authorize?client_id=270716626469519372&permissions=2550262784&redirect_uri=https%3A%2F%2Fbot.weakauras.wtf%2Faccounts%2Fdiscord%2Flogin%2Fcallback%2F&integration_type=0&scope=bot+applications.commands" target="_blank" rel="noopener">'
                    "Click here to invite the bot with proper permissions</a>."
                ),
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


@login_required
def manage_assignable_roles(request, guild_id):
    """Manage assignable roles for a server."""
    try:
        guild_name, server_config, user_guilds = _validate_admin_panel_access(
            request, int(guild_id)
        )

        if request.method == "POST":
            return _handle_assignable_role_update(request, server_config, guild_id)

        # Fetch Discord roles for dropdown
        discord_roles = []
        try:
            discord_roles = get_guild_roles(int(guild_id))
            if discord_roles is None:
                discord_roles = []
                messages.warning(
                    request,
                    format_html(
                        "Could not fetch Discord roles. The bot may not be in this server or may lack permissions. "
                        '<a href="https://discord.com/oauth2/authorize?client_id=270716626469519372&permissions=2550262784&redirect_uri=https%3A%2F%2Fbot.weakauras.wtf%2Faccounts%2Fdiscord%2Flogin%2Fcallback%2F&integration_type=0&scope=bot+applications.commands" target="_blank" rel="noopener">'
                        "Click here to invite the bot with proper permissions</a>."
                    ),
                )
        except DiscordAPIError as e:
            logger.warning(f"Failed to fetch Discord roles for guild {guild_id}: {e}")
            messages.warning(
                request,
                format_html(
                    "Could not fetch Discord roles. Some features may not work correctly. "
                    '<a href="https://discord.com/oauth2/authorize?client_id=270716626469519372&permissions=2550262784&redirect_uri=https%3A%2F%2Fbot.weakauras.wtf%2Faccounts%2Fdiscord%2Flogin%2Fcallback%2F&integration_type=0&scope=bot+applications.commands" target="_blank" rel="noopener">'
                    "Click here to invite the bot with proper permissions</a>."
                ),
            )

        # Get current assignable roles
        assignable_roles = AssignableRole.objects.filter(server_config=server_config)

        # Filter out roles that are already assignable
        assignable_role_ids = {role.role_id for role in assignable_roles}
        available_roles = [
            role
            for role in discord_roles
            if role["id"] not in assignable_role_ids and role["name"] != "@everyone"
        ]

        context = {
            "guild_id": guild_id,
            "guild_name": guild_name,
            "server_config": server_config,
            "assignable_roles": assignable_roles,
            "available_roles": available_roles,
            "discord_roles": discord_roles,
            "permission_choices": ServerPermissionConfig.PERMISSION_CHOICES,
        }

        return render(request, "admin_panel/manage_assignable_roles.html", context)

    except Http404:
        messages.error(
            request,
            "You don't have permission to access the admin panel for this server",
        )
        return redirect("servers:dashboard")


def _process_role_assignments(
    role_ids,
    discord_roles,
    server_config,
    user_id,
    user_name,
    is_self_assignable,
    requires_permission,
):
    """Process role assignments and return results."""
    added_roles = []
    updated_roles = []
    failed_roles = []

    for role_id in role_ids:
        # Ensure role_id is a string for comparison with Discord API
        role_id = str(role_id)

        # Find role info in Discord data
        role_info = next(
            (role for role in discord_roles if str(role["id"]) == role_id), None
        )

        if not role_info:
            failed_roles.append(f"Role ID {role_id}")
            continue

        # Convert color from decimal to hex
        role_color = ""
        if role_info.get("color"):
            role_color = f"#{role_info['color']:06x}"

        # Create or update assignable role
        try:
            assignable_role, created = AssignableRole.objects.get_or_create(
                server_config=server_config,
                role_id=role_id,
                defaults={
                    "role_name": role_info["name"],
                    "role_color": role_color,
                    "is_self_assignable": is_self_assignable,
                    "requires_permission": requires_permission,
                    "added_by": user_id,
                    "added_by_name": user_name,
                },
            )

            if created:
                added_roles.append(role_info["name"])
                logger.info(f"Created assignable role: {role_info['name']} (ID: {role_id}) for guild {server_config.guild_id}")
            else:
                # Update existing role
                assignable_role.role_name = role_info["name"]
                assignable_role.role_color = role_color
                assignable_role.is_self_assignable = is_self_assignable
                assignable_role.requires_permission = requires_permission
                assignable_role.save()
                updated_roles.append(role_info["name"])
                logger.info(f"Updated assignable role: {role_info['name']} (ID: {role_id}) for guild {server_config.guild_id}")
        except Exception as e:
            logger.exception(f"Failed to create/update assignable role {role_info['name']} (ID: {role_id}): {e}")
            failed_roles.append(f"Role {role_info['name']} - Database error: {str(e)}")

    return added_roles, updated_roles, failed_roles


def _display_role_assignment_messages(
    request, added_roles, updated_roles, failed_roles
):
    """Display appropriate messages for role assignment results."""
    if added_roles:
        if len(added_roles) == 1:
            messages.success(
                request, f"Role '{added_roles[0]}' added to assignable roles."
            )
        else:
            role_list = "', '".join(added_roles)
            messages.success(
                request,
                f"Added {len(added_roles)} roles to assignable list: '{role_list}'",
            )

    if updated_roles:
        if len(updated_roles) == 1:
            messages.info(request, f"Role '{updated_roles[0]}' settings updated.")
        else:
            role_list = "', '".join(updated_roles)
            messages.info(
                request,
                f"Updated {len(updated_roles)} role settings: '{role_list}'",
            )

    if failed_roles:
        if len(failed_roles) == 1:
            messages.error(request, f"Could not find role: {failed_roles[0]}")
        else:
            role_list = ", ".join(failed_roles)
            messages.error(
                request, f"Could not find {len(failed_roles)} roles: {role_list}"
            )


@require_POST
@login_required
def add_assignable_role(request, guild_id):  # noqa: PLR0912
    """Add one or more roles to the assignable roles list."""
    logger.info(f"add_assignable_role called: guild_id={guild_id}, method={request.method}")
    try:
        guild_name, server_config, user_guilds = _validate_admin_panel_access(
            request, int(guild_id)
        )
        logger.info(f"Access validation passed for guild {guild_id}")

        # Handle both single role_id (legacy) and multiple role_ids
        role_ids = request.POST.getlist("role_ids")
        logger.info(f"Initial role_ids from POST: {role_ids}")
        if not role_ids:
            # Fallback to single role_id for backward compatibility
            single_role_id = request.POST.get("role_id")
            if single_role_id:
                role_ids = [single_role_id]
            logger.info(f"After fallback, role_ids: {role_ids}")

        is_self_assignable = request.POST.get("is_self_assignable") == "on"
        requires_permission = request.POST.get("requires_permission", "everyone")
        logger.info(f"Form data: role_ids={role_ids}, is_self_assignable={is_self_assignable}, requires_permission={requires_permission}")

        if not role_ids:
            logger.warning("No role IDs provided in form submission")
            messages.error(request, "Please select at least one role to add.")
            return redirect("admin_panel:manage_assignable_roles", guild_id=guild_id)

        # Fetch role information from Discord
        try:
            discord_roles = get_guild_roles(int(guild_id))
            logger.info(f"Fetched {len(discord_roles) if discord_roles else 0} roles from Discord")
        except DiscordAPIError as e:
            logger.error(f"DiscordAPIError fetching roles: {e}")
            messages.error(request, "Could not fetch role information from Discord.")
            return redirect("admin_panel:manage_assignable_roles", guild_id=guild_id)

        # Get user info for logging
        user_id = (
            str(request.user.socialaccount_set.first().uid)
            if request.user.socialaccount_set.first()
            else str(request.user.id)
        )
        user_name = request.user.username

        # Process role assignments
        logger.info(f"Processing role assignments for {len(role_ids)} roles")
        with transaction.atomic():
            added_roles, updated_roles, failed_roles = _process_role_assignments(
                role_ids,
                discord_roles,
                server_config,
                user_id,
                user_name,
                is_self_assignable,
                requires_permission,
            )
        logger.info(f"Role processing complete: added={len(added_roles)}, updated={len(updated_roles)}, failed={len(failed_roles)}")

        # Display appropriate messages
        _display_role_assignment_messages(
            request, added_roles, updated_roles, failed_roles
        )

    except Http404:
        logger.error(f"Http404 in add_assignable_role for guild {guild_id}")
        messages.error(
            request,
            "You don't have permission to access the admin panel for this server",
        )
    except Exception as e:
        logger.exception(f"Unexpected error in add_assignable_role for guild {guild_id}: {e}")
        messages.error(request, "An unexpected error occurred while adding roles.")

    logger.info(f"Redirecting to manage_assignable_roles for guild {guild_id}")
    return redirect("admin_panel:manage_assignable_roles", guild_id=guild_id)


@require_POST
@login_required
def remove_assignable_role(request, guild_id, role_id):
    """Remove a role from the assignable roles list."""
    try:
        guild_name, server_config, user_guilds = _validate_admin_panel_access(
            request, int(guild_id)
        )

        assignable_role = AssignableRole.objects.get(
            server_config=server_config, role_id=role_id
        )

        role_name = assignable_role.role_name
        assignable_role.delete()

        messages.success(request, f"Role '{role_name}' removed from assignable roles.")

    except AssignableRole.DoesNotExist:
        messages.error(request, "Assignable role not found.")
    except Http404:
        messages.error(
            request,
            "You don't have permission to access the admin panel for this server",
        )

    return redirect("admin_panel:manage_assignable_roles", guild_id=guild_id)


def _handle_assignable_role_update(request, server_config, guild_id):
    """Handle updates to assignable role settings."""
    try:
        # Handle bulk updates to existing assignable roles
        for role_id in request.POST.getlist("role_ids"):
            try:
                assignable_role = AssignableRole.objects.get(
                    server_config=server_config, role_id=role_id
                )

                # Update settings
                is_self_assignable_key = f"is_self_assignable_{role_id}"
                requires_permission_key = f"requires_permission_{role_id}"

                assignable_role.is_self_assignable = (
                    request.POST.get(is_self_assignable_key) == "on"
                )
                assignable_role.requires_permission = request.POST.get(
                    requires_permission_key, "everyone"
                )
                assignable_role.save()

            except AssignableRole.DoesNotExist:
                continue

        messages.success(request, "Assignable role settings updated successfully.")

    except Exception:
        logger.exception("Error updating assignable roles")
        messages.error(request, "An error occurred while updating role settings.")

    return redirect("admin_panel:manage_assignable_roles", guild_id=guild_id)


@login_required
def manage_events(request, guild_id):
    """Manage bot events configuration for a server."""
    try:
        guild_name, server_config, user_guilds = _validate_admin_panel_access(
            request, int(guild_id)
        )

        # Get all available event types
        available_events = EventConfig.EVENT_TYPE_CHOICES

        # Get current event configurations
        current_events = {}
        for event_config in EventConfig.objects.filter(server_config=server_config):
            current_events[event_config.event_type] = event_config

        # Create list of events with their status
        events_status = []
        for event_type, event_display_name in available_events:
            event_config = current_events.get(event_type)
            if event_config:
                enabled = event_config.enabled
                config_obj = event_config
            else:
                # Default to enabled for new events
                enabled = True
                config_obj = None

            # Get description for this event type
            temp_config = EventConfig(event_type=event_type)
            description = temp_config.get_event_description()

            events_status.append(
                {
                    "type": event_type,
                    "display_name": event_display_name,
                    "enabled": enabled,
                    "config": config_obj,
                    "description": description,
                }
            )

        context = {
            "guild_id": guild_id,
            "guild_name": guild_name,
            "server_config": server_config,
            "events_status": events_status,
        }

        return render(request, "admin_panel/manage_events.html", context)

    except Http404:
        messages.error(
            request,
            "You don't have permission to access the admin panel for this server",
        )
        return redirect("servers:dashboard")


@require_POST
@login_required
def toggle_event(request, guild_id, event_type):
    """Toggle an event on/off for a server."""
    try:
        guild_name, server_config, user_guilds = _validate_admin_panel_access(
            request, int(guild_id)
        )

        # Validate event type
        valid_event_types = [choice[0] for choice in EventConfig.EVENT_TYPE_CHOICES]
        if event_type not in valid_event_types:
            messages.error(request, f"Invalid event type: {event_type}")
            return redirect("admin_panel:manage_events", guild_id=guild_id)

        # Get user info for logging
        user_id = (
            str(request.user.socialaccount_set.first().uid)
            if request.user.socialaccount_set.first()
            else str(request.user.id)
        )
        user_name = request.user.username

        # Get or create event configuration
        event_config, created = EventConfig.objects.get_or_create(
            server_config=server_config,
            event_type=event_type,
            defaults={
                "enabled": True,
                "updated_by": user_id,
                "updated_by_name": user_name,
            },
        )

        if not created:
            # Toggle the existing configuration
            event_config.enabled = not event_config.enabled
            event_config.updated_by = user_id
            event_config.updated_by_name = user_name
            event_config.save()

        event_display_name = dict(EventConfig.EVENT_TYPE_CHOICES)[event_type]
        status = "enabled" if event_config.enabled else "disabled"

        messages.success(
            request,
            f"{event_display_name} event has been {status} for this server.",
        )

    except Http404:
        messages.error(
            request,
            "You don't have permission to access the admin panel for this server",
        )

    return redirect("admin_panel:manage_events", guild_id=guild_id)
