import datetime

from discord import Message
from sqlalchemy import Connection, select, update

from database import markov


def tick_markov(c: Connection, message: Message):
    markov_data = c.execute(
        select(markov.c.mode, markov.c.period, markov.c.period_num)
        .where(markov.c.channel_id == message.channel.id)
    ).fetchone()

    if not markov_data:
        return

    if markov_data[0] == "messages":
        c.execute(
            update(markov)
            .where(markov.c.channel_id == str(message.channel.id))
            .values(messages_sent_since=markov.c.messages_sent_since + 1)
        )


def post_markov_run(c: Connection, message: Message):
    markov_data = c.execute(
        select(markov.c.mode, markov.c.period, markov.c.period_num)
        .where(markov.c.channel_id == message.channel.id)
    ).fetchone()

    if not markov_data:
        return False

    if markov_data[0] == "periodic":
        _, period, period_num = markov_data
        if period == "minutely":
            next_send = datetime.datetime.now() + datetime.timedelta(
                minutes=period_num
            )
        elif period == "hourly":
            next_send = datetime.datetime.now() + datetime.timedelta(
                hours=period_num
            )
        elif period == "daily":
            next_send = datetime.datetime.now() + datetime.timedelta(
                days=period_num
            )
        else:
            next_send = datetime.datetime.now() + datetime.timedelta(days=1)

        c.execute(
            update(markov)
            .where(markov.c.channel_id == str(message.channel.id))
            .values(next_send=next_send)
        )

    elif markov_data[0] == "messages":
        c.execute(
            update(markov)
            .where(markov.c.channel_id == str(message.channel.id))
            .values(messages_sent_since=0)
        )


def should_trigger_markov(c: Connection, message: Message) -> bool:
    markov_data = c.execute(
        select(markov.c.mode)
        .where(markov.c.channel_id == message.channel.id)
    ).fetchone()

    if not markov_data:
        return False

    if markov_data[0] == "periodic":
        # Has the sent_mode passed/
        row = c.execute(
            select(markov).where(
                (markov.c.channel_id == str(message.channel.id))
                & (
                    (markov.c.next_send < datetime.datetime.now())
                    | (markov.c.next_send is None)
                )
            )
        ).fetchone()

        return row is not None

    elif markov_data[0] == "messages":
        # Has enough messages been sent
        row = c.execute(
            select(markov)
            .where(
                (markov.c.channel_id == str(message.channel.id))
                & (
                    markov.c.messages_num < markov.c.messages_sent_since
                )
            )
        ).fetchone()

        return row is not None

    return False
