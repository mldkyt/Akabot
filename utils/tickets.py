import datetime

from discord import Bot, Embed, Guild
from sqlalchemy import Connection, delete, insert, select, update

from database import engine, tickets
from logger import akabot_logger
from utils.logs import send_message_to_log_channel
from utils.server_settings import KV
from utils.timezones import get_now

ticket_category = KV(
    name="Ticket category",
    default="0",
)

ticket_hide_time = KV(
    name="Ticket hide time",
    default="0",
)

ticket_archive_time = KV(
    name="Ticket archive time",
    default="0",
)


def add_ticket(
    c: Connection, guild_id: int, channel_id: int, user_id: int
) -> None:
    c.execute(
        insert(tickets).values(
            gid=str(guild_id),
            cid=str(channel_id),
            uid=str(user_id),
            last_activity=get_now(guild_id, c),
        )
    )


def is_ticket_channel(
    c: Connection, guild_id: int, channel_id: int
) -> bool:
    row = c.execute(
        select(tickets.c.cid).where(
            (tickets.c.gid == str(guild_id))
            & (tickets.c.cid == str(channel_id))
        )
    ).fetchone()
    return row is not None


def get_ticket_creator(
    c: Connection, guild_id: int, channel_id: int
) -> int | None:
    row = c.execute(
        select(tickets.c.uid).where(
            (tickets.c.gid == str(guild_id))
            & (tickets.c.cid == str(channel_id))
        )
    ).fetchone()
    if row is None:
        return None

    try:
        return int(row[0])
    except (TypeError, ValueError):
        return None


def remove_ticket(c: Connection, guild_id: int, channel_id: int) -> None:
    c.execute(
        delete(tickets).where(
            (tickets.c.gid == str(guild_id))
            & (tickets.c.cid == str(channel_id))
        )
    )


def update_last_activity(
    c: Connection, guild_id: int, channel_id: int
) -> None:
    c.execute(
        update(tickets)
        .values(last_activity=get_now(guild_id, c))
        .where(
            (tickets.c.gid == str(guild_id))
            & (tickets.c.cid == str(channel_id))
        )
    )


def archive_ticket(c: Connection, guild_id: int, channel_id: int) -> None:
    c.execute(
        update(tickets)
        .values(archived_at=get_now(guild_id, c))
        .where(
            (tickets.c.gid == str(guild_id))
            & (tickets.c.cid == str(channel_id))
        )
    )


def is_archived(c: Connection, guild_id: int, channel_id: int) -> bool:
    row = c.execute(
        select(tickets.c.archived_at).where(
            (tickets.c.gid == str(guild_id))
            & (tickets.c.cid == str(channel_id))
        )
    ).fetchone()
    return row is not None and row[0] is not None


def list_archived_tickets(c: Connection):
    return c.execute(
        select(tickets).where(tickets.c.archived_at.is_not(None))
    ).fetchall()


def list_not_archived_tickets(c: Connection):
    return c.execute(
        select(tickets).where(tickets.c.archived_at.is_(None))
    ).fetchall()


def check_archive_time(
    c: Connection, guild_id: int, channel_id: int
) -> bool:
    archive_hours = int(ticket_archive_time.get(c, guild_id) or 0)
    if archive_hours <= 0:
        return False

    row = c.execute(
        select(tickets.c.last_activity).where(
            (tickets.c.gid == str(guild_id))
            & (tickets.c.cid == str(channel_id))
        )
    ).fetchone()
    if row is None or row[0] is None:
        return False

    return get_now(guild_id, c) - row[0] >= datetime.timedelta(
        hours=archive_hours
    )


def check_hide_time(c: Connection, guild_id: int, channel_id: int) -> bool:
    hide_hours = int(ticket_hide_time.get(c, guild_id) or 0)
    if hide_hours <= 0:
        return False

    row = c.execute(
        select(tickets.c.archived_at).where(
            (tickets.c.gid == str(guild_id))
            & (tickets.c.cid == str(channel_id))
        )
    ).fetchone()
    if row is None or row[0] is None:
        return False

    return get_now(guild_id, c) - row[0] >= datetime.timedelta(
        hours=hide_hours
    )


async def log_ticket_event(guild: Guild, embed: Embed) -> None:
    try:
        with engine.begin() as c:
            await send_message_to_log_channel(c, guild, "tickets", embed)
    except Exception:
        akabot_logger.exception("Failed to send ticket log event")


async def archive_inactive_tickets(bot: Bot) -> None:
    try:
        with engine.begin() as c:
            rows = list_not_archived_tickets(c)
            expired = []
            for row in rows:
                guild_id = int(row.gid)
                channel_id = int(row.cid)

                if not check_archive_time(c, guild_id, channel_id):
                    continue

                expired.append(
                    {
                        "gid": guild_id,
                        "cid": channel_id,
                        "uid": int(row.uid),
                        "hide_hours": int(
                            ticket_hide_time.get(c, guild_id) or 0
                        ),
                    }
                )
    except Exception:
        akabot_logger.exception(
            "Failed to find inactive tickets to archive"
        )
        return

    for ticket in expired:
        try:
            guild = bot.get_guild(ticket["gid"])
            if guild is None:
                continue

            channel = guild.get_channel(ticket["cid"])
            if channel is None:
                with engine.begin() as c:
                    remove_ticket(c, ticket["gid"], ticket["cid"])
                continue

            member = guild.get_member(ticket["uid"])

            if ticket["hide_hours"] > 0:
                if member is not None:
                    await channel.set_permissions(
                        member,
                        view_channel=True,
                        read_messages=True,
                        send_messages=False,
                    )
                with engine.begin() as c:
                    archive_ticket(c, ticket["gid"], ticket["cid"])
            else:
                if member is not None:
                    await channel.set_permissions(
                        member,
                        view_channel=False,
                        read_messages=False,
                        send_messages=False,
                    )
                with engine.begin() as c:
                    remove_ticket(c, ticket["gid"], ticket["cid"])

            await channel.send(
                "Ticket closed automatically because there was no activity "
                "for a certain amount of time."
            )

            log_embed = Embed(
                title="Ticket Closed Automatically",
                description=(
                    "Ticket closed automatically by the system in "
                    f"{channel.mention} because there was no activity for a "
                    "certain amount of time."
                ),
            )
            log_embed.add_field(
                name="Ticket Closed Automatically Time",
                value=get_now(guild.id).isoformat(),
            )
            log_embed.add_field(
                name="Ticket Closed Automatically Message",
                value=channel.jump_url,
            )

            await log_ticket_event(guild, log_embed)
        except Exception:
            akabot_logger.exception(
                f"Failed to archive ticket {ticket['cid']} in guild "
                f"{ticket['gid']}"
            )


async def hide_archived_tickets(bot: Bot) -> None:
    try:
        with engine.begin() as c:
            rows = list_archived_tickets(c)
            expired = []
            for row in rows:
                guild_id = int(row.gid)
                channel_id = int(row.cid)

                if not check_hide_time(c, guild_id, channel_id):
                    continue

                expired.append(
                    {
                        "gid": guild_id,
                        "cid": channel_id,
                        "uid": int(row.uid),
                    }
                )
    except Exception:
        akabot_logger.exception("Failed to find tickets to hide")
        return

    for ticket in expired:
        try:
            guild = bot.get_guild(ticket["gid"])
            if guild is None:
                continue

            channel = guild.get_channel(ticket["cid"])
            if channel is None:
                with engine.begin() as c:
                    remove_ticket(c, ticket["gid"], ticket["cid"])
                continue

            member = guild.get_member(ticket["uid"])
            if member is not None:
                await channel.set_permissions(
                    member,
                    view_channel=False,
                    read_messages=False,
                    send_messages=False,
                )

            with engine.begin() as c:
                remove_ticket(c, ticket["gid"], ticket["cid"])

            log_embed = Embed(
                title="Ticket Hidden",
                description=(
                    "Ticket hidden by the system in "
                    f"{channel.mention} because the hide time is up."
                ),
            )
            log_embed.add_field(
                name="Ticket Hidden Time",
                value=get_now(guild.id).isoformat(),
            )
            log_embed.add_field(
                name="Ticket Hidden Message",
                value=channel.jump_url,
            )

            await log_ticket_event(guild, log_embed)
        except Exception:
            akabot_logger.exception(
                f"Failed to hide ticket {ticket['cid']} in guild "
                f"{ticket['gid']}"
            )
