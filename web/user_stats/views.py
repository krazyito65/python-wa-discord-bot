"""
Views for user statistics display and management.

This module provides web views for displaying Discord user message statistics
collected from various channels within Discord servers.
"""

import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db.models import Count, Max, Sum
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
    """Display dashboard with available guilds and their statistics (cached)."""
    try:
        # Check cache first
        cache_key = f"user_stats_dashboard_{request.user.id}"
        cached_data = cache.get(cache_key)

        if cached_data:
            return render(request, "user_stats/dashboard.html", cached_data)

        user_guilds = get_user_guilds(request.user)
        user_guild_ids = [int(guild["id"]) for guild in user_guilds]

        # Get guilds that have statistics data and user has access to
        # Use more efficient query with only necessary fields
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

        # Cache using configurable timeout
        cache_timeout = getattr(settings, "USER_STATS_CACHE_TIMEOUT", 300)
        cache.set(cache_key, context, cache_timeout)

        return render(request, "user_stats/dashboard.html", context)

    except DiscordAPIError as e:
        messages.error(request, f"Error accessing Discord servers: {e}")
        return redirect("servers:dashboard")


@login_required
def guild_user_stats(request, guild_id):
    """Display user statistics for a specific guild with optimized database queries."""
    try:
        # Check cache first for performance
        cache_key = f"guild_stats_{guild_id}_{request.user.id}"
        filter_params = {
            "user": request.GET.get("user"),
            "channel": request.GET.get("channel"),
            "time_range": request.GET.get("time_range", "all"),
        }

        # Create cache key that includes filters
        cache_key_with_filters = (
            f"{cache_key}_{hash(str(sorted(filter_params.items())))}"
        )
        cached_data = cache.get(cache_key_with_filters)

        if cached_data:
            return render(request, "user_stats/guild_stats.html", cached_data)

        # Verify user has access to this guild
        user_guilds = get_user_guilds(request.user)
        user_guild_ids = [int(guild["id"]) for guild in user_guilds]

        if guild_id not in user_guild_ids:
            raise Http404("Access denied")  # noqa: TRY003

        # Get guild and its statistics
        guild = get_object_or_404(DiscordGuild, guild_id=str(guild_id))

        # Get filter parameters
        selected_user_id = filter_params["user"]
        selected_channel_id = filter_params["channel"]
        time_range = filter_params["time_range"]

        # Determine message field based on time range
        if time_range == "7d":
            message_field = "messages_last_7_days"
        elif time_range == "30d":
            message_field = "messages_last_30_days"
        elif time_range == "90d":
            message_field = "messages_last_90_days"
        else:
            message_field = "total_messages"

        # Build base queryset with proper select_related for performance
        base_queryset = MessageStatistics.objects.select_related(
            "user", "channel"
        ).filter(
            channel__guild=guild,
            **{
                f"{message_field}__gt": 0
            },  # Only include records with messages in time range
        )

        # Apply filters
        if selected_user_id:
            base_queryset = base_queryset.filter(user__user_id=selected_user_id)
        if selected_channel_id:
            base_queryset = base_queryset.filter(
                channel__channel_id=selected_channel_id
            )

        # Get user statistics using database aggregation (much faster)
        user_stats_qs = (
            base_queryset.values(
                "user__user_id",
                "user__username",
                "user__display_name",
                "user__avatar_url",
            )
            .annotate(
                total_messages=Sum(message_field),
                channel_count=Count("channel", distinct=True),
                latest_message=Max("last_message_date"),
            )
            .order_by("-total_messages")
        )

        # Get channel statistics using database aggregation
        channel_stats_qs = (
            base_queryset.values(
                "channel__channel_id", "channel__name", "channel__type"
            )
            .annotate(
                total_messages=Sum(message_field),
                user_count=Count("user", distinct=True),
            )
            .order_by("-total_messages")
        )

        # Get overall totals using database aggregation
        totals = base_queryset.aggregate(
            total_messages=Sum(message_field),
            total_users=Count("user", distinct=True),
            total_channels=Count("channel", distinct=True),
        )

        # Convert querysets to lists for template (and calculate additional data)
        user_stats_list = []
        for user_stat in user_stats_qs:
            # Get detailed channel breakdown for each user
            user_channels = (
                base_queryset.filter(user__user_id=user_stat["user__user_id"])
                .values("channel__channel_id", "channel__name", "last_message_date")
                .annotate(message_count=Sum(message_field))
                .filter(message_count__gt=0)
            )

            user_stat["channels"] = {
                ch["channel__channel_id"]: {
                    "channel": {
                        "channel_id": ch["channel__channel_id"],
                        "name": ch["channel__name"],
                    },
                    "message_count": ch["message_count"],
                    "last_message_date": ch["last_message_date"],
                }
                for ch in user_channels
            }

            # Create user object for template compatibility
            user_stat["user"] = {
                "user_id": user_stat["user__user_id"],
                "username": user_stat["user__username"],
                "display_name": user_stat["user__display_name"],
                "avatar_url": user_stat["user__avatar_url"],
            }

            user_stats_list.append((user_stat["user__user_id"], user_stat))

        channel_stats_list = [
            (
                ch["channel__channel_id"],
                {
                    "channel": {
                        "channel_id": ch["channel__channel_id"],
                        "name": ch["channel__name"],
                        "type": ch["channel__type"],
                    },
                    "total_messages": ch["total_messages"],
                    "user_count": ch["user_count"],
                },
            )
            for ch in channel_stats_qs
        ]

        # Get available users and channels for filters (with better queries)
        available_users = (
            DiscordUser.objects.filter(message_stats__channel__guild=guild)
            .distinct()
            .order_by("username")
            .only("user_id", "username")
        )

        available_channels = (
            DiscordChannel.objects.filter(guild=guild, message_stats__isnull=False)
            .distinct()
            .order_by("name")
            .only("channel_id", "name")
        )

        # Get recent collection jobs
        recent_jobs = StatisticsCollectionJob.objects.filter(guild=guild).order_by(
            "-created_at"
        )[:5]

        # Calculate average messages per user
        total_messages = totals["total_messages"] or 0
        total_users = totals["total_users"] or 0
        avg_messages_per_user = (
            round(total_messages / total_users) if total_users > 0 else 0
        )

        context = {
            "guild": guild,
            "user_stats": user_stats_list,
            "channel_stats": channel_stats_list,
            "total_messages": total_messages,
            "total_users": total_users,
            "total_channels": totals["total_channels"] or 0,
            "avg_messages_per_user": avg_messages_per_user,
            "available_users": available_users,
            "available_channels": available_channels,
            "selected_user_id": selected_user_id,
            "selected_channel_id": selected_channel_id,
            "time_range": time_range,
            "recent_jobs": recent_jobs,
        }

        # Cache the results using configurable timeout to improve performance
        cache_timeout = getattr(settings, "USER_STATS_CACHE_TIMEOUT", 300)
        cache.set(cache_key_with_filters, context, cache_timeout)

        return render(request, "user_stats/guild_stats.html", context)

    except DiscordAPIError as e:
        messages.error(request, f"Error accessing Discord data: {e}")
        return redirect("user_stats:dashboard")


@login_required
def user_detail_stats(request, guild_id, user_id):
    """Display detailed statistics for a specific user in a guild with caching."""
    try:
        # Check cache first
        cache_key = f"user_detail_{guild_id}_{user_id}_{request.user.id}"
        cached_data = cache.get(cache_key)

        if cached_data:
            return render(request, "user_stats/user_detail.html", cached_data)

        # Verify access
        user_guilds = get_user_guilds(request.user)
        user_guild_ids = [int(guild["id"]) for guild in user_guilds]

        if guild_id not in user_guild_ids:
            raise Http404("Access denied")  # noqa: TRY003

        guild = get_object_or_404(DiscordGuild, guild_id=str(guild_id))
        user = get_object_or_404(DiscordUser, user_id=str(user_id))

        # Get user's statistics for this guild with optimized query
        user_stats = (
            MessageStatistics.objects.select_related("channel")
            .filter(user=user, channel__guild=guild)
            .order_by("-total_messages")
        )

        # Use database aggregation for totals (much faster)
        totals = user_stats.aggregate(
            total_messages=Sum("total_messages"),
            messages_7d=Sum("messages_last_7_days"),
            messages_30d=Sum("messages_last_30_days"),
            messages_90d=Sum("messages_last_90_days"),
        )

        # Get chart data for visualization (only fetch needed fields)
        chart_data_query = user_stats.values(
            "channel__name",
            "total_messages",
            "messages_last_7_days",
            "messages_last_30_days",
            "messages_last_90_days",
        )

        chart_data = {
            "channels": [f"#{stat['channel__name']}" for stat in chart_data_query],
            "messages": [stat["total_messages"] for stat in chart_data_query],
            "messages_7d": [stat["messages_last_7_days"] for stat in chart_data_query],
            "messages_30d": [
                stat["messages_last_30_days"] for stat in chart_data_query
            ],
            "messages_90d": [
                stat["messages_last_90_days"] for stat in chart_data_query
            ],
        }

        context = {
            "guild": guild,
            "target_user": user,
            "user_stats": user_stats,
            "total_messages": totals["total_messages"] or 0,
            "messages_7d": totals["messages_7d"] or 0,
            "messages_30d": totals["messages_30d"] or 0,
            "messages_90d": totals["messages_90d"] or 0,
            "chart_data": json.dumps(chart_data),
        }

        # Cache using configurable timeout to improve performance
        cache_timeout = getattr(settings, "USER_STATS_CACHE_TIMEOUT", 300)
        cache.set(cache_key, context, cache_timeout)

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


def clear_user_stats_cache(user, guild_id=None):
    """Clear cached statistics data for a specific user.

    Args:
        user: Django user object to clear cache for
        guild_id: Optional guild ID to clear specific guild cache, or None for all
    """
    if guild_id:
        # Clear specific guild caches
        cache.delete(f"guild_stats_{guild_id}_{user.id}")
        cache.delete(f"user_detail_{guild_id}_{user.id}")
        # Clear all possible filter combinations (this is approximate)
        for i in range(100):  # Clear potential hash variants
            cache.delete(f"guild_stats_{guild_id}_{user.id}_{i}")
    else:
        # Clear dashboard cache
        cache.delete(f"user_stats_dashboard_{user.id}")
        # For complete clearing, you might want to use cache patterns if your backend supports it
