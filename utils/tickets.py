import datetime

from discord import (
    Bot,
    ButtonStyle,
    CategoryChannel,
    Embed,
    Guild,
    Interaction,
    NotFound,
)
from discord.ui import Button, View
from sqlalchemy import Connection, delete, insert, select, update

from database import engine, ticket_messages, tickets
from logger import akabot_logger
from utils.logs import send_message_to_log_channel
from utils.server_settings import KV
from utils.tasks import register_task
from utils.timezones import get_now

ticket_hide_time = KV(
    name="Ticket hide time",
    default="0",
)

ticket_archive_time = KV(
    name="Ticket archive time",
    default="0",
)


def get_ticket_message(c: Connection, message_id: int):
    return c.execute(
        select(ticket_messages).where(ticket_messages.c.id == message_id)
    ).fetchone()


def get_ticket_message_by_mid(
    c: Connection, guild_id: int, message_id: int
):
    return c.execute(
        select(ticket_messages).where(
            (ticket_messages.c.gid == str(guild_id))
            & (ticket_messages.c.mid == str(message_id))
        )
    ).fetchone()


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


class TicketMessageView(View):
    """View for the message sent on top of every ticket."""

    def __init__(self):
        super().__init__(timeout=None)

        close_button = Button(
            style=ButtonStyle.danger,
            label="Close Ticket",
            custom_id="close_ticket",
        )
        close_button.callback = self.close_ticket
        self.add_item(close_button)

    async def close_ticket(self, interaction: Interaction):
        if interaction.guild is None or interaction.channel is None:
            await interaction.response.send_message(
                "This can only be used in a server.", ephemeral=True
            )
            return

        with engine.begin() as c:
            if not is_ticket_channel(
                c, interaction.guild.id, interaction.channel.id
            ):
                await interaction.response.send_message(
                    "This is not a ticket channel.", ephemeral=True
                )
                return

            hide_hours = int(
                ticket_hide_time.get(c, interaction.guild.id) or 0
            )
            creator_id = get_ticket_creator(
                c, interaction.guild.id, interaction.channel.id
            )

        member = (
            interaction.guild.get_member(creator_id)
            if creator_id is not None
            else None
        )

        if hide_hours > 0:
            if member is not None:
                await interaction.channel.set_permissions(
                    member,
                    view_channel=True,
                    read_messages=True,
                    send_messages=False,
                )
            with engine.begin() as c:
                archive_ticket(
                    c, interaction.guild.id, interaction.channel.id
                )
        else:
            if member is not None:
                await interaction.channel.set_permissions(
                    member,
                    view_channel=False,
                    read_messages=False,
                    send_messages=False,
                )
            with engine.begin() as c:
                remove_ticket(
                    c, interaction.guild.id, interaction.channel.id
                )

        await interaction.channel.send(
            "Ticket closed by " + interaction.user.mention
        )

        if interaction.message is not None:
            # Use a fresh view so disabling the button does not affect the
            # persistent view instance shared by other ticket messages.
            closed_view = TicketMessageView()
            closed_view.disable_all_items()
            await interaction.message.edit(view=closed_view)

        await interaction.response.send_message(
            "Ticket closed!", ephemeral=True
        )


class TicketCreateView(View):
    def __init__(self, button_label: str = "Create Ticket"):
        super().__init__(timeout=None)

        create_button = Button(
            style=ButtonStyle.primary,
            label=button_label,
            custom_id="create_ticket",
        )
        create_button.callback = self.create_ticket
        self.add_item(create_button)

    async def create_ticket(self, interaction: Interaction):
        if interaction.guild is None or interaction.message is None:
            await interaction.response.send_message(
                "This can only be used in a server.", ephemeral=True
            )
            return

        with engine.begin() as c:
            panel = get_ticket_message_by_mid(
                c, interaction.guild.id, interaction.message.id
            )

        if panel is None:
            await interaction.response.send_message(
                "This ticket panel is no longer configured.",
                ephemeral=True,
            )
            return

        category = interaction.guild.get_channel(int(panel.category_id))
        if not isinstance(category, CategoryChannel):
            await interaction.response.send_message(
                "The configured ticket category no longer exists. Please "
                "ping the admins of the server to fix this.",
                ephemeral=True,
            )
            return

        if (
            not interaction.guild.me.guild_permissions.manage_channels
            or not interaction.guild.me.guild_permissions.manage_roles
        ):
            await interaction.response.send_message(
                "The bot needs Manage Channels and Manage Roles permissions "
                "to create tickets.",
                ephemeral=True,
            )
            return

        channel_name = f"{panel.prefix}-{interaction.user.name}"[:100]
        try:
            channel = await category.create_text_channel(
                channel_name,
                topic=f"Ticket for {interaction.user.display_name}",
                reason="Ticket creation",
            )
        except Exception:
            akabot_logger.exception("Failed to create ticket channel")
            await interaction.response.send_message(
                "Failed to create the ticket channel. Please contact the "
                "server admins.",
                ephemeral=True,
            )
            return

        # Set overwrite for the creator of the ticket, so they can see the
        # channel and send messages.
        await channel.set_permissions(
            interaction.user, read_messages=True, send_messages=True
        )

        await channel.send(
            panel.initial_message,
            view=TicketMessageView(),
        )

        with engine.begin() as c:
            add_ticket(
                c,
                interaction.guild.id,
                channel.id,
                interaction.user.id,
            )

        await interaction.response.send_message(
            "Ticket created! " + channel.mention, ephemeral=True
        )

        log_embed = Embed(
            title="Ticket Created",
            description=(
                f"Ticket created by {interaction.user.mention} in "
                f"{channel.mention}"
            ),
        )
        log_embed.add_field(name="Ticket ID", value=str(channel.id))
        log_embed.add_field(
            name="Ticket Creator", value=interaction.user.mention
        )
        log_embed.add_field(name="Ticket Channel", value=channel.mention)
        log_embed.add_field(name="Ticket Category", value=category.name)
        log_embed.add_field(
            name="Ticket Creation Time",
            value=get_now(interaction.guild.id).isoformat(),
        )

        await log_ticket_event(interaction.guild, log_embed)


async def _delete_panel_message(
    bot: Bot, guild_id: str, channel_id: str | None, message_id: str
) -> None:
    if not channel_id or not message_id:
        return

    guild = bot.get_guild(int(guild_id))
    if guild is None:
        return

    channel = guild.get_channel(int(channel_id))
    if channel is None:
        return

    try:
        message = await channel.fetch_message(int(message_id))
    except NotFound:
        return

    await message.delete()


@register_task("tickets_message_create")
async def handle_ticket_message_create(bot: Bot, data: dict) -> None:
    panel_id = data["id"]

    with engine.begin() as c:
        panel = get_ticket_message(c, panel_id)

    if panel is None:
        return

    guild = bot.get_guild(int(panel.gid))
    if guild is None:
        raise ValueError(f"Guild {panel.gid} not found")

    channel = guild.get_channel(int(panel.cid))
    if channel is None:
        raise ValueError(f"Channel {panel.cid} not found")

    if not channel.permissions_for(guild.me).send_messages:
        raise ValueError(f"Missing send messages permission in {channel.name}")

    message = await channel.send(
        content=panel.message,
        view=TicketCreateView(panel.button_label),
    )

    with engine.begin() as c:
        c.execute(
            update(ticket_messages)
            .where(ticket_messages.c.id == panel_id)
            .values(mid=str(message.id))
        )


@register_task("tickets_message_edit")
async def handle_ticket_message_edit(bot: Bot, data: dict) -> None:
    panel_id = data["id"]

    with engine.begin() as c:
        panel = get_ticket_message(c, panel_id)

    if panel is None:
        return

    old_cid = data.get("old_cid")
    old_mid = data.get("old_mid")
    if old_mid and (old_cid != panel.cid or not panel.mid):
        await _delete_panel_message(bot, panel.gid, old_cid, old_mid)

    guild = bot.get_guild(int(panel.gid))
    if guild is None:
        raise ValueError(f"Guild {panel.gid} not found")

    channel = guild.get_channel(int(panel.cid))
    if channel is None:
        raise ValueError(f"Channel {panel.cid} not found")

    if not channel.permissions_for(guild.me).send_messages:
        raise ValueError(f"Missing send messages permission in {channel.name}")

    view = TicketCreateView(panel.button_label)

    if panel.mid:
        try:
            message = await channel.fetch_message(int(panel.mid))
        except NotFound:
            message = None

        if message is not None:
            await message.edit(content=panel.message, view=view)
            return

    message = await channel.send(content=panel.message, view=view)

    with engine.begin() as c:
        c.execute(
            update(ticket_messages)
            .where(ticket_messages.c.id == panel_id)
            .values(mid=str(message.id))
        )


@register_task("tickets_message_delete")
async def handle_ticket_message_delete(bot: Bot, data: dict) -> None:
    mid = data.get("mid")
    if not mid:
        return

    await _delete_panel_message(bot, data["gid"], data["cid"], mid)
