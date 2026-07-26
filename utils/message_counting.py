from discord import Message
from sqlalchemy import Connection, insert, select, update

from database import message_counting, message_counting_members
from utils.server_settings import ServerSetting, SettingType

setting_enable_leaderboard = ServerSetting(
    name="Message Counting leaderboard",
    setting_type=SettingType.NORMAL,
    default="false",
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

    if a is None or a[1] != str(m.author.id):
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

    if a is None or a[1] != str(m.author.id):
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
