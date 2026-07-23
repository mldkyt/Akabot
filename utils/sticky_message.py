import datetime

from discord import Message
from sqlalchemy import select, update

from database import engine, sticky_messages


async def update_sticky_message(message: Message):
    if message.author.bot:
        return

    with engine.begin() as c:
        existing_record = c.execute(
            select(sticky_messages.c.content, sticky_messages.c.last_msg_id).where(
                (sticky_messages.c.channel_id == str(message.channel.id))
                & (
                    (sticky_messages.c.cooldown < datetime.datetime.now())
                    | (sticky_messages.c.cooldown == None)
                )
            )
        ).fetchone()

        if existing_record is None:
            return

        if existing_record[1]:
            try:
                existing_message = await message.channel.fetch_message(
                    existing_record[1]
                )
                await existing_message.delete()
            except Exception:
                pass

        new_message = await message.channel.send(existing_record[0])
        c.execute(
            update(sticky_messages)
            .where(sticky_messages.c.channel_id == str(message.channel.id))
            .values(
                last_msg_id=str(new_message.id),
                cooldown=datetime.datetime.now() + datetime.timedelta(minutes=1),
            )
        )
