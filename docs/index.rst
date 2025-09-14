WeakAuras Discord Bot Documentation
=====================================

Welcome to the WeakAuras Discord Bot documentation! This bot is designed to facilitate common questions and FAQs for World of Warcraft addon support through Discord slash commands.

.. note::
   This documentation is automatically updated from the main branch.
   Visit the `live documentation <https://krazyito65.github.io/python-wa-discord-bot/>`_ for the latest version.

Features
--------

* **Server-Specific Macro Storage**: Each Discord server gets its own isolated macro storage
* **Slash Commands Only**: Modern Discord interaction system with slash commands
* **Role-Based Permissions**: Admin roles can manage macros and configuration
* **Temperature Events**: Automatic weather-based messages and configuration
* **WeakAuras Branding**: Consistent UI with WeakAuras theme and colors

Quick Start
-----------

1. **Installation**:

   .. code-block:: bash

      # Clone the repository
      git clone https://github.com/krazyito65/python-wa-discord-bot.git
      cd python-wa-discord-bot

      # Install dependencies
      uv sync

2. **Configuration**:

   .. code-block:: bash

      # Copy configuration template
      cp settings/token.yml.example settings/token.yml

      # Edit with your Discord bot tokens
      # vim settings/token.yml

3. **Running the Bot**:

   .. code-block:: bash

      # Development environment
      uv run python main.py

      # Production environment
      uv run python main.py --env prod

Available Commands
------------------

* ``/create_macro <name> <message>`` - Create a new WeakAuras macro
* ``/macro <name>`` - Execute an existing WeakAuras macro
* ``/list_macros`` - Show all available WeakAuras macros for current server
* ``/delete_macro <name>`` - Remove a WeakAuras macro (admin role required)
* ``/ping`` - Test bot responsiveness and show server information
* ``/toggle_temperature`` - Enable/disable temperature events (admin role required)

Documentation
-------------

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   getting_started
   configuration
   development

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
