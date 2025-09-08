# WeakAuras Discord Bot

A Discord bot designed to facilitate common questions and FAQs for the WeakAuras World of Warcraft addon community. The bot provides macro functionality that allows users to create custom commands (macros) that store and replay messages via Discord slash commands only.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Code style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-blue.svg)](https://krazyito65.github.io/python-wa-discord-bot/)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/krazyito65/python-wa-discord-bot)

📖 **[View Full Documentation](https://krazyito65.github.io/python-wa-discord-bot/)**

## ✨ Features

- **Server-Isolated Macros**: Each Discord server has its own separate macro storage
- **Slash Commands Only**: Modern Discord interface with `/create_macro`, `/macro`, `/list_macros`, `/delete_macro`
- **Role-Based Permissions**: Admin role required for macro deletion (configurable)
- **Django Web Interface**: Web dashboard for macro management with Discord OAuth authentication
- **Environment Management**: Separate dev/prod configuration support
- **Comprehensive Testing**: Full test coverage for both Discord bot and Django web components
- **Development Tools**: Convenient scripts for testing, logging, and service management
- **Automatic Code Quality**: Pre-commit hooks with Ruff formatting and linting
- **External Configuration**: Safe storage of tokens and data outside repository
- **WeakAuras Branding**: Purple theme and WeakAuras-focused messaging

## 🚀 Quick Start

### Prerequisites

- Python 3.13 or higher
- [uv](https://docs.astral.sh/uv/) package manager
- Discord bot token ([Create one here](https://discord.com/developers/applications))

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd python-wa-discord-bot
   ```

2. **Install dependencies**
   ```bash
   uv sync --dev
   ```

3. **Configure your bot tokens**
   ```bash
   # Copy the template
   cp settings/token.yml.example settings/token.yml

   # Edit with your actual Discord bot tokens
   vim settings/token.yml  # or your preferred editor
   ```

4. **Set up pre-commit hooks** (recommended)
   ```bash
   uv run pre-commit install
   ```

5. **Run the bot**
   ```bash
   # Using the launcher script from project root (recommended)
   python run-bot.py
   python run-bot.py --env dev
   python run-bot.py --env prod

   # Or directly from discord-bot folder
   cd discord-bot
   uv run python main.py
   uv run python main.py --env prod
   ```

6. **Set up Django web interface** (optional)
   ```bash
   # Start Django development server
   bin/dev-start-django

   # Or manually
   cd web
   uv run python manage.py migrate
   uv run python manage.py runserver
   ```

### Discord Bot Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to "Bot" section and create a bot
4. Copy the bot token to your `settings/token.yml`
5. In "OAuth2 > URL Generator":
   - Select "bot" and "applications.commands" scopes
   - Select "Send Messages" and "Use Slash Commands" permissions
6. Use the generated URL to invite your bot to servers

## 🎮 Usage

### Available Commands

- `/create_macro <name> <message>` - Create a new WeakAuras macro
- `/macro <name>` - Execute an existing WeakAuras macro
- `/list_macros` - Show all available WeakAuras macros for the current server
- `/delete_macro <name>` - Delete a WeakAuras macro (requires admin role)

### Example Workflow

```
/create_macro welcome Welcome to the WeakAuras Discord! Check out #getting-started for help.
/macro welcome
/list_macros
```

## 🛠️ Development

### Project Structure

```
├── run-bot.py                  # Launcher script (recommended entry point)
├── discord-bot/                # Discord bot application
│   ├── main.py                # Bot entry point with CLI argument parsing
│   ├── logging_config.py      # Centralized logging configuration
│   ├── settings/
│   │   ├── token.yml.example  # Configuration template
│   │   └── token.yml          # Your actual tokens (gitignored)
│   ├── bot/
│   │   ├── __init__.py
│   │   └── weakauras_bot.py   # Main bot class
│   ├── commands/
│   │   ├── __init__.py
│   │   └── macro_commands.py  # Slash command implementations
│   ├── events/                # Discord event handlers
│   ├── utils/                 # Utility modules
│   └── tests/                 # Discord bot unit tests
├── web/                       # Django web interface
│   ├── manage.py              # Django management script
│   ├── weakauras_web/         # Django project settings
│   ├── authentication/        # Discord OAuth authentication
│   ├── macros/                # Macro management views
│   ├── servers/               # Server management views
│   ├── shared/                # Shared utilities and bot interface
│   └── templates/             # HTML templates
├── bin/                       # Development and testing scripts
│   ├── dev-start-django       # Start Django server in background
│   ├── dev-start-bot          # Start Discord bot in background
│   ├── dev-logs-*             # Real-time log viewers
│   ├── test-*                 # Test runners with coverage
│   └── dev-stop-all           # Stop all services
├── docs/                      # Sphinx documentation
├── logs/                      # Development log files (auto-created)
├── server_data/               # Per-server macro storage (auto-created)
│   └── {server_name}_{id}/    # Individual server folders
├── pyproject.toml             # Project configuration
├── ruff.toml                  # Code quality configuration
└── .pre-commit-config.yaml    # Pre-commit hooks
```

### Development Commands

```bash
# Environment setup
uv sync --dev                          # Install with dev dependencies

# Running services
python run-bot.py --env dev            # Run Discord bot (development)
bin/dev-start-django                   # Start Django web server in background
bin/dev-start-bot                      # Start Discord bot in background
bin/dev-start-all                      # Start both services in background
bin/dev-stop-all                       # Stop all background services

# Development monitoring
bin/dev-logs-bot                       # View Discord bot logs in real-time
bin/dev-logs-django                    # View Django server logs in real-time

# Testing
bin/test-bot                           # Run Discord bot tests
bin/test-web                           # Run Django web tests
bin/test-all                           # Run all tests
bin/test-all --coverage                # Run all tests with coverage

# Code quality checks
uv run ruff check .                    # Lint code
uv run ruff check --fix .              # Auto-fix issues
uv run ruff format .                   # Format code

# Pre-commit hooks
uv run pre-commit install              # Install hooks
uv run pre-commit run --all-files      # Run all hooks manually

# Dependencies
uv add <package-name>                  # Production dependency
uv add --dev <package-name>            # Development dependency
```

### Configuration

The bot uses a YAML configuration file that can be stored in multiple locations for security:

**Recommended locations (checked in order):**
1. `~/.config/weakauras-bot/token.yml` (XDG standard - **recommended**)
2. `~/weakauras-bot-config/token.yml` (user directory)
3. `discord-bot/settings/token.yml` (repository - **unsafe with git clean**)

```yaml
discord:
  tokens:
    dev: "your_dev_token_here"
    prod: "your_prod_token_here"

bot:
  admin_role: "admin"  # Role required for deletions

storage:
  data_directory: "~/weakauras-bot-data"  # External storage (recommended)
  # data_directory: "server_data"         # Repository storage (unsafe)
```

**⚠️ Data Protection**: Store configuration and data externally to prevent loss from `git clean -dffx`:

```bash
# Setup external configuration (recommended)
mkdir -p ~/.config/weakauras-bot
cp discord-bot/settings/token.yml ~/.config/weakauras-bot/

# External data storage
mkdir -p ~/weakauras-bot-data
```

### Code Quality

This project uses automated code quality tools:

- **Ruff**: Fast Python linter and formatter
- **Pre-commit hooks**: Automatic checks before each commit
- **Type hints**: Modern Python typing with `dict[str, Any]` syntax

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for detailed information about:

- **Development Setup**: Getting your environment ready
- **Code Standards**: Style guidelines and best practices
- **Testing Requirements**: How to write and run tests
- **Pull Request Process**: Step-by-step submission guide
- **Architecture Overview**: Understanding the codebase structure

### Quick Start for Contributors

1. Fork the repository
2. Set up development environment: `uv sync --dev`
3. Create feature branch: `git checkout -b feature/amazing-feature`
4. Make changes and run tests: `bin/test-all`
5. Check code quality: `uv run ruff check --fix . && uv run ruff format .`
6. Submit PR with detailed description

📖 **[Read the full Contributing Guide →](CONTRIBUTING.md)**

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Discord**: Join the [WeakAuras Discord](https://discord.gg/weakauras) for community support
- **Issues**: Report bugs and request features via GitHub Issues
- **Documentation**: See [CLAUDE.md](CLAUDE.md) for detailed technical documentation

## 🙏 Acknowledgments

- [WeakAuras](https://github.com/WeakAuras/WeakAuras2) - The amazing World of Warcraft addon this bot supports
- [discord.py](https://github.com/Rapptz/discord.py) - The Discord API wrapper
- [Ruff](https://github.com/astral-sh/ruff) - Fast Python linter and formatter
- [uv](https://github.com/astral-sh/uv) - Modern Python package manager
