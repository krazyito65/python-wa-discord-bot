import os
import re
import sys
from pathlib import Path

import discord
import django
from bot.weakauras_bot import WeakAurasBot
from discord import app_commands
from utils.logging import get_logger, log_command

# Setup Django for database access
try:
    web_dir = Path(__file__).resolve().parent.parent.parent / "web"
    if str(web_dir) not in sys.path:
        sys.path.append(str(web_dir))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "weakauras_web.settings")
    django.setup()
    from admin_panel.models import AssignableRole, ServerPermissionConfig
    from asgiref.sync import sync_to_async
except ImportError:
    # Django models not available - assignable role commands will be disabled
    AssignableRole = None
    ServerPermissionConfig = None
    sync_to_async = None

logger = get_logger(__name__)

# Hex color length constant
HEX_COLOR_LENGTH = 6

# Role list display limit
ROLE_LIST_DISPLAY_LIMIT = 20


def is_valid_hex_color(hex_color: str) -> bool:
    """
    Validate if a string is a valid hex color code.

    Args:
        hex_color: String to validate (with or without # prefix)

    Returns:
        bool: True if valid hex color, False otherwise
    """
    # Remove # if present and ensure lowercase
    color = hex_color.lstrip("#").lower()

    # Check if it's exactly 6 characters and all are valid hex digits
    return len(color) == HEX_COLOR_LENGTH and all(
        c in "0123456789abcdef" for c in color
    )


def hex_to_discord_color(hex_color: str) -> discord.Color:
    """
    Convert hex color string to Discord Color object.

    Args:
        hex_color: Hex color string (with or without # prefix)

    Returns:
        discord.Color: Discord color object
    """
    # Remove # if present
    color = hex_color.lstrip("#")
    # Convert to integer
    return discord.Color(int(color, 16))


def find_existing_color_role(
    guild: discord.Guild, hex_color: str
) -> discord.Role | None:
    """
    Find an existing role with the same hex color name.

    Args:
        guild: Discord guild to search in
        hex_color: Hex color string to search for

    Returns:
        discord.Role | None: Existing role if found, None otherwise
    """
    # Normalize the hex color for comparison
    normalized_color = hex_color.lstrip("#").lower()

    for role in guild.roles:
        # Check if role name matches hex pattern and color
        if re.match(r"^#?[0-9a-f]{6}$", role.name.lower()):
            role_color = role.name.lstrip("#").lower()
            if role_color == normalized_color:
                return role

    return None


async def get_lowest_position(_guild: discord.Guild) -> int:
    """
    Get the lowest position for placing color roles at the bottom of hierarchy.

    Args:
        guild: Discord guild

    Returns:
        int: Position for new color role (just above @everyone)
    """
    # Position 1 is just above @everyone (which is position 0)
    return 1


async def create_color_role(
    guild: discord.Guild, hex_color: str, _bot_member: discord.Member
) -> discord.Role:
    """
    Create a new color role with the specified hex color.

    Args:
        guild: Discord guild to create role in
        hex_color: Hex color string
        bot_member: Bot's member object for permission checking

    Returns:
        discord.Role: The created role

    Raises:
        discord.Forbidden: If bot lacks permissions
        discord.HTTPException: If role creation fails
    """
    # Normalize hex color for role name
    normalized_color = hex_color.lstrip("#").lower()
    role_name = f"#{normalized_color}"

    # Convert to Discord color
    role_color = hex_to_discord_color(normalized_color)

    # Get position for role (bottom of hierarchy)
    position = await get_lowest_position(guild)

    # Create the role
    role = await guild.create_role(
        name=role_name, color=role_color, reason="Color role created by WeakAuras bot"
    )

    # Move role to bottom position
    try:
        await role.edit(position=position)
    except discord.HTTPException:
        # If position edit fails, role is still created successfully
        logger.warning(
            f"Could not set position for color role {role_name} in {guild.name}"
        )

    return role


async def remove_existing_color_roles(member: discord.Member) -> list[str]:
    """
    Remove all existing color roles from a member.

    Args:
        member: Discord member to remove color roles from

    Returns:
        list[str]: List of removed role names
    """
    removed_roles = []
    for user_role in member.roles:
        # Check if it's a color role (hex pattern)
        if re.match(r"^#[0-9a-f]{6}$", user_role.name.lower()):
            try:
                await member.remove_roles(user_role, reason="Removing old color role")
                removed_roles.append(user_role.name)
                logger.info(
                    f"Removed old color role {user_role.name} from {member.name}"
                )
            except discord.HTTPException as e:
                logger.warning(f"Could not remove old color role {user_role.name}: {e}")
    return removed_roles


async def validate_color_role_request(
    interaction: discord.Interaction, hex_color: str
) -> tuple[bool, str | None]:
    """
    Validate a color role request.

    Args:
        interaction: Discord interaction
        hex_color: Hex color string to validate

    Returns:
        tuple[bool, str | None]: (is_valid, error_message)
    """
    # Ensure command is used in a guild
    if not interaction.guild:
        return False, "❌ This command can only be used in a server."

    # Validate hex color
    if not is_valid_hex_color(hex_color):
        return (
            False,
            "❌ Invalid hex color code. Please use format: `#ff0000` or `ff0000`",
        )

    # Check bot permissions
    bot_member = interaction.guild.get_member(interaction.client.user.id)
    if not bot_member:
        return False, "❌ Bot member not found in this server."

    if not bot_member.guild_permissions.manage_roles:
        return (
            False,
            "❌ Bot lacks permission to manage roles. Please contact an administrator.",
        )

    return True, None


async def get_assignable_roles_from_db(guild_id: int) -> list[dict]:
    """
    Get assignable roles from the Django database.

    Args:
        guild_id: Discord guild ID

    Returns:
        list[dict]: List of assignable role data from database
    """
    try:
        if not AssignableRole or not ServerPermissionConfig or not sync_to_async:
            return []

        # Get server config using sync_to_async
        server_config = await sync_to_async(
            lambda: ServerPermissionConfig.objects.filter(
                guild_id=str(guild_id)
            ).first()
        )()
        if not server_config:
            return []

        # Get assignable roles using sync_to_async
        assignable_roles = await sync_to_async(
            lambda: list(
                AssignableRole.objects.filter(
                    server_config=server_config, is_self_assignable=True
                )
            )
        )()

        return [
            {
                "role_id": role.role_id,
                "role_name": role.role_name,
                "role_color": role.role_color,
                "requires_permission": role.requires_permission,
            }
            for role in assignable_roles
        ]

    except Exception:
        logger.exception("Error fetching assignable roles from database")
        return []


async def assignable_role_autocomplete(
    interaction: discord.Interaction, current: str
) -> list[app_commands.Choice[str]]:
    """Autocomplete function for assignable role names."""
    if not interaction.guild:
        return []

    # Get assignable roles from database
    assignable_roles = await get_assignable_roles_from_db(interaction.guild.id)

    # Filter by current input
    filtered_roles = [
        role
        for role in assignable_roles
        if current.lower() in role["role_name"].lower()
    ]

    # Return up to 25 choices (Discord limit)
    return [
        app_commands.Choice(name=role["role_name"], value=role["role_id"])
        for role in filtered_roles[:25]
    ]


def setup_basic_color_commands(bot: WeakAurasBot):
    """Set up basic color role commands (role, remove_role)."""

    @bot.tree.command(
        name="role",
        description="Apply a color role using hex color code OR assign an available server role",
    )
    @app_commands.describe(
        hex_color="Hex color code (e.g., #ff0000) OR leave blank to assign server role",
        role_id="Server role to assign (use autocomplete, optional)",
    )
    @app_commands.autocomplete(role_id=assignable_role_autocomplete)
    @log_command
    async def role(
        interaction: discord.Interaction, hex_color: str = None, role_id: str = None
    ):
        """Apply a color role using hex color code OR assign an available server role."""

        # Ensure command is used in a guild
        if not interaction.guild:
            await interaction.response.send_message(
                "❌ This command can only be used in a server.", ephemeral=True
            )
            return

        # Check if both parameters are provided or neither
        if (hex_color and role_id) or (not hex_color and not role_id):
            await interaction.response.send_message(
                "❌ Please provide either a hex color code OR select a server role, not both.",
                ephemeral=True,
            )
            return

        # Handle assignable role assignment
        if role_id:
            await assign_server_role(interaction, role_id)
            return

        # Handle hex color role assignment
        if hex_color:
            # Validate the hex color request
            is_valid, error_message = await validate_color_role_request(
                interaction, hex_color
            )
            if not is_valid:
                await interaction.response.send_message(error_message, ephemeral=True)
                return

            await assign_hex_color_role(interaction, hex_color, bot)


async def assign_server_role(interaction: discord.Interaction, role_id: str):
    """Handle assignable role assignment logic."""
    # Get assignable roles from database
    assignable_roles = await get_assignable_roles_from_db(interaction.guild.id)

    # Find the requested role
    role_data = next(
        (role for role in assignable_roles if role["role_id"] == role_id), None
    )
    if not role_data:
        await interaction.response.send_message(
            "❌ This role is not available for assignment or does not exist.",
            ephemeral=True,
        )
        return

    # Get the Discord role object
    discord_role = interaction.guild.get_role(int(role_id))
    if not discord_role:
        await interaction.response.send_message(
            "❌ Role not found in Discord server.", ephemeral=True
        )
        return

    # Check bot permissions
    bot_member = interaction.guild.get_member(interaction.client.user.id)
    if not bot_member or not bot_member.guild_permissions.manage_roles:
        await interaction.response.send_message(
            "❌ Bot lacks permission to manage roles. Please contact an administrator.",
            ephemeral=True,
        )
        return

    # Get user member - interaction.user should be a Member in guild context
    user_member = interaction.user
    if not hasattr(interaction.user, "roles"):
        # Fallback: try to get Member object explicitly
        user_member = interaction.guild.get_member(interaction.user.id)
    if not user_member:
        await interaction.response.send_message(
            "❌ Could not find your member profile in this server. Please try again.",
            ephemeral=True,
        )
        return

    # Check if user already has this role
    if discord_role in user_member.roles:
        await interaction.response.send_message(
            f"ℹ️ You already have the role **{discord_role.name}**.", ephemeral=True
        )
        return

    # Assign the role
    try:
        await user_member.add_roles(
            discord_role, reason="Self-assigned via bot command"
        )

        # Success message with role color
        embed = discord.Embed(
            title="✅ Role Assigned",
            description=f"You have been assigned the role: **{discord_role.name}**",
            color=discord_role.color
            if discord_role.color.value != 0
            else discord.Color.green(),
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

        logger.info(
            f"Successfully assigned role {discord_role.name} to {interaction.user.name} in {interaction.guild.name}"
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ Bot lacks permission to assign this role. It may be higher in the hierarchy.",
            ephemeral=True,
        )
        logger.warning(
            f"Forbidden: Could not assign role {discord_role.name} in {interaction.guild.name}"
        )

    except discord.HTTPException:
        await interaction.response.send_message(
            "❌ Failed to assign role. Please try again later.", ephemeral=True
        )
        logger.exception("HTTPException assigning role")


async def assign_hex_color_role(
    interaction: discord.Interaction, hex_color: str, bot: WeakAurasBot
):
    """Handle hex color role assignment logic."""

    # Normalize hex color
    normalized_color = hex_color.lstrip("#").lower()
    bot_member = interaction.guild.get_member(bot.user.id)

    # Defer response as role operations might take time
    await interaction.response.defer(ephemeral=True)

    try:
        # Check if role already exists
        existing_role = find_existing_color_role(interaction.guild, normalized_color)

        if existing_role:
            # Use existing role
            role = existing_role
            logger.info(
                f"Using existing color role {role.name} for user {interaction.user.name}"
            )
        else:
            # Create new role
            role = await create_color_role(
                interaction.guild, normalized_color, bot_member
            )
            logger.info(
                f"Created new color role {role.name} for user {interaction.user.name}"
            )

        # Get user member - interaction.user should be a Member in guild context
        user_member = interaction.user
        if not hasattr(interaction.user, "roles"):
            # Fallback: try to get Member object explicitly
            user_member = interaction.guild.get_member(interaction.user.id)
            if not user_member:
                await interaction.followup.send(
                    "❌ Could not find your member profile in this server. Please try again.",
                    ephemeral=True,
                )
                return

        # Remove any existing color roles from user
        await remove_existing_color_roles(user_member)

        # Add new color role
        await user_member.add_roles(role, reason="Applied color role via bot command")

        # Success message
        embed = discord.Embed(
            title="🎨 Color Role Applied",
            description=f"You now have the color role: **{role.name}**",
            color=role.color,
        )
        embed.add_field(
            name="Color Preview",
            value=f"Your color: `{role.name}`",
            inline=False,
        )

        await interaction.followup.send(embed=embed, ephemeral=True)

        logger.info(
            f"Successfully applied color role {role.name} to {interaction.user.name} in {interaction.guild.name}"
        )

    except discord.Forbidden:
        await interaction.followup.send(
            "❌ Bot lacks permission to create or assign roles. Please contact an administrator.",
            ephemeral=True,
        )
        logger.exception(
            f"Forbidden: Could not create/assign color role in {interaction.guild.name}"
        )

    except discord.HTTPException:
        await interaction.followup.send(
            "❌ Failed to create or assign color role. Please try again later.",
            ephemeral=True,
        )
        logger.exception("HTTPException creating color role")

    except Exception:
        await interaction.followup.send(
            "❌ An unexpected error occurred. Please try again later.",
            ephemeral=True,
        )
        logger.exception("Unexpected error in color_role command")


def setup_remove_role_command(bot: WeakAurasBot):
    """Set up the remove_role command."""

    @bot.tree.command(
        name="remove_role",
        description="Remove your current color role OR unassign a server role",
    )
    @app_commands.describe(
        role_id="Server role to remove (use autocomplete, optional - leave blank to remove color roles)"
    )
    @app_commands.autocomplete(role_id=assignable_role_autocomplete)
    @log_command
    async def remove_color_role(interaction: discord.Interaction, role_id: str = None):
        """Remove the user's current color role OR unassign a server role."""

        # Ensure command is used in a guild
        if not interaction.guild:
            await interaction.response.send_message(
                "❌ This command can only be used in a server.", ephemeral=True
            )
            return

        # Handle specific role removal
        if role_id:
            await remove_specific_role(interaction, role_id)
            return

        # Handle color role removal (default behavior)
        await remove_color_roles(interaction)


async def remove_specific_role(interaction: discord.Interaction, role_id: str):
    """Handle removal of a specific assignable role."""
    # Get the Discord role object
    discord_role = interaction.guild.get_role(int(role_id))
    if not discord_role:
        await interaction.response.send_message(
            "❌ Role not found in Discord server.", ephemeral=True
        )
        return

    # Check bot permissions
    bot_member = interaction.guild.get_member(interaction.client.user.id)
    if not bot_member or not bot_member.guild_permissions.manage_roles:
        await interaction.response.send_message(
            "❌ Bot lacks permission to manage roles. Please contact an administrator.",
            ephemeral=True,
        )
        return

    # Get user member - interaction.user should be a Member in guild context
    user_member = interaction.user
    if not hasattr(interaction.user, "roles"):
        # Fallback: try to get Member object explicitly
        user_member = interaction.guild.get_member(interaction.user.id)
    if not user_member:
        await interaction.response.send_message(
            "❌ Could not find your member profile in this server. Please try again.",
            ephemeral=True,
        )
        return

    # Check if user has this role
    if discord_role not in user_member.roles:
        await interaction.response.send_message(
            f"ℹ️ You don't have the role **{discord_role.name}**.", ephemeral=True
        )
        return

    # Remove the role
    try:
        await user_member.remove_roles(
            discord_role, reason="Self-removed via bot command"
        )

        await interaction.response.send_message(
            f"✅ Removed role: **{discord_role.name}**", ephemeral=True
        )

        logger.info(
            f"Successfully removed role {discord_role.name} from {interaction.user.name} in {interaction.guild.name}"
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ Bot lacks permission to remove this role.", ephemeral=True
        )
        logger.warning(
            f"Forbidden: Could not remove role {discord_role.name} in {interaction.guild.name}"
        )

    except discord.HTTPException:
        await interaction.response.send_message(
            "❌ Failed to remove role. Please try again later.", ephemeral=True
        )
        logger.exception("HTTPException removing role")


async def remove_color_roles(interaction: discord.Interaction):
    """Handle removal of color roles."""
    # Check bot permissions
    bot_member = interaction.guild.get_member(interaction.client.user.id)
    if not bot_member or not bot_member.guild_permissions.manage_roles:
        await interaction.response.send_message(
            "❌ Bot lacks permission to manage roles. Please contact an administrator.",
            ephemeral=True,
        )
        return

    # Get user member - interaction.user should be a Member in guild context
    user_member = interaction.user
    if not hasattr(interaction.user, "roles"):
        # Fallback: try to get Member object explicitly
        user_member = interaction.guild.get_member(interaction.user.id)
    if not user_member:
        await interaction.response.send_message(
            "❌ Could not find your member profile in this server. Please try again.",
            ephemeral=True,
        )
        return

    # Find and remove color roles
    removed_roles = []
    for user_role in user_member.roles:
        # Check if it's a color role (hex pattern)
        if re.match(r"^#[0-9a-f]{6}$", user_role.name.lower()):
            try:
                await user_member.remove_roles(
                    user_role, reason="User requested color role removal"
                )
                removed_roles.append(user_role.name)
                logger.info(
                    f"Removed color role {user_role.name} from {interaction.user.name}"
                )
            except discord.HTTPException as e:
                logger.warning(f"Could not remove color role {user_role.name}: {e}")

    if removed_roles:
        await interaction.response.send_message(
            f"✅ Removed color role(s): {', '.join(removed_roles)}", ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "ℹ️ You don't currently have any color roles.", ephemeral=True
        )


def setup_assign_role_command(bot: WeakAurasBot):
    """Set up the assign_role command."""

    @bot.tree.command(
        name="assign_role",
        description="Assign a role from the server's assignable roles list",
    )
    @app_commands.describe(role_id="Role to assign (from assignable roles list)")
    @app_commands.autocomplete(role_id=assignable_role_autocomplete)
    @log_command
    async def assign_role(interaction: discord.Interaction, role_id: str):
        """Assign an assignable role to the user."""

        # Ensure command is used in a guild
        if not interaction.guild:
            await interaction.response.send_message(
                "❌ This command can only be used in a server.", ephemeral=True
            )
            return

        # Get assignable roles from database
        assignable_roles = await get_assignable_roles_from_db(interaction.guild.id)

        # Find the requested role
        role_data = next(
            (role for role in assignable_roles if role["role_id"] == role_id), None
        )
        if not role_data:
            await interaction.response.send_message(
                "❌ This role is not available for assignment or does not exist.",
                ephemeral=True,
            )
            return

        # Get the Discord role object
        discord_role = interaction.guild.get_role(int(role_id))
        if not discord_role:
            await interaction.response.send_message(
                "❌ Role not found in Discord server.", ephemeral=True
            )
            return

        # Check bot permissions
        bot_member = interaction.guild.get_member(bot.user.id)
        if not bot_member or not bot_member.guild_permissions.manage_roles:
            await interaction.response.send_message(
                "❌ Bot lacks permission to manage roles. Please contact an administrator.",
                ephemeral=True,
            )
            return

        # Get user member
        user_member = interaction.guild.get_member(interaction.user.id)
        if not user_member:
            await interaction.response.send_message(
                "❌ Could not find your member profile in this server. Please try again.",
                ephemeral=True,
            )
            return

        # Check if user already has this role
        if discord_role in user_member.roles:
            await interaction.response.send_message(
                f"ℹ️ You already have the role **{discord_role.name}**.", ephemeral=True
            )
            return

        # Assign the role
        try:
            await user_member.add_roles(
                discord_role, reason="Self-assigned via bot command"
            )

            # Success message with role color
            embed = discord.Embed(
                title="✅ Role Assigned",
                description=f"You have been assigned the role: **{discord_role.name}**",
                color=discord_role.color
                if discord_role.color.value != 0
                else discord.Color.green(),
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

            logger.info(
                f"Successfully assigned role {discord_role.name} to {interaction.user.name} in {interaction.guild.name}"
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Bot lacks permission to assign this role. It may be higher in the hierarchy.",
                ephemeral=True,
            )
            logger.warning(
                f"Forbidden: Could not assign role {discord_role.name} in {interaction.guild.name}"
            )

        except discord.HTTPException:
            await interaction.response.send_message(
                "❌ Failed to assign role. Please try again later.", ephemeral=True
            )
            logger.exception("HTTPException assigning role")


def setup_unassign_role_command(bot: WeakAurasBot):
    """Set up the unassign_role command."""

    @bot.tree.command(name="unassign_role", description="Remove a role from yourself")
    @app_commands.describe(role_id="Role to remove (from your current roles)")
    @app_commands.autocomplete(role_id=assignable_role_autocomplete)
    @log_command
    async def unassign_role(interaction: discord.Interaction, role_id: str):
        """Remove an assignable role from the user."""

        # Ensure command is used in a guild
        if not interaction.guild:
            await interaction.response.send_message(
                "❌ This command can only be used in a server.", ephemeral=True
            )
            return

        # Get the Discord role object
        discord_role = interaction.guild.get_role(int(role_id))
        if not discord_role:
            await interaction.response.send_message(
                "❌ Role not found in Discord server.", ephemeral=True
            )
            return

        # Check bot permissions
        bot_member = interaction.guild.get_member(bot.user.id)
        if not bot_member or not bot_member.guild_permissions.manage_roles:
            await interaction.response.send_message(
                "❌ Bot lacks permission to manage roles. Please contact an administrator.",
                ephemeral=True,
            )
            return

        # Get user member
        user_member = interaction.guild.get_member(interaction.user.id)
        if not user_member:
            await interaction.response.send_message(
                "❌ Could not find your member profile in this server. Please try again.",
                ephemeral=True,
            )
            return

        # Check if user has this role
        if discord_role not in user_member.roles:
            await interaction.response.send_message(
                f"ℹ️ You don't have the role **{discord_role.name}**.", ephemeral=True
            )
            return

        # Remove the role
        try:
            await user_member.remove_roles(
                discord_role, reason="Self-removed via bot command"
            )

            await interaction.response.send_message(
                f"✅ Removed role: **{discord_role.name}**", ephemeral=True
            )

            logger.info(
                f"Successfully removed role {discord_role.name} from {interaction.user.name} in {interaction.guild.name}"
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Bot lacks permission to remove this role.", ephemeral=True
            )
            logger.warning(
                f"Forbidden: Could not remove role {discord_role.name} in {interaction.guild.name}"
            )

        except discord.HTTPException:
            await interaction.response.send_message(
                "❌ Failed to remove role. Please try again later.", ephemeral=True
            )
            logger.exception("HTTPException removing role")


def setup_list_roles_command(bot: WeakAurasBot):
    """Set up the list_roles command."""

    @bot.tree.command(
        name="list_roles",
        description="List all available assignable roles in this server",
    )
    @log_command
    async def list_roles(interaction: discord.Interaction):
        """List all assignable roles in the server."""

        # Ensure command is used in a guild
        if not interaction.guild:
            await interaction.response.send_message(
                "❌ This command can only be used in a server.", ephemeral=True
            )
            return

        # Get assignable roles from database
        assignable_roles = await get_assignable_roles_from_db(interaction.guild.id)

        if not assignable_roles:
            await interaction.response.send_message(
                "ℹ️ No assignable roles are currently configured for this server.",
                ephemeral=True,
            )
            return

        # Create embed with role list
        embed = discord.Embed(
            title="🎭 Assignable Roles",
            description=f"Available roles in **{interaction.guild.name}**:",
            color=discord.Color.blue(),
        )

        role_list = []
        for role_data in assignable_roles:
            discord_role = interaction.guild.get_role(int(role_data["role_id"]))
            if discord_role:
                role_list.append(f"• **{discord_role.name}**")

        if role_list:
            embed.add_field(
                name="Available Roles",
                value="\n".join(role_list[:ROLE_LIST_DISPLAY_LIMIT]),
                inline=False,
            )

            if len(role_list) > ROLE_LIST_DISPLAY_LIMIT:
                embed.add_field(
                    name="",
                    value=f"... and {len(role_list) - ROLE_LIST_DISPLAY_LIMIT} more roles",
                    inline=False,
                )

            embed.set_footer(text="Use /role to assign a role to yourself")

            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(
                "ℹ️ No assignable roles are currently available.", ephemeral=True
            )


def setup_color_role_commands(bot: WeakAurasBot):
    """Set up all color role and assignable role commands."""
    setup_basic_color_commands(bot)
    setup_remove_role_command(bot)
    setup_list_roles_command(bot)
