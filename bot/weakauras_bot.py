import json
import re
from pathlib import Path
from typing import Any

import discord
from discord.ext import commands


class WeakAurasBot(commands.Bot):
    def __init__(self, config: dict[str, Any]):
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
        """Get or create the server folder path"""
        sanitized_name = self.sanitize_server_name(guild_name)
        folder_name = f"{sanitized_name}_{guild_id}"
        server_folder = self.data_dir / folder_name

        # Create folder if it doesn't exist
        server_folder.mkdir(exist_ok=True)

        return server_folder

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

    def update_server_folder_name(
        self, guild_id: int, old_name: str, new_name: str
    ) -> None:
        """Update server folder name if server name changed"""
        if old_name == new_name:
            return

        old_sanitized = self.sanitize_server_name(old_name)
        new_sanitized = self.sanitize_server_name(new_name)

        if old_sanitized == new_sanitized:
            return  # No change needed

        old_folder = self.data_dir / f"{old_sanitized}_{guild_id}"
        new_folder = self.data_dir / f"{new_sanitized}_{guild_id}"

        # Rename folder if it exists and new name doesn't exist
        if old_folder.exists() and not new_folder.exists():
            old_folder.rename(new_folder)

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
