Development
===========

This guide covers development setup, code structure, and contribution guidelines for the WeakAuras Discord Bot.

Development Setup
-----------------

1. **Clone and Install**

   .. code-block:: bash

      git clone https://github.com/krazyito65/python-wa-discord-bot.git
      cd python-wa-discord-bot
      uv sync

2. **Pre-commit Hooks**

   .. code-block:: bash

      uv run pre-commit install

3. **Code Quality Tools**

   .. code-block:: bash

      # Linting
      uv run ruff check .

      # Auto-fix issues
      uv run ruff check --fix .

      # Code formatting
      uv run ruff format .

Project Structure
-----------------

.. code-block:: text

   python-wa-discord-bot/
   ├── main.py                 # Entry point
   ├── bot/
   │   ├── __init__.py
   │   └── weakauras_bot.py    # Core bot implementation
   ├── commands/
   │   ├── __init__.py
   │   ├── macro_commands.py   # Macro-related slash commands
   │   ├── ping_commands.py    # Ping command
   │   └── config_commands.py  # Configuration commands
   ├── events/
   │   ├── __init__.py
   │   └── temperature_event.py # Temperature event handling
   ├── settings/
   │   ├── token.yml.example   # Configuration template
   │   └── token.yml          # Actual config (gitignored)
   ├── server_data/           # Server-specific data storage
   └── docs/                  # Documentation

Architecture
------------

Core Components
^^^^^^^^^^^^^^^

**WeakAurasBot Class**
  Extends ``discord.ext.commands.Bot`` with WeakAuras-specific functionality:

  * Server-specific data management
  * Folder naming and guild ID matching
  * Role-based permission checking
  * Branded embed creation

**Command Modules**
  Each command category is in a separate module:

  * ``macro_commands.py`` - Macro creation, execution, listing, deletion
  * ``ping_commands.py`` - Bot status and server information
  * ``config_commands.py`` - Server configuration management

**Event Handlers**
  Background events and scheduled tasks:

  * ``temperature_event.py`` - Weather-based messaging

Data Storage
^^^^^^^^^^^^

**Server Isolation**
  Each Discord server gets its own folder:

  .. code-block:: text

     server_data/
     ├── ServerName_123456789012345678/
     │   ├── 123456789012345678_macros.json
     │   └── 123456789012345678_config.json
     └── AnotherServer_987654321098765432/
         ├── 987654321098765432_macros.json
         └── 987654321098765432_config.json

**Folder Naming**
  Folders use format: ``{sanitized_server_name}_{guild_id}``

  The bot automatically renames folders when server names change,
  using guild ID as the primary identifier.

Adding New Commands
-------------------

1. **Create Command Function**

   .. code-block:: python

      @bot.tree.command(name="my_command", description="My new command")
      async def my_command(interaction: discord.Interaction, param: str):
          """Command implementation"""
          # Your logic here
          await interaction.response.send_message("Response")

2. **Add to Setup Function**

   .. code-block:: python

      def setup_my_commands(bot: WeakAurasBot):
          """Setup my commands"""
          # Command definitions here
          pass

3. **Register in main.py**

   .. code-block:: python

      from commands.my_commands import setup_my_commands

      # In main():
      setup_my_commands(bot)

Adding New Events
-----------------

1. **Create Event Handler**

   .. code-block:: python

      def setup_my_event(bot: WeakAurasBot):
          @bot.event
          async def on_my_event():
              # Event logic here
              pass

2. **Register in main.py**

   .. code-block:: python

      from events.my_event import setup_my_event

      # In main():
      setup_my_event(bot)

Code Style Guidelines
---------------------

**General Principles**
  * Follow PEP 8 style guidelines
  * Use type hints for all function parameters and return values
  * Write comprehensive docstrings for all public functions
  * Prefer explicit over implicit

**Docstring Format**
  Use Google-style docstrings:

  .. code-block:: python

     def my_function(param1: str, param2: int) -> bool:
         """Brief description of function.

         Longer description if needed.

         Args:
             param1: Description of first parameter.
             param2: Description of second parameter.

         Returns:
             Description of return value.

         Raises:
             SomeException: When this exception is raised.

         Example:
             >>> result = my_function("hello", 42)
             >>> print(result)
             True
         """

**Error Handling**
  * Use appropriate exception types
  * Provide helpful error messages
  * Log errors for debugging
  * Fail gracefully in user-facing commands

Testing
-------

**Manual Testing**
  1. Run bot in development mode
  2. Test commands in a test Discord server
  3. Verify error handling with invalid inputs
  4. Check permission restrictions

**Code Quality Checks**
  .. code-block:: bash

     # Run all quality checks
     uv run ruff check .
     uv run ruff format .

     # Pre-commit hooks (run automatically)
     uv run pre-commit run --all-files

Documentation
-------------

**Building Documentation**
  .. code-block:: bash

     cd docs
     uv run sphinx-build -b html . _build/html

**Updating Documentation**
  * Update docstrings in code
  * Add new pages to ``docs/`` directory
  * Update ``index.rst`` table of contents
  * Rebuild documentation

Contributing
------------

1. **Fork the Repository**
2. **Create Feature Branch**

   .. code-block:: bash

      git checkout -b feature/my-new-feature

3. **Make Changes**
   * Follow code style guidelines
   * Add appropriate tests
   * Update documentation

4. **Run Quality Checks**

   .. code-block:: bash

      uv run ruff check --fix .
      uv run ruff format .

5. **Commit Changes**

   .. code-block:: bash

      git commit -m "Add feature: description"

6. **Create Pull Request**
   * Describe changes clearly
   * Reference any related issues
   * Ensure CI checks pass

Release Process
---------------

1. **Update Version Numbers**
   * ``docs/conf.py``
   * Any other version references

2. **Update Changelog**
   * Document new features
   * List bug fixes
   * Note breaking changes

3. **Create Release Tag**

   .. code-block:: bash

      git tag -a v1.0.0 -m "Release version 1.0.0"
      git push origin v1.0.0

4. **Deploy Documentation**
   * Build and publish documentation
   * Update any deployment configurations
