import os

import requests
from discord import Bot, Cog, SlashCommand
from discord.ext.tasks import loop
from sentry_sdk.api import capture_exception

from logger import akabot_logger


class TopGGIntegration(Cog):
    def __init__(self, bot: Bot) -> None:
        super().__init__()
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        if os.getenv("TOPGG_TOKEN") is not None:
            self.topgg_update_metrics.start()
            self.topgg_sync_commands()

    def topgg_sync_commands(self):
        try:
            payload = []
            for cmd in self.bot.application_commands:
                if isinstance(cmd, SlashCommand):
                    payload.append(
                        {
                            "name": cmd.name,
                            "description": cmd.description
                            or "No description provided.",
                            "type": int(cmd.type),
                        }
                    )

            requests.post(
                "https://top.gg/api/v1/projects/@me/commands",
                headers={"Authorization": f"Bearer {os.getenv('TOPGG_TOKEN')}"},
                json=payload,
            ).raise_for_status()
        except Exception as e:
            akabot_logger.exception(f"Failed to sync top.gg commands: {e}")
            capture_exception(e)

    @loop(hours=24)
    async def topgg_update_metrics(self):
        # https://top.gg/api/v1/projects/@me/metrics

        try:
            requests.patch(
                "https://top.gg/api/v1/projects/@me/metrics",
                headers={"Authorization": f"Bearer {os.getenv('TOPGG_TOKEN')}"},
                json={"server_count": len(self.bot.guilds)},
            ).raise_for_status()
        except Exception as e:
            akabot_logger.exception(f"Failed to update top.gg metrics: {e}")
            capture_exception(e)


def setup(bot: Bot):
    bot.add_cog(TopGGIntegration(bot))
