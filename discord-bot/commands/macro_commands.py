import discord
from bot.weakauras_bot import WeakAurasBot
from discord import app_commands
from utils.django_permissions import (
    check_server_permission,
    get_permission_error_message,
    get_server_permission_config,
)
from utils.logging import get_logger, log_command

logger = get_logger(__name__)


async def send_embed_response(
    interaction: discord.Interaction,
    embed: discord.Embed,
    logo_file: discord.File | None,
    ephemeral: bool = True,
):
    """Helper function to send embed response with optional file attachment"""
    kwargs = {"embed": embed, "ephemeral": ephemeral}
    if logo_file:
        kwargs["file"] = logo_file
    await interaction.response.send_message(**kwargs)


def setup_macro_commands(bot: WeakAurasBot):  # noqa: PLR0915
    """Setup all macro-related slash commands"""

    async def macro_name_autocomplete(
        interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete function for macro names"""
        if not interaction.guild:
            return []

        guild_id = interaction.guild.id
        guild_name = interaction.guild.name
        macros = bot.load_server_macros(guild_id, guild_name)

        # Filter macro names based on current input
        filtered_macros = [name for name in macros if current.lower() in name.lower()]

        # Return up to 25 choices (Discord limit)
        return [
            app_commands.Choice(name=name, value=name) for name in filtered_macros[:25]
        ]

    @bot.tree.command(
        name="create_macro", description="Create a new WeakAuras macro command"
    )
    @log_command
    async def create_macro(interaction: discord.Interaction, name: str, message: str):
        """Create a new macro with the given name and message"""
        if not interaction.guild:
            logger.warning("create_macro command used outside of server")
            await interaction.response.send_message(
                "This command can only be used in a server!", ephemeral=True
            )
            return

        guild_id = interaction.guild.id
        guild_name = interaction.guild.name

        # Check if user has permission to create macros
        if not isinstance(interaction.user, discord.Member) or not check_server_permission(
            interaction.user, guild_id, 'create_macros'
        ):
            config = get_server_permission_config(guild_id)
            error_message = get_permission_error_message('create_macros', config)

            embed, logo_file = bot.create_embed(
                title="❌ Permission Denied",
                description=error_message,
                footer_text=f"Server: {guild_name}",
            )
            await send_embed_response(interaction, embed, logo_file)
            logger.warning("create_macro command denied - insufficient permissions")
            return

        # Load server-specific macros
        macros = bot.load_server_macros(guild_id, guild_name)

        if name in macros:
            logger.info(f"create_macro failed - macro '{name}' already exists")
            await interaction.response.send_message(
                f"WeakAuras macro '{name}' already exists!", ephemeral=True
            )
            return

        # Store as JSON-formatted macro data
        macro_data = {
            "name": name,
            "message": message,
            "created_by": str(interaction.user.id),
            "created_by_name": interaction.user.name,
            "created_at": interaction.created_at.isoformat(),
        }

        macros[name] = macro_data
        bot.save_server_macros(guild_id, guild_name, macros)
        logger.info(
            f"Successfully created macro '{name}' in guild {guild_name} ({guild_id})"
        )

        # Create branded success embed
        embed, logo_file = bot.create_embed(
            title="✅ Macro Created",
            description=f"Successfully created macro **{name}**",
            footer_text=f"Server: {guild_name}",
        )
        await send_embed_response(interaction, embed, logo_file)

    @bot.tree.command(
        name="list_macros", description="List all available WeakAuras macros"
    )
    @log_command
    async def list_macros(interaction: discord.Interaction):
        """List all available macros for this server"""
        if not interaction.guild:
            logger.warning("list_macros command used outside of server")
            await interaction.response.send_message(
                "This command can only be used in a server!", ephemeral=True
            )
            return

        guild_id = interaction.guild.id
        guild_name = interaction.guild.name
        macros = bot.load_server_macros(guild_id, guild_name)

        if not macros:
            logger.info(
                f"list_macros returned 0 macros for guild {guild_name} ({guild_id})"
            )
            embed, logo_file = bot.create_embed(
                title="📂 No Macros Found",
                description="No WeakAuras macros available in this server.",
                footer_text=f"Server: {guild_name}",
            )
            await send_embed_response(interaction, embed, logo_file)
            return

        logger.info(
            f"list_macros returned {len(macros)} macros for guild {guild_name} ({guild_id}): {', '.join(macros.keys())}"
        )
        macro_list = "\n".join([f"• {name}" for name in macros])
        embed, logo_file = bot.create_embed(
            title="📂 WeakAuras Macros",
            description=macro_list,
            footer_text=f"Server: {guild_name}",
        )
        await send_embed_response(interaction, embed, logo_file)

    @bot.tree.command(
        name="delete_macro",
        description="Delete an existing WeakAuras macro (Admin only)",
    )
    @app_commands.autocomplete(name=macro_name_autocomplete)
    @log_command
    async def delete_macro(interaction: discord.Interaction, name: str):
        """Delete a macro from this server (requires admin role)"""
        if not interaction.guild:
            logger.warning("delete_macro command used outside of server")
            await interaction.response.send_message(
                "This command can only be used in a server!", ephemeral=True
            )
            return

        # Check if user has permission to delete macros
        if not isinstance(interaction.user, discord.Member) or not check_server_permission(
            interaction.user, interaction.guild.id, 'delete_macros'
        ):
            config = get_server_permission_config(interaction.guild.id)
            error_message = get_permission_error_message('delete_macros', config)

            embed, logo_file = bot.create_embed(
                title="❌ Permission Denied",
                description=error_message,
                footer_text=f"Server: {interaction.guild.name}",
            )
            await send_embed_response(interaction, embed, logo_file)
            logger.warning("delete_macro command denied - insufficient permissions")
            return

        guild_id = interaction.guild.id
        guild_name = interaction.guild.name
        macros = bot.load_server_macros(guild_id, guild_name)

        if name not in macros:
            logger.info(
                f"delete_macro failed - macro '{name}' does not exist in guild {guild_name} ({guild_id})"
            )
            embed, logo_file = bot.create_embed(
                title="❌ Macro Not Found",
                description=f"WeakAuras macro '{name}' does not exist!",
                footer_text=f"Server: {guild_name}",
            )
            await send_embed_response(interaction, embed, logo_file)
            return

        del macros[name]
        bot.save_server_macros(guild_id, guild_name, macros)
        logger.info(
            f"Successfully deleted macro '{name}' from guild {guild_name} ({guild_id})"
        )

        embed, logo_file = bot.create_embed(
            title="🗑️ Macro Deleted",
            description=f"Successfully deleted macro **{name}**",
            footer_text=f"Server: {guild_name}",
        )
        await send_embed_response(interaction, embed, logo_file)

    @bot.tree.command(name="macro", description="Execute a saved WeakAuras macro")
    @app_commands.autocomplete(name=macro_name_autocomplete)
    @log_command
    async def execute_macro(interaction: discord.Interaction, name: str):
        """Execute a saved macro from this server"""
        if not interaction.guild:
            logger.warning("macro command used outside of server")
            await interaction.response.send_message(
                "This command can only be used in a server!", ephemeral=True
            )
            return

        guild_id = interaction.guild.id
        guild_name = interaction.guild.name
        macros = bot.load_server_macros(guild_id, guild_name)

        if name not in macros:
            logger.info(
                f"macro execution failed - macro '{name}' does not exist in guild {guild_name} ({guild_id})"
            )
            embed, logo_file = bot.create_embed(
                title="❌ Macro Not Found",
                description=f"WeakAuras macro '{name}' does not exist!",
                footer_text=f"Server: {guild_name}",
            )
            await send_embed_response(interaction, embed, logo_file)
            return

        macro_data = macros[name]
        message = (
            macro_data.get("message", macro_data)
            if isinstance(macro_data, dict)
            else macro_data
        )
        logger.info(
            f"Successfully executed macro '{name}' from guild {guild_name} ({guild_id})"
        )
        await interaction.response.send_message(message)
