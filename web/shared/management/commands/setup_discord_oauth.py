"""
Django management command to setup Discord OAuth from bot configuration.

This command automatically configures Discord OAuth credentials in Django
by reading them from the bot's token.yml configuration file. This ensures
the OAuth configuration stays in sync with the bot configuration.

Usage:
    python manage.py setup_discord_oauth
    python manage.py setup_discord_oauth --config-path /path/to/token.yml
"""

from pathlib import Path

import yaml
from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand, CommandError

# Constants for verbosity levels
VERBOSE_LEVEL_1 = 1
VERBOSE_LEVEL_2 = 2


class Command(BaseCommand):
    help = "Setup Discord OAuth configuration from bot token file"

    def add_arguments(self, parser):
        parser.add_argument(
            "--config-path",
            type=str,
            help="Path to token.yml file (auto-detected if not provided)",
        )
        parser.add_argument(
            "--site-domain",
            type=str,
            default="bot.weakauras.wtf",
            help="Domain for the Django site (default: bot.weakauras.wtf)",
        )

    def handle(self, **options):
        """Setup Discord OAuth configuration from bot config file."""
        self.verbosity = options["verbosity"]

        # Load bot configuration
        config = self._load_bot_config(options.get("config_path"))

        # Extract OAuth credentials
        oauth_config = config.get("discord", {}).get("oauth", {})
        if not oauth_config:
            raise CommandError("No Discord OAuth configuration found in token file")

        client_id = oauth_config.get("client_id")
        client_secret = oauth_config.get("client_secret")

        if not client_id or not client_secret:
            raise CommandError("Discord OAuth client_id and client_secret are required")

        # Update Django site
        site_domain = options["site_domain"]
        self._update_site(site_domain)

        # Setup Discord OAuth app
        self._setup_discord_oauth(client_id, client_secret, site_domain)

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Discord OAuth configured successfully:\n"
                f"   - Client ID: {client_id}\n"
                f"   - Site Domain: {site_domain}\n"
                f"   - Redirect URL: https://{site_domain}/accounts/discord/login/callback/"
            )
        )

    def _load_bot_config(self, config_path):
        """Load bot configuration from token.yml with fallback locations."""
        if config_path:
            config_file = Path(config_path)
            if not config_file.exists():
                raise CommandError(f"Config file not found: {config_path}")
        else:
            # Auto-detect config file (same logic as main.py)
            fallback_paths = [
                Path("~/.config/weakauras-bot/token.yml").expanduser(),
                Path("~/weakauras-bot-config/token.yml").expanduser(),
                Path("../discord-bot/settings/token.yml"),
                Path("discord-bot/settings/token.yml"),
            ]

            config_file = None
            for path in fallback_paths:
                if path.exists():
                    config_file = path
                    break

            if not config_file:
                raise CommandError(
                    "Bot configuration file not found. Checked:\n"
                    + "\n".join(f"  - {p}" for p in fallback_paths)
                    + "\nUse --config-path to specify the location."
                )

        if self.verbosity >= VERBOSE_LEVEL_2:
            self.stdout.write(f"Loading config from: {config_file}")

        try:
            with open(config_file) as f:
                return yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise CommandError(f"Invalid YAML in config file: {e}") from e
        except Exception as e:
            raise CommandError(f"Error reading config file: {e}") from e

    def _update_site(self, domain):
        """Update Django site configuration."""
        try:
            site = Site.objects.get(id=1)
            if site.domain != domain:
                old_domain = site.domain
                site.domain = domain
                site.name = "WeakAuras Bot"
                site.save()

                if self.verbosity >= 1:
                    self.stdout.write(f"Updated site domain: {old_domain} → {domain}")
            elif self.verbosity >= VERBOSE_LEVEL_2:
                self.stdout.write(f"Site domain already correct: {domain}")
        except Site.DoesNotExist:
            site = Site.objects.create(id=1, domain=domain, name="WeakAuras Bot")
            if self.verbosity >= 1:
                self.stdout.write(f"Created site: {domain}")

    def _setup_discord_oauth(self, client_id, client_secret, site_domain):
        """Setup or update Discord OAuth app in Django."""
        site = Site.objects.get(domain=site_domain)

        try:
            # Try to get existing Discord OAuth app
            app = SocialApp.objects.get(provider="discord")

            # Update credentials if they've changed
            updated_fields = []
            if app.client_id != client_id:
                app.client_id = client_id
                updated_fields.append("client_id")

            if app.secret != client_secret:
                app.secret = client_secret
                updated_fields.append("client_secret")

            if updated_fields:
                app.save()
                if self.verbosity >= 1:
                    self.stdout.write(
                        f"Updated Discord OAuth: {', '.join(updated_fields)}"
                    )
            elif self.verbosity >= VERBOSE_LEVEL_2:
                self.stdout.write("Discord OAuth credentials already up to date")

        except SocialApp.DoesNotExist:
            # Create new Discord OAuth app
            app = SocialApp.objects.create(
                provider="discord",
                name="Discord OAuth",
                client_id=client_id,
                secret=client_secret,
            )
            if self.verbosity >= 1:
                self.stdout.write("Created Discord OAuth app")

        # Ensure app is associated with the correct site
        if not app.sites.filter(id=site.id).exists():
            app.sites.add(site)
            if self.verbosity >= VERBOSE_LEVEL_2:
                self.stdout.write(f"Associated OAuth app with site: {site_domain}")
