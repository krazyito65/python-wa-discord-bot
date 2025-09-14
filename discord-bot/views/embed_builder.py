"""Views for embed builder interface"""

from collections.abc import Callable

import discord
from modals.embed_builder import EmbedBuilderModal, EmbedFieldModal


class EmbedBuilderView(discord.ui.View):
    """View for building embeds with multiple options"""

    def __init__(
        self,
        timeout: float | None = 300,
        embed_data: dict | None = None,
        macro_name: str = "",
        callback_func: Callable | None = None,
    ):
        super().__init__(timeout=timeout)
        self.embed_data = embed_data or {}
        self.macro_name = macro_name
        self.callback_func = callback_func
        self.fields = self.embed_data.get("fields", [])

    def create_preview_embed(self) -> discord.Embed:
        """Create a preview embed from current data"""
        embed = discord.Embed()

        # Set title
        if self.embed_data.get("title"):
            embed.title = self.embed_data["title"]

        # Set description
        if self.embed_data.get("description"):
            embed.description = self.embed_data["description"]

        # Set color
        if self.embed_data.get("color"):
            embed.color = self.embed_data["color"]

        # Set footer
        if self.embed_data.get("footer"):
            embed.set_footer(text=self.embed_data["footer"])

        # Set image
        if self.embed_data.get("image"):
            embed.set_image(url=self.embed_data["image"])

        # Add fields
        for field in self.fields:
            embed.add_field(
                name=field["name"],
                value=field["value"],
                inline=field.get("inline", False),
            )

        # If embed is empty, add placeholder
        if not any(
            [
                embed.title,
                embed.description,
                embed.footer.text if embed.footer else None,
                embed.image,
                self.fields,
            ]
        ):
            embed.title = "Embed Preview"
            embed.description = (
                "*No content added yet. Use the buttons below to build your embed.*"
            )
            embed.color = discord.Color.greyple()

        return embed

    async def update_preview(self, interaction: discord.Interaction):
        """Update the embed preview"""
        preview_embed = self.create_preview_embed()

        # Create status text
        status_parts = []
        if self.embed_data.get("title"):
            status_parts.append("✅ Title")
        if self.embed_data.get("description"):
            status_parts.append("✅ Description")
        if self.embed_data.get("color"):
            status_parts.append("✅ Color")
        if self.embed_data.get("footer"):
            status_parts.append("✅ Footer")
        if self.embed_data.get("image"):
            status_parts.append("✅ Image")
        if self.fields:
            status_parts.append(f"✅ {len(self.fields)} Field(s)")

        status_text = (
            " | ".join(status_parts) if status_parts else "No content added yet"
        )

        content = (
            f"**Building Embed Macro: `{self.macro_name}`**\n*Status: {status_text}*"
        )

        await interaction.response.edit_message(
            content=content, embed=preview_embed, view=self
        )

    @discord.ui.button(
        label="Edit Basic Info", style=discord.ButtonStyle.primary, emoji="📝"
    )
    async def edit_basic_info(
        self, interaction: discord.Interaction, _button: discord.ui.Button
    ):
        """Edit basic embed information"""

        async def handle_basic_embed_data(
            interaction: discord.Interaction, embed_data: dict
        ):
            self.embed_data.update(embed_data)
            await self.update_preview(interaction)

        modal = EmbedBuilderModal(
            title_text="Edit Embed Info",
            embed_data=self.embed_data,
            callback_func=handle_basic_embed_data,
        )
        await interaction.response.send_modal(modal)

    @discord.ui.button(
        label="Add Field", style=discord.ButtonStyle.secondary, emoji="➕"
    )
    async def add_field(
        self, interaction: discord.Interaction, _button: discord.ui.Button
    ):
        """Add a custom field to the embed"""

        async def handle_field_data(interaction: discord.Interaction, field_data: dict):
            self.fields.append(field_data)
            self.embed_data["fields"] = self.fields
            await self.update_preview(interaction)

        modal = EmbedFieldModal(callback_func=handle_field_data)
        await interaction.response.send_modal(modal)

    @discord.ui.button(
        label="Clear Fields", style=discord.ButtonStyle.secondary, emoji="🗑️"
    )
    async def clear_fields(
        self, interaction: discord.Interaction, _button: discord.ui.Button
    ):
        """Clear all custom fields"""
        if not self.fields:
            await interaction.response.send_message(
                "❌ No fields to clear!", ephemeral=True
            )
            return

        self.fields.clear()
        self.embed_data["fields"] = self.fields
        await self.update_preview(interaction)

    @discord.ui.button(
        label="Save Macro", style=discord.ButtonStyle.success, emoji="💾"
    )
    async def save_macro(
        self, interaction: discord.Interaction, _button: discord.ui.Button
    ):
        """Save the embed macro"""
        # Validate embed has content
        if not any(
            [
                self.embed_data.get("title"),
                self.embed_data.get("description"),
                self.embed_data.get("footer"),
                self.embed_data.get("image"),
                self.fields,
            ]
        ):
            await interaction.response.send_message(
                "❌ Please add some content to your embed before saving!",
                ephemeral=True,
            )
            return

        # Call the callback function to save
        if self.callback_func:
            await self.callback_func(interaction, self.embed_data)
        else:
            await interaction.response.send_message(
                "✅ Embed macro saved successfully!", ephemeral=True
            )

        # Disable all buttons after saving
        for item in self.children:
            item.disabled = True
        await interaction.edit_original_response(view=self)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, emoji="❌")
    async def cancel(
        self, interaction: discord.Interaction, _button: discord.ui.Button
    ):
        """Cancel embed creation"""
        await interaction.response.edit_message(
            content="❌ Embed creation cancelled.", embed=None, view=None
        )

    async def on_timeout(self):
        """Handle view timeout"""
        # Disable all buttons on timeout
        for item in self.children:
            item.disabled = True
