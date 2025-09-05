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


def setup_ping_commands(bot: WeakAurasBot):
    """Setup ping-related commands"""

    @bot.tree.command(name="wa_ping", description="Test WeakAuras bot responsiveness")
    async def ping(interaction: discord.Interaction):
        """Simple ping command to test bot responsiveness"""
        latency = round(bot.latency * 1000)  # Convert to milliseconds

        # Build description with bot info and GitHub link
        description = (
            f"🏓 **Pong!** Bot latency: **{latency}ms**\n\n"
            f"📊 **Bot Information:**\n"
            f"• Servers: **{len(bot.guilds)}**\n"
            f"• Users: **{sum(guild.member_count or 0 for guild in bot.guilds)}**\n"
            f"• Commands: **{len(bot.tree.get_commands())}**\n\n"
            f"🔗 **Links:**\n"
            f"• [GitHub Repository](https://github.com/krazyito/python-wa-discord-bot)\n"
            f"• [WeakAuras Website](https://weakauras.wtf)"
        )

        embed, logo_file = bot.create_embed(
            title="WeakAuras Bot Status",
            description=description,
            footer_text="WeakAuras Bot is online and ready",
        )
        await send_embed_response(interaction, embed, logo_file)
