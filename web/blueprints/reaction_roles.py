import datetime
import json

from flask import Blueprint, flash, redirect, render_template, request, session
from sqlalchemy import delete, insert, select, update

from database import (
    engine,
    reaction_roles,
    reaction_roles_options,
    synced_channels,
    synced_emojis,
    synced_roles,
    tasks,
)
from utils.reaction_roles import CUSTOM_EMOJI_RE, setting_reaction_roles_bot_ok
from utils.tasks import create_task
from web.webutils.tokens import authorize, get_token_data

reaction_roles_bp = Blueprint(
    "reaction_roles", __name__, template_folder="templates"
)

MAX_OPTIONS = 20
ALLOWED_STYLES = ("primary", "secondary", "success", "danger")


def get_limit(c, guild_id: str, default: int) -> int:
    """Return the reaction role message limit for a guild."""
    return default


def get_text_channel(c, guild_id: str, channel_id: str):
    return c.execute(
        select(synced_channels.c.cid).where(
            (synced_channels.c.gid == guild_id)
            & (synced_channels.c.cid == channel_id)
            & (synced_channels.c.ctype == "text")
        )
    ).fetchone()


def get_role(c, guild_id: str, role_id: str):
    return c.execute(
        select(synced_roles.c.rid).where(
            (synced_roles.c.gid == guild_id) & (synced_roles.c.rid == role_id)
        )
    ).fetchone()


def parse_options(form) -> list[dict]:
    roles = form.getlist("role")
    labels = form.getlist("label")
    emojis = form.getlist("emoji")
    styles = form.getlist("style")

    options = []
    for i in range(len(roles)):
        options.append(
            {
                "rid": roles[i].strip(),
                "label": labels[i].strip() if i < len(labels) else "",
                "emoji": emojis[i].strip() if i < len(emojis) else "",
                "style": styles[i].strip() if i < len(styles) else "primary",
            }
        )

    return options


def validate_options(c, guild_id: str, options: list[dict]) -> str | None:
    if not 1 <= len(options) <= MAX_OPTIONS:
        return f"Set between 1 and {MAX_OPTIONS} roles"

    seen = set()
    for option in options:
        if not option["rid"].isdigit() or get_role(c, guild_id, option["rid"]) is None:
            return "Invalid role selected"

        if option["rid"] in seen:
            return "Each role can only be used once"

        seen.add(option["rid"])

        if option["style"] not in ALLOWED_STYLES:
            return "Invalid button style"

        if not option["emoji"]:
            continue

        match = CUSTOM_EMOJI_RE.fullmatch(option["emoji"])
        if match is None:
            continue

        found = c.execute(
            select(synced_emojis.c.eid).where(
                (synced_emojis.c.gid == guild_id)
                & (synced_emojis.c.eid == match.group(3))
            )
        ).fetchone()
        if found is None:
            return "Custom emojis must be from this server"

    return None


def option_display(c, guild_id: str, option) -> dict:
    role = c.execute(
        select(synced_roles.c.rname).where(
            (synced_roles.c.gid == guild_id) & (synced_roles.c.rid == option.rid)
        )
    ).fetchone()

    emoji = option.emoji or ""
    emoji_url = None
    match = CUSTOM_EMOJI_RE.fullmatch(emoji)
    if match is not None:
        emoji_url = f"https://cdn.discordapp.com/emojis/{match.group(3)}.png"

    return {
        "id": option.id,
        "rid": option.rid,
        "label": option.label or "",
        "emoji": emoji,
        "emoji_url": emoji_url,
        "style": option.style or "primary",
        "role_name": role[0] if role is not None else option.rid,
    }


def save_create(c, auth, form) -> None:
    channel_id = form.get("channel", "")
    rr_type = form.get("type", "n")
    content = form.get("content", "")

    if rr_type not in ("n", "a", "r", "s"):
        flash("Invalid reaction role type")
        return

    if get_text_channel(c, auth["guild"], channel_id) is None:
        flash("Invalid channel selected")
        return

    options = parse_options(form)
    error = validate_options(c, auth["guild"], options)
    if error is not None:
        flash(error)
        return

    limit = get_limit(c, auth["guild"], 3)
    count = len(
        c.execute(
            select(reaction_roles.c.id).where(reaction_roles.c.gid == auth["guild"])
        ).fetchall()
    )
    if limit is not None and count >= limit:
        flash("Free plan is limited to 3 reaction role messages")
        return

    now = datetime.datetime.now(datetime.UTC)
    result = c.execute(
        insert(reaction_roles).values(
            gid=auth["guild"],
            cid=channel_id,
            type=rr_type,
            content=content,
            created_at=now,
        )
    )
    rr_id = result.inserted_primary_key[0]

    for position, option in enumerate(options):
        c.execute(
            insert(reaction_roles_options).values(
                rr_id=rr_id,
                position=position,
                style=option["style"],
                label=option["label"] or None,
                emoji=option["emoji"] or None,
                rid=option["rid"],
            )
        )

    create_task(c, "bot", "reactionRoles_create", {"id": rr_id, "gid": auth["guild"]})
    flash("Reaction role is being created")


def save_edit(c, auth, form) -> None:
    if not form.get("id", "").isdigit():
        flash("Invalid reaction role")
        return

    rr_id = int(form["id"])
    row = c.execute(
        select(reaction_roles).where(
            (reaction_roles.c.id == rr_id) & (reaction_roles.c.gid == auth["guild"])
        )
    ).fetchone()
    if row is None:
        flash("Reaction role not found")
        return

    rr_type = form.get("type", "n")
    content = form.get("content", "")

    if rr_type not in ("n", "a", "r", "s"):
        flash("Invalid reaction role type")
        return

    options = parse_options(form)
    error = validate_options(c, auth["guild"], options)
    if error is not None:
        flash(error)
        return

    existing = {
        i.rid: i
        for i in c.execute(
            select(reaction_roles_options).where(
                reaction_roles_options.c.rr_id == rr_id
            )
        ).fetchall()
    }
    new_rids = [option["rid"] for option in options]

    for option in existing.values():
        if option.rid not in new_rids:
            c.execute(
                delete(reaction_roles_options).where(
                    reaction_roles_options.c.id == option.id
                )
            )

    for position, option in enumerate(options):
        if option["rid"] in existing:
            c.execute(
                update(reaction_roles_options)
                .where(reaction_roles_options.c.id == existing[option["rid"]].id)
                .values(
                    position=position,
                    style=option["style"],
                    label=option["label"] or None,
                    emoji=option["emoji"] or None,
                )
            )
        else:
            c.execute(
                insert(reaction_roles_options).values(
                    rr_id=rr_id,
                    position=position,
                    style=option["style"],
                    label=option["label"] or None,
                    emoji=option["emoji"] or None,
                    rid=option["rid"],
                )
            )

    c.execute(
        update(reaction_roles)
        .where(reaction_roles.c.id == rr_id)
        .values(type=rr_type, content=content)
    )

    create_task(c, "bot", "reactionRoles_edit", {"id": rr_id, "gid": auth["guild"]})
    flash("Reaction role is being updated")


def save_delete(c, auth, form) -> None:
    rr_id_value = form.get("id") or form.get("delete") or ""
    if not rr_id_value.isdigit():
        flash("Invalid reaction role")
        return

    rr_id = int(rr_id_value)
    row = c.execute(
        select(reaction_roles).where(
            (reaction_roles.c.id == rr_id) & (reaction_roles.c.gid == auth["guild"])
        )
    ).fetchone()
    if row is None:
        flash("Reaction role not found")
        return

    create_task(
        c,
        "bot",
        "reactionRoles_delete",
        {"gid": row.gid, "cid": row.cid, "mid": row.mid},
    )
    c.execute(
        delete(reaction_roles_options).where(reaction_roles_options.c.rr_id == rr_id)
    )
    c.execute(delete(reaction_roles).where(reaction_roles.c.id == rr_id))
    flash("Reaction role is being deleted")


def save_dismiss(c, auth, form) -> None:
    if not form.get("dismiss", "").isdigit():
        return

    c.execute(delete(tasks).where(tasks.c.id == int(form["dismiss"])))
    flash("Dismissed task")


@reaction_roles_bp.route("/settings/reaction_roles", methods=["GET", "POST"])
def reaction_roles_index():
    authorization = authorize("/settings/reaction_roles")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    with engine.begin() as c:
        if request.method == "POST":
            action = request.form.get("action")

            if action == "create":
                save_create(c, auth, request.form)
            elif action == "edit":
                save_edit(c, auth, request.form)
            elif action == "delete":
                save_delete(c, auth, request.form)
            elif action == "dismiss":
                save_dismiss(c, auth, request.form)

            return redirect(
                f"/settings/reaction_roles?tab={request.form.get('_tab', 'messages')}",
                303,
            )

        active_tab = request.args.get("tab", "messages")
        if active_tab not in {"messages", "create"}:
            active_tab = "messages"

        text_channels = [
            {"id": i[0], "name": i[1]}
            for i in c.execute(
                select(synced_channels.c.cid, synced_channels.c.cname).where(
                    (synced_channels.c.gid == auth["guild"])
                    & (synced_channels.c.ctype == "text")
                )
            ).fetchall()
        ]

        roles = [
            {"id": i[0], "name": i[1]}
            for i in c.execute(
                select(synced_roles.c.rid, synced_roles.c.rname).where(
                    synced_roles.c.gid == auth["guild"]
                )
            ).fetchall()
        ]

        emojis = [
            {"name": i[0], "id": i[1], "animated": bool(i[2])}
            for i in c.execute(
                select(synced_emojis.c.name, synced_emojis.c.eid, synced_emojis.c.animated)
                .where(synced_emojis.c.gid == auth["guild"])
                .order_by(synced_emojis.c.name)
            ).fetchall()
        ]

        reaction_role_list = []
        for row in c.execute(
            select(reaction_roles)
            .where(reaction_roles.c.gid == auth["guild"])
            .order_by(reaction_roles.c.id)
        ).fetchall():
            channel = c.execute(
                select(synced_channels.c.cname).where(
                    (synced_channels.c.cid == row.cid)
                    & (synced_channels.c.gid == auth["guild"])
                )
            ).fetchone()

            options = [
                option_display(c, auth["guild"], option)
                for option in c.execute(
                    select(reaction_roles_options)
                    .where(reaction_roles_options.c.rr_id == row.id)
                    .order_by(
                        reaction_roles_options.c.position,
                        reaction_roles_options.c.id,
                    )
                ).fetchall()
            ]

            reaction_role_list.append(
                {
                    "id": row.id,
                    "channel_id": row.cid,
                    "channel_name": channel[0] if channel is not None else row.cid,
                    "mid": row.mid,
                    "type": row.type,
                    "content": row.content or "",
                    "options": options,
                }
            )

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

            if data.get("gid") != auth["guild"]:
                continue

            failed_tasks.append({"id": row.id, "type": row.type, "error": row.error})

        bot_ok = setting_reaction_roles_bot_ok.get(c, auth["guild"]) == "true"

    return render_template(
        "reaction_roles.html",
        text_channels=text_channels,
        roles=roles,
        emojis=emojis,
        reaction_roles=reaction_role_list,
        failed_tasks=failed_tasks,
        bot_ok=bot_ok,
        max_options=MAX_OPTIONS,
        active_tab=active_tab,
    )
