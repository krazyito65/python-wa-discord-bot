import json
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
        self.servers_mapping_file = self.data_dir / config.get("storage", {}).get(
            "servers_mapping_file", "servers.json"
        )
        self.servers_mapping: dict[str, str] = self.load_servers_mapping()

        # Ensure data directory exists
        self.data_dir.mkdir(exist_ok=True)

    def load_servers_mapping(self) -> dict[str, str]:
        """Load server ID to name mapping"""
        try:
            with open(self.servers_mapping_file) as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_servers_mapping(self) -> None:
        """Save server ID to name mapping"""
        with open(self.servers_mapping_file, "w") as f:
            json.dump(self.servers_mapping, f, indent=2)

    def get_server_macros_file(self, guild_id: int) -> Path:
        """Get the macros file path for a specific server"""
        return self.data_dir / f"{guild_id}_macros.json"

    def load_server_macros(self, guild_id: int) -> dict[str, Any]:
        """Load macros for a specific server"""
        macros_file = self.get_server_macros_file(guild_id)
        try:
            with open(macros_file) as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_server_macros(self, guild_id: int, macros: dict[str, Any]) -> None:
        """Save macros for a specific server"""
        macros_file = self.get_server_macros_file(guild_id)
        with open(macros_file, "w") as f:
            json.dump(macros, f, indent=2)

    def update_server_name(self, guild_id: int, guild_name: str) -> None:
        """Update server name in mapping if changed"""
        if (
            str(guild_id) not in self.servers_mapping
            or self.servers_mapping[str(guild_id)] != guild_name
        ):
            self.servers_mapping[str(guild_id)] = guild_name
            self.save_servers_mapping()

    def has_admin_role(self, member: discord.Member) -> bool:
        """Check if member has the configured admin role"""
        admin_role_name = self.config.get("bot", {}).get("admin_role", "admin").lower()
        return any(role.name.lower() == admin_role_name for role in member.roles)

    async def on_ready(self):
        print(f"{self.user} (WeakAuras Bot) has connected to Discord!")
        await self.sync_commands()

        # Update server names for all guilds
        for guild in self.guilds:
            self.update_server_name(guild.id, guild.name)

    async def sync_commands(self):
        """Sync slash commands with Discord"""
        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} command(s)")
        except Exception as e:
            print(f"Failed to sync commands: {e}")
