import logging

import discord
import requests
import sentry_sdk
from discord.ext import tasks

from utils.config import get_key


class Heartbeat(discord.Cog):
    def __init__(self) -> None:
        self.interval_cnt = int(get_key("Heartbeat_Interval", '60'))
        super().__init__()

        if get_key("Heartbeat_Enabled", "false") == "true":
            self.heartbeat_task.start()
            logging.info("Heartbeat started")
        else:
            logging.warning("Heartbeat is disabled")

    @tasks.loop(seconds=1)
    async def heartbeat_task(self):
        try:
            self.interval_cnt += 1
            if self.interval_cnt >= int(get_key("Heartbeat_Interval", '60')):
                self.interval_cnt = 0
                # Send heartbeat
                method = get_key("Heartbeat_HTTPMethod", 'post').lower()
                url = get_key('Heartbeat_URL', 'https://example.com')
                if method == "get":
                    requests.get(url)
                elif method == "post":
                    requests.post(url)
                elif method == "put":
                    requests.put(url)
                elif method == "delete":
                    requests.delete(url)
        except Exception as e:
            sentry_sdk.capture_exception(e)
