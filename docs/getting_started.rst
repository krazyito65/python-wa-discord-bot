Getting Started
===============

Prerequisites
-------------

* Python 3.13 or higher
* uv package manager (recommended) or pip
* A Discord bot token
* Discord server with appropriate permissions

Installation
------------

1. **Clone the Repository**

   .. code-block:: bash

      git clone https://github.com/krazyito65/python-wa-discord-bot.git
      cd python-wa-discord-bot

2. **Install Dependencies**

   Using uv (recommended):

   .. code-block:: bash

      uv sync

   Or using pip:

   .. code-block:: bash

      pip install -r requirements.txt

3. **Create Configuration File**

   .. code-block:: bash

      cp settings/token.yml.example settings/token.yml

Configuration
-------------

Edit ``settings/token.yml`` with your Discord bot tokens:

.. code-block:: yaml

   discord:
     tokens:
       dev: "your_dev_token_here"
       prod: "your_prod_token_here"
   bot:
     admin_role: "admin"
   storage:
     data_directory: "server_data"

Discord Bot Setup
-----------------

1. **Create a Discord Application**

   * Go to https://discord.com/developers/applications
   * Click "New Application"
   * Give your bot a name

2. **Create a Bot User**

   * In your application, go to the "Bot" section
   * Click "Add Bot"
   * Copy the token to your ``settings/token.yml`` file

3. **Set Bot Permissions**

   Required permissions:
   * Use Slash Commands
   * Send Messages
   * Embed Links
   * Read Message History

4. **Invite Bot to Server**

   * Go to the "OAuth2" > "URL Generator" section
   * Select "bot" and "applications.commands" scopes
   * Select the required permissions
   * Use the generated URL to invite the bot

Running the Bot
---------------

Development mode (default):

.. code-block:: bash

   uv run python main.py

Production mode:

.. code-block:: bash

   uv run python main.py --env prod

Custom configuration file:

.. code-block:: bash

   uv run python main.py --config my_config.yml

First Steps
-----------

Once the bot is running and in your server:

1. **Test the Bot**

   .. code-block:: text

      /ping

2. **Create Your First Macro**

   .. code-block:: text

      /create_macro welcome "Welcome to our WeakAuras community!"

3. **Use the Macro**

   .. code-block:: text

      /macro welcome

4. **List All Macros**

   .. code-block:: text

      /list_macros

Troubleshooting
---------------

**Bot doesn't respond to commands:**
  * Make sure the bot has "Use Slash Commands" permission
  * Check that commands are synced (should happen automatically on startup)

**"No token found" error:**
  * Verify your ``settings/token.yml`` file exists and has valid tokens
  * Check that the token matches the environment you're running

**Permission errors:**
  * Ensure the bot has necessary permissions in your Discord server
  * Check that admin roles are properly configured for management commands
