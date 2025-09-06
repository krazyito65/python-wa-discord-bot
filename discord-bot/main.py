#!/usr/bin/env python3
"""
WeakAuras Discord Bot - Main Entry Point

This module serves as the main entry point for the WeakAuras Discord bot.
It handles configuration loading, command-line argument parsing, bot initialization,
and command/event registration.

The bot is designed to facilitate common questions and FAQs for World of Warcraft
addon support through Discord slash commands. Each Discord server has its own
isolated macro and configuration storage.

Example:
    Run the bot in development mode (default)::

        $ python main.py

    Run the bot in production mode::

        $ python main.py --env prod

    Use a custom configuration file::

        $ python main.py --config my_config.yml

Attributes:
    None

Note:
    Requires a valid configuration file with Discord bot tokens.
    See settings/token.yml.example for the required format.
"""

import argparse
import sys
from pathlib import Path

import yaml
from bot import WeakAurasBot
from commands import setup_macro_commands
from commands.config_commands import setup_config_commands
from commands.ping_commands import setup_ping_commands
from commands.wiki_commands import setup_wiki_commands
from events import setup_temperature_event
from utils.logging import get_logger, setup_logging

bot_root = Path(__file__).resolve().parent


def load_config(config_path: str = f"{bot_root}/settings/token.yml") -> dict:
    """Load configuration from YAML file.

    Args:
        config_path (str): Path to the YAML configuration file.
            Defaults to "settings/token.yml".

    Returns:
        dict: Parsed configuration dictionary.

    Raises:
        SystemExit: If the configuration file is not found or contains
            invalid YAML syntax.

    Example:
        >>> config = load_config("my_config.yml")
        >>> print(config["discord"]["tokens"]["dev"])
    """
    config_file = Path(config_path)
    if not config_file.exists():
        print(f"Error: Configuration file '{config_path}' not found!")
        print("Please create a settings/token.yml file with your bot tokens.")
        sys.exit(1)

    try:
        with open(config_file) as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"Error parsing config file: {e}")
        sys.exit(1)


def get_token(config: dict, environment: str) -> str:
    """Get Discord token for the specified environment.

    Args:
        config (dict): Configuration dictionary loaded from YAML.
        environment (str): Environment name ("dev" or "prod").

    Returns:
        str: Discord bot token for the specified environment.

    Raises:
        SystemExit: If the environment is not found in config or
            if the token is not properly configured.

    Example:
        >>> config = {"discord": {"tokens": {"dev": "your_token_here"}}}
        >>> token = get_token(config, "dev")
    """
    tokens = config.get("discord", {}).get("tokens", {})

    if environment not in tokens:
        print(f"Error: No token found for environment '{environment}'")
        print(f"Available environments: {', '.join(tokens.keys())}")
        sys.exit(1)

    token = tokens[environment]
    if not token or token == f"your_{environment}_token_here":
        print(
            f"Error: Please set a valid token for environment '{environment}' in config.yml"
        )
        sys.exit(1)

    return token


def main() -> None:
    """Main entry point for the WeakAuras Discord Bot.

    This function handles:
    - Command-line argument parsing
    - Configuration loading
    - Bot initialization
    - Command and event registration
    - Bot startup and error handling

    Command-line Arguments:
        --env: Environment to run in ("dev" or "prod", defaults to "dev")
        --config: Path to configuration file (defaults to "settings/token.yml")

    Raises:
        SystemExit: If configuration is invalid or bot fails to start.

    Example:
        This function is called when the script is run directly::

            $ python main.py --env prod
    """
    parser = argparse.ArgumentParser(description="WeakAuras Discord Bot")
    parser.add_argument(
        "--env",
        choices=["dev", "prod"],
        default="dev",
        help="Environment to run in (dev or prod), defaults to dev",
    )
    parser.add_argument(
        "--config",
        default=f"{bot_root}/settings/token.yml",
        help="Path to configuration file (default: settings/token.yml)",
    )

    args = parser.parse_args()

    # Setup logging first
    setup_logging(args.env)
    logger = get_logger(__name__)

    logger.info(f"Starting WeakAuras Discord Bot in '{args.env}' environment")

    # Load configuration
    config = load_config(args.config)
    logger.info(f"Loaded configuration from: {args.config}")

    # Get token for specified environment
    token = get_token(config, args.env)
    logger.info(f"Retrieved token for environment: {args.env}")

    # Create bot instance
    bot = WeakAurasBot(config)
    logger.info("WeakAuras bot instance created")

    # Setup commands
    setup_macro_commands(bot)
    logger.info("Macro commands registered")

    setup_ping_commands(bot)
    logger.info("Ping commands registered")

    setup_config_commands(bot)
    logger.info("Config commands registered")

    setup_wiki_commands(bot)
    logger.info("Wiki commands registered")

    # Setup events
    setup_temperature_event(bot)
    logger.info("Temperature event handler registered")

    print(f"Starting WeakAuras Discord Bot in '{args.env}' environment...")
    logger.info("Bot initialization complete, starting Discord connection")

    try:
        bot.run(token)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (KeyboardInterrupt)")
        print("\nBot stopped by user")
    except Exception as e:
        logger.error(f"Error running bot: {e}", exc_info=True)
        print(f"Error running bot: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
