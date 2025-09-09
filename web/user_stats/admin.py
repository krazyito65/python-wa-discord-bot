"""
Django admin configuration for user statistics models.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import (
    DiscordChannel,
    DiscordGuild,
    DiscordUser,
    MessageStatistics,
    StatisticsCollectionJob,
)


@admin.register(DiscordUser)
class DiscordUserAdmin(admin.ModelAdmin):
    """Admin interface for Discord users."""

    list_display = ["username", "display_name", "user_id", "first_seen", "last_updated"]
    list_filter = ["first_seen", "last_updated"]
    search_fields = ["username", "display_name", "user_id"]
    readonly_fields = ["user_id", "first_seen", "last_updated"]
    ordering = ["username"]


@admin.register(DiscordGuild)
class DiscordGuildAdmin(admin.ModelAdmin):
    """Admin interface for Discord guilds."""

    list_display = ["name", "guild_id", "first_seen", "last_updated"]
    list_filter = ["first_seen", "last_updated"]
    search_fields = ["name", "guild_id"]
    readonly_fields = ["guild_id", "first_seen", "last_updated"]
    ordering = ["name"]


@admin.register(DiscordChannel)
class DiscordChannelAdmin(admin.ModelAdmin):
    """Admin interface for Discord channels."""

    list_display = ["name", "guild", "channel_type", "channel_id", "first_seen"]
    list_filter = ["guild", "channel_type", "first_seen"]
    search_fields = ["name", "channel_id", "guild__name"]
    readonly_fields = ["channel_id", "first_seen", "last_updated"]
    ordering = ["guild__name", "name"]


@admin.register(MessageStatistics)
class MessageStatisticsAdmin(admin.ModelAdmin):
    """Admin interface for message statistics."""

    list_display = [
        "user",
        "channel",
        "total_messages",
        "messages_last_7_days",
        "messages_last_30_days",
        "last_message_date",
        "last_collected",
    ]
    list_filter = [
        "channel__guild",
        "channel",
        "collection_method",
        "last_collected",
        "last_message_date",
    ]
    search_fields = [
        "user__username",
        "user__display_name",
        "channel__name",
        "channel__guild__name",
    ]
    readonly_fields = ["last_collected"]
    ordering = ["-total_messages"]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("user", "channel", "channel__guild")
        )


@admin.register(StatisticsCollectionJob)
class StatisticsCollectionJobAdmin(admin.ModelAdmin):
    """Admin interface for statistics collection jobs."""

    list_display = [
        "id",
        "guild",
        "target_user",
        "status",
        "progress_display",
        "created_at",
        "completed_at",
    ]
    list_filter = ["status", "guild", "created_at", "completed_at"]
    search_fields = ["guild__name", "target_user__username"]
    readonly_fields = [
        "created_at",
        "started_at",
        "completed_at",
        "progress_current",
        "progress_total",
        "messages_processed",
        "users_updated",
    ]
    ordering = ["-created_at"]

    def progress_display(self, obj):
        """Display progress as a percentage bar."""
        if obj.progress_total == 0:
            return "Not started"

        percentage = obj.progress_percentage
        color = (
            "success"
            if obj.status == "completed"
            else "primary"
            if obj.status == "running"
            else "secondary"
        )

        return format_html(
            '<div class="progress" style="width: 100px;">'
            '<div class="progress-bar bg-{}" role="progressbar" style="width: {}%" '
            'aria-valuenow="{}" aria-valuemin="0" aria-valuemax="100">'
            "{}%</div></div>",
            color,
            percentage,
            percentage,
            int(percentage),
        )

    progress_display.short_description = "Progress"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("guild", "target_user")
