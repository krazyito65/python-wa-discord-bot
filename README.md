# WeakAuras Discord Bot

A Discord bot designed to facilitate common questions and FAQs for the WeakAuras World of Warcraft addon community. The bot provides macro functionality that allows users to create custom commands (macros) that store and replay messages via Discord slash commands only.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Code style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

## ✨ Features

- **Server-Isolated Macros**: Each Discord server has its own separate macro storage
- **Slash Commands Only**: Modern Discord interface with `/create_macro`, `/macro`, `/list_macros`, `/delete_macro`
- **Role-Based Permissions**: Admin role required for macro deletion (configurable)
- **Environment Management**: Separate dev/prod configuration support
- **Automatic Code Quality**: Pre-commit hooks with Ruff formatting and linting
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
   # Development environment (default)
   uv run python main.py

   # Production environment
   uv run python main.py --env prod
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
├── main.py                     # Entry point with CLI argument parsing
├── settings/
│   ├── token.yml.example      # Configuration template
│   └── token.yml              # Your actual tokens (gitignored)
├── bot/
│   ├── __init__.py
│   └── weakauras_bot.py       # Main bot class
├── commands/
│   ├── __init__.py
│   └── macro_commands.py      # Slash command implementations
├── server_data/               # Per-server macro storage (auto-created)
│   └── {server_name}_{id}/    # Individual server folders
├── pyproject.toml             # Project configuration
├── ruff.toml                  # Code quality configuration
└── .pre-commit-config.yaml    # Pre-commit hooks
```

### Development Commands

```bash
# Install with dev dependencies
uv sync --dev

# Run development server
uv run python main.py --env dev

# Code quality checks
uv run ruff check .                    # Lint code
uv run ruff check --fix .              # Auto-fix issues
uv run ruff format .                   # Format code

# Pre-commit hooks
uv run pre-commit install              # Install hooks
uv run pre-commit run --all-files      # Run all hooks manually

# Add new dependencies
uv add <package-name>                  # Production dependency
uv add --dev <package-name>            # Development dependency
```

### Configuration

The bot uses a YAML configuration file (`settings/token.yml`):

```yaml
discord:
  tokens:
    dev: "your_dev_token_here"
    prod: "your_prod_token_here"

bot:
  admin_role: "admin"  # Role required for deletions

storage:
  data_directory: "server_data"
```

### Code Quality

This project uses automated code quality tools:

- **Ruff**: Fast Python linter and formatter
- **Pre-commit hooks**: Automatic checks before each commit
- **Type hints**: Modern Python typing with `dict[str, Any]` syntax

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run the code quality checks (`uv run ruff check --fix . && uv run ruff format .`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Development Guidelines

- Follow the existing code style (enforced by Ruff)
- Add type hints to all functions
- Write descriptive commit messages
- Test your changes with both dev and prod configurations
- Update documentation as needed

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
