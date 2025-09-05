import discord

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


def setup_config_commands(bot: WeakAurasBot):
    """Setup configuration-related commands"""

    @bot.tree.command(
        name="config", description="Configure WeakAuras bot settings (Admin only)"
    )
    async def config_command(interaction: discord.Interaction):
        """Main configuration command"""
        if not interaction.guild:
            await interaction.response.send_message(
                "This command can only be used in a server!", ephemeral=True
            )
            return

        # Check if user has admin access
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

        # Load current server configuration
        guild_id = interaction.guild.id
        guild_name = interaction.guild.name
        server_config = bot.load_server_config(guild_id, guild_name)

        # Create configuration view with buttons
        view = ConfigView(bot, guild_id, guild_name, server_config)

        embed, logo_file = bot.create_embed(
            title="⚙️ WeakAuras Bot Configuration",
            description=view.get_config_status(server_config),
            footer_text=f"Server: {guild_name}",
        )

        if logo_file:
            await interaction.response.send_message(
                embed=embed, file=logo_file, view=view, ephemeral=True
            )
        else:
            await interaction.response.send_message(
                embed=embed, view=view, ephemeral=True
            )


class ConfigView(discord.ui.View):
    def __init__(self, bot: WeakAurasBot, guild_id: int, guild_name: str, config: dict):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        self.guild_name = guild_name
        self.config = config

    def get_config_status(self, config: dict) -> str:
        """Generate configuration status text"""
        temp_config = config.get("events", {}).get("temperature", {})
        temp_enabled = temp_config.get("enabled", True)

        status_lines = [
            "**Event Configuration:**",
            f"🌡️ Temperature Conversion: {'✅ Enabled' if temp_enabled else '❌ Disabled'}",
            "",
            "Use the button below to toggle settings:",
        ]

        return "\n".join(status_lines)

    @discord.ui.button(
        label="Toggle Temperature Event", style=discord.ButtonStyle.primary, emoji="🌡️"
    )
    async def toggle_temperature(
        self, interaction: discord.Interaction, _button: discord.ui.Button
    ):
        """Toggle temperature conversion event"""
        events_config = self.config.setdefault("events", {})
        temp_config = events_config.setdefault("temperature", {"enabled": True})

        temp_config["enabled"] = not temp_config.get("enabled", True)
        self.bot.save_server_config(self.guild_id, self.guild_name, self.config)

        # Update embed
        embed, _logo_file = self.bot.create_embed(
            title="⚙️ WeakAuras Bot Configuration",
            description=self.get_config_status(self.config),
            footer_text=f"Server: {self.guild_name}",
        )

        await interaction.response.edit_message(embed=embed, view=self)
