from flask import Blueprint, flash, redirect, render_template, request, session
from sqlalchemy import select

from database import engine, synced_channels
from utils.welcome_goodbye import (
    goodbye_channel,
    goodbye_message_message,
    goodbye_message_title,
    goodbye_message_type,
    welcome_channel,
    welcome_grace_period_first,
    welcome_grace_period_second,
    welcome_message_message,
    welcome_message_title,
    welcome_message_type,
)
from web.webutils.discord_sync import validate_text_channel_id
from web.webutils.tokens import authorize, get_token_data

welcome_goodbye_bp = Blueprint(
    "welcome_goodbye", __name__, template_folder="templates"
)


def _save_channel(c, auth, setting, field):
    if field not in request.form:
        return
    if request.form[field] == "unset":
        setting.set(c, auth["guild"], "")
    elif validate_text_channel_id(request.form[field]):
        setting.set(c, auth["guild"], request.form[field])
    else:
        flash("Invalid channel selected")


def handle_save(auth, section):
    with engine.begin() as c:
        if section == "welcome":
            _save_channel(c, auth, welcome_channel, "welcome_channel")

            if (
                "welcome_title" in request.form
                and 1 < len(request.form["welcome_title"]) < 100
            ):
                welcome_message_title.set(
                    c, auth["guild"], request.form["welcome_title"]
                )

            if (
                "welcome_msg" in request.form
                and 1 < len(request.form["welcome_msg"]) < 1000
            ):
                welcome_message_message.set(
                    c, auth["guild"], request.form["welcome_msg"]
                )

            if request.form.get("welcome_type") in ("text", "embed"):
                welcome_message_type.set(
                    c, auth["guild"], request.form["welcome_type"]
                )

            if (
                request.form.get("welcome_first", "").isnumeric()
                and 0 < int(request.form["welcome_first"]) < 300
            ):
                welcome_grace_period_first.set(
                    c, auth["guild"], request.form["welcome_first"]
                )

            if (
                request.form.get("welcome_second", "").isnumeric()
                and 0 < int(request.form["welcome_second"]) < 60
            ):
                welcome_grace_period_second.set(
                    c, auth["guild"], request.form["welcome_second"]
                )

        elif section == "goodbye":
            _save_channel(c, auth, goodbye_channel, "goodbye_channel")

            if (
                "goodbye_title" in request.form
                and 1 < len(request.form["goodbye_title"]) < 100
            ):
                goodbye_message_title.set(
                    c, auth["guild"], request.form["goodbye_title"]
                )

            if (
                "goodbye_msg" in request.form
                and 1 < len(request.form["goodbye_msg"]) < 1000
            ):
                goodbye_message_message.set(
                    c, auth["guild"], request.form["goodbye_msg"]
                )

            if request.form.get("goodbye_type") in ("text", "embed"):
                goodbye_message_type.set(
                    c, auth["guild"], request.form["goodbye_type"]
                )


@welcome_goodbye_bp.route("/settings/welcome_goodbye", methods=["GET", "POST"])
def welcome_goodbye_index():
    authorization = authorize("/settings/welcome_goodbye")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    if request.method == "POST":
        section = request.form.get("_section", "welcome")
        if section not in {"welcome", "goodbye"}:
            section = "welcome"
        handle_save(auth, section)
        return redirect(
            f"/settings/welcome_goodbye?tab={request.form.get('_tab', section)}", 303
        )

    active_tab = request.args.get("tab", "welcome")
    if active_tab not in {"welcome", "goodbye", "placeholders"}:
        active_tab = "welcome"

    with engine.begin() as c:
        welcome_chan = welcome_channel.get(c, auth["guild"])
        welcome_title = welcome_message_title.get(c, auth["guild"])
        welcome_msg = welcome_message_message.get(c, auth["guild"])
        welcome_type = welcome_message_type.get(c, auth["guild"])
        welcome_first = welcome_grace_period_first.get(c, auth["guild"])
        welcome_second = welcome_grace_period_second.get(c, auth["guild"])

        goodbye_chan = goodbye_channel.get(c, auth["guild"])
        goodbye_title = goodbye_message_title.get(c, auth["guild"])
        goodbye_msg = goodbye_message_message.get(c, auth["guild"])
        goodbye_type = goodbye_message_type.get(c, auth["guild"])

        channels = [
            {"id": i[0], "name": i[1]}
            for i in c.execute(
                select(synced_channels.c.cid, synced_channels.c.cname).where(
                    (synced_channels.c.gid == auth["guild"])
                    & (synced_channels.c.ctype == "text")
                )
            )
        ]

    return render_template(
        "welcome_goodbye.html",
        welcome_channel=welcome_chan,
        welcome_title=welcome_title,
        welcome_msg=welcome_msg,
        welcome_type=welcome_type,
        welcome_first=welcome_first,
        welcome_second=welcome_second,
        goodbye_channel=goodbye_chan,
        goodbye_title=goodbye_title,
        goodbye_msg=goodbye_msg,
        goodbye_type=goodbye_type,
        channels=channels,
        active_tab=active_tab,
    )
