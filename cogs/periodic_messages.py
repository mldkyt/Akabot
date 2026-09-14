import datetime

from discord import Bot, Cog, Message
from sqlalchemy import select, update

from database import engine, periodic_messages
from logger import akabot_logger


class PeriodicMessages(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @Cog.listener()
    async def on_message(self, message: Message):
        if message.author.bot:
            return

        with engine.begin() as c:
            # Find all expired messages in this channel
            expired_messages = c.execute(
                select(
                    periodic_messages.c.id,
                    periodic_messages.c.content,
                    periodic_messages.c.period,
                    periodic_messages.c.period_num,
                ).where(
                    periodic_messages.c.channel_id == str(message.channel.id),
                    periodic_messages.c.next_send <= datetime.datetime.now(),
                )
            ).fetchall()

            for msg in expired_messages:
                try:
                    # Send the message
                    await message.channel.send(msg[1])

                    # Calculate the next send time based on the period
                    if msg[2] == "daily":
                        next_send = datetime.datetime.now() + datetime.timedelta(
                            days=msg[3]
                        )
                    elif msg[2] == "hourly":
                        next_send = datetime.datetime.now() + datetime.timedelta(
                            hours=msg[3]
                        )
                    elif msg[2] == "weekly":
                        next_send = datetime.datetime.now() + datetime.timedelta(
                            weeks=msg[3]
                        )
                    elif msg[2] == "monthly":
                        next_send = datetime.datetime.now() + datetime.timedelta(
                            days=31 * msg[3]
                        )
                    elif msg[2] == "yearly":
                        next_send = datetime.datetime.now() + datetime.timedelta(
                            days=365 * msg[3]
                        )
                    else:
                        next_send = datetime.datetime.now() + datetime.timedelta(
                            minutes=msg[3]
                        )

                    # Update next_send to the next period
                    c.execute(
                        update(periodic_messages)
                        .where(
                            periodic_messages.c.id == msg[0],
                            periodic_messages.c.channel_id == str(message.channel.id),
                        )
                        .values(next_send=next_send)
                    )
                except Exception:
                    akabot_logger.exception(
                        f"Failed to send periodic message {msg[0]} in channel {message.channel.id}"
                    )


def setup(bot: Bot):
    bot.add_cog(PeriodicMessages(bot))
