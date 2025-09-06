"""
API views for WeakAuras Web Interface

This module contains REST API views for managing macros and servers
through programmatic access to the bot's data.
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from shared.bot_interface import bot_interface
from shared.discord_api import (
    DiscordAPIError,
    filter_available_servers,
    get_user_guilds,
)


class ServerListAPIView(APIView):
    """API view to list available servers for the authenticated user."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get list of servers user has access to.

        Returns:
            Response: JSON list of available servers with guild info.
        """
        try:
            user_guilds = get_user_guilds(request.user)
            bot_servers = bot_interface.get_available_servers()
            available_servers = filter_available_servers(user_guilds, bot_servers)

            return Response(available_servers, status=status.HTTP_200_OK)

        except DiscordAPIError as e:
            return Response(
                {"error": f"Discord API error: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class MacroListAPIView(APIView):
    """API view to list macros for a specific server."""

    permission_classes = [IsAuthenticated]

    def get(self, request, guild_id):
        """Get list of macros for a specific server.

        Args:
            guild_id (int): Discord guild/server ID.

        Returns:
            Response: JSON list of macros for the server.
        """
        try:
            # Verify user has access to this server
            user_guilds = get_user_guilds(request.user)
            user_guild_ids = [int(guild["id"]) for guild in user_guilds]

            if guild_id not in user_guild_ids:
                return Response(
                    {"error": "Access denied to this server"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Find guild name
            guild_name = None
            for guild in user_guilds:
                if int(guild["id"]) == guild_id:
                    guild_name = guild["name"]
                    break

            if not guild_name:
                return Response(
                    {"error": "Server not found"}, status=status.HTTP_404_NOT_FOUND
                )

            # Load macros
            macros = bot_interface.load_server_macros(guild_id, guild_name)

            return Response(macros, status=status.HTTP_200_OK)

        except DiscordAPIError as e:
            return Response(
                {"error": f"Discord API error: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class MacroCreateAPIView(APIView):
    """API view to create new macros."""

    permission_classes = [IsAuthenticated]

    def post(self, _request, _guild_id):
        """Create a new macro for a specific server.

        Args:
            guild_id (int): Discord guild/server ID.

        Expected JSON payload:
            {
                "name": "macro_name",
                "message": "macro content"
            }

        Returns:
            Response: Success or error message.
        """
        try:
            # TODO: Implement macro creation via API
            return Response(
                {"message": "Macro creation API coming soon!"},
                status=status.HTTP_501_NOT_IMPLEMENTED,
            )

        except Exception as e:
            return Response(
                {"error": f"Unexpected error: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class MacroDetailAPIView(APIView):
    """API view for individual macro operations (get, update, delete)."""

    permission_classes = [IsAuthenticated]

    def get(self, _request, _guild_id, _macro_name):
        """Get details of a specific macro."""
        # TODO: Implement macro detail retrieval
        return Response(
            {"message": f"Getting macro {_macro_name} coming soon!"},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )

    def put(self, _request, _guild_id, _macro_name):
        """Update a specific macro."""
        # TODO: Implement macro update
        return Response(
            {"message": f"Updating macro {_macro_name} coming soon!"},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )

    def delete(self, _request, _guild_id, _macro_name):
        """Delete a specific macro."""
        # TODO: Implement macro deletion via API
        return Response(
            {"message": f"Deleting macro {_macro_name} coming soon!"},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )
