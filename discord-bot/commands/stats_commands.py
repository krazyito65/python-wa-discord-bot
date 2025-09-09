"""
User Statistics Collection Commands

This module provides Discord slash commands for collecting and managing
user message statistics from Discord channels.
"""

import asyncio
from datetime import datetime, timedelta

import discord
from bot.weakauras_bot import WeakAurasBot
from discord import app_commands
from utils.logging import get_logger, log_command

# Import stats service
try:
    from services.stats_service import stats_service

    STATS_SERVICE_AVAILABLE = True
except ImportError:
    STATS_SERVICE_AVAILABLE = False
    print("Warning: Stats service not available")

logger = get_logger(__name__)


class StatsCollector:
    """Service class for collecting user message statistics."""

    def __init__(self, bot: WeakAurasBot):
        self.bot = bot
        self.active_jobs = {}  # Track active collection jobs

    async def collect_user_stats(  # noqa: PLR0912, PLR0915
        self,
        guild: discord.Guild,
        target_user: discord.Member = None,
        channels: list[discord.TextChannel] = None,
        days_back: int = None,
        job_id: str = None,
    ) -> dict:
        """
        Collect message statistics for user(s) in specified channels.

        Args:
            guild: Discord guild to scan
            target_user: Specific user to collect stats for (None = all users)
            channels: List of channels to scan (None = all text channels)
            days_back: Number of days to look back (None = all time)
            job_id: Unique job identifier for progress tracking

        Returns:
            dict: Collection results with statistics
        """
        try:
            # Mark job as running
            if job_id:
                self.active_jobs[job_id] = {
                    "status": "running",
                    "progress": 0,
                    "total": 0,
                    "started_at": datetime.now(),
                    "messages_processed": 0,
                    "users_found": set(),
                }

            # Get channels to scan
            if channels is None:
                channels = [
                    ch
                    for ch in guild.text_channels
                    if ch.permissions_for(guild.me).read_message_history
                ]

            # Calculate cutoff date
            cutoff_date = None
            if days_back is not None:
                cutoff_date = datetime.now() - timedelta(days=days_back)

            # Initialize result structure
            results = {
                "guild_id": guild.id,
                "guild_name": guild.name,
                "channels_scanned": len(channels),
                "total_messages": 0,
                "unique_users": set(),
                "user_stats": {},  # user_id -> {channel_id: count, ...}
                "channel_stats": {},  # channel_id -> {user_id: count, ...}
                "time_range": f"{days_back} days" if days_back else "all time",
                "collection_start": datetime.now(),
            }

            # Update job progress
            if job_id:
                self.active_jobs[job_id]["total"] = len(channels)

            logger.info(
                f"Starting statistics collection for {guild.name} ({len(channels)} channels)"
            )

            # Scan each channel
            for channel_idx, channel in enumerate(channels):
                try:
                    logger.info(
                        f"Scanning channel #{channel.name} ({channel_idx + 1}/{len(channels)})"
                    )

                    # Initialize channel stats
                    channel_user_counts = {}
                    channel_message_count = 0

                    # Track message timestamps for time-based statistics
                    channel_user_messages = {}  # user_id -> list of message timestamps

                    # Scan messages in channel
                    async for message in channel.history(
                        limit=None, after=cutoff_date, oldest_first=False
                    ):
                        # Skip if targeting specific user and this isn't them
                        if target_user and message.author.id != target_user.id:
                            continue

                        # Skip bot messages
                        if message.author.bot:
                            continue

                        # Convert Discord timestamp to datetime
                        message_datetime = message.created_at.replace(tzinfo=None)

                        # Count message for this user in this channel
                        user_id = message.author.id
                        channel_user_counts[user_id] = (
                            channel_user_counts.get(user_id, 0) + 1
                        )
                        channel_message_count += 1

                        # Track message timestamps for time-based stats
                        if user_id not in channel_user_messages:
                            channel_user_messages[user_id] = []
                        channel_user_messages[user_id].append(message_datetime)

                        # Update global user stats
                        if user_id not in results["user_stats"]:
                            results["user_stats"][user_id] = {
                                "username": message.author.display_name,
                                "avatar_url": str(message.author.avatar.url)
                                if message.author.avatar
                                else "",
                                "channels": {},
                                "total_messages": 0,
                                "message_timestamps": [],  # Track all message timestamps
                            }

                        results["user_stats"][user_id]["channels"][channel.id] = (
                            channel_user_counts[user_id]
                        )
                        results["user_stats"][user_id]["total_messages"] = (
                            results["user_stats"][user_id].get("total_messages", 0) + 1
                        )
                        results["user_stats"][user_id]["message_timestamps"].append(
                            message_datetime
                        )

                        # Track unique users
                        results["unique_users"].add(user_id)

                        # Update job progress
                        if job_id:
                            self.active_jobs[job_id]["messages_processed"] += 1

                    # Store channel stats with timestamp information
                    results["channel_stats"][channel.id] = {
                        "name": channel.name,
                        "total_messages": channel_message_count,
                        "user_counts": channel_user_counts,
                        "user_messages": channel_user_messages,  # Include timestamps per user
                    }

                    results["total_messages"] += channel_message_count

                    logger.info(
                        f"Channel #{channel.name}: {channel_message_count} messages from {len(channel_user_counts)} users"
                    )

                except discord.Forbidden:
                    logger.warning(f"No permission to read history in #{channel.name}")
                except Exception:
                    logger.exception(f"Error scanning channel #{channel.name}")

                # Update job progress
                if job_id:
                    self.active_jobs[job_id]["progress"] = channel_idx + 1
                    self.active_jobs[job_id]["users_found"] = results[
                        "unique_users"
                    ].copy()

                # Save progressive data to Django after each channel
                if (
                    STATS_SERVICE_AVAILABLE and (channel_idx + 1) % 1 == 0
                ):  # Save after every channel
                    try:
                        # Create a copy of current results for saving
                        partial_results = results.copy()
                        partial_results["collection_end"] = datetime.now()
                        partial_results["collection_duration"] = (
                            partial_results["collection_end"]
                            - partial_results["collection_start"]
                        )
                        partial_results["unique_users"] = len(
                            partial_results["unique_users"]
                        )
                        partial_results["is_partial"] = True
                        partial_results["channels_completed"] = channel_idx + 1

                        saved = await stats_service.save_statistics_to_django_async(
                            partial_results, job_id
                        )
                        if saved:
                            logger.info(
                                f"Progressive data saved after channel {channel_idx + 1}/{len(channels)}"
                            )
                    except Exception:
                        logger.exception("Error saving progressive data")

            results["collection_end"] = datetime.now()
            results["collection_duration"] = (
                results["collection_end"] - results["collection_start"]
            )
            results["unique_users"] = len(results["unique_users"])

            # Save to Django database if available
            if STATS_SERVICE_AVAILABLE:
                try:
                    saved = await stats_service.save_statistics_to_django_async(
                        results, job_id
                    )
                    if saved:
                        logger.info("Statistics saved to Django database")
                    else:
                        logger.warning("Failed to save statistics to Django database")
                except Exception:
                    logger.exception("Error saving to Django")

            # Mark job as completed
            if job_id:
                self.active_jobs[job_id]["status"] = "completed"
                self.active_jobs[job_id]["completed_at"] = datetime.now()

            logger.info(
                f"Collection complete: {results['total_messages']} messages from "
                f"{results['unique_users']} users across {results['channels_scanned']} channels"
            )

        except Exception as e:
            logger.exception("Error during statistics collection")
            if job_id:
                self.active_jobs[job_id]["status"] = "failed"
                self.active_jobs[job_id]["error"] = str(e)
            raise
        else:
            return results

    def get_job_status(self, job_id: str) -> dict:
        """Get status of a collection job."""
        return self.active_jobs.get(job_id, {"status": "not_found"})

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a running collection job."""
        if job_id in self.active_jobs:
            self.active_jobs[job_id]["status"] = "cancelled"
            return True
        return False


def setup_stats_commands(bot: WeakAurasBot):  # noqa: PLR0915
    """Setup all user statistics slash commands."""

    # Initialize stats collector
    stats_collector = StatsCollector(bot)

    @bot.tree.command(
        name="collect_user_stats",
        description="Collect message statistics for users in this server",
    )
    @app_commands.describe(
        user="Specific user to collect stats for (leave empty for all users)",
        days_back="Number of days to look back (leave empty for all time)",
        channels="Comma-separated list of channel names to scan (leave empty for all channels)",
    )
    @log_command
    async def collect_user_stats(
        interaction: discord.Interaction,
        user: discord.Member = None,
        days_back: int = None,
        channels: str = None,
    ):
        """Collect user message statistics for the current server."""

        if not interaction.guild:
            await interaction.response.send_message(
                "❌ This command can only be used in a server.", ephemeral=True
            )
            return

        # Check permissions
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message(
                "❌ You need 'Manage Messages' permission to collect user statistics.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        try:
            # Parse channels if specified
            target_channels = None
            if channels:
                channel_names = [
                    name.strip().lstrip("#") for name in channels.split(",")
                ]
                target_channels = []
                for name in channel_names:
                    channel = discord.utils.get(
                        interaction.guild.text_channels, name=name
                    )
                    if channel:
                        target_channels.append(channel)
                    else:
                        await interaction.followup.send(
                            f"⚠️ Channel '{name}' not found or not accessible.",
                            ephemeral=True,
                        )
                        return

            # Generate job ID
            job_id = f"{interaction.guild.id}_{interaction.user.id}_{int(datetime.now().timestamp())}"

            # Start collection (this will run in background)
            asyncio.create_task(
                stats_collector.collect_user_stats(
                    guild=interaction.guild,
                    target_user=user,
                    channels=target_channels,
                    days_back=days_back,
                    job_id=job_id,
                )
            )

            # Send initial response
            embed = discord.Embed(
                title="📊 User Statistics Collection Started",
                description="Collection job has been started in the background.",
                color=bot.config.get("bot", {}).get("brand_color", 0x9F4AF3),
            )

            if user:
                embed.add_field(name="Target User", value=user.mention, inline=True)
            if days_back:
                embed.add_field(
                    name="Time Range", value=f"{days_back} days", inline=True
                )
            if target_channels:
                embed.add_field(
                    name="Channels",
                    value=f"{len(target_channels)} channel(s)",
                    inline=True,
                )

            embed.add_field(name="Job ID", value=f"`{job_id}`", inline=False)
            embed.add_field(
                name="Progress",
                value="Use `/stats_progress` to check progress",
                inline=False,
            )

            embed.set_footer(text="This may take several minutes for large servers...")

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.exception("Error starting stats collection")
            await interaction.followup.send(
                f"❌ Error starting statistics collection: {e}", ephemeral=True
            )

    @bot.tree.command(
        name="stats_progress",
        description="Check progress of a statistics collection job",
    )
    @app_commands.describe(job_id="Job ID from the collect_user_stats command")
    @log_command
    async def stats_progress(interaction: discord.Interaction, job_id: str):
        """Check the progress of a statistics collection job."""

        status = stats_collector.get_job_status(job_id)

        if status["status"] == "not_found":
            await interaction.response.send_message(
                f"❌ Job ID `{job_id}` not found.", ephemeral=True
            )
            return

        embed = discord.Embed(
            title="📊 Statistics Collection Progress",
            color=bot.config.get("bot", {}).get("brand_color", 0x9F4AF3),
        )

        embed.add_field(name="Job ID", value=f"`{job_id}`", inline=False)
        embed.add_field(name="Status", value=status["status"].title(), inline=True)

        if status["status"] == "running":
            progress_pct = (
                (status["progress"] / status["total"] * 100)
                if status["total"] > 0
                else 0
            )
            embed.add_field(
                name="Progress",
                value=f"{status['progress']}/{status['total']} channels ({progress_pct:.1f}%)",
                inline=True,
            )
            embed.add_field(
                name="Messages Processed",
                value=f"{status['messages_processed']:,}",
                inline=True,
            )
            embed.add_field(
                name="Users Found", value=f"{len(status['users_found'])}", inline=True
            )

            # Calculate estimated time remaining
            if status["progress"] > 0:
                elapsed = datetime.now() - status["started_at"]
                estimated_total = elapsed * status["total"] / status["progress"]
                remaining = estimated_total - elapsed
                embed.add_field(
                    name="Estimated Time Remaining",
                    value=f"{remaining.seconds // 60}m {remaining.seconds % 60}s",
                    inline=True,
                )

        elif status["status"] == "completed":
            embed.add_field(
                name="Messages Processed",
                value=f"{status['messages_processed']:,}",
                inline=True,
            )
            embed.add_field(
                name="Users Found", value=f"{len(status['users_found'])}", inline=True
            )
            duration = status["completed_at"] - status["started_at"]
            embed.add_field(
                name="Duration",
                value=f"{duration.seconds // 60}m {duration.seconds % 60}s",
                inline=True,
            )
            embed.add_field(
                name="Next Steps",
                value="View results on the web interface at your server's stats page.",
                inline=False,
            )

        elif status["status"] == "failed":
            embed.add_field(
                name="Error", value=status.get("error", "Unknown error"), inline=False
            )
            embed.color = discord.Color.red()

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.tree.command(
        name="cancel_stats_job",
        description="Cancel a running statistics collection job",
    )
    @app_commands.describe(job_id="Job ID to cancel")
    @log_command
    async def cancel_stats_job(interaction: discord.Interaction, job_id: str):
        """Cancel a running statistics collection job."""

        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message(
                "❌ You need 'Manage Messages' permission to cancel statistics jobs.",
                ephemeral=True,
            )
            return

        success = stats_collector.cancel_job(job_id)

        if success:
            await interaction.response.send_message(
                f"✅ Job `{job_id}` has been cancelled.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"❌ Job ID `{job_id}` not found or already completed.", ephemeral=True
            )

    logger.info("User statistics commands registered")
