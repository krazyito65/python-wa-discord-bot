import discord
from bot.weakauras_bot import WeakAurasBot
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


def setup_ping_commands(bot: WeakAurasBot):
    """Setup ping-related slash commands for the WeakAuras bot.

    Registers the wa_ping command which provides bot status information
    including latency, server details, and helpful links.

    Args:
        bot (WeakAurasBot): The WeakAuras bot instance to register
            commands with.

    Note:
        This function should be called during bot initialization to
        register all ping-related commands with the bot's command tree.
    """

    @bot.tree.command(name="wa_ping", description="Test WeakAuras bot responsiveness")
    @log_command
    async def ping(interaction: discord.Interaction):
        """Test WeakAuras bot responsiveness with server information.

        Responds with bot latency, server information, available commands count,
        and helpful links to GitHub repository and WeakAuras website.

        Args:
            interaction (discord.Interaction): The Discord interaction object
                containing user and guild information.

        Note:
            This command provides essential bot status information and
            is useful for testing if the bot is responsive and properly
            connected to Discord.
        """
        latency = round(bot.latency * 1000)  # Convert to milliseconds

        # Get current server information
        guild = interaction.guild
        member_count = guild.member_count or 0 if guild else 0
        server_name = guild.name if guild else "Unknown Server"

        logger.info(
            f"wa_ping response: latency={latency}ms, server={server_name}, members={member_count}"
        )

        # Build description with bot info and GitHub link
        description = (
            f"🏓 **Pong!** Bot latency: **{latency}ms**\n\n"
            f"📊 **Server Information:**\n"
            f"• Server: **{server_name}**\n"
            f"• Members: **{member_count:,}**\n"
            f"• Available Commands: **{len(bot.tree.get_commands())}**\n\n"
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
