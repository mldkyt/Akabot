import random
import re

from discord import Cog, Bot, ButtonStyle, Button, Interaction, slash_command, ApplicationContext, default_permissions
from discord.ui import View, button, Modal, InputText

from database import engine
from utils.docs import Docs, DocsCommand
from utils.server_settings import settings
from utils.verification import setting_verification_mode, setting_verification_role


class VerificationModalSilly(Modal):
    def __init__(self):
        super().__init__(title="Silly Verification", timeout=180)

        verification_types = ["meow", "bark", "waf"]
        self.verification_type = random.choice(verification_types)

        self.text = InputText(label=f"{self.verification_type} for me uwu?", required=True)
        self.add_item(self.text)

    async def callback(self, interaction: Interaction):
        with engine.begin() as c:
            verification_role_id = setting_verification_role.get(c, interaction.guild_id)

        if verification_role_id is None:
            await interaction.respond("The owner has misconfigured the verification channel", ephemeral=True)
            return

        verification_role = interaction.guild.get_role(int(verification_role_id))
        if verification_role is None:
            await interaction.respond(
                "The owner has misconfigured the verification channel (no verification role found)", ephemeral=True)
            return

        if self.text is None or self.text.value is None:
            await interaction.respond(
                "The value is not present for some godforsaken reason", ephemeral=True)
            return

        split = self.text.value.split(" ")
        if self.verification_type == "meow" and any([re.match(r"^[meowr]+$", i) for i in split]):
            await interaction.user.add_roles(verification_role)
            await interaction.respond("You have been verified!", ephemeral=True)
        elif self.verification_type == "bark" and any([re.match(r"^[awruf]+$", i) for i in split]):
            await interaction.user.add_roles(verification_role)
            await interaction.respond("You have been verified!", ephemeral=True)
        elif self.verification_type == "waf" and any([re.match(r"^[waf]+$", i) for i in split]):
            await interaction.user.add_roles(verification_role)
            await interaction.respond("You have been verified!", ephemeral=True)
        else:
            await interaction.respond("Verification failed", ephemeral=True)


class VerificationModalMath(Modal):
    def __init__(self):
        super().__init__(title="Verification", timeout=180)

        self.a = random.randint(1, 10)
        self.b = random.randint(1, 10)
        self.result = self.a + self.b

        self.text = InputText(label=f"{self.a} + {self.b} = ?", required=True)
        self.add_item(self.text)

    async def callback(self, interaction: Interaction):
        if self.text.value != str(self.result):
            await interaction.respond("Verification failed", ephemeral=True)
            return

        with engine.begin() as c:
            verification_role_id = setting_verification_role.get(c, interaction.guild_id)

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
            verification_role_id = setting_verification_role.get(c, interaction.guild.id)

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

        with engine.begin() as c:
            ver_guild = setting_verification_mode.get(c, interaction.guild.id)
            if ver_guild == "math":
                await interaction.response.send_modal(VerificationModalMath())
            elif ver_guild == "silly":
                await interaction.response.send_modal(VerificationModalSilly())
            elif ver_guild == "none":
                await interaction.respond("Verified!", ephemeral=True)
                await interaction.user.add_roles(verification_role)



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
            verification_role_id = setting_verification_role.get(c, ctx.guild.id)

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

    settings.add_settings(
        setting_verification_role,
        setting_verification_mode
    )


def docs():
    return str(
        Docs(
            name="Verification",
            description="You can set up verification for your server using the verification module. Members have to solve a simple math problem to verify.",
            settings=[
                setting_verification_role,
                setting_verification_mode
            ],
            commands=[
                DocsCommand(
                    command="send_verify_message",
                    description="Sends a verification message",
                )
            ]
        )
    )
