import os

from aiohttp import ClientSession, ClientTimeout
from discord import Bot, Cog, SlashCommand
from discord.ext.tasks import loop

from logger import akabot_logger


class TopGGIntegration(Cog):
    def __init__(self, bot: Bot) -> None:
        super().__init__()
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        if os.getenv("TOPGG_TOKEN") is not None:
            if not self.topgg_update_metrics.is_running():
                self.topgg_update_metrics.start()
            await self.topgg_sync_commands()

    async def topgg_sync_commands(self):
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

            async with ClientSession(timeout=ClientTimeout(total=15)) as session:
                async with session.post(
                    "https://top.gg/api/v1/projects/@me/commands",
                    headers={"Authorization": f"Bearer {os.getenv('TOPGG_TOKEN')}"},
                    json=payload,
                ) as resp:
                    resp.raise_for_status()
        except Exception as e:
            akabot_logger.exception(f"Failed to sync top.gg commands: {e}")

    @loop(hours=24)
    async def topgg_update_metrics(self):
        # https://top.gg/api/v1/projects/@me/metrics

        try:
            async with ClientSession(timeout=ClientTimeout(total=15)) as session:
                async with session.patch(
                    "https://top.gg/api/v1/projects/@me/metrics",
                    headers={"Authorization": f"Bearer {os.getenv('TOPGG_TOKEN')}"},
                    json={"server_count": len(self.bot.guilds)},
                ) as resp:
                    resp.raise_for_status()
        except Exception as e:
            akabot_logger.exception(f"Failed to update top.gg metrics: {e}")


def setup(bot: Bot):
    bot.add_cog(TopGGIntegration(bot))
