Configuration
=============

The WeakAuras Discord Bot uses YAML configuration files for settings. The main configuration file is ``settings/token.yml``.

Configuration File Structure
----------------------------

.. code-block:: yaml

   discord:
     tokens:
       dev: "your_development_token"
       prod: "your_production_token"

   bot:
     permissions:
       admin_roles: ["admin", "moderator"]
       admin_permissions: ["administrator", "manage_guild"]
     brand_color: 0x9F4AF3
     logo_path: "assets/weakauras_logo.png"

   storage:
     data_directory: "server_data"

Configuration Sections
----------------------

Discord Settings
^^^^^^^^^^^^^^^^

``discord.tokens``
  Dictionary of Discord bot tokens for different environments.

  * ``dev``: Token for development environment
  * ``prod``: Token for production environment

Bot Settings
^^^^^^^^^^^^

``bot.permissions``
  Permission configuration for administrative commands.

``bot.permissions.admin_roles``
  List of role names that grant administrative access. Case-insensitive matching.

  **Default:** ``["admin"]``

``bot.permissions.admin_permissions``
  List of Discord permission names that grant administrative access.

  **Common values:** ``["administrator", "manage_guild", "manage_channels"]``

``bot.brand_color``
  Hexadecimal color code for WeakAuras branding in embeds.

  **Default:** ``0x9F4AF3`` (WeakAuras purple)

``bot.logo_path``
  Path to logo file for embed thumbnails.

  **Optional:** If not provided or file doesn't exist, text-only footer is used.

Storage Settings
^^^^^^^^^^^^^^^^

``storage.data_directory``
  Directory path where server-specific data is stored.

  **Default:** ``"server_data"``

Environment Variables
---------------------

You can also use environment variables for sensitive configuration:

.. code-block:: bash

   export DISCORD_DEV_TOKEN="your_dev_token"
   export DISCORD_PROD_TOKEN="your_prod_token"

Server-Specific Configuration
-----------------------------

Each Discord server gets its own configuration file stored in:

``{data_directory}/{server_name}_{guild_id}/{guild_id}_config.json``

Server configuration includes:

.. code-block:: json

   {
     "events": {
       "temperature": {
         "enabled": true
       }
     }
   }

Configuration Examples
----------------------

Minimal Configuration
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: yaml

   discord:
     tokens:
       dev: "your_token_here"

Full Configuration
^^^^^^^^^^^^^^^^^^

.. code-block:: yaml

   discord:
     tokens:
       dev: "MDx1234567890.ABCDEF.your_development_token_here"
       prod: "MDx0987654321.GHIJKL.your_production_token_here"

   bot:
     permissions:
       admin_roles: ["admin", "moderator", "wa-admin"]
       admin_permissions: ["administrator", "manage_guild"]
     brand_color: 0x9F4AF3
     logo_path: "assets/weakauras_logo.png"

   storage:
     data_directory: "server_data"

Security Considerations
-----------------------

1. **Never commit tokens to version control**

   The ``settings/token.yml`` file is gitignored by default.

2. **Use different tokens for dev/prod**

   This prevents accidental commands on production servers during development.

3. **Restrict bot permissions**

   Only grant the minimum necessary permissions in Discord server settings.

4. **Protect configuration files**

   Ensure configuration files are not publicly readable on your server.

Configuration Validation
-------------------------

The bot validates configuration on startup:

* Checks for required token based on environment
* Validates YAML syntax
* Warns about missing optional settings

If validation fails, the bot will exit with an error message indicating the issue.
