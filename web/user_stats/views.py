"""
Views for user statistics display and management.

This module provides web views for displaying Discord user message statistics
collected from various channels within Discord servers.
"""

import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from shared.discord_api import DiscordAPIError, get_user_guilds

from .models import (
    DiscordChannel,
    DiscordGuild,
    DiscordUser,
    MessageStatistics,
    StatisticsCollectionJob,
)


@login_required
def user_stats_dashboard(request):
    """Display dashboard with available guilds and their statistics."""
    try:
        user_guilds = get_user_guilds(request.user)
        user_guild_ids = [int(guild["id"]) for guild in user_guilds]

        # Get guilds that have statistics data and user has access to
        guilds_with_stats = (
            DiscordGuild.objects.filter(
                guild_id__in=[str(gid) for gid in user_guild_ids]
            )
            .annotate(
                user_count=Count("channels__message_stats__user", distinct=True),
                message_count=Sum("channels__message_stats__total_messages"),
                channel_count=Count("channels", distinct=True),
            )
            .filter(user_count__gt=0)
            .order_by("-message_count")
        )

        context = {
            "guilds_with_stats": guilds_with_stats,
            "total_guilds": len(user_guilds),
        }

        return render(request, "user_stats/dashboard.html", context)

    except DiscordAPIError as e:
        messages.error(request, f"Error accessing Discord servers: {e}")
        return redirect("servers:dashboard")


@login_required
def guild_user_stats(request, guild_id):  # noqa: PLR0912, PLR0915
    """Display user statistics for a specific guild."""
    try:
        # Verify user has access to this guild
        user_guilds = get_user_guilds(request.user)
        user_guild_ids = [int(guild["id"]) for guild in user_guilds]

        if guild_id not in user_guild_ids:
            raise Http404("You don't have access to this server")

        # Get guild and its statistics
        guild = get_object_or_404(DiscordGuild, guild_id=str(guild_id))

        # Get filter parameters
        selected_user_id = request.GET.get("user")
        selected_channel_id = request.GET.get("channel")
        time_range = request.GET.get("time_range", "all")

        # Base query
        stats_query = MessageStatistics.objects.select_related(
            "user", "channel"
        ).filter(channel__guild=guild)

        # Apply filters
        if selected_user_id:
            stats_query = stats_query.filter(user__user_id=selected_user_id)

        if selected_channel_id:
            stats_query = stats_query.filter(channel__channel_id=selected_channel_id)

        # Get statistics based on time range
        if time_range == "7d":
            stats_query = stats_query.filter(messages_last_7_days__gt=0)
        elif time_range == "30d":
            stats_query = stats_query.filter(messages_last_30_days__gt=0)
        elif time_range == "90d":
            stats_query = stats_query.filter(messages_last_90_days__gt=0)

        # Get user statistics aggregated by user
        user_stats = {}
        channel_stats = {}
        total_messages = 0

        for stat in stats_query:
            user_id = stat.user.user_id
            channel_id = stat.channel.channel_id

            # Select message count based on time range
            if time_range == "7d":
                message_count = stat.messages_last_7_days
            elif time_range == "30d":
                message_count = stat.messages_last_30_days
            elif time_range == "90d":
                message_count = stat.messages_last_90_days
            else:
                message_count = stat.total_messages

            # Skip if no messages in this time range
            if message_count == 0:
                continue

            # Aggregate user stats
            if user_id not in user_stats:
                user_stats[user_id] = {
                    "user": stat.user,
                    "total_messages": 0,
                    "channels": {},
                }

            user_stats[user_id]["total_messages"] += message_count
            user_stats[user_id]["channels"][channel_id] = {
                "channel": stat.channel,
                "message_count": message_count,
                "last_message_date": stat.last_message_date,
            }

            # Aggregate channel stats
            if channel_id not in channel_stats:
                channel_stats[channel_id] = {
                    "channel": stat.channel,
                    "total_messages": 0,
                    "user_count": 0,
                }

            channel_stats[channel_id]["total_messages"] += message_count
            channel_stats[channel_id]["user_count"] += 1

            total_messages += message_count

        # Sort users by message count
        sorted_user_stats = sorted(
            user_stats.items(), key=lambda x: x[1]["total_messages"], reverse=True
        )

        # Get available users and channels for filters
        available_users = (
            DiscordUser.objects.filter(message_stats__channel__guild=guild)
            .distinct()
            .order_by("username")
        )

        available_channels = (
            DiscordChannel.objects.filter(guild=guild, message_stats__isnull=False)
            .distinct()
            .order_by("name")
        )

        # Get recent collection jobs
        recent_jobs = StatisticsCollectionJob.objects.filter(guild=guild).order_by(
            "-created_at"
        )[:5]

        # Calculate average messages per user
        avg_messages_per_user = (
            round(total_messages / len(user_stats)) if len(user_stats) > 0 else 0
        )

        context = {
            "guild": guild,
            "user_stats": sorted_user_stats,
            "channel_stats": sorted(
                channel_stats.items(),
                key=lambda x: x[1]["total_messages"],
                reverse=True,
            ),
            "total_messages": total_messages,
            "total_users": len(user_stats),
            "total_channels": len(channel_stats),
            "avg_messages_per_user": avg_messages_per_user,
            "available_users": available_users,
            "available_channels": available_channels,
            "selected_user_id": selected_user_id,
            "selected_channel_id": selected_channel_id,
            "time_range": time_range,
            "recent_jobs": recent_jobs,
        }

        return render(request, "user_stats/guild_stats.html", context)

    except DiscordAPIError as e:
        messages.error(request, f"Error accessing Discord data: {e}")
        return redirect("user_stats:dashboard")


@login_required
def user_detail_stats(request, guild_id, user_id):
    """Display detailed statistics for a specific user in a guild."""
    try:
        # Verify access
        user_guilds = get_user_guilds(request.user)
        user_guild_ids = [int(guild["id"]) for guild in user_guilds]

        if guild_id not in user_guild_ids:
            raise Http404("You don't have access to this server")

        guild = get_object_or_404(DiscordGuild, guild_id=str(guild_id))
        user = get_object_or_404(DiscordUser, user_id=str(user_id))

        # Get user's statistics for this guild
        user_stats = (
            MessageStatistics.objects.select_related("channel")
            .filter(user=user, channel__guild=guild)
            .order_by("-total_messages")
        )

        # Calculate totals
        total_messages = sum(stat.total_messages for stat in user_stats)
        messages_7d = sum(stat.messages_last_7_days for stat in user_stats)
        messages_30d = sum(stat.messages_last_30_days for stat in user_stats)
        messages_90d = sum(stat.messages_last_90_days for stat in user_stats)

        # Get chart data for visualization
        chart_data = {
            "channels": [f"#{stat.channel.name}" for stat in user_stats],
            "messages": [stat.total_messages for stat in user_stats],
            "messages_7d": [stat.messages_last_7_days for stat in user_stats],
            "messages_30d": [stat.messages_last_30_days for stat in user_stats],
            "messages_90d": [stat.messages_last_90_days for stat in user_stats],
        }

        context = {
            "guild": guild,
            "target_user": user,
            "user_stats": user_stats,
            "total_messages": total_messages,
            "messages_7d": messages_7d,
            "messages_30d": messages_30d,
            "messages_90d": messages_90d,
            "chart_data": json.dumps(chart_data),
        }

        return render(request, "user_stats/user_detail.html", context)

    except DiscordAPIError as e:
        messages.error(request, f"Error accessing Discord data: {e}")
        return redirect("user_stats:dashboard")


@login_required
def api_guild_stats_json(request, guild_id):
    """API endpoint for guild statistics as JSON."""
    try:
        # Verify access
        user_guilds = get_user_guilds(request.user)
        user_guild_ids = [int(guild["id"]) for guild in user_guilds]

        if guild_id not in user_guild_ids:
            return JsonResponse({"error": "Access denied"}, status=403)

        guild = get_object_or_404(DiscordGuild, guild_id=str(guild_id))

        # Get time range filter
        time_range = request.GET.get("time_range", "all")

        # Get statistics
        stats_query = MessageStatistics.objects.select_related(
            "user", "channel"
        ).filter(channel__guild=guild)

        data = {
            "guild_id": guild.guild_id,
            "guild_name": guild.name,
            "users": [],
            "channels": [],
        }

        user_data = {}
        channel_data = {}

        for stat in stats_query:
            # Select message count based on time range
            if time_range == "7d":
                message_count = stat.messages_last_7_days
            elif time_range == "30d":
                message_count = stat.messages_last_30_days
            elif time_range == "90d":
                message_count = stat.messages_last_90_days
            else:
                message_count = stat.total_messages

            if message_count == 0:
                continue

            user_id = stat.user.user_id
            channel_id = stat.channel.channel_id

            # Aggregate user data
            if user_id not in user_data:
                user_data[user_id] = {
                    "user_id": user_id,
                    "username": stat.user.username,
                    "display_name": stat.user.display_name,
                    "avatar_url": stat.user.avatar_url,
                    "total_messages": 0,
                }
            user_data[user_id]["total_messages"] += message_count

            # Aggregate channel data
            if channel_id not in channel_data:
                channel_data[channel_id] = {
                    "channel_id": channel_id,
                    "name": stat.channel.name,
                    "total_messages": 0,
                }
            channel_data[channel_id]["total_messages"] += message_count

        # Sort and add to response
        data["users"] = sorted(
            user_data.values(), key=lambda x: x["total_messages"], reverse=True
        )

        data["channels"] = sorted(
            channel_data.values(), key=lambda x: x["total_messages"], reverse=True
        )

        return JsonResponse(data)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def live_stats_update(request, guild_id):
    """
    AJAX endpoint for live statistics updates during collection.
    Returns current stats count and collection progress.
    """
    try:
        # Verify user has access to this guild
        user_guilds = get_user_guilds(request.user)
        user_guild_ids = [int(guild["id"]) for guild in user_guilds]

        if int(guild_id) not in user_guild_ids:
            return JsonResponse({"error": "Access denied"}, status=403)

        # Get current stats count
        try:
            guild = DiscordGuild.objects.get(guild_id=str(guild_id))

            # Count current statistics
            stats_count = MessageStatistics.objects.filter(channel__guild=guild).count()

            user_count = (
                MessageStatistics.objects.filter(channel__guild=guild)
                .values("user")
                .distinct()
                .count()
            )

            channel_count = (
                MessageStatistics.objects.filter(channel__guild=guild)
                .values("channel")
                .distinct()
                .count()
            )

            total_messages = (
                MessageStatistics.objects.filter(channel__guild=guild).aggregate(
                    total=Sum("total_messages")
                )["total"]
                or 0
            )

            # Get latest collection job progress
            latest_job = (
                StatisticsCollectionJob.objects.filter(guild=guild)
                .order_by("-created_at")
                .first()
            )

            job_progress = None
            if latest_job:
                job_progress = {
                    "status": latest_job.status,
                    "progress_current": latest_job.progress_current,
                    "progress_total": latest_job.progress_total,
                    "progress_percentage": latest_job.progress_percentage,
                    "created_at": latest_job.created_at.isoformat(),
                    "completed_at": latest_job.completed_at.isoformat()
                    if latest_job.completed_at
                    else None,
                }

            return JsonResponse(
                {
                    "stats_count": stats_count,
                    "user_count": user_count,
                    "channel_count": channel_count,
                    "total_messages": total_messages,
                    "job_progress": job_progress,
                    "last_updated": timezone.now().isoformat(),
                }
            )

        except DiscordGuild.DoesNotExist:
            return JsonResponse(
                {
                    "stats_count": 0,
                    "user_count": 0,
                    "channel_count": 0,
                    "total_messages": 0,
                    "job_progress": None,
                    "last_updated": timezone.now().isoformat(),
                }
            )

    except DiscordAPIError as e:
        return JsonResponse({"error": f"Discord API error: {e}"}, status=500)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
