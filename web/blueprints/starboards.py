import datetime
import json

from flask import Blueprint, flash, redirect, render_template, request, session
from sqlalchemy import delete, func, insert, select, update

from database import (
    engine,
    starboard_emojis,
    starboard_messages,
    starboards,
    synced_channels,
    synced_emojis,
    tasks,
)
from utils.emoji import CUSTOM_EMOJI_RE
from utils.starboard import (
    MAX_EMOJIS,
    MAX_MIN_COUNT,
    MIN_MIN_COUNT,
    get_emojis,
    setting_starboard_bot_ok,
)
from utils.tasks import create_task
from web.webutils.tokens import authorize, get_token_data

starboards_bp = Blueprint("starboards", __name__, template_folder="templates")


def get_text_channel(c, guild_id: str, channel_id: str):
    return c.execute(
        select(synced_channels.c.cid).where(
            (synced_channels.c.gid == guild_id)
            & (synced_channels.c.cid == channel_id)
            & (synced_channels.c.ctype == "text")
        )
    ).fetchone()


def parse_emojis(form) -> list[str]:
    emojis = []
    for value in form.getlist("emoji"):
        value = value.strip()
        if value and value not in emojis:
            emojis.append(value)
    return emojis


def validate_emojis(c, guild_id: str, emojis: list[str]) -> str | None:
    if not 1 <= len(emojis) <= MAX_EMOJIS:
        return f"Set between 1 and {MAX_EMOJIS} emojis"

    for emoji in emojis:
        if len(emoji) > 64:
            return "One of the emojis is too long"

        if any(character.isspace() for character in emoji):
            return "Emojis cannot contain spaces"

        match = CUSTOM_EMOJI_RE.fullmatch(emoji)
        if match is None:
            if emoji.startswith("<") or emoji.endswith(">"):
                return "Invalid custom emoji"
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


def parse_min_count(value: str | None) -> int | None:
    if value is None or not value.strip().isdigit():
        return None

    count = int(value)
    if not MIN_MIN_COUNT <= count <= MAX_MIN_COUNT:
        return None

    return count


def emoji_display(emoji: str) -> dict:
    match = CUSTOM_EMOJI_RE.fullmatch(emoji)
    if match is not None:
        return {
            "raw": emoji,
            "name": match.group(2),
            "url": f"https://cdn.discordapp.com/emojis/{match.group(3)}.png",
        }

    return {"raw": emoji, "name": emoji, "url": None}


def load_starboard_rows(c, guild_id: str) -> list[dict]:
    rows = c.execute(
        select(starboards)
        .where(starboards.c.gid == guild_id)
        .order_by(starboards.c.id)
    ).fetchall()

    result = []
    for row in rows:
        channel = c.execute(
            select(synced_channels.c.cname).where(
                (synced_channels.c.gid == guild_id)
                & (synced_channels.c.cid == row.cid)
            )
        ).fetchone()

        posted = c.execute(
            select(func.count())
            .select_from(starboard_messages)
            .where(starboard_messages.c.starboard_id == row.id)
        ).scalar()

        result.append(
            {
                "id": row.id,
                "channel_id": row.cid,
                "channel_name": channel[0] if channel is not None else row.cid,
                "min_count": row.min_count,
                "posted": posted or 0,
                "emojis": [
                    emoji_display(emoji) for emoji in get_emojis(c, row.id)
                ],
            }
        )

    return result


def save_create(c, auth, form) -> None:
    channel_id = form.get("channel", "")

    if get_text_channel(c, auth["guild"], channel_id) is None:
        flash("Invalid channel selected")
        return

    existing = c.execute(
        select(starboards.c.id).where(
            (starboards.c.gid == auth["guild"])
            & (starboards.c.cid == channel_id)
        )
    ).fetchone()
    if existing is not None:
        flash("That channel already has a starboard")
        return

    min_count = parse_min_count(form.get("min_count"))
    if min_count is None:
        flash(f"Minimum must be between {MIN_MIN_COUNT} and {MAX_MIN_COUNT}")
        return

    emojis = parse_emojis(form)
    error = validate_emojis(c, auth["guild"], emojis)
    if error is not None:
        flash(error)
        return

    result = c.execute(
        insert(starboards).values(
            gid=auth["guild"],
            cid=channel_id,
            min_count=min_count,
            created_at=datetime.datetime.now(datetime.UTC),
        )
    )
    starboard_id = result.inserted_primary_key[0]

    for position, emoji in enumerate(emojis):
        c.execute(
            insert(starboard_emojis).values(
                starboard_id=starboard_id,
                position=position,
                emoji=emoji,
            )
        )

    flash("Starboard is being created")


def save_update(c, auth, form) -> None:
    starboard_id_value = form.get("id", "")
    if not starboard_id_value.isdigit():
        flash("Invalid starboard")
        return

    starboard_id = int(starboard_id_value)
    row = c.execute(
        select(starboards).where(
            (starboards.c.id == starboard_id)
            & (starboards.c.gid == auth["guild"])
        )
    ).fetchone()
    if row is None:
        flash("Starboard not found")
        return

    channel_id = form.get("channel", "")
    if get_text_channel(c, auth["guild"], channel_id) is None:
        flash("Invalid channel selected")
        return

    conflict = c.execute(
        select(starboards.c.id).where(
            (starboards.c.gid == auth["guild"])
            & (starboards.c.cid == channel_id)
            & (starboards.c.id != starboard_id)
        )
    ).fetchone()
    if conflict is not None:
        flash("That channel already has a starboard")
        return

    min_count = parse_min_count(form.get("min_count"))
    if min_count is None:
        flash(f"Minimum must be between {MIN_MIN_COUNT} and {MAX_MIN_COUNT}")
        return

    emojis = parse_emojis(form)
    error = validate_emojis(c, auth["guild"], emojis)
    if error is not None:
        flash(error)
        return

    c.execute(
        update(starboards)
        .where(starboards.c.id == starboard_id)
        .values(cid=channel_id, min_count=min_count)
    )

    c.execute(
        delete(starboard_emojis).where(
            starboard_emojis.c.starboard_id == starboard_id
        )
    )

    for position, emoji in enumerate(emojis):
        c.execute(
            insert(starboard_emojis).values(
                starboard_id=starboard_id,
                position=position,
                emoji=emoji,
            )
        )

    flash("Saved starboard")


def save_delete(c, auth, form) -> None:
    starboard_id_value = form.get("id") or form.get("delete") or ""
    if not starboard_id_value.isdigit():
        flash("Invalid starboard")
        return

    starboard_id = int(starboard_id_value)
    row = c.execute(
        select(starboards).where(
            (starboards.c.id == starboard_id)
            & (starboards.c.gid == auth["guild"])
        )
    ).fetchone()
    if row is None:
        flash("Starboard not found")
        return

    entries = c.execute(
        select(
            starboard_messages.c.starboard_cid,
            starboard_messages.c.starboard_mid,
        ).where(starboard_messages.c.starboard_id == starboard_id)
    ).fetchall()

    posts = [
        {"cid": entry.starboard_cid, "mid": entry.starboard_mid}
        for entry in entries
    ]
    if posts:
        create_task(
            c,
            "bot",
            "starboards_cleanup",
            {"gid": auth["guild"], "posts": posts},
        )

    c.execute(
        delete(starboard_emojis).where(
            starboard_emojis.c.starboard_id == starboard_id
        )
    )
    c.execute(
        delete(starboard_messages).where(
            starboard_messages.c.starboard_id == starboard_id
        )
    )
    c.execute(delete(starboards).where(starboards.c.id == starboard_id))

    flash("Starboard is being deleted")


def save_dismiss(c, auth, form) -> None:
    if not form.get("dismiss", "").isdigit():
        return

    c.execute(delete(tasks).where(tasks.c.id == int(form["dismiss"])))
    flash("Dismissed task")


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

        if row.type != "starboards_cleanup" or data.get("gid") != guild_id:
            continue

        failed_tasks.append({"id": row.id, "type": row.type, "error": row.error})

    return failed_tasks


@starboards_bp.route("/settings/starboards", methods=["GET", "POST"])
def starboards_index():
    authorization = authorize("/settings/starboards")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    with engine.begin() as c:
        if request.method == "POST":
            action = request.form.get("action")

            if action == "create":
                save_create(c, auth, request.form)
            elif action == "update":
                save_update(c, auth, request.form)
            elif action == "delete":
                save_delete(c, auth, request.form)
            elif action == "dismiss":
                save_dismiss(c, auth, request.form)

            return redirect(
                f"/settings/starboards?tab={request.form.get('_tab', 'starboards')}",
                303,
            )

        active_tab = request.args.get("tab", "starboards")
        if active_tab not in {"starboards", "create"}:
            active_tab = "starboards"

        text_channels = [
            {"id": i[0], "name": i[1]}
            for i in c.execute(
                select(synced_channels.c.cid, synced_channels.c.cname).where(
                    (synced_channels.c.gid == auth["guild"])
                    & (synced_channels.c.ctype == "text")
                )
            ).fetchall()
        ]

        custom_emojis = [
            {"name": i[0], "id": i[1], "animated": bool(i[2])}
            for i in c.execute(
                select(
                    synced_emojis.c.name,
                    synced_emojis.c.eid,
                    synced_emojis.c.animated,
                )
                .where(synced_emojis.c.gid == auth["guild"])
                .order_by(synced_emojis.c.name)
            ).fetchall()
        ]

        starboard_rows = load_starboard_rows(c, auth["guild"])
        failed_tasks = load_failed_tasks(c, auth["guild"])
        bot_ok = setting_starboard_bot_ok.get(c, auth["guild"]) == "true"

    return render_template(
        "starboards.html",
        text_channels=text_channels,
        custom_emojis=custom_emojis,
        starboards=starboard_rows,
        failed_tasks=failed_tasks,
        bot_ok=bot_ok,
        max_emojis=MAX_EMOJIS,
        min_min_count=MIN_MIN_COUNT,
        max_min_count=MAX_MIN_COUNT,
        active_tab=active_tab,
    )
