"""
Server views for WeakAuras Web Interface

This module contains views for server selection and dashboard functionality,
allowing users to choose which Discord server to manage macros for.
"""

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from shared.bot_interface import bot_interface
from shared.discord_api import (
    DiscordAPIError,
    filter_available_servers,
    get_user_guilds,
)

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
                from user_stats.models import DiscordGuild, MessageStatistics

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


@login_required
def server_detail(request, guild_id):
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
            else:
                # Legacy format (just message string)
                macro_info = {
                    "name": name,
                    "message": data,
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
                    or search_lower in macro["message"].lower()
                )
            ]

        # Sort macros by name for better user experience
        macros.sort(key=lambda macro: macro["name"].lower())

        # Test message to verify message display is working
        if request.GET.get("test_message"):
            messages.info(
                request, "Test message: Message display is working correctly!"
            )

        context = {
            "guild_id": guild_id,
            "guild_name": guild_name,
            "server_info": server_info,
            "macros": macros,
            "macro_count": len(macros),
            "search_query": search_query,
            "total_macros": len(macros_dict),  # Total before filtering
        }

        return render(request, "servers/server_detail.html", context)

    except DiscordAPIError as e:
        logger.exception("DiscordAPIError in server_detail")
        messages.error(request, f"Error accessing server information: {e}")
        return redirect("servers:dashboard")
