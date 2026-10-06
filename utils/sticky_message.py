import datetime

from discord import Message
from sqlalchemy import select, update

from database import engine, sticky_messages
from logger import akabot_logger
from utils.timezones import get_now


async def update_sticky_message(message: Message):
    if message.author.bot:
        return

    if message.guild is None:
        return

    with engine.begin() as c:
        existing_record = c.execute(
            select(sticky_messages.c.content, sticky_messages.c.last_msg_id).where(
                (sticky_messages.c.channel_id == str(message.channel.id))
                & (
                    (sticky_messages.c.cooldown < get_now(message.guild.id, c))
                    | (sticky_messages.c.cooldown == None)
                )
            )
        ).fetchone()

        if existing_record is None:
            return

        # Reserve the cooldown window before any await. The block runs without
        # yielding, so a burst of messages cannot pass this check again while
        # the network calls below are in flight.
        c.execute(
            update(sticky_messages)
            .where(sticky_messages.c.channel_id == str(message.channel.id))
            .values(cooldown=get_now(message.guild.id, c) + datetime.timedelta(minutes=1))
        )

    if existing_record[1]:
        try:
            existing_message = await message.channel.fetch_message(
                existing_record[1]
            )
            await existing_message.delete()
        except Exception:
            akabot_logger.exception(
                f"Failed to fetch/delete previous sticky message {existing_record[1]} in channel {message.channel.id}"
            )

    new_message = await message.channel.send(existing_record[0])

    with engine.begin() as c:
        c.execute(
            update(sticky_messages)
            .where(sticky_messages.c.channel_id == str(message.channel.id))
            .values(last_msg_id=str(new_message.id))
        )
