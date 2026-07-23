from discord import Bot, Cog, Member
from discord.ext.tasks import loop

from database import engine
from logger import akabot_logger
from utils.welcome_goodbye import (
    add_member_to_grace_period,
    handle_timed_events,
    send_goodbye_message,
)


class WelcomeGoodbye(Cog):
    def __init__(self, bot: Bot):
        super().__init__()
        self.bot = bot

    has_init = False

    @Cog.listener()
    async def on_ready(self):
        if not self.has_init:
            self.timed_tasks.start()
            self.has_init = True

    @Cog.listener()
    async def on_member_join(self, member: Member):
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
