import discord
from discord import app_commands

from bot.weakauras_bot import WeakAurasBot


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
    async def create_macro(interaction: discord.Interaction, name: str, message: str):
        """Create a new macro with the given name and message"""
        if not interaction.guild:
            await interaction.response.send_message(
                "This command can only be used in a server!", ephemeral=True
            )
            return

        guild_id = interaction.guild.id
        guild_name = interaction.guild.name

        # Load server-specific macros
        macros = bot.load_server_macros(guild_id, guild_name)

        if name in macros:
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
    async def list_macros(interaction: discord.Interaction):
        """List all available macros for this server"""
        if not interaction.guild:
            await interaction.response.send_message(
                "This command can only be used in a server!", ephemeral=True
            )
            return

        guild_id = interaction.guild.id
        guild_name = interaction.guild.name
        macros = bot.load_server_macros(guild_id, guild_name)

        if not macros:
            embed, logo_file = bot.create_embed(
                title="📂 No Macros Found",
                description="No WeakAuras macros available in this server.",
                footer_text=f"Server: {guild_name}",
            )
            await send_embed_response(interaction, embed, logo_file)
            return

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
    async def delete_macro(interaction: discord.Interaction, name: str):
        """Delete a macro from this server (requires admin role)"""
        if not interaction.guild:
            await interaction.response.send_message(
                "This command can only be used in a server!", ephemeral=True
            )
            return

        # Check if user has admin access (ensure user is a member)
        if not isinstance(interaction.user, discord.Member) or not bot.has_admin_access(
            interaction.user
        ):
            permissions_config = bot.config.get("bot", {}).get("permissions", {})
            admin_roles = permissions_config.get("admin_roles", ["admin"])
            admin_permissions = permissions_config.get("admin_permissions", [])

            roles_text = ", ".join(f"'{role}'" for role in admin_roles)
            perms_text = ", ".join(admin_permissions)

            description = (
                f"You need either:\n• Role: {roles_text}\n• Permission: {perms_text}"
            )

            embed, logo_file = bot.create_embed(
                title="❌ Permission Denied",
                description=description,
                footer_text=f"Server: {interaction.guild.name}",
            )
            await send_embed_response(interaction, embed, logo_file)
            return

        guild_id = interaction.guild.id
        guild_name = interaction.guild.name
        macros = bot.load_server_macros(guild_id, guild_name)

        if name not in macros:
            embed, logo_file = bot.create_embed(
                title="❌ Macro Not Found",
                description=f"WeakAuras macro '{name}' does not exist!",
                footer_text=f"Server: {guild_name}",
            )
            await send_embed_response(interaction, embed, logo_file)
            return

        del macros[name]
        bot.save_server_macros(guild_id, guild_name, macros)

        embed, logo_file = bot.create_embed(
            title="🗑️ Macro Deleted",
            description=f"Successfully deleted macro **{name}**",
            footer_text=f"Server: {guild_name}",
        )
        await send_embed_response(interaction, embed, logo_file)

    @bot.tree.command(name="macro", description="Execute a saved WeakAuras macro")
    @app_commands.autocomplete(name=macro_name_autocomplete)
    async def execute_macro(interaction: discord.Interaction, name: str):
        """Execute a saved macro from this server"""
        if not interaction.guild:
            await interaction.response.send_message(
                "This command can only be used in a server!", ephemeral=True
            )
            return

        guild_id = interaction.guild.id
        guild_name = interaction.guild.name
        macros = bot.load_server_macros(guild_id, guild_name)

        if name not in macros:
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
        await interaction.response.send_message(message)
