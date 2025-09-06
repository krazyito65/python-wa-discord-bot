"""
Logging Utilities for WeakAuras Discord Bot

This module provides centralized logging configuration and utilities for the
WeakAuras Discord bot. It handles environment-based logging levels, file and
console output, and provides helper functions for consistent logging across
all bot components.

Example:
    Setting up logging at bot startup::

        from utils.logging import setup_logging
        setup_logging("dev")  # or "prod"

    Using the command logger decorator::

        from utils.logging import log_command

        @log_command
        async def my_command(interaction: discord.Interaction, ...):
            # Command implementation
            pass

    Getting a logger for a module::

        from utils.logging import get_logger
        logger = get_logger(__name__)
        logger.info("Module initialized")

Attributes:
    DEFAULT_LOG_FORMAT (str): Standard log message format
    DEFAULT_DATE_FORMAT (str): Standard date format for logs
"""

import functools
import logging
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

import discord

# Type variables for decorator
F = TypeVar("F", bound=Callable[..., Any])

# Log formatting constants
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(environment: str = "dev", log_dir: Path | None = None) -> None:
    """Setup centralized logging configuration for the bot.

    Args:
        environment (str): Environment name ("dev" or "prod"). Defaults to "dev".
            - "dev": DEBUG level with console + file output
            - "prod": INFO level with file output only
        log_dir (Path | None): Directory for log files. If None, uses ../../logs
            relative to this module.

    Note:
        This function should be called once during bot initialization.
        It configures the root logger and sets Discord.py logging levels.
    """
    # Determine log directory
    if log_dir is None:
        # Default to logs directory in project root (two levels up from utils/)
        current_dir = Path(__file__).resolve().parent
        log_dir = current_dir.parent.parent / "logs"

    log_dir.mkdir(exist_ok=True)

    # Configure logging level based on environment
    log_level = logging.DEBUG if environment == "dev" else logging.INFO

    # Create handlers
    handlers: list[logging.Handler] = [
        # File handler for all logs
        logging.FileHandler(log_dir / "bot.log", encoding="utf-8")
    ]

    # Add console handlers for development
    if environment == "dev":
        # Custom handler for stdout (DEBUG, INFO, WARNING)
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.addFilter(lambda record: record.levelno < logging.ERROR)

        # Handler for stderr (ERROR and above)
        stderr_handler = logging.StreamHandler(sys.stderr)
        stderr_handler.setLevel(logging.ERROR)

        handlers.extend([stdout_handler, stderr_handler])

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=DEFAULT_LOG_FORMAT,
        datefmt=DEFAULT_DATE_FORMAT,
        handlers=handlers,
        force=True,  # Override any existing configuration
    )

    # Set discord.py logging to WARNING to reduce noise
    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("discord.http").setLevel(logging.WARNING)

    # Log the logging configuration
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured for {environment} environment")
    logger.info(f"Log level: {logging.getLevelName(log_level)}")
    logger.info(f"Log directory: {log_dir}")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the specified module.

    Args:
        name (str): Logger name, typically __name__ from the calling module.

    Returns:
        logging.Logger: Configured logger instance.

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Module initialized")
    """
    return logging.getLogger(name)


def format_interaction_info(interaction: discord.Interaction) -> str:
    """Format Discord interaction information for logging.

    Args:
        interaction (discord.Interaction): Discord interaction object.

    Returns:
        str: Formatted string with user and guild information.

    Example:
        >>> info = format_interaction_info(interaction)
        >>> logger.info(f"Command executed: {info}")
    """
    user_info = f"{interaction.user.name} ({interaction.user.id})"

    if interaction.guild:
        guild_info = f"{interaction.guild.name} ({interaction.guild.id})"
    else:
        guild_info = "DM (N/A)"

    return f"user={user_info} guild={guild_info}"


def log_command(func: F) -> F:  # noqa: UP047
    """Decorator to automatically log slash command invocations.

    This decorator logs command invocations with user and guild information,
    and logs success or failure of command execution.

    Args:
        func: The command function to decorate. Must be an async function
            that takes discord.Interaction as its first parameter.

    Returns:
        The decorated function with logging.

    Example:
        >>> @log_command
        ... async def my_command(interaction: discord.Interaction, arg: str):
        ...     await interaction.response.send_message(f"Got: {arg}")

    Note:
        The decorated function must be an async function and take
        discord.Interaction as its first parameter.
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Get logger for the module where the command is defined
        logger = logging.getLogger(func.__module__)

        # Extract interaction from arguments
        interaction = None
        if args and isinstance(args[0], discord.Interaction):
            interaction = args[0]

        if interaction:
            # Extract command arguments (skip interaction)
            cmd_args = args[1:] if len(args) > 1 else []
            arg_strs = []

            # Format positional arguments
            for i, arg in enumerate(cmd_args):
                if isinstance(arg, str):
                    arg_strs.append(f"arg{i}='{arg}'")
                else:
                    arg_strs.append(f"arg{i}={arg}")

            # Format keyword arguments
            for key, value in kwargs.items():
                if isinstance(value, str):
                    arg_strs.append(f"{key}='{value}'")
                else:
                    arg_strs.append(f"{key}={value}")

            args_str = " " + " ".join(arg_strs) if arg_strs else ""

            logger.info(
                f"{func.__name__} command invoked by {format_interaction_info(interaction)}{args_str}"
            )

        try:
            result = await func(*args, **kwargs)
        except Exception as e:
            if interaction:
                logger.error(f"{func.__name__} command failed: {e}", exc_info=True)
            raise
        else:
            if interaction:
                logger.debug(f"{func.__name__} command completed successfully")
            return result

    return wrapper  # type: ignore[return-value]


def log_event(event_name: str) -> Callable[[F], F]:
    """Decorator to automatically log event handler invocations.

    Args:
        event_name (str): Name of the event for logging purposes.

    Returns:
        Decorator function that logs event invocations.

    Example:
        >>> @log_event("temperature_conversion")
        ... async def handle_temperature(message):
        ...     # Event handler implementation
        ...     pass
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            logger = logging.getLogger(func.__module__)
            logger.debug(f"{event_name} event triggered")

            try:
                result = await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"{event_name} event failed: {e}", exc_info=True)
                raise
            else:
                logger.debug(f"{event_name} event completed")
                return result

        return wrapper  # type: ignore[return-value]

    return decorator


def log_action(
    action: str, success_msg: str | None = None, failure_msg: str | None = None
) -> Callable[[F], F]:
    """Decorator to log specific actions within functions.

    Args:
        action (str): Description of the action being performed.
        success_msg (str | None): Message to log on success. If None, uses default.
        failure_msg (str | None): Message to log on failure. If None, uses default.

    Returns:
        Decorator function that logs the specified action.

    Example:
        >>> @log_action("macro_creation", "Macro created successfully", "Failed to create macro")
        ... async def create_macro_internal(name: str, content: str):
        ...     # Implementation
        ...     pass
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            logger = logging.getLogger(func.__module__)
            logger.debug(f"Starting {action}")

            try:
                result = await func(*args, **kwargs)
            except Exception as e:
                msg = failure_msg or f"{action} failed: {e}"
                logger.error(msg, exc_info=True)
                raise
            else:
                msg = success_msg or f"{action} completed successfully"
                logger.info(msg)
                return result

        return wrapper  # type: ignore[return-value]

    return decorator
