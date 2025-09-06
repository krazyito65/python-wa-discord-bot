#!/usr/bin/env python3
"""
WeakAuras Discord Bot - Launcher Script

This script provides a convenient way to run the Discord bot from the project root.
It simply forwards all arguments to the main bot script in the discord-bot folder.

Examples:
    python run-bot.py
    python run-bot.py --env prod
    python run-bot.py --config custom_config.yml
"""

import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    # Path to the main bot script
    bot_script = Path(__file__).parent / "discord-bot" / "main.py"

    # Forward all arguments to the bot script
    cmd = [sys.executable, str(bot_script)] + sys.argv[1:]

    # Run the bot script
    sys.exit(subprocess.call(cmd))
