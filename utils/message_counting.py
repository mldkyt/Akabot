import sentry_sdk
from discord import Guild, Message, TextChannel, VoiceChannel
from sqlalchemy import Connection, delete, insert, select, update

from database import engine, message_counting, message_counting_members
from utils.server_settings import ServerSetting, SettingType

setting_enable_leaderboard = ServerSetting(
    name="Message Counting leaderboard",
    setting_type=SettingType.NORMAL,
    default="false",
)

setting_enable_indexer = ServerSetting(
    name="Enable indexer command", setting_type=SettingType.NORMAL, default="false"
)

setting_count_deletes = ServerSetting(
    name="Count deletes", setting_type=SettingType.NORMAL, default="true"
)


def dec(c: Connection, m: Message):
    # Decrement for channel

    a = c.execute(
        select(
            message_counting.c.messages,
        ).where(message_counting.c.gid == str(m.guild.id))
    ).fetchone()
    if a is None:
        c.execute(
            insert(message_counting).values(
                gid=str(m.guild.id),
                messages=0,
            )
        )
    else:
        c.execute(
            update(message_counting)
            .values(messages=a[0] - 1)
            .where((message_counting.c.gid == str(m.guild.id)))
        )

    # Decrement for user
    a = c.execute(
        select(message_counting_members.c.messages).where(
            (message_counting_members.c.gid == str(m.guild.id))
            & (message_counting_members.c.uid == str(m.author.id))
        )
    ).fetchone()
    if a is None:
        c.execute(
            insert(message_counting_members).values(
                gid=str(m.guild.id),
                uid=str(m.author.id),
                messages=0,
            )
        )
    else:
        c.execute(
            update(message_counting_members)
            .values(messages=a[0] - 1)
            .where(
                (message_counting_members.c.gid == str(m.guild.id))
                & (message_counting_members.c.uid == str(m.author.id))
            )
        )


def inc(c: Connection, m: Message):
    # Increment for channel

    a = c.execute(
        select(
            message_counting.c.messages,
        ).where(message_counting.c.gid == str(m.guild.id))
    ).fetchone()
    if a is None:
        c.execute(
            insert(message_counting).values(
                gid=str(m.guild.id),
                messages=1,
            )
        )
    else:
        c.execute(
            update(message_counting)
            .values(messages=a[0] + 1)
            .where((message_counting.c.gid == str(m.guild.id)))
        )

    # Increment for user
    a = c.execute(
        select(message_counting_members.c.messages).where(
            (message_counting_members.c.gid == str(m.guild.id))
            & (message_counting_members.c.uid == str(m.author.id))
        )
    ).fetchone()
    if a is None:
        c.execute(
            insert(message_counting_members).values(
                gid=str(m.guild.id),
                uid=str(m.author.id),
                messages=1,
            )
        )
    else:
        c.execute(
            update(message_counting_members)
            .values(messages=a[0] + 1)
            .where(
                (message_counting_members.c.gid == str(m.guild.id))
                & (message_counting_members.c.uid == str(m.author.id))
            )
        )


async def reindex(guild: Guild):
    final_count = 0

    with engine.begin() as c:
        c.execute(
            update(message_counting)
            .where(message_counting.c.gid == str(guild.id))
            .values(messages=0)
        )
        c.execute(
            delete(message_counting_members).where(
                message_counting_members.c.gid == str(guild.id)
            )
        )

        for text in guild.text_channels:
            try:
                async for message in text.history(limit=None):
                    if message.author.bot:
                        continue

                    inc(c, message)
                    final_count += 1
            except Exception as e:
                print(e)
                sentry_sdk.capture_exception(e)

        for voice in guild.voice_channels:
            try:
                async for message in voice.history(limit=None):
                    if message.author.bot:
                        continue

                    inc(c, message)
                    final_count += 1
            except Exception as e:
                print(e)
                sentry_sdk.capture_exception(e)

    return final_count
