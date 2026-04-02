from datetime import date, datetime

from discord import (
    Guild,
    Member,
    Message,
    TextChannel,
)
from sqlalchemy import Connection, delete, desc, insert, select, update

from database import (
    chat_summary_channels,
    chat_summary_members,
    engine,
    monthly_chat_summary_channels,
    monthly_chat_summary_members,
    yearly_chat_summary_channels,
    yearly_chat_summary_members,
)
from logger import nekona_logger
from utils.ads import get_ad
from utils.conversion import convert_text_channel
from utils.server_settings import (
    ServerSetting,
    SettingType,
    setting_to_number,
    setting_simple_list_string,
    setting_simple_string,
    setting_simple_string_boolean,
    setting_to_boolean,
)


def chat_summary_add_processor(c: Connection, m: Member, v: str) -> tuple[bool, str]:
    s = v.split(",")
    if len(s) == 2 and s[1].isnumeric():
        chat_convert = convert_text_channel(m.guild, s[0], int(s[1]))
    else:
        chat_convert = convert_text_channel(m.guild, v)

    if chat_convert is None:
        return False, "Invalid channel"

    return True, str(chat_convert.id)


def chat_summary_rows_processor(c: Connection, m: Member, v: str) -> tuple[bool, str]:
    (ok, val) = setting_to_number(c, m, v)
    if not ok:
        return ok, val

    v2 = int(v)
    if v2 <= 0 or v2 > 10:
        return False, "Invalid range"

    return True, v


chat_summary = ServerSetting(
    "Chat summary channels",
    setting_type=SettingType.LIST,
    list_add_processor=chat_summary_add_processor,
    list_add_response=setting_simple_string("Channel <#%s> was added to Chat Summary."),
    list_remove_processor=chat_summary_add_processor,
    list_remove_response=setting_simple_string(
        "Channel <#%s> was removed from Chat Summary."
    ),
    list_view=setting_simple_list_string("Chat summary channels: %s", ", ", "None"),
)

chat_summary_rows = ServerSetting(
    "Chat summary rows",
    setting_type=SettingType.NORMAL,
    normal_processor=chat_summary_rows_processor,
    normal_response=setting_simple_string("Now showing %s rows in Chat Summaries"),
    normal_view=setting_simple_string("Chat Summary shows %s rows per chat summary"),
    default="5",
)

chat_summary_extra = ServerSetting(
    "Chat summary extra summaries",
    setting_type=SettingType.NORMAL,
    normal_processor=setting_to_boolean,
    normal_response=setting_simple_string_boolean(
        "%s extra summaries (yearly, monthly)", "Enabled", "Disabled"
    ),
    normal_view=setting_simple_string_boolean(
        "Monthly and yearly chat summaries are %s", "enabled", "disabled"
    ),
    default="true",
)

chat_summary_rows_extra = ServerSetting(
    "Chat summary rows (monthly, yearly)",
    setting_type=SettingType.NORMAL,
    normal_processor=chat_summary_rows_processor,
    normal_response=setting_simple_string(
        "Chat summary shows %s rows per monthly or yearly chat summary"
    ),
    normal_view=setting_simple_string(
        "Chat summary shows %s rows per monthly or yearly chat summary"
    ),
    default="10",
)

chat_summary_unique = ServerSetting(
    "Chat summary unique mode",
    setting_type=SettingType.NORMAL,
    normal_processor=setting_to_boolean,
    normal_response=setting_simple_string_boolean(
        "Chat Summary %s count messages sent consecutively by one member",
        "won't",
        "will",
    ),
    default="false",
)


def inc(c: Connection, m: Message):
    # Increment for channel

    a = c.execute(
        select(
            chat_summary_channels.c.messages, chat_summary_channels.c.last_member
        ).where(
            (chat_summary_channels.c.gid == str(m.guild.id))
            & (chat_summary_channels.c.cid == str(m.channel.id))
        )
    ).fetchone()
    if a is None:
        c.execute(
            insert(chat_summary_channels).values(
                gid=str(m.guild.id),
                cid=str(m.channel.id),
                messages=1,
                last_member=str(m.author.id),
            )
        )
    else:
        if a[1] != str(m.author.id):
            c.execute(
                update(chat_summary_channels)
                .values(messages=a[0] + 1, last_member=str(m.author.id))
                .where(
                    (chat_summary_channels.c.gid == str(m.guild.id))
                    & (chat_summary_channels.c.cid == str(m.channel.id))
                )
            )

    # Increment for user

    if a is None or a[1] != str(m.author.id):
        a = c.execute(
            select(chat_summary_members.c.messages).where(
                (chat_summary_members.c.gid == str(m.guild.id))
                & (chat_summary_members.c.cid == str(m.channel.id))
                & (chat_summary_members.c.uid == str(m.author.id))
            )
        ).fetchone()
        if a is None:
            c.execute(
                insert(chat_summary_members).values(
                    gid=str(m.guild.id),
                    cid=str(m.channel.id),
                    uid=str(m.author.id),
                    messages=1,
                )
            )
        else:
            c.execute(
                update(chat_summary_members)
                .values(messages=a[0] + 1)
                .where(
                    (chat_summary_members.c.gid == str(m.guild.id))
                    & (chat_summary_members.c.cid == str(m.channel.id))
                    & (chat_summary_members.c.uid == str(m.author.id))
                )
            )

    # Increment monthly

    # Increment for channel

    a = c.execute(
        select(
            monthly_chat_summary_channels.c.messages,
            monthly_chat_summary_channels.c.last_member,
        ).where(
            (monthly_chat_summary_channels.c.gid == str(m.guild.id))
            & (monthly_chat_summary_channels.c.cid == str(m.channel.id))
        )
    ).fetchone()
    if a is None:
        c.execute(
            insert(monthly_chat_summary_channels).values(
                gid=str(m.guild.id),
                cid=str(m.channel.id),
                messages=1,
                last_member=str(m.author.id),
            )
        )
    else:
        if a[1] != str(m.author.id):
            c.execute(
                update(monthly_chat_summary_channels)
                .values(messages=a[0] + 1, last_member=str(m.author.id))
                .where(
                    (monthly_chat_summary_channels.c.gid == str(m.guild.id))
                    & (monthly_chat_summary_channels.c.cid == str(m.channel.id))
                )
            )

    # Increment for user

    if a is None or a[1] != str(m.author.id):
        a = c.execute(
            select(monthly_chat_summary_members.c.messages).where(
                (monthly_chat_summary_members.c.gid == str(m.guild.id))
                & (monthly_chat_summary_members.c.cid == str(m.channel.id))
                & (monthly_chat_summary_members.c.uid == str(m.author.id))
            )
        ).fetchone()
        if a is None:
            c.execute(
                insert(monthly_chat_summary_members).values(
                    gid=str(m.guild.id),
                    cid=str(m.channel.id),
                    uid=str(m.author.id),
                    messages=1,
                )
            )
        else:
            c.execute(
                update(monthly_chat_summary_members)
                .values(messages=a[0] + 1)
                .where(
                    (monthly_chat_summary_members.c.gid == str(m.guild.id))
                    & (monthly_chat_summary_members.c.cid == str(m.channel.id))
                    & (monthly_chat_summary_members.c.uid == str(m.author.id))
                )
            )

    # Increment yearly

    # Increment for channel

    a = c.execute(
        select(
            yearly_chat_summary_channels.c.messages,
            yearly_chat_summary_channels.c.last_member,
        ).where(
            (yearly_chat_summary_channels.c.gid == str(m.guild.id))
            & (yearly_chat_summary_channels.c.cid == str(m.channel.id))
        )
    ).fetchone()
    if a is None:
        c.execute(
            insert(yearly_chat_summary_channels).values(
                gid=str(m.guild.id),
                cid=str(m.channel.id),
                messages=1,
                last_member=str(m.author.id),
            )
        )
    else:
        if a[1] != str(m.author.id):
            c.execute(
                update(yearly_chat_summary_channels)
                .values(messages=a[0] + 1, last_member=str(m.author.id))
                .where(
                    (yearly_chat_summary_channels.c.gid == str(m.guild.id))
                    & (yearly_chat_summary_channels.c.cid == str(m.channel.id))
                )
            )

    # Increment for user

    if a is None or a[1] != str(m.author.id):
        a = c.execute(
            select(yearly_chat_summary_members.c.messages).where(
                (yearly_chat_summary_members.c.gid == str(m.guild.id))
                & (yearly_chat_summary_members.c.cid == str(m.channel.id))
                & (yearly_chat_summary_members.c.uid == str(m.author.id))
            )
        ).fetchone()
        if a is None:
            c.execute(
                insert(yearly_chat_summary_members).values(
                    gid=str(m.guild.id),
                    cid=str(m.channel.id),
                    uid=str(m.author.id),
                    messages=1,
                )
            )
        else:
            c.execute(
                update(yearly_chat_summary_members)
                .values(messages=a[0] + 1)
                .where(
                    (yearly_chat_summary_members.c.gid == str(m.guild.id))
                    & (yearly_chat_summary_members.c.cid == str(m.channel.id))
                    & (yearly_chat_summary_members.c.uid == str(m.author.id))
                )
            )


async def summarize(c: Connection, g: Guild):
    now = datetime.now()
    chat_summaries = chat_summary.get_guild(c, g)
    extra = chat_summary_extra.get_guild(c, g)
    for i in chat_summaries:
        channel = g.get_channel(int(i))

        if extra == "true" and now.month == 1 and now.day == 1:
            total_messages = c.execute(
                select(yearly_chat_summary_channels.c.messages).where(
                    (yearly_chat_summary_channels.c.gid == str(g.id))
                    & (yearly_chat_summary_channels.c.cid == str(channel.id))
                )
            ).fetchone()
            members_messages: list[tuple[str, int]] = [
                (i[0], i[1])
                for i in c.execute(
                    select(
                        yearly_chat_summary_members.c.uid,
                        yearly_chat_summary_members.c.messages,
                    )
                    .where(
                        (yearly_chat_summary_members.c.gid == str(g.id))
                        & (yearly_chat_summary_members.c.cid == str(channel.id))
                    )
                    .order_by(desc(yearly_chat_summary_members.c.messages))
                ).fetchall()
            ]
            msg_begin = "# Yearly Chat Summary"
            rows = int(chat_summary_rows_extra.get_guild(c, g))
        elif extra == "true" and now.day == 1:
            total_messages = c.execute(
                select(monthly_chat_summary_channels.c.messages).where(
                    (monthly_chat_summary_channels.c.gid == str(g.id))
                    & (monthly_chat_summary_channels.c.cid == str(channel.id))
                )
            ).fetchone()
            members_messages: list[tuple[str, int]] = [
                (i[0], i[1])
                for i in c.execute(
                    select(
                        monthly_chat_summary_members.c.uid,
                        monthly_chat_summary_members.c.messages,
                    )
                    .where(
                        (monthly_chat_summary_members.c.gid == str(g.id))
                        & (monthly_chat_summary_members.c.cid == str(channel.id))
                    )
                    .order_by(desc(monthly_chat_summary_members.c.messages))
                ).fetchall()
            ]
            msg_begin = "# Monthly Chat Summary"
            rows = int(chat_summary_rows_extra.get_guild(c, g))
        else:
            total_messages = c.execute(
                select(chat_summary_channels.c.messages).where(
                    (chat_summary_channels.c.gid == str(g.id))
                    & (chat_summary_channels.c.cid == str(channel.id))
                )
            ).fetchone()
            members_messages: list[tuple[str, int]] = [
                (i[0], i[1])
                for i in c.execute(
                    select(chat_summary_members.c.uid, chat_summary_members.c.messages)
                    .where(
                        (chat_summary_members.c.gid == str(g.id))
                        & (chat_summary_members.c.cid == str(channel.id))
                    )
                    .order_by(desc(chat_summary_members.c.messages))
                ).fetchall()
            ]
            msg_begin = "# Chat Summary"
            rows = int(chat_summary_rows.get_guild(c, g))

        if total_messages is None:
            total_messages = (0,)

        total_messages = total_messages[0]

        if len(members_messages) == 0:
            members_messages = []

        msg = (
            f"{msg_begin} for {now.strftime('%Y/%m/%d')}\n"
            f"**Total messages**: {total_messages}\n"
        )

        for j in range(len(members_messages)):
            k = members_messages[j]
            m = await g.fetch_member(int(k[0]))
            if m is not None:
                msg += f"{j + 1}. **{m.display_name}**: {k[1]} messages\n"
            else:
                msg += f"{j + 1}. **<@{k[0]}>**: {k[1]} messages\n"
            if j >= rows - 1:
                break

        ad = get_ad()
        await channel.send(msg, view=ad)

        if now.month == 1 and now.day == 1:
            c.execute(
                delete(yearly_chat_summary_members).where(
                    (yearly_chat_summary_members.c.gid == str(g.id))
                    & (yearly_chat_summary_members.c.cid == str(channel.id))
                )
            )
            c.execute(
                delete(yearly_chat_summary_channels).where(
                    (yearly_chat_summary_channels.c.gid == str(g.id))
                    & (yearly_chat_summary_channels.c.cid == str(channel.id))
                )
            )

        if now.day == 1:
            c.execute(
                delete(monthly_chat_summary_members).where(
                    (monthly_chat_summary_members.c.gid == str(g.id))
                    & (monthly_chat_summary_members.c.cid == str(channel.id))
                )
            )
            c.execute(
                delete(monthly_chat_summary_channels).where(
                    (monthly_chat_summary_channels.c.gid == str(g.id))
                    & (monthly_chat_summary_channels.c.cid == str(channel.id))
                )
            )

        c.execute(
            delete(chat_summary_members).where(
                (chat_summary_members.c.gid == str(g.id))
                & (chat_summary_members.c.cid == str(channel.id))
            )
        )
        c.execute(
            delete(chat_summary_channels).where(
                (chat_summary_channels.c.gid == str(g.id))
                & (chat_summary_channels.c.cid == str(channel.id))
            )
        )


async def perform_backfill(guild: Guild, channel: TextChannel):
    try:
        nekona_logger.debug("[Chat Summary/Backfill: Backfilling channel %s in %s", channel.name, guild.name)
        with engine.begin() as c:
            # Clear the messages
            c.execute(
                delete(chat_summary_members).where(
                    (chat_summary_members.c.gid == str(guild.id))
                    & (chat_summary_members.c.cid == str(channel.id))
                )
            )
            c.execute(
                delete(chat_summary_channels).where(
                    (chat_summary_channels.c.gid == str(guild.id))
                    & (chat_summary_channels.c.cid == str(channel.id))
                )
            )
            c.execute(
                delete(monthly_chat_summary_members).where(
                    (monthly_chat_summary_members.c.gid == str(guild.id))
                    & (monthly_chat_summary_members.c.cid == str(channel.id))
                )
            )
            c.execute(
                delete(monthly_chat_summary_channels).where(
                    (monthly_chat_summary_channels.c.gid == str(guild.id))
                    & (monthly_chat_summary_channels.c.cid == str(channel.id))
                )
            )
            c.execute(
                delete(yearly_chat_summary_members).where(
                    (yearly_chat_summary_members.c.gid == str(guild.id))
                    & (yearly_chat_summary_members.c.cid == str(channel.id))
                )
            )
            c.execute(
                delete(yearly_chat_summary_channels).where(
                    (yearly_chat_summary_channels.c.gid == str(guild.id))
                    & (yearly_chat_summary_channels.c.cid == str(channel.id))
                )
            )

            i = 0

            day_messages = 0
            month_messages = 0
            year_messages = 0

            today = date.today()
            async for message in channel.history(limit=None):
                if message.author.bot:
                    continue

                # Add each message into each group
                if (
                    message.created_at.day == today.day
                    and message.created_at.month == today.month
                ):
                    # Increment for channel

                    a = c.execute(
                        select(
                            chat_summary_channels.c.messages,
                            chat_summary_channels.c.last_member,
                        ).where(
                            (chat_summary_channels.c.gid == str(message.guild.id))
                            & (chat_summary_channels.c.cid == str(message.channel.id))
                        )
                    ).fetchone()
                    if a is None:
                        c.execute(
                            insert(chat_summary_channels).values(
                                gid=str(message.guild.id),
                                cid=str(message.channel.id),
                                messages=1,
                                last_member=str(message.author.id),
                            )
                        )
                    else:
                        if a[1] != str(message.author.id):
                            c.execute(
                                update(chat_summary_channels)
                                .values(
                                    messages=a[0] + 1,
                                    last_member=str(message.author.id),
                                )
                                .where(
                                    (
                                        chat_summary_channels.c.gid
                                        == str(message.guild.id)
                                    )
                                    & (
                                        chat_summary_channels.c.cid
                                        == str(message.channel.id)
                                    )
                                )
                            )

                    # Increment for user

                    if a is None or a[1] != str(message.author.id):
                        a = c.execute(
                            select(chat_summary_members.c.messages).where(
                                (chat_summary_members.c.gid == str(message.guild.id))
                                & (
                                    chat_summary_members.c.cid
                                    == str(message.channel.id)
                                )
                                & (chat_summary_members.c.uid == str(message.author.id))
                            )
                        ).fetchone()
                        if a is None:
                            c.execute(
                                insert(chat_summary_members).values(
                                    gid=str(message.guild.id),
                                    cid=str(message.channel.id),
                                    uid=str(message.author.id),
                                    messages=1,
                                )
                            )
                        else:
                            c.execute(
                                update(chat_summary_members)
                                .values(messages=a[0] + 1)
                                .where(
                                    (
                                        chat_summary_members.c.gid
                                        == str(message.guild.id)
                                    )
                                    & (
                                        chat_summary_members.c.cid
                                        == str(message.channel.id)
                                    )
                                    & (
                                        chat_summary_members.c.uid
                                        == str(message.author.id)
                                    )
                                )
                            )

                    day_messages += 1
                if message.created_at.month == today.month:
                    # Increment for channel

                    a = c.execute(
                        select(
                            monthly_chat_summary_channels.c.messages,
                            monthly_chat_summary_channels.c.last_member,
                        ).where(
                            (
                                monthly_chat_summary_channels.c.gid
                                == str(message.guild.id)
                            )
                            & (
                                monthly_chat_summary_channels.c.cid
                                == str(message.channel.id)
                            )
                        )
                    ).fetchone()
                    if a is None:
                        c.execute(
                            insert(monthly_chat_summary_channels).values(
                                gid=str(message.guild.id),
                                cid=str(message.channel.id),
                                messages=1,
                                last_member=str(message.author.id),
                            )
                        )
                    else:
                        if a[1] != str(message.author.id):
                            c.execute(
                                update(monthly_chat_summary_channels)
                                .values(
                                    messages=a[0] + 1,
                                    last_member=str(message.author.id),
                                )
                                .where(
                                    (
                                        monthly_chat_summary_channels.c.gid
                                        == str(message.guild.id)
                                    )
                                    & (
                                        monthly_chat_summary_channels.c.cid
                                        == str(message.channel.id)
                                    )
                                )
                            )

                    # Increment for user

                    if a is None or a[1] != str(message.author.id):
                        a = c.execute(
                            select(monthly_chat_summary_members.c.messages).where(
                                (
                                    monthly_chat_summary_members.c.gid
                                    == str(message.guild.id)
                                )
                                & (
                                    monthly_chat_summary_members.c.cid
                                    == str(message.channel.id)
                                )
                                & (
                                    monthly_chat_summary_members.c.uid
                                    == str(message.author.id)
                                )
                            )
                        ).fetchone()
                        if a is None:
                            c.execute(
                                insert(monthly_chat_summary_members).values(
                                    gid=str(message.guild.id),
                                    cid=str(message.channel.id),
                                    uid=str(message.author.id),
                                    messages=1,
                                )
                            )
                        else:
                            c.execute(
                                update(monthly_chat_summary_members)
                                .values(messages=a[0] + 1)
                                .where(
                                    (
                                        monthly_chat_summary_members.c.gid
                                        == str(message.guild.id)
                                    )
                                    & (
                                        monthly_chat_summary_members.c.cid
                                        == str(message.channel.id)
                                    )
                                    & (
                                        monthly_chat_summary_members.c.uid
                                        == str(message.author.id)
                                    )
                                )
                            )

                    month_messages += 1
                if message.created_at.year != today.year:
                    break

                # Increment for channel

                a = c.execute(
                    select(
                        yearly_chat_summary_channels.c.messages,
                        yearly_chat_summary_channels.c.last_member,
                    ).where(
                        (yearly_chat_summary_channels.c.gid == str(message.guild.id))
                        & (
                            yearly_chat_summary_channels.c.cid
                            == str(message.channel.id)
                        )
                    )
                ).fetchone()
                if a is None:
                    c.execute(
                        insert(yearly_chat_summary_channels).values(
                            gid=str(message.guild.id),
                            cid=str(message.channel.id),
                            messages=1,
                            last_member=str(message.author.id),
                        )
                    )
                else:
                    if a[1] != str(message.author.id):
                        c.execute(
                            update(yearly_chat_summary_channels)
                            .values(
                                messages=a[0] + 1, last_member=str(message.author.id)
                            )
                            .where(
                                (
                                    yearly_chat_summary_channels.c.gid
                                    == str(message.guild.id)
                                )
                                & (
                                    yearly_chat_summary_channels.c.cid
                                    == str(message.channel.id)
                                )
                            )
                        )

                # Increment for user

                if a is None or a[1] != str(message.author.id):
                    a = c.execute(
                        select(yearly_chat_summary_members.c.messages).where(
                            (yearly_chat_summary_members.c.gid == str(message.guild.id))
                            & (
                                yearly_chat_summary_members.c.cid
                                == str(message.channel.id)
                            )
                            & (
                                yearly_chat_summary_members.c.uid
                                == str(message.author.id)
                            )
                        )
                    ).fetchone()
                    if a is None:
                        c.execute(
                            insert(yearly_chat_summary_members).values(
                                gid=str(message.guild.id),
                                cid=str(message.channel.id),
                                uid=str(message.author.id),
                                messages=1,
                            )
                        )
                    else:
                        c.execute(
                            update(yearly_chat_summary_members)
                            .values(messages=a[0] + 1)
                            .where(
                                (
                                    yearly_chat_summary_members.c.gid
                                    == str(message.guild.id)
                                )
                                & (
                                    yearly_chat_summary_members.c.cid
                                    == str(message.channel.id)
                                )
                                & (
                                    yearly_chat_summary_members.c.uid
                                    == str(message.author.id)
                                )
                            )
                        )

                year_messages += 1

                i += 1
                if i % 500 == 0:
                    # Update status message
                    nekona_logger.debug(
                        "[Chat Summary/Backfill: Processing... %d messages today, %d this month, %d this year",
                        day_messages, month_messages, year_messages)

            nekona_logger.debug(
                "[Chat Summary/Backfill: OK: Task finished: %d messages today, %d messages this month, %d this year",
                day_messages, month_messages, year_messages)
    except Exception:
        nekona_logger.exception("Chat Summary Backfill failed:")
        nekona_logger.debug("[Chat Summary/Backfill: An error occurred")
