"""
Macro views for WeakAuras Web Interface

This module contains views for managing macros (create, edit, delete, list)
for specific Discord servers through the web interface.
"""

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import redirect
from shared.bot_interface import MacroUpdateData, bot_interface
from shared.discord_api import DiscordAPIError, get_user_guilds

logger = logging.getLogger(__name__)


@login_required
def macro_list(_request, guild_id):
    """Display list of macros for a specific server.

    Args:
        _request: Django HTTP request object with authenticated user (unused).
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


def _validate_server_access(request, guild_id):
    """Validate user access to server and return guild info."""
    user_guilds = get_user_guilds(request.user)
    user_guild_ids = [int(guild["id"]) for guild in user_guilds]

    if guild_id not in user_guild_ids:
        msg = "You don't have access to this server"
        raise Http404(msg)

    guild_name = next(
        (guild["name"] for guild in user_guilds if int(guild["id"]) == guild_id),
        None,
    )

    if not guild_name:
        msg = "Server not found"
        raise Http404(msg)

    return guild_name


def _validate_macro_edit_inputs(request, macro_name, guild_id, guild_name):
    """Validate macro edit inputs and check if macro exists."""
    macros_dict = bot_interface.load_server_macros(guild_id, guild_name)

    if macro_name not in macros_dict:
        messages.error(request, f"Macro '{macro_name}' not found")
        return None, None, None

    new_name = request.POST.get("name", "").strip()
    new_message = request.POST.get("message", "").strip()

    if not new_name:
        messages.error(request, "Macro name cannot be empty")
        return None, None, None

    if not new_message:
        messages.error(request, "Macro message cannot be empty")
        return None, None, None

    return new_name, new_message, macros_dict


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
    try:
        guild_name = _validate_server_access(request, guild_id)

        if request.method == "POST":
            # Debug logging
            logger.debug(f"Editing macro '{macro_name}' for guild {guild_id}")
            logger.debug(
                f"Form data - name: '{request.POST.get('name')}', message length: {len(request.POST.get('message', ''))}"
            )

            validation_result = _validate_macro_edit_inputs(
                request, macro_name, guild_id, guild_name
            )
            if validation_result[0] is None:  # Validation failed
                logger.debug("Validation failed, redirecting")
                return redirect("servers:server_detail", guild_id=guild_id)

            new_name, new_message, existing_macros = validation_result
            logger.debug(
                f"After validation - old_name: '{macro_name}', new_name: '{new_name}'"
            )
            logger.debug(f"Existing macros: {list(existing_macros.keys())}")

            # Check for name conflicts
            if new_name != macro_name and new_name in existing_macros:
                error_msg = f"A macro named '{new_name}' already exists"
                messages.error(request, error_msg)
                logger.info(
                    f"Name conflict detected for '{new_name}' in guild {guild_id}"
                )
                return redirect("servers:server_detail", guild_id=guild_id)

            # Get user info and update macro
            user_id = str(request.user.socialaccount_set.first().uid)
            user_name = request.user.username

            update_data = MacroUpdateData(
                guild_id=guild_id,
                guild_name=guild_name,
                old_name=macro_name,
                new_name=new_name,
                message=new_message,
                edited_by=user_id,
                edited_by_name=user_name,
            )

            success, error_message = bot_interface.update_macro(update_data)

            if success:
                if new_name != macro_name:
                    messages.success(
                        request,
                        f"Successfully renamed macro '{macro_name}' to '{new_name}' and updated content",
                    )
                else:
                    messages.success(
                        request, f"Successfully updated macro '{macro_name}'"
                    )
            else:
                messages.error(request, error_message)
                logger.error(f"Bot interface error: {error_message}")

            return redirect("servers:server_detail", guild_id=guild_id)

        # For GET requests
        messages.info(
            request, f"Use the edit button on the server page to edit '{macro_name}'"
        )
        return redirect("servers:server_detail", guild_id=guild_id)

    except DiscordAPIError as e:
        messages.error(request, f"Error accessing server: {e}")
        return redirect("servers:server_detail", guild_id=guild_id)


@login_required
def macro_get(request, guild_id, macro_name):
    """Get macro data for editing (AJAX endpoint).

    Args:
        request: Django HTTP request object with authenticated user.
        guild_id (int): Discord guild/server ID containing the macro.
        macro_name (str): Name of the macro to get.

    Returns:
        JsonResponse: Macro data in JSON format or error response.
    """
    try:
        # Get user's Discord guilds to verify access
        user_guilds = get_user_guilds(request.user)
        user_guild_ids = [int(guild["id"]) for guild in user_guilds]

        if guild_id not in user_guild_ids:
            return JsonResponse(
                {"error": "You don't have access to this server"}, status=403
            )

        # Find guild name
        guild_name = None
        for guild in user_guilds:
            if int(guild["id"]) == guild_id:
                guild_name = guild["name"]
                break

        if not guild_name:
            return JsonResponse({"error": "Server not found"}, status=404)

        # Load current macros
        macros_dict = bot_interface.load_server_macros(guild_id, guild_name)

        if macro_name not in macros_dict:
            return JsonResponse({"error": "Macro not found"}, status=404)

        current_macro = macros_dict[macro_name]

        # Extract current message (handle both legacy and modern formats)
        if isinstance(current_macro, dict):
            message = current_macro.get("message", "")
            created_by_name = current_macro.get("created_by_name", "Unknown")
            created_at = current_macro.get("created_at", "")
            updated_by_name = current_macro.get("updated_by_name", "")
            updated_at = current_macro.get("updated_at", "")
        else:
            message = current_macro
            created_by_name = "Unknown"
            created_at = ""
            updated_by_name = ""
            updated_at = ""

        return JsonResponse(
            {
                "name": macro_name,
                "message": message,
                "created_by_name": created_by_name,
                "created_at": created_at,
                "updated_by_name": updated_by_name,
                "updated_at": updated_at,
            }
        )

    except DiscordAPIError as e:
        return JsonResponse({"error": f"Error accessing server: {e}"}, status=500)


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


@login_required
def check_macro_name(request, guild_id, macro_name):
    """Check if a macro name is available for use (AJAX endpoint).

    Args:
        request: Django HTTP request object with authenticated user.
        guild_id (int): Discord guild/server ID to check macros for.
        macro_name (str): Name to check for availability.

    Returns:
        JsonResponse: Availability status and message.
    """
    try:
        # Get user's Discord guilds to verify access
        user_guilds = get_user_guilds(request.user)
        user_guild_ids = [int(guild["id"]) for guild in user_guilds]

        if guild_id not in user_guild_ids:
            return JsonResponse(
                {"error": "You don't have access to this server"}, status=403
            )

        # Find guild name
        guild_name = None
        for guild in user_guilds:
            if int(guild["id"]) == guild_id:
                guild_name = guild["name"]
                break

        if not guild_name:
            return JsonResponse({"error": "Server not found"}, status=404)

        # Load current macros
        macros_dict = bot_interface.load_server_macros(guild_id, guild_name)

        # Check if name exists
        name_exists = macro_name in macros_dict

        return JsonResponse(
            {
                "available": not name_exists,
                "message": f"Macro name '{macro_name}' is already taken"
                if name_exists
                else f"Macro name '{macro_name}' is available",
            }
        )

    except DiscordAPIError as e:
        return JsonResponse({"error": f"Error accessing server: {e}"}, status=500)
