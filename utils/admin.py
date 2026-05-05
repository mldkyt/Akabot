from discord import InputTextStyle, Interaction
from discord.ui import Modal, TextInput

from utils.mail import add_mail


class CreateMailModal(Modal):
    def __init__(self):
        super().__init__(title="Create Mail", timeout=30 * 3600)

        self.content = TextInput(label="Content", placeholder="Lorem ipsum...", required=True,
                                 style=InputTextStyle.paragraph)
        self.add_item(self.content)

    async def callback(self, interaction: Interaction):
        add_mail(interaction.user.display_name, self.content.value)

        await interaction.respond("added mail", ephemeral=True)
