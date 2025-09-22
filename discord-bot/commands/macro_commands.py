from typing import Any

import discord
from bot.weakauras_bot import WeakAurasBot
from discord import app_commands
from utils.django_permissions import (
    check_server_permission,
    get_permission_error_message,
    get_server_permission_config,
)
from utils.logging import get_logger, log_command
from views.embed_builder import EmbedBuilderView

logger = get_logger(__name__)


class MacroListView(discord.ui.View):
    """A paginated view for displaying macro lists"""

    def __init__(
        self, macros: dict, guild_name: str, bot: WeakAurasBot, items_per_page: int = 50
    ):
        super().__init__(timeout=300)  # 5 minute timeout
        self.macros = macros
        self.guild_name = guild_name
        self.bot = bot
        self.items_per_page = items_per_page
        self.current_page = 0

        # Convert macros dict to list of tuples for easier pagination
        self.macro_items = list(macros.items())
        self.total_pages = (
            len(self.macro_items) + items_per_page - 1
        ) // items_per_page

        # Update button states
        self._update_buttons()

    def _update_buttons(self):
        """Update button states based on current page"""
        # Remove all items first
        self.clear_items()

        # Only add navigation buttons if we have multiple pages
        if self.total_pages > 1:
            # Previous button
            prev_button = discord.ui.Button(
                style=discord.ButtonStyle.secondary,
                emoji="⬅️",
                disabled=self.current_page == 0,
                custom_id="prev_page",
            )
            prev_button.callback = self._prev_page
            self.add_item(prev_button)

            # Page indicator button (disabled, just for display)
            page_button = discord.ui.Button(
                style=discord.ButtonStyle.secondary,
                label=f"Page {self.current_page + 1}/{self.total_pages}",
                disabled=True,
                custom_id="page_indicator",
            )
            self.add_item(page_button)

            # Next button
            next_button = discord.ui.Button(
                style=discord.ButtonStyle.secondary,
                emoji="➡️",
                disabled=self.current_page >= self.total_pages - 1,
                custom_id="next_page",
            )
            next_button.callback = self._next_page
            self.add_item(next_button)

    def create_embed(self) -> tuple[discord.Embed, discord.File | None]:
        """Create the embed for the current page"""
        start_idx = self.current_page * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, len(self.macro_items))
        page_items = self.macro_items[start_idx:end_idx]

        # Build macro list with type indicators for current page
        macro_lines = []
        for name, data in page_items:
            if isinstance(data, dict) and data.get("type") == "embed":
                macro_lines.append(f"📄 {name} *(embed)*")
            else:
                macro_lines.append(f"💬 {name} *(text)*")

        macro_list = "\n".join(macro_lines)

        # Add page info to title if multiple pages
        title = "📂 WeakAuras Macros"
        if self.total_pages > 1:
            title += f" (Page {self.current_page + 1}/{self.total_pages})"

        embed, logo_file = self.bot.create_embed(
            title=title,
            description=macro_list,
            footer_text=f"Server: {self.guild_name} • Total macros: {len(self.macro_items)}",
        )
        return embed, logo_file

    async def _prev_page(self, interaction: discord.Interaction):
        """Handle previous page button click"""
        if self.current_page > 0:
            self.current_page -= 1
            self._update_buttons()
            embed, logo_file = self.create_embed()

            # Update the message
            kwargs = {"embed": embed, "view": self}
            if logo_file:
                kwargs["attachments"] = [logo_file]

            await interaction.response.edit_message(**kwargs)

    async def _next_page(self, interaction: discord.Interaction):
        """Handle next page button click"""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self._update_buttons()
            embed, logo_file = self.create_embed()

            # Update the message
            kwargs = {"embed": embed, "view": self}
            if logo_file:
                kwargs["attachments"] = [logo_file]

            await interaction.response.edit_message(**kwargs)

    async def on_timeout(self):
        """Called when the view times out"""
        # Disable all buttons when view times out
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True


async def send_embed_response(
    interaction: discord.Interaction,
    embed: discord.Embed,
    logo_file: discord.File | None,
    ephemeral: bool = True,
):
    """Helper function to send embed response with optional file attachment"""
    kwargs = {"embed": embed, "ephemeral": ephemeral}
    if logo_file:
        kwargs["file"] = logo_file
    await interaction.response.send_message(**kwargs)


def setup_macro_commands(bot: WeakAurasBot):  # noqa: PLR0915
    """Setup all macro-related slash commands"""

    async def macro_name_autocomplete(
        interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete function for all macro names"""
        if not interaction.guild:
            return []

        guild_id = interaction.guild.id
        guild_name = interaction.guild.name
        macros = bot.load_server_macros(guild_id, guild_name)

        # Filter macro names based on current input
        filtered_macros = [name for name in macros if current.lower() in name.lower()]

        # Return up to 25 choices (Discord limit)
        return [
            app_commands.Choice(name=name, value=name) for name in filtered_macros[:25]
        ]

    async def text_macro_autocomplete(
        interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete function for text macro names only"""
        if not interaction.guild:
            return []

        guild_id = interaction.guild.id
        guild_name = interaction.guild.name
        macros = bot.load_server_macros(guild_id, guild_name)

        # Filter for text macros only and current input
        filtered_macros = []
        for name, data in macros.items():
            if current.lower() in name.lower():
                # Check if it's a text macro (not embed)
                if isinstance(data, dict):
                    macro_type = data.get("type", "text")
                    if macro_type == "text":
                        filtered_macros.append(name)
                else:
                    # Legacy format is always text
                    filtered_macros.append(name)

        # Return up to 25 choices (Discord limit)
        return [
            app_commands.Choice(name=name, value=name) for name in filtered_macros[:25]
        ]

    async def embed_macro_autocomplete(
        interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete function for embed macro names only"""
        if not interaction.guild:
            return []

        guild_id = interaction.guild.id
        guild_name = interaction.guild.name
        macros = bot.load_server_macros(guild_id, guild_name)

        # Filter for embed macros only and current input
        filtered_macros = []
        for name, data in macros.items():
            if current.lower() in name.lower() and isinstance(data, dict):
                macro_type = data.get("type", "text")
                if macro_type == "embed":
                    filtered_macros.append(name)
                # Note: Legacy format is never embed, so we skip those

        # Return up to 25 choices (Discord limit)
        return [
            app_commands.Choice(name=name, value=name) for name in filtered_macros[:25]
        ]

    @bot.tree.command(
        name="create_macro", description="Create a new WeakAuras macro command"
    )
    @log_command
    async def create_macro(interaction: discord.Interaction, name: str, message: str):
        """Create a new macro with the given name and message"""
        if not interaction.guild:
            logger.warning("create_macro command used outside of server")
            await interaction.response.send_message(
                "This command can only be used in a server!", ephemeral=True
            )
            return

        guild_id = interaction.guild.id
        guild_name = interaction.guild.name

        # Check if user has permission to create macros
        if not isinstance(
            interaction.user, discord.Member
        ) or not check_server_permission(interaction.user, guild_id, "create_macros"):
            config = get_server_permission_config(guild_id)
            error_message = get_permission_error_message("create_macros", config)

            embed, logo_file = bot.create_embed(
                title="❌ Permission Denied",
                description=error_message,
                footer_text=f"Server: {guild_name}",
            )
            await send_embed_response(interaction, embed, logo_file)
            logger.warning("create_macro command denied - insufficient permissions")
            return

        # Load server-specific macros
        macros = bot.load_server_macros(guild_id, guild_name)

        if name in macros:
            logger.info(f"create_macro failed - macro '{name}' already exists")
            await interaction.response.send_message(
                f"WeakAuras macro '{name}' already exists!", ephemeral=True
            )
            return

        # Store as JSON-formatted macro data
        macro_data = {
            "name": name,
            "message": message,
            "created_by": str(interaction.user.id),
            "created_by_name": interaction.user.name,
            "created_at": interaction.created_at.isoformat(),
        }

        macros[name] = macro_data
        bot.save_server_macros(guild_id, guild_name, macros)
        logger.info(
            f"Successfully created macro '{name}' in guild {guild_name} ({guild_id})"
        )

        # Create branded success embed
        embed, logo_file = bot.create_embed(
            title="✅ Macro Created",
            description=f"Successfully created macro **{name}**",
            footer_text=f"Server: {guild_name}",
        )
        await send_embed_response(interaction, embed, logo_file)

    @bot.tree.command(
        name="create_embed_macro",
        description="Create a new WeakAuras embed macro with rich formatting",
    )
    @log_command
    async def create_embed_macro(interaction: discord.Interaction, name: str):
        """Create a new embed macro with rich formatting"""
        if not interaction.guild:
            logger.warning("create_embed_macro command used outside of server")
            await interaction.response.send_message(
                "This command can only be used in a server!", ephemeral=True
            )
            return

        guild_id = interaction.guild.id
        guild_name = interaction.guild.name

        # Check if user has permission to create macros
        if not isinstance(
            interaction.user, discord.Member
        ) or not check_server_permission(interaction.user, guild_id, "create_macros"):
            config = get_server_permission_config(guild_id)
            error_message = get_permission_error_message("create_macros", config)

            embed, logo_file = bot.create_embed(
                title="❌ Permission Denied",
                description=error_message,
                footer_text=f"Server: {guild_name}",
            )
            await send_embed_response(interaction, embed, logo_file)
            logger.warning(
                "create_embed_macro command denied - insufficient permissions"
            )
            return

        # Load server-specific macros
        macros = bot.load_server_macros(guild_id, guild_name)

        if name in macros:
            logger.info(f"create_embed_macro failed - macro '{name}' already exists")
            await interaction.response.send_message(
                f"WeakAuras macro '{name}' already exists!", ephemeral=True
            )
            return

        async def save_embed_macro(
            save_interaction: discord.Interaction, embed_data: dict[str, Any]
        ):
            """Callback to save the embed macro"""
            # Store as JSON-formatted macro data with embed type
            macro_data = {
                "name": name,
                "type": "embed",
                "embed_data": embed_data,
                "created_by": str(interaction.user.id),
                "created_by_name": interaction.user.name,
                "created_at": interaction.created_at.isoformat(),
            }

            macros[name] = macro_data
            bot.save_server_macros(guild_id, guild_name, macros)
            logger.info(
                f"Successfully created embed macro '{name}' in guild {guild_name} ({guild_id})"
            )

            # Create branded success embed
            success_embed, logo_file = bot.create_embed(
                title="✅ Embed Macro Created",
                description=f"Successfully created embed macro **{name}**",
                footer_text=f"Server: {guild_name}",
            )
            if logo_file:
                await save_interaction.response.send_message(
                    embed=success_embed, file=logo_file, ephemeral=True
                )
            else:
                await save_interaction.response.send_message(
                    embed=success_embed, ephemeral=True
                )

        # Create embed builder view
        embed_view = EmbedBuilderView(macro_name=name, callback_func=save_embed_macro)

        # Create initial preview
        preview_embed = embed_view.create_preview_embed()
        content = f"**Building Embed Macro: `{name}`**\n*Status: No content added yet*"

        await interaction.response.send_message(
            content=content, embed=preview_embed, view=embed_view, ephemeral=True
        )

    @bot.tree.command(
        name="list_macros", description="List all available WeakAuras macros"
    )
    @log_command
    async def list_macros(interaction: discord.Interaction):
        """List all available macros for this server"""
        if not interaction.guild:
            logger.warning("list_macros command used outside of server")
            await interaction.response.send_message(
                "This command can only be used in a server!", ephemeral=True
            )
            return

        guild_id = interaction.guild.id
        guild_name = interaction.guild.name
        macros = bot.load_server_macros(guild_id, guild_name)

        if not macros:
            logger.info(
                f"list_macros returned 0 macros for guild {guild_name} ({guild_id})"
            )
            embed, logo_file = bot.create_embed(
                title="📂 No Macros Found",
                description="No WeakAuras macros available in this server.",
                footer_text=f"Server: {guild_name}",
            )
            await send_embed_response(interaction, embed, logo_file)
            return

        logger.info(
            f"list_macros returned {len(macros)} macros for guild {guild_name} ({guild_id}): {', '.join(macros.keys())}"
        )

        # Create paginated view for macro list
        macro_view = MacroListView(macros, guild_name, bot, items_per_page=50)
        embed, logo_file = macro_view.create_embed()

        # Send with view (pagination buttons) if multiple pages, otherwise without view
        if macro_view.total_pages > 1:
            # Use view for pagination
            if logo_file:
                await interaction.response.send_message(
                    embed=embed, file=logo_file, view=macro_view, ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    embed=embed, view=macro_view, ephemeral=True
                )
        # No pagination needed
        elif logo_file:
            await interaction.response.send_message(
                embed=embed, file=logo_file, ephemeral=True
            )
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.tree.command(
        name="delete_macro",
        description="Delete an existing WeakAuras macro (Admin only)",
    )
    @app_commands.autocomplete(name=macro_name_autocomplete)
    @log_command
    async def delete_macro(interaction: discord.Interaction, name: str):
        """Delete a macro from this server (requires admin role)"""
        if not interaction.guild:
            logger.warning("delete_macro command used outside of server")
            await interaction.response.send_message(
                "This command can only be used in a server!", ephemeral=True
            )
            return

        # Check if user has permission to delete macros
        if not isinstance(
            interaction.user, discord.Member
        ) or not check_server_permission(
            interaction.user, interaction.guild.id, "delete_macros"
        ):
            config = get_server_permission_config(interaction.guild.id)
            error_message = get_permission_error_message("delete_macros", config)

            embed, logo_file = bot.create_embed(
                title="❌ Permission Denied",
                description=error_message,
                footer_text=f"Server: {interaction.guild.name}",
            )
            await send_embed_response(interaction, embed, logo_file)
            logger.warning("delete_macro command denied - insufficient permissions")
            return

        guild_id = interaction.guild.id
        guild_name = interaction.guild.name
        macros = bot.load_server_macros(guild_id, guild_name)

        if name not in macros:
            logger.info(
                f"delete_macro failed - macro '{name}' does not exist in guild {guild_name} ({guild_id})"
            )
            embed, logo_file = bot.create_embed(
                title="❌ Macro Not Found",
                description=f"WeakAuras macro '{name}' does not exist!",
                footer_text=f"Server: {guild_name}",
            )
            await send_embed_response(interaction, embed, logo_file)
            return

        del macros[name]
        bot.save_server_macros(guild_id, guild_name, macros)
        logger.info(
            f"Successfully deleted macro '{name}' from guild {guild_name} ({guild_id})"
        )

        embed, logo_file = bot.create_embed(
            title="🗑️ Macro Deleted",
            description=f"Successfully deleted macro **{name}**",
            footer_text=f"Server: {guild_name}",
        )
        await send_embed_response(interaction, embed, logo_file)

    @bot.tree.command(
        name="edit_macro",
        description="Edit an existing WeakAuras macro (text or embed)",
    )
    @app_commands.autocomplete(name=macro_name_autocomplete)
    @log_command
    async def edit_macro(interaction: discord.Interaction, name: str):
        """Edit an existing macro (automatically detects text vs embed type)"""
        if not interaction.guild:
            logger.warning("edit_macro command used outside of server")
            await interaction.response.send_message(
                "This command can only be used in a server!", ephemeral=True
            )
            return

        guild_id = interaction.guild.id
        guild_name = interaction.guild.name

        # Check if user has permission to edit macros
        if not isinstance(
            interaction.user, discord.Member
        ) or not check_server_permission(interaction.user, guild_id, "edit_macros"):
            config = get_server_permission_config(guild_id)
            error_message = get_permission_error_message("edit_macros", config)

            embed, logo_file = bot.create_embed(
                title="❌ Permission Denied",
                description=error_message,
                footer_text=f"Server: {guild_name}",
            )
            await send_embed_response(interaction, embed, logo_file)
            logger.warning("edit_macro command denied - insufficient permissions")
            return

        # Load server-specific macros
        macros = bot.load_server_macros(guild_id, guild_name)

        if name not in macros:
            logger.info(f"edit_macro failed - macro '{name}' does not exist")
            await interaction.response.send_message(
                f"WeakAuras macro '{name}' does not exist!", ephemeral=True
            )
            return

        macro_data = macros[name]

        # Check if this is an embed macro
        if isinstance(macro_data, dict) and macro_data.get("type") == "embed":
            # Redirect to embed editing
            async def update_embed_macro(
                save_interaction: discord.Interaction, embed_data: dict[str, Any]
            ):
                """Callback to update the embed macro"""
                macro_data["embed_data"] = embed_data
                macro_data["modified_by"] = str(interaction.user.id)
                macro_data["modified_by_name"] = interaction.user.name
                macro_data["modified_at"] = interaction.created_at.isoformat()

                macros[name] = macro_data
                bot.save_server_macros(guild_id, guild_name, macros)
                logger.info(
                    f"Successfully updated embed macro '{name}' via edit_macro in guild {guild_name} ({guild_id})"
                )

                success_embed, logo_file = bot.create_embed(
                    title="✅ Embed Macro Updated",
                    description=f"Successfully updated embed macro **{name}**",
                    footer_text=f"Server: {guild_name}",
                )
                if logo_file:
                    await save_interaction.response.send_message(
                        embed=success_embed, file=logo_file, ephemeral=True
                    )
                else:
                    await save_interaction.response.send_message(
                        embed=success_embed, ephemeral=True
                    )

            # Create embed builder view with existing data
            existing_embed_data = macro_data.get("embed_data", {})
            embed_view = EmbedBuilderView(
                macro_name=name,
                embed_data=existing_embed_data,
                callback_func=update_embed_macro,
            )

            preview_embed = embed_view.create_preview_embed()
            content = f"**Editing Embed Macro: `{name}`**\n*Use the buttons below to modify your embed.*"

            await interaction.response.send_message(
                content=content, embed=preview_embed, view=embed_view, ephemeral=True
            )
        else:
            # Handle text macro editing with a simple modal
            class TextMacroEditModal(discord.ui.Modal):
                def __init__(self, current_message: str):
                    super().__init__(title=f"Edit Text Macro: {name}")

                    self.message_input = discord.ui.TextInput(
                        label="Macro Message",
                        placeholder="Enter the macro content...",
                        default=current_message,
                        style=discord.TextStyle.paragraph,
                        max_length=2000,
                        required=True,
                    )
                    self.add_item(self.message_input)

                async def on_submit(self, modal_interaction: discord.Interaction):
                    new_message = self.message_input.value.strip()

                    if not new_message:
                        await modal_interaction.response.send_message(
                            "❌ Macro message cannot be empty!", ephemeral=True
                        )
                        return

                    # Update the macro
                    if isinstance(macro_data, dict):
                        macro_data["message"] = new_message
                        macro_data["updated_by"] = str(interaction.user.id)
                        macro_data["updated_by_name"] = interaction.user.name
                        macro_data["updated_at"] = interaction.created_at.isoformat()
                        macros[name] = macro_data
                    else:
                        # Convert legacy format to modern format with update info
                        macros[name] = {
                            "name": name,
                            "message": new_message,
                            "created_by": "",
                            "created_by_name": "Unknown",
                            "created_at": "",
                            "updated_by": str(interaction.user.id),
                            "updated_by_name": interaction.user.name,
                            "updated_at": interaction.created_at.isoformat(),
                        }

                    bot.save_server_macros(guild_id, guild_name, macros)
                    logger.info(
                        f"Successfully updated text macro '{name}' via edit_macro in guild {guild_name} ({guild_id})"
                    )

                    success_embed, logo_file = bot.create_embed(
                        title="✅ Text Macro Updated",
                        description=f"Successfully updated text macro **{name}**",
                        footer_text=f"Server: {guild_name}",
                    )
                    if logo_file:
                        await modal_interaction.response.send_message(
                            embed=success_embed, file=logo_file, ephemeral=True
                        )
                    else:
                        await modal_interaction.response.send_message(
                            embed=success_embed, ephemeral=True
                        )

            # Get current message
            current_message = (
                macro_data.get("message", macro_data)
                if isinstance(macro_data, dict)
                else macro_data
            )

            modal = TextMacroEditModal(current_message)
            await interaction.response.send_modal(modal)

    @bot.tree.command(
        name="edit_embed_macro",
        description="Edit an existing WeakAuras embed macro",
    )
    @app_commands.autocomplete(name=embed_macro_autocomplete)
    @log_command
    async def edit_embed_macro(interaction: discord.Interaction, name: str):
        """Edit an existing embed macro"""
        if not interaction.guild:
            logger.warning("edit_embed_macro command used outside of server")
            await interaction.response.send_message(
                "This command can only be used in a server!", ephemeral=True
            )
            return

        guild_id = interaction.guild.id
        guild_name = interaction.guild.name

        # Check if user has permission to create/edit macros
        if not isinstance(
            interaction.user, discord.Member
        ) or not check_server_permission(interaction.user, guild_id, "create_macros"):
            config = get_server_permission_config(guild_id)
            error_message = get_permission_error_message("create_macros", config)

            embed, logo_file = bot.create_embed(
                title="❌ Permission Denied",
                description=error_message,
                footer_text=f"Server: {guild_name}",
            )
            await send_embed_response(interaction, embed, logo_file)
            logger.warning("edit_embed_macro command denied - insufficient permissions")
            return

        # Load server-specific macros
        macros = bot.load_server_macros(guild_id, guild_name)

        if name not in macros:
            logger.info(f"edit_embed_macro failed - macro '{name}' does not exist")
            await interaction.response.send_message(
                f"WeakAuras macro '{name}' does not exist!", ephemeral=True
            )
            return

        macro_data = macros[name]

        # Check if this is an embed macro
        if not (isinstance(macro_data, dict) and macro_data.get("type") == "embed"):
            await interaction.response.send_message(
                f"❌ Macro '{name}' is not an embed macro! Use `/create_embed_macro` to create a new embed version.",
                ephemeral=True,
            )
            return

        async def update_embed_macro(
            save_interaction: discord.Interaction, embed_data: dict[str, Any]
        ):
            """Callback to update the embed macro"""
            # Update the existing macro data
            macro_data["embed_data"] = embed_data
            macro_data["modified_by"] = str(interaction.user.id)
            macro_data["modified_by_name"] = interaction.user.name
            macro_data["modified_at"] = interaction.created_at.isoformat()

            macros[name] = macro_data
            bot.save_server_macros(guild_id, guild_name, macros)
            logger.info(
                f"Successfully updated embed macro '{name}' in guild {guild_name} ({guild_id})"
            )

            # Create branded success embed
            success_embed, logo_file = bot.create_embed(
                title="✅ Embed Macro Updated",
                description=f"Successfully updated embed macro **{name}**",
                footer_text=f"Server: {guild_name}",
            )
            if logo_file:
                await save_interaction.response.send_message(
                    embed=success_embed, file=logo_file, ephemeral=True
                )
            else:
                await save_interaction.response.send_message(
                    embed=success_embed, ephemeral=True
                )

        # Create embed builder view with existing data
        existing_embed_data = macro_data.get("embed_data", {})
        embed_view = EmbedBuilderView(
            macro_name=name,
            embed_data=existing_embed_data,
            callback_func=update_embed_macro,
        )

        # Create initial preview
        preview_embed = embed_view.create_preview_embed()
        content = f"**Editing Embed Macro: `{name}`**\n*Use the buttons below to modify your embed.*"

        await interaction.response.send_message(
            content=content, embed=preview_embed, view=embed_view, ephemeral=True
        )

    @bot.tree.command(name="macro", description="Execute a saved WeakAuras macro")
    @app_commands.autocomplete(name=macro_name_autocomplete)
    @log_command
    async def execute_macro(interaction: discord.Interaction, name: str):
        """Execute a saved macro from this server"""
        if not interaction.guild:
            logger.warning("macro command used outside of server")
            await interaction.response.send_message(
                "This command can only be used in a server!", ephemeral=True
            )
            return

        guild_id = interaction.guild.id
        guild_name = interaction.guild.name
        macros = bot.load_server_macros(guild_id, guild_name)

        if name not in macros:
            logger.info(
                f"macro execution failed - macro '{name}' does not exist in guild {guild_name} ({guild_id})"
            )
            embed, logo_file = bot.create_embed(
                title="❌ Macro Not Found",
                description=f"WeakAuras macro '{name}' does not exist!",
                footer_text=f"Server: {guild_name}",
            )
            await send_embed_response(interaction, embed, logo_file)
            return

        macro_data = macros[name]

        # Check if this is an embed macro
        if isinstance(macro_data, dict) and macro_data.get("type") == "embed":
            # Handle embed macro
            embed_data = macro_data.get("embed_data", {})
            embed = discord.Embed()

            # Set embed properties
            if embed_data.get("title"):
                embed.title = embed_data["title"]
            if embed_data.get("description"):
                embed.description = embed_data["description"]
            if embed_data.get("color"):
                embed.color = embed_data["color"]
            if embed_data.get("footer"):
                embed.set_footer(text=embed_data["footer"])
            if embed_data.get("image"):
                embed.set_image(url=embed_data["image"])

            # Add custom fields
            for field in embed_data.get("fields", []):
                embed.add_field(
                    name=field["name"],
                    value=field["value"],
                    inline=field.get("inline", False),
                )

            logger.info(
                f"Successfully executed embed macro '{name}' from guild {guild_name} ({guild_id})"
            )
            await interaction.response.send_message(embed=embed)
        else:
            # Handle regular text macro (backward compatibility)
            message = (
                macro_data.get("message", macro_data)
                if isinstance(macro_data, dict)
                else macro_data
            )
            logger.info(
                f"Successfully executed text macro '{name}' from guild {guild_name} ({guild_id})"
            )
            await interaction.response.send_message(message)
