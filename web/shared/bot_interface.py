"""
Bot Interface Module for WeakAuras Web Interface

This module provides functions to interface with the Discord bot's data storage
system, allowing the web interface to read and write macro data for servers.
"""

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from django.conf import settings


@dataclass
class MacroData:
    """Data structure for macro information."""

    guild_id: int
    guild_name: str
    name: str
    message: str
    created_by: str
    created_by_name: str


class BotDataInterface:
    """Interface class for accessing Discord bot data from the web application.

    This class provides methods to interact with the bot's server-specific
    data storage, including macros and configuration files.

    Attributes:
        data_dir (Path): Path to the bot's server data directory.
    """

    def __init__(self):
        """Initialize the bot data interface with the configured data directory."""
        self.data_dir = Path(settings.BOT_DATA_DIR)

    def sanitize_server_name(self, server_name: str) -> str:
        """Sanitize server name for use as folder name.

        Args:
            server_name (str): The original server name from Discord.

        Returns:
            str: Sanitized server name safe for filesystem usage.
        """
        # Replace invalid filesystem characters with underscores
        sanitized = re.sub(r'[<>:"/\\|?*]', "_", server_name)
        # Remove multiple consecutive underscores and trailing/leading spaces
        sanitized = re.sub(r"_+", "_", sanitized.strip())
        # Ensure it's not empty and limit length
        if not sanitized:
            sanitized = "unknown_server"
        return sanitized[:100]  # Limit to 100 chars

    def get_server_folder(self, guild_id: int, _guild_name: str) -> Path | None:
        """Get the server folder path for a given guild.

        Args:
            guild_id (int): Discord guild/server ID.
            guild_name (str): Discord guild/server name.

        Returns:
            Optional[Path]: Path to the server folder if it exists, None otherwise.
        """
        # Check if any existing folder has the same guild_id suffix
        if not self.data_dir.exists():
            return None

        for folder_path in self.data_dir.iterdir():
            if folder_path.is_dir() and folder_path.name.endswith(f"_{guild_id}"):
                return folder_path

        return None

    def get_available_servers(self) -> list[dict[str, Any]]:
        """Get list of all servers that have data folders.

        Returns:
            List[Dict[str, Any]]: List of server information dictionaries containing
                guild_id, guild_name, and folder_path for each available server.
        """
        servers = []

        if not self.data_dir.exists():
            return servers

        for folder_path in self.data_dir.iterdir():
            if not folder_path.is_dir():
                continue

            # Extract guild_id from folder name (format: servername_guildid)
            folder_name = folder_path.name
            parts = folder_name.split("_")

            min_parts = 2
            if len(parts) >= min_parts:
                try:
                    guild_id = int(parts[-1])
                    # Reconstruct server name from all parts except the last (guild_id)
                    guild_name = "_".join(parts[:-1])

                    servers.append(
                        {
                            "guild_id": guild_id,
                            "guild_name": guild_name,
                            "folder_path": folder_path,
                            "folder_name": folder_name,
                        }
                    )
                except ValueError:
                    # Skip folders that don't follow the expected naming pattern
                    continue

        return servers

    def get_server_macros_file(self, guild_id: int, guild_name: str) -> Path | None:
        """Get the macros file path for a specific server.

        Args:
            guild_id (int): Discord guild/server ID.
            guild_name (str): Discord guild/server name.

        Returns:
            Optional[Path]: Path to the macros file if server folder exists, None otherwise.
        """
        server_folder = self.get_server_folder(guild_id, guild_name)
        if server_folder:
            return server_folder / f"{guild_id}_macros.json"
        return None

    def load_server_macros(self, guild_id: int, guild_name: str) -> dict[str, Any]:
        """Load macros for a specific server.

        Args:
            guild_id (int): Discord guild/server ID.
            guild_name (str): Discord guild/server name.

        Returns:
            Dict[str, Any]: Dictionary containing all macros for the server.
                Returns empty dict if no macros file exists.
        """
        macros_file = self.get_server_macros_file(guild_id, guild_name)

        if not macros_file or not macros_file.exists():
            return {}

        try:
            with open(macros_file, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return {}

    def save_server_macros(
        self, guild_id: int, guild_name: str, macros: dict[str, Any]
    ) -> bool:
        """Save macros for a specific server.

        Args:
            guild_id (int): Discord guild/server ID.
            guild_name (str): Discord guild/server name.
            macros (Dict[str, Any]): Dictionary containing all macros to save.

        Returns:
            bool: True if save was successful, False otherwise.
        """
        server_folder = self.get_server_folder(guild_id, guild_name)

        if not server_folder:
            return False

        macros_file = server_folder / f"{guild_id}_macros.json"

        try:
            with open(macros_file, "w", encoding="utf-8") as f:
                json.dump(macros, f, indent=2, ensure_ascii=False)
        except OSError:
            return False
        else:
            return True

    def add_macro(self, macro_data: MacroData) -> bool:
        """Add a new macro to the server.

        Args:
            macro_data (MacroData): Macro information containing all required fields.

        Returns:
            bool: True if macro was added successfully, False if macro already exists or save failed.
        """
        macros = self.load_server_macros(macro_data.guild_id, macro_data.guild_name)

        if macro_data.name in macros:
            return False  # Macro already exists

        macro_dict = {
            "name": macro_data.name,
            "message": macro_data.message,
            "created_by": macro_data.created_by,
            "created_by_name": macro_data.created_by_name,
            "created_at": datetime.now().isoformat(),
        }

        macros[macro_data.name] = macro_dict
        return self.save_server_macros(
            macro_data.guild_id, macro_data.guild_name, macros
        )

    def update_macro(
        self, guild_id: int, guild_name: str, name: str, message: str
    ) -> bool:
        """Update an existing macro's message.

        Args:
            guild_id (int): Discord guild/server ID.
            guild_name (str): Discord guild/server name.
            name (str): Macro name to update.
            message (str): New macro message content.

        Returns:
            bool: True if macro was updated successfully, False if macro doesn't exist or save failed.
        """
        macros = self.load_server_macros(guild_id, guild_name)

        if name not in macros:
            return False  # Macro doesn't exist

        # Update the message while preserving other metadata
        if isinstance(macros[name], dict):
            macros[name]["message"] = message
            macros[name]["updated_at"] = datetime.now().isoformat()
        else:
            # Handle legacy string-only macros
            macros[name] = message

        return self.save_server_macros(guild_id, guild_name, macros)

    def delete_macro(self, guild_id: int, guild_name: str, name: str) -> bool:
        """Delete a macro from the server.

        Args:
            guild_id (int): Discord guild/server ID.
            guild_name (str): Discord guild/server name.
            name (str): Macro name to delete.

        Returns:
            bool: True if macro was deleted successfully, False if macro doesn't exist or save failed.
        """
        macros = self.load_server_macros(guild_id, guild_name)

        if name not in macros:
            return False  # Macro doesn't exist

        del macros[name]
        return self.save_server_macros(guild_id, guild_name, macros)


# Singleton instance for use throughout the web application
bot_interface = BotDataInterface()
