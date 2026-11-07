import json
import re

from flask import Blueprint, flash, redirect, render_template, request, session
from sqlalchemy import delete, insert, select, update

from database import engine, synced_channels, tasks, ticket_messages
from utils.tasks import create_task
from utils.tickets import ticket_archive_time, ticket_hide_time
from web.webutils.tokens import authorize, get_token_data

tickets_bp = Blueprint("tickets", __name__, template_folder="templates")

PREFIX_RE = re.compile(r"^[a-z]{1,8}$")
MAX_BUTTON_LABEL = 80
MAX_MESSAGE_LENGTH = 2000


def get_synced_channel(c, guild_id: str, channel_id: str, ctype: str):
    return c.execute(
        select(synced_channels.c.cid).where(
            (synced_channels.c.gid == guild_id)
            & (synced_channels.c.cid == channel_id)
            & (synced_channels.c.ctype == ctype)
        )
    ).fetchone()


def get_channel_name(c, guild_id: str, channel_id: str) -> str:
    row = c.execute(
        select(synced_channels.c.cname).where(
            (synced_channels.c.gid == guild_id)
            & (synced_channels.c.cid == channel_id)
        )
    ).fetchone()
    return row[0] if row is not None else channel_id


def parse_hours(value: str | None) -> int | None:
    if value is None:
        return None

    value = value.strip()
    if not value.isdigit():
        return None

    return int(value)


def parse_panel(c, guild_id: str, form, panel_id: int | None = None):
    channel_id = form.get("channel", "")
    prefix = form.get("prefix", "").strip()
    category_id = form.get("category", "")
    initial_message = form.get("initial_message", "")
    message = form.get("message", "")
    button_label = form.get("button_label", "").strip() or "Create Ticket"

    if get_synced_channel(c, guild_id, channel_id, "text") is None:
        flash("Invalid channel selected")
        return None

    if PREFIX_RE.fullmatch(prefix) is None:
        flash("Prefix must be 1 to 8 lowercase letters")
        return None

    conflict_query = select(ticket_messages.c.id).where(
        (ticket_messages.c.gid == guild_id)
        & (ticket_messages.c.prefix == prefix)
    )
    if panel_id is not None:
        conflict_query = conflict_query.where(ticket_messages.c.id != panel_id)

    if c.execute(conflict_query).fetchone() is not None:
        flash("That prefix is already in use")
        return None

    if get_synced_channel(c, guild_id, category_id, "category") is None:
        flash("Invalid category selected")
        return None

    if not initial_message.strip():
        flash("Initial message cannot be empty")
        return None

    if len(initial_message) > MAX_MESSAGE_LENGTH:
        flash(f"Initial message must be {MAX_MESSAGE_LENGTH} characters or fewer")
        return None

    if not message.strip():
        flash("Panel message cannot be empty")
        return None

    if len(message) > MAX_MESSAGE_LENGTH:
        flash(f"Panel message must be {MAX_MESSAGE_LENGTH} characters or fewer")
        return None

    if len(button_label) > MAX_BUTTON_LABEL:
        flash(f"Button label must be {MAX_BUTTON_LABEL} characters or fewer")
        return None

    return {
        "cid": channel_id,
        "prefix": prefix,
        "category_id": category_id,
        "initial_message": initial_message,
        "message": message,
        "button_label": button_label,
    }


def save_settings(c, auth, form) -> None:
    archive_time = parse_hours(form.get("archive_time"))
    hide_time = parse_hours(form.get("hide_time"))

    if archive_time is None or hide_time is None:
        flash("Times must be non-negative whole numbers")
        return

    ticket_archive_time.set(c, auth["guild"], str(archive_time))
    ticket_hide_time.set(c, auth["guild"], str(hide_time))
    flash("Ticket settings saved")


def save_create(c, auth, form) -> None:
    panel = parse_panel(c, auth["guild"], form)
    if panel is None:
        return

    result = c.execute(
        insert(ticket_messages).values(gid=auth["guild"], **panel)
    )
    panel_id = result.inserted_primary_key[0]

    create_task(
        c,
        "bot",
        "tickets_message_create",
        {"id": panel_id, "gid": auth["guild"]},
    )
    flash("Ticket message is being created")


def save_edit(c, auth, form) -> None:
    if not form.get("id", "").isdigit():
        flash("Invalid ticket message")
        return

    panel_id = int(form["id"])
    row = c.execute(
        select(ticket_messages).where(
            (ticket_messages.c.id == panel_id)
            & (ticket_messages.c.gid == auth["guild"])
        )
    ).fetchone()
    if row is None:
        flash("Ticket message not found")
        return

    panel = parse_panel(c, auth["guild"], form, panel_id)
    if panel is None:
        return

    channel_changed = row.cid != panel["cid"]
    old_cid = row.cid
    old_mid = row.mid

    c.execute(
        update(ticket_messages)
        .where(ticket_messages.c.id == panel_id)
        .values(mid=None if channel_changed else row.mid, **panel)
    )

    create_task(
        c,
        "bot",
        "tickets_message_edit",
        {
            "id": panel_id,
            "gid": auth["guild"],
            "old_cid": old_cid,
            "old_mid": old_mid,
        },
    )
    flash("Ticket message is being updated")


def save_delete(c, auth, form) -> None:
    panel_id_value = form.get("id") or form.get("delete") or ""
    if not panel_id_value.isdigit():
        flash("Invalid ticket message")
        return

    panel_id = int(panel_id_value)
    row = c.execute(
        select(ticket_messages).where(
            (ticket_messages.c.id == panel_id)
            & (ticket_messages.c.gid == auth["guild"])
        )
    ).fetchone()
    if row is None:
        flash("Ticket message not found")
        return

    create_task(
        c,
        "bot",
        "tickets_message_delete",
        {"gid": row.gid, "cid": row.cid, "mid": row.mid},
    )
    c.execute(
        delete(ticket_messages).where(ticket_messages.c.id == panel_id)
    )
    flash("Ticket message is being deleted")


def save_dismiss(c, auth, form) -> None:
    if not form.get("dismiss", "").isdigit():
        return

    c.execute(delete(tasks).where(tasks.c.id == int(form["dismiss"])))
    flash("Dismissed task")


def load_panels(c, guild_id: str) -> list[dict]:
    rows = c.execute(
        select(ticket_messages)
        .where(ticket_messages.c.gid == guild_id)
        .order_by(ticket_messages.c.id)
    ).fetchall()

    return [
        {
            "id": row.id,
            "channel_id": row.cid,
            "channel_name": get_channel_name(c, guild_id, row.cid),
            "mid": row.mid,
            "prefix": row.prefix,
            "category_id": row.category_id,
            "category_name": get_channel_name(
                c, guild_id, row.category_id
            ),
            "initial_message": row.initial_message,
            "message": row.message,
            "button_label": row.button_label,
        }
        for row in rows
    ]


def load_failed_tasks(c, guild_id: str) -> list[dict]:
    failed_tasks = []
    for row in c.execute(
        select(tasks.c.id, tasks.c.type, tasks.c.data, tasks.c.error)
        .where((tasks.c.direction == "bot") & (tasks.c.error.is_not(None)))
        .order_by(tasks.c.id.desc())
    ).fetchall():
        try:
            data = json.loads(row.data)
        except (TypeError, ValueError):
            data = {}

        if data.get("gid") != guild_id:
            continue

        if not row.type.startswith("tickets_message_"):
            continue

        failed_tasks.append({"id": row.id, "type": row.type, "error": row.error})

    return failed_tasks


@tickets_bp.route("/settings/tickets", methods=["GET", "POST"])
def tickets_index():
    authorization = authorize("/settings/tickets")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    with engine.begin() as c:
        if request.method == "POST":
            action = request.form.get("action")

            if action == "settings":
                save_settings(c, auth, request.form)
            elif action == "create":
                save_create(c, auth, request.form)
            elif action == "edit":
                save_edit(c, auth, request.form)
            elif action == "delete":
                save_delete(c, auth, request.form)
            elif action == "dismiss":
                save_dismiss(c, auth, request.form)

            return redirect(
                f"/settings/tickets?tab={request.form.get('_tab', 'messages')}",
                303,
            )

        active_tab = request.args.get("tab", "messages")
        if active_tab not in {"messages", "settings"}:
            active_tab = "messages"

        text_channels = [
            {"id": i[0], "name": i[1]}
            for i in c.execute(
                select(synced_channels.c.cid, synced_channels.c.cname)
                .where(
                    (synced_channels.c.gid == auth["guild"])
                    & (synced_channels.c.ctype == "text")
                )
                .order_by(synced_channels.c.cname)
            ).fetchall()
        ]

        categories = [
            {"id": i[0], "name": i[1]}
            for i in c.execute(
                select(synced_channels.c.cid, synced_channels.c.cname)
                .where(
                    (synced_channels.c.gid == auth["guild"])
                    & (synced_channels.c.ctype == "category")
                )
                .order_by(synced_channels.c.cname)
            ).fetchall()
        ]

        panels = load_panels(c, auth["guild"])
        failed_tasks = load_failed_tasks(c, auth["guild"])
        archive_time = int(ticket_archive_time.get(c, auth["guild"]) or 0)
        hide_time = int(ticket_hide_time.get(c, auth["guild"]) or 0)

    return render_template(
        "tickets.html",
        text_channels=text_channels,
        categories=categories,
        panels=panels,
        failed_tasks=failed_tasks,
        archive_time=archive_time,
        hide_time=hide_time,
        max_button_label=MAX_BUTTON_LABEL,
        max_message_length=MAX_MESSAGE_LENGTH,
        active_tab=active_tab,
    )
