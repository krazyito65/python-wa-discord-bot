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
# Run in development environment (default)
uv run python main.py
# or
uv run python main.py --env dev

# Run in production environment
uv run python main.py --env prod

# Use custom config file
uv run python main.py --config my_custom_token.yml
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

### Documentation
```bash
# Build documentation
cd docs && uv run sphinx-build -b html . _build/html

# Serve documentation locally (opens browser automatically)
uv run python serve_docs.py

# Serve on custom port
uv run python serve_docs.py --port 8080

# Rebuild API documentation (if new modules added)
uv run sphinx-apidoc -o docs/api . migrate_old_macros.py
```

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

## Configuration

- **Required**: Valid tokens in `settings/token.yml` for desired environment(s)
- **Bot Permissions**: Bot needs application commands permission in Discord server
- **Intents**: Bot uses default intents (message content intent enabled but not required for slash commands)
- **Admin Role**: Configurable role name for delete permissions (default: "admin")
- **Data Storage**: Server-specific folders and macro files created automatically in configured directory
- since this is a standalone app and not an API, there is no need to preserve 'legacy methods'. simply rename or remove them as needed.
- make sure you continue documenting functions as we crete or update them so that the sphinx documentation is always updated
