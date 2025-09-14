"""
Discord API utilities for WeakAuras Web Interface

This module provides functions to interact with the Discord API,
specifically for fetching user guild information for server selection.
"""

import requests
from allauth.socialaccount.models import SocialToken
from django.conf import settings
from django.core.cache import cache

from .bot_interface import bot_interface

# HTTP status constants
HTTP_NOT_FOUND = 404


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

    Uses caching to avoid hitting Discord API rate limits. Cache duration
    can be configured via DISCORD_GUILD_CACHE_TIMEOUT setting (default: 300 seconds).

    Args:
        user: Django user object with Discord OAuth token.

    Returns:
        List[Dict]: List of guild information dictionaries from Discord API.
                   Each dict contains guild id, name, icon, permissions, etc.

    Raises:
        DiscordAPIError: If Discord API request fails.
    """
    # Check cache first to avoid rate limiting
    cache_key = f"discord_guilds_{user.id}"
    cached_guilds = cache.get(cache_key)

    if cached_guilds is not None:
        return cached_guilds

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
        guilds = response.json()

        # Cache the result to avoid rate limiting
        # Default cache timeout is 5 minutes, configurable via settings
        cache_timeout = getattr(settings, "DISCORD_GUILD_CACHE_TIMEOUT", 300)
        cache.set(cache_key, guilds, cache_timeout)

        return guilds

    except requests.RequestException as e:
        msg = f"Failed to fetch user guilds: {e}"
        raise DiscordAPIError(msg) from e


def get_user_info(user) -> dict | None:
    """Fetch Discord user information.

    Uses caching to avoid hitting Discord API rate limits. Cache duration
    can be configured via DISCORD_USER_CACHE_TIMEOUT setting (default: 300 seconds).

    Args:
        user: Django user object with Discord OAuth token.

    Returns:
        Optional[Dict]: User information from Discord API, None if request fails.
    """
    # Check cache first to avoid rate limiting
    cache_key = f"discord_user_{user.id}"
    cached_user_info = cache.get(cache_key)

    if cached_user_info is not None:
        return cached_user_info

    token = get_user_discord_token(user)
    if not token:
        return None

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    try:
        response = requests.get(
            "https://discord.com/api/v10/users/@me", headers=headers, timeout=10
        )
        response.raise_for_status()
        user_info = response.json()

        # Cache the result to avoid rate limiting
        # Default cache timeout is 5 minutes, configurable via settings
        cache_timeout = getattr(settings, "DISCORD_USER_CACHE_TIMEOUT", 300)
        cache.set(cache_key, user_info, cache_timeout)

        return user_info

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


def get_user_guild_member(user, guild_id: int) -> dict | None:
    """Fetch user's member information for a specific guild/server.

    This includes roles, permissions, and other server-specific data.
    Uses caching to avoid hitting Discord API rate limits.

    Args:
        user: Django user object with Discord OAuth token.
        guild_id: Discord guild ID to get member info for.

    Returns:
        Optional[Dict]: Member information from Discord API, None if request fails.
                       Contains roles, permissions, nick, joined_at, etc.

    Raises:
        DiscordAPIError: If Discord API request fails.
    """
    token = get_user_discord_token(user)
    if not token:
        raise DiscordAPIError("No Discord token available")

    user_id = user.socialaccount_set.first().uid
    cache_key = f"discord_member_{user_id}_{guild_id}"

    # Check cache first
    cached_member = cache.get(cache_key)
    if cached_member is not None:
        return cached_member

    try:
        headers = {"Authorization": f"Bearer {token}"}

        # Get guild member information
        response = requests.get(
            f"https://discord.com/api/v10/users/@me/guilds/{guild_id}/member",
            headers=headers,
            timeout=10,
        )

        if response.status_code == HTTP_NOT_FOUND:
            # User is not a member of this guild
            cache.set(cache_key, None, 300)  # Cache negative result briefly
            return None

        response.raise_for_status()
        member_data = response.json()

        # Cache the result
        cache_timeout = getattr(settings, "DISCORD_MEMBER_CACHE_TIMEOUT", 300)
        cache.set(cache_key, member_data, cache_timeout)

        return member_data

    except requests.RequestException as e:
        msg = f"Failed to fetch guild member info: {e}"
        raise DiscordAPIError(msg) from e


def clear_user_discord_cache(user) -> None:
    """Clear cached Discord data for a specific user.

    Useful when user's Discord server membership changes or when
    debugging rate limit issues.

    Args:
        user: Django user object to clear cache for.
    """
    user_id = (
        user.socialaccount_set.first().uid if user.socialaccount_set.first() else None
    )

    if user_id:
        cache.delete(f"discord_guilds_{user.id}")
        cache.delete(f"discord_user_{user.id}")

        # Clear member cache for all guilds (basic approach)
        # In production, you might want more sophisticated pattern-based cache clearing
        try:
            # Try to clear member cache keys - this is cache backend dependent
            for i in range(
                100000000000000000, 999999999999999999, 1000000000
            ):  # Common Discord ID range
                cache.delete(f"discord_member_{user_id}_{i}")
        except Exception:
            pass  # Cache clearing is best effort


def clear_all_discord_cache() -> None:
    """Clear all Discord API cache data.

    This is a more aggressive cache clearing that removes all Discord-related
    cached data. Use sparingly as it will cause all users to hit the API again.
    """
    # Django's cache.clear() clears all cache, which might be too broad
    # For production, you might want to implement a more targeted approach
    # using cache key patterns if your cache backend supports it
    cache.clear()


def get_bot_discord_token() -> str | None:
    """Get the Discord bot token from configuration.

    Returns:
        Optional[str]: Discord bot token if available, None otherwise.
    """
    try:
        config = bot_interface.load_bot_config()
        # Try to get dev token first, then prod
        tokens = config.get("discord", {}).get("tokens", {})
        return tokens.get("dev") or tokens.get("prod")
    except Exception:
        return None


def get_user_roles_in_guild(user, guild_id: int) -> list[dict] | None:
    """Fetch user's roles in a specific guild using bot token.

    This uses the bot token to make privileged API calls to get detailed
    member information including roles.

    Args:
        user: Django user object with Discord social account.
        guild_id: Discord guild ID to get roles for.

    Returns:
        Optional[List[Dict]]: List of role objects from Discord API, None if request fails.
                             Each role dict contains id, name, color, permissions, etc.

    Raises:
        DiscordAPIError: If Discord API request fails.
    """
    bot_token = get_bot_discord_token()
    if not bot_token:
        raise DiscordAPIError("No Discord bot token available")

    user_id = (
        user.socialaccount_set.first().uid if user.socialaccount_set.first() else None
    )
    if not user_id:
        raise DiscordAPIError("No Discord user ID available")

    cache_key = f"discord_user_roles_{user_id}_{guild_id}"

    # Check cache first
    cached_roles = cache.get(cache_key)
    if cached_roles is not None:
        return cached_roles

    try:
        headers = {"Authorization": f"Bot {bot_token}"}

        # Get guild member information using bot token
        response = requests.get(
            f"https://discord.com/api/v10/guilds/{guild_id}/members/{user_id}",
            headers=headers,
            timeout=10,
        )

        if response.status_code == HTTP_NOT_FOUND:
            # User is not a member of this guild
            cache.set(cache_key, None, 300)  # Cache negative result briefly
            return None

        response.raise_for_status()
        member_data = response.json()

        # Extract role IDs from member data
        role_ids = member_data.get("roles", [])

        if not role_ids:
            # User has no roles (only @everyone)
            cache.set(cache_key, [], 300)
            return []

        # Get detailed role information
        guild_response = requests.get(
            f"https://discord.com/api/v10/guilds/{guild_id}",
            headers=headers,
            timeout=10,
        )
        guild_response.raise_for_status()
        guild_data = guild_response.json()

        # Filter roles to only include the ones the user has
        all_roles = guild_data.get("roles", [])
        user_roles = [role for role in all_roles if role["id"] in role_ids]

        # Cache the result
        cache_timeout = getattr(settings, "DISCORD_ROLES_CACHE_TIMEOUT", 300)
        cache.set(cache_key, user_roles, cache_timeout)

        return user_roles

    except requests.RequestException as e:
        msg = f"Failed to fetch user roles: {e}"
        raise DiscordAPIError(msg) from e


def get_guild_roles(guild_id: int) -> list[dict] | None:
    """Fetch all roles in a specific guild using bot token.

    This uses the bot token to make privileged API calls to get all
    roles available in the guild.

    Args:
        guild_id: Discord guild ID to get roles for.

    Returns:
        Optional[List[Dict]]: List of role objects from Discord API, None if request fails.
                             Each role dict contains id, name, color, permissions, etc.

    Raises:
        DiscordAPIError: If Discord API request fails.
    """
    bot_token = get_bot_discord_token()
    if not bot_token:
        raise DiscordAPIError("No Discord bot token available")

    cache_key = f"discord_guild_roles_{guild_id}"

    # Check cache first
    cached_roles = cache.get(cache_key)
    if cached_roles is not None:
        return cached_roles

    try:
        headers = {"Authorization": f"Bot {bot_token}"}

        # Get guild information including roles
        response = requests.get(
            f"https://discord.com/api/v10/guilds/{guild_id}",
            headers=headers,
            timeout=10,
        )

        if response.status_code == HTTP_NOT_FOUND:
            # Guild not found or bot not in guild
            cache.set(cache_key, None, 300)  # Cache negative result briefly
            return None

        response.raise_for_status()
        guild_data = response.json()

        # Extract roles from guild data
        all_roles = guild_data.get("roles", [])

        # Sort roles by position (higher positions first), then by name
        all_roles.sort(
            key=lambda role: (-role.get("position", 0), role.get("name", "").lower())
        )

        # Cache the result
        cache_timeout = getattr(settings, "DISCORD_ROLES_CACHE_TIMEOUT", 300)
        cache.set(cache_key, all_roles, cache_timeout)

        return all_roles

    except requests.RequestException as e:
        msg = f"Failed to fetch guild roles: {e}"
        raise DiscordAPIError(msg) from e
