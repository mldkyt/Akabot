from flask import Blueprint, flash, redirect, render_template, request, session
from sqlalchemy import delete, insert, select, update

from database import chat_revive_channels, engine, synced_channels, synced_roles
from utils.chat_revive import setting_chat_revive_role
from web.webutils.discord_sync import validate_role_id, validate_text_channel_id
from web.webutils.tokens import authorize, get_token_data

chat_revive_bp = Blueprint("chat_revive", __name__, template_folder="templates")


def handle_settings(auth):
    if "revive_role" in request.form and (
        validate_role_id(request.form["revive_role"])
        or request.form["revive_role"] == "unset"
    ):
        with engine.begin() as c:
            if request.form["revive_role"] == "unset":
                setting_chat_revive_role.set(c, auth["guild"], "")
            else:
                setting_chat_revive_role.set(
                    c, auth["guild"], request.form["revive_role"]
                )


def handle_post(auth, is_edit: bool = False):
    if "channel" not in request.form or "minutes" not in request.form:
        return False

    if not validate_text_channel_id(request.form["channel"]):
        flash("Invalid text channel")
        return False

    if not request.form["minutes"].isnumeric():
        flash("Minutes is not a number")
        return False

    with engine.begin() as c:
        existing = c.execute(
            select(chat_revive_channels.c.id).where(
                (chat_revive_channels.c.gid == str(auth["guild"]))
                & (chat_revive_channels.c.cid == request.form["channel"])
            )
        ).fetchone()

        if existing is not None:
            flash("This channel was already added")
            return False

        c.execute(
            insert(chat_revive_channels).values(
                gid=str(auth["guild"]),
                cid=request.form["channel"],
                minutes=int(request.form["minutes"]),
            )
        )

    if is_edit:
        flash("Edited chat revive")
    else:
        flash("Added chat revive")

    return True


def handle_delete(auth):
    with engine.begin() as c:
        c.execute(
            delete(chat_revive_channels).where(
                (chat_revive_channels.c.gid == str(auth["guild"]))
                & (chat_revive_channels.c.id == request.args["delete"])
            )
        )


@chat_revive_bp.route("/settings/chat_revive", methods=["POST", "GET"])
def chat_revive_index():
    authorization = authorize("/settings/chat_revive")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    if request.method == "POST":
        section = request.form.get("_section", "general")
        if section == "general":
            handle_settings(auth)
            return redirect("/settings/chat_revive?tab=general", 303)

        action = request.form.get("action", "create")
        if action == "create":
            handle_post(auth)
        elif action == "update":
            channel = request.form.get("channel", "")
            minutes = request.form.get("minutes", "")
            revive_id = request.form.get("id", "")
            if (
                revive_id.isnumeric()
                and validate_text_channel_id(channel)
                and minutes.isnumeric()
            ):
                with engine.begin() as c:
                    c.execute(
                        update(chat_revive_channels)
                        .where(
                            (chat_revive_channels.c.gid == str(auth["guild"]))
                            & (chat_revive_channels.c.id == int(revive_id))
                        )
                        .values(cid=channel, minutes=int(minutes))
                    )
                flash("Edited chat revive")
            else:
                flash("Invalid chat revive")
        elif action == "delete":
            revive_id = request.form.get("id", "")
            if revive_id.isnumeric():
                with engine.begin() as c:
                    c.execute(
                        delete(chat_revive_channels).where(
                            (chat_revive_channels.c.gid == str(auth["guild"]))
                            & (chat_revive_channels.c.id == int(revive_id))
                        )
                    )
                flash("Deleted chat revive")

        return redirect("/settings/chat_revive?tab=channels", 303)

    active_tab = request.args.get("tab", "general")
    if active_tab not in {"general", "channels"}:
        active_tab = "general"

    with engine.begin() as c:
        chat_revives = []
        setting_chat_revives = c.execute(
            select(
                chat_revive_channels.c.id,
                chat_revive_channels.c.cid,
                chat_revive_channels.c.minutes,
            )
            .where(chat_revive_channels.c.gid == str(auth["guild"]))
            .order_by(chat_revive_channels.c.id)
        ).fetchall()
        for i in range(len(setting_chat_revives)):
            args = setting_chat_revives[i]
            channel = c.execute(
                select(synced_channels.c.cname).where(
                    (synced_channels.c.gid == str(auth["guild"]))
                    & (synced_channels.c.cid == args[1])
                )
            ).fetchone()

            chat_revives.append(
                {
                    "id": args[0],
                    "index": i,
                    "channel": f"#{channel[0]}" if channel else "Unknown Channel",
                    "channel_id": args[1],
                    "minutes": args[2],
                }
            )

        chat_revive_role = setting_chat_revive_role.get(c, auth["guild"])
        channels = [
            {"id": i[0], "name": i[1]}
            for i in c.execute(
                select(synced_channels.c.cid, synced_channels.c.cname).where(
                    (synced_channels.c.gid == str(auth["guild"]))
                    & (synced_channels.c.ctype == "text")
                )
            ).fetchall()
        ]
        roles = [
            {"id": i[0], "name": i[1]}
            for i in c.execute(
                select(synced_roles.c.rid, synced_roles.c.rname).where(
                    synced_roles.c.gid == str(auth["guild"])
                )
            ).fetchall()
        ]

    return render_template(
        "chat_revive.html",
        chat_revive_role=chat_revive_role,
        roles=roles,
        channels=channels,
        chat_revives=chat_revives,
        active_tab=active_tab,
    )
