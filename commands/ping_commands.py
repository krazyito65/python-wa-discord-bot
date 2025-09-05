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

    @bot.tree.command(name="ping", description="Test bot responsiveness")
    async def ping(interaction: discord.Interaction):
        """Simple ping command to test bot responsiveness"""
        latency = round(bot.latency * 1000)  # Convert to milliseconds

        embed, logo_file = bot.create_embed(
            title="🏓 Pong!",
            description=f"Bot latency: **{latency}ms**",
            footer_text="WeakAuras Bot is online",
        )
        await send_embed_response(interaction, embed, logo_file)
