"""
Views for user statistics display and management.

This module provides web views for displaying Discord user message statistics
collected from various channels within Discord servers.
"""

import json
import logging
import time

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
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


def _get_message_field_for_time_range(time_range: str) -> str:
    """Get the appropriate message field name for the given time range."""
    time_range_fields = {
        "7d": "messages_last_7_days",
        "30d": "messages_last_30_days",
        "90d": "messages_last_90_days",
    }
    return time_range_fields.get(time_range, "total_messages")


def _build_base_queryset(
    guild, message_field: str, selected_user_ids=None, selected_channel_ids=None
):
    """Build the base queryset for message statistics with filters applied."""
    base_queryset = MessageStatistics.objects.select_related("user", "channel").filter(
        channel__guild=guild,
        **{
            f"{message_field}__gt": 0
        },  # Only include records with messages in time range
    )

    # Apply filters for multiple users and channels
    if selected_user_ids:
        user_ids = [uid for uid in selected_user_ids if uid]  # Remove empty values
        if user_ids:
            base_queryset = base_queryset.filter(user__user_id__in=user_ids)

    if selected_channel_ids:
        channel_ids = [cid for cid in selected_channel_ids if cid]  # Remove empty values
        if channel_ids:
            base_queryset = base_queryset.filter(channel__channel_id__in=channel_ids)

    return base_queryset


def _get_period_field(period):
    """Get the database field name for a given time period."""
    period_fields = {
        "7d": "messages_last_7_days",
        "30d": "messages_last_30_days",
        "90d": "messages_last_90_days",
        "all": "total_messages",
    }
    return period_fields.get(period, "messages_last_7_days")


def _determine_activity_level(user_stats, _sort_period):
    """Determine user activity level based on recent message counts."""
    if user_stats.get("messages_7d", 0) > 0:
        return "active_7d"
    if user_stats.get("messages_30d", 0) > 0:
        return "active_30d"
    if user_stats.get("messages_90d", 0) > 0:
        return "active_90d"
    return "inactive"


def _get_multi_user_channel_data(guild, selected_user_ids, sort_period, show_channels, activity_filter):
    """Get optimized channel statistics for multiple users."""
    users_data = {}

    # Single optimized query for all users and their channels
    base_queryset = MessageStatistics.objects.select_related(
        "user", "channel"
    ).filter(
        user__user_id__in=selected_user_ids,
        channel__guild=guild
    )

    # Group data by user for efficient processing
    for stat in base_queryset:
        user_id = stat.user.user_id

        if user_id not in users_data:
            users_data[user_id] = {
                "user": stat.user,
                "channels": [],
                "total_stats": {
                    "total_messages": 0,
                    "messages_7d": 0,
                    "messages_30d": 0,
                    "messages_90d": 0,
                    "channel_count": 0,
                },
                "activity_level": "inactive",
            }

        # Add channel data
        users_data[user_id]["channels"].append({
            "channel": stat.channel,
            "total_messages": stat.total_messages,
            "messages_7d": stat.messages_last_7_days,
            "messages_30d": stat.messages_last_30_days,
            "messages_90d": stat.messages_last_90_days,
            "last_message_date": stat.last_message_date,
        })

        # Accumulate totals
        totals = users_data[user_id]["total_stats"]
        totals["total_messages"] += stat.total_messages
        totals["messages_7d"] += stat.messages_last_7_days
        totals["messages_30d"] += stat.messages_last_30_days
        totals["messages_90d"] += stat.messages_last_90_days
        totals["channel_count"] += 1

    # Sort channels and determine activity levels for each user
    for _user_id, data in users_data.items():
        # Sort channels by the selected period
        period_field = f"messages_{sort_period}" if sort_period != "all" else "total_messages"
        data["channels"].sort(key=lambda x: x[period_field], reverse=True)

        # Limit channels if requested
        if show_channels == "top5":
            data["channels"] = data["channels"][:5]
        elif show_channels == "top10":
            data["channels"] = data["channels"][:10]

        # Determine activity level
        data["activity_level"] = _determine_activity_level(data["total_stats"], sort_period)

    # Apply activity filter
    if activity_filter != "all":
        users_data = {
            user_id: data for user_id, data in users_data.items()
            if (activity_filter == "recent" and data["activity_level"] in ["active_7d", "active_30d"])
            or (activity_filter == "active_7d" and data["activity_level"] == "active_7d")
            or (activity_filter == "active_30d" and data["activity_level"] in ["active_7d", "active_30d"])
        }

    return users_data


def _sort_users_by_activity(users_data, sort_period):
    """Sort users by their activity in the selected period."""
    period_field = f"messages_{sort_period}" if sort_period != "all" else "total_messages"

    sorted_items = sorted(
        users_data.items(),
        key=lambda item: item[1]["total_stats"][period_field],
        reverse=True
    )

    # Convert back to OrderedDict-like structure for template
    return dict(sorted_items)


def _get_user_statistics(base_queryset, message_field: str):
    """Get user statistics with efficient aggregation."""
    # Get total counts
    totals = base_queryset.aggregate(
        total_messages=Sum(message_field),
        total_users=Count("user", distinct=True),
        total_channels=Count("channel", distinct=True),
    )

    # Get user statistics with efficient aggregation (no per-user channel breakdown)
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
        )
        .order_by("-total_messages")[:50]  # Limit to top 50 users for performance
    )

    # Get top channel for each user efficiently
    user_ids = [user_stat["user__user_id"] for user_stat in user_stats_qs]
    top_channels_qs = (
        base_queryset.filter(user__user_id__in=user_ids)
        .values("user__user_id", "channel__name")
        .annotate(messages=Sum(message_field))
        .order_by("user__user_id", "-messages")
    )

    # Group top channels by user
    top_channels_by_user = {}
    for tc in top_channels_qs:
        user_id = tc["user__user_id"]
        if user_id not in top_channels_by_user:
            top_channels_by_user[user_id] = {
                "name": tc["channel__name"],
                "messages": tc["messages"],
            }

    # Convert to format expected by template
    user_stats_list = []
    for user_stat in user_stats_qs:
        user_id = user_stat["user__user_id"]
        top_channel = top_channels_by_user.get(user_id, {"name": "N/A", "messages": 0})

        user_stats_list.append(
            (
                user_id,
                {
                    "user": {
                        "user_id": user_id,
                        "username": user_stat["user__username"],
                        "display_name": user_stat["user__display_name"]
                        or user_stat["user__username"],
                        "avatar_url": user_stat["user__avatar_url"],
                    },
                    "total_messages": user_stat["total_messages"],
                    "channel_count": user_stat["channel_count"],
                    "top_channel": top_channel,
                    "channels": {},  # Empty for now to avoid N+1 queries
                },
            )
        )

    return totals, user_stats_list


def _get_channel_statistics(base_queryset, message_field: str):
    """Get channel statistics efficiently."""
    channel_stats_qs = (
        base_queryset.values("channel__channel_id", "channel__name")
        .annotate(
            total_messages=Sum(message_field),
            user_count=Count("user", distinct=True),
        )
        .order_by("-total_messages")[:20]  # Limit to top 20 channels for performance
    )

    return [
        (
            ch["channel__channel_id"],
            {
                "channel": {
                    "channel_id": ch["channel__channel_id"],
                    "name": ch["channel__name"],
                },
                "total_messages": ch["total_messages"],
                "user_count": ch["user_count"],
            },
        )
        for ch in channel_stats_qs
    ]


def _get_available_users(guild):
    """Get list of users with message statistics for filter dropdown."""
    # Get users ordered by total message count for better relevance
    return (
        DiscordUser.objects.filter(message_stats__channel__guild=guild)
        .distinct()
        .annotate(total_message_count=Sum("message_stats__total_messages"))
        .order_by("-total_message_count", "display_name", "username")
        .only("user_id", "username", "display_name")
        # Order by activity level - most active users first for better UX
    )


def _get_available_channels(guild):
    """Get list of channels with message statistics for filter dropdown."""
    # Order channels by total message count for better relevance
    return (
        DiscordChannel.objects.filter(guild=guild, message_stats__isnull=False)
        .distinct()
        .annotate(total_message_count=Sum("message_stats__total_messages"))
        .order_by("-total_message_count", "name")
        .only("channel_id", "name")
        # Order by activity level - most active channels first for better UX
    )


@login_required
def guild_user_stats(request, guild_id):
    """Display user statistics for a specific guild with optimized database queries."""
    logger = logging.getLogger(__name__)
    start_time = time.time()

    try:
        logger.debug(f"Starting guild_user_stats for guild_id: {guild_id}")
        # Check cache first for performance
        cache_key = f"guild_stats_{guild_id}_{request.user.id}"
        filter_params = {
            "user": request.GET.getlist("user"),  # Handle multiple users
            "channel": request.GET.getlist("channel"),  # Handle multiple channels
            "time_range": request.GET.get("time_range", "all"),
        }

        # Create cache key that includes filters
        cache_key_with_filters = (
            f"{cache_key}_{hash(str(sorted(filter_params.items())))}"
        )
        cached_data = cache.get(cache_key_with_filters)

        if cached_data:
            logger.debug("Cache hit for guild_stats - returning cached data")
            return render(request, "user_stats/guild_stats.html", cached_data)

        logger.debug(
            f"Cache miss - starting fresh query. Time elapsed: {time.time() - start_time:.3f}s"
        )

        # Verify user has access to this guild
        discord_start = time.time()
        user_guilds = get_user_guilds(request.user)
        user_guild_ids = [int(guild["id"]) for guild in user_guilds]
        logger.debug(
            f"Discord API call completed in: {time.time() - discord_start:.3f}s"
        )

        if guild_id not in user_guild_ids:
            raise Http404("Access denied")  # noqa: TRY003

        # Get guild and its statistics
        guild = get_object_or_404(DiscordGuild, guild_id=str(guild_id))

        # Get filter parameters
        selected_user_ids = filter_params["user"]  # Now a list
        selected_channel_ids = filter_params["channel"]  # Now a list
        time_range = filter_params["time_range"]

        # Determine message field and build base queryset
        message_field = _get_message_field_for_time_range(time_range)
        base_queryset = _build_base_queryset(
            guild, message_field, selected_user_ids, selected_channel_ids
        )

        # Get statistics using helper functions
        totals, user_stats_list = _get_user_statistics(base_queryset, message_field)
        channel_stats_list = _get_channel_statistics(base_queryset, message_field)

        # Get filter dropdown data
        available_users = _get_available_users(guild)
        available_channels = _get_available_channels(guild)
        recent_jobs = []  # Keep minimal for now

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
            "selected_user_ids": selected_user_ids,
            "selected_channel_ids": selected_channel_ids,
            "time_range": time_range,
            "recent_jobs": recent_jobs,
        }

        # Cache the results using configurable timeout to improve performance
        cache_timeout = getattr(settings, "USER_STATS_CACHE_TIMEOUT", 300)
        cache.set(cache_key_with_filters, context, cache_timeout)

        total_time = time.time() - start_time
        logger.debug(f"guild_user_stats completed in: {total_time:.3f}s")

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
def multi_user_channel_stats(request, guild_id):
    """Display detailed channel statistics for multiple selected users with activity sorting."""
    try:
        # Check cache first
        selected_user_ids = request.GET.getlist("user")
        sort_period = request.GET.get("sort_period", "7d")
        show_channels = request.GET.get("show_channels", "top5")
        activity_filter = request.GET.get("activity_filter", "all")

        cache_key = f"multi_user_stats_{guild_id}_{'-'.join(selected_user_ids)}_{sort_period}_{show_channels}_{activity_filter}_{request.user.id}"
        cached_data = cache.get(cache_key)

        if cached_data:
            return render(request, "user_stats/multi_user_stats.html", cached_data)

        # Verify access
        user_guilds = get_user_guilds(request.user)
        user_guild_ids = [int(guild["id"]) for guild in user_guilds]

        if guild_id not in user_guild_ids:
            raise Http404("Access denied")

        guild = get_object_or_404(DiscordGuild, guild_id=str(guild_id))

        # Get all available users for the dropdown (reuse existing logic)
        available_users = (
            DiscordUser.objects.filter(
                message_stats__channel__guild=guild
            ).distinct().order_by("display_name", "username")
        )

        # If no users selected, default to top 10 most active users in selected period
        if not selected_user_ids or not any(uid for uid in selected_user_ids if uid):
            period_field = _get_period_field(sort_period)
            top_users = (
                MessageStatistics.objects
                .filter(channel__guild=guild)
                .values("user__user_id")
                .annotate(total_period_messages=Sum(period_field))
                .filter(total_period_messages__gt=0)
                .order_by("-total_period_messages")[:10]
            )
            selected_user_ids = [str(user["user__user_id"]) for user in top_users]

        # Remove empty values from selected users
        selected_user_ids = [uid for uid in selected_user_ids if uid]

        if not selected_user_ids:
            # No valid users selected, show empty state
            context = {
                "guild": guild,
                "available_users": available_users,
                "selected_user_ids": [],
                "users_data": {},
                "sort_period": sort_period,
                "show_channels": show_channels,
                "activity_filter": activity_filter,
                "total_users": 0,
            }
            return render(request, "user_stats/multi_user_stats.html", context)

        # Get multi-user channel statistics with optimized query
        users_data = _get_multi_user_channel_data(
            guild, selected_user_ids, sort_period, show_channels, activity_filter
        )

        # Sort users by activity in the selected period
        sorted_users_data = _sort_users_by_activity(users_data, sort_period)

        context = {
            "guild": guild,
            "available_users": available_users,
            "selected_user_ids": selected_user_ids,
            "users_data": sorted_users_data,
            "sort_period": sort_period,
            "show_channels": show_channels,
            "activity_filter": activity_filter,
            "total_users": len(sorted_users_data),
        }

        # Cache the results
        cache_timeout = getattr(settings, "USER_STATS_CACHE_TIMEOUT", 300)
        cache.set(cache_key, context, cache_timeout)

        return render(request, "user_stats/multi_user_stats.html", context)

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
