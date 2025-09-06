"""
Macro views for WeakAuras Web Interface

This module contains views for managing macros (create, edit, delete, list)
for specific Discord servers through the web interface.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect
from shared.bot_interface import bot_interface
from shared.discord_api import DiscordAPIError, get_user_guilds


@login_required
def macro_list(_request, guild_id):
    """Display list of macros for a specific server.

    Args:
        request: Django HTTP request object with authenticated user.
        guild_id (int): Discord guild/server ID to show macros for.

    Returns:
        HttpResponse: Rendered macro list template.

    Raises:
        Http404: If user doesn't have access to this server.
    """
    # Basic placeholder - will redirect to server detail page
    return redirect("servers:server_detail", guild_id=guild_id)


@login_required
def macro_add(request, guild_id):
    """Add a new macro to a specific server.

    Args:
        request: Django HTTP request object with authenticated user.
        guild_id (int): Discord guild/server ID to add macro to.

    Returns:
        HttpResponse: Rendered macro add template or redirect after creation.
    """
    # TODO: Implement macro creation form
    messages.info(request, "Macro creation form coming soon!")
    return redirect("servers:server_detail", guild_id=guild_id)


@login_required
def macro_edit(request, guild_id, macro_name):
    """Edit an existing macro for a specific server.

    Args:
        request: Django HTTP request object with authenticated user.
        guild_id (int): Discord guild/server ID containing the macro.
        macro_name (str): Name of the macro to edit.

    Returns:
        HttpResponse: Rendered macro edit template or redirect after update.
    """
    # TODO: Implement macro editing form
    messages.info(request, f"Editing macro '{macro_name}' coming soon!")
    return redirect("servers:server_detail", guild_id=guild_id)


@login_required
def macro_delete(request, guild_id, macro_name):
    """Delete an existing macro from a specific server.

    Args:
        request: Django HTTP request object with authenticated user.
        guild_id (int): Discord guild/server ID containing the macro.
        macro_name (str): Name of the macro to delete.

    Returns:
        HttpResponse: Redirect to server detail page after deletion.
    """
    try:
        # Get user's Discord guilds to verify access
        user_guilds = get_user_guilds(request.user)
        user_guild_ids = [int(guild["id"]) for guild in user_guilds]

        if guild_id not in user_guild_ids:
            msg = "You don't have access to this server"
            raise Http404(msg)

        # Find guild name
        guild_name = None
        for guild in user_guilds:
            if int(guild["id"]) == guild_id:
                guild_name = guild["name"]
                break

        if not guild_name:
            msg = "Server not found"
            raise Http404(msg)

        # Attempt to delete macro
        if bot_interface.delete_macro(guild_id, guild_name, macro_name):
            messages.success(request, f"Successfully deleted macro '{macro_name}'")
        else:
            messages.error(
                request, f"Macro '{macro_name}' not found or could not be deleted"
            )

    except DiscordAPIError as e:
        messages.error(request, f"Error accessing server: {e}")

    return redirect("servers:server_detail", guild_id=guild_id)
