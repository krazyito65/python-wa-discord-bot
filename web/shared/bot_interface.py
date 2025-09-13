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

import yaml
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


@dataclass
class MacroUpdateData:
    """Data structure for macro update information."""

    guild_id: int
    guild_name: str
    old_name: str
    new_name: str
    message: str
    edited_by: str
    edited_by_name: str


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

    def create_server_folder(self, guild_id: int, guild_name: str) -> Path | None:
        """Create a server folder for the given guild.

        Args:
            guild_id (int): Discord guild/server ID.
            guild_name (str): Discord guild/server name.

        Returns:
            Optional[Path]: Path to the created server folder, None if creation failed.
        """
        sanitized_name = self.sanitize_server_name(guild_name)
        folder_name = f"{sanitized_name}_{guild_id}"
        server_folder = self.data_dir / folder_name

        try:
            server_folder.mkdir(parents=True, exist_ok=True)
        except OSError:
            return None
        else:
            return server_folder

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
            # Try to create the folder if it doesn't exist
            server_folder = self.create_server_folder(guild_id, guild_name)
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

    def update_macro(self, update_data: MacroUpdateData) -> tuple[bool, str]:
        """Update an existing macro's name and/or message.

        Args:
            update_data (MacroUpdateData): Macro update information containing all required fields.

        Returns:
            tuple[bool, str]: (success, error_message). If success is True, error_message is empty.
                             If success is False, error_message contains the specific error.
        """
        macros = self.load_server_macros(update_data.guild_id, update_data.guild_name)

        if update_data.old_name not in macros:
            return False, f"Macro '{update_data.old_name}' not found"

        # Check if new name conflicts with existing macro (unless it's the same macro)
        if (
            update_data.new_name != update_data.old_name
            and update_data.new_name in macros
        ):
            return False, f"A macro named '{update_data.new_name}' already exists"

        current_macro = macros[update_data.old_name]
        now = datetime.now()

        # Update the macro data while preserving metadata
        if isinstance(current_macro, dict):
            updated_macro = current_macro.copy()
            updated_macro["message"] = update_data.message
            updated_macro["updated_at"] = now.isoformat()
            updated_macro["updated_by"] = update_data.edited_by
            updated_macro["updated_by_name"] = update_data.edited_by_name
        else:
            # Convert legacy format to modern format
            updated_macro = {
                "name": update_data.new_name,
                "message": update_data.message,
                "created_by": "",
                "created_by_name": "Unknown",
                "created_at": "",
                "updated_at": now.isoformat(),
                "updated_by": update_data.edited_by,
                "updated_by_name": update_data.edited_by_name,
            }

        # Handle name change
        if update_data.new_name != update_data.old_name:
            # Remove old entry and add new one
            del macros[update_data.old_name]
            macros[update_data.new_name] = updated_macro
        else:
            # Just update existing entry
            macros[update_data.old_name] = updated_macro

        save_success = self.save_server_macros(
            update_data.guild_id, update_data.guild_name, macros
        )

        if save_success:
            return True, ""
        return False, "Failed to save macro changes to file"

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

    def load_bot_config(self) -> dict:
        """Load bot configuration from token.yml file.
        
        Returns:
            dict: Bot configuration dictionary, or default config if file not found.
        """
        # Try multiple locations for bot configuration
        config_paths = [
            Path("~/.config/weakauras-bot/token.yml").expanduser(),
            Path("~/weakauras-bot-config/token.yml").expanduser(),
            Path(settings.BASE_DIR).parent / "discord-bot" / "settings" / "token.yml",
        ]

        for config_path in config_paths:
            if config_path.exists():
                try:
                    with open(config_path, encoding='utf-8') as f:
                        return yaml.safe_load(f) or {}
                except (yaml.YAMLError, OSError):
                    continue

        # Return default configuration if no file found
        return {
            "bot": {
                "permissions": {
                    "admin_roles": ["admin"],
                    "admin_permissions": ["administrator"]
                }
            }
        }

    def check_admin_access(self, user_roles: list[str], guild_permissions: int = 0) -> bool:
        """Check if user has admin access based on roles or Discord permissions.
        
        Args:
            user_roles: List of role names the user has in the server.
            guild_permissions: User's Discord permissions in the server (as integer).
            
        Returns:
            bool: True if user has admin access, False otherwise.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        config = self.load_bot_config()
        permissions_config = config.get("bot", {}).get("permissions", {})
        
        logger.info(f"Bot config loaded: {permissions_config}")

        # Check role names (case-insensitive)
        admin_roles = permissions_config.get("admin_roles", ["admin"])
        user_role_names = [role.lower() for role in user_roles]
        
        logger.info(f"Admin roles: {admin_roles}, User roles: {user_role_names}")

        for admin_role in admin_roles:
            if admin_role.lower() in user_role_names:
                logger.info(f"User has admin role: {admin_role}")
                return True

        # Check Discord permissions
        admin_permissions = permissions_config.get("admin_permissions", ["administrator"])
        
        logger.info(f"Admin permissions: {admin_permissions}, User guild permissions: {guild_permissions} (0x{guild_permissions:x})")

        for permission_name in admin_permissions:
            # Convert permission name to Discord permission bit
            permission_bit = self._get_permission_bit(permission_name)
            logger.info(f"Checking permission '{permission_name}' (bit: 0x{permission_bit:x})")
            if permission_bit and (guild_permissions & permission_bit) == permission_bit:
                logger.info(f"User has admin permission: {permission_name}")
                return True

        logger.info("User does not have admin access")
        return False

    def _get_permission_bit(self, permission_name: str) -> int:
        """Get Discord permission bit value for a permission name.
        
        Args:
            permission_name: Name of the Discord permission.
            
        Returns:
            int: Permission bit value, or 0 if permission not found.
        """
        permission_bits = {
            "administrator": 0x8,
            "manage_channels": 0x10,
            "manage_guild": 0x20,
            "manage_messages": 0x2000,
            "manage_roles": 0x10000000,
            "manage_webhooks": 0x20000000,
            "kick_members": 0x2,
            "ban_members": 0x4,
        }

        return permission_bits.get(permission_name.lower(), 0)


# Singleton instance for use throughout the web application
bot_interface = BotDataInterface()
