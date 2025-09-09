"""
Statistics Service for Django Integration

This service handles saving Discord message statistics to the Django database.
It provides an interface between the Discord bot and the Django web application.
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add the Django project to Python path
django_path = Path(__file__).parent.parent.parent / "web"
sys.path.append(str(django_path))

# Configure Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "weakauras_web.settings")

try:
    import django

    django.setup()

    # Now we can import Django models
    from asgiref.sync import sync_to_async
    from django.db import models, transaction
    from django.utils import timezone
    from user_stats.models import (
        DiscordChannel,
        DiscordGuild,
        DiscordUser,
        MessageStatistics,
        StatisticsCollectionJob,
    )

    DJANGO_AVAILABLE = True
    STATS_SERVICE_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Django not available in bot environment: {e}")
    DJANGO_AVAILABLE = False
    STATS_SERVICE_AVAILABLE = False


class StatsService:
    """Service for managing user statistics data with Django integration."""

    def __init__(self):
        self.django_available = DJANGO_AVAILABLE

    def save_statistics_to_django(self, stats_data: dict, job_id: str = None) -> bool:  # noqa: PLR0912, PLR0915
        """
        Save collected statistics to Django database.

        Args:
            stats_data: Statistics data from bot collection
            job_id: Optional job ID for tracking

        Returns:
            bool: True if saved successfully, False otherwise
        """
        if not self.django_available:
            print("Django not available, cannot save statistics to database")
            return False

        try:
            with transaction.atomic():
                # Get or create guild
                guild, created = DiscordGuild.objects.get_or_create(
                    guild_id=str(stats_data["guild_id"]),
                    defaults={
                        "name": stats_data["guild_name"],
                    },
                )

                if not created:
                    # Update guild name if it changed
                    guild.name = stats_data["guild_name"]
                    guild.save()

                # Process channel statistics
                channels_created = 0
                users_created = 0
                stats_updated = 0

                for channel_id, channel_data in stats_data["channel_stats"].items():
                    # Get or create channel
                    channel, created = DiscordChannel.objects.get_or_create(
                        channel_id=str(channel_id),
                        defaults={
                            "guild": guild,
                            "name": channel_data["name"],
                            "channel_type": "text",
                        },
                    )

                    if created:
                        channels_created += 1
                    elif channel.name != channel_data["name"]:
                        # Update channel name if it changed
                        channel.name = channel_data["name"]
                        channel.save()

                    # Process user statistics for this channel
                    for user_id, message_count in channel_data["user_counts"].items():
                        if user_id in stats_data["user_stats"]:
                            user_info = stats_data["user_stats"][user_id]

                            # Get or create user
                            user, created = DiscordUser.objects.get_or_create(
                                user_id=str(user_id),
                                defaults={
                                    "username": user_info["username"],
                                    "display_name": user_info["username"],
                                    "avatar_url": user_info.get("avatar_url", ""),
                                },
                            )

                            if created:
                                users_created += 1
                            # Update user info if it changed
                            elif user.username != user_info["username"]:
                                user.username = user_info["username"]
                                user.display_name = user_info["username"]
                                user.save()

                            # Calculate time-based statistics using actual message timestamps
                            now = timezone.now()
                            cutoff_7_days = now - timedelta(days=7)
                            cutoff_30_days = now - timedelta(days=30)
                            cutoff_90_days = now - timedelta(days=90)

                            # Get message timestamps for this user in this channel
                            message_timestamps = []
                            if (
                                "user_messages" in channel_data
                                and user_id in channel_data["user_messages"]
                            ):
                                message_timestamps = channel_data["user_messages"][
                                    user_id
                                ]

                            # Convert timestamps to timezone-aware datetime objects
                            tz_aware_timestamps = []
                            for ts in message_timestamps:
                                if isinstance(ts, datetime):
                                    # Make timezone-aware if not already
                                    if ts.tzinfo is None:
                                        tz_aware_ts = timezone.make_aware(ts)
                                    else:
                                        tz_aware_ts = ts
                                    tz_aware_timestamps.append(tz_aware_ts)

                            # Calculate time-based counts using actual message dates
                            messages_last_7_days = sum(
                                1 for ts in tz_aware_timestamps if ts >= cutoff_7_days
                            )
                            messages_last_30_days = sum(
                                1 for ts in tz_aware_timestamps if ts >= cutoff_30_days
                            )
                            messages_last_90_days = sum(
                                1 for ts in tz_aware_timestamps if ts >= cutoff_90_days
                            )

                            # Find first and last message dates
                            first_message_date = (
                                min(tz_aware_timestamps) if tz_aware_timestamps else now
                            )
                            last_message_date = (
                                max(tz_aware_timestamps) if tz_aware_timestamps else now
                            )

                            stats, created = MessageStatistics.objects.get_or_create(
                                user=user,
                                channel=channel,
                                defaults={
                                    "total_messages": message_count,
                                    "messages_last_7_days": messages_last_7_days,
                                    "messages_last_30_days": messages_last_30_days,
                                    "messages_last_90_days": messages_last_90_days,
                                    "last_message_date": last_message_date,
                                    "first_message_date": first_message_date,
                                    "collection_method": "full_scan",
                                },
                            )

                            if not created:
                                # Update existing statistics with proper time-based calculations
                                stats.total_messages = message_count
                                stats.messages_last_7_days = messages_last_7_days
                                stats.messages_last_30_days = messages_last_30_days
                                stats.messages_last_90_days = messages_last_90_days
                                stats.last_message_date = last_message_date
                                stats.first_message_date = first_message_date
                                stats.last_collected = now
                                stats.save()

                            stats_updated += 1

                # Update collection job if provided
                if job_id:
                    try:
                        job = StatisticsCollectionJob.objects.get(id=job_id)
                        job.status = "completed"
                        job.completed_at = timezone.now()
                        job.messages_processed = stats_data["total_messages"]
                        job.users_updated = len(stats_data["user_stats"])
                        job.save()
                    except StatisticsCollectionJob.DoesNotExist:
                        # Job might not exist in Django if created outside
                        pass

                print(
                    f"Statistics saved: {channels_created} channels, {users_created} users, {stats_updated} stats"
                )
                return True

        except Exception as e:
            print(f"Error saving statistics to Django: {e}")
            return False

    async def save_statistics_to_django_async(
        self, stats_data: dict, job_id: str = None
    ) -> bool:
        """
        Async version of save_statistics_to_django for use in Discord bot context.
        """
        if not self.django_available:
            return False

        # Wrap the sync method with sync_to_async
        sync_save = sync_to_async(self.save_statistics_to_django, thread_sensitive=True)
        return await sync_save(stats_data, job_id)

    def create_collection_job(
        self,
        guild_id: int,
        guild_name: str,
        target_user_id: int = None,
        target_username: str = None,
        time_range_days: int = None,
    ) -> str:
        """
        Create a statistics collection job in Django.

        Returns:
            str: Job ID if successful, None otherwise
        """
        if not self.django_available:
            return None

        try:
            # Get or create guild
            guild, _ = DiscordGuild.objects.get_or_create(
                guild_id=str(guild_id), defaults={"name": guild_name}
            )

            # Get or create target user if specified
            target_user = None
            if target_user_id:
                target_user, _ = DiscordUser.objects.get_or_create(
                    user_id=str(target_user_id),
                    defaults={
                        "username": target_username or f"User_{target_user_id}",
                        "display_name": target_username or f"User_{target_user_id}",
                    },
                )

            # Create collection job
            job = StatisticsCollectionJob.objects.create(
                guild=guild,
                target_user=target_user,
                time_range_days=time_range_days,
                status="pending",
            )

            return str(job.id)

        except Exception as e:
            print(f"Error creating collection job: {e}")
            return None

    def get_user_statistics(self, guild_id: int, user_id: int = None) -> dict:
        """
        Get user statistics from Django database.

        Args:
            guild_id: Discord guild ID
            user_id: Optional specific user ID

        Returns:
            dict: Statistics data
        """
        if not self.django_available:
            return {}

        try:
            guild = DiscordGuild.objects.get(guild_id=str(guild_id))

            query = MessageStatistics.objects.select_related("user", "channel").filter(
                channel__guild=guild
            )

            if user_id:
                query = query.filter(user__user_id=str(user_id))

            stats = query.order_by("-total_messages")

            result = {"guild_id": guild_id, "guild_name": guild.name, "users": {}}

            for stat in stats:
                user_id_str = stat.user.user_id
                if user_id_str not in result["users"]:
                    result["users"][user_id_str] = {
                        "username": stat.user.username,
                        "display_name": stat.user.display_name,
                        "avatar_url": stat.user.avatar_url,
                        "total_messages": 0,
                        "channels": {},
                    }

                result["users"][user_id_str]["channels"][stat.channel.channel_id] = {
                    "name": stat.channel.name,
                    "total_messages": stat.total_messages,
                    "messages_last_7_days": stat.messages_last_7_days,
                    "messages_last_30_days": stat.messages_last_30_days,
                    "messages_last_90_days": stat.messages_last_90_days,
                    "last_message_date": stat.last_message_date.isoformat()
                    if stat.last_message_date
                    else None,
                }

                result["users"][user_id_str]["total_messages"] += stat.total_messages

        except Exception as e:
            print(f"Error getting statistics from Django: {e}")
            return {}
        else:
            return result

    def get_available_guilds(self) -> list:
        """Get list of available guilds with statistics data."""
        if not self.django_available:
            return []

        try:
            guilds = DiscordGuild.objects.annotate(
                user_count=models.Count("channels__message_stats__user", distinct=True),
                message_count=models.Sum("channels__message_stats__total_messages"),
            ).filter(user_count__gt=0)

            return [
                {
                    "guild_id": guild.guild_id,
                    "name": guild.name,
                    "user_count": guild.user_count,
                    "message_count": guild.message_count or 0,
                    "last_updated": guild.last_updated.isoformat(),
                }
                for guild in guilds
            ]

        except Exception as e:
            print(f"Error getting available guilds: {e}")
            return []


# Global instance
stats_service = StatsService()
