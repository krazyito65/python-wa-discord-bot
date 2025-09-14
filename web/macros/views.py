"""
Macro views for WeakAuras Web Interface

This module contains views for managing macros (create, edit, delete, list)
for specific Discord servers through the web interface.
"""

import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render

from admin_panel.models import ServerPermissionConfig
from shared.bot_interface import MacroData, MacroUpdateData, bot_interface
from shared.discord_api import DiscordAPIError, get_user_guilds, get_user_roles_in_guild

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
def macro_add(request, guild_id):  # noqa: PLR0911
    """Add a new macro to a specific server.

    Args:
        request: Django HTTP request object with authenticated user.
        guild_id (int): Discord guild/server ID to add macro to.

    Returns:
        HttpResponse: Rendered macro add template or redirect after creation.
    """
    try:
        guild_name = _validate_server_access(request, guild_id)

        # Check create_macros permission
        if not _check_server_permission(request, guild_id, 'create_macros'):
            messages.error(
                request, "You don't have permission to create macros in this server"
            )
            return redirect("servers:server_detail", guild_id=guild_id)

        if request.method == "POST":
            # Get form data
            macro_name = request.POST.get("name", "").strip()
            macro_message = request.POST.get("message", "").strip()

            # Validate inputs - if validation fails, we'll render the form again with data
            validation_errors = []
            if not macro_name:
                validation_errors.append("Macro name cannot be empty")

            if not macro_message:
                validation_errors.append("Macro message cannot be empty")

            # Check if macro name already exists
            if macro_name:  # Only check if name is not empty
                existing_macros = bot_interface.load_server_macros(guild_id, guild_name)
                if macro_name in existing_macros:
                    validation_errors.append(
                        f"A macro named '{macro_name}' already exists"
                    )

            # If there are validation errors, render form with preserved data
            if validation_errors:
                for error in validation_errors:
                    messages.error(request, error)

                # Get guild info for template context
                user_guilds = get_user_guilds(request.user)
                guild_info = next(
                    (guild for guild in user_guilds if int(guild["id"]) == guild_id),
                    None,
                )

                if not guild_info:
                    messages.error(request, "Server not found")
                    return redirect("servers:dashboard")

                context = {
                    "guild": guild_info,
                    "guild_id": guild_id,
                    "form_data": {
                        "name": macro_name,
                        "message": macro_message,
                    },
                    "feature_flags": settings.FEATURE_FLAGS,
                }

                return render(request, "macros/macro_add.html", context)

            # Get user info
            user_id = str(request.user.socialaccount_set.first().uid) if request.user.socialaccount_set.first() else str(request.user.id)
            user_name = request.user.username

            # Create macro data
            macro_data = MacroData(
                guild_id=guild_id,
                guild_name=guild_name,
                name=macro_name,
                message=macro_message,
                created_by=user_id,
                created_by_name=user_name,
            )

            # Add the macro
            if bot_interface.add_macro(macro_data):
                messages.success(request, f"Successfully created macro '{macro_name}'")
                return redirect("servers:server_detail", guild_id=guild_id)

            messages.error(request, "Failed to create macro. Please try again.")

            # Get guild info for template context
            user_guilds = get_user_guilds(request.user)
            guild_info = next(
                (guild for guild in user_guilds if int(guild["id"]) == guild_id), None
            )

            if not guild_info:
                messages.error(request, "Server not found")
                return redirect("servers:dashboard")

            context = {
                "guild": guild_info,
                "guild_id": guild_id,
                "form_data": {
                    "name": macro_name,
                    "message": macro_message,
                },
                "feature_flags": settings.FEATURE_FLAGS,
            }

            return render(request, "macros/macro_add.html", context)

        # For GET requests, render the creation form
        # Get guild info for template context
        user_guilds = get_user_guilds(request.user)
        guild_info = next(
            (guild for guild in user_guilds if int(guild["id"]) == guild_id), None
        )

        if not guild_info:
            messages.error(request, "Server not found")
            return redirect("servers:dashboard")

        context = {
            "guild": guild_info,
            "guild_id": guild_id,
            "feature_flags": settings.FEATURE_FLAGS,
        }

        return render(request, "macros/macro_add.html", context)

    except DiscordAPIError as e:
        messages.error(request, f"Error accessing server: {e}")
        return redirect("servers:dashboard")


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


def _check_server_permission(request, guild_id: int, permission_type: str) -> bool:
    """
    Check if user has the specified permission for the given server using admin panel config.

    Args:
        request: Django HTTP request with authenticated user
        guild_id: Discord guild ID to check permissions for
        permission_type: Type of permission to check ('create_macros', 'edit_macros', 'delete_macros', etc.)

    Returns:
        bool: True if user has the specified permission, False otherwise
    """
    try:
        # Get user's Discord guilds to get guild info and permissions
        user_guilds = get_user_guilds(request.user)
        guild_info = next(
            (guild for guild in user_guilds if int(guild["id"]) == guild_id),
            None,
        )

        if not guild_info:
            logger.warning(f"Guild {guild_id} not found in user's guilds")
            return False

        guild_name = guild_info["name"]
        is_server_owner = guild_info.get("owner", False)
        guild_permissions = int(guild_info.get("permissions", 0))

        # Get or create server permission configuration
        server_config, created = ServerPermissionConfig.objects.get_or_create(
            guild_id=str(guild_id),
            defaults={
                'guild_name': guild_name,
                'updated_by': str(request.user.socialaccount_set.first().uid) if request.user.socialaccount_set.first() else '',
                'updated_by_name': request.user.username,
            }
        )

        # For newly created configs, default to admin_only for create/edit/delete operations
        if created:
            logger.info(f"Created new server config for guild {guild_id}, using default admin-only permissions")
            # For new configs, use basic admin permission check (Discord administrator/owner/manage server)
            return is_server_owner or (guild_permissions & 0x8) == 0x8 or (guild_permissions & 0x20) == 0x20
        else:
            # Use the configured permission system with actual roles
            try:
                user_roles_data = get_user_roles_in_guild(request.user, guild_id) or []
                user_role_names = [role["name"].lower() for role in user_roles_data]
            except DiscordAPIError:
                user_role_names = []  # Fall back to empty roles if API fails

            has_permission = server_config.has_permission(user_role_names, permission_type, guild_permissions, is_server_owner)

            logger.info(
                f"Permission check for user {request.user.username} in guild {guild_id}: "
                f"permission_type={permission_type}, result={has_permission}, "
                f"permission_level={getattr(server_config, permission_type, 'admin_only')}"
            )

            return has_permission

    except Exception as e:
        logger.error(f"Error checking {permission_type} permission for user {request.user.username} in guild {guild_id}: {e}")
        return False


def _validate_admin_permissions(request, guild_id):
    """Validate that user has admin permissions for the given server.

    This is a legacy function that now uses the server-specific permission system
    for 'edit_macros' and 'delete_macros' permissions.

    Args:
        request: Django HTTP request with authenticated user.
        guild_id: Discord guild ID to check permissions for.

    Returns:
        bool: True if user has admin permissions, False otherwise.
    """
    return _check_server_permission(request, guild_id, 'edit_macros')


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

        # Check admin permissions for editing macros
        if not _validate_admin_permissions(request, guild_id):
            messages.error(
                request, "You don't have permission to edit macros in this server"
            )
            return redirect("servers:server_detail", guild_id=guild_id)

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
            user_id = str(request.user.socialaccount_set.first().uid) if request.user.socialaccount_set.first() else str(request.user.id)
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
        guild_name = _validate_server_access(request, guild_id)

        # Check admin permissions for editing macros
        if not _validate_admin_permissions(request, guild_id):
            return JsonResponse(
                {"error": "You don't have permission to edit macros in this server"},
                status=403,
            )

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
def debug_permissions(request, guild_id):
    """Debug endpoint to show user's permissions for troubleshooting."""
    try:
        guild_name = _validate_server_access(request, guild_id)

        # Get guild permissions
        user_guilds = get_user_guilds(request.user)
        guild_permissions = 0
        guild_info = None

        for guild in user_guilds:
            if int(guild["id"]) == guild_id:
                guild_permissions = int(guild.get("permissions", 0))
                guild_info = guild
                break

        # Get bot config
        config = bot_interface.load_bot_config()
        permissions_config = config.get("bot", {}).get("permissions", {})

        # Check admin access
        admin_access = _validate_admin_permissions(request, guild_id)

        # Create debug info
        debug_info = {
            "guild_id": guild_id,
            "guild_name": guild_name,
            "guild_info": guild_info,
            "user_permissions": guild_permissions,
            "user_permissions_hex": f"0x{guild_permissions:x}",
            "bot_config": permissions_config,
            "admin_access": admin_access,
            "permission_bits": {
                "administrator": 0x8,
                "manage_channels": 0x10,
                "manage_guild": 0x20,
                "manage_messages": 0x2000,
                "manage_roles": 0x10000000,
                "manage_webhooks": 0x20000000,
                "kick_members": 0x2,
                "ban_members": 0x4,
            },
        }

        return JsonResponse(debug_info, json_dumps_params={"indent": 2})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


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
        guild_name = _validate_server_access(request, guild_id)

        # Check delete_macros permission
        if not _check_server_permission(request, guild_id, 'delete_macros'):
            messages.error(
                request, "You don't have permission to delete macros in this server"
            )
            return redirect("servers:server_detail", guild_id=guild_id)

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
        guild_name = _validate_server_access(request, guild_id)

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
