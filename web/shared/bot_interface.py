"""
Bot Interface Module for WeakAuras Web Interface

This module provides functions to interface with the Discord bot's data storage
system, allowing the web interface to read and write macro data for servers.
"""

import json
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from django.conf import settings

logger = logging.getLogger(__name__)


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
class EmbedMacroData:
    """Data structure for embed macro information."""

    guild_id: int
    guild_name: str
    name: str
    embed_data: dict[str, Any]
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


@dataclass
class EmbedMacroUpdateData:
    """Data structure for embed macro update information."""

    guild_id: int
    guild_name: str
    old_name: str
    new_name: str
    embed_data: dict[str, Any]
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
        return self._find_existing_server_folder(guild_id)

    def _find_existing_server_folder(self, guild_id: int) -> Path | None:
        """Find existing server folder with the same guild ID but potentially different name.

        Args:
            guild_id (int): Discord guild/server ID to search for.

        Returns:
            Optional[Path]: Path to existing folder, None if not found.
        """
        if not self.data_dir.exists():
            return None

        # Search for directories ending with the guild_id
        guild_id_suffix = f"_{guild_id}"
        matching_folders = [
            folder_path
            for folder_path in self.data_dir.iterdir()
            if folder_path.is_dir() and folder_path.name.endswith(guild_id_suffix)
        ]

        if not matching_folders:
            return None

        # If multiple folders exist for same guild_id, consolidate them
        if len(matching_folders) > 1:
            logger.warning(
                f"Found {len(matching_folders)} directories for guild_id {guild_id}. Consolidating..."
            )
            self._consolidate_duplicate_folders(matching_folders, guild_id)

            # Return the remaining folder after consolidation
            remaining_folders = [f for f in matching_folders if f.exists()]
            return remaining_folders[0] if remaining_folders else None

        return matching_folders[0]

    def _consolidate_duplicate_folders(
        self, folders: list[Path], guild_id: int
    ) -> None:
        """Consolidate multiple folders for the same guild_id into one.

        Args:
            folders (list[Path]): List of folder paths to consolidate.
            guild_id (int): Discord guild/server ID.
        """
        if len(folders) <= 1:
            return

        # Find the folder with the most recent modification time (likely has the latest data)
        primary_folder = max(folders, key=lambda f: f.stat().st_mtime)
        other_folders = [f for f in folders if f != primary_folder]

        logger.info(
            f"Consolidating {len(folders)} folders for guild_id {guild_id}. Primary: {primary_folder.name}"
        )

        # Merge data from other folders into the primary folder
        for folder in other_folders:
            macro_file = folder / f"{guild_id}_macros.json"
            config_file = folder / f"{guild_id}_config.json"

            # Only merge if the other folder has newer or additional data
            if macro_file.exists():
                primary_macro_file = primary_folder / f"{guild_id}_macros.json"
                if not primary_macro_file.exists():
                    # Primary has no macros, copy from other
                    logger.info(
                        f"Copying macros from {folder.name} to {primary_folder.name}"
                    )
                    macro_file.rename(primary_macro_file)
                else:
                    # Both have macros, merge them (primary takes precedence)
                    logger.info(
                        f"Both folders have macros. Keeping primary folder's data: {primary_folder.name}"
                    )
                    # Remove the duplicate macros file
                    macro_file.unlink()

            if config_file.exists():
                primary_config_file = primary_folder / f"{guild_id}_config.json"
                if not primary_config_file.exists():
                    logger.info(
                        f"Copying config from {folder.name} to {primary_folder.name}"
                    )
                    config_file.rename(primary_config_file)
                else:
                    # Remove duplicate config file
                    config_file.unlink()

            # Remove any remaining files in the folder
            for file_path in folder.iterdir():
                if file_path.is_file():
                    logger.info(f"Removing remaining file: {file_path.name}")
                    file_path.unlink()

            # Remove the now-empty folder
            try:
                logger.info(f"Removing duplicate folder: {folder.name}")
                folder.rmdir()
            except OSError:
                logger.exception(f"Failed to remove duplicate folder {folder.name}")

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

        # Check if folder already exists with correct name
        if server_folder.exists():
            return server_folder

        # Check for existing directories with same guild_id but different name
        existing_folder = self._find_existing_server_folder(guild_id)
        if existing_folder:
            # Only migrate if the names are actually different
            if existing_folder.name != folder_name:
                try:
                    # Migrate old folder to new name
                    logger.info(
                        f"Migrating server folder from '{existing_folder.name}' to '{folder_name}'"
                    )
                    existing_folder.rename(server_folder)
                    logger.info(
                        f"Successfully migrated server folder to '{folder_name}'"
                    )
                    return server_folder
                except OSError:
                    logger.exception("Failed to migrate server folder")
                    # Fall through to create new folder
            else:
                # Names are the same, just return the existing folder
                return existing_folder

        # Create new folder
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
            "created_at": datetime.now(UTC).isoformat(),
        }

        macros[macro_data.name] = macro_dict
        return self.save_server_macros(
            macro_data.guild_id, macro_data.guild_name, macros
        )

    def add_embed_macro(self, macro_data: EmbedMacroData) -> bool:
        """Add a new embed macro to the server.

        Args:
            macro_data (EmbedMacroData): Embed macro information containing all required fields.

        Returns:
            bool: True if macro was added successfully, False if macro already exists or save failed.
        """
        macros = self.load_server_macros(macro_data.guild_id, macro_data.guild_name)

        if macro_data.name in macros:
            return False  # Macro already exists

        macro_dict = {
            "name": macro_data.name,
            "type": "embed",
            "embed_data": macro_data.embed_data,
            "created_by": macro_data.created_by,
            "created_by_name": macro_data.created_by_name,
            "created_at": datetime.now(UTC).isoformat(),
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
        now = datetime.now(UTC)

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

    def update_embed_macro(self, update_data: EmbedMacroUpdateData) -> tuple[bool, str]:
        """Update an existing embed macro's name and/or embed data.

        Args:
            update_data (EmbedMacroUpdateData): Embed macro update information containing all required fields.

        Returns:
            tuple[bool, str]: (success, error_message). If success is True, error_message is empty.
                             If success is False, error_message contains the specific error.
        """
        macros = self.load_server_macros(update_data.guild_id, update_data.guild_name)

        if update_data.old_name not in macros:
            return False, f"Macro '{update_data.old_name}' not found"

        current_macro = macros[update_data.old_name]

        # Check if this is an embed macro
        if not (
            isinstance(current_macro, dict) and current_macro.get("type") == "embed"
        ):
            return False, f"Macro '{update_data.old_name}' is not an embed macro"

        # Check if new name conflicts with existing macro (unless it's the same macro)
        if (
            update_data.new_name != update_data.old_name
            and update_data.new_name in macros
        ):
            return False, f"A macro named '{update_data.new_name}' already exists"

        now = datetime.now(UTC)

        # Update the macro data while preserving metadata
        updated_macro = current_macro.copy()
        updated_macro["name"] = update_data.new_name
        updated_macro["embed_data"] = update_data.embed_data
        updated_macro["modified_at"] = now.isoformat()
        updated_macro["modified_by"] = update_data.edited_by
        updated_macro["modified_by_name"] = update_data.edited_by_name

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
        return False, "Failed to save embed macro changes to file"

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
                    with open(config_path, encoding="utf-8") as f:
                        return yaml.safe_load(f) or {}
                except (yaml.YAMLError, OSError):
                    continue

        # Return default configuration if no file found
        return {
            "bot": {
                "permissions": {
                    "admin_roles": ["admin"],
                    "admin_permissions": ["administrator"],
                }
            }
        }

    def check_admin_access(
        self, user_roles: list[str], guild_permissions: int = 0
    ) -> bool:
        """Check if user has admin access based on roles or Discord permissions.

        Args:
            user_roles: List of role names the user has in the server.
            guild_permissions: User's Discord permissions in the server (as integer).

        Returns:
            bool: True if user has admin access, False otherwise.
        """
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
        admin_permissions = permissions_config.get(
            "admin_permissions", ["administrator"]
        )

        logger.info(
            f"Admin permissions: {admin_permissions}, User guild permissions: {guild_permissions} (0x{guild_permissions:x})"
        )

        for permission_name in admin_permissions:
            # Convert permission name to Discord permission bit
            permission_bit = self._get_permission_bit(permission_name)
            logger.info(
                f"Checking permission '{permission_name}' (bit: 0x{permission_bit:x})"
            )
            if (
                permission_bit
                and (guild_permissions & permission_bit) == permission_bit
            ):
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
