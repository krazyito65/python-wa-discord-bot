"""
Django management command to set up Discord OAuth configuration.

This command reads Discord OAuth credentials from the bot's token.yml file
and creates/updates the necessary SocialApp record in Django's database.
"""

from pathlib import Path

import yaml
from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    """Management command to set up Discord OAuth SocialApp configuration."""

    help = "Set up Discord OAuth configuration from bot config file"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--config-path",
            type=str,
            help="Path to the bot config file (default: ../discord-bot/settings/token.yml)",
        )

    def handle(self, *args, **options):  # noqa: ARG002
        """Execute the command."""
        # Determine config file path
        if options["config_path"]:
            config_path = Path(options["config_path"])
        else:
            # Default path relative to the Django project
            config_path = (
                Path(__file__).resolve().parent.parent.parent.parent.parent
                / "discord-bot"
                / "settings"
                / "token.yml"
            )

        # Check if config file exists
        if not config_path.exists():
            msg = f"Bot config file not found: {config_path}"
            raise CommandError(msg) from None

        # Load configuration
        try:
            with open(config_path) as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            msg = f"Error parsing config file: {e}"
            raise CommandError(msg) from e

        # Extract Discord OAuth credentials
        discord_config = config.get("discord", {})
        oauth_config = discord_config.get("oauth", {})

        client_id = oauth_config.get("client_id")
        client_secret = oauth_config.get("client_secret")

        if not client_id or not client_secret:
            msg = (
                "Discord OAuth credentials not found in config file. "
                "Expected: discord.oauth.client_id and discord.oauth.client_secret"
            )
            raise CommandError(msg) from None

        # Get the default site
        try:
            site = Site.objects.get(pk=1)
        except Site.DoesNotExist:
            msg = "Default site not found. Run 'python manage.py migrate' first."
            raise CommandError(msg) from None

        # Create or update Discord SocialApp
        discord_app, created = SocialApp.objects.get_or_create(
            provider="discord",
            defaults={
                "name": "Discord OAuth",
                "client_id": client_id,
                "secret": client_secret,
            },
        )

        # Associate with the site
        discord_app.sites.add(site)

        if created:
            self.stdout.write(
                self.style.SUCCESS("✓ Created Discord SocialApp configuration")
            )
        else:
            # Update existing app
            discord_app.client_id = client_id
            discord_app.secret = client_secret
            discord_app.save()
            self.stdout.write(
                self.style.SUCCESS("✓ Updated Discord SocialApp configuration")
            )

        self.stdout.write(f"Discord App: {discord_app.name}")
        self.stdout.write(f"Client ID: {discord_app.client_id}")
        self.stdout.write(f"Associated with site: {site.domain}")
