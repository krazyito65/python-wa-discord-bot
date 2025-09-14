"""
Server views for WeakAuras Web Interface

This module contains views for server selection and dashboard functionality,
allowing users to choose which Discord server to manage macros for.
"""

import logging

from admin_panel.models import (
    DISCORD_ADMINISTRATOR_PERMISSION,
    DISCORD_MANAGE_CHANNELS_PERMISSION,
    DISCORD_MANAGE_SERVER_PERMISSION,
    ServerPermissionConfig,
)
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from shared.bot_interface import bot_interface
from shared.discord_api import (
    DiscordAPIError,
    filter_available_servers,
    get_user_guilds,
    get_user_roles_in_guild,
)
from user_stats.models import DiscordGuild, MessageStatistics

logger = logging.getLogger(__name__)


@login_required
def dashboard(request):
    """Dashboard view showing server selection for authenticated users.

    This view displays all Discord servers where:
    1. The user is a member
    2. The WeakAuras bot has data stored

    Args:
        request: Django HTTP request object with authenticated user.

    Returns:
        HttpResponse: Rendered dashboard template with available servers.
    """
    try:
        # Get user's Discord guilds
        user_guilds = get_user_guilds(request.user)

        # Get servers that have bot data
        bot_servers = bot_interface.get_available_servers()

        # Filter to servers where user is member AND bot has data
        available_servers = filter_available_servers(user_guilds, bot_servers)

        context = {
            "available_servers": available_servers,
            "total_servers": len(available_servers),
        }

        # If user only has access to one server, redirect directly to it
        if len(available_servers) == 1:
            return redirect(
                "servers:server_hub", guild_id=available_servers[0]["guild_id"]
            )

        return render(request, "servers/dashboard.html", context)

    except DiscordAPIError as e:
        messages.error(request, f"Error fetching Discord servers: {e}")
        return render(request, "servers/dashboard.html", {"available_servers": []})


@login_required
def server_select(request):
    """Server selection view (same as dashboard but different template).

    Args:
        request: Django HTTP request object with authenticated user.

    Returns:
        HttpResponse: Rendered server selection template.
    """
    return dashboard(request)  # Use same logic as dashboard


@login_required
def server_hub(request, guild_id):
    """Server management hub - choose between stats or macros.

    Args:
        request: Django HTTP request object with authenticated user.
        guild_id (int): Discord guild/server ID.

    Returns:
        HttpResponse: Rendered server hub template with management options.
    """
    try:
        logger.debug(f"Server hub view called for guild_id: {guild_id}")

        # Get user's Discord guilds to verify access
        user_guilds = get_user_guilds(request.user)
        user_guild_ids = [int(guild["id"]) for guild in user_guilds]

        # Check if user has access to this server
        if guild_id not in user_guild_ids:
            raise Http404("You don't have access to this server")

        # Get bot servers and check if this server has data
        bot_servers = bot_interface.get_available_servers()
        bot_guild_ids = [server["guild_id"] for server in bot_servers]

        # Find the specific server info
        guild_name = None
        guild_icon = None

        for guild in user_guilds:
            if int(guild["id"]) == guild_id:
                guild_name = guild["name"]
                guild_icon = guild.get("icon")
                break

        if not guild_name:
            raise Http404("Server information not found")

        # Check what features are available
        has_bot_data = guild_id in bot_guild_ids
        has_stats_data = False

        if has_bot_data:
            # Check if server has statistics data
            try:
                try:
                    stats_guild = DiscordGuild.objects.get(guild_id=str(guild_id))
                    stats_count = MessageStatistics.objects.filter(
                        channel__guild=stats_guild
                    ).count()
                    has_stats_data = stats_count > 0
                except DiscordGuild.DoesNotExist:
                    has_stats_data = False
            except ImportError:
                has_stats_data = False

        context = {
            "guild_id": guild_id,
            "guild_name": guild_name,
            "guild_icon": guild_icon,
            "has_bot_data": has_bot_data,
            "has_stats_data": has_stats_data,
        }

        return render(request, "servers/server_hub.html", context)

    except DiscordAPIError as e:
        logger.exception("DiscordAPIError in server_hub")
        messages.error(request, f"Error accessing server information: {e}")
        return redirect("servers:dashboard")


def _check_admin_panel_access(request, guild_id: int, user_guilds: list) -> bool:
    """
    Check if user has access to the admin panel for the specified server.

    Args:
        request: Django HTTP request with authenticated user
        guild_id: Discord guild ID to check admin panel access for
        user_guilds: List of user's Discord guilds from API

    Returns:
        bool: True if user has admin panel access, False otherwise
    """
    try:
        # Get guild info
        guild_info = next(
            (guild for guild in user_guilds if int(guild["id"]) == guild_id),
            None,
        )

        if not guild_info:
            return False

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
                else "",
                "updated_by_name": request.user.username,
            },
        )

        # For newly created configs, default to basic admin permission check
        if created:
            # For new configs, use basic admin permission check (Discord administrator/owner)
            return (
                is_server_owner
                or (guild_permissions & DISCORD_ADMINISTRATOR_PERMISSION)
                == DISCORD_ADMINISTRATOR_PERMISSION
                or (guild_permissions & DISCORD_MANAGE_SERVER_PERMISSION)
                == DISCORD_MANAGE_SERVER_PERMISSION
            )
        # Use the configured permission system
        user_roles = []  # We'll need to implement role fetching from Discord API in the future
        return server_config.has_permission(
            user_roles, "admin_panel_access", guild_permissions, is_server_owner
        )

    except Exception:
        logger.exception("Error checking admin panel access")
        return False


def _check_macro_permission(
    request, guild_id: int, user_guilds: list, permission_type: str
) -> bool:
    """
    Check if user has the specified macro permission for the given server.

    Args:
        request: Django HTTP request with authenticated user
        guild_id: Discord guild ID to check permissions for
        user_guilds: List of user's Discord guilds from API
        permission_type: Type of permission to check ('create_macros', 'edit_macros', 'delete_macros')

    Returns:
        bool: True if user has the specified permission, False otherwise
    """
    try:
        # Get guild info
        guild_info = next(
            (guild for guild in user_guilds if int(guild["id"]) == guild_id),
            None,
        )

        if not guild_info:
            return False

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
                else "",
                "updated_by_name": request.user.username,
            },
        )

        # For newly created configs, default to admin_only for create/edit/delete operations
        if created:
            # For new configs, use basic admin permission check (Discord administrator/owner/manage server)
            return (
                is_server_owner
                or (guild_permissions & DISCORD_ADMINISTRATOR_PERMISSION)
                == DISCORD_ADMINISTRATOR_PERMISSION
                or (guild_permissions & DISCORD_MANAGE_SERVER_PERMISSION)
                == DISCORD_MANAGE_SERVER_PERMISSION
            )
        # Use the configured permission system with actual roles
        try:
            user_roles_data = get_user_roles_in_guild(request.user, guild_id) or []
            user_role_names = [role["name"].lower() for role in user_roles_data]
        except DiscordAPIError:
            user_role_names = []  # Fall back to empty roles if API fails

        return server_config.has_permission(
            user_role_names, permission_type, guild_permissions, is_server_owner
        )

    except Exception:
        logger.exception(f"Error checking {permission_type} permission")
        return False


def _get_user_permission_status(request, guild_id: int, user_guilds: list) -> dict:
    """
    Get detailed information about user's permission status for display.

    Args:
        request: Django HTTP request with authenticated user
        guild_id: Discord guild ID to check permissions for
        user_guilds: List of user's Discord guilds from API

    Returns:
        dict: Detailed permission status information for template display
    """
    try:
        # Get guild info
        guild_info = next(
            (guild for guild in user_guilds if int(guild["id"]) == guild_id),
            None,
        )

        if not guild_info:
            return {"error": "Server not found"}

        guild_name = guild_info["name"]
        is_server_owner = guild_info.get("owner", False)
        guild_permissions = int(guild_info.get("permissions", 0))

        # Check Discord permission bits
        has_administrator = (
            guild_permissions & DISCORD_ADMINISTRATOR_PERMISSION
        ) == DISCORD_ADMINISTRATOR_PERMISSION
        has_manage_server = (
            guild_permissions & DISCORD_MANAGE_SERVER_PERMISSION
        ) == DISCORD_MANAGE_SERVER_PERMISSION
        has_manage_channels = (
            guild_permissions & DISCORD_MANAGE_CHANNELS_PERMISSION
        ) == DISCORD_MANAGE_CHANNELS_PERMISSION

        # Get server permission configuration
        server_config, created = ServerPermissionConfig.objects.get_or_create(
            guild_id=str(guild_id),
            defaults={
                "guild_name": guild_name,
                "updated_by": str(request.user.socialaccount_set.first().uid)
                if request.user.socialaccount_set.first()
                else "",
                "updated_by_name": request.user.username,
            },
        )

        # Build permission status
        discord_permissions = []
        if is_server_owner:
            discord_permissions.append({"name": "Server Owner", "has": True})
        if has_administrator:
            discord_permissions.append({"name": "Discord Administrator", "has": True})
        if has_manage_server:
            discord_permissions.append({"name": "Discord Manage Server", "has": True})
        if has_manage_channels:
            discord_permissions.append({"name": "Discord Manage Channels", "has": True})

        # Get user's actual Discord roles
        user_roles_data = []
        user_role_names = []
        try:
            user_roles_data = get_user_roles_in_guild(request.user, guild_id) or []
            user_role_names = [role["name"].lower() for role in user_roles_data]
        except DiscordAPIError:
            # If we can't fetch roles, fall back to empty list
            pass

        # Check role requirements with actual user roles
        role_requirements = []
        if server_config.admin_roles:
            for role_name in server_config.admin_roles:
                has_role = role_name.lower() in user_role_names
                role_requirements.append(
                    {
                        "name": f'Admin Role: "{role_name}"',
                        "has": has_role,
                        "type": "admin",
                    }
                )
        if server_config.moderator_roles:
            for role_name in server_config.moderator_roles:
                has_role = role_name.lower() in user_role_names
                role_requirements.append(
                    {
                        "name": f'Moderator Role: "{role_name}"',
                        "has": has_role,
                        "type": "moderator",
                    }
                )
        if server_config.trusted_user_roles:
            for role_name in server_config.trusted_user_roles:
                has_role = role_name.lower() in user_role_names
                role_requirements.append(
                    {
                        "name": f'Trusted Role: "{role_name}"',
                        "has": has_role,
                        "type": "trusted",
                    }
                )

        # Check specific permissions with actual roles
        permissions_status = {}
        for permission_type in [
            "create_macros",
            "edit_macros",
            "delete_macros",
            "admin_panel_access",
        ]:
            has_perm = server_config.has_permission(
                user_role_names, permission_type, guild_permissions, is_server_owner
            )
            perm_level = getattr(server_config, permission_type, "admin_only")
            permissions_status[permission_type] = {
                "has": has_perm,
                "level": perm_level,
                "display": server_config.get_permission_level_display(permission_type),
            }

        return {
            "discord_permissions": discord_permissions,
            "role_requirements": role_requirements,
            "permissions_status": permissions_status,
            "has_any_discord_permissions": len(discord_permissions) > 0,
            "user_roles": user_roles_data,
            "server_config": server_config,
        }

    except Exception as e:
        logger.exception("Error getting user permission status")
        return {"error": f"Error checking permissions: {e}"}


@login_required
def server_detail(request, guild_id):  # noqa: PLR0912, PLR0915
    """Server detail view showing macro management interface for a specific server.

    Args:
        request: Django HTTP request object with authenticated user.
        guild_id (int): Discord guild/server ID to display details for.

    Returns:
        HttpResponse: Rendered server detail template with macro information.

    Raises:
        Http404: If user doesn't have access to this server or server doesn't exist.
    """
    try:
        logger.debug(f"Server detail view called for guild_id: {guild_id}")

        # Get user's Discord guilds to verify access
        user_guilds = get_user_guilds(request.user)
        user_guild_ids = [int(guild["id"]) for guild in user_guilds]
        logger.debug(f"User guild IDs: {user_guild_ids}")

        # Check if user has access to this server
        if guild_id not in user_guild_ids:
            msg = "You don't have access to this server"
            logger.debug(f"Access denied: {msg}")
            raise Http404(msg)

        # Get bot servers and check if this server has data
        bot_servers = bot_interface.get_available_servers()
        bot_guild_ids = [server["guild_id"] for server in bot_servers]
        logger.debug(f"Bot guild IDs: {bot_guild_ids}")

        if guild_id not in bot_guild_ids:
            msg = "No bot data found for this server"
            logger.debug(f"No bot data: {msg}")
            raise Http404(msg)

        # Find the specific server info
        server_info = None
        guild_name = None

        for guild in user_guilds:
            if int(guild["id"]) == guild_id:
                guild_name = guild["name"]
                break

        for server in bot_servers:
            if server["guild_id"] == guild_id:
                server_info = server
                break

        if not server_info or not guild_name:
            msg = "Server information not found"
            raise Http404(msg)

        # Load macros for this server
        macros_dict = bot_interface.load_server_macros(guild_id, guild_name)

        # Convert dict to sorted list of macro data for template display
        macros = []
        for name, data in macros_dict.items():
            if isinstance(data, dict):
                # Modern macro format with metadata
                macro_info = data.copy()
                macro_info["name"] = name  # Ensure name is included

                # Determine macro type
                macro_type = data.get("type", "text")
                macro_info["type"] = macro_type

                # For embed macros, ensure embed_data is available
                if macro_type == "embed":
                    macro_info["embed_data"] = data.get("embed_data", {})
                    # Create a text representation for search
                    embed_data = macro_info["embed_data"]
                    search_text_parts = []
                    if embed_data.get("title"):
                        search_text_parts.append(embed_data["title"])
                    if embed_data.get("description"):
                        search_text_parts.append(embed_data["description"])
                    if embed_data.get("footer"):
                        search_text_parts.append(embed_data["footer"])
                    for field in embed_data.get("fields", []):
                        if field.get("name"):
                            search_text_parts.append(field["name"])
                        if field.get("value"):
                            search_text_parts.append(field["value"])
                    macro_info["searchable_text"] = " ".join(search_text_parts)
                else:
                    # Text macro - use message for search
                    macro_info["searchable_text"] = data.get("message", "")
            else:
                # Legacy format (just message string)
                macro_info = {
                    "name": name,
                    "message": data,
                    "type": "text",
                    "searchable_text": data,
                    "created_by": "",
                    "created_by_name": "Unknown",
                    "created_at": "",
                }
            macros.append(macro_info)

        # Apply search filter if provided
        search_query = request.GET.get("search", "").strip()
        if search_query:
            search_lower = search_query.lower()
            macros = [
                macro
                for macro in macros
                if (
                    search_lower in macro["name"].lower()
                    or search_lower in macro.get("searchable_text", "").lower()
                )
            ]

        # Sort macros by name for better user experience
        macros.sort(key=lambda macro: macro["name"].lower())

        # Test message to verify message display is working
        if request.GET.get("test_message"):
            messages.info(
                request, "Test message: Message display is working correctly!"
            )

        # Check if user has admin panel access
        has_admin_panel_access = _check_admin_panel_access(
            request, guild_id, user_guilds
        )

        # Check if user has create_macros permission
        has_create_macros_access = _check_macro_permission(
            request, guild_id, user_guilds, "create_macros"
        )

        # Get detailed user permission status for display
        user_permission_status = _get_user_permission_status(
            request, guild_id, user_guilds
        )

        context = {
            "guild_id": guild_id,
            "guild_name": guild_name,
            "server_info": server_info,
            "macros": macros,
            "macro_count": len(macros),
            "search_query": search_query,
            "total_macros": len(macros_dict),  # Total before filtering
            "has_admin_panel_access": has_admin_panel_access,
            "has_create_macros_access": has_create_macros_access,
            "user_permission_status": user_permission_status,
        }

        return render(request, "servers/server_detail.html", context)

    except DiscordAPIError as e:
        logger.exception("DiscordAPIError in server_detail")
        messages.error(request, f"Error accessing server information: {e}")
        return redirect("servers:dashboard")
