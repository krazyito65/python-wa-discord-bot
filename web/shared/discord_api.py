"""
Discord API utilities for WeakAuras Web Interface

This module provides functions to interact with the Discord API,
specifically for fetching user guild information for server selection.
"""

import requests
from allauth.socialaccount.models import SocialToken


class DiscordAPIError(Exception):
    """Exception raised when Discord API calls fail."""


def get_user_discord_token(user) -> str | None:
    """Get the Discord OAuth token for a user.

    Args:
        user: Django user object with social account information.

    Returns:
        Optional[str]: Discord OAuth token if available, None otherwise.
    """
    try:
        # Get the Discord social token for this user
        token = SocialToken.objects.get(account__user=user, account__provider="discord")
    except SocialToken.DoesNotExist:
        return None
    else:
        return token.token


def get_user_guilds(user) -> list[dict]:
    """Fetch the list of Discord guilds/servers the user belongs to.

    Args:
        user: Django user object with Discord OAuth token.

    Returns:
        List[Dict]: List of guild information dictionaries from Discord API.
                   Each dict contains guild id, name, icon, permissions, etc.

    Raises:
        DiscordAPIError: If Discord API request fails.
    """
    token = get_user_discord_token(user)
    if not token:
        msg = "No Discord token available for user"
        raise DiscordAPIError(msg)

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    try:
        response = requests.get(
            "https://discord.com/api/v10/users/@me/guilds", headers=headers, timeout=10
        )
        response.raise_for_status()
        return response.json()

    except requests.RequestException as e:
        msg = f"Failed to fetch user guilds: {e}"
        raise DiscordAPIError(msg) from e


def get_user_info(user) -> dict | None:
    """Fetch Discord user information.

    Args:
        user: Django user object with Discord OAuth token.

    Returns:
        Optional[Dict]: User information from Discord API, None if request fails.
    """
    token = get_user_discord_token(user)
    if not token:
        return None

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    try:
        response = requests.get(
            "https://discord.com/api/v10/users/@me", headers=headers, timeout=10
        )
        response.raise_for_status()
        return response.json()

    except requests.RequestException:
        return None


def filter_available_servers(
    user_guilds: list[dict], bot_servers: list[dict]
) -> list[dict]:
    """Filter user guilds to only show servers where the bot has data.

    Args:
        user_guilds (List[Dict]): List of guilds from Discord API that user belongs to.
        bot_servers (List[Dict]): List of servers that have bot data folders.

    Returns:
        List[Dict]: List of server information for servers where:
                   - User is a member AND
                   - Bot has data stored for that server
                   Each dict contains both Discord guild info and bot data info.
    """
    available_servers = []

    # Create a lookup dictionary for bot servers by guild_id
    bot_servers_dict = {server["guild_id"]: server for server in bot_servers}

    for guild in user_guilds:
        guild_id = int(guild["id"])

        # Check if this guild exists in bot data
        if guild_id in bot_servers_dict:
            bot_server = bot_servers_dict[guild_id]

            # Combine Discord guild info with bot server info
            combined_server = {
                "guild_id": guild_id,
                "guild_name": guild["name"],
                "guild_icon": guild.get("icon"),
                "user_permissions": guild.get("permissions", 0),
                "bot_folder_name": bot_server["folder_name"],
                "bot_folder_path": str(bot_server["folder_path"]),
            }

            available_servers.append(combined_server)

    # Sort by server name for consistent display
    available_servers.sort(key=lambda x: x["guild_name"].lower())

    return available_servers
