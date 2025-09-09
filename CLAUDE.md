# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

For user-facing documentation and getting started instructions, see [README.md](README.md).

## Project Overview

This is a WeakAuras Discord bot designed to facilitate common questions and FAQs for World of Warcraft addon support. The bot provides macro functionality that allows users to create custom commands (macros) that store and replay messages via Discord slash commands only. Each Discord server has its own isolated macro storage. The project uses modern Python tooling with uv for dependency management and Python 3.13.

## Development Environment

- **Python Version**: 3.13.7 (specified in `.python-version`)
- **Package Manager**: uv (evident from `uv.lock` and `pyproject.toml`)
- **Virtual Environment**: `.venv` directory (created by uv)

## Common Commands

### Environment Setup
```bash
# Install dependencies and setup virtual environment
uv sync

# Activate virtual environment (if needed manually)
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate     # Windows
```

### Configuration
Copy the template and configure your Discord bot tokens:
```bash
# Copy the template to create your config file
cp settings/token.yml.example settings/token.yml

# Edit with your actual tokens
# vim settings/token.yml
```

Example configuration structure:
```yaml
discord:
  tokens:
    dev: "your_dev_token_here"
    prod: "your_prod_token_here"
bot:
  admin_role: "admin"
```

### Running the Bot
```bash
# From project root (recommended)
python run-bot.py
python run-bot.py --env dev
python run-bot.py --env prod
python run-bot.py --config my_custom_token.yml

# Or directly from discord-bot folder
cd discord-bot
uv run python main.py
uv run python main.py --env prod
```

### Logging
The bot includes comprehensive logging at the INFO level for all slash commands and events using a dedicated logging module:

```bash
# View bot logs in real-time
bin/dev-logs-bot

# Log files are stored in:
logs/bot.log
```

**Logging Architecture:**
- **Centralized Configuration**: `logging_config.py` module handles all logging setup
- **Automatic Command Logging**: `@log_command` decorator logs all slash command invocations
- **Event Logging**: `@log_event` decorator for Discord event handlers
- **Action Logging**: `@log_action` decorator for specific business logic actions

**Logged Information:**
- Bot startup and initialization
- Command registration and Discord connection events
- All slash command invocations with user details, guild information, and parameters
- Temperature conversion event triggers and results
- Configuration changes and permission checks
- Error conditions with full stack traces

**Log Levels:**
- **Development (`--env dev`)**: DEBUG level with console + file output
- **Production (`--env prod`)**: INFO level with file output only
- Discord.py logs are set to WARNING level to reduce noise

**Using the Logging Module:**
```python
# Setup logging (done in main.py)
from logging_config import setup_logging
setup_logging("dev")

# Get a logger for your module
from logging_config import get_logger
logger = get_logger(__name__)

# Use decorators for automatic logging
from logging_config import log_command, log_event

@log_command
async def my_slash_command(interaction: discord.Interaction, arg: str):
    # Automatically logs invocation and completion/errors
    pass

@log_event("my_event")
async def my_event_handler(message: discord.Message):
    # Automatically logs event trigger and completion/errors
    pass
```

### Development Tasks
```bash
# Add new dependencies
uv add <package-name>

# Add development dependencies
uv add --dev <package-name>

# Update dependencies
uv sync --upgrade
```

### Code Quality
```bash
# Check code with Ruff (linting)
uv run ruff check .

# Auto-fix issues with Ruff
uv run ruff check --fix .

# Format code with Ruff
uv run ruff format .

# Run both linting and formatting
uv run ruff check --fix . && uv run ruff format .
```

### Development Services
The project includes convenient scripts for managing development services with automatic database setup:

```bash
# Start/stop development services (can be run from anywhere)
bin/dev-start-django        # Stop all and start Django in background (auto-runs migrations)
bin/dev-start-bot           # Stop all and start Discord bot in background
bin/dev-start-all           # Stop all and start both services in background (auto-runs migrations)
bin/dev-stop-all            # Stop all development services

# View logs in real-time (Ctrl+C to stop)
bin/dev-logs-django         # Follow Django server logs
bin/dev-logs-bot            # Follow Discord bot logs

# Examples from different directories
./bin/dev-start-django      # From project root
../bin/dev-logs-bot         # From subdirectory
/full/path/to/bin/dev-stop-all  # Using absolute path
```

**Development Workflow:**
1. Start Django server: `bin/dev-start-django` (auto-runs migrations)
2. In VS Code, use "Debug Discord Bot" configuration
3. Monitor logs: `bin/dev-logs-django` and `bin/dev-logs-bot`
4. Stop all when done: `bin/dev-stop-all`

### Documentation
```bash
# Build documentation
cd docs && uv run sphinx-build -b html . _build/html

# Serve documentation locally (opens browser automatically)
uv run python serve_docs.py

# Serve on custom port
uv run python serve_docs.py --port 8080

# Rebuild API documentation (if new modules added)
cd docs && uv run sphinx-apidoc -o api ../discord-bot --force
```

### Testing
The project has comprehensive unit test coverage for both Discord bot and Django web components:

```bash
# Using convenient test runner scripts (recommended - can be run from anywhere)
bin/test-bot              # Run Discord bot tests
bin/test-web              # Run Django web tests
bin/test-all              # Run all tests

# With additional options
bin/test-bot --coverage   # Run bot tests with coverage report
bin/test-web --verbose    # Run web tests with verbose output
bin/test-all --coverage --verbose  # Run all tests with options

# Examples from different directories
./bin/test-web            # From project root
../bin/test-bot           # From subdirectory
/full/path/to/bin/test-all  # Using absolute path

# Manual commands (alternative)
cd discord-bot && uv run pytest
cd web && uv run python manage.py test
```

**Test Coverage Areas:**
- Discord bot core functionality and macro commands
- Django authentication adapters and Discord OAuth
- Bot data interface and server macro management
- Discord API utilities and error handling

**Test Validation Requirements:**
- **ALWAYS run tests before making changes** to ensure existing functionality works
- **ALWAYS run tests after making changes** to validate your implementations
- **ALWAYS update unit tests** when adding new features or modifying existing functionality
- **NEVER commit code** without running the full test suite first
- Add new test cases for any new functions, methods, or command handlers you create
- Mock external dependencies (Discord API, file system, database) in tests
- Use proper test isolation with temporary directories and cleanup

### Pre-commit Hooks
Pre-commit hooks automatically run code quality checks before each commit:

```bash
# Install pre-commit hooks (run once per developer)
uv run pre-commit install

# Run all hooks manually on all files
uv run pre-commit run --all-files

# Run hooks on specific files
uv run pre-commit run --files <file1> <file2>

# Skip pre-commit hooks for a specific commit (use sparingly)
git commit --no-verify -m "commit message"
```

**Automated Checks on Every Commit:**
- Ruff linting with auto-fix
- Ruff code formatting
- File size limits (max 1MB)
- Merge conflict detection
- YAML/TOML syntax validation
- Trailing whitespace removal
- Private key detection
- Python syntax validation
- **Discord bot tests** (runs when discord-bot/ files are modified)
- **Django web tests** (runs when web/ files are modified)

## Architecture

The bot is built using discord.py with a slash commands only interface and server-specific data isolation. Key components:

### WeakAurasBot Class (`bot/weakauras_bot.py`)
- Extends `commands.Bot` with WeakAuras-specific functionality
- Handles server-specific macro storage/retrieval using JSON persistence
- Manages slash command registration and syncing
- Maintains server ID to name mapping for human-readable identification
- Includes role-based permission system for administrative commands

### Configuration System (`settings/token.yml`)
- YAML-based configuration with dev/prod environment support
- Token management for different environments
- Configurable admin role for delete permissions
- Storage path configuration
- File is gitignored for security

### Server-Specific Macro System
- **Storage Structure**:
  - `server_data/{server_name}_{guild_id}/` - Individual folders per server (human-readable)
  - `{guild_id}_macros.json` - Macro file within each server folder
- **Folder Naming**: `{sanitized_server_name}_{guild_id}` (e.g., `WeakAuras_Discord_123456789012345678/`)
- **Macro Format**: JSON objects with metadata (name, message, created_by, created_by_name, created_at)
- **Commands Available** (`commands/macro_commands.py`):
  - `/create_macro <name> <message>` - Create new WeakAuras macro
  - `/macro <name>` - Execute existing WeakAuras macro
  - `/list_macros` - Show all available WeakAuras macros for current server
  - `/delete_macro <name>` - Remove a WeakAuras macro (admin role required)

### Bot Features
- Environment-based configuration (dev/prod modes)
- Server isolation (each Discord server has separate macro storage)
- Role-based permissions (admin role required for deletions)
- Automatic server name updating when server names change
- Automatic slash command syncing on startup
- Persistent macro storage across bot restarts
- Error handling for duplicate/missing macros
- Ephemeral responses for management commands
- WeakAuras branding throughout user interface

## Project Structure

- `main.py` - Entry point with argument parsing and bot initialization
- `logging_config.py` - Centralized logging configuration and decorators
- `settings/` - Configuration directory
  - `token.yml.example` - Configuration template (committed to repo)
  - `token.yml` - Actual configuration file with tokens (gitignored)
- `bot/` - Bot implementation directory
  - `__init__.py` - Package initialization
  - `weakauras_bot.py` - Main WeakAurasBot class with core functionality
- `commands/` - Command implementation directory
  - `__init__.py` - Package initialization
  - `macro_commands.py` - All slash command implementations
- `server_data/` - Directory containing server-specific data (auto-created)
  - `{server_name}_{guild_id}/` - Individual folders per Discord server
    - `{guild_id}_macros.json` - Macro storage file for each server
- `pyproject.toml` - Project configuration and dependencies (discord.py, pyyaml, ruff, pre-commit)
- `ruff.toml` - Code formatting and linting configuration
- `.pre-commit-config.yaml` - Pre-commit hooks configuration
- `uv.lock` - Locked dependency versions
- `.python-version` - Python version specification for uv
- `LICENSE` - MIT License file
- `README.md` - User-facing documentation and setup instructions

### Test Structure
- `bin/` - Test runner and development scripts for convenient execution
  - `test-bot` - Discord bot test runner with coverage support
  - `test-web` - Django web test runner with verbose output
  - `test-all` - Combined test runner for all components
  - `dev-start-django` - Stop all services and start Django in background
  - `dev-start-bot` - Stop all services and start Discord bot in background
  - `dev-stop-all` - Stop all development services
  - `dev-logs-django` - View Django server logs in real-time
  - `dev-logs-bot` - View Discord bot logs in real-time
- `discord-bot/tests/` - Discord bot unit tests
  - `__init__.py` - Test package initialization
  - `test_bot.py` - Core WeakAurasBot functionality tests
  - `test_macro_commands.py` - Macro command setup tests
  - `pytest.ini` - Pytest configuration
- `web/authentication/tests.py` - Django authentication adapter tests
- `web/shared/tests.py` - Bot interface and Discord API utility tests
- `logs/` - Development log files (gitignored)
  - `bot.log` - Discord bot runtime logs
  - `django.log` - Django web server logs

### CI/CD Integration
- `.pre-commit-config.yaml` - Pre-commit hooks including automated test execution
- `.github/workflows/ci.yml` - GitHub Actions workflow for PR validation
  - Runs all pre-commit hooks on pull requests
  - Executes full test suite with coverage reporting
  - Uploads coverage artifacts for review
  - Validates both Discord bot and Django web components

## Configuration

- **Required**: Valid tokens in `settings/token.yml` for desired environment(s)
- **Bot Permissions**: Bot needs application commands permission in Discord server
- **Intents**: Bot uses default intents (message content intent enabled but not required for slash commands)
- **Admin Role**: Configurable role name for delete permissions (default: "admin")
- **Data Storage**: Server-specific folders and macro files created automatically in configured directory (recommended to use external path to prevent data loss from `git clean`)
- since this is a standalone app and not an API, there is no need to preserve 'legacy methods'. simply rename or remove them as needed.
- make sure you continue documenting functions as we create or update them so that the sphinx documentation is always updated
- keep launch.json updated with debug options to allow developers to test with breakpoints
- make sure to fix ruff errors from the Django application as well

## Debugging Configuration

The project includes comprehensive VS Code debugging setup in `.vscode/`:

### Debug Configurations
- **Discord Bot Debugging**: Multiple configurations for dev/prod environments
- **Django Web Server Debugging**: Web interface, shell, and test debugging
- **Automatic Service Management**: Pre-launch tasks handle starting/stopping services
- **Background Service Logs**: Log files stored in `logs/` directory for monitoring

### Key Features
- **Clean Service Management**: Every debug session stops all services first, then starts the opposite service in background
- **Bot Debugging**: Automatically runs Django server in background for web interface access
- **Django Debugging**: Automatically runs Discord bot in background for full system functionality
- **Proper Environment Setup**: PYTHONPATH and working directories configured correctly
- **Breakpoint Support**: Full debugging capabilities with watch variables and call stack
- **Log Monitoring**: Built-in tasks to view real-time logs from background services (stored in `logs/` directory)

See `.vscode/README.md` for detailed usage instructions.
- use absolute paths when trying to run scripts so we dont get the error where you're in the wrong directory.
- **CRITICAL**: after making changes to the code base, ALWAYS run ruff and the test suite to ensure everything works:
  ```bash
  # Run linting and formatting
  uv run ruff check --fix . && uv run ruff format .

  # Run all tests to validate functionality
  bin/test-all
  ```
- **IMPORTANT**: Keep unit tests up-to-date when modifying bot functionality, commands, or events. All tests must pass before considering changes complete.
- New logging has been added to all slash commands and events at INFO level using the `logging_config.py` module - use the `@log_command` and `@log_event` decorators for future commands and events to maintain consistency.
- use absolute paths when using cd to ensure you always know where you're going.

## Data Protection

To prevent accidental loss of server data and configuration during development:

### Configuration Protection (Critical)
**IMPORTANT**: The `token.yml` file contains sensitive Discord tokens and is gitignored, so it gets deleted by `git clean -dffx`. Store it externally:

**Recommended locations (automatically checked in order):**
1. `~/.config/weakauras-bot/token.yml` (XDG standard)
2. `~/weakauras-bot-config/token.yml` (user directory)
3. `discord-bot/settings/token.yml` (repository - unsafe)

**Setup external config:**
```bash
# Create external config directory and copy tokens
mkdir -p ~/.config/weakauras-bot
cp discord-bot/settings/token.yml ~/.config/weakauras-bot/

# Now safe from git clean operations
```

### Server Data Protection
Configure `token.yml` to store server data and database outside the repository:
```yaml
storage:
  data_directory: "~/weakauras-bot-data"  # External storage (safe)
  # data_directory: "server_data"         # Repository storage (unsafe)

django:
  database_url: "sqlite:///~/weakauras-bot-data/statistics.db"  # External database (safe)
  # database_url: "sqlite:///web/db.sqlite3"                   # Repository database (unsafe)
```

### Benefits
- **Safe from `git clean -dffx`**: Config, server data, and statistics database stored outside repository
- **Persistent across resets**: Configuration, server macros, and user statistics survive repository cleanup
- **Easy backups**: Single directories contain all sensitive data and user statistics
- **Production ready**: External storage is standard for production deployments
- **Automatic fallback**: Bot automatically finds config in multiple locations
- **Auto-recovery**: Django migration automatically restores Discord OAuth from external config

### Manual Backup (Alternative)
If using repository paths, backup before major operations:
```bash
# Backup configuration and server data
cp discord-bot/settings/token.yml ~/backup-token-$(date +%Y%m%d).yml
cp -r discord-bot/server_data ~/backup-server-data-$(date +%Y%m%d)

# Restore after git clean if needed
cp ~/backup-token-*.yml discord-bot/settings/token.yml
cp -r ~/backup-server-data-* discord-bot/server_data
```

### Recovery After `git clean -dffx`

If you have external config/data setup and run `git clean -dffx`, here's the recovery process:

**Automatic Recovery (Recommended Setup):**
1. **Bot**: Already works - uses external config and data automatically
2. **Django**: Run `bin/dev-start-django` - automatically runs migrations and restores Discord OAuth

**Manual Recovery (if needed):**
```bash
# From web directory
cd web

# Recreate Django database and tables
uv run python manage.py migrate

# If migration didn't find external config, manually setup Discord OAuth
uv run python manage.py setup_discord_oauth --config-path ~/.config/weakauras-bot/token.yml

# Both Discord bot and Django web interface now work normally
```

**What Survives `git clean -dffx`:**
- ✅ Discord tokens (stored in `~/.config/weakauras-bot/token.yml`)
- ✅ Server macro data (stored in `~/weakauras-bot-data/`)
- ✅ User statistics database (stored in `~/weakauras-bot-data/statistics.db`)
- ❌ Repository database (if using `web/db.sqlite3` path - recreated by migrations)
- when you restart the services, always use `bin/dev-start-all` so that both services are always running at the same time
