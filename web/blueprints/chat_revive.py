from flask import Blueprint, render_template, session, request, flash, redirect
from sqlalchemy import delete, insert, select

from database import chat_revive_channels, engine, synced_channels, synced_roles
from utils.chat_revive import setting_chat_revive_role
from utils.premium import get_limit, get_premium_context
from web.webutils.discord_sync import validate_text_channel_id, validate_role_id
from web.webutils.tokens import authorize, get_token_data

chat_revive_bp = Blueprint("chat_revive", __name__, template_folder='templates')


def handle_settings(auth):
    if "revive_role" in request.form and (
            validate_role_id(request.form["revive_role"]) or request.form["revive_role"] == "unset"):
        with engine.begin() as c:
            if request.form["revive_role"] == "unset":
                setting_chat_revive_role.set(c, auth["guild"], "")
            else:
                setting_chat_revive_role.set(c, auth["guild"], request.form["revive_role"])


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
        free_tier = get_premium_context(c, auth["guild"])["premium_only"]

        if free_tier and int(request.form["minutes"]) < 60:
            flash("Free plan cannot set the chat revive interval below 60 minutes")
            return False

        limit = get_limit(c, auth["guild"], 1)
        existing = c.execute(
            select(chat_revive_channels.c.id).where(
                (chat_revive_channels.c.gid == str(auth["guild"]))
                & (chat_revive_channels.c.cid == request.form["channel"])
            )
        ).fetchone()

        if existing is not None:
            flash("This channel was already added")
            return False

        current = c.execute(
            select(chat_revive_channels.c.id).where(
                chat_revive_channels.c.gid == str(auth["guild"])
            )
        ).fetchall()
        if limit is not None and len(current) >= limit:
            flash("Free plan is limited to 1 chat revive channel")
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


@chat_revive_bp.route("/settings/chat_revive", methods=["POST", "GET"])
def chat_revive_index():
    authorization = authorize("/settings/chat_revive")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    if request.method == "POST":
        handle_post(auth)
        handle_settings(auth)

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
                select(synced_channels.c.cname)
                .where((synced_channels.c.gid == str(auth["guild"])) & (synced_channels.c.cid == args[1]))
            ).fetchone()

            chat_revives.append({
                "index": i,
                "channel": f"#{channel[0]}" if channel else "Unknown Channel",
                "channel_id": args[1],
                "minutes": args[2]
            })

        chat_revive_role = setting_chat_revive_role.get(c, auth["guild"])
        channels = [{
            "id": i[0],
            "name": i[1]
        } for i in c.execute(
            select(synced_channels.c.cid, synced_channels.c.cname)
            .where((synced_channels.c.gid == str(auth["guild"])) & (synced_channels.c.ctype == "text"))
        ).fetchall()]
        roles = [{
            "id": i[0],
            "name": i[1]
        } for i in c.execute(
            select(synced_roles.c.rid, synced_roles.c.rname)
            .where(synced_roles.c.gid == str(auth["guild"]))
        ).fetchall()]

        premium = get_premium_context(c, auth["guild"])

    return render_template("chat_revive.html", chat_revive_role=chat_revive_role, roles=roles, channels=channels,
                           chat_revives=chat_revives, premium=premium)


@chat_revive_bp.route("/settings/chat_revive/delete/<index>")
def chat_revive_delete(index: str):
    authorization = authorize("/settings/chat_revive")
    if authorization is not None:
        return authorization

    if not index.isnumeric():
        return redirect("/settings/chat_revive", 302)

    auth = get_token_data(session["token"])
    assert auth is not None

    with engine.begin() as c:
        chat_revives = c.execute(
            select(
                chat_revive_channels.c.id,
                chat_revive_channels.c.cid,
                chat_revive_channels.c.minutes,
            )
            .where(chat_revive_channels.c.gid == str(auth["guild"]))
            .order_by(chat_revive_channels.c.id)
        ).fetchall()
        if len(chat_revives) <= int(index):
            return redirect("/settings/chat_revive", 302)

        chat_revive = chat_revives[int(index)]

        channel_info = c.execute(
            select(synced_channels.c.cname)
            .where((synced_channels.c.cid == chat_revive[1]) & (synced_channels.c.gid == str(auth["guild"])))
        ).fetchone()

    if "confirm" in request.args and request.args["confirm"] == "yes":
        with engine.begin() as c:
            c.execute(
                delete(chat_revive_channels).where(chat_revive_channels.c.id == chat_revive[0])
            )

        return redirect("/settings/chat_revive", 303)

    chat_revive_parsed = {
        "index": int(index),
        "channel": channel_info[0] if channel_info else "Unknown Channel",
        "minutes": chat_revive[2]
    }

    return render_template("chat_revive_delete.html", chat_revive=chat_revive_parsed)


@chat_revive_bp.route("/settings/chat_revive/edit/<index>", methods=["POST"])
def chat_revive_edit(index: str):
    authorization = authorize("/settings/chat_revive")
    if authorization is not None:
        return authorization

    if not index.isnumeric():
        return redirect("/settings/chat_revive", 302)

    auth = get_token_data(session["token"])
    assert auth is not None

    with engine.begin() as c:
        chat_revives = c.execute(
            select(chat_revive_channels.c.id)
            .where(chat_revive_channels.c.gid == str(auth["guild"]))
            .order_by(chat_revive_channels.c.id)
        ).fetchall()
        if len(chat_revives) <= int(index):
            return redirect("/settings/chat_revive", 302)

        c.execute(
            delete(chat_revive_channels).where(chat_revive_channels.c.id == chat_revives[int(index)][0])
        )
        handle_post(auth, is_edit=True)
        return redirect("/settings/chat_revive", 303)
