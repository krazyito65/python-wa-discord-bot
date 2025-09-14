"""Modal for building Discord embeds for macros"""

import discord


class EmbedBuilderModal(discord.ui.Modal):
    """Modal for creating/editing Discord embeds for macros"""

    def __init__(
        self,
        title_text: str = "Create Embed Macro",
        embed_data: dict | None = None,
        callback_func=None,
    ):
        super().__init__(title=title_text)

        # Store callback function for when modal is submitted
        self.callback_func = callback_func

        # Pre-fill with existing data if editing
        existing_data = embed_data or {}

        # Embed title field
        self.embed_title = discord.ui.TextInput(
            label="Embed Title",
            placeholder="Enter the embed title...",
            default=existing_data.get("title", ""),
            max_length=256,
            required=False,
        )

        # Embed description field
        self.embed_description = discord.ui.TextInput(
            label="Description",
            placeholder="Enter the main description...",
            default=existing_data.get("description", ""),
            style=discord.TextStyle.paragraph,
            max_length=4000,
            required=False,
        )

        # Color field (hex format)
        self.embed_color = discord.ui.TextInput(
            label="Color (hex)",
            placeholder="#5865F2 (optional)",
            default=existing_data.get("color", ""),
            max_length=7,
            required=False,
        )

        # Footer text
        self.embed_footer = discord.ui.TextInput(
            label="Footer Text",
            placeholder="Footer text (optional)...",
            default=existing_data.get("footer", ""),
            max_length=2048,
            required=False,
        )

        # Image URL
        self.embed_image = discord.ui.TextInput(
            label="Image URL",
            placeholder="https://example.com/image.png (optional)",
            default=existing_data.get("image", ""),
            max_length=500,
            required=False,
        )

        # Add all fields to modal
        self.add_item(self.embed_title)
        self.add_item(self.embed_description)
        self.add_item(self.embed_color)
        self.add_item(self.embed_footer)
        self.add_item(self.embed_image)

    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission"""
        # Parse color
        color = None
        if self.embed_color.value:
            try:
                # Remove # if present and convert to int
                color_str = self.embed_color.value.lstrip("#")
                color = int(color_str, 16)
            except ValueError:
                await interaction.response.send_message(
                    "❌ Invalid color format! Please use hex format like #5865F2",
                    ephemeral=True,
                )
                return

        # Validate at least one field is filled
        if not any(
            [
                self.embed_title.value,
                self.embed_description.value,
                self.embed_footer.value,
                self.embed_image.value,
            ]
        ):
            await interaction.response.send_message(
                "❌ Please fill in at least one field for the embed!", ephemeral=True
            )
            return

        # Build embed data
        embed_data = {}

        if self.embed_title.value:
            embed_data["title"] = self.embed_title.value

        if self.embed_description.value:
            embed_data["description"] = self.embed_description.value

        if color is not None:
            embed_data["color"] = color

        if self.embed_footer.value:
            embed_data["footer"] = self.embed_footer.value

        if self.embed_image.value:
            embed_data["image"] = self.embed_image.value

        # Call the callback function with embed data
        if self.callback_func:
            await self.callback_func(interaction, embed_data)
        else:
            await interaction.response.send_message(
                "✅ Embed created successfully!", ephemeral=True
            )


class EmbedFieldModal(discord.ui.Modal):
    """Modal for adding custom fields to embeds"""

    def __init__(self, callback_func=None):
        super().__init__(title="Add Embed Field")
        self.callback_func = callback_func

        # Field name
        self.field_name = discord.ui.TextInput(
            label="Field Name",
            placeholder="Enter field name...",
            max_length=256,
            required=True,
        )

        # Field value
        self.field_value = discord.ui.TextInput(
            label="Field Value",
            placeholder="Enter field content...",
            style=discord.TextStyle.paragraph,
            max_length=1024,
            required=True,
        )

        # Inline checkbox (represented as text since modals don't support checkboxes)
        self.field_inline = discord.ui.TextInput(
            label="Inline (yes/no)",
            placeholder="yes or no",
            default="no",
            max_length=3,
            required=False,
        )

        self.add_item(self.field_name)
        self.add_item(self.field_value)
        self.add_item(self.field_inline)

    async def on_submit(self, interaction: discord.Interaction):
        """Handle field modal submission"""
        inline = self.field_inline.value.lower() in ["yes", "y", "true", "1"]

        field_data = {
            "name": self.field_name.value,
            "value": self.field_value.value,
            "inline": inline,
        }

        if self.callback_func:
            await self.callback_func(interaction, field_data)
        else:
            await interaction.response.send_message(
                "✅ Field added successfully!", ephemeral=True
            )
