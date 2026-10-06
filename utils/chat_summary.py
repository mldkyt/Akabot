import datetime

import sentry_sdk
from discord import (
    ButtonStyle,
    Guild,
    Interaction,
    Message,
    TextChannel,
)
from discord.ui import Button, View
from sqlalchemy import Connection, delete, desc, insert, select, update

from database import (
    chat_summary_channels,
    chat_summary_members,
    engine,
    monthly_chat_summary_channels,
    monthly_chat_summary_members,
    past_chat_summaries,
    past_chat_summaries_rows,
    yearly_chat_summary_channels,
    yearly_chat_summary_members,
)
from logger import akabot_logger
from utils.ads import get_ad
from utils.premium import has_premium
from utils.server_settings import (
    ServerSetting,
    SettingType,
)
from utils.timezones import get_now

chat_summary = ServerSetting(
    "Chat summary channels",
    setting_type=SettingType.LIST,
)

chat_summary_rows = ServerSetting(
    "Chat summary rows",
    setting_type=SettingType.NORMAL,
    default="5",
)

chat_summary_extra = ServerSetting(
    "Chat summary extra summaries",
    setting_type=SettingType.NORMAL,
    default="true",
)

chat_summary_rows_extra = ServerSetting(
    "Chat summary rows (monthly, yearly)",
    setting_type=SettingType.NORMAL,
    default="10",
)

chat_summary_unique = ServerSetting(
    "Chat summary unique mode",
    setting_type=SettingType.NORMAL,
    default="false",
)

chat_summary_history = ServerSetting(
    "Chat summary history",
    setting_type=SettingType.NORMAL,
    default="true",
)


def inc(c: Connection, m: Message):
    # With unique mode on, consecutive messages from the same author count once.
    unique = chat_summary_unique.get(c, m.guild.id) == "true"

    # Increment for channel

    a = c.execute(
        select(
            chat_summary_channels.c.messages, chat_summary_channels.c.last_member
        ).where(
            (chat_summary_channels.c.gid == str(m.guild.id))
            & (chat_summary_channels.c.cid == str(m.channel.id))
        )
    ).fetchone()
    collapsed = unique and a is not None and a[1] == str(m.author.id)
    if a is None:
        c.execute(
            insert(chat_summary_channels).values(
                gid=str(m.guild.id),
                cid=str(m.channel.id),
                messages=1,
                last_member=str(m.author.id),
            )
        )
    elif not collapsed:
        c.execute(
            update(chat_summary_channels)
            .values(messages=a[0] + 1, last_member=str(m.author.id))
            .where(
                (chat_summary_channels.c.gid == str(m.guild.id))
                & (chat_summary_channels.c.cid == str(m.channel.id))
            )
        )

    # Increment for user

    if not collapsed:
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
                    last_message=datetime.datetime.now(datetime.UTC),
                )
            )
        else:
            c.execute(
                update(chat_summary_members)
                .values(
                    messages=a[0] + 1, last_message=datetime.datetime.now(datetime.UTC)
                )
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
    collapsed = unique and a is not None and a[1] == str(m.author.id)
    if a is None:
        c.execute(
            insert(monthly_chat_summary_channels).values(
                gid=str(m.guild.id),
                cid=str(m.channel.id),
                messages=1,
                last_member=str(m.author.id),
            )
        )
    elif not collapsed:
        c.execute(
            update(monthly_chat_summary_channels)
            .values(messages=a[0] + 1, last_member=str(m.author.id))
            .where(
                (monthly_chat_summary_channels.c.gid == str(m.guild.id))
                & (monthly_chat_summary_channels.c.cid == str(m.channel.id))
            )
        )

    # Increment for user

    if not collapsed:
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
    collapsed = unique and a is not None and a[1] == str(m.author.id)
    if a is None:
        c.execute(
            insert(yearly_chat_summary_channels).values(
                gid=str(m.guild.id),
                cid=str(m.channel.id),
                messages=1,
                last_member=str(m.author.id),
            )
        )
    elif not collapsed:
        c.execute(
            update(yearly_chat_summary_channels)
            .values(messages=a[0] + 1, last_member=str(m.author.id))
            .where(
                (yearly_chat_summary_channels.c.gid == str(m.guild.id))
                & (yearly_chat_summary_channels.c.cid == str(m.channel.id))
            )
        )

    # Increment for user

    if not collapsed:
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


class SummaryHistoryView(View):
    def __init__(self, ad_view: View | None = None):
        super().__init__(timeout=None)
        show_more_btn = Button(
            label="Show more",
            style=ButtonStyle.primary,
            custom_id="summary_history:show_more",
        )
        show_more_btn.callback = self.show_more
        self.add_item(show_more_btn)
        if ad_view is not None:
            for item in ad_view.children:
                self.add_item(item)

    async def show_more(self, interaction: Interaction):
        assert interaction.message is not None

        summary_id = str(interaction.message.id)

        with engine.begin() as c:
            rows = c.execute(
                select(
                    past_chat_summaries_rows.c.uid,
                    past_chat_summaries_rows.c.messages,
                    past_chat_summaries_rows.c.rank,
                )
                .where(past_chat_summaries_rows.c.summary_id == summary_id)
                .order_by(past_chat_summaries_rows.c.rank)
            ).fetchall()

        if not rows:
            await interaction.response.send_message("No more data available", ephemeral=True)
            return

        pages = []
        page_size = 10
        for start in range(0, len(rows), page_size):
            chunk = rows[start:start + page_size]
            page_text = ""
            for row in chunk:
                member = interaction.guild.get_member(int(row[0]))
                if member is None:
                    try:
                        member = interaction.guild.get_member(int(row[0]))
                    except Exception:
                        akabot_logger.exception(
                            f"Failed to resolve member {row[0]} for chat summary pagination"
                        )
                        member = None
                if member is not None:
                    page_text += f"{row[2]}. **{member.display_name}**: {row[1]} messages\n"
                else:
                    page_text += f"{row[2]}. **<@{row[0]}>**: {row[1]} messages\n"
            pages.append(page_text)

        from discord.ext.pages import Paginator

        paginator = Paginator(pages)
        await paginator.respond(interaction, ephemeral=True)


async def summarize(c: Connection, g: Guild):
    now = get_now(g.id, c)
    yesterday = now - datetime.timedelta(days=1)
    chat_summaries = chat_summary.get(c, g.id)
    premium = has_premium(c, g.id)
    extra = chat_summary_extra.get(c, g.id) == "true" and premium
    history_enabled = chat_summary_history.get(c, g.id) == "true" and premium

    for i in chat_summaries:
        channel = g.get_channel(int(i))

        if extra and now.month == 1 and now.day == 1:
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
                    .order_by(
                        desc(yearly_chat_summary_members.c.messages),
                        desc(yearly_chat_summary_members.c.last_message),
                    )
                ).fetchall()
            ]
            msg_begin = "# Yearly Chat Summary"
            rows = int(chat_summary_rows_extra.get(c, g.id))
            kind = "yearly"
            period = str(yesterday.year)
        elif extra and now.day == 1:
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
                    .order_by(
                        desc(monthly_chat_summary_members.c.messages),
                        desc(monthly_chat_summary_members.c.last_message),
                    )
                ).fetchall()
            ]
            msg_begin = "# Monthly Chat Summary"
            rows = int(chat_summary_rows_extra.get(c, g.id))
            kind = "monthly"
            period = yesterday.strftime("%Y-%m")
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
                    .order_by(
                        desc(chat_summary_members.c.messages),
                        desc(chat_summary_members.c.last_message),
                    )
                ).fetchall()
            ]
            msg_begin = "# Chat Summary"
            rows = int(chat_summary_rows.get(c, g.id))
            kind = "daily"
            period = yesterday.strftime("%Y-%m-%d")

        if total_messages is None:
            total_messages = (0,)

        total_messages = total_messages[0]

        if len(members_messages) == 0:
            members_messages = []

        msg = (
            f"{msg_begin} for {yesterday.strftime('%Y/%m/%d')}\n"
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
        if history_enabled and len(members_messages) > rows:
            ad = SummaryHistoryView(ad_view=ad)

        sent_msg = await channel.send(msg, view=ad)

        if history_enabled:
            c.execute(
                insert(past_chat_summaries).values(
                    id=str(sent_msg.id),
                    gid=str(g.id),
                    cid=str(channel.id),
                    kind=kind,
                    period=period,
                    total_messages=total_messages,
                    created_at=datetime.datetime.now(datetime.UTC),
                )
            )
            for idx, (uid, msgs) in enumerate(members_messages):
                c.execute(
                    insert(past_chat_summaries_rows).values(
                        summary_id=str(sent_msg.id),
                        uid=uid,
                        messages=msgs,
                        rank=idx + 1,
                    )
                )

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
        with engine.begin() as c:
            today = get_now(guild.id, c).date()
            unique = chat_summary_unique.get(c, guild.id) == "true"
        daily_data = {}
        monthly_data = {}
        yearly_data = {}

        async for message in channel.history(limit=None):
            if message.author.bot:
                continue

            msg_date = message.created_at.date()
            if msg_date.year != today.year:
                continue

            gid = str(guild.id)
            cid = str(channel.id)
            uid = str(message.author.id)

            year_key = (gid, cid)
            year_data = yearly_data.setdefault(year_key, {"messages": 0, "last_member": None})
            if not unique or year_data["last_member"] != uid:
                year_data["messages"] += 1
                year_data["last_member"] = uid
                year_user = yearly_data.setdefault((gid, cid, uid), {"messages": 0})
                year_user["messages"] += 1

            if msg_date.month == today.month:
                month_key = (gid, cid)
                month_data = monthly_data.setdefault(month_key, {"messages": 0, "last_member": None})
                if not unique or month_data["last_member"] != uid:
                    month_data["messages"] += 1
                    month_data["last_member"] = uid
                    month_user = monthly_data.setdefault((gid, cid, uid), {"messages": 0})
                    month_user["messages"] += 1

                if msg_date.day == today.day:
                    day_key = (gid, cid)
                    day_data = daily_data.setdefault(day_key, {"messages": 0, "last_member": None})
                    if not unique or day_data["last_member"] != uid:
                        day_data["messages"] += 1
                        day_data["last_member"] = uid
                        day_user = daily_data.setdefault((gid, cid, uid), {"messages": 0})
                        day_user["messages"] += 1

        with engine.begin() as c:
            for key, data in daily_data.items():
                if "last_member" in data:
                    gid, cid = key
                    existing = c.execute(
                        select(
                            chat_summary_channels.c.messages,
                            chat_summary_channels.c.last_member,
                        ).where(
                            (chat_summary_channels.c.gid == gid)
                            & (chat_summary_channels.c.cid == cid)
                        )
                    ).fetchone()
                    if existing is None:
                        c.execute(
                            insert(chat_summary_channels).values(
                                gid=gid,
                                cid=cid,
                                messages=data["messages"],
                                last_member=data["last_member"],
                            )
                        )
                    else:
                        c.execute(
                            update(chat_summary_channels)
                            .values(
                                messages=existing[0] + data["messages"],
                                last_member=data["last_member"],
                            )
                            .where(
                                (chat_summary_channels.c.gid == gid)
                                & (chat_summary_channels.c.cid == cid)
                            )
                        )
                else:
                    gid, cid, uid = key
                    existing = c.execute(
                        select(chat_summary_members.c.messages).where(
                            (chat_summary_members.c.gid == gid)
                            & (chat_summary_members.c.cid == cid)
                            & (chat_summary_members.c.uid == uid)
                        )
                    ).fetchone()
                    if existing is None:
                        c.execute(
                            insert(chat_summary_members).values(
                                gid=gid,
                                cid=cid,
                                uid=uid,
                                messages=data["messages"],
                            )
                        )
                    else:
                        c.execute(
                            update(chat_summary_members)
                            .values(messages=existing[0] + data["messages"])
                            .where(
                                (chat_summary_members.c.gid == gid)
                                & (chat_summary_members.c.cid == cid)
                                & (chat_summary_members.c.uid == uid)
                            )
                        )

            for key, data in monthly_data.items():
                if "last_member" in data:
                    gid, cid = key
                    existing = c.execute(
                        select(
                            monthly_chat_summary_channels.c.messages,
                            monthly_chat_summary_channels.c.last_member,
                        ).where(
                            (monthly_chat_summary_channels.c.gid == gid)
                            & (monthly_chat_summary_channels.c.cid == cid)
                        )
                    ).fetchone()
                    if existing is None:
                        c.execute(
                            insert(monthly_chat_summary_channels).values(
                                gid=gid,
                                cid=cid,
                                messages=data["messages"],
                                last_member=data["last_member"],
                            )
                        )
                    else:
                        c.execute(
                            update(monthly_chat_summary_channels)
                            .values(
                                messages=existing[0] + data["messages"],
                                last_member=data["last_member"],
                            )
                            .where(
                                (monthly_chat_summary_channels.c.gid == gid)
                                & (monthly_chat_summary_channels.c.cid == cid)
                            )
                        )
                else:
                    gid, cid, uid = key
                    existing = c.execute(
                        select(monthly_chat_summary_members.c.messages).where(
                            (monthly_chat_summary_members.c.gid == gid)
                            & (monthly_chat_summary_members.c.cid == cid)
                            & (monthly_chat_summary_members.c.uid == uid)
                        )
                    ).fetchone()
                    if existing is None:
                        c.execute(
                            insert(monthly_chat_summary_members).values(
                                gid=gid,
                                cid=cid,
                                uid=uid,
                                messages=data["messages"],
                            )
                        )
                    else:
                        c.execute(
                            update(monthly_chat_summary_members)
                            .values(messages=existing[0] + data["messages"])
                            .where(
                                (monthly_chat_summary_members.c.gid == gid)
                                & (monthly_chat_summary_members.c.cid == cid)
                                & (monthly_chat_summary_members.c.uid == uid)
                            )
                        )

            for key, data in yearly_data.items():
                if "last_member" in data:
                    gid, cid = key
                    existing = c.execute(
                        select(
                            yearly_chat_summary_channels.c.messages,
                            yearly_chat_summary_channels.c.last_member,
                        ).where(
                            (yearly_chat_summary_channels.c.gid == gid)
                            & (yearly_chat_summary_channels.c.cid == cid)
                        )
                    ).fetchone()
                    if existing is None:
                        c.execute(
                            insert(yearly_chat_summary_channels).values(
                                gid=gid,
                                cid=cid,
                                messages=data["messages"],
                                last_member=data["last_member"],
                            )
                        )
                    else:
                        c.execute(
                            update(yearly_chat_summary_channels)
                            .values(
                                messages=existing[0] + data["messages"],
                                last_member=data["last_member"],
                            )
                            .where(
                                (yearly_chat_summary_channels.c.gid == gid)
                                & (yearly_chat_summary_channels.c.cid == cid)
                            )
                        )
                else:
                    gid, cid, uid = key
                    existing = c.execute(
                        select(yearly_chat_summary_members.c.messages).where(
                            (yearly_chat_summary_members.c.gid == gid)
                            & (yearly_chat_summary_members.c.cid == cid)
                            & (yearly_chat_summary_members.c.uid == uid)
                        )
                    ).fetchone()
                    if existing is None:
                        c.execute(
                            insert(yearly_chat_summary_members).values(
                                gid=gid,
                                cid=cid,
                                uid=uid,
                                messages=data["messages"],
                            )
                        )
                    else:
                        c.execute(
                            update(yearly_chat_summary_members)
                            .values(messages=existing[0] + data["messages"])
                            .where(
                                (yearly_chat_summary_members.c.gid == gid)
                                & (yearly_chat_summary_members.c.cid == cid)
                                & (yearly_chat_summary_members.c.uid == uid)
                            )
                        )
    except Exception as e:
        akabot_logger.exception(f"Failed to summarize chat for guild {gid}: {e}")
        sentry_sdk.capture_exception(e)
