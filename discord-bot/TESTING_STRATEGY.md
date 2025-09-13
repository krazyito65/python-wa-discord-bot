# Discord Bot Testing and Coverage Strategy

This document explains our approach to testing the Discord bot, including what we test, what we exclude from coverage, and why.

## Overview

Our testing strategy focuses on **core business logic** and **user-facing functionality** while strategically excluding complex Discord.py integration code that would require extensive mocking with minimal value.

## Current Coverage Results

- **Overall Discord Bot Coverage**: 53%
- **Core Business Logic Coverage**: ~78% (WeakAurasBot class)
- **Total Statements Covered**: 175 out of 328 statements
- **Excluded Integration Code**: 734 statements (complex Discord commands/events)

## What We Test (Included in Coverage)

### ✅ Core Business Logic (`bot/weakauras_bot.py` - 78% coverage)
- **Server folder management**: Creating, organizing, and maintaining server-specific data directories
- **Macro persistence**: Loading/saving macro data with JSON validation and error handling
- **Configuration management**: Processing bot configuration and data directory setup
- **Permission checking**: Role-based access control using admin roles and Discord permissions
- **Server name sanitization**: Filesystem-safe naming with edge case handling
- **Embed creation**: Branded Discord embeds with custom colors, footers, and attachments

### ✅ Utility Functions (`utils/` - 35-45% coverage)
- **Django permissions integration**: Database path resolution, config parsing
- **Logging configuration**: Environment-specific setup (dev/prod), logger hierarchy
- **Macro functionality helpers**: Embed response handling, parameter validation

### ✅ Command Business Logic (`commands/macro_commands.py` - 71% coverage)
- **Testable utility functions**: Embed response helpers, parameter handling
- **Core macro operations**: The business logic portions that can be tested without Discord mocking

## What We Exclude from Coverage (And Why)

### ❌ Complex Discord Command Modules (0% coverage - excluded)

#### `commands/config_commands.py` (60 statements)
- **Why excluded**: Primarily Discord slash command registration and interaction handling
- **Testing challenge**: Would require mocking `discord.Interaction`, command trees, user permissions
- **Business logic**: Minimal - mostly Discord API calls and response formatting
- **Alternative validation**: Manual testing through Discord interface

#### `commands/ping_commands.py` (21 statements)
- **Why excluded**: Simple bot status command with Discord-specific responses
- **Testing challenge**: Requires mocking bot latency, guild information, command trees
- **Business logic**: Minimal - just formats bot status information
- **Alternative validation**: Easy to verify manually with `/wa_ping` command

#### `commands/stats_commands.py` (267 statements)
- **Why excluded**: Complex Discord API integration for message statistics collection
- **Testing challenge**: Would need mocking of Discord channels, message history, API rate limits
- **Business logic**: Mostly Discord API calls and data aggregation
- **Alternative validation**: Integration testing with real Discord data is more valuable

#### `commands/wiki_commands.py` (20 statements)
- **Why excluded**: Simple wiki/documentation commands
- **Testing challenge**: Basic Discord interaction mocking overhead
- **Business logic**: Minimal - just response formatting
- **Alternative validation**: Manual verification is sufficient

### ❌ Event Handlers and Services (0% coverage - excluded)

#### `events/temperature_event.py` (44 statements)
- **Why excluded**: Discord message event handlers requiring live client connection
- **Testing challenge**: Would need complex Discord.py event system mocking
- **Business logic**: Event-driven temperature conversion responses
- **Alternative validation**: Integration testing with real Discord events is more appropriate

#### `services/stats_service.py` (203 statements)
- **Why excluded**: Discord API statistics collection requiring channel access
- **Testing challenge**: Complex Discord API mocking, rate limiting, async operations
- **Business logic**: Primarily API calls and data processing
- **Alternative validation**: Real Discord environment testing is more valuable

### ❌ Discord.py Integration Patterns (excluded via regex)

#### Command Registration Decorators
```python
@bot.tree.command  # Excluded - creates Discord slash commands
@log_command      # Excluded - logging decorator for Discord events
@log_event        # Excluded - logging decorator for Discord events
```

#### Discord Interaction Handling
```python
await interaction.response.send_message(...)  # Excluded - requires live Discord objects
if not interaction.guild:                     # Excluded - Discord validation
if not isinstance(user, discord.Member):     # Excluded - Discord type checking
```

#### Discord Client Lifecycle
```python
async def on_ready(self):      # Excluded - Discord connection event
async def sync_commands(self): # Excluded - Discord API synchronization
```

## Testing Philosophy

### Focus Areas
1. **Data Persistence**: Macro storage, configuration loading, file operations
2. **Business Logic**: Permission checking, server management, data validation
3. **Error Handling**: JSON parsing errors, file system issues, configuration problems
4. **Edge Cases**: Invalid inputs, missing files, permission edge cases

### Excluded Areas
1. **Discord API Integration**: Command registration, interaction responses
2. **Live Client Features**: Event handling, real-time Discord operations
3. **Complex Mocking Scenarios**: Where mock setup outweighs test value

### Why This Approach Works

1. **High Signal-to-Noise Ratio**: We test code that contains actual business logic
2. **Maintainable Tests**: Avoid brittle mocks of complex Discord.py internals
3. **Meaningful Coverage**: 53% coverage of business logic is more valuable than 90% coverage of mostly integration code
4. **Practical Validation**: Discord commands are easily tested manually in real Discord environment

## Running Tests

```bash
# Run all Discord bot tests
uv run pytest

# Run with coverage report
uv run pytest --cov=. --cov-report=term-missing

# Run coverage validation (requires 80% on included code)
../bin/test-coverage --min-coverage=80
```

## Coverage Targets

- **Current**: 53% overall (175/328 statements)
- **Target**: 80% on business logic code
- **Strategy**: Focus on improving utility function coverage while maintaining exclusions

## Future Improvements

1. **Integration Tests**: Add Discord bot integration tests using real Discord test server
2. **Mock Simplification**: Identify any complex excluded code that could be simplified for testing
3. **Business Logic Extraction**: Refactor Discord commands to separate business logic from Discord integration
4. **End-to-End Testing**: Automated testing through Discord API in CI/CD environment

---

This strategy ensures we have comprehensive coverage of the code that matters most while avoiding the maintenance burden of extensive Discord.py mocking.