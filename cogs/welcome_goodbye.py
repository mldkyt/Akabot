from discord import Cog, Bot, Member
from discord.ext.tasks import loop

from database import engine
from logger import nekona_logger
from utils.docs import Docs, DocsSetting
from utils.server_settings import settings, SettingType
from utils.welcome_goodbye import add_member_to_grace_period, handle_timed_events, welcome_channel, \
    welcome_grace_period_first, welcome_grace_period_second, send_goodbye_message, goodbye_channel, \
    welcome_message_title, welcome_message_message, welcome_message_type, goodbye_message_title, \
    goodbye_message_message, goodbye_message_type


class WelcomeGoodbye(Cog):
    def __init__(self, bot: Bot):
        super().__init__()
        self.bot = bot

    has_init = False

    @Cog.listener()
    async def on_ready(self):
        if not self.has_init:
            nekona_logger.debug("Welcoming: Starting timed tasks")
            self.timed_tasks.start()

            self.has_init = True

    @Cog.listener()
    async def on_member_join(self, member: Member):
        nekona_logger.debug("Welcome: Member joined: %s, adding to first grace period", member.display_name)
        with engine.begin() as c:
            add_member_to_grace_period(c, member)

    @Cog.listener()
    async def on_member_remove(self, member: Member):
        with engine.begin() as c:
            await send_goodbye_message(c, member)

    @loop(seconds=1)
    async def timed_tasks(self):
        await handle_timed_events()


def setup(bot: Bot):
    bot.add_cog(WelcomeGoodbye(bot))

    settings.add_settings(
        welcome_channel,
        welcome_grace_period_first,
        welcome_grace_period_second,
        welcome_message_title,
        welcome_message_message,
        welcome_message_type,
        goodbye_channel,
        goodbye_message_title,
        goodbye_message_message,
        goodbye_message_type
    )


def docs():
    return str(Docs(
        name="Welcome & Goodbye Messages",
        description="You can use Nekona to welcome new members and say goodbye to those who leave. There are two grace periods available, one for before the welcome message is sent, and one for when the welcome message gets deleted (when a member leaves too quickly). Both can be disabled",
        settings=[
            DocsSetting(
                name="Welcome channel",
                description="Set a channel to send welcome messages into.",
                setting_type=SettingType.NORMAL,
            ),
            DocsSetting(
                name="Welcoming first grace period",
                description="The number of seconds between a member join and the welcome message being sent. This can be used to not welcome raiders (if they get kicked quickly enough).",
                setting_type=SettingType.NORMAL,
            ),
            DocsSetting(
                name="Welcoming second grace period",
                description="The number of minutes between the welcome message sent and it persisting when the member leaves. When it persists, a goodbye message is sent instead when the member leaves. When a member joins the server for a short period of time, this will unclog the goodbye channel.",
                setting_type=SettingType.NORMAL,
            ),
            DocsSetting(
                name="Welcome message title",
                description="The title of the embed in the welcome message. Not used if the message type is text. %s - server, %U - display name, %u - name of member, %m - mention of member",
                setting_type=SettingType.NORMAL,
            ),
            DocsSetting(
                name="Welcome message",
                description="The text of the message or the content of the embed. %s - server, %U - display name, %u - name of member, %m - mention of member",
                setting_type=SettingType.NORMAL,
            ),
            DocsSetting(
                name="Welcome message type",
                description="The type of the welcome message. Can be one of `text` or `embed`.",
                setting_type=SettingType.NORMAL,
            ),
            DocsSetting(
                name="Goodbye channel",
                description="Set a channel to send goodbye messages into.",
                setting_type=SettingType.NORMAL,
            ),
            DocsSetting(
                name="Goodbye message title",
                description="The title of the embed in the goodbye message. Not used if the message type is text. %s - server, %U - display name, %u - name of member, %m - mention of member",
                setting_type=SettingType.NORMAL,
            ),
            DocsSetting(
                name="Goodbye message",
                description="The text of the message or the content of the embed. %s - server, %U - display name, %u - name of member, %m - mention of member",
                setting_type=SettingType.NORMAL,
            ),
            DocsSetting(
                name="Goodbye message type",
                description="The type of the goodbye message. Can be one of `text` or `embed`.",
                setting_type=SettingType.NORMAL,
            ),
        ]
    ))
