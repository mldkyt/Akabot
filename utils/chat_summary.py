from datetime import datetime

from discord import Message, Guild, Member
from sqlalchemy import Connection, select, insert, update, delete

from database import chat_summary_channels, chat_summary_members, monthly_chat_summary_channels, \
    monthly_chat_summary_members, yearly_chat_summary_channels, yearly_chat_summary_members
from utils.conversion import convert_text_channel
from utils.server_settings import ServerSetting, SettingType, setting_is_number, setting_is_boolean, setting_to_boolean


def chat_summary_add_validator(c: Connection, m: Member, v: str) -> tuple[bool, str]:
    s = v.split(",")
    if len(s) == 2 and s[1].isnumeric():
        chat_convert = convert_text_channel(m.guild, s[0], int(s[1]))
    else:
        chat_convert = convert_text_channel(m.guild, v)

    if chat_convert is None:
        return False, "Invalid channel"
    else:
        return True, ""


def chat_summary_add_transformer(c: Connection, m: Member, v: str) -> str:
    s = v.split(",")
    if len(s) == 2 and s[1].isnumeric():
        chat_convert = convert_text_channel(m.guild, s[0], int(s[1]))
    else:
        chat_convert = convert_text_channel(m.guild, v)

    if chat_convert is None:
        raise ValueError("Value should not be null! This should have been caught by chat_summary_add_validator")

    return str(chat_convert.id)


def chat_summary_add_response(c: Connection, m: Member, v: str) -> str:
    return f"Channel <#{v}> was added to Chat Summary."


def chat_summary_remove_response(c: Connection, m: Member, v: str) -> str:
    return f"Channel <#{v}> was removed from Chat Summary."


def chat_summary_list_view(c: Connection, m: Member, v: list[str]) -> str:
    return "Chat summary channels: " + ", ".join([f"<#{i}>" for i in v])


def chat_summary_rows_validator(c: Connection, m: Member, v: str) -> tuple[bool, str]:
    (ok, err) = setting_is_number(c, m, v)
    if not ok:
        return ok, err

    v = int(v)
    if v <= 0 or v > 10:
        return False, "Invalid range"

    return True, ""


def chat_summary_rows_response(c: Connection, m: Member, v: str) -> str:
    return f"Now showing {v} rows in Chat Summaries"


def chat_summary_extra_response(c: Connection, m: Member, v: str) -> str:
    if v == "true":
        return "Enabled extra summaries (yearly, monthly). These will happen at the end of the month and year."
    elif v == "false":
        return "Disabled extra summaries (yearly, monthly)"
    else:
        return "You're not supposed to see this message, and if you do, tell the developer :3"


def chat_summary_rows_view(c: Connection, m: Member, v: str) -> str:
    return f"Chat summary shows {v} rows per normal summary"

def chat_summary_rows_extra_view(c: Connection, m: Member, v: str) -> str:
    return f"Chat summary shows {v} rows per monthly or yearly chat summary"

def chat_summary_extra_view(c: Connection, m: Member, v: str) -> str:
    return "Monthly and yearly chat summaries are " + ("enabled" if v == "true" else "disabled")

def chat_summary_unique_mode_response(c: Connection, m: Member, v: str) -> str:
    return "Chat summary won't count messages sent consecutively by one member" if v == "true" else \
            "Chat summary will count every message regardless if a member spams"

chat_summary = ServerSetting(
    "Chat summary channels",
    setting_type=SettingType.LIST,
    list_add_validator=chat_summary_add_validator,
    list_add_transformer=chat_summary_add_transformer,
    list_add_response=chat_summary_add_response,
    list_remove_validator=chat_summary_add_validator,
    list_remove_transformer=chat_summary_add_transformer,
    list_remove_response=chat_summary_remove_response,
    list_view=chat_summary_list_view
)

chat_summary_rows = ServerSetting(
    "Chat summary rows",
    setting_type=SettingType.NORMAL,
    normal_validator=chat_summary_rows_validator,
    normal_response=chat_summary_rows_response,
    normal_view=chat_summary_rows_view,
    default="5"
)

chat_summary_extra = ServerSetting(
    "Chat summary extra summaries",
    setting_type=SettingType.NORMAL,
    normal_validator=setting_is_boolean,
    normal_transformer=setting_to_boolean,
    normal_response=chat_summary_extra_response,
    normal_view=chat_summary_extra_view,
    default="true"
)

chat_summary_rows_extra = ServerSetting(
    "Chat summary rows (monthly, yearly)",
    setting_type=SettingType.NORMAL,
    normal_validator=chat_summary_rows_validator,
    normal_response=chat_summary_rows_response,
    normal_view=chat_summary_rows_extra_view,
    default="10"
)

chat_summary_unique = ServerSetting(
    "Chat summary unique mode",
    setting_type=SettingType.NORMAL,
    normal_validator=setting_is_boolean,
    normal_transformer=setting_to_boolean,
    normal_response=chat_summary_unique_mode_response,
    default="false"
)

def inc(c: Connection, m: Message):
    # Increment for channel

    a = c.execute(
        select(chat_summary_channels.c.messages, chat_summary_channels.c.last_member)
        .where((chat_summary_channels.c.gid == str(m.guild.id)) & (chat_summary_channels.c.cid == str(m.channel.id)))
    ).fetchone()
    if a is None:
        c.execute(
            insert(chat_summary_channels)
            .values(gid=str(m.guild.id), cid=str(m.channel.id), messages=1, last_member=str(m.author.id))
        )
    else:
        if a[1] != str(m.author.id):
            c.execute(
                update(chat_summary_channels)
                .values(messages=a[0] + 1, last_member=str(m.author.id))
                .where(
                    (chat_summary_channels.c.gid == str(m.guild.id)) & (chat_summary_channels.c.cid == str(m.channel.id)))
            )

    # Increment for user

    if a is None or a[1] != str(m.author.id):
        a = c.execute(
            select(chat_summary_members.c.messages)
            .where((chat_summary_members.c.gid == str(m.guild.id)) & (chat_summary_members.c.cid == str(m.channel.id)) & (
                    chat_summary_members.c.uid == str(m.author.id)))
        ).fetchone()
        if a is None:
            c.execute(
                insert(chat_summary_members)
                .values(gid=str(m.guild.id), cid=str(m.channel.id), uid=str(m.author.id), messages=1)
            )
        else:
            c.execute(
                update(chat_summary_members)
                .values(messages=a[0] + 1)
                .where(
                    (chat_summary_members.c.gid == str(m.guild.id)) & (chat_summary_members.c.cid == str(m.channel.id)) & (
                            chat_summary_members.c.uid == str(m.author.id)))
            )

    # Increment monthly

    # Increment for channel

    a = c.execute(
        select(monthly_chat_summary_channels.c.messages, monthly_chat_summary_channels.c.last_member)
        .where(
            (monthly_chat_summary_channels.c.gid == str(m.guild.id)) & (
                        monthly_chat_summary_channels.c.cid == str(m.channel.id)))
    ).fetchone()
    if a is None:
        c.execute(
            insert(monthly_chat_summary_channels)
            .values(gid=str(m.guild.id), cid=str(m.channel.id), messages=1, last_member=str(m.author.id))
        )
    else:
        if a[1] != str(m.author.id):
            c.execute(
                update(monthly_chat_summary_channels)
                .values(messages=a[0] + 1, last_member=str(m.author.id))
                .where(
                    (monthly_chat_summary_channels.c.gid == str(m.guild.id)) & (
                            monthly_chat_summary_channels.c.cid == str(m.channel.id)))
            )

    # Increment for user

    if a is None or a[1] != str(m.author.id):
        a = c.execute(
            select(monthly_chat_summary_members.c.messages)
            .where(
                (monthly_chat_summary_members.c.gid == str(m.guild.id)) & (
                            monthly_chat_summary_members.c.cid == str(m.channel.id)) & (
                        monthly_chat_summary_members.c.uid == str(m.author.id)))
        ).fetchone()
        if a is None:
            c.execute(
                insert(monthly_chat_summary_members)
                .values(gid=str(m.guild.id), cid=str(m.channel.id), uid=str(m.author.id), messages=1)
            )
        else:
            c.execute(
                update(monthly_chat_summary_members)
                .values(messages=a[0] + 1)
                .where(
                    (monthly_chat_summary_members.c.gid == str(m.guild.id)) & (
                            monthly_chat_summary_members.c.cid == str(m.channel.id)) & (
                            monthly_chat_summary_members.c.uid == str(m.author.id)))
            )

    # Increment yearly

    # Increment for channel

    a = c.execute(
        select(yearly_chat_summary_channels.c.messages, yearly_chat_summary_channels.c.last_member)
        .where(
            (yearly_chat_summary_channels.c.gid == str(m.guild.id)) & (
                    yearly_chat_summary_channels.c.cid == str(m.channel.id)))
    ).fetchone()
    if a is None:
        c.execute(
            insert(yearly_chat_summary_channels)
            .values(gid=str(m.guild.id), cid=str(m.channel.id), messages=1, last_member=str(m.author.id))
        )
    else:
        if a[1] != str(m.author.id):
            c.execute(
                update(yearly_chat_summary_channels)
                .values(messages=a[0] + 1, last_member=str(m.author.id))
                .where(
                    (yearly_chat_summary_channels.c.gid == str(m.guild.id)) & (
                            yearly_chat_summary_channels.c.cid == str(m.channel.id)))
            )

    # Increment for user

    if a is None or a[1] != str(m.author.id):
        a = c.execute(
            select(yearly_chat_summary_members.c.messages)
            .where(
                (yearly_chat_summary_members.c.gid == str(m.guild.id)) & (
                        yearly_chat_summary_members.c.cid == str(m.channel.id)) & (
                        yearly_chat_summary_members.c.uid == str(m.author.id)))
        ).fetchone()
        if a is None:
            c.execute(
                insert(yearly_chat_summary_members)
                .values(gid=str(m.guild.id), cid=str(m.channel.id), uid=str(m.author.id), messages=1)
            )
        else:
            c.execute(
                update(yearly_chat_summary_members)
                .values(messages=a[0] + 1)
                .where(
                    (yearly_chat_summary_members.c.gid == str(m.guild.id)) & (
                            yearly_chat_summary_members.c.cid == str(m.channel.id)) & (
                            yearly_chat_summary_members.c.uid == str(m.author.id)))
            )


async def summarize(c: Connection, g: Guild):
    now = datetime.now()
    chat_summaries = chat_summary.get_direct(c, g)
    extra = chat_summary_extra.get_direct(c, g)
    for i in chat_summaries:
        channel = g.get_channel(int(i))

        if extra == "true" and now.month == 1 and now.day == 1:
            total_messages = c.execute(
                select(yearly_chat_summary_channels.c.messages)
                .where((yearly_chat_summary_channels.c.gid == str(g.id)) & (
                            yearly_chat_summary_channels.c.cid == str(channel.id)))
            ).fetchone()
            members_messages: list[tuple[str, int]] = [(i[0], i[1]) for i in c.execute(
                select(yearly_chat_summary_members.c.uid, yearly_chat_summary_members.c.messages)
                .where((yearly_chat_summary_members.c.gid == str(g.id)) & (
                            yearly_chat_summary_members.c.cid == str(channel.id)))
            ).fetchall()]
            msg_begin = "# Yearly Chat Summary"
            rows = int(chat_summary_rows_extra.get_direct(c, g))
        elif extra == "true" and now.day == 1:
            total_messages = c.execute(
                select(monthly_chat_summary_channels.c.messages)
                .where((monthly_chat_summary_channels.c.gid == str(g.id)) & (
                        monthly_chat_summary_channels.c.cid == str(channel.id)))
            ).fetchone()
            members_messages: list[tuple[str, int]] = [(i[0], i[1]) for i in c.execute(
                select(monthly_chat_summary_members.c.uid, monthly_chat_summary_members.c.messages)
                .where((monthly_chat_summary_members.c.gid == str(g.id)) & (
                            monthly_chat_summary_members.c.cid == str(channel.id)))
            ).fetchall()]
            msg_begin = "# Monthly Chat Summary"
            rows = int(chat_summary_rows_extra.get_direct(c, g))
        else:
            total_messages = c.execute(
                select(chat_summary_channels.c.messages)
                .where((chat_summary_channels.c.gid == str(g.id)) & (chat_summary_channels.c.cid == str(channel.id)))
            ).fetchone()
            members_messages: list[tuple[str, int]] = [(i[0], i[1]) for i in c.execute(
                select(chat_summary_members.c.uid, chat_summary_members.c.messages)
                .where((chat_summary_members.c.gid == str(g.id)) & (chat_summary_members.c.cid == str(channel.id)))
            ).fetchall()]
            msg_begin = "# Chat Summary"
            rows = int(chat_summary_rows.get_direct(c, g))

        if total_messages is None:
            total_messages = (0,)

        total_messages = total_messages[0]

        if len(members_messages) == 0:
            members_messages = []

        msg = (f"{msg_begin} for {now.strftime('%Y/%m/%d')}\n"
               f"**Total messages**: {total_messages}\n")

        for j in range(len(members_messages)):
            k = members_messages[j]
            msg += f"{j + 1}. **<@{k[0]}>**: {k[1]} messages\n"
            if j >= rows - 1:
                break

        msg += "\n-# Chat Summaries provided by Nekona :3"
        await channel.send(msg)

        if now.month == 1 and now.day == 1:
            c.execute(
                delete(yearly_chat_summary_members)
                .where((yearly_chat_summary_members.c.gid == str(g.id)) & (
                            yearly_chat_summary_members.c.cid == str(channel.id)))
            )
            c.execute(
                delete(yearly_chat_summary_channels)
                .where((yearly_chat_summary_channels.c.gid == str(g.id)) & (
                            yearly_chat_summary_channels.c.cid == str(channel.id)))
            )

        if now.day == 1:
            c.execute(
                delete(monthly_chat_summary_members)
                .where((monthly_chat_summary_members.c.gid == str(g.id)) & (
                        monthly_chat_summary_members.c.cid == str(channel.id)))
            )
            c.execute(
                delete(monthly_chat_summary_channels)
                .where((monthly_chat_summary_channels.c.gid == str(g.id)) & (
                            monthly_chat_summary_channels.c.cid == str(channel.id)))
            )

        c.execute(
            delete(chat_summary_members)
            .where((chat_summary_members.c.gid == str(g.id)) & (chat_summary_members.c.cid == str(channel.id)))
        )
        c.execute(
            delete(chat_summary_channels)
            .where((chat_summary_channels.c.gid == str(g.id)) & (chat_summary_channels.c.cid == str(channel.id)))
        )
