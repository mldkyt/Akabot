import os

import requests
from discord import Bot, Cog
from discord.ext.tasks import loop

HEARTBEAT_URL = os.getenv("HEARTBEAT_URL") or ""
HEARTBEAT_INTERVAL = os.getenv("HEARTBEAT_INTERVAL") or "60"


class Heartbeat(Cog):
    def __init__(self):
        super().__init__()

    has_started = False

    @Cog.listener()
    async def on_ready(self):
        if not self.has_started:
            self.heartbeat.start()
            self.has_started = True

    @loop(seconds=int(HEARTBEAT_INTERVAL))
    async def heartbeat(self):
        requests.post(HEARTBEAT_URL)


def setup(bot: Bot):
    if HEARTBEAT_URL.strip() != "":
        bot.add_cog(Heartbeat())
