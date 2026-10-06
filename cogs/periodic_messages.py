import datetime

from discord import Bot, Cog
from discord.ext.tasks import loop
from sqlalchemy import select, update

from database import engine, periodic_messages
from logger import akabot_logger
from utils.timezones import get_now


def next_send_after(now: datetime.datetime, period: str, period_num: int) -> datetime.datetime:
    if period == "daily":
        return now + datetime.timedelta(days=period_num)

    if period == "hourly":
        return now + datetime.timedelta(hours=period_num)

    if period == "weekly":
        return now + datetime.timedelta(weeks=period_num)

    if period == "monthly":
        return now + datetime.timedelta(days=31 * period_num)

    if period == "yearly":
        return now + datetime.timedelta(days=365 * period_num)

    return now + datetime.timedelta(minutes=period_num)


class PeriodicMessages(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        if not self.send_due.is_running():
            self.send_due.start()

    @loop(seconds=60)
    async def send_due(self):
        with engine.begin() as c:
            rows = c.execute(
                select(
                    periodic_messages.c.id,
                    periodic_messages.c.guild_id,
                    periodic_messages.c.channel_id,
                    periodic_messages.c.content,
                    periodic_messages.c.period,
                    periodic_messages.c.period_num,
                    periodic_messages.c.next_send,
                ).where(periodic_messages.c.next_send.is_not(None))
            ).fetchall()

        for row in rows:
            try:
                await self.send_row(row)
            except Exception:
                akabot_logger.exception(
                    f"Failed to send periodic message {row.id} in channel {row.channel_id}"
                )

    async def send_row(self, row) -> None:
        try:
            guild_id = int(row.guild_id)
            channel_id = int(row.channel_id)
        except (TypeError, ValueError):
            return

        now = get_now(guild_id)

        if row.next_send > now:
            return

        channel = self.bot.get_channel(channel_id)
        if channel is None:
            # The bot is no longer in the guild or the channel was deleted.
            return

        await channel.send(row.content)

        with engine.begin() as c:
            c.execute(
                update(periodic_messages)
                .where(periodic_messages.c.id == row.id)
                .values(next_send=next_send_after(now, row.period, row.period_num))
            )


def setup(bot: Bot):
    bot.add_cog(PeriodicMessages(bot))
