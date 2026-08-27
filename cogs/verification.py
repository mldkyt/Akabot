import random
import re

from discord import (
    ApplicationContext,
    Bot,
    Button,
    ButtonStyle,
    Cog,
    Embed,
    EmbedAuthor,
    Interaction,
    Message,
    default_permissions,
    slash_command,
)
from discord.ext.tasks import loop
from discord.ui import InputText, Modal, View, button
from sentry_sdk import capture_exception
from sqlalchemy import delete, insert, select

from database import engine, verification_introduction_messages
from utils.bot_channel import setting_admin_bot_channel
from utils.verification import (
    setting_introduction_channel,
    setting_kick_unverified_users,
    setting_verification_mode,
    setting_verification_role,
    unverified_members,
)


class VerificationModalSilly(Modal):
    def __init__(self):
        super().__init__(title="Silly Verification", timeout=180)

        verification_types = ["meow", "bark", "waf"]
        self.verification_type = random.choice(verification_types)

        self.text = InputText(
            label=f"{self.verification_type} for me uwu?", required=True
        )
        self.add_item(self.text)

    async def callback(self, interaction: Interaction):
        with engine.begin() as c:
            verification_role_id = setting_verification_role.get(
                c, interaction.guild_id
            )

        if verification_role_id is None:
            await interaction.respond(
                "The owner has misconfigured the verification channel", ephemeral=True
            )
            return

        verification_role = interaction.guild.get_role(int(verification_role_id))
        if verification_role is None:
            await interaction.respond(
                "The owner has misconfigured the verification channel (no verification role found)",
                ephemeral=True,
            )
            return

        if self.text is None or self.text.value is None:
            await interaction.respond(
                "The value is not present for some godforsaken reason", ephemeral=True
            )
            return

        split = self.text.value.split(" ")
        if (
            self.verification_type == "meow"
            and any([re.match(r"^[meowr]+$", i) for i in split])
            or self.verification_type == "bark"
            and any([re.match(r"^[awruf]+$", i) for i in split])
            or self.verification_type == "waf"
            and any([re.match(r"^[waf]+$", i) for i in split])
        ):
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
            verification_role_id = setting_verification_role.get(
                c, interaction.guild_id
            )

        if verification_role_id is None:
            await interaction.respond(
                "The owner has misconfigured the verification channel", ephemeral=True
            )
            return

        verification_role = interaction.guild.get_role(int(verification_role_id))
        if verification_role is None:
            await interaction.respond(
                "The owner has misconfigured the verification channel (no verification role found)",
                ephemeral=True,
            )
            return

        await interaction.user.add_roles(verification_role)
        await interaction.respond("You have been verified!", ephemeral=True)


class VerificationView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="Verify", style=ButtonStyle.primary, custom_id="verification")
    async def verify(self, _: Button, interaction: Interaction):
        with engine.begin() as c:
            verification_role_id = setting_verification_role.get(
                c, interaction.guild.id
            )

        if verification_role_id is None:
            await interaction.respond(
                "The owner has misconfigured the verification channel", ephemeral=True
            )
            return

        verification_role = interaction.guild.get_role(int(verification_role_id))
        if verification_role is None:
            await interaction.respond(
                "The owner has misconfigured the verification channel (no verification role found)",
                ephemeral=True,
            )
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


class AdminIntroductionVerifyView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="Approve", style=ButtonStyle.green, custom_id="ver:intro:approve")
    async def approve(self, button: Button, interaction: Interaction):
        with engine.begin() as c:
            verification_message = c.execute(
                select(
                    verification_introduction_messages.c.author_id,
                    verification_introduction_messages.c.id,
                ).where(
                    verification_introduction_messages.c.admin_message_id
                    == str(interaction.message.id)
                )
            ).fetchone()
            if verification_message is None:
                await interaction.respond(
                    "The verification introduction message data is missing",
                    ephemeral=True,
                )
                return

            verification_role_id = setting_verification_role.get(
                c, interaction.guild.id
            )
            verification_role = interaction.guild.get_role(int(verification_role_id))

            author_id = verification_message[0]
            author = await interaction.guild.fetch_member(int(author_id))

            await author.add_roles(verification_role)

            self.disable_all_items()
            await interaction.edit(view=self)
            await interaction.respond("Member verified!", ephemeral=True)

            with engine.begin() as c:
                c.execute(
                    delete(verification_introduction_messages).where(
                        verification_introduction_messages.c.id
                        == verification_message[1]
                    )
                )

    @button(label="Deny", style=ButtonStyle.red, custom_id="ver:intro:deny")
    async def deny(self, button: Button, interaction: Interaction):
        with engine.begin() as c:
            verification_message = c.execute(
                select(
                    verification_introduction_messages.c.introduction_message_id,
                    verification_introduction_messages.c.author_id,
                    verification_introduction_messages.c.id,
                ).where(
                    verification_introduction_messages.c.admin_message_id
                    == str(interaction.message.id)
                )
            ).fetchone()
            if verification_message is None:
                await interaction.respond(
                    "The verification introduction message data is missing",
                    ephemeral=True,
                )
                return

            introduction_channel_id = setting_introduction_channel.get(
                c, interaction.guild.id
            )
            introduction_channel = interaction.guild.get_channel(
                int(introduction_channel_id)
            )

        try:
            introduction_message = await introduction_channel.fetch_message(
                int(verification_message[0])
            )
            await introduction_message.delete()
        except Exception:
            pass

        member_id = verification_message[1]
        member = await interaction.guild.fetch_member(int(member_id))

        try:
            await member.send(
                f"An admin denied your introduction in {interaction.guild.name} and you were kicked, you can rejoin."
            )
        except Exception:
            pass

        await member.kick(reason="Verification failed")

        self.disable_all_items()
        await interaction.edit(view=self)
        await interaction.respond(
            "Member denied and kicked from the server", ephemeral=True
        )


class Verification(Cog):
    def __init__(self, bot: Bot):
        super().__init__()

        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        self.bot.add_view(VerificationView())
        self.bot.add_view(AdminIntroductionVerifyView())

    @Cog.listener()
    async def on_message(self, msg: Message):
        if msg.guild is None:
            return
        if msg.author.bot:
            return

        with engine.begin() as c:
            verification_mode = setting_verification_mode.get(c, msg.guild.id)
            if verification_mode != "introduction":
                return

            introduction_channel = setting_introduction_channel.get(c, msg.guild.id)
            if str(msg.channel.id) != introduction_channel:
                return

            existing_message = c.execute(
                select(verification_introduction_messages.c.id).where(
                    (
                        verification_introduction_messages.c.author_id
                        == str(msg.author.id)
                    )
                    & (
                        verification_introduction_messages.c.guild_id
                        == str(msg.guild.id)
                    )
                )
            ).fetchone()

            if existing_message is not None:
                await msg.delete(reason="Member is already getting verified")
                tmp = await msg.channel.send(
                    f"{msg.author.mention}, you are already in the process of verification."
                )
                await tmp.delete(delay=5)
                return

            admin_bot_channel_id = setting_admin_bot_channel.get(c, msg.guild.id)
            admin_bot_channel = msg.guild.get_channel(int(admin_bot_channel_id))

            admin_channel_message = await admin_bot_channel.send(
                embed=Embed(
                    title="Member Verification",
                    author=EmbedAuthor(
                        name=msg.author.display_name,
                        icon_url=msg.author.display_avatar.url,
                    ),
                    description=msg.clean_content,
                ),
                view=AdminIntroductionVerifyView(),
            )

            c.execute(
                insert(verification_introduction_messages).values(
                    author_id=str(msg.author.id),
                    guild_id=str(msg.guild.id),
                    admin_message_id=str(admin_channel_message.id),
                    introduction_message_id=str(msg.id),
                )
            )

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

        await ctx.channel.send(
            "Please verify yourself to access this server", view=VerificationView()
        )
        await ctx.respond("Sent", ephemeral=True)

    @loop(hours=1)
    async def kick_unverified_members(self):
        for guild in self.bot.guilds:
            with engine.begin() as c:
                kick_unverified_users = (
                    setting_kick_unverified_users.get(c, guild.id) == "true"
                )

            if not kick_unverified_users:
                continue

            async for member in unverified_members(guild):
                if guild.me.guild_permissions.kick_members:
                    try:
                        await member.send(
                            f"You have been kicked from {guild.name} for not verifying in 24 hours, you can rejoin."
                        )
                    except Exception:
                        pass

                    try:
                        await member.kick(reason="Verification failed")
                    except Exception as e:
                        capture_exception(e)


def setup(bot: Bot):
    bot.add_cog(Verification(bot))
