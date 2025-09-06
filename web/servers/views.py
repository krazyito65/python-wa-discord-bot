"""
Server views for WeakAuras Web Interface

This module contains views for server selection and dashboard functionality,
allowing users to choose which Discord server to manage macros for.
"""

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
                "servers:server_detail", guild_id=available_servers[0]["guild_id"]
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
        # Get user's Discord guilds to verify access
        user_guilds = get_user_guilds(request.user)
        user_guild_ids = [int(guild["id"]) for guild in user_guilds]

        # Check if user has access to this server
        if guild_id not in user_guild_ids:
            msg = "You don't have access to this server"
            raise Http404(msg)

        # Get bot servers and check if this server has data
        bot_servers = bot_interface.get_available_servers()
        bot_guild_ids = [server["guild_id"] for server in bot_servers]

        if guild_id not in bot_guild_ids:
            msg = "No bot data found for this server"
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
        macros = bot_interface.load_server_macros(guild_id, guild_name)

        context = {
            "guild_id": guild_id,
            "guild_name": guild_name,
            "server_info": server_info,
            "macros": macros,
            "macro_count": len(macros),
        }

        return render(request, "servers/server_detail.html", context)

    except DiscordAPIError as e:
        messages.error(request, f"Error accessing server information: {e}")
        return redirect("servers:dashboard")
