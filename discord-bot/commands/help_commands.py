"""
Help command for displaying available bot commands and their usage.

This module provides a comprehensive help system that categorizes commands
and provides detailed usage information for users.
"""

import discord
from bot.weakauras_bot import WeakAurasBot
from discord import app_commands
from utils.logging import get_logger, log_command

logger = get_logger(__name__)

# Command categories with their descriptions
COMMAND_CATEGORIES = {
    "macros": {
        "title": "📝 Macro Commands",
        "description": "Create and manage server-specific macros",
        "commands": [
            {
                "name": "/create_macro",
                "description": "Create a new text macro",
                "usage": "/create_macro name:welcome message:Welcome to our server!",
                "example": "Creates a macro called 'welcome' with the welcome message",
            },
            {
                "name": "/create_embed_macro",
                "description": "Create a rich embed macro with multiple fields",
                "usage": "/create_embed_macro name:rules",
                "example": "Opens a form to create a rich embed macro for server rules",
            },
            {
                "name": "/macro",
                "description": "Execute an existing macro",
                "usage": "/macro name:welcome",
                "example": "Sends the welcome macro message",
            },
            {
                "name": "/list_macros",
                "description": "Show all available macros in this server",
                "usage": "/list_macros",
                "example": "Displays a list of all macros you can use",
            },
            {
                "name": "/edit_macro",
                "description": "Edit an existing text macro (admin only)",
                "usage": "/edit_macro name:welcome",
                "example": "Opens editor to modify the welcome macro",
            },
            {
                "name": "/edit_embed_macro",
                "description": "Edit an existing embed macro (admin only)",
                "usage": "/edit_embed_macro name:rules",
                "example": "Opens form to edit the rules embed macro",
            },
            {
                "name": "/delete_macro",
                "description": "Delete a macro (admin only)",
                "usage": "/delete_macro name:old_macro",
                "example": "Permanently removes the old_macro",
            },
        ],
    },
    "roles": {
        "title": "🎭 Role Commands",
        "description": "Manage your roles and colors",
        "commands": [
            {
                "name": "/role",
                "description": "Apply a color role using hex color code OR assign an available server role",
                "usage": "/role hex_color:#ff0000 OR /role role_id:Member",
                "example": "Gives you a red color role or assigns the Member role",
            },
            {
                "name": "/remove_role",
                "description": "Remove your current color role OR unassign a server role",
                "usage": "/remove_role OR /remove_role role_id:Member",
                "example": "Removes color roles or removes the Member role from yourself",
            },
            {
                "name": "/list_roles",
                "description": "Show all available assignable roles",
                "usage": "/list_roles",
                "example": "Displays roles you can assign to yourself",
            },
        ],
    },
    "utility": {
        "title": "🛠️ Utility Commands",
        "description": "General bot utilities and information",
        "commands": [
            {
                "name": "/ping",
                "description": "Check bot responsiveness and latency",
                "usage": "/ping",
                "example": "Shows bot ping and response time",
            },
            {
                "name": "/help",
                "description": "Display this help message",
                "usage": "/help [category:macros]",
                "example": "Shows all commands or commands in a specific category",
            },
        ],
    },
    "stats": {
        "title": "📊 Statistics Commands",
        "description": "Server and user statistics (admin only)",
        "commands": [
            {
                "name": "/collect_stats",
                "description": "Collect user message statistics (admin only)",
                "usage": "/collect_stats",
                "example": "Starts collecting message stats for the server",
            }
        ],
    },
    "config": {
        "title": "⚙️ Configuration Commands",
        "description": "Bot configuration and settings (admin only)",
        "commands": [
            {
                "name": "/config",
                "description": "Show bot configuration for this server (admin only)",
                "usage": "/config",
                "example": "Displays current bot settings",
            }
        ],
    },
}

# Available categories for autocomplete
CATEGORY_CHOICES = [
    app_commands.Choice(name="📝 Macros", value="macros"),
    app_commands.Choice(name="🎭 Roles", value="roles"),
    app_commands.Choice(name="🛠️ Utility", value="utility"),
    app_commands.Choice(name="📊 Statistics", value="stats"),
    app_commands.Choice(name="⚙️ Configuration", value="config"),
    app_commands.Choice(name="🌟 All Commands", value="all"),
]


def create_help_embed(
    category: str = "all", guild_name: str = "Server"
) -> discord.Embed:
    """
    Create a help embed for the specified category.

    Args:
        category: Command category to show ("all" for all categories)
        guild_name: Name of the Discord server

    Returns:
        discord.Embed: Formatted help embed
    """
    if category == "all":
        # Show overview of all categories
        embed = discord.Embed(
            title="🤖 WeakAuras Bot Commands",
            description=f"Available commands in **{guild_name}**\n\nUse `/help category:<category>` for detailed information about specific command groups.",
            color=discord.Color.blue(),
        )

        for cat_data in COMMAND_CATEGORIES.values():
            command_count = len(cat_data["commands"])
            embed.add_field(
                name=cat_data["title"],
                value=f"{cat_data['description']}\n`{command_count} commands`",
                inline=True,
            )

        embed.set_footer(
            text="💡 Use autocomplete to explore command categories • Bot made for WeakAuras community"
        )

    else:
        # Show specific category
        if category not in COMMAND_CATEGORIES:
            # Fallback to all if invalid category
            return create_help_embed("all", guild_name)

        cat_data = COMMAND_CATEGORIES[category]
        embed = discord.Embed(
            title=cat_data["title"],
            description=cat_data["description"],
            color=discord.Color.green(),
        )

        for cmd in cat_data["commands"]:
            field_value = f"**Usage:** `{cmd['usage']}`\n**Example:** {cmd['example']}"
            embed.add_field(
                name=f"`{cmd['name']}`",
                value=f"{cmd['description']}\n{field_value}",
                inline=False,
            )

        embed.set_footer(
            text=f"Use /help to see all command categories • {len(cat_data['commands'])} commands in this category"
        )

    return embed


def setup_help_commands(bot: WeakAurasBot):
    """Set up help commands for the bot."""

    @bot.tree.command(
        name="help", description="Show available bot commands and usage information"
    )
    @app_commands.describe(
        category="Specific command category to show (leave blank for overview)"
    )
    @app_commands.choices(category=CATEGORY_CHOICES)
    @log_command
    async def help_command(
        interaction: discord.Interaction, category: app_commands.Choice[str] = None
    ):
        """Display help information about bot commands."""

        # Determine category to show
        category_value = "all"
        if category:
            category_value = category.value

        # Get guild name for embed
        guild_name = interaction.guild.name if interaction.guild else "Direct Message"

        # Create and send help embed
        help_embed = create_help_embed(category_value, guild_name)

        await interaction.response.send_message(embed=help_embed, ephemeral=True)

        logger.info(
            f"Help command used by {interaction.user.name} in {guild_name} - Category: {category_value}"
        )


def get_command_info(command_name: str) -> dict | None:
    """
    Get detailed information about a specific command.

    Args:
        command_name: Name of the command to get info for

    Returns:
        dict: Command information or None if not found
    """
    for category_data in COMMAND_CATEGORIES.values():
        for cmd in category_data["commands"]:
            if cmd["name"] == command_name or cmd["name"] == f"/{command_name}":
                return cmd
    return None


def get_total_command_count() -> int:
    """Get the total number of commands available."""
    total = 0
    for category_data in COMMAND_CATEGORIES.values():
        total += len(category_data["commands"])
    return total
