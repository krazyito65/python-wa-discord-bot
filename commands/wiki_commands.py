import urllib.parse

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


def setup_wiki_commands(bot: WeakAurasBot):
    """Setup all wiki-related slash commands"""

    @bot.tree.command(
        name="wiki", description="Search the Warcraft Wiki for information"
    )
    async def wiki_search(interaction: discord.Interaction, query: str):
        """Search warcraft.wiki.gg for the given query"""
        # URL encode the search query
        encoded_query = urllib.parse.quote_plus(query)
        search_url = (
            f"https://warcraft.wiki.gg/wiki/Special:Search?search={encoded_query}"
        )

        # Create branded embed with search link
        embed, logo_file = bot.create_embed(
            title="🔍 Warcraft Wiki Search",
            description=f"**Search Query:** {query}\n\n[Click here to view search results]({search_url})",
            footer_text="Powered by warcraft.wiki.gg",
        )
        await send_embed_response(interaction, embed, logo_file, ephemeral=False)
