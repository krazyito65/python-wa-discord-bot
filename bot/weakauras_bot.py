"""
WeakAuras Discord Bot - Core Bot Implementation

This module contains the main WeakAurasBot class which extends discord.py's
commands.Bot with WeakAuras-specific functionality including server-specific
macro storage, configuration management, and administrative features.

The bot provides:
- Server-isolated macro storage and retrieval
- Role-based permission system
- Automatic folder management with guild ID matching
- Branded embed creation for consistent UI
- Server configuration management

Example:
    Creating and running the bot::

        config = {"discord": {"tokens": {"dev": "your_token"}}}
        bot = WeakAurasBot(config)
        bot.run(config["discord"]["tokens"]["dev"])

Attributes:
    Module-level constants and imports for Discord bot functionality.
"""

import json
import re
from pathlib import Path
from typing import Any

import discord
from discord.ext import commands


class WeakAurasBot(commands.Bot):
    """WeakAuras Discord Bot with server-specific macro storage and management.

    This bot extends discord.py's commands.Bot to provide WeakAuras-specific
    functionality including macro storage, server configuration, and administrative
    features. Each Discord server gets its own isolated data storage.

    Attributes:
        config (dict[str, Any]): Bot configuration dictionary.
        data_dir (Path): Directory path for server data storage.

    Example:
        >>> config = {"storage": {"data_directory": "server_data"}}
        >>> bot = WeakAurasBot(config)
        >>> # Bot is now ready for command registration and startup
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize the WeakAuras bot with configuration.

        Args:
            config (dict[str, Any]): Configuration dictionary containing bot
                settings, storage paths, and other options.

        Example:
            >>> config = {
            ...     "storage": {"data_directory": "server_data"},
            ...     "bot": {"brand_color": 0x9F4AF3}
            ... }
            >>> bot = WeakAurasBot(config)
        """
        intents = discord.Intents.default()
        intents.message_content = True

        # Using "!" as command_prefix but we only use slash commands
        super().__init__(command_prefix="!", intents=intents)

        self.config = config
        self.data_dir = Path(
            config.get("storage", {}).get("data_directory", "server_data")
        )

        # Ensure data directory exists
        self.data_dir.mkdir(exist_ok=True)

    def sanitize_server_name(self, server_name: str) -> str:
        """Sanitize server name for use as folder name"""
        # Replace invalid filesystem characters with underscores
        sanitized = re.sub(r'[<>:"/\\|?*]', "_", server_name)
        # Remove multiple consecutive underscores and trailing/leading spaces
        sanitized = re.sub(r"_+", "_", sanitized.strip())
        # Ensure it's not empty and limit length
        if not sanitized:
            sanitized = "unknown_server"
        return sanitized[:100]  # Limit to 100 chars

    def get_server_folder(self, guild_id: int, guild_name: str) -> Path:
        """Get or create the server folder path, checking for existing folders by guild ID"""
        sanitized_name = self.sanitize_server_name(guild_name)
        desired_folder_name = f"{sanitized_name}_{guild_id}"
        desired_folder_path = self.data_dir / desired_folder_name

        # Check if any existing folder has the same guild_id suffix
        existing_folder = None
        for folder_path in self.data_dir.iterdir():
            if folder_path.is_dir() and folder_path.name.endswith(f"_{guild_id}"):
                existing_folder = folder_path
                break

        # If we found an existing folder with the same guild_id
        if existing_folder:
            # If the name matches what we want, use it
            if existing_folder.name == desired_folder_name:
                return existing_folder
            # If the name is different, rename the folder to match current server name
            try:
                existing_folder.rename(desired_folder_path)
            except OSError:
                # If rename fails, use existing folder
                return existing_folder
            else:
                return desired_folder_path

        # No existing folder found, create new one
        desired_folder_path.mkdir(exist_ok=True)
        return desired_folder_path

    def get_server_macros_file(self, guild_id: int, guild_name: str) -> Path:
        """Get the macros file path for a specific server"""
        server_folder = self.get_server_folder(guild_id, guild_name)
        return server_folder / f"{guild_id}_macros.json"

    def load_server_macros(self, guild_id: int, guild_name: str) -> dict[str, Any]:
        """Load macros for a specific server"""
        macros_file = self.get_server_macros_file(guild_id, guild_name)
        try:
            with open(macros_file) as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_server_macros(
        self, guild_id: int, guild_name: str, macros: dict[str, Any]
    ) -> None:
        """Save macros for a specific server"""
        macros_file = self.get_server_macros_file(guild_id, guild_name)
        with open(macros_file, "w") as f:
            json.dump(macros, f, indent=2)

    def get_server_config_file(self, guild_id: int, guild_name: str) -> Path:
        """Get the configuration file path for a specific server"""
        server_folder = self.get_server_folder(guild_id, guild_name)
        return server_folder / f"{guild_id}_config.json"

    def load_server_config(self, guild_id: int, guild_name: str) -> dict[str, Any]:
        """Load configuration for a specific server"""
        config_file = self.get_server_config_file(guild_id, guild_name)
        try:
            with open(config_file) as f:
                return json.load(f)
        except FileNotFoundError:
            # Return default server configuration
            return {
                "events": {
                    "temperature": {
                        "enabled": True,
                    }
                }
            }

    def save_server_config(
        self, guild_id: int, guild_name: str, config: dict[str, Any]
    ) -> None:
        """Save configuration for a specific server"""
        config_file = self.get_server_config_file(guild_id, guild_name)
        with open(config_file, "w") as f:
            json.dump(config, f, indent=2)

    def has_admin_access(self, member: discord.Member) -> bool:
        """Check if member has admin access via role names or Discord permissions"""
        permissions_config = self.config.get("bot", {}).get("permissions", {})

        # Check role names (case-insensitive)
        admin_roles = permissions_config.get("admin_roles", ["admin"])
        member_role_names = [role.name.lower() for role in member.roles]

        for admin_role in admin_roles:
            if admin_role.lower() in member_role_names:
                return True

        # Check Discord permissions
        admin_permissions = permissions_config.get("admin_permissions", [])
        member_permissions = member.guild_permissions

        for permission_name in admin_permissions:
            if hasattr(member_permissions, permission_name) and getattr(
                member_permissions, permission_name
            ):
                return True

        return False

    def create_embed(
        self,
        title: str | None = None,
        description: str | None = None,
        color: int | None = None,
        footer_text: str | None = None,
    ) -> tuple[discord.Embed, discord.File | None]:
        """Create a branded WeakAuras embed with logo attachment"""
        # Use configured color or default WeakAuras purple
        embed_color = color or self.config.get("bot", {}).get("brand_color", 0x9F4AF3)

        embed = discord.Embed(
            title=title,
            description=description,
            color=embed_color,
        )

        # Handle logo file attachment
        logo_file = None
        logo_path = self.config.get("bot", {}).get("logo_path")
        if logo_path and Path(logo_path).exists():
            logo_file = discord.File(logo_path, filename="weakauras_logo.png")
            thumbnail_url = "attachment://weakauras_logo.png"
            embed.set_thumbnail(url=thumbnail_url)

            # Add footer with WeakAuras branding
            if footer_text:
                embed.set_footer(
                    text=f"{footer_text} • WeakAuras Bot",
                    icon_url=thumbnail_url,
                )
            else:
                embed.set_footer(
                    text="WeakAuras Bot",
                    icon_url=thumbnail_url,
                )
        # Fallback to text-only footer if no logo
        elif footer_text:
            embed.set_footer(text=f"{footer_text} • WeakAuras Bot")
        else:
            embed.set_footer(text="WeakAuras Bot")

        return embed, logo_file

    async def on_ready(self):
        print(f"{self.user} (WeakAuras Bot) has connected to Discord!")

        # Print registered commands before sync
        registered_commands = [cmd.name for cmd in self.tree.get_commands()]
        print(f"Commands registered locally: {', '.join(registered_commands)}")

        await self.sync_commands()

        # Ensure server folders exist for all guilds
        for guild in self.guilds:
            self.get_server_folder(guild.id, guild.name)

    async def sync_commands(self):
        """Sync slash commands with Discord"""
        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} command(s)")
            if synced:
                command_names = [cmd.name for cmd in synced]
                print(f"Available commands: {', '.join(command_names)}")
        except Exception as e:
            print(f"Failed to sync commands: {e}")
