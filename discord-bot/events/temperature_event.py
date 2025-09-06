import re

import discord
from bot.weakauras_bot import WeakAurasBot
from utils.logging import get_logger, log_event

logger = get_logger(__name__)


def setup_temperature_event(bot: WeakAurasBot):
    """Setup temperature conversion event handler"""

    @bot.event
    @log_event("temperature_conversion")
    async def on_message(message: discord.Message):
        # Don't respond to bot messages
        if message.author.bot:
            return

        # Only process messages in guilds
        if not message.guild:
            return

        # Check server-specific configuration
        server_config = bot.load_server_config(message.guild.id, message.guild.name)
        temp_config = server_config.get("events", {}).get("temperature", {})

        if not temp_config.get("enabled", True):
            logger.debug(
                f"Temperature event disabled for guild {message.guild.name} ({message.guild.id})"
            )
            return

        # Regex patterns to match temperature formats
        # Matches: 75F, 75°F, 75 F, 75 degrees F, 23C, 23°C, 23 C, 23 degrees C
        temp_pattern = r"(-?\d+(?:\.\d+)?)\s*(?:degrees?\s*)?([°]?)([FfCc])\b"

        matches = re.findall(temp_pattern, message.content)

        if not matches:
            return

        logger.info(
            f"Temperature conversion triggered by {message.author.name} ({message.author.id}) in guild {message.guild.name} ({message.guild.id}) with matches: {matches}"
        )

        conversions = []
        for temp_str, _degree_symbol, temp_unit in matches:
            try:
                temp = float(temp_str)
                unit = temp_unit.upper()

                if unit == "F":
                    # Fahrenheit to Celsius
                    celsius = (temp - 32) * 5 / 9
                    conversions.append(f"{temp}°F = {celsius:.1f}°C")
                    logger.debug(f"Converted {temp}°F to {celsius:.1f}°C")
                elif unit == "C":
                    # Celsius to Fahrenheit
                    fahrenheit = (temp * 9 / 5) + 32
                    conversions.append(f"{temp}°C = {fahrenheit:.1f}°F")
                    logger.debug(f"Converted {temp}°C to {fahrenheit:.1f}°F")
            except ValueError:
                logger.warning(f"Failed to parse temperature value: {temp_str}")
                continue

        if not conversions:
            return

        # Send conversion as a simple text reply
        conversion_text = " | ".join(conversions)
        logger.info(f"Sending temperature conversion reply: {conversion_text}")
        await message.reply(f"🌡️ {conversion_text}")
