from random import randint

from discord import Cog, Bot, ButtonStyle, Button, Interaction, slash_command, ApplicationContext, default_permissions
from discord.ui import View, button, Modal, InputText

from database import engine
from utils.docs import Docs, DocsSetting, DocsCommand
from utils.server_settings import settings, SettingType
from utils.verification import setting_verification_role


class VerificationModal(Modal):
    def __init__(self):
        super().__init__(title="Verification", timeout=180)

        self.a = randint(1, 10)
        self.b = randint(1, 10)
        self.result = self.a + self.b

        self.text = InputText(label=f"{self.a} + {self.b} = ?", required=True)
        self.add_item(self.text)

    async def callback(self, interaction: Interaction):
        if self.text.value != str(self.result):
            await interaction.respond("Verification failed", ephemeral=True)
            return

        with engine.begin() as c:
            verification_role_id = setting_verification_role.get_guild(c, interaction.guild)

        if verification_role_id is None:
            await interaction.respond("The owner has misconfigured the verification channel", ephemeral=True)
            return

        verification_role = interaction.guild.get_role(int(verification_role_id))
        if verification_role is None:
            await interaction.respond(
                "The owner has misconfigured the verification channel (no verification role found)", ephemeral=True)
            return

        await interaction.user.add_roles(verification_role)
        await interaction.respond("You have been verified!", ephemeral=True)


class VerificationView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="Verify", style=ButtonStyle.primary, custom_id="verification")
    async def verify(self, _: Button, interaction: Interaction):
        with engine.begin() as c:
            verification_role_id = setting_verification_role.get_guild(c, interaction.guild)

        if verification_role_id is None:
            await interaction.respond("The owner has misconfigured the verification channel", ephemeral=True)
            return

        verification_role = interaction.guild.get_role(int(verification_role_id))
        if verification_role is None:
            await interaction.respond(
                "The owner has misconfigured the verification channel (no verification role found)", ephemeral=True)
            return

        if verification_role in interaction.user.roles:
            await interaction.respond("You are already verified", ephemeral=True)
            return

        await interaction.response.send_modal(VerificationModal())


class Verification(Cog):
    def __init__(self, bot: Bot):
        super().__init__()

        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        self.bot.add_view(VerificationView())

    @slash_command()
    @default_permissions(manage_guild=True)
    async def send_verify_message(self, ctx: ApplicationContext):
        with engine.begin() as c:
            verification_role_id = setting_verification_role.get(c, ctx.user)

        if verification_role_id is None or not verification_role_id.isnumeric():
            await ctx.respond("Please set a verification role first", ephemeral=True)
            return

        verification_role = ctx.guild.get_role(int(verification_role_id))
        if verification_role is None:
            await ctx.respond("Please set a verification role first", ephemeral=True)
            return

        await ctx.channel.send("Please verify yourself to access this server", view=VerificationView())
        await ctx.respond("Sent", ephemeral=True)


def setup(bot: Bot):
    bot.add_cog(Verification(bot))

    settings.add_setting(
        setting_verification_role
    )


def docs():
    return Docs(
        name="Verification",
        description="You can set up verification for your server using the verification module. Members have to solve a simple math problem to verify.",
        settings=[
            DocsSetting(
                name="Verification role",
                setting_type=SettingType.NORMAL,
                description="The verification role",
                set_description="Sets the verification role to whatever you desire."
            )
        ],
        commands=[
            DocsCommand(
                command="send_verify_message",
                description="Sends a verification message",
            )
        ]
    )
