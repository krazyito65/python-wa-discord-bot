#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

import yaml

from bot import WeakAurasBot
from commands import setup_macro_commands
from commands.ping_commands import setup_ping_commands


def load_config(config_path: str = "settings/token.yml") -> dict:
    """Load configuration from YAML file"""
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
    """Get Discord token for the specified environment"""
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


def main():
    parser = argparse.ArgumentParser(description="WeakAuras Discord Bot")
    parser.add_argument(
        "--env",
        choices=["dev", "prod"],
        default="dev",
        help="Environment to run in (dev or prod), defaults to dev",
    )
    parser.add_argument(
        "--config",
        default="settings/token.yml",
        help="Path to configuration file (default: settings/token.yml)",
    )

    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)

    # Get token for specified environment
    token = get_token(config, args.env)

    # Create bot instance
    bot = WeakAurasBot(config)

    # Setup commands
    setup_macro_commands(bot)
    setup_ping_commands(bot)

    print(f"Starting WeakAuras Discord Bot in '{args.env}' environment...")

    try:
        bot.run(token)
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"Error running bot: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
