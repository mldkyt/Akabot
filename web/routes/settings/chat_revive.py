from flask import Blueprint, render_template, session, request, flash, redirect
from sqlalchemy import select

from database import engine, synced_channels, synced_roles
from utils.chat_revive import setting_chat_revive_channels, setting_chat_revive_role
from web.webutils.discord_sync import validate_text_channel_id, validate_role_id
from web.webutils.tokens import authorize, get_token_data

chat_revive_bp = Blueprint("chat_revive", __name__, template_folder='templates')


def handle_settings(auth):
    if "revive_role" in request.form and (
            validate_role_id(request.form["revive_role"]) or request.form["revive_role"] == "unset"):
        with engine.begin() as c:
            if request.form["revive_role"] == "unset":
                setting_chat_revive_role.direct_set(c, auth["guild"], "")
            else:
                setting_chat_revive_role.direct_set(c, auth["guild"], request.form["revive_role"])


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
        setting_chat_revive_channels.add_to_list(c, auth["guild"],
                                                 f"{request.form['channel']};{request.form['minutes']}")

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
        setting_chat_revives = setting_chat_revive_channels.get(c, auth["guild"])
        for i in range(len(setting_chat_revives)):
            args = setting_chat_revives[i].split(";")
            channel = c.execute(
                select(synced_channels.c.cname)
                .where((synced_channels.c.gid == str(auth["guild"])) & (synced_channels.c.cid == args[0]))
            ).fetchone()

            chat_revives.append({
                "index": i,
                "channel": f"#{channel[0]}",
                "minutes": args[1]
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

    return render_template("chat_revive.html", chat_revive_role=chat_revive_role, roles=roles, channels=channels,
                           chat_revives=chat_revives)


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
        chat_revives = setting_chat_revive_channels.get(c, auth["guild"])
        chat_revive = chat_revives[int(index)].split(";")

        channel_info = c.execute(
            select(synced_channels.c.cname)
            .where((synced_channels.c.cid == chat_revive[0]) & (synced_channels.c.gid == str(auth["guild"])))
        ).fetchone()

    if len(chat_revives) <= int(index):
        return redirect("/settings/chat_revive", 302)

    if "confirm" in request.args and request.args["confirm"] == "yes":
        with engine.begin() as c:
            setting_chat_revive_channels.remove_from_list(c, auth["guild"], chat_revives[int(index)])

        return redirect("/settings/chat_revive", 303)

    chat_revive_parsed = {
        "index": int(index),
        "channel": channel_info[0],
        "minutes": chat_revive[1]
    }

    return render_template("chat_revive_delete.html", chat_revive=chat_revive_parsed)


@chat_revive_bp.route("/settings/chat_revive/edit/<index>", methods=["GET", "POST"])
def chat_revive_edit(index: str):
    authorization = authorize("/settings/chat_revive")
    if authorization is not None:
        return authorization

    if not index.isnumeric():
        return redirect("/settings/chat_revive", 302)

    auth = get_token_data(session["token"])
    assert auth is not None

    with engine.begin() as c:
        chat_revives = setting_chat_revive_channels.get(c, auth["guild"])
        chat_revive = chat_revives[int(index)].split(";")

        channel_info = c.execute(
            select(synced_channels.c.cname)
            .where((synced_channels.c.cid == chat_revive[0]) & (synced_channels.c.gid == str(auth["guild"])))
        ).fetchone()

        channels = [{
            "id": i[0],
            "name": i[1]
        } for i in c.execute(
            select(synced_channels.c.cid, synced_channels.c.cname)
            .where((synced_channels.c.gid == str(auth["guild"])) & (synced_channels.c.ctype == "text"))
        ).fetchall()]

    if len(chat_revives) <= int(index):
        return redirect("/settings/chat_revive", 302)

    if request.method == "POST":
        with engine.begin() as c:
            setting_chat_revive_channels.remove_from_list(c, auth["guild"], chat_revives[int(index)])

        handle_post(auth, is_edit=True)
        return redirect("/settings/chat_revive", 303)

    chat_revive_parsed = {
        "index": int(index),
        "cid": chat_revive[0],
        "channel": channel_info[0],
        "minutes": chat_revive[1]
    }

    return render_template("chat_revive_edit.html", chat_revive=chat_revive_parsed, channels=channels)
