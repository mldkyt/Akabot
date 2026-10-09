from discord import Guild, Message
from sqlalchemy import Connection, delete, insert, select, update

from database import engine, message_counting, message_counting_members, message_counting_rewards
from logger import akabot_logger
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
                name=m.guild.name,
                messages=0,
            )
        )
    else:
        c.execute(
            update(message_counting)
            .values(messages=a[0] - 1, name=m.guild.name)
            .where(message_counting.c.gid == str(m.guild.id))
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
                name=m.author.display_name,
                messages=0,
            )
        )
    else:
        c.execute(
            update(message_counting_members)
            .values(messages=a[0] - 1, name=m.author.display_name)
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
                name=m.guild.name,
                messages=1,
            )
        )
    else:
        c.execute(
            update(message_counting)
            .values(messages=a[0] + 1, name=m.guild.name)
            .where(message_counting.c.gid == str(m.guild.id))
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
                name=m.author.display_name,
                messages=1,
            )
        )
    else:
        c.execute(
            update(message_counting_members)
            .values(messages=a[0] + 1, name=m.author.display_name)
            .where(
                (message_counting_members.c.gid == str(m.guild.id))
                & (message_counting_members.c.uid == str(m.author.id))
            )
        )

fetched_roles = []

async def update_roles(c: Connection, message: Message):
    message_count = c.execute(
        select(message_counting_members.c.messages)
        .where((message_counting_members.c.gid == str(message.guild.id)) &
               (message_counting_members.c.uid == str(message.author.id)))
    ).fetchone()

    if message_count is None:
        return

    rewards = c.execute(
        select(message_counting_rewards.c.rid)
        .where((message_counting_rewards.c.gid == str(message.guild.id)) &
               (message_counting_rewards.c.type == "role") &
               (message_count[0] >= message_counting_rewards.c.messages))
    ).fetchall()

    for r in rewards:
        if r[0] is None:
            continue

        if message.guild.id not in fetched_roles:
            await message.guild.fetch_roles()
            fetched_roles.append(message.guild.id)

        role = [i for i in message.guild.roles if i.id == int(r[0])]
        if len(role) == 0:
            continue

        if role[0] not in message.author.roles:
            await message.author.add_roles(role[0])

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
                akabot_logger.exception(f"Failed to reindex text channel {text}: {e}")

        for voice in guild.voice_channels:
            try:
                async for message in voice.history(limit=None):
                    if message.author.bot:
                        continue

                    inc(c, message)
                    final_count += 1
            except Exception as e:
                akabot_logger.exception(f"Failed to reindex voice channel {voice}: {e}")

    return final_count

# async def update_rewards(m: Message):
#     with engine.begin() as c:
#
