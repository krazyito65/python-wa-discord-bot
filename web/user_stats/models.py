"""
Models for user message statistics.

This module stores Discord user message statistics collected from various
channels within Discord servers.
"""

from django.db import models
from django.utils import timezone


class DiscordUser(models.Model):
    """Discord user information."""

    user_id = models.CharField(max_length=20, unique=True, help_text="Discord user ID")
    username = models.CharField(max_length=32, help_text="Discord username")
    display_name = models.CharField(
        max_length=32, blank=True, help_text="Discord display name"
    )
    avatar_url = models.URLField(blank=True, help_text="Discord avatar URL")

    # Metadata
    first_seen = models.DateTimeField(
        default=timezone.now, help_text="First time we recorded this user"
    )
    last_updated = models.DateTimeField(
        auto_now=True, help_text="Last time user info was updated"
    )

    class Meta:
        ordering = ["username"]

    def __str__(self):
        return f"{self.display_name or self.username} ({self.user_id})"


class DiscordGuild(models.Model):
    """Discord server/guild information."""

    guild_id = models.CharField(
        max_length=20, unique=True, help_text="Discord guild ID"
    )
    name = models.CharField(max_length=100, help_text="Discord guild name")
    icon_url = models.URLField(blank=True, help_text="Discord guild icon URL")

    # Metadata
    first_seen = models.DateTimeField(
        default=timezone.now, help_text="First time we recorded this guild"
    )
    last_updated = models.DateTimeField(
        auto_now=True, help_text="Last time guild info was updated"
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.guild_id})"


class DiscordChannel(models.Model):
    """Discord channel information."""

    channel_id = models.CharField(
        max_length=20, unique=True, help_text="Discord channel ID"
    )
    guild = models.ForeignKey(
        DiscordGuild, on_delete=models.CASCADE, related_name="channels"
    )
    name = models.CharField(max_length=100, help_text="Discord channel name")
    channel_type = models.CharField(
        max_length=20,
        choices=[
            ("text", "Text Channel"),
            ("voice", "Voice Channel"),
            ("category", "Category"),
            ("news", "News Channel"),
            ("store", "Store Channel"),
            ("thread", "Thread"),
            ("forum", "Forum Channel"),
        ],
        default="text",
        help_text="Type of Discord channel",
    )

    # Metadata
    first_seen = models.DateTimeField(
        default=timezone.now, help_text="First time we recorded this channel"
    )
    last_updated = models.DateTimeField(
        auto_now=True, help_text="Last time channel info was updated"
    )

    class Meta:
        ordering = ["guild__name", "name"]

    def __str__(self):
        return f"#{self.name} ({self.guild.name})"


class MessageStatistics(models.Model):
    """User message statistics per channel."""

    user = models.ForeignKey(
        DiscordUser, on_delete=models.CASCADE, related_name="message_stats"
    )
    channel = models.ForeignKey(
        DiscordChannel, on_delete=models.CASCADE, related_name="message_stats"
    )

    # Statistics
    total_messages = models.PositiveIntegerField(
        default=0, help_text="Total messages sent in this channel"
    )
    messages_last_7_days = models.PositiveIntegerField(
        default=0, help_text="Messages sent in last 7 days"
    )
    messages_last_30_days = models.PositiveIntegerField(
        default=0, help_text="Messages sent in last 30 days"
    )
    messages_last_90_days = models.PositiveIntegerField(
        default=0, help_text="Messages sent in last 90 days"
    )

    # Time tracking
    first_message_date = models.DateTimeField(
        null=True, blank=True, help_text="Date of first message"
    )
    last_message_date = models.DateTimeField(
        null=True, blank=True, help_text="Date of most recent message"
    )

    # Metadata
    last_collected = models.DateTimeField(
        default=timezone.now, help_text="When these stats were last collected"
    )
    collection_method = models.CharField(
        max_length=20,
        choices=[
            ("full_scan", "Full Channel Scan"),
            ("incremental", "Incremental Update"),
            ("manual", "Manual Collection"),
        ],
        default="full_scan",
        help_text="How these statistics were collected",
    )

    class Meta:
        unique_together = ["user", "channel"]
        ordering = ["-total_messages"]

    def __str__(self):
        return f"{self.user.username} in {self.channel.name}: {self.total_messages} messages"


class DailyMessageStatistics(models.Model):
    """Daily message statistics per user per channel."""

    user = models.ForeignKey(
        DiscordUser, on_delete=models.CASCADE, related_name="daily_message_stats"
    )
    channel = models.ForeignKey(
        DiscordChannel, on_delete=models.CASCADE, related_name="daily_message_stats"
    )
    date = models.DateField(help_text="Date for these statistics")
    message_count = models.PositiveIntegerField(
        default=0, help_text="Number of messages sent on this date"
    )

    # Metadata
    created_at = models.DateTimeField(
        default=timezone.now, help_text="When this record was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True, help_text="When this record was last updated"
    )

    class Meta:
        unique_together = ["user", "channel", "date"]
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["user", "channel", "date"]),
            models.Index(fields=["date"]),
            models.Index(fields=["channel", "date"]),
        ]

    def __str__(self):
        return f"{self.user.username} in {self.channel.name} on {self.date}: {self.message_count} messages"


class StatisticsCollectionJob(models.Model):
    """Track statistics collection jobs."""

    guild = models.ForeignKey(
        DiscordGuild, on_delete=models.CASCADE, related_name="collection_jobs"
    )

    # Job parameters
    target_user = models.ForeignKey(
        DiscordUser,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Specific user to collect stats for (null = all users)",
    )
    target_channels = models.ManyToManyField(
        DiscordChannel,
        blank=True,
        help_text="Specific channels to scan (empty = all channels)",
    )
    time_range_days = models.PositiveIntegerField(
        null=True, blank=True, help_text="Number of days to look back (null = all time)"
    )

    # Job status
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("running", "Running"),
            ("completed", "Completed"),
            ("failed", "Failed"),
            ("cancelled", "Cancelled"),
        ],
        default="pending",
        help_text="Current status of the collection job",
    )

    # Progress tracking
    progress_current = models.PositiveIntegerField(
        default=0, help_text="Current progress"
    )
    progress_total = models.PositiveIntegerField(
        default=0, help_text="Total items to process"
    )
    error_message = models.TextField(
        blank=True, help_text="Error message if job failed"
    )

    # Timestamps
    created_at = models.DateTimeField(
        default=timezone.now, help_text="When job was created"
    )
    started_at = models.DateTimeField(
        null=True, blank=True, help_text="When job started running"
    )
    completed_at = models.DateTimeField(
        null=True, blank=True, help_text="When job completed"
    )

    # Results
    messages_processed = models.PositiveIntegerField(
        default=0, help_text="Total messages processed"
    )
    users_updated = models.PositiveIntegerField(
        default=0, help_text="Number of users updated"
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        target = (
            f"user {self.target_user.username}" if self.target_user else "all users"
        )
        return f"Collection job for {target} in {self.guild.name} ({self.status})"

    @property
    def progress_percentage(self):
        """Calculate progress percentage."""
        if self.progress_total == 0:
            return 0
        return (self.progress_current / self.progress_total) * 100
