# Contributing to WeakAuras Discord Bot

Thank you for your interest in contributing to the WeakAuras Discord Bot! This guide will help you get started with development and ensure your contributions meet our project standards.

## 🚀 Getting Started

### Prerequisites

- Python 3.13 or higher
- [uv](https://docs.astral.sh/uv/) package manager
- Git
- Discord bot token for testing ([Create one here](https://discord.com/developers/applications))

### Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/your-username/python-wa-discord-bot.git
   cd python-wa-discord-bot
   ```

2. **Install dependencies**
   ```bash
   uv sync --dev
   ```

3. **Set up configuration**
   ```bash
   # Recommended: External configuration (safe from git clean)
   mkdir -p ~/.config/weakauras-bot
   cp discord-bot/settings/token.yml.example ~/.config/weakauras-bot/token.yml

   # Edit with your test bot tokens
   vim ~/.config/weakauras-bot/token.yml
   ```

4. **Install pre-commit hooks**
   ```bash
   uv run pre-commit install
   ```

5. **Verify setup**
   ```bash
   # Run all tests to ensure everything works
   bin/test-all

   # Start the bot in development mode
   python run-bot.py --env dev
   ```

## 🛠️ Development Workflow

### Making Changes

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Run tests before making changes**
   ```bash
   bin/test-all
   ```
   This ensures you start with a working baseline.

3. **Make your changes**
   - Follow existing code patterns and conventions
   - Add type hints to all functions
   - Update unit tests for new functionality
   - Use the logging decorators (`@log_command`, `@log_event`) for new Discord commands

4. **Test your changes**
   ```bash
   # Run specific test suites
   bin/test-bot              # Discord bot tests
   bin/test-web              # Django web tests
   bin/test-all              # All tests
   bin/test-all --coverage   # With coverage report
   ```

5. **Check code quality**
   ```bash
   # Run linting and formatting (required before committing)
   uv run ruff check --fix . && uv run ruff format .
   ```

6. **Test in both environments**
   ```bash
   # Development environment
   python run-bot.py --env dev

   # Production-like environment
   python run-bot.py --env prod
   ```

### Development Services

Use the convenient development scripts for service management:

```bash
# Service management (can be run from any directory)
bin/dev-start-django      # Start Django web server in background
bin/dev-start-bot         # Start Discord bot in background
bin/dev-start-all         # Start both services in background
bin/dev-stop-all          # Stop all development services

# Real-time monitoring
bin/dev-logs-django       # View Django server logs
bin/dev-logs-bot          # View Discord bot logs (Ctrl+C to exit)
```

### Debugging

The project includes VS Code debugging configurations:

- **Discord Bot**: Debug the bot with automatic Django server startup
- **Django Web**: Debug the web interface with automatic bot startup
- **Breakpoints**: Full debugging support with variable inspection

See `.vscode/README.md` for detailed debugging instructions.

## 📋 Code Standards

### Code Style

- **Formatter**: Ruff (automatically applied by pre-commit hooks)
- **Linter**: Ruff (catches common issues and enforces standards)
- **Type Hints**: Required for all functions using modern Python syntax
- **Imports**: Follow existing patterns, group by standard/third-party/local

### Python Standards

```python
# Good: Modern type hints
def create_macro(name: str, message: str) -> dict[str, Any]:
    """Create a new macro with the given name and message."""
    return {"name": name, "message": message, "created_at": datetime.now()}

# Good: Use logging decorators for Discord commands
@log_command
async def macro_command(interaction: discord.Interaction, name: str):
    """Execute a macro command."""
    # Implementation here
    pass
```

### Testing Standards

- **Coverage**: Maintain high test coverage for all new functionality
- **Isolation**: Use mocks for external dependencies (Discord API, file system)
- **Test Data**: Use temporary directories and cleanup after tests
- **Descriptive Names**: Test functions should clearly describe what they test

```python
def test_create_macro_with_valid_data_should_succeed(self):
    """Test that creating a macro with valid data succeeds."""
    # Test implementation
    pass
```

### Git Standards

- **Commit Messages**: Use descriptive, imperative mood messages
  ```bash
  # Good
  git commit -m "Add macro validation to prevent empty names"

  # Bad
  git commit -m "fix bug"
  ```

- **Branch Names**: Use descriptive feature branch names
  ```bash
  feature/macro-validation
  fix/discord-connection-timeout
  docs/update-contributing-guide
  ```

## 🧪 Testing

### Test Organization

- `discord-bot/tests/` - Discord bot unit tests
- `web/*/tests.py` - Django app tests
- `bin/test-*` - Test runner scripts

### Running Tests

```bash
# Run specific test suites
bin/test-bot                    # Discord bot tests only
bin/test-web                    # Django web tests only
bin/test-all                    # All tests (recommended)

# With additional options
bin/test-all --coverage         # Generate coverage report
bin/test-web --verbose          # Verbose output
```

### Writing Tests

1. **Add tests for new features**: Every new function, command, or view should have tests
2. **Update existing tests**: Modify tests when changing functionality
3. **Mock external dependencies**: Don't make real Discord API calls or file system operations
4. **Test edge cases**: Include tests for error conditions and boundary cases

## 🔧 Project Architecture

### Discord Bot (`discord-bot/`)

- **Entry Point**: `main.py` with CLI argument parsing
- **Bot Class**: `bot/weakauras_bot.py` extends `discord.py` with macro functionality
- **Commands**: `commands/macro_commands.py` implements slash commands
- **Events**: `events/` handles Discord events (messages, temperature conversion)
- **Utilities**: `utils/` contains Discord API helpers and data processing
- **Logging**: `logging_config.py` provides centralized logging with decorators

### Django Web Interface (`web/`)

- **Authentication**: Discord OAuth integration
- **Macros**: Web interface for macro management
- **Servers**: Server selection and management
- **Shared**: Bot data interface and Discord utilities
- **Templates**: Bootstrap-based UI matching WeakAuras theme

### Development Tools (`bin/`)

- **Service Management**: Start/stop development services
- **Testing**: Automated test execution with coverage
- **Logging**: Real-time log monitoring

## 📝 Documentation

### Code Documentation

- **Functions**: Document all public functions with docstrings
- **Classes**: Include class-level documentation explaining purpose
- **Modules**: Add module-level docstrings for complex modules
- **API Changes**: Update relevant documentation when changing interfaces

### Sphinx Documentation

```bash
# Build documentation locally
cd docs
uv run sphinx-build -b html . _build/html

# Serve documentation
uv run python serve_docs.py
```

### Updating Documentation

- **API Changes**: Run `sphinx-apidoc` to regenerate API documentation
- **New Modules**: Add them to the appropriate `toctree` in documentation
- **Examples**: Include code examples in docstrings where helpful

## 🚫 What Not to Do

### Security

- **Never commit tokens**: Use external configuration or gitignored files
- **No hardcoded secrets**: All sensitive data should be in configuration files
- **Validate input**: Always validate user input in commands and web forms

### Code Quality

- **Don't skip tests**: All changes must pass the full test suite
- **Don't ignore Ruff**: Fix all linting errors, don't suppress unnecessarily
- **No debugging code**: Remove `print()` statements and debugging code before committing
- **Don't bypass pre-commit**: Only use `--no-verify` in exceptional circumstances

### Architecture

- **Don't couple components**: Keep Discord bot and Django web interface loosely coupled
- **No direct Discord API in web**: Use the shared bot interface for Discord operations
- **Don't break server isolation**: Each Discord server must have separate data storage

## 🎯 Pull Request Process

### Before Submitting

1. **Ensure all tests pass**: `bin/test-all`
2. **Check code quality**: `uv run ruff check --fix . && uv run ruff format .`
3. **Test both environments**: Verify dev and prod configurations work
4. **Update documentation**: Include any necessary documentation changes
5. **Write descriptive PR description**: Explain what changes and why

### PR Requirements

- **Tests**: All new functionality must have tests
- **Documentation**: Update docstrings and documentation as needed
- **Code Quality**: All Ruff checks must pass
- **No Breaking Changes**: Maintain backward compatibility unless explicitly discussed
- **Small, Focused Changes**: Keep PRs focused on a single feature or fix

### Review Process

- **Automated Checks**: GitHub Actions will run all tests and quality checks
- **Code Review**: Maintainers will review code for quality and design
- **Testing**: Changes will be tested in development environment
- **Merge**: PRs are typically squashed and merged to maintain clean history

## 🆘 Getting Help

### Resources

- **Documentation**: [GitHub Pages](https://krazyito65.github.io/python-wa-discord-bot/)
- **Issues**: GitHub Issues for bugs and feature requests
- **Discord**: [WeakAuras Discord](https://discord.gg/weakauras) for community discussion
- **Code**: Review existing code for patterns and examples

### Common Issues

- **Configuration**: Ensure external configuration is set up correctly
- **Dependencies**: Run `uv sync --dev` if packages are missing
- **Tests Failing**: Check that you're using the correct Python version (3.13)
- **Pre-commit Issues**: Install hooks with `uv run pre-commit install`

### Getting Support

1. **Check existing issues**: Search GitHub Issues for similar problems
2. **Review documentation**: Check CLAUDE.md and README.md for detailed guidance
3. **Ask questions**: Open a discussion or issue for help with development
4. **Provide context**: Include error messages, environment details, and steps to reproduce

## 🙏 Recognition

Contributors will be recognized in:
- **GitHub Contributors**: Automatic recognition for all merged PRs
- **Release Notes**: Major contributions highlighted in release notes
- **Documentation**: Significant contributors mentioned in project documentation

Thank you for contributing to the WeakAuras Discord Bot! Your efforts help improve the World of Warcraft addon community experience.
