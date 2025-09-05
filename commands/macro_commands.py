import discord

from bot.weakauras_bot import WeakAurasBot


def setup_macro_commands(bot: WeakAurasBot):
    """Setup all macro-related slash commands"""

    @bot.tree.command(
        name="create_macro", description="Create a new WeakAuras macro command"
    )
    async def create_macro(interaction: discord.Interaction, name: str, message: str):
        """Create a new macro with the given name and message"""
        guild_id = interaction.guild.id
        guild_name = interaction.guild.name

        # Update server name in mapping
        bot.update_server_name(guild_id, guild_name)

        # Load server-specific macros
        macros = bot.load_server_macros(guild_id)

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
            "created_at": interaction.created_at.isoformat(),
        }

        macros[name] = macro_data
        bot.save_server_macros(guild_id, macros)
        await interaction.response.send_message(
            f"Created WeakAuras macro '{name}' successfully!", ephemeral=True
        )

    @bot.tree.command(
        name="list_macros", description="List all available WeakAuras macros"
    )
    async def list_macros(interaction: discord.Interaction):
        """List all available macros for this server"""
        guild_id = interaction.guild.id
        macros = bot.load_server_macros(guild_id)

        if not macros:
            await interaction.response.send_message(
                "No WeakAuras macros available in this server.", ephemeral=True
            )
            return

        macro_list = "\n".join([f"• {name}" for name in macros])
        embed = discord.Embed(
            title="WeakAuras Macros", description=macro_list, color=0x9F4AF3
        )
        embed.set_footer(text=f"Server: {interaction.guild.name}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.tree.command(
        name="delete_macro",
        description="Delete an existing WeakAuras macro (Admin only)",
    )
    async def delete_macro(interaction: discord.Interaction, name: str):
        """Delete a macro from this server (requires admin role)"""
        # Check if user has admin role
        if not bot.has_admin_role(interaction.user):
            admin_role_name = bot.config.get("bot", {}).get("admin_role", "admin")
            await interaction.response.send_message(
                f"❌ You need the '{admin_role_name}' role to delete macros!",
                ephemeral=True,
            )
            return

        guild_id = interaction.guild.id
        macros = bot.load_server_macros(guild_id)

        if name not in macros:
            await interaction.response.send_message(
                f"WeakAuras macro '{name}' does not exist!", ephemeral=True
            )
            return

        del macros[name]
        bot.save_server_macros(guild_id, macros)
        await interaction.response.send_message(
            f"Deleted WeakAuras macro '{name}' successfully!", ephemeral=True
        )

    @bot.tree.command(name="macro", description="Execute a saved WeakAuras macro")
    async def execute_macro(interaction: discord.Interaction, name: str):
        """Execute a saved macro from this server"""
        guild_id = interaction.guild.id
        macros = bot.load_server_macros(guild_id)

        if name not in macros:
            await interaction.response.send_message(
                f"WeakAuras macro '{name}' does not exist!", ephemeral=True
            )
            return

        macro_data = macros[name]
        message = (
            macro_data.get("message", macro_data)
            if isinstance(macro_data, dict)
            else macro_data
        )
        await interaction.response.send_message(message)
